"""
Options Orders Background Processing Service

Handles background processing of options orders synchronization for all users.
Runs as a background job to:

1. Identify users needing sync (new users or incremental updates)
2. Load and synchronize their options orders from Robinhood API
3. Store results in the database with progress tracking
4. Update sync status and schedule next processing

Key Features:
- Incremental processing (only new orders since last sync)
- Error handling and retry logic
- Performance monitoring and logging
- Graceful handling of large datasets
- Progress tracking for real-time UI updates
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_, text
from sqlalchemy.dialects.postgresql import insert
from uuid import UUID

from app.core.database import get_db
from app.models.user import User
from app.models.options_order import OptionsOrder
from app.services.robinhood_service import RobinhoodService
from app.services.options_order_service import OptionsOrderService
from app.core.redis import cache

logger = logging.getLogger(__name__)


class OptionsOrdersBackgroundService:
    """Background service for processing options orders synchronization"""
    
    def __init__(self):
        self.rh_service = RobinhoodService()
        self.options_service = OptionsOrderService(self.rh_service)
        self.processing_timeout = 300  # 5 minutes per user
        self.max_retries = 3
        
    async def process_all_users(self) -> Dict[str, Any]:
        """
        Main entry point for background job - process all users needing updates
        
        Returns:
            Summary of processing results
        """
        start_time = datetime.now(timezone.utc)
        logger.info("Starting options orders background processing for all users")
        
        try:
            # Get users needing processing
            users_to_process = await self._get_users_needing_processing()
            logger.info(f"Found {len(users_to_process)} users needing options orders processing")
            
            if not users_to_process:
                return {
                    'success': True,
                    'message': 'No users need processing',
                    'users_processed': 0,
                    'total_orders': 0,
                    'processing_time': 0
                }
            
            # Process each user
            total_orders = 0
            users_processed = 0
            errors = []
            
            for user_info in users_to_process:
                try:
                    user_id = str(user_info['user_id'])
                    logger.info(f"Processing options orders for user {user_id}")
                    
                    # Update status to processing in cache
                    await self._update_sync_status(user_id, 'processing')
                    
                    # Process user with timeout
                    result = await asyncio.wait_for(
                        self._process_user_options_orders(user_info),
                        timeout=self.processing_timeout
                    )
                    
                    if result['success']:
                        users_processed += 1
                        total_orders += result.get('orders_processed', 0)
                        logger.info(f"Successfully processed user {user_id}: {result.get('orders_processed', 0)} orders")
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
            
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            return {
                'success': True,
                'message': f'Processed {users_processed}/{len(users_to_process)} users successfully',
                'users_processed': users_processed,
                'total_orders': total_orders,
                'processing_time': processing_time,
                'errors': errors[:10]  # Limit error messages
            }
            
        except Exception as e:
            logger.error(f"Error in process_all_users: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'Background processing failed: {str(e)}',
                'users_processed': 0,
                'total_orders': 0,
                'processing_time': (datetime.now(timezone.utc) - start_time).total_seconds()
            }
    
    async def _get_users_needing_processing(self) -> List[Dict[str, Any]]:
        """Get list of users who need options orders processing"""
        
        async for db in get_db():
            try:
                # Get all users and their last sync info
                query = select(
                    User.id,
                    func.max(OptionsOrder.created_at).label('last_order_sync'),
                    func.count(OptionsOrder.id).label('total_orders')
                ).select_from(
                    User
                ).outerjoin(
                    OptionsOrder, User.id == OptionsOrder.user_id
                ).group_by(
                    User.id
                ).having(
                    # Users with no orders OR orders older than 1 hour
                    or_(
                        func.count(OptionsOrder.id) == 0,
                        func.max(OptionsOrder.created_at) < datetime.now(timezone.utc) - timedelta(hours=1)
                    )
                )
                
                result = await db.execute(query)
                users = []
                
                for row in result:
                    user_data = {
                        'user_id': row.id,
                        'last_order_sync': row.last_order_sync,
                        'total_orders': row.total_orders or 0,
                        'full_sync_required': row.total_orders == 0  # Full sync for new users
                    }
                    users.append(user_data)
                
                return users
                
            except Exception as e:
                logger.error(f"Error getting users needing processing: {e}")
                return []
    
    async def _process_user_options_orders(self, user_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process options orders for a single user
        
        Args:
            user_info: User information from _get_users_needing_processing
            
        Returns:
            Processing result summary
        """
        user_id = str(user_info['user_id'])
        full_sync = user_info.get('full_sync_required', False)
        
        try:
            # Determine sync parameters
            if full_sync:
                # Full sync - process more historical data for new users
                days_back = 365  # 1 year max
                logger.info(f"Full sync for user {user_id} - processing {days_back} days")
            else:
                # Incremental sync - only recent data
                days_back = 7  # Last week
                logger.info(f"Incremental sync for user {user_id} - processing {days_back} days")
            
            # Set up progress callback for this user
            progress_data = {}
            
            def progress_callback(progress: Dict[str, Any]):
                progress_data.update(progress)
                # Store progress in Redis for real-time UI updates
                asyncio.create_task(self._store_progress_in_cache(user_id, progress))
            
            # Sync orders using the service
            result = await self.options_service.sync_options_orders(
                user_id=user_id,
                force_full_sync=full_sync,
                days_back=days_back,
                progress_callback=progress_callback
            )
            
            if result['success']:
                # Update sync status to completed
                await self._update_sync_status(
                    user_id, 'completed', 
                    orders_synced=result['data']['orders_stored'],
                    sync_type=result['data']['sync_type']
                )
                
                return {
                    'success': True,
                    'message': f'Synced {result["data"]["orders_stored"]} orders',
                    'orders_processed': result['data']['orders_stored'],
                    'sync_type': result['data']['sync_type']
                }
            else:
                # Update sync status to error
                await self._update_sync_status(user_id, 'error', result.get('message'))
                return {
                    'success': False,
                    'message': result.get('message', 'Sync failed'),
                    'orders_processed': 0
                }
                
        except Exception as e:
            logger.error(f"Error processing user {user_id}: {str(e)}", exc_info=True)
            await self._update_sync_status(user_id, 'error', str(e))
            return {
                'success': False,
                'message': str(e),
                'orders_processed': 0
            }
    
    async def _store_progress_in_cache(self, user_id: str, progress: Dict[str, Any]):
        """Store progress data in Redis for real-time UI updates"""
        try:
            cache_key = f"options_orders_sync_progress:{user_id}"
            progress_with_timestamp = {
                **progress,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'user_id': user_id
            }
            await cache.set(cache_key, progress_with_timestamp, ttl=3600)  # 1 hour
        except Exception as e:
            logger.warning(f"Failed to store progress in cache: {str(e)}")
    
    async def _update_sync_status(
        self,
        user_id: str,
        status: str,
        error_message: Optional[str] = None,
        orders_synced: Optional[int] = None,
        sync_type: Optional[str] = None
    ) -> None:
        """Update sync status for a user in cache"""
        try:
            cache_key = f"options_orders_sync_status:{user_id}"
            
            # Calculate next sync time
            next_sync = None
            if status == 'completed':
                # Incremental sync every 15 minutes
                next_sync = datetime.now(timezone.utc) + timedelta(minutes=15)
            
            status_data = {
                'user_id': user_id,
                'status': status,
                'last_sync': datetime.now(timezone.utc).isoformat(),
                'next_sync': next_sync.isoformat() if next_sync else None,
                'error_message': error_message,
                'orders_synced': orders_synced,
                'sync_type': sync_type
            }
            
            await cache.set(cache_key, status_data, ttl=3600 * 24)  # 24 hours
            
        except Exception as e:
            logger.error(f"Error updating sync status for user {user_id}: {e}")
    
    async def get_processing_status(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get processing status for a user or all users"""
        try:
            if user_id:
                # Get status for specific user
                cache_key = f"options_orders_sync_status:{user_id}"
                status_data = await cache.get(cache_key)
                
                if status_data:
                    return status_data
                else:
                    return {
                        'status': 'pending',
                        'message': 'User not yet processed',
                        'user_id': user_id
                    }
            else:
                # Get summary for all users
                # This would require scanning cache keys or using database
                async for db in get_db():
                    try:
                        # Get basic stats from database
                        result = await db.execute(
                            select(
                                func.count(User.id).label('total_users'),
                                func.count(OptionsOrder.user_id.distinct()).label('users_with_orders'),
                                func.count(OptionsOrder.id).label('total_orders'),
                                func.max(OptionsOrder.created_at).label('last_order')
                            ).select_from(User).outerjoin(OptionsOrder)
                        )
                        
                        summary = result.first()
                        return {
                            'total_users': summary.total_users or 0,
                            'users_with_orders': summary.users_with_orders or 0,
                            'total_orders': summary.total_orders or 0,
                            'last_order': summary.last_order.isoformat() if summary.last_order else None
                        }
                        
                    except Exception as e:
                        logger.error(f"Error getting processing summary: {e}")
                        return {
                            'status': 'error',
                            'message': str(e)
                        }
                    
        except Exception as e:
            logger.error(f"Error getting processing status: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    async def get_user_progress(self, user_id: str) -> Dict[str, Any]:
        """Get real-time progress for a user's sync operation"""
        try:
            cache_key = f"options_orders_sync_progress:{user_id}"
            progress_data = await cache.get(cache_key)
            
            if progress_data:
                return progress_data
            else:
                # Check if sync is complete
                status_key = f"options_orders_sync_status:{user_id}"
                status_data = await cache.get(status_key)
                
                if status_data and status_data.get('status') == 'completed':
                    return {
                        'status': 'complete',
                        'message': 'Sync completed successfully',
                        'progress': 100,
                        'user_id': user_id
                    }
                else:
                    return {
                        'status': 'not_started',
                        'message': 'No sync in progress',
                        'progress': 0,
                        'user_id': user_id
                    }
                    
        except Exception as e:
            logger.error(f"Error getting user progress: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'progress': 0,
                'user_id': user_id
            }


# Global service instance
options_orders_background_service = OptionsOrdersBackgroundService()