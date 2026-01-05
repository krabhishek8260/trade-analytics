"""
Rolled Options Background Processing Service

This service handles the background processing of rolled options chains
for all users. It runs as a cron job to:

1. Identify users needing processing (new users or incremental updates)
2. Load and analyze their options orders
3. Detect rolled options chains using precise algorithms
4. Store pre-computed results in the database
5. Update sync status and schedule next processing

Key Features:
- Incremental processing (only new orders since last sync)
- Error handling and retry logic
- Performance monitoring and logging
- Graceful handling of large datasets
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_, text
from sqlalchemy.dialects.postgresql import insert
import uuid

from app.core.database import get_db
from app.models.user import User
from app.models.options_order import OptionsOrder
from app.models.rolled_options_chain import RolledOptionsChain, UserRolledOptionsSync
from app.services.rolled_options_chain_detector import RolledOptionsChainDetector
from app.services.json_rolled_options_service import JsonRolledOptionsService
from app.core.redis import cache

logger = logging.getLogger(__name__)


class RolledOptionsCronService:
    """Background service for processing rolled options chains"""
    
    def __init__(self):
        # Initialize services for chain detection
        from app.services.robinhood_service import RobinhoodService
        from app.services.options_order_service import OptionsOrderService
        
        rh_service = RobinhoodService()
        options_service = OptionsOrderService(rh_service)
        self.options_service = options_service  # keep reference to run order syncs
        self.chain_detector = RolledOptionsChainDetector(options_service)
        self.json_service = JsonRolledOptionsService()
        self.processing_timeout = 300  # 5 minutes per user
        self.max_retries = 3
        
    async def process_all_users(self) -> Dict[str, Any]:
        """
        Main entry point for cron job - process all users needing updates
        
        Returns:
            Summary of processing results
        """
        start_time = datetime.now()
        logger.info("Starting rolled options background processing for all users")
        
        try:
            # Get users needing processing
            users_to_process = await self._get_users_needing_processing()
            logger.info(f"Found {len(users_to_process)} users needing rolled options processing")
            
            if not users_to_process:
                return {
                    'success': True,
                    'message': 'No users need processing',
                    'users_processed': 0,
                    'total_chains': 0,
                    'processing_time': 0
                }
            
            # Process each user
            total_chains = 0
            users_processed = 0
            errors = []
            
            for user_info in users_to_process:
                try:
                    user_id = str(user_info['user_id'])
                    logger.info(f"Processing rolled options for user {user_id}")
                    
                    # Update status to processing
                    await self._update_sync_status(user_id, 'processing')
                    
                    # Process user with timeout
                    result = await asyncio.wait_for(
                        self._process_user_rolled_options(user_info),
                        timeout=self.processing_timeout
                    )
                    
                    if result['success']:
                        users_processed += 1
                        total_chains += result.get('chains_processed', 0)
                        logger.info(f"Successfully processed user {user_id}: {result.get('chains_processed', 0)} chains")
                    else:
                        errors.append(f"User {user_id}: {result.get('message', 'Unknown error')}")
                        
                except asyncio.TimeoutError:
                    error_msg = f"Processing timeout for user {user_info['user_id']}"
                    logger.error(error_msg)
                    await self._update_sync_status(str(user_info['user_id']), 'error', error_msg)
                    errors.append(error_msg)
                    
                except Exception as e:
                    error_msg = f"Error processing user {user_info['user_id']}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    await self._update_sync_status(str(user_info['user_id']), 'error', error_msg)
                    errors.append(error_msg)
            
            # Refresh materialized view
            await self._refresh_materialized_view()
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                'success': True,
                'message': f'Processed {users_processed}/{len(users_to_process)} users successfully',
                'users_processed': users_processed,
                'total_chains': total_chains,
                'processing_time': processing_time,
                'errors': errors[:10]  # Limit error messages
            }
            
        except Exception as e:
            logger.error(f"Error in process_all_users: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'Background processing failed: {str(e)}',
                'users_processed': 0,
                'total_chains': 0,
                'processing_time': (datetime.now() - start_time).total_seconds()
            }
    
    async def _get_users_needing_processing(self) -> List[Dict[str, Any]]:
        """Get list of users who need rolled options processing"""
        
        async for db in get_db():
            try:
                # Call the database function to get users needing processing
                result = await db.execute(
                    select(func.get_users_needing_rolled_options_processing())
                )
                
                users = []
                for row in result:
                    if row[0]:  # row[0] contains the function result
                        user_data = row[0]
                        users.append({
                            'user_id': user_data[0],
                            'last_processed_at': user_data[1],
                            'processing_status': user_data[2],
                            'full_sync_required': user_data[3]
                        })
                
                return users
                
            except Exception as e:
                logger.error(f"Error getting users needing processing: {e}")
                return []
    
    async def _process_user_rolled_options(self, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process rolled options for a single user
        
        Args:
            user_info: User information from _get_users_needing_processing
            
        Returns:
            Processing result summary
        """
        user_id = str(user_info['user_id'])
        full_sync = user_info.get('full_sync_required', True)
        
        try:
            # Ensure the user exists in the DB to satisfy FK constraints when storing chains
            async for db in get_db():
                try:
                    user_uuid = uuid.UUID(user_id)
                    user_exists = await db.execute(
                        select(User).where(User.id == user_uuid)
                    )
                    if not user_exists.scalar_one_or_none():
                        # Create a minimal user record
                        from sqlalchemy.dialects.postgresql import insert as pg_insert
                        dummy_email = f"user_{user_id[:8]}@tradeanalytics.local"
                        dummy_name = "TradeAnalytics User"
                        insert_stmt = pg_insert(User).values(
                            id=user_uuid,
                            email=dummy_email,
                            full_name=dummy_name,
                            is_active=True,
                            robinhood_username=None,
                            robinhood_user_id=None
                        ).on_conflict_do_nothing(index_elements=[User.id])
                        await db.execute(insert_stmt)
                        await db.commit()
                        logger.info(f"Ensured user exists for rolled options processing: {user_id}")
                except Exception as e:
                    logger.warning(f"Could not ensure user exists ({user_id}): {e}")
                finally:
                    break

            # Determine date range for processing
            if full_sync:
                # Full sync - process full history
                days_back = None
                logger.info(f"Full sync for user {user_id} - processing full history")
            else:
                # Incremental sync - rely on DB delta, no explicit lookback cutoff
                days_back = None
                logger.info(f"Incremental sync for user {user_id} - processing since last update")
            
            # Load orders data
            orders_data = await self._load_user_orders(user_id, days_back)
            logger.info(f"Loaded {len(orders_data)} orders for user {user_id}")
            
            if not orders_data:
                await self._update_sync_status(
                    user_id, 'completed', 
                    total_chains=0, active_chains=0, closed_chains=0, orders_processed=0
                )
                return {
                    'success': True,
                    'message': 'No orders found for processing',
                    'chains_processed': 0
                }
            
            # Use RolledOptionsChainDetector (database-first + heuristics) to detect chains
            # Detect across full DB history
            detection_days = None
            chains = await self.chain_detector.detect_chains_from_database(
                user_id=user_id,
                days_back=None,
                symbol=None
            )
            logger.info(f"🔍 Detector returned {len(chains)} chains for user {user_id}")
            
            # Count enhanced chains (those starting with single-leg opening orders)
            enhanced_chain_count = 0
            for chain in chains:
                chain_orders = chain.get('orders', [])
                if chain_orders:
                    first_order = chain_orders[0]
                    legs = first_order.get('legs', [])
                    if len(legs) == 1 and (legs[0] or {}).get('position_effect') == 'open':
                        enhanced_chain_count += 1
            
            logger.info(f"🎉 Found {enhanced_chain_count} enhanced chains starting with single-leg opening orders")
            
            # Analyze and store chains
            chains_stored = 0
            active_chains = 0
            closed_chains = 0
            
            async for db in get_db():
                try:
                    # Clear existing chains for full sync
                    if full_sync:
                        await db.execute(
                            delete(RolledOptionsChain).where(
                                RolledOptionsChain.user_id == user_id
                            )
                        )
                        await db.commit()
                        logger.info(f"Cleared existing chains for user {user_id} (full sync)")
                    
                    # Process each detected chain with individual error handling
                    for i, chain_data in enumerate(chains):
                        try:
                            chain_orders = chain_data.get('orders', [])
                            logger.debug(f"Processing chain {i+1}/{len(chains)} with {len(chain_orders)} orders")
                            
                            # Normalize into full analysis for storage
                            chain_analysis = self.chain_detector.get_chain_analysis(chain_orders)
                            
                            if chain_analysis and chain_analysis.get('chain_id'):
                                logger.info(f"Chain {i+1}/{len(chains)}: {chain_analysis.get('chain_id')} - {len(chain_orders)} orders")
                                
                                # Store chain in database (has its own error handling)
                                await self._store_chain(db, user_id, chain_analysis)
                                chains_stored += 1
                                
                                # Count by status
                                status = chain_analysis.get('status', 'active')
                                if status == 'active':
                                    active_chains += 1
                                elif status == 'closed':
                                    closed_chains += 1
                                    
                            else:
                                logger.warning(f"Chain {i+1} analysis failed or returned invalid data: analysis={bool(chain_analysis)}")
                                if chain_analysis:
                                    logger.debug(f"Chain analysis keys: {list(chain_analysis.keys())}")
                                    
                        except Exception as e:
                            logger.error(f"Error processing chain {i+1} for user {user_id}: {e}", exc_info=True)
                            # Continue processing other chains
                            continue
                    
                    await db.commit()
                    
                    # Update sync status
                    await self._update_sync_status(
                        user_id, 'completed',
                        total_chains=chains_stored,
                        active_chains=active_chains,
                        closed_chains=closed_chains,
                        orders_processed=len(orders_data)
                    )
                    
                    # Expire Redis caches so UI reflects fresh chains immediately
                    try:
                        cleared = await cache.clear_pattern("rolled_options:*")
                        logger.info(f"Cleared {cleared} rolled_options* Redis keys after processing user {user_id}")
                    except Exception as e:
                        logger.warning(f"Could not clear rolled_options Redis cache: {e}")
                    
                    logger.info(f"Successfully stored {chains_stored} chains for user {user_id}")
                    
                    return {
                        'success': True,
                        'message': f'Processed {chains_stored} chains',
                        'chains_processed': chains_stored,
                        'active_chains': active_chains,
                        'closed_chains': closed_chains
                    }
                    
                except Exception as e:
                    await db.rollback()
                    raise e
            
        except Exception as e:
            logger.error(f"Error processing user {user_id}: {str(e)}", exc_info=True)
            await self._update_sync_status(user_id, 'error', str(e))
            return {
                'success': False,
                'message': str(e),
                'chains_processed': 0
            }
    
    async def _load_user_orders(self, user_id: str, days_back: Optional[int]) -> List[Dict[str, Any]]:
        """
        Load orders for chain detection - uses database as primary data source
        """
        try:
            # Primary: Load from database (production)
            logger.info(f"🔍 Loading orders from database for enhanced detection (user: {user_id}, days_back: {days_back})")
            
            # For enhanced detection, load with extended lookback to find historical opening orders
            extended_days_back = None  # always full history from DB for enhanced detection
            
            database_orders = await self._load_orders_from_database(user_id, extended_days_back)
            if database_orders:
                logger.info(f"🔍 Loaded {len(database_orders)} orders from database for enhanced detection")
                return database_orders
            
            # Fallback 1: Try debug files (development/testing)
            logger.warning("No orders found in database, trying debug files as fallback")
            debug_orders = await self._load_orders_from_debug_files()
            if debug_orders:
                logger.info(f"🔍 Loaded {len(debug_orders)} orders from debug files for enhanced detection")
                return debug_orders
            
            # Fallback 2: Load from JSON service (API)
            logger.warning("No orders in debug files, falling back to API loading")
            logger.info(f"🔍 Loading orders from API with extended lookback ({extended_days_back} days)")
            result = await self.json_service._load_raw_orders(extended_days_back)
            
            if result.get('success') and result.get('orders'):
                orders = result['orders']
                logger.info(f"Loaded {len(orders)} raw orders from API for enhanced detection")
                
                # Filter for filled options orders only
                options_orders = [
                    order for order in orders
                    if (order.get('legs') and len(order.get('legs', [])) > 0 and
                        order.get('state', '').lower() == 'filled')
                ]
                
                logger.info(f"Filtered to {len(options_orders)} filled options orders from API")
                return options_orders
            
            # Final fallback with shorter timeframe
            logger.warning("Extended API loading failed, falling back to regular API loading")
            result = await self.json_service._load_raw_orders(days_back)
            
            if result.get('success') and result.get('orders'):
                orders = result['orders']
                options_orders = [
                    order for order in orders
                    if (order.get('legs') and len(order.get('legs', [])) > 0 and
                        order.get('state', '').lower() == 'filled')
                ]
                return options_orders
            
            return []
            
        except Exception as e:
            logger.error(f"Error loading orders for user {user_id}: {e}")
            return []

    async def _load_orders_from_database(self, user_id: str, days_back: Optional[int]) -> List[Dict[str, Any]]:
        """
        Load orders from the database options_orders table
        """
        try:
            async for db in get_db():
                # Calculate cutoff date
                from datetime import datetime, timedelta
                cutoff_date = datetime.now() - timedelta(days=days_back)
                
                # Query filled options orders from the database
                base_sql = '''
                    SELECT 
                        order_id,
                        chain_symbol,
                        strike_price,
                        expiration_date,
                        option_type,
                        state,
                        created_at,
                        updated_at,
                        position_effect,
                        processed_premium,
                        direction,
                        legs_count,
                        legs_details,
                        strategy,
                        opening_strategy,
                        closing_strategy
                    FROM options_orders 
                    WHERE user_id = :user_id
                    AND state = 'filled'
                    AND legs_count > 0
                '''
                params = {'user_id': user_id}
                if days_back is not None and days_back > 0:
                    base_sql += " AND created_at >= :cutoff_date"
                    from datetime import datetime, timedelta
                    params['cutoff_date'] = datetime.now() - timedelta(days=days_back)
                base_sql += " ORDER BY created_at DESC"
                result = await db.execute(text(base_sql), params)
                
                db_orders = result.fetchall()
                logger.info(f"Found {len(db_orders)} filled options orders in database for user {user_id}")
                
                # Convert database orders to the expected format for chain detection
                converted_orders = []
                
                for db_order in db_orders:
                    # Convert to the format expected by chain detector
                    order_dict = {
                        'id': db_order.order_id,
                        'state': db_order.state,
                        'created_at': db_order.created_at.isoformat() if db_order.created_at else None,
                        'updated_at': db_order.updated_at.isoformat() if db_order.updated_at else None,
                        'direction': db_order.direction,
                        'premium': float(db_order.processed_premium or 0),
                        'processed_premium': float(db_order.processed_premium or 0),
                        'strategy': db_order.strategy,
                        'opening_strategy': db_order.opening_strategy,
                        'closing_strategy': db_order.closing_strategy,
                        # Helpful fields for detector grouping/validation
                        'chain_symbol': db_order.chain_symbol,
                        'underlying_symbol': db_order.chain_symbol,
                        'processed_quantity': float(getattr(db_order, 'processed_quantity', 0) or 0),
                        'legs': []
                    }
                    
                    # Convert legs_details from database format
                    if db_order.legs_details:
                        legs = db_order.legs_details if isinstance(db_order.legs_details, list) else []
                        for leg in legs:
                            # Provide per-leg fields directly for detector logic
                            strike = leg.get('strike_price', None)
                            try:
                                strike_val = float(strike) if strike is not None else None
                            except Exception:
                                strike_val = None
                            leg_dict = {
                                'id': leg.get('id'),
                                'side': leg.get('side'),
                                'position_effect': leg.get('position_effect'),
                                'option_type': leg.get('option_type') or (db_order.option_type if db_order.option_type else None),
                                'strike_price': strike_val if strike_val is not None else (float(db_order.strike_price) if db_order.strike_price is not None else None),
                                'expiration_date': leg.get('expiration_date') or (str(db_order.expiration_date) if db_order.expiration_date else None),
                                'long_strategy_code': leg.get('long_strategy_code'),
                                'short_strategy_code': leg.get('short_strategy_code')
                            }
                            order_dict['legs'].append(leg_dict)
                    
                    # Only include orders with legs (options orders)
                    if order_dict['legs']:
                        converted_orders.append(order_dict)
                
                logger.info(f"Converted {len(converted_orders)} database orders to chain detection format")
                return converted_orders
                
        except Exception as e:
            logger.error(f"Error loading orders from database for user {user_id}: {e}")
            return []

    async def _load_orders_from_debug_files(self) -> List[Dict[str, Any]]:
        """
        Load orders from debug data files (development only)
        """
        import json
        from pathlib import Path
        
        try:
            debug_data_dir = Path(__file__).parent.parent.parent / "debug_data"
            options_files = list(debug_data_dir.glob("*options_orders*.json"))
            
            if not options_files:
                return []
            
            all_orders = []
            
            # Load from 5 most recent files
            for file_path in sorted(options_files, reverse=True)[:5]:
                try:
                    with open(file_path, 'r') as f:
                        orders = json.load(f)
                        
                    # Filter for filled orders only
                    filled_orders = [
                        order for order in orders 
                        if order.get('state') == 'filled'
                    ]
                    
                    all_orders.extend(filled_orders)
                            
                except Exception as e:
                    logger.error(f"Error loading {file_path}: {e}")
                    continue
            
            # Remove duplicates
            seen_ids = set()
            unique_orders = []
            for order in all_orders:
                order_id = order.get('id')
                if order_id and order_id not in seen_ids:
                    seen_ids.add(order_id)
                    unique_orders.append(order)
            
            return unique_orders
            
        except Exception as e:
            logger.error(f"Error loading from debug files: {e}")
            return []
    
    async def _store_chain(
        self, 
        db: AsyncSession, 
        user_id: str, 
        chain_analysis: Dict[str, Any]
    ) -> None:
        """Store a detected chain in the database with individual transaction handling"""
        
        try:
            # Validate required fields first
            chain_id = chain_analysis.get('chain_id', '')
            if not chain_id:
                logger.error(f"Chain missing chain_id: {chain_analysis}")
                return
            
            underlying_symbol = chain_analysis.get('underlying_symbol', '')
            if not underlying_symbol:
                logger.error(f"Chain missing underlying_symbol: {chain_analysis}")
                return
            
            # Ensure numeric fields are valid
            total_orders = max(0, int(chain_analysis.get('total_orders', 0)))
            roll_count = max(0, int(chain_analysis.get('roll_count', 0)))
            total_credits = float(chain_analysis.get('total_credits_collected', 0.0))
            total_debits = float(chain_analysis.get('total_debits_paid', 0.0))
            net_premium = float(chain_analysis.get('net_premium', 0.0))
            total_pnl = float(chain_analysis.get('total_pnl', 0.0))
            
            # Validate status
            status = chain_analysis.get('status', 'active')
            if status not in ['active', 'closed', 'expired']:
                status = 'active'
            
            # Parse dates safely
            start_date = self._parse_datetime(chain_analysis.get('start_date'))
            last_activity_date = self._parse_datetime(chain_analysis.get('last_activity_date'))
            
            # Check if this is an enhanced chain (starts with single-leg opening order)
            orders = chain_analysis.get('orders', [])
            is_enhanced = False
            if orders and len(orders) > 0:
                first_order = orders[0]
                legs = first_order.get('legs', [])
                if len(legs) == 1 and legs[0].get('position_effect') == 'open':
                    is_enhanced = True
            
            # Prepare chain data with clean structure
            clean_chain_data = {
                'chain_id': chain_id,
                'underlying_symbol': underlying_symbol,
                'chain_type': chain_analysis.get('chain_type', 'unknown'),
                'status': status,
                'total_orders': total_orders,
                'roll_count': roll_count,
                'orders': orders,
                'enhanced': is_enhanced,  # Mark enhanced chains
                'latest_position': chain_analysis.get('latest_position')
            }
            
            # Summary metrics
            summary_metrics = {
                'chain_type': chain_analysis.get('chain_type', 'unknown'),
                'orders_count': total_orders,
                'net_premium': net_premium,
                'status': status
            }
            
            enhanced_flag = "🎉 ENHANCED" if is_enhanced else ""
            logger.info(f"Storing chain {chain_id} for user {user_id}: {total_orders} orders, status={status} {enhanced_flag}")
            
            # Use individual transaction for this chain
            async with db.begin_nested() as nested_txn:
                try:
                    # Use upsert to handle duplicates
                    stmt = insert(RolledOptionsChain).values(
                        user_id=user_id,
                        chain_id=chain_id,
                        underlying_symbol=underlying_symbol,
                        status=status,
                        initial_strategy=chain_analysis.get('initial_strategy'),
                        start_date=start_date,
                        last_activity_date=last_activity_date,
                        total_orders=total_orders,
                        roll_count=roll_count,
                        total_credits_collected=total_credits,
                        total_debits_paid=total_debits,
                        net_premium=net_premium,
                        total_pnl=total_pnl,
                        chain_data=clean_chain_data,
                        summary_metrics=summary_metrics,
                        processed_at=datetime.now()
                    )
                    
                    # On conflict, update the record using column names instead of constraint name
                    upsert_stmt = stmt.on_conflict_do_update(
                        index_elements=['user_id', 'chain_id'],  # Use column names instead of constraint
                        set_=dict(
                            status=stmt.excluded.status,
                            initial_strategy=stmt.excluded.initial_strategy,
                            last_activity_date=stmt.excluded.last_activity_date,
                            total_orders=stmt.excluded.total_orders,
                            roll_count=stmt.excluded.roll_count,
                            total_credits_collected=stmt.excluded.total_credits_collected,
                            total_debits_paid=stmt.excluded.total_debits_paid,
                            net_premium=stmt.excluded.net_premium,
                            total_pnl=stmt.excluded.total_pnl,
                            chain_data=stmt.excluded.chain_data,
                            summary_metrics=stmt.excluded.summary_metrics,
                            processed_at=stmt.excluded.processed_at,
                            updated_at=func.now()
                        )
                    )
                    
                    await db.execute(upsert_stmt)
                    await nested_txn.commit()
                    
                    logger.debug(f"Successfully stored chain {chain_id}")
                    
                except Exception as nested_e:
                    logger.error(f"Error in nested transaction for chain {chain_id}: {nested_e}")
                    await nested_txn.rollback()
                    raise
            
        except Exception as e:
            logger.error(f"Error storing chain {chain_analysis.get('chain_id', 'unknown')}: {e}")
            # Don't re-raise to prevent aborting the entire batch
            return
    
    async def _update_sync_status(
        self,
        user_id: str,
        status: str,
        error_message: Optional[str] = None,
        total_chains: Optional[int] = None,
        active_chains: Optional[int] = None,
        closed_chains: Optional[int] = None,
        orders_processed: Optional[int] = None
    ) -> None:
        """Update sync status for a user"""
        
        async for db in get_db():
            try:
                # Calculate next sync time
                next_sync = None
                if status == 'completed':
                    next_sync = datetime.now() + timedelta(minutes=30)  # Sync every 30 minutes
                
                # Use the database function for status updates
                await db.execute(
                    text("SELECT update_user_rolled_options_sync_status(:user_id, :status, :error_msg, :total_chains, :active_chains, :closed_chains, :orders_processed)"),
                    {
                        "user_id": user_id,
                        "status": status,
                        "error_msg": error_message,
                        "total_chains": total_chains,
                        "active_chains": active_chains,
                        "closed_chains": closed_chains,
                        "orders_processed": orders_processed
                    }
                )
                
                await db.commit()
                
            except Exception as e:
                logger.error(f"Error updating sync status for user {user_id}: {e}")
                await db.rollback()
    
    async def _refresh_materialized_view(self) -> None:
        """Refresh the rolled options summary materialized view"""
        
        async for db in get_db():
            try:
                await db.execute(select(func.refresh_rolled_options_summary()))
                await db.commit()
                logger.info("Refreshed rolled_options_summary materialized view")
                
            except Exception as e:
                logger.error(f"Error refreshing materialized view: {e}")
                await db.rollback()
    
    async def get_processing_status(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get processing status for a user or all users"""
        
        async for db in get_db():
            try:
                if user_id:
                    # Get status for specific user
                    result = await db.execute(
                        select(UserRolledOptionsSync).where(
                            UserRolledOptionsSync.user_id == user_id
                        )
                    )
                    sync_record = result.scalar_one_or_none()
                    
                    if sync_record:
                        return sync_record.processing_summary
                    else:
                        return {
                            'status': 'pending',
                            'message': 'User not yet processed'
                        }
                else:
                    # Get summary for all users
                    result = await db.execute(
                        select(
                            func.count(UserRolledOptionsSync.user_id).label('total_users'),
                            func.count().filter(UserRolledOptionsSync.processing_status == 'completed').label('completed'),
                            func.count().filter(UserRolledOptionsSync.processing_status == 'processing').label('processing'),
                            func.count().filter(UserRolledOptionsSync.processing_status == 'error').label('errors'),
                            func.count().filter(UserRolledOptionsSync.processing_status == 'pending').label('pending'),
                            func.sum(UserRolledOptionsSync.total_chains).label('total_chains'),
                            func.max(UserRolledOptionsSync.last_successful_sync).label('last_sync')
                        )
                    )
                    
                    summary = result.first()
                    return {
                        'total_users': summary.total_users or 0,
                        'completed': summary.completed or 0,
                        'processing': summary.processing or 0,
                        'errors': summary.errors or 0,
                        'pending': summary.pending or 0,
                        'total_chains': float(summary.total_chains or 0),
                        'last_sync': summary.last_sync.isoformat() if summary.last_sync else None
                    }
                    
            except Exception as e:
                logger.error(f"Error getting processing status: {e}")
                return {
                    'status': 'error',
                    'message': str(e)
                }
    
    def _parse_datetime(self, date_str: str) -> Optional[datetime]:
        """Parse datetime string with robust error handling"""
        if not date_str:
            return None
        
        try:
            # Handle ISO format with 'Z' suffix
            if date_str.endswith('Z'):
                date_str = date_str.replace('Z', '+00:00')
            
            return datetime.fromisoformat(date_str)
        except Exception as e:
            logger.warning(f"Could not parse datetime '{date_str}': {e}")
            return None
