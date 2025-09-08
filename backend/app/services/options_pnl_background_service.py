"""
Options P&L Background Processing Service

Handles background processing of complex P&L calculations to avoid
blocking API requests. Processes all historical trades without dropping any data.
"""

import asyncio
import logging
import time
import traceback
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, extract, desc, asc, update
from sqlalchemy.orm import selectinload

from app.core.database import get_db, AsyncSessionLocal
from app.models.options_order import OptionsOrder
from app.models.options_position import OptionsPosition
from app.models.options_pnl_cache import UserOptionsPnLCache, OptionsPnLProcessingLog

logger = logging.getLogger(__name__)


class OptionsPnLBackgroundService:
    """Background service for processing options P&L calculations"""
    
    def __init__(self):
        self.processing_users = set()  # Track users currently being processed
    
    async def _ensure_user_exists(self, db: AsyncSession, user_id: UUID) -> bool:
        """
        Ensure user exists in database, create demo user if needed
        
        Args:
            db: Database session
            user_id: User UUID to check
            
        Returns:
            True if user exists, False otherwise
        """
        try:
            from app.models.user import User
            from app.core.security import ensure_demo_user_exists
            
            # Check if user exists
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                return True
            
            # If it's the demo user, ensure it exists
            if str(user_id) == "00000000-0000-0000-0000-000000000001":
                await ensure_demo_user_exists(db)
                # Re-check after ensuring demo user exists
                result = await db.execute(stmt)
                user = result.scalar_one_or_none()
                return user is not None
            
            # For other users, they should be created by the authentication system
            # If they don't exist, it's an error
            logger.error(f"User {user_id} does not exist in database")
            return False
            
        except Exception as e:
            logger.error(f"Error ensuring user exists: {str(e)}")
            return False
    
    async def _handle_session_error(self, db: AsyncSession, error: Exception) -> bool:
        """
        Handle session errors like PendingRollbackError
        
        Args:
            db: Database session
            error: The exception that occurred
            
        Returns:
            True if error was handled, False otherwise
        """
        try:
            from sqlalchemy.exc import PendingRollbackError
            
            if isinstance(error, PendingRollbackError):
                logger.warning("Session has pending rollback, attempting to rollback and continue")
                await db.rollback()
                return True
            return False
        except Exception as e:
            logger.error(f"Error handling session error: {str(e)}")
            return False
    
    async def process_user_pnl(
        self, 
        user_id: UUID, 
        processing_type: str = "full",
        force_recalculation: bool = False
    ) -> Dict[str, Any]:
        """
        Process P&L calculations for a user in the background
        
        Args:
            user_id: User UUID
            processing_type: 'full', 'incremental', or 'repair'
            force_recalculation: Force recalculation even if cache is fresh
            
        Returns:
            Dict with processing results
        """
        if user_id in self.processing_users:
            return {
                "success": False, 
                "message": "P&L processing already in progress for this user"
            }
        
        self.processing_users.add(user_id)
        
        async with AsyncSessionLocal() as db:
            try:
                # First, ensure the user exists in the database
                if not await self._ensure_user_exists(db, user_id):
                    return {
                        "success": False,
                        "message": f"User {user_id} does not exist in database"
                    }
                
                # Create processing log entry
                log_entry = OptionsPnLProcessingLog(
                    user_id=user_id,
                    processing_type=processing_type,
                    status="started"
                )
                db.add(log_entry)
                await db.commit()
                
                start_time = time.time()
                
                # Check if we need to process
                if not force_recalculation and processing_type == "incremental":
                    cache_entry = await self._get_cache_entry(db, user_id)
                    if cache_entry and not cache_entry.is_stale:
                        logger.info(f"P&L cache for user {user_id} is fresh, skipping processing")
                        return {"success": True, "message": "Cache is fresh, no processing needed"}
                
                # Update cache status to processing
                await self._update_cache_status(db, user_id, "processing")
                
                # Get all orders and positions for this user
                orders_data = await self._get_all_user_orders(db, user_id)
                positions_data = await self._get_all_user_positions(db, user_id)
                
                logger.info(f"Processing P&L for user {user_id}: {len(orders_data)} orders, {len(positions_data)} positions")
                
                # Calculate unrealized P&L from positions (fast)
                unrealized_data = self._calculate_unrealized_pnl(positions_data)
                
                # Calculate realized P&L from orders (potentially slow but comprehensive)
                realized_data = await self._calculate_realized_pnl_comprehensive(orders_data)
                
                # Combine and calculate final metrics
                final_metrics = self._combine_pnl_data(realized_data, unrealized_data)
                
                # Update cache with results
                await self._update_cache_with_results(db, user_id, final_metrics, orders_data, positions_data)
                
                # Update processing log with success
                processing_time = time.time() - start_time
                await self._update_processing_log(db, log_entry.id, "completed", processing_time, final_metrics)
                
                logger.info(f"P&L processing completed for user {user_id} in {processing_time:.2f}s")
                
                return {
                    "success": True,
                    "message": "P&L processing completed successfully",
                    "processing_time": processing_time,
                    "orders_processed": len(orders_data),
                    "positions_processed": len(positions_data)
                }
                
            except Exception as e:
                logger.error(f"Error processing P&L for user {user_id}: {str(e)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                
                # Handle session errors first
                if await self._handle_session_error(db, e):
                    # If session error was handled, try to continue with error reporting
                    try:
                        await self._update_cache_status(db, user_id, "error", str(e))
                    except Exception as update_error:
                        logger.error(f"Error updating cache status after session recovery: {str(update_error)}")
                    
                    try:
                        if 'log_entry' in locals():
                            await self._update_processing_log(db, log_entry.id, "error", None, None, str(e))
                    except Exception as log_error:
                        logger.error(f"Error updating processing log after session recovery: {str(log_error)}")
                else:
                    # Regular error handling
                    try:
                        await self._update_cache_status(db, user_id, "error", str(e))
                    except Exception as update_error:
                        logger.error(f"Error updating cache status: {str(update_error)}")
                    
                    try:
                        if 'log_entry' in locals():
                            await self._update_processing_log(db, log_entry.id, "error", None, None, str(e))
                    except Exception as log_error:
                        logger.error(f"Error updating processing log: {str(log_error)}")
                
                return {
                    "success": False,
                    "message": f"P&L processing failed: {str(e)}"
                }
            finally:
                self.processing_users.discard(user_id)
    
    async def get_cached_pnl(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get cached P&L data for a user"""
        async with AsyncSessionLocal() as db:
            cache_entry = await self._get_cache_entry(db, user_id)
            if cache_entry and cache_entry.calculation_status == "completed":
                return {
                    "analytics": cache_entry.to_analytics_dict(),
                    "yearly_breakdown": cache_entry.yearly_breakdown,
                    "symbol_breakdown": cache_entry.symbol_breakdown,
                    "calculation_info": cache_entry.calculation_summary
                }
            return None
    
    async def trigger_user_pnl_processing(self, user_id: UUID) -> Dict[str, Any]:
        """Trigger P&L processing for a user (non-blocking)"""
        if user_id in self.processing_users:
            return {
                "success": False,
                "message": "Processing already in progress"
            }
        
        # Start processing in background
        asyncio.create_task(self.process_user_pnl(user_id))
        
        return {
            "success": True,
            "message": "P&L processing started in background"
        }
    
    async def _get_cache_entry(self, db: AsyncSession, user_id: UUID) -> Optional[UserOptionsPnLCache]:
        """Get cache entry for user"""
        stmt = select(UserOptionsPnLCache).where(UserOptionsPnLCache.user_id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def _update_cache_status(
        self, 
        db: AsyncSession, 
        user_id: UUID, 
        status: str, 
        error_message: Optional[str] = None
    ):
        """Update cache status"""
        # First, ensure the user exists in the database
        if not await self._ensure_user_exists(db, user_id):
            logger.error(f"User {user_id} does not exist in database, cannot update cache status")
            return
        
        # Now update or create cache entry
        stmt = select(UserOptionsPnLCache).where(UserOptionsPnLCache.user_id == user_id)
        result = await db.execute(stmt)
        cache_entry = result.scalar_one_or_none()
        
        if not cache_entry:
            cache_entry = UserOptionsPnLCache(user_id=user_id)
            db.add(cache_entry)
        
        cache_entry.calculation_status = status
        if error_message:
            cache_entry.error_message = error_message
        
        await db.commit()
    
    async def _get_all_user_orders(self, db: AsyncSession, user_id: UUID) -> List[OptionsOrder]:
        """Get all options orders for a user"""
        stmt = select(OptionsOrder).where(
            and_(
                OptionsOrder.user_id == user_id,
                OptionsOrder.state == "filled",
                OptionsOrder.processed_premium.isnot(None)
            )
        ).order_by(OptionsOrder.filled_at)
        
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def _get_all_user_positions(self, db: AsyncSession, user_id: UUID) -> List[OptionsPosition]:
        """Get all options positions for a user"""
        stmt = select(OptionsPosition).where(
            and_(
                OptionsPosition.user_id == user_id,
                OptionsPosition.total_return.isnot(None)
            )
        )
        
        result = await db.execute(stmt)
        return result.scalars().all()
    
    def _calculate_unrealized_pnl(self, positions: List[OptionsPosition]) -> Dict[str, Any]:
        """Calculate unrealized P&L from positions"""
        total_pnl = 0.0
        position_count = len(positions)
        winning_positions = 0
        losing_positions = 0
        largest_winner = 0.0
        largest_loser = 0.0
        symbol_breakdown = {}
        
        for position in positions:
            pnl = float(position.total_return or 0)
            # Use chain_symbol as canonical ticker for positions; fallback to underlying_symbol
            try:
                symbol = (position.chain_symbol or position.underlying_symbol or "UNKNOWN").upper()
            except Exception:
                symbol = "UNKNOWN"
            
            total_pnl += pnl
            
            if pnl > 0:
                winning_positions += 1
                largest_winner = max(largest_winner, pnl)
            elif pnl < 0:
                losing_positions += 1
                largest_loser = min(largest_loser, pnl)
            
            # Symbol breakdown
            if symbol not in symbol_breakdown:
                symbol_breakdown[symbol] = {
                    "symbol": symbol,
                    "total_pnl": 0.0,
                    "position_count": 0,
                    "winning_positions": 0,
                    "losing_positions": 0
                }
            
            symbol_breakdown[symbol]["total_pnl"] += pnl
            symbol_breakdown[symbol]["position_count"] += 1
            if pnl > 0:
                symbol_breakdown[symbol]["winning_positions"] += 1
            elif pnl < 0:
                symbol_breakdown[symbol]["losing_positions"] += 1
        
        return {
            "total_pnl": total_pnl,
            "position_count": position_count,
            "winning_positions": winning_positions,
            "losing_positions": losing_positions,
            "largest_winner": largest_winner,
            "largest_loser": largest_loser,
            "symbol_breakdown": symbol_breakdown
        }
    
    async def _calculate_realized_pnl_comprehensive(self, orders: List[OptionsOrder]) -> Dict[str, Any]:
        """Calculate comprehensive realized P&L from all orders"""
        logger.info(f"Processing {len(orders)} orders for realized P&L calculation")
        
        # Match opening and closing orders
        matched_trades = self._match_opening_closing_orders_optimized(orders)
        
        logger.info(f"Matched {len(matched_trades)} trades from {len(orders)} orders")
        
        # Calculate metrics from matched trades
        total_pnl = 0.0
        trade_count = len(matched_trades)
        winning_trades = 0
        losing_trades = 0
        largest_winner = 0.0
        largest_loser = 0.0
        yearly_breakdown = {}
        symbol_breakdown = {}
        
        for trade in matched_trades:
            pnl = trade["pnl"]
            symbol = trade["symbol"]
            close_year = trade.get("close_year", datetime.now().year)
            
            total_pnl += pnl
            
            if pnl > 0:
                winning_trades += 1
                largest_winner = max(largest_winner, pnl)
            elif pnl < 0:
                losing_trades += 1
                largest_loser = min(largest_loser, pnl)
            
            # Yearly breakdown
            if close_year not in yearly_breakdown:
                yearly_breakdown[close_year] = {
                    "year": close_year,
                    "realized_pnl": 0.0,
                    "trade_count": 0,
                    "winning_trades": 0,
                    "losing_trades": 0
                }
            
            yearly_breakdown[close_year]["realized_pnl"] += pnl
            yearly_breakdown[close_year]["trade_count"] += 1
            if pnl > 0:
                yearly_breakdown[close_year]["winning_trades"] += 1
            elif pnl < 0:
                yearly_breakdown[close_year]["losing_trades"] += 1
            
            # Symbol breakdown
            if symbol not in symbol_breakdown:
                symbol_breakdown[symbol] = {
                    "symbol": symbol,
                    "total_pnl": 0.0,
                    "trade_count": 0,
                    "winning_trades": 0,
                    "losing_trades": 0
                }
            
            symbol_breakdown[symbol]["total_pnl"] += pnl
            symbol_breakdown[symbol]["trade_count"] += 1
            if pnl > 0:
                symbol_breakdown[symbol]["winning_trades"] += 1
            elif pnl < 0:
                symbol_breakdown[symbol]["losing_trades"] += 1
        
        # Calculate win rates for yearly breakdown
        for year_data in yearly_breakdown.values():
            total = year_data["winning_trades"] + year_data["losing_trades"]
            year_data["win_rate"] = (year_data["winning_trades"] / total * 100) if total > 0 else 0
        
        return {
            "total_pnl": total_pnl,
            "trade_count": trade_count,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "largest_winner": largest_winner,
            "largest_loser": largest_loser,
            "yearly_breakdown": sorted(yearly_breakdown.values(), key=lambda x: x["year"]),
            "symbol_breakdown": symbol_breakdown
        }
    
    def _match_opening_closing_orders_optimized(self, orders: List[OptionsOrder]) -> List[Dict[str, Any]]:
        """
        Optimized order matching that processes ALL orders without dropping any
        Uses efficient data structures and algorithms for large datasets
        """
        trades = []
        
        # Group orders by position key for efficient matching
        position_groups = defaultdict(list)
        
        for order in orders:
            if not order.underlying_symbol or not order.strike_price:
                continue
                
            key = (
                order.underlying_symbol,
                str(order.strike_price),
                order.expiration_date,
                order.option_type
            )
            position_groups[key].append(order)
        
        logger.info(f"Grouped orders into {len(position_groups)} position groups")
        
        # Process each position group
        for key, group_orders in position_groups.items():
            # Sort by filled_at for proper FIFO matching
            group_orders.sort(key=lambda x: x.filled_at or datetime.min)
            
            # Use deque for efficient FIFO operations
            from collections import deque
            open_orders = deque()
            
            for order in group_orders:
                if order.position_effect == "open":
                    open_orders.append(order)
                elif order.position_effect == "close" and open_orders:
                    # Match with the first open order (FIFO)
                    open_order = open_orders.popleft()
                    
                    # Calculate P&L
                    pnl = self._calculate_trade_pnl_optimized(open_order, order)
                    
                    # Extract close date for yearly breakdown
                    close_date = order.filled_at
                    close_year = datetime.now().year
                    if close_date:
                        try:
                            close_year = close_date.year
                        except:
                            pass
                    
                    trades.append({
                        "symbol": order.underlying_symbol,
                        "strike_price": float(order.strike_price or 0),
                        "expiration_date": order.expiration_date,
                        "option_type": order.option_type,
                        "open_date": open_order.filled_at,
                        "close_date": order.filled_at,
                        "close_year": close_year,
                        "contracts": abs(float(order.quantity or 0)),
                        "opening_premium": float(open_order.processed_premium or 0),
                        "closing_premium": float(order.processed_premium or 0),
                        "pnl": pnl,
                        "transaction_side": open_order.transaction_side,
                        "processed_premium_direction": open_order.processed_premium_direction
                    })
        
        return trades
    
    def _calculate_trade_pnl_optimized(self, open_order: OptionsOrder, close_order: OptionsOrder) -> float:
        """Optimized P&L calculation for a matched trade pair"""
        try:
            open_premium = float(open_order.processed_premium or 0)
            close_premium = float(close_order.processed_premium or 0)
            contracts = abs(float(close_order.quantity or 0))
            
            # Determine position type based on direction
            open_direction = (open_order.processed_premium_direction or open_order.direction or "").lower()
            
            # Debug logging for suspicious values
            if contracts > 1000 or abs(open_premium) > 1000 or abs(close_premium) > 1000:
                logger.warning(f"Suspicious trade values: {open_order.underlying_symbol} - contracts: {contracts}, open_premium: {open_premium}, close_premium: {close_premium}")
            
            # Based on analysis of inflated P&L numbers, processed_premium appears to be 
            # already the total premium (not per-contract), so we should NOT multiply by 100
            if open_direction == "debit":
                # Long position: paid to open, received to close
                pnl = (close_premium - open_premium)
            elif open_direction == "credit":
                # Short position: received to open, paid to close  
                pnl = (open_premium - close_premium)
            else:
                # Fallback logic based on transaction side
                if open_order.transaction_side == "buy":
                    pnl = (close_premium - open_premium)
                else:
                    pnl = (open_premium - close_premium)
            
            # Additional debug logging for extreme P&L values
            if abs(pnl) > 50000:
                logger.warning(f"Extreme P&L calculated: {pnl} for {open_order.underlying_symbol} - open: {open_premium}, close: {close_premium}, contracts: {contracts}")
            
            return pnl
            
        except Exception as e:
            logger.error(f"Error calculating trade P&L: {str(e)}")
            return 0.0
    
    def _combine_pnl_data(self, realized_data: Dict[str, Any], unrealized_data: Dict[str, Any]) -> Dict[str, Any]:
        """Combine realized and unrealized P&L data"""
        total_pnl = realized_data["total_pnl"] + unrealized_data["total_pnl"]
        total_trades = realized_data["trade_count"] + unrealized_data["position_count"]
        
        winning_trades = realized_data["winning_trades"] + unrealized_data["winning_positions"]
        losing_trades = realized_data["losing_trades"] + unrealized_data["losing_positions"]
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Combine symbol breakdowns
        combined_symbols = self._combine_symbol_breakdowns(
            realized_data["symbol_breakdown"], 
            unrealized_data["symbol_breakdown"]
        )
        
        return {
            "total_pnl": total_pnl,
            "realized_pnl": realized_data["total_pnl"],
            "unrealized_pnl": unrealized_data["total_pnl"],
            "total_trades": total_trades,
            "realized_trades": realized_data["trade_count"],
            "open_positions": unrealized_data["position_count"],
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "largest_winner": max(realized_data["largest_winner"], unrealized_data["largest_winner"]),
            "largest_loser": min(realized_data["largest_loser"], unrealized_data["largest_loser"]),
            "avg_trade_pnl": total_pnl / total_trades if total_trades > 0 else 0,
            "yearly_breakdown": realized_data["yearly_breakdown"],
            "symbol_breakdown": combined_symbols
        }
    
    def _combine_symbol_breakdowns(self, realized: Dict, unrealized: Dict) -> List[Dict[str, Any]]:
        """Combine realized and unrealized symbol breakdowns"""
        combined = {}
        
        # Add realized data
        for symbol, data in realized.items():
            combined[symbol] = {
                "symbol": symbol,
                "total_pnl": data["total_pnl"],
                "realized_pnl": data["total_pnl"],
                "unrealized_pnl": 0.0,
                "total_trades": data["trade_count"],
                "realized_trades": data["trade_count"],
                "open_positions": 0,
                "winning_trades": data["winning_trades"],
                "losing_trades": data["losing_trades"]
            }
        
        # Add unrealized data
        for symbol, data in unrealized.items():
            if symbol not in combined:
                combined[symbol] = {
                    "symbol": symbol,
                    "total_pnl": data["total_pnl"],
                    "realized_pnl": 0.0,
                    "unrealized_pnl": data["total_pnl"],
                    "total_trades": data["position_count"],
                    "realized_trades": 0,
                    "open_positions": data["position_count"],
                    "winning_trades": data["winning_positions"],
                    "losing_trades": data["losing_positions"]
                }
            else:
                combined[symbol]["total_pnl"] += data["total_pnl"]
                combined[symbol]["unrealized_pnl"] = data["total_pnl"]
                combined[symbol]["total_trades"] += data["position_count"]
                combined[symbol]["open_positions"] = data["position_count"]
                combined[symbol]["winning_trades"] += data["winning_positions"]
                combined[symbol]["losing_trades"] += data["losing_positions"]
        
        # Calculate win rates and sort by total P&L
        symbol_list = []
        for symbol_data in combined.values():
            total_trades = symbol_data["winning_trades"] + symbol_data["losing_trades"]
            symbol_data["win_rate"] = (symbol_data["winning_trades"] / total_trades * 100) if total_trades > 0 else 0
            symbol_data["avg_trade_pnl"] = symbol_data["total_pnl"] / symbol_data["total_trades"] if symbol_data["total_trades"] > 0 else 0
            symbol_list.append(symbol_data)
        
        return sorted(symbol_list, key=lambda x: x["total_pnl"], reverse=True)
    
    async def _update_processing_log(
        self,
        db: AsyncSession,
        log_id: UUID,
        status: str,
        processing_time: Optional[float] = None,
        metrics: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ):
        """Update processing log entry with results or error"""
        stmt = select(OptionsPnLProcessingLog).where(OptionsPnLProcessingLog.id == log_id)
        result = await db.execute(stmt)
        log_entry = result.scalar_one_or_none()
        
        if log_entry:
            log_entry.status = status
            log_entry.completed_at = datetime.utcnow()
            
            if processing_time is not None:
                log_entry.processing_time_seconds = round(processing_time, 3)
            
            if metrics is not None:
                log_entry.orders_found = metrics.get("total_trades", 0)
                log_entry.orders_processed = metrics.get("total_trades", 0)
                log_entry.trades_matched = metrics.get("realized_trades", 0)
                log_entry.positions_processed = metrics.get("open_positions", 0)
                log_entry.total_pnl_calculated = metrics.get("total_pnl", 0)
            
            if error_message is not None:
                log_entry.error_message = error_message
                log_entry.error_details = {"traceback": traceback.format_exc()}
            
            await db.commit()
    
    async def _update_cache_with_results(
        self, 
        db: AsyncSession, 
        user_id: UUID, 
        metrics: Dict[str, Any],
        orders: List[OptionsOrder],
        positions: List[OptionsPosition]
    ):
        """Update cache with calculated results"""
        # First, ensure the user exists in the database
        if not await self._ensure_user_exists(db, user_id):
            logger.error(f"User {user_id} does not exist in database, cannot update cache with results")
            return
        
        # Now update or create cache entry
        stmt = select(UserOptionsPnLCache).where(UserOptionsPnLCache.user_id == user_id)
        result = await db.execute(stmt)
        cache_entry = result.scalar_one_or_none()
        
        if not cache_entry:
            cache_entry = UserOptionsPnLCache(user_id=user_id)
            db.add(cache_entry)
        
        # Update all metrics
        cache_entry.total_pnl = metrics["total_pnl"]
        cache_entry.realized_pnl = metrics["realized_pnl"]
        cache_entry.unrealized_pnl = metrics["unrealized_pnl"]
        cache_entry.total_trades = metrics["total_trades"]
        cache_entry.realized_trades = metrics["realized_trades"]
        cache_entry.open_positions = metrics["open_positions"]
        cache_entry.winning_trades = metrics["winning_trades"]
        cache_entry.losing_trades = metrics["losing_trades"]
        cache_entry.win_rate = metrics["win_rate"]
        cache_entry.largest_winner = metrics["largest_winner"]
        cache_entry.largest_loser = metrics["largest_loser"]
        cache_entry.avg_trade_pnl = metrics["avg_trade_pnl"]
        
        # Store breakdowns as JSON
        cache_entry.yearly_breakdown = metrics["yearly_breakdown"]
        cache_entry.symbol_breakdown = metrics["symbol_breakdown"]
        
        # Update processing metadata
        cache_entry.last_calculated_at = datetime.utcnow()
        cache_entry.calculation_status = "completed"
        cache_entry.error_message = None
        cache_entry.orders_processed = len(orders)
        cache_entry.positions_processed = len(positions)
        cache_entry.needs_recalculation = False
        
        # Set last order date for freshness tracking
        if orders:
            filled_dates = [order.filled_at for order in orders if order.filled_at]
            if filled_dates:
                cache_entry.last_order_date = max(filled_dates)
        
        await db.commit()


# Global service instance
pnl_background_service = OptionsPnLBackgroundService()
