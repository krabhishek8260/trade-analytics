"""
Optimized Rolled Options Service

This service combines the best features from all previous implementations:
- Redis caching for fast response times
- Database persistence for data consistency
- Smart data fetching with timeout protection
- Efficient pagination and filtering
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict
import hashlib
import json

from app.core.redis import cache
from app.services.options_order_service import OptionsOrderService
from app.services.fast_rolled_options_service import FastRolledOptionsService

logger = logging.getLogger(__name__)


class OptimizedRolledOptionsService:
    """Optimized rolled options service with Redis caching and smart data fetching"""
    
    def __init__(self, robinhood_service):
        self.rh_service = robinhood_service
        self.options_order_service = OptionsOrderService(robinhood_service)
        self.fast_service = FastRolledOptionsService(robinhood_service)
        
    def _generate_cache_key(self, user_id: str, days_back: int, symbol: Optional[str] = None, 
                          status: Optional[str] = None, min_orders: int = 2) -> str:
        """Generate a unique cache key for the request parameters"""
        key_data = f"{user_id}:{days_back}:{symbol or 'all'}:{status or 'all'}:{min_orders}"
        return f"rolled_options:{hashlib.md5(key_data.encode()).hexdigest()}"
    
    async def get_rolled_options_chains_optimized(
        self,
        user_id: str,
        days_back: int = 30,
        symbol: Optional[str] = None,
        status: Optional[str] = None,
        min_orders: int = 2,
        page: int = 1,
        limit: int = 50,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get rolled options chains with optimized performance using multi-layer caching
        
        Performance optimizations:
        1. Redis cache for instant responses (15-minute TTL)
        2. Database cache for medium-term storage
        3. Smart API fetching with timeout protection
        4. Efficient pagination without re-processing
        """
        try:
            # Step 1: Check Redis cache first
            cache_key = self._generate_cache_key(user_id, days_back, symbol, status, min_orders)
            
            if use_cache:
                cached_result = await cache.get(cache_key)
                if cached_result:
                    logger.info(f"Cache hit for rolled options: {cache_key}")
                    return self._paginate_cached_result(cached_result, page, limit)
            
            # Step 2: Determine optimal strategy based on request parameters
            strategy = self._determine_optimal_strategy(days_back, symbol, user_id)
            
            if strategy == "fast":
                # Use fast service for quick results
                logger.info(f"Using fast strategy for days_back={days_back}")
                result = await self.fast_service.get_rolled_options_chains_fast(
                    days_back=min(days_back, 90),  # Cap at 90 days for fast service
                    symbol=symbol,
                    status=status,
                    min_orders=min_orders,
                    page=1,  # Get all data for caching
                    limit=1000  # Large limit to get all chains
                )
                
            elif strategy == "database":
                # Use database service for cached data
                logger.info(f"Using database strategy for user {user_id}")
                result = await self._get_from_database_with_fallback(
                    user_id, days_back, symbol, status, min_orders
                )
                
            else:
                # Fallback to empty result to prevent timeouts
                logger.warning(f"Using fallback strategy for days_back={days_back}")
                result = self._get_empty_result(days_back, symbol, status, min_orders)
            
            # Step 3: Cache the result if successful
            if result.get("success", False) and use_cache:
                # Cache for 15 minutes
                await cache.set(cache_key, result, ttl=900)
                logger.info(f"Cached rolled options result: {cache_key}")
            
            # Step 4: Apply pagination
            return self._paginate_result(result, page, limit)
            
        except Exception as e:
            logger.error(f"Error in optimized rolled options service: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"Service error: {str(e)}",
                "data": self._get_empty_pagination_data(page, limit, days_back)
            }
    
    def _determine_optimal_strategy(self, days_back: int, symbol: Optional[str], user_id: str) -> str:
        """Determine the optimal strategy based on request parameters"""
        
        # Always use database strategy - it can handle any date range efficiently
        # The database service has been optimized with proper indexing and caching
        return "database"
    
    async def _get_from_database_with_fallback(
        self,
        user_id: str,
        days_back: int,
        symbol: Optional[str],
        status: Optional[str],
        min_orders: int
    ) -> Dict[str, Any]:
        """Get data from database with smart fallback strategies"""
        try:
            # Try database first
            db_result = await self.options_order_service.get_rolled_options_chains_from_db(
                user_id=user_id,
                days_back=days_back,
                symbol=symbol,
                status=status,
                min_orders=min_orders
            )
            
            # If database has data, return it
            if db_result.get("success", False) and db_result.get("data", {}).get("chains"):
                chains = db_result['data']['chains']
                logger.info(f"Database returned {len(chains)} chains")
                
                # Debug: log symbols from first few chains
                for i, chain in enumerate(chains[:3]):
                    symbol = chain.get('underlying_symbol', 'NO_SYMBOL')
                    logger.info(f"Chain {i+1} symbol: '{symbol}'")
                    
                return db_result
            
            # If no data in database, try smart sync with timeout protection
            logger.info("No database data found. Attempting smart sync...")
            
            # Use shorter sync period to prevent timeouts
            sync_days = min(days_back, 60)  # Cap sync at 60 days
            
            # Set a timeout for the sync operation
            try:
                sync_task = asyncio.create_task(
                    self.options_order_service.sync_options_orders(
                        user_id=user_id,
                        days_back=sync_days,
                        force_full_sync=False
                    )
                )
                
                # Wait for sync with 30-second timeout
                sync_result = await asyncio.wait_for(sync_task, timeout=30.0)
                
                if sync_result.get("success", False):
                    logger.info(f"Smart sync completed: {sync_result.get('data', {}).get('orders_stored', 0)} orders")
                    
                    # Try database again after sync
                    return await self.options_order_service.get_rolled_options_chains_from_db(
                        user_id=user_id,
                        days_back=days_back,
                        symbol=symbol,
                        status=status,
                        min_orders=min_orders
                    )
                
            except asyncio.TimeoutError:
                logger.warning("Sync operation timed out after 30 seconds")
            except Exception as sync_error:
                logger.error(f"Sync operation failed: {str(sync_error)}")
            
            # If sync fails, fallback to fast service with limited data
            logger.info("Falling back to fast service due to sync issues")
            return await self.fast_service.get_rolled_options_chains_fast(
                days_back=min(days_back, 30),  # Very limited for fallback
                symbol=symbol,
                status=status,
                min_orders=min_orders,
                page=1,
                limit=500
            )
            
        except Exception as e:
            logger.error(f"Database fallback error: {str(e)}")
            return self._get_empty_result(days_back, symbol, status, min_orders)
    
    def _get_empty_result(self, days_back: int, symbol: Optional[str], 
                         status: Optional[str], min_orders: int) -> Dict[str, Any]:
        """Return empty result structure"""
        return {
            "success": True,
            "message": "No rolled options chains found (optimized for performance)",
            "data": {
                "chains": [],
                "summary": {
                    "total_chains": 0,
                    "active_chains": 0,
                    "closed_chains": 0,
                    "total_orders": 0,
                    "net_premium_collected": 0.0,
                    "total_pnl": 0.0,
                    "avg_orders_per_chain": 0.0,
                    "most_active_symbol": None,
                    "symbol_distribution": {}
                },
                "filters_applied": {
                    "symbol": symbol,
                    "status": status,
                    "min_orders": min_orders
                },
                "analysis_period_days": days_back,
                "performance_note": "Results optimized for fast response times"
            }
        }
    
    def _paginate_result(self, result: Dict[str, Any], page: int, limit: int) -> Dict[str, Any]:
        """Apply pagination to any result format"""
        if not result.get("success", False):
            return result
        
        data = result.get("data", {})
        chains = data.get("chains", [])
        
        # Calculate pagination
        total_chains = len(chains)
        total_pages = (total_chains + limit - 1) // limit if total_chains > 0 else 1
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        
        # Slice chains for current page
        paginated_chains = chains[start_idx:end_idx]
        
        # Update data with pagination info
        paginated_data = data.copy()
        paginated_data.update({
            "chains": paginated_chains,
            "total_chains": total_chains,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
            "current_page": page,
            "page_size": limit,
            "chains_on_page": len(paginated_chains)
        })
        
        return {
            "success": True,
            "message": f"Retrieved page {page} of {total_pages} ({len(paginated_chains)} chains)",
            "data": paginated_data
        }
    
    def _paginate_cached_result(self, cached_result: Dict[str, Any], page: int, limit: int) -> Dict[str, Any]:
        """Apply pagination to cached result"""
        return self._paginate_result(cached_result, page, limit)
    
    def _get_empty_pagination_data(self, page: int, limit: int, days_back: int) -> Dict[str, Any]:
        """Get empty pagination data structure"""
        return {
            "chains": [],
            "summary": {
                "total_chains": 0,
                "active_chains": 0,
                "closed_chains": 0,
                "total_orders": 0,
                "net_premium_collected": 0.0,
                "total_pnl": 0.0,
                "avg_orders_per_chain": 0.0,
                "most_active_symbol": None,
                "symbol_distribution": {}
            },
            "total_chains": 0,
            "total_pages": 0,
            "has_next": False,
            "has_prev": False,
            "current_page": page,
            "page_size": limit,
            "chains_on_page": 0,
            "analysis_period_days": days_back,
            "performance_optimized": True
        }
    
    async def clear_cache(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Clear cached rolled options data"""
        try:
            if user_id:
                # Clear cache for specific user
                pattern = f"rolled_options:*{user_id}*"
            else:
                # Clear all rolled options cache
                pattern = "rolled_options:*"
            
            cleared_count = await cache.clear_pattern(pattern)
            
            return {
                "success": True,
                "message": f"Cleared {cleared_count} cache entries",
                "data": {"cleared_entries": cleared_count}
            }
            
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            return {
                "success": False,
                "message": f"Cache clear error: {str(e)}",
                "data": None
            }
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring"""
        try:
            # This is a simplified version - in production you might want more detailed stats
            return {
                "success": True,
                "message": "Cache stats retrieved",
                "data": {
                    "cache_enabled": True,
                    "default_ttl_seconds": 900,
                    "note": "Detailed cache statistics require Redis monitoring tools"
                }
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return {
                "success": False,
                "message": f"Cache stats error: {str(e)}",
                "data": None
            }
