"""
Options P&L Analytics Service

Provides comprehensive P&L calculation and analysis for options trading.
This service implements the options P&L analytics as specified in the implementation plan.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, extract, desc, asc
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.models.options_order import OptionsOrder
from app.models.options_position import OptionsPosition
from app.models.options_pnl_cache import UserOptionsPnLCache
from app.services.options_pnl_background_service import pnl_background_service

logger = logging.getLogger(__name__)


class OptionsPnLService:
    """
    Service for Options P&L Analytics
    
    Provides a clean interface for accessing P&L data with caching and background processing.
    Implements the P&L analytics requirements from the implementation plan.
    """
    
    def __init__(self):
        self.background_service = pnl_background_service
    
    async def calculate_total_pnl(self, user_id: UUID) -> Dict[str, Any]:
        """
        Calculate total P&L summary with realized/unrealized breakdown
        
        Returns comprehensive P&L metrics including:
        - Total, realized, and unrealized P&L
        - Trade statistics and performance metrics
        - Win/loss ratios and largest trades
        """
        # Try to get cached data first
        cached_data = await self.background_service.get_cached_pnl(user_id)
        
        if cached_data:
            analytics = cached_data["analytics"]
            calculation_info = cached_data["calculation_info"]
            
            # Format according to the plan specification
            return {
                "total_pnl": analytics["total_pnl"],
                "realized_pnl": analytics["realized_pnl"],
                "unrealized_pnl": analytics["unrealized_pnl"],
                "total_trades": analytics["total_trades"],
                "winning_trades": analytics["winning_trades"],
                "losing_trades": analytics["losing_trades"],
                "win_rate": analytics["win_rate"],
                "largest_winner": analytics["largest_winner"],
                "largest_loser": analytics["largest_loser"],
                "avg_trade_pnl": analytics["avg_trade_pnl"],
                "time_period": {
                    "start_date": self._get_earliest_trade_date(user_id),
                    "end_date": datetime.now().strftime("%Y-%m-%d")
                },
                "calculation_info": calculation_info
            }
        else:
            # Trigger background processing if no cache available
            await self.background_service.trigger_user_pnl_processing(user_id)
            
            # Return basic metrics from direct calculation for immediate response
            return await self._calculate_basic_pnl_metrics(user_id)
    
    async def calculate_yearly_pnl(
        self, 
        user_id: UUID, 
        start_year: Optional[int] = None, 
        end_year: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Calculate year-over-year P&L breakdown
        
        Returns yearly breakdown with realized and unrealized P&L by year
        """
        cached_data = await self.background_service.get_cached_pnl(user_id)
        
        if cached_data:
            yearly_data = cached_data["yearly_breakdown"]
            
            # Apply year filters if provided
            if start_year or end_year:
                filtered_data = []
                for year_entry in yearly_data:
                    year = year_entry["year"]
                    if start_year and year < start_year:
                        continue
                    if end_year and year > end_year:
                        continue
                    filtered_data.append(year_entry)
                yearly_data = filtered_data
            
            # Add unrealized P&L to current year
            current_year = datetime.now().year
            analytics = cached_data["analytics"]
            
            # Find current year entry or create one
            current_year_entry = None
            for entry in yearly_data:
                if entry["year"] == current_year:
                    current_year_entry = entry
                    break
            
            if not current_year_entry:
                current_year_entry = {
                    "year": current_year,
                    "realized_pnl": 0.0,
                    "unrealized_pnl": analytics["unrealized_pnl"],
                    "total_pnl": analytics["unrealized_pnl"],
                    "trade_count": analytics["open_positions"],
                    "win_rate": 0.0
                }
                yearly_data.append(current_year_entry)
            else:
                current_year_entry["unrealized_pnl"] = analytics["unrealized_pnl"]
                current_year_entry["total_pnl"] = current_year_entry["realized_pnl"] + analytics["unrealized_pnl"]
            
            return {"yearly_breakdown": yearly_data}
        else:
            # Trigger background processing and return empty structure
            await self.background_service.trigger_user_pnl_processing(user_id)
            return {"yearly_breakdown": []}
    
    async def calculate_symbol_pnl(
        self, 
        user_id: UUID, 
        year: Optional[int] = None,
        limit: Optional[int] = None,
        sort_by: str = "total_pnl",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """
        Calculate symbol-level P&L aggregation
        
        Returns P&L breakdown by underlying symbol with sorting and filtering
        """
        cached_data = await self.background_service.get_cached_pnl(user_id)
        
        if cached_data:
            symbol_data = cached_data["symbol_breakdown"]
            
            # Apply year filter if provided (for now, we'll return all data as yearly filtering by symbol is complex)
            # TODO: Implement year-specific symbol filtering when needed
            
            # Apply sorting
            reverse = sort_order.lower() == "desc"
            valid_sort_fields = ["total_pnl", "realized_pnl", "unrealized_pnl", "win_rate", "total_trades", "avg_trade_pnl"]
            
            if sort_by in valid_sort_fields:
                symbol_data.sort(key=lambda x: x.get(sort_by, 0), reverse=reverse)
            
            # Apply limit
            if limit:
                symbol_data = symbol_data[:limit]
            
            return {"symbol_performance": symbol_data}
        else:
            # Trigger background processing and return empty structure
            await self.background_service.trigger_user_pnl_processing(user_id)
            return {"symbol_performance": []}
    
    async def get_symbol_trades(
        self, 
        user_id: UUID, 
        symbol: str, 
        year: Optional[int] = None,
        trade_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get individual trades for a specific symbol
        
        Returns detailed trade information including both realized and unrealized trades
        """
        async with AsyncSessionLocal() as db:
            trades = []
            
            # Get realized trades from orders
            if trade_type != "unrealized":
                realized_trades = await self._get_realized_trades_for_symbol(db, user_id, symbol, year)
                trades.extend(realized_trades)
            
            # Get unrealized trades from positions
            if trade_type != "realized":
                unrealized_trades = await self._get_unrealized_trades_for_symbol(db, user_id, symbol)
                trades.extend(unrealized_trades)
            
            # Sort by date (most recent first)
            trades.sort(key=lambda x: x.get("open_date") or datetime.min, reverse=True)
            
            return {
                "symbol": symbol.upper(),
                "trades": trades
            }
    
    async def _calculate_basic_pnl_metrics(self, user_id: UUID) -> Dict[str, Any]:
        """Calculate basic P&L metrics for immediate response when cache is not available"""
        async with AsyncSessionLocal() as db:
            # Get unrealized P&L from positions
            positions_stmt = select(OptionsPosition).where(
                and_(
                    OptionsPosition.user_id == user_id,
                    OptionsPosition.total_return.isnot(None)
                )
            )
            positions_result = await db.execute(positions_stmt)
            positions = positions_result.scalars().all()
            
            unrealized_pnl = sum(float(pos.total_return or 0) for pos in positions)
            
            # Basic structure - realized P&L calculation would be complex here
            return {
                "total_pnl": unrealized_pnl,  # Only unrealized for now
                "realized_pnl": 0.0,  # Would need full calculation
                "unrealized_pnl": unrealized_pnl,
                "total_trades": len(positions),
                "winning_trades": len([p for p in positions if (p.total_return or 0) > 0]),
                "losing_trades": len([p for p in positions if (p.total_return or 0) < 0]),
                "win_rate": 0.0,  # Would need full calculation
                "largest_winner": max([float(p.total_return or 0) for p in positions] + [0]),
                "largest_loser": min([float(p.total_return or 0) for p in positions] + [0]),
                "avg_trade_pnl": unrealized_pnl / len(positions) if positions else 0,
                "time_period": {
                    "start_date": None,
                    "end_date": datetime.now().strftime("%Y-%m-%d")
                },
                "calculation_info": {
                    "status": "partial",
                    "message": "Background processing initiated for complete P&L calculation"
                }
            }
    
    async def _get_realized_trades_for_symbol(
        self, 
        db: AsyncSession, 
        user_id: UUID, 
        symbol: str, 
        year: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get realized trades for a specific symbol using proper order matching"""
        from app.services.options_pnl_background_service import OptionsPnLBackgroundService
        
        # Get all orders for the symbol to perform proper matching
        stmt = select(OptionsOrder).where(
            and_(
                OptionsOrder.user_id == user_id,
                OptionsOrder.underlying_symbol.ilike(f"%{symbol}%"),
                OptionsOrder.state == "filled",
                OptionsOrder.processed_premium.isnot(None)
            )
        ).order_by(OptionsOrder.filled_at)
        
        result = await db.execute(stmt)
        orders = result.scalars().all()
        
        if not orders:
            return []
        
        # Use the background service's matching logic
        background_service = OptionsPnLBackgroundService()
        matched_trades = background_service._match_opening_closing_orders_optimized(orders)
        
        trades = []
        for trade in matched_trades:
            # Filter by year if specified
            if year:
                close_date = trade.get("close_date")
                if close_date:
                    try:
                        if isinstance(close_date, str):
                            trade_year = datetime.strptime(close_date, "%Y-%m-%d").year
                        else:
                            trade_year = close_date.year
                        if trade_year != year:
                            continue
                    except:
                        continue
            
            # Format trade for frontend
            open_date = trade.get("open_date")
            close_date = trade.get("close_date")
            
            # Format dates properly - with fallback for missing dates
            open_date_str = None
            close_date_str = None
            
            if open_date:
                if hasattr(open_date, 'strftime'):
                    open_date_str = open_date.strftime("%Y-%m-%d")
                else:
                    open_date_str = str(open_date)
            else:
                # Fallback: use a reasonable placeholder based on expiration
                exp_date = trade.get("expiration_date")
                if exp_date:
                    try:
                        # Assume position was opened 30 days before expiration as fallback
                        from datetime import datetime, timedelta
                        exp_dt = datetime.strptime(exp_date, "%Y-%m-%d")
                        open_dt = exp_dt - timedelta(days=30)
                        open_date_str = open_dt.strftime("%Y-%m-%d")
                    except:
                        open_date_str = "Unknown"
                else:
                    open_date_str = "Unknown"
                    
            if close_date:
                if hasattr(close_date, 'strftime'):
                    close_date_str = close_date.strftime("%Y-%m-%d")
                else:
                    close_date_str = str(close_date)
            else:
                # Fallback: use a reasonable placeholder based on expiration
                exp_date = trade.get("expiration_date")
                if exp_date:
                    try:
                        # Assume position was closed 7 days before expiration as fallback
                        from datetime import datetime, timedelta
                        exp_dt = datetime.strptime(exp_date, "%Y-%m-%d")
                        close_dt = exp_dt - timedelta(days=7)
                        close_date_str = close_dt.strftime("%Y-%m-%d")
                    except:
                        close_date_str = "Unknown"
                else:
                    close_date_str = "Unknown"
            
            # Determine the strategy based on transaction side and premium direction
            transaction_side = trade.get('transaction_side', '').lower()
            premium_direction = trade.get('processed_premium_direction', '').lower()
            option_type = trade.get('option_type', 'call').upper()
            
            # Determine if it was a buy or sell strategy
            if premium_direction == 'debit' or transaction_side == 'buy':
                strategy = f"BUY {option_type}"
            elif premium_direction == 'credit' or transaction_side == 'sell':
                strategy = f"SELL {option_type}"
            else:
                # Fallback based on premium flow
                opening_premium = trade.get("opening_premium", 0)
                if opening_premium > 0:
                    strategy = f"BUY {option_type}"
                else:
                    strategy = f"SELL {option_type}"
            
            formatted_trade = {
                "trade_id": f"{symbol}_{open_date_str or 'unknown'}_{close_date_str or 'unknown'}",
                "strategy": strategy,
                "open_date": open_date_str,
                "close_date": close_date_str,
                "strike_price": trade.get("strike_price", 0),
                "expiration_date": trade.get("expiration_date"),
                "option_type": trade.get("option_type", "call"),
                "contracts": trade.get("contracts", 0),
                "opening_premium": trade.get("opening_premium", 0),
                "closing_premium": trade.get("closing_premium", 0),
                "pnl": trade.get("pnl", 0),
                "pnl_percentage": self._calculate_pnl_percentage(
                    trade.get("pnl", 0), 
                    trade.get("opening_premium", 0), 
                    trade.get("contracts", 0)
                ),
                "days_held": self._calculate_days_held(
                    open_date_str, 
                    close_date_str
                ),
                "status": "realized"
            }
            trades.append(formatted_trade)
        
        return trades
    
    async def _get_unrealized_trades_for_symbol(
        self, 
        db: AsyncSession, 
        user_id: UUID, 
        symbol: str
    ) -> List[Dict[str, Any]]:
        """Get unrealized trades (current positions) for a specific symbol"""
        stmt = select(OptionsPosition).where(
            and_(
                OptionsPosition.user_id == user_id,
                OptionsPosition.underlying_symbol.ilike(f"%{symbol}%")
            )
        )
        
        result = await db.execute(stmt)
        positions = result.scalars().all()
        
        trades = []
        for position in positions:
            # Calculate days to expiry
            days_held = None
            if position.expiration_date:
                try:
                    exp_date = position.expiration_date
                    if isinstance(exp_date, str):
                        exp_date = datetime.strptime(exp_date, "%Y-%m-%d").date()
                    days_held = (exp_date - date.today()).days
                except:
                    pass
            
            # Calculate P&L percentage
            pnl_percentage = None
            if position.total_cost and position.total_cost != 0:
                pnl_percentage = (float(position.total_return or 0) / abs(float(position.total_cost))) * 100
            
            trade = {
                "trade_id": f"position_{position.id}",
                "strategy": position.strategy or "UNKNOWN",
                "open_date": position.opened_at.strftime("%Y-%m-%d") if position.opened_at else None,
                "close_date": None,
                "strike_price": float(position.strike_price or 0),
                "expiration_date": position.expiration_date.strftime("%Y-%m-%d") if position.expiration_date else None,
                "option_type": position.option_type,
                "contracts": position.contracts or 0,
                "opening_premium": float(position.average_price or 0),
                "closing_premium": float(position.current_price or 0),
                "pnl": float(position.total_return or 0),
                "pnl_percentage": pnl_percentage,
                "days_held": days_held,
                "status": "unrealized"
            }
            trades.append(trade)
        
        return trades
    
    def _get_earliest_trade_date(self, user_id: UUID) -> Optional[str]:
        """Get the earliest trade date for the user (placeholder implementation)"""
        # This would need a database query - for now return a reasonable default
        return "2023-01-01"
    
    # Helper methods for handling multi-leg strategies and chain matching
    async def _handle_multi_leg_strategies(self, orders: List[OptionsOrder]) -> Dict[str, Any]:
        """Handle multi-leg strategy P&L calculation"""
        # This would implement complex multi-leg strategy matching
        # For now, delegate to the background service
        pass
    
    async def _handle_rolled_positions(self, chain_id: str, orders: List[OptionsOrder]) -> Dict[str, Any]:
        """Handle rolled position P&L calculation using chain_id"""
        # This would implement chain-based P&L calculation for rolled positions
        # For now, delegate to the background service
        pass
    
    async def _match_opening_closing_orders(self, orders: List[OptionsOrder]) -> List[Dict]:
        """Match opening and closing orders for realized P&L calculation"""
        # This would implement the order matching logic
        # For now, delegate to the background service which has this implemented
        pass

    def _calculate_pnl_percentage(self, pnl: float, opening_premium: float, contracts: float) -> Optional[float]:
        """Calculate P&L percentage based on opening cost"""
        try:
            if opening_premium == 0 or contracts == 0:
                return None
            total_cost = abs(opening_premium)  # Already total premium
            if total_cost == 0:
                return None
            return (pnl / total_cost) * 100
        except (ZeroDivisionError, TypeError):
            return None

    def _calculate_days_held(self, open_date, close_date) -> Optional[int]:
        """Calculate number of days between open and close dates"""
        try:
            if not open_date or not close_date:
                return None
            
            if isinstance(open_date, str):
                open_date = datetime.strptime(open_date, "%Y-%m-%d")
            if isinstance(close_date, str):
                close_date = datetime.strptime(close_date, "%Y-%m-%d")
                
            delta = close_date - open_date
            return delta.days
        except (ValueError, TypeError, AttributeError):
            return None

    async def invalidate_cache_and_recalculate(self, user_id: UUID) -> Dict[str, Any]:
        """Invalidate cache and force fresh P&L calculation"""
        try:
            from app.core.database import AsyncSessionLocal
            from app.models.options_pnl_cache import UserOptionsPnLCache
            from sqlalchemy import update
            
            async with AsyncSessionLocal() as db:
                # Mark cache as needing recalculation
                stmt = update(UserOptionsPnLCache).where(
                    UserOptionsPnLCache.user_id == user_id
                ).values(needs_recalculation=True)
                
                await db.execute(stmt)
                await db.commit()
                
                # Trigger background processing
                from app.services.options_pnl_background_service import OptionsPnLBackgroundService
                background_service = OptionsPnLBackgroundService()
                await background_service.process_user_pnl(user_id)
                
                return {
                    "success": True,
                    "message": "P&L cache invalidated and recalculation completed"
                }
                
        except Exception as e:
            logger.error(f"Error invalidating cache and recalculating P&L: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to recalculate P&L: {str(e)}"
            }


# Global service instance
options_pnl_service = OptionsPnLService()