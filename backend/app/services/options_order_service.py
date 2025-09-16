"""
Options Orders Database Service

Handles persistent storage and incremental synchronization of options orders
to optimize rolled options analysis performance.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Callable
from sqlalchemy import select, and_, desc, func, asc, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import get_db
from app.core.redis import cache
from app.models.options_order import OptionsOrder
from app.models.user import User  # Import User model to resolve relationship
from app.services.robinhood_service import RobinhoodService

logger = logging.getLogger(__name__)


class OptionsOrderService:
    """Service for managing options orders in database with incremental sync"""
    
    def __init__(self, rh_service: RobinhoodService):
        self.rh_service = rh_service
        self.progress_callbacks = {}
    
    def set_progress_callback(self, user_id: str, callback: Callable[[Dict[str, Any]], None]):
        """Set a progress callback for a user's sync operation"""
        self.progress_callbacks[user_id] = callback
    
    def _update_progress(self, user_id: str, progress_data: Dict[str, Any]):
        """Update progress for a user if callback is set"""
        callback = self.progress_callbacks.get(user_id)
        if callback:
            try:
                callback(progress_data)
            except Exception as e:
                logger.warning(f"Progress callback error for user {user_id}: {str(e)}")
    
    async def sync_options_orders(
        self, 
        user_id: str, 
        force_full_sync: bool = False,
        days_back: int = 30,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """
        Sync options orders from Robinhood to database with incremental updates
        
        Args:
            user_id: User ID to sync orders for
            force_full_sync: If True, fetch all orders regardless of last sync
            days_back: Days to look back for incremental sync
            progress_callback: Optional callback to receive progress updates
        """
        if progress_callback:
            self.set_progress_callback(user_id, progress_callback)
        
        # Update progress: Starting sync
        self._update_progress(user_id, {
            "status": "starting",
            "message": "Initializing options orders sync...",
            "progress": 0
        })
        try:
            async for db in get_db():
                # Determine sync strategy
                last_sync_time = None
                if not force_full_sync:
                    last_sync_time = await self._get_last_sync_time(db, user_id)
                
                # If no last sync or force full sync, go back specified days
                if last_sync_time is None:
                    since_time = datetime.now() - timedelta(days=days_back)
                    sync_type = "full"
                else:
                    # Incremental sync: get orders since last sync minus 1 day buffer
                    since_time = last_sync_time - timedelta(days=1)
                    sync_type = "incremental"
                
                logger.info(f"Syncing options orders ({sync_type}) since {since_time} for user {user_id}")
                
                # Update progress: Fetching from API
                self._update_progress(user_id, {
                    "status": "fetching",
                    "message": f"Fetching orders from Robinhood API ({sync_type} sync)...",
                    "progress": 10,
                    "sync_type": sync_type,
                    "since_time": since_time.isoformat()
                })
                
                # Fetch orders from Robinhood with smart limits
                # Use smaller limit for initial sync to prevent timeouts
                limit = 1000 if days_back <= 90 else 2000
                orders_response = await self.rh_service.get_options_orders(
                    limit=limit,
                    since_time=since_time
                )
                
                if not orders_response["success"]:
                    # Check if it's an authentication error, then use demo data
                    if "logged in" in orders_response.get("message", "").lower():
                        logger.info("Authentication required for Robinhood API. Creating demo data.")
                        return await self._create_demo_data(user_id, days_back)
                    return {
                        "success": False,
                        "message": "Failed to fetch orders from Robinhood",
                        "data": None
                    }
                
                orders = orders_response["data"]
                
                # Update progress: Processing orders
                self._update_progress(user_id, {
                    "status": "processing",
                    "message": f"Processing {len(orders)} orders...",
                    "progress": 30,
                    "orders_fetched": len(orders)
                })
                
                # Process and store orders with progress updates
                stored_count = await self._store_orders_with_progress(db, user_id, orders)
                
                # Clear progress callback
                if user_id in self.progress_callbacks:
                    del self.progress_callbacks[user_id]

                # Invalidate cached options orders so UI sees fresh data
                try:
                    cleared = await cache.clear_pattern("options:orders:*")
                    if cleared:
                        logger.info(f"Cleared {cleared} cached options:orders entries after sync")
                except Exception as cache_error:
                    logger.warning(f"Could not clear options orders cache: {cache_error}")

                # Update progress: Complete
                self._update_progress(user_id, {
                    "status": "complete",
                    "message": f"Successfully synced {stored_count} orders",
                    "progress": 100,
                    "orders_stored": stored_count
                })
                
                return {
                    "success": True,
                    "message": f"Synced {stored_count} orders",
                    "data": {
                        "orders_processed": len(orders),
                        "orders_stored": stored_count,
                        "sync_time": datetime.now().isoformat(),
                        "since_time": since_time.isoformat(),
                        "sync_type": sync_type
                    }
                }
                
        except Exception as e:
            logger.error(f"Error syncing options orders: {str(e)}", exc_info=True)
            # Update progress: Error
            self._update_progress(user_id, {
                "status": "error",
                "message": f"Sync failed: {str(e)}",
                "progress": 0
            })
            # Clear progress callback
            if user_id in self.progress_callbacks:
                del self.progress_callbacks[user_id]
            return {
                "success": False,
                "message": f"Sync error: {str(e)}",
                "data": None
            }
    
    async def get_orders_by_chain_id(
        self, 
        user_id: str,
        chain_id: str,
        db: AsyncSession
    ) -> List[OptionsOrder]:
        """Get all orders for a specific chain ID"""
        try:
            stmt = select(OptionsOrder).where(
                and_(
                    OptionsOrder.user_id == user_id,
                    OptionsOrder.chain_id == chain_id,
                    OptionsOrder.state.notin_(['cancelled', 'canceled', 'rejected', 'failed'])
                )
            ).order_by(OptionsOrder.order_created_at.desc())
            
            result = await db.execute(stmt)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error fetching orders by chain_id {chain_id}: {str(e)}")
            return []
    
    async def get_orders_by_chain_id_and_type(
        self, 
        user_id: str,
        chain_id: str,
        option_type: str,
        db: AsyncSession
    ) -> List[OptionsOrder]:
        """Get all orders for a specific chain ID and option type (call/put)"""
        try:
            stmt = select(OptionsOrder).where(
                and_(
                    OptionsOrder.user_id == user_id,
                    OptionsOrder.chain_id == chain_id,
                    OptionsOrder.option_type == option_type,
                    OptionsOrder.state.notin_(['cancelled', 'canceled', 'rejected', 'failed'])
                )
            ).order_by(OptionsOrder.order_created_at.desc())
            
            result = await db.execute(stmt)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error fetching orders by chain_id {chain_id} and type {option_type}: {str(e)}")
            return []
    
    async def get_rolled_options_chains_from_db(
        self,
        user_id: str,
        days_back: int = 365,
        symbol: Optional[str] = None,
        status: Optional[str] = None,
        min_orders: int = 2
    ) -> Dict[str, Any]:
        """
        Get rolled options chains from database with optimized queries
        """
        try:
            async for db in get_db():
                # Build base query
                since_time = datetime.now() - timedelta(days=days_back)
                
                conditions = [
                    OptionsOrder.user_id == user_id,
                    OptionsOrder.order_created_at >= since_time,
                    OptionsOrder.chain_id.isnot(None),
                    OptionsOrder.chain_id != "",
                    OptionsOrder.state.notin_(['cancelled', 'canceled', 'rejected', 'failed'])
                ]
                
                if symbol:
                    conditions.append(OptionsOrder.underlying_symbol == symbol.upper())
                
                # Get chain IDs with sufficient orders, separating calls and puts
                chain_count_stmt = select(
                    OptionsOrder.chain_id,
                    OptionsOrder.option_type,
                    func.count(OptionsOrder.id).label('order_count'),
                    OptionsOrder.underlying_symbol
                ).where(
                    and_(*conditions)
                ).group_by(
                    OptionsOrder.chain_id, 
                    OptionsOrder.option_type,
                    OptionsOrder.underlying_symbol
                ).having(
                    func.count(OptionsOrder.id) >= min_orders
                )
                
                chain_result = await db.execute(chain_count_stmt)
                chain_data = chain_result.all()
                
                if not chain_data:
                    return {
                        "success": True,
                        "message": "No rolled options chains found",
                        "data": {
                            "chains": [],
                            "summary": {
                                "total_chains": 0,
                                "total_orders": 0,
                                "total_pnl": 0.0
                            }
                        }
                    }
                
                # Get detailed orders for each chain
                chains = []
                total_orders = 0
                total_pnl = 0.0
                
                for chain_id, option_type, order_count, underlying_symbol in chain_data:
                    orders = await self.get_orders_by_chain_id_and_type(user_id, chain_id, option_type, db)
                    
                    if len(orders) >= min_orders:
                        chain_analysis = await self._analyze_chain(orders)
                        if chain_analysis.get("is_rolled_chain", False):
                            # Try to extract better symbol if current one is UNKNOWN
                            final_symbol = underlying_symbol
                            if not underlying_symbol or underlying_symbol.upper() == "UNKNOWN":
                                final_symbol = self._extract_symbol_from_orders(orders)
                                logger.info(f"Extracted symbol '{final_symbol}' for chain {chain_id}")
                            
                            # Create unique chain identifier combining chain_id and option_type
                            unique_chain_id = f"{chain_id}_{option_type}"
                            
                            chains.append({
                                "chain_id": unique_chain_id,
                                "original_chain_id": chain_id,
                                "option_type": option_type,
                                "underlying_symbol": final_symbol,
                                "order_count": len(orders),
                                **chain_analysis
                            })
                            total_orders += len(orders)
                            total_pnl += chain_analysis.get("total_pnl", 0.0)
                
                # Filter by status if specified
                if status:
                    chains = [c for c in chains if c.get("status", "").lower() == status.lower()]
                
                # Sort chains by latest activity first (most recent first)  
                chains.sort(key=lambda x: x.get("last_activity", ""), reverse=True)
                
                return {
                    "success": True,
                    "message": f"Found {len(chains)} rolled options chains",
                    "data": {
                        "chains": chains,
                        "summary": {
                            "total_chains": len(chains),
                            "total_orders": total_orders,
                            "total_pnl": total_pnl,
                            "avg_orders_per_chain": total_orders / len(chains) if len(chains) > 0 else 0.0
                        }
                    }
                }
                
        except Exception as e:
            logger.error(f"Error getting rolled options chains from DB: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"Database error: {str(e)}",
                "data": None
            }
    
    async def _get_last_sync_time(self, db: AsyncSession, user_id: str) -> Optional[datetime]:
        """Get the timestamp of the most recent order for a user"""
        try:
            stmt = select(func.max(OptionsOrder.order_created_at)).where(
                OptionsOrder.user_id == user_id
            )
            result = await db.execute(stmt)
            return result.scalar()
        except Exception:
            return None
    
    async def _store_orders_with_progress(self, db: AsyncSession, user_id: str, orders: List[Dict[str, Any]]) -> int:
        """Store or update orders in database with progress updates"""
        if not orders:
            return 0
        
        # Process orders in batches for better performance
        batch_size = 50
        stored_count = 0
        total_orders = len(orders)
        
        for i in range(0, len(orders), batch_size):
            batch = orders[i:i + batch_size]
            batch_count = await self._process_order_batch(db, user_id, batch)
            stored_count += batch_count
            
            # Update progress
            progress = min(90, 30 + int((stored_count / total_orders) * 60))  # 30-90% range
            self._update_progress(user_id, {
                "status": "storing",
                "message": f"Stored {stored_count} of {total_orders} orders...",
                "progress": progress,
                "orders_stored": stored_count,
                "total_orders": total_orders
            })
            
            # Commit each batch
            await db.commit()
            
            # Small delay to prevent overwhelming the database
            if len(orders) > batch_size:
                await asyncio.sleep(0.1)
        
        return stored_count
    
    async def _store_orders(self, db: AsyncSession, user_id: str, orders: List[Dict[str, Any]]) -> int:
        """Store or update orders in database using async batch processing (legacy method)"""
        return await self._store_orders_with_progress(db, user_id, orders)
    
    async def _process_order_batch(self, db: AsyncSession, user_id: str, batch: List[Dict[str, Any]]) -> int:
        """Process a batch of orders asynchronously"""
        stored_count = 0
        
        for order_data in batch:
            try:
                # Prepare order record using the correct field names from the model
                order_record = {
                    "user_id": user_id,
                    "order_id": order_data.get("order_id", ""),
                    "chain_id": order_data.get("chain_id", ""),
                    "chain_symbol": order_data.get("chain_symbol", ""),
                    "closing_strategy": order_data.get("closing_strategy"),
                    "opening_strategy": order_data.get("opening_strategy"),
                    "strategy": order_data.get("strategy", ""),
                    "direction": order_data.get("direction", ""),
                    "state": order_data.get("state", ""),
                    "type": order_data.get("type", ""),
                    "processed_quantity": order_data.get("processed_quantity", 0),
                    "premium": order_data.get("premium"),
                    "processed_premium": order_data.get("processed_premium"),
                    "legs_count": order_data.get("legs_count", 0),
                    "legs_details": order_data.get("legs_details", []),
                    # Top-level leg fields (extract from first leg if available)
                    "leg_index": 0 if order_data.get("legs_details") else None,
                    "side": order_data.get("transaction_side"),
                    "position_effect": order_data.get("position_effect"),
                    "option_type": order_data.get("option_type"),
                    "strike_price": order_data.get("strike_price"),
                    "expiration_date": order_data.get("expiration_date"),
                    "created_at": self._parse_datetime(order_data.get("created_at")),
                    "updated_at": self._parse_datetime(order_data.get("updated_at")),
                    "raw_data": order_data
                }
                
                # Use PostgreSQL upsert (ON CONFLICT DO UPDATE)
                insert_stmt = insert(OptionsOrder).values(order_record)
                upsert_stmt = insert_stmt.on_conflict_do_update(
                    index_elements=["order_id"],
                    set_={
                        key: insert_stmt.excluded[key] 
                        for key in order_record.keys() 
                        if key not in ["id", "user_id", "order_id", "db_created_at"]
                    }
                )
                
                await db.execute(upsert_stmt)
                stored_count += 1
                
            except Exception as e:
                logger.error(f"Error storing order {order_data.get('order_id', 'unknown')}: {str(e)}")
                continue
        
        return stored_count
    
    async def _analyze_chain(self, orders: List[OptionsOrder]) -> Dict[str, Any]:
        """Analyze a chain of orders to determine if it's a rolled options chain"""
        # Filter out canceled orders - they weren't executed so not relevant for analysis
        executed_orders = [
            order for order in orders 
            if order.state and order.state.lower() not in ['cancelled', 'canceled', 'rejected', 'failed']
        ]
        
        if len(executed_orders) < 2:
            return {"is_rolled_chain": False}
        
        # Correct roll detection: check if chain has orders from strategy_roll
        
        # Try to find roll orders using form_source (preferred method)
        has_roll_order = any(
            order.raw_data and 
            isinstance(order.raw_data, dict) and 
            order.raw_data.get("form_source") == "strategy_roll" 
            for order in executed_orders
        )
        
        # Fallback: if no form_source available, use opening/closing strategy logic
        if not has_roll_order:
            has_opening_strategy = any(order.opening_strategy for order in executed_orders)
            has_closing_strategy = any(order.closing_strategy for order in executed_orders)
            has_roll_order = has_opening_strategy and has_closing_strategy
        
        if not has_roll_order:
            return {"is_rolled_chain": False}
        
        # Sort executed orders by date (latest first for display)
        sorted_orders = sorted(executed_orders, key=lambda x: x.order_created_at or datetime.min, reverse=True)
        
        # Basic analysis
        total_credits = sum(
            float(order.processed_premium or 0) 
            for order in sorted_orders 
            if order.direction == "credit"
        )
        total_debits = sum(
            float(order.processed_premium or 0) 
            for order in sorted_orders 
            if order.direction == "debit"
        )
        
        net_premium = total_credits - total_debits
        
        # Determine if this looks like a rolled chain
        # Simple heuristic: alternating open/close pattern
        has_closes = any(order.position_effect == "close" for order in sorted_orders)
        has_opens = any(order.position_effect == "open" for order in sorted_orders)
        is_rolled_chain = has_closes and has_opens and len(sorted_orders) >= 2
        
        # Determine status
        last_order = sorted_orders[-1]
        if last_order.position_effect == "close":
            status = "closed"
        elif any(order.state == "cancelled" for order in sorted_orders):
            status = "cancelled"
        else:
            status = "active"
        
        return {
            "is_rolled_chain": is_rolled_chain,
            "status": status,
            "total_credits": total_credits,
            "total_debits": total_debits,
            "net_premium": net_premium,
            "total_pnl": net_premium,  # Simplified P&L calculation
            "start_date": sorted_orders[-1].order_created_at.isoformat() if sorted_orders[-1].order_created_at else None,
            "last_activity": sorted_orders[0].order_created_at.isoformat() if sorted_orders[0].order_created_at else None,
            "orders": [
                {
                    "order_id": order.order_id,
                    "direction": order.direction,
                    "position_effect": order.position_effect,
                    "processed_premium": float(order.processed_premium or 0),
                    "premium": float(order.processed_premium or 0),
                    "price": float(order.processed_premium or 0) / float(order.quantity or 1) if order.quantity else 0,
                    "created_at": order.order_created_at.isoformat() if order.order_created_at else None,
                    "option_type": order.option_type or "unknown",
                    "strike_price": float(order.strike_price or 0),
                    "expiration_date": order.expiration_date or "unknown",
                    "transaction_side": order.transaction_side or "unknown", 
                    "state": order.state or "unknown",
                    "strategy": order.strategy or "unknown",
                    "quantity": float(order.quantity or 0)
                }
                for order in sorted_orders
            ]
        }
    
    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string from Robinhood API"""
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return None
    
    def _extract_symbol_from_orders(self, orders: List[OptionsOrder]) -> str:
        """Extract underlying symbol from options orders with fallback logic"""
        # Try to find symbol from any order
        for order in orders:
            # Try chain_symbol first
            if hasattr(order, 'chain_symbol') and order.chain_symbol:
                symbol = order.chain_symbol.strip()
                if symbol and symbol.upper() != "UNKNOWN":
                    return symbol.upper()
            
            # Try underlying_symbol
            if hasattr(order, 'underlying_symbol') and order.underlying_symbol:
                symbol = order.underlying_symbol.strip()
                if symbol and symbol.upper() != "UNKNOWN":
                    return symbol.upper()
            
            # Try to extract from option chain details if available
            if hasattr(order, 'option_type') and hasattr(order, 'strike_price'):
                # If we have option details but no symbol, we can't infer the symbol
                # This would require parsing instrument URLs or other fields
                pass
        
        return "UNKNOWN"
    
    async def _create_demo_data(self, user_id: str, days_back: int) -> Dict[str, Any]:
        """Create demo rolled options data for testing when Robinhood API is not available"""
        try:
            async for db in get_db():
                # First ensure user exists in the users table
                from app.models.user import User
                from sqlalchemy.dialects.postgresql import insert
                
                user_record = {
                    "id": user_id,
                    "full_name": "Demo User",
                    "email": f"demo-{user_id}@example.com",  # Unique email per user
                    "is_active": True
                }
                
                insert_user_stmt = insert(User).values(user_record)
                upsert_user_stmt = insert_user_stmt.on_conflict_do_nothing(index_elements=["id"])
                await db.execute(upsert_user_stmt)
                
                # Create sample rolled options chains
                demo_chains = [
                    {
                        "chain_id": "demo-chain-1",
                        "underlying_symbol": "AAPL",
                        "orders": [
                            {
                                "order_id": "demo-order-1",
                                "direction": "credit",
                                "position_effect": "open", 
                                "processed_premium": 150.0,
                                "quantity": 1.0,
                                "created_at": (datetime.now() - timedelta(days=10))
                            },
                            {
                                "order_id": "demo-order-2", 
                                "direction": "debit",
                                "position_effect": "close",
                                "processed_premium": 75.0,
                                "quantity": 1.0,
                                "created_at": (datetime.now() - timedelta(days=5))
                            },
                            {
                                "order_id": "demo-order-3",
                                "direction": "credit", 
                                "position_effect": "open",
                                "processed_premium": 200.0,
                                "quantity": 1.0,
                                "created_at": (datetime.now() - timedelta(days=3))
                            }
                        ]
                    },
                    {
                        "chain_id": "demo-chain-2",
                        "underlying_symbol": "TSLA", 
                        "orders": [
                            {
                                "order_id": "demo-order-4",
                                "direction": "credit",
                                "position_effect": "open",
                                "processed_premium": 300.0,
                                "quantity": 2.0,
                                "created_at": (datetime.now() - timedelta(days=15))
                            },
                            {
                                "order_id": "demo-order-5",
                                "direction": "debit",
                                "position_effect": "close", 
                                "processed_premium": 100.0,
                                "quantity": 2.0,
                                "created_at": (datetime.now() - timedelta(days=8))
                            }
                        ]
                    }
                ]
                
                # Store demo orders in database
                stored_count = 0
                for chain in demo_chains:
                    for order in chain["orders"]:
                        order_record = {
                            "user_id": user_id,
                            "order_id": order["order_id"],
                            "chain_id": chain["chain_id"],
                            "chain_symbol": chain["underlying_symbol"],
                            "underlying_symbol": chain["underlying_symbol"],
                            "direction": order["direction"],
                            "position_effect": order["position_effect"],
                            "processed_premium": order["processed_premium"],
                            "quantity": order["quantity"],
                            "state": "filled",
                            "type": "limit",
                            "strategy": "DEMO",
                            "legs_count": 1,
                            "executions_count": 1,
                            "option_type": "call",
                            "strike_price": 150.0,
                            "expiration_date": "2024-12-20",
                            "transaction_side": "sell" if order["direction"] == "credit" else "buy",
                            "order_created_at": order["created_at"],
                            "order_updated_at": order["created_at"],
                            "raw_data": {"demo": True}
                        }
                        
                        # Use PostgreSQL upsert
                        insert_stmt = insert(OptionsOrder).values(order_record)
                        upsert_stmt = insert_stmt.on_conflict_do_update(
                            index_elements=["order_id"],
                            set_={
                                key: insert_stmt.excluded[key] 
                                for key in order_record.keys() 
                                if key not in ["id", "user_id", "order_id", "created_at"]
                            }
                        )
                        await db.execute(upsert_stmt)
                        stored_count += 1
                
                await db.commit()
                
                logger.info(f"Created {stored_count} demo orders for user {user_id}")
                
                return {
                    "success": True,
                    "message": f"Created demo data with {stored_count} orders",
                    "data": {
                        "orders_processed": stored_count,
                        "orders_stored": stored_count,
                        "sync_time": datetime.now().isoformat(),
                        "demo_mode": True
                    }
                }
                
        except Exception as e:
            logger.error(f"Error creating demo data: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"Demo data creation error: {str(e)}",
                "data": None
            }
    
    async def get_user_orders(
        self,
        user_id: UUID,
        page: int = 1,
        limit: int = 50,
        symbol: Optional[str] = None,
        state: Optional[str] = None,
        strategy: Optional[str] = None,
        option_type: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """
        Get paginated options orders for a user from database
        
        Args:
            user_id: User UUID
            page: Page number (1-based)
            limit: Orders per page
            symbol: Filter by underlying symbol
            state: Filter by order state
            strategy: Filter by strategy
            sort_by: Field to sort by
            sort_order: 'asc' or 'desc'
        """
        try:
            async for db in get_db():
                # Build base query conditions
                conditions = [OptionsOrder.user_id == str(user_id)]
                
                # Add filters
                if symbol:
                    conditions.append(OptionsOrder.chain_symbol == symbol.upper())
                if state:
                    conditions.append(OptionsOrder.state == state)
                if strategy:
                    conditions.append(OptionsOrder.strategy.ilike(f"%{strategy}%"))
                if option_type:
                    # DB stores lower-case 'call'/'put'
                    conditions.append(OptionsOrder.option_type == option_type.lower())
                
                # Build base query
                base_query = select(OptionsOrder).where(and_(*conditions))
                
                # Add sorting
                allowed_sorts = {
                    "created_at": OptionsOrder.created_at,
                    "updated_at": OptionsOrder.updated_at,
                    "processed_premium": OptionsOrder.processed_premium,
                    "premium": OptionsOrder.premium,
                    "strike_price": OptionsOrder.strike_price,
                    "expiration_date": OptionsOrder.expiration_date,
                    "chain_symbol": OptionsOrder.chain_symbol,
                    "state": OptionsOrder.state,
                }
                sort_column = allowed_sorts.get(sort_by, OptionsOrder.created_at)
                if sort_order.lower() == "desc":
                    base_query = base_query.order_by(desc(sort_column))
                else:
                    base_query = base_query.order_by(asc(sort_column))
                
                # Get total count
                count_query = select(func.count()).select_from(
                    select(OptionsOrder.id).where(and_(*conditions)).subquery()
                )
                total_result = await db.execute(count_query)
                total_count = total_result.scalar() or 0
                
                # Apply pagination
                offset = (page - 1) * limit
                paginated_query = base_query.offset(offset).limit(limit)
                
                # Execute query
                result = await db.execute(paginated_query)
                orders = result.scalars().all()
                
                # Convert to dict format
                orders_data = []
                for order in orders:
                    order_dict = {
                        "order_id": order.order_id,
                        "chain_symbol": order.chain_symbol,
                        "underlying_symbol": order.chain_symbol,  # Use chain_symbol as underlying
                        "state": order.state,
                        "strategy": order.strategy,
                        "direction": order.direction,
                        "processed_premium": float(order.processed_premium or 0),
                        "premium": float(order.premium or 0),
                        # Quantity fields
                        "processed_quantity": float(order.processed_quantity or 0),
                        "quantity": float(order.processed_quantity or 0),
                        "legs_count": order.legs_count or 0,
                        "created_at": order.created_at.isoformat() if order.created_at else None,
                        "updated_at": order.updated_at.isoformat() if order.updated_at else None,
                        "option_type": order.option_type,
                        "strike_price": float(order.strike_price or 0),
                        "expiration_date": order.expiration_date,
                        # Include both for compatibility with UI
                        "transaction_side": order.side,
                        "side": order.side,
                        "position_effect": order.position_effect,
                        "type": order.type,
                        "legs_details": order.legs_details or []
                    }
                    orders_data.append(order_dict)
                
                # Calculate pagination info
                total_pages = (total_count + limit - 1) // limit
                has_next = page < total_pages
                has_prev = page > 1
                
                return {
                    "success": True,
                    "data": orders_data,
                    "pagination": {
                        "page": page,
                        "limit": limit,
                        "total": total_count,
                        "total_pages": total_pages,
                        "has_next": has_next,
                        "has_prev": has_prev
                    },
                    "filters_applied": {
                        "symbol": symbol,
                        "state": state,
                        "strategy": strategy,
                        "option_type": option_type,
                        "sort_by": sort_by,
                        "sort_order": sort_order
                    }
                }
                
        except Exception as e:
            logger.error(f"Error getting user orders: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": str(e),
                "data": []
            }
    
    async def get_sync_status(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get sync status for a user
        
        Args:
            user_id: User UUID
        """
        try:
            async for db in get_db():
                # Get order count and last sync time
                stmt = select(
                    func.count(OptionsOrder.id).label("total_orders"),
                    func.max(OptionsOrder.created_at).label("last_sync"),
                    func.max(OptionsOrder.created_at).label("last_order_date")
                ).where(OptionsOrder.user_id == str(user_id))
                
                result = await db.execute(stmt)
                stats = result.first()
                
                # Check if sync is needed (no orders or old data)
                needs_sync = False
                if not stats.total_orders:
                    needs_sync = True
                    sync_reason = "No orders found - full sync needed"
                elif stats.last_sync and stats.last_sync < datetime.now(timezone.utc) - timedelta(hours=1):
                    needs_sync = True
                    sync_reason = "Data is stale - incremental sync recommended"
                else:
                    sync_reason = "Data is current"
                
                return {
                    "success": True,
                    "data": {
                        "user_id": str(user_id),
                        "total_orders": stats.total_orders or 0,
                        "last_sync": stats.last_sync.isoformat() if stats.last_sync else None,
                        "last_order_date": stats.last_order_date.isoformat() if stats.last_order_date else None,
                        "needs_sync": needs_sync,
                        "sync_reason": sync_reason,
                        "sync_status": "up_to_date" if not needs_sync else "sync_needed"
                    }
                }
                
        except Exception as e:
            logger.error(f"Error getting sync status: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": str(e),
                "data": {}
            }
    
    async def get_orders_for_chain_detection(
        self,
        user_id: str,
        days_back: Optional[int] = 365,
        symbol: Optional[str] = None
    ) -> List[OptionsOrder]:
        """
        Get options orders optimized for chain detection.
        
        Returns only filled orders with proper indexing for strategy code grouping
        and heuristic analysis.
        
        Args:
            user_id: User ID to get orders for
            days_back: Number of days to look back
            symbol: Optional symbol filter
            
        Returns:
            List of OptionsOrder objects sorted by creation time
        """
        try:
            async for db in get_db():
                # Build query conditions
                conditions = [
                    OptionsOrder.user_id == user_id,
                    OptionsOrder.state == "filled"  # Only filled orders for chain detection
                ]
                
                # Apply lookback window only when days_back is provided and > 0
                if days_back is not None and days_back > 0:
                    since_time = datetime.now() - timedelta(days=days_back)
                    conditions.append(OptionsOrder.created_at >= since_time)
                
                if symbol:
                    conditions.append(OptionsOrder.chain_symbol == symbol.upper())
                
                # Query with optimized indexes
                stmt = select(OptionsOrder).where(
                    and_(*conditions)
                ).order_by(OptionsOrder.created_at.asc())  # Chronological order for chain analysis
                
                result = await db.execute(stmt)
                orders = result.scalars().all()
                
                logger.info(f"Retrieved {len(orders)} filled orders for chain detection (user: {user_id}, days: {days_back})")
                return orders
                
        except Exception as e:
            logger.error(f"Error getting orders for chain detection: {str(e)}", exc_info=True)
            return []
