"""
Rolled Options API V2 - Database-Driven

Fast rolled options endpoints that serve pre-computed data from the database
instead of processing on-demand. Uses background cron job processing.

Key improvements over V1:
- Response times: 100ms vs 2-5 minutes
- No timeout errors
- Supports pagination and filtering
- Real-time sync status
- Handles large datasets efficiently
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi import status as http_status
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.user import User
from app.models.rolled_options_chain import RolledOptionsChain, UserRolledOptionsSync
from app.services.rolled_options_cron_service import RolledOptionsCronService
from app.schemas.common import DataResponse, ListResponse, ErrorResponse
from app.services.robinhood_service import RobinhoodService
from app.core.security import get_current_user_id
from app.core.redis import cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rolled-options-v2", tags=["rolled-options-v2"])


def get_robinhood_service() -> RobinhoodService:
    """Dependency to get Robinhood service instance"""
    return RobinhoodService()


def get_cron_service() -> RolledOptionsCronService:
    """Dependency to get cron service instance"""
    return RolledOptionsCronService()


@router.post(
    "/cache/expire",
    response_model=DataResponse,
    responses={
        200: {"description": "Cache expired successfully"},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def expire_rolled_options_cache(
    scope: str = Query("all", regex="^(all|user)$", description="Expire all rolled options cache or only current user"),
    user_id: str = Depends(get_current_user_id),
):
    """Expire Redis caches used for rolled options UI responses."""
    try:
        pattern = "rolled_options:*"
        # Note: current cache keys are hashed and do not embed user_id; clear all for now
        cleared = await cache.clear_pattern(pattern)
        return DataResponse(data={
            "cleared_entries": cleared,
            "scope": scope
        })
    except Exception as e:
        logger.error(f"Error expiring rolled options cache: {e}")
        raise HTTPException(status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to expire cache")


@router.get(
    "/chains",
    response_model=DataResponse,
    responses={
        200: {"description": "Rolled options chains retrieved successfully"},
        202: {"description": "Processing in progress", "model": DataResponse},
        400: {"description": "Bad request", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_rolled_options_chains(
    symbol: Optional[str] = Query(None, description="Filter by underlying symbol"),
    status: Optional[str] = Query(None, regex="^(active|closed|expired)$", description="Filter by chain status"),
    page: int = Query(1, ge=1, description="Page number for pagination"),  
    limit: int = Query(25, ge=5, le=100, description="Number of chains per page"),
    sort_by: str = Query("last_activity", regex="^(last_activity|net_premium|total_pnl|start_date)$", description="Sort field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """
    Get rolled options chains from pre-computed database records
    
    This endpoint serves data from the database that has been pre-processed
    by background jobs, providing fast response times and no timeout issues.
    
    **Performance:**
    - Response time: < 200ms (vs 2-5 minutes in V1)
    - No processing timeouts
    - Efficient pagination
    - Real-time filtering and sorting
    
    **Data Freshness:**
    - Updated every 30 minutes by background jobs
    - Manual refresh available via /sync endpoint
    - Processing status available via /status endpoint
    """
    try:
        # Check if user has data or is being processed
        sync_status = await _get_user_sync_status(db, user_id)
        
        # If user has never been processed, trigger processing
        if not sync_status or sync_status.processing_status == 'pending':
            # Return processing status with empty data
            return DataResponse(data={
                "chains": [],
                "summary": {
                    "total_chains": 0,
                    "active_chains": 0,
                    "closed_chains": 0,
                    "total_orders": 0,
                    "net_premium_collected": 0.0,
                    "total_pnl": 0.0,
                    "avg_orders_per_chain": 0.0
                },
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total_chains": 0,
                    "total_pages": 0,
                    "has_next": False,
                    "has_prev": False
                },
                "processing_status": {
                    "status": sync_status.processing_status if sync_status else "pending",
                    "message": "Data is being processed in the background. Please check back in a few minutes.",
                    "last_processed": sync_status.last_processed_at.isoformat() if sync_status and sync_status.last_processed_at else None
                },
                "filters_applied": {
                    "symbol": symbol,
                    "status": status
                }
            })
        
        # Build query for chains
        query = select(RolledOptionsChain).where(
            RolledOptionsChain.user_id == user_id
        )
        
        # Apply filters
        if symbol:
            query = query.where(RolledOptionsChain.underlying_symbol == symbol.upper())
        
        if status:
            query = query.where(RolledOptionsChain.status == status)
        
        # Apply sorting
        sort_field = {
            "last_activity": RolledOptionsChain.last_activity_date,
            "net_premium": RolledOptionsChain.net_premium,
            "total_pnl": RolledOptionsChain.total_pnl,
            "start_date": RolledOptionsChain.start_date
        }.get(sort_by, RolledOptionsChain.last_activity_date)
        
        if sort_order == "desc":
            query = query.order_by(desc(sort_field))
        else:
            query = query.order_by(sort_field)
        
        # Get total count for pagination
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total_chains = total_result.scalar() or 0
        
        # Apply pagination
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        chains_records = result.scalars().all()
        
        # Convert to API format
        chains = []
        for record in chains_records:
            chain_data = record.chain_data or {}
            
            # Determine latest position for active chains
            latest_position = None
            if record.status == "active":
                # Check if latest_position is already in chain_data
                latest_position = chain_data.get("latest_position")
                
                # If not, derive it from the first order's roll_details.open_position
                if not latest_position:
                    orders = chain_data.get("orders", [])
                    if orders:
                        first_order = orders[0]
                        roll_details = first_order.get("roll_details")
                        if roll_details and roll_details.get("open_position"):
                            open_pos = roll_details["open_position"]
                            latest_position = {
                                "strike_price": open_pos.get("strike_price"),
                                "expiration_date": open_pos.get("expiration_date"),
                                "option_type": open_pos.get("option_type")
                            }
            
            # Ensure required fields exist
            chain_api = {
                "chain_id": record.chain_id,
                "underlying_symbol": record.underlying_symbol,
                "status": record.status,
                "initial_strategy": record.initial_strategy,
                "start_date": record.start_date.isoformat() if record.start_date else None,
                "last_activity_date": record.last_activity_date.isoformat() if record.last_activity_date else None,
                "total_orders": record.total_orders,
                "roll_count": record.roll_count,
                "total_credits_collected": float(record.total_credits_collected or 0),
                "total_debits_paid": float(record.total_debits_paid or 0),
                "net_premium": float(record.net_premium or 0),
                "total_pnl": float(record.total_pnl or 0),
                "latest_position": latest_position,  # Add latest position field
                "orders": chain_data.get("orders", [])
            }
            chains.append(chain_api)
        
        # Calculate pagination
        total_pages = (total_chains + limit - 1) // limit
        has_next = page < total_pages
        has_prev = page > 1
        
        # Get summary statistics
        summary = await _get_chains_summary(db, user_id, symbol, status)
        
        return DataResponse(data={
            "chains": chains,
            "summary": summary,
            "pagination": {
                "page": page,
                "limit": limit,
                "total_chains": total_chains,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev
            },
            "processing_status": {
                "status": sync_status.processing_status,
                "last_processed": sync_status.last_processed_at.isoformat() if sync_status.last_processed_at else None,
                "last_successful": sync_status.last_successful_sync.isoformat() if sync_status.last_successful_sync else None,
                "data_age_minutes": _calculate_data_age_minutes(sync_status.last_successful_sync) if sync_status.last_successful_sync else None
            },
            "filters_applied": {
                "symbol": symbol,
                "status": status,
                "sort_by": sort_by,
                "sort_order": sort_order
            },
            "performance_optimized": True,
            "data_source": "database"
        })
        
    except Exception as e:
        logger.error(f"Error retrieving rolled options chains: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/chains/{chain_id}",
    response_model=DataResponse,
    responses={
        200: {"description": "Chain details retrieved successfully"},
        404: {"description": "Chain not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_rolled_options_chain_details(
    chain_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a specific rolled options chain"""
    
    try:
        # Query for the specific chain
        query = select(RolledOptionsChain).where(
            and_(
                RolledOptionsChain.user_id == user_id,
                RolledOptionsChain.chain_id == chain_id
            )
        )
        
        result = await db.execute(query)
        chain_record = result.scalar_one_or_none()
        
        if not chain_record:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Chain with ID {chain_id} not found"
            )
        
        # Return complete chain data
        chain_data = chain_record.chain_data or {}
        
        return DataResponse(data={
            "chain_id": chain_record.chain_id,
            "underlying_symbol": chain_record.underlying_symbol,
            "status": chain_record.status,
            "initial_strategy": chain_record.initial_strategy,
            "start_date": chain_record.start_date.isoformat() if chain_record.start_date else None,
            "last_activity_date": chain_record.last_activity_date.isoformat() if chain_record.last_activity_date else None,
            "total_orders": chain_record.total_orders,
            "roll_count": chain_record.roll_count,
            "total_credits_collected": float(chain_record.total_credits_collected or 0),
            "total_debits_paid": float(chain_record.total_debits_paid or 0),
            "net_premium": float(chain_record.net_premium or 0),
            "total_pnl": float(chain_record.total_pnl or 0),
            "orders": chain_data.get("orders", []),
            "analysis": chain_data,
            "last_updated": chain_record.processed_at.isoformat() if chain_record.processed_at else None
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving chain details for {chain_id}: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/summary",
    response_model=DataResponse,
    responses={
        200: {"description": "Summary retrieved successfully"},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_rolled_options_summary(
    symbol: Optional[str] = Query(None, description="Filter by underlying symbol"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """Get summary statistics for rolled options activity"""
    
    try:
        summary = await _get_chains_summary(db, user_id, symbol)
        
        # Get sync status
        sync_status = await _get_user_sync_status(db, user_id)
        
        return DataResponse(data={
            **summary,
            "processing_status": {
                "status": sync_status.processing_status if sync_status else "pending",
                "last_updated": sync_status.last_successful_sync.isoformat() if sync_status and sync_status.last_successful_sync else None,
                "data_age_minutes": _calculate_data_age_minutes(sync_status.last_successful_sync) if sync_status and sync_status.last_successful_sync else None
            }
        })
        
    except Exception as e:
        logger.error(f"Error retrieving rolled options summary: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post(
    "/sync",
    response_model=DataResponse,
    responses={
        200: {"description": "Sync initiated successfully"},
        400: {"description": "Bad request", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def trigger_rolled_options_sync(
    background_tasks: BackgroundTasks,
    force_full_sync: bool = Query(False, description="Force full sync instead of incremental"),
    user_id: str = Depends(get_current_user_id),
    cron_service: RolledOptionsCronService = Depends(get_cron_service),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger rolled options processing for the current user
    
    This endpoint allows users to manually refresh their rolled options data
    instead of waiting for the background cron job.
    """
    try:
        # Check if already processing
        sync_status = await _get_user_sync_status(db, user_id)
        if sync_status and sync_status.processing_status == 'processing':
            return DataResponse(data={
                "message": "Processing already in progress",
                "status": "processing",
                "estimated_completion": "2-5 minutes"
            })
        
        # Trigger background processing
        user_info = {
            'user_id': user_id,
            'full_sync_required': force_full_sync
        }
        
        background_tasks.add_task(
            _process_user_background,
            cron_service,
            user_info
        )
        
        return DataResponse(data={
            "message": "Rolled options processing started in background",
            "user_id": user_id,
            "force_full_sync": force_full_sync,
            "estimated_completion": "2-5 minutes",
            "status": "processing"
        })
        
    except Exception as e:
        logger.error(f"Error triggering sync for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start sync"
        )


@router.get(
    "/status",
    response_model=DataResponse,
    responses={
        200: {"description": "Status retrieved successfully"},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_rolled_options_status(
    user_id: str = Depends(get_current_user_id),
    cron_service: RolledOptionsCronService = Depends(get_cron_service)
):
    """Get the processing status for rolled options"""
    
    try:
        status = await cron_service.get_processing_status(user_id)
        return DataResponse(data=status)
        
    except Exception as e:
        logger.error(f"Error getting status for user {user_id}: {str(e)}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get status"
        )


# Helper functions

async def _get_user_sync_status(db: AsyncSession, user_id: str) -> Optional[UserRolledOptionsSync]:
    """Get sync status for a user"""
    result = await db.execute(
        select(UserRolledOptionsSync).where(UserRolledOptionsSync.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def _get_chains_summary(
    db: AsyncSession, 
    user_id: str, 
    symbol: Optional[str] = None,
    status: Optional[str] = None
) -> Dict[str, Any]:
    """Get summary statistics for user's chains"""
    
    # Build base query
    query = select(RolledOptionsChain).where(RolledOptionsChain.user_id == user_id)
    
    if symbol:
        query = query.where(RolledOptionsChain.underlying_symbol == symbol.upper())
    
    if status:
        query = query.where(RolledOptionsChain.status == status)
    
    result = await db.execute(query)
    chains = result.scalars().all()
    
    if not chains:
        return {
            "total_chains": 0,
            "active_chains": 0,
            "closed_chains": 0,
            "expired_chains": 0,
            "total_orders": 0,
            "net_premium_collected": 0.0,
            "total_pnl": 0.0,
            "avg_orders_per_chain": 0.0
        }
    
    # Calculate statistics
    total_chains = len(chains)
    active_chains = len([c for c in chains if c.status == 'active'])
    closed_chains = len([c for c in chains if c.status == 'closed'])
    expired_chains = len([c for c in chains if c.status == 'expired'])
    
    total_orders = sum(c.total_orders for c in chains)
    net_premium = sum(float(c.net_premium or 0) for c in chains)
    total_pnl = sum(float(c.total_pnl or 0) for c in chains)
    avg_orders = total_orders / total_chains if total_chains > 0 else 0
    
    return {
        "total_chains": total_chains,
        "active_chains": active_chains,
        "closed_chains": closed_chains,
        "expired_chains": expired_chains,
        "total_orders": total_orders,
        "net_premium_collected": net_premium,
        "total_pnl": total_pnl,
        "avg_orders_per_chain": round(avg_orders, 1)
    }


def _calculate_data_age_minutes(last_sync: Optional[datetime]) -> Optional[int]:
    """Calculate how many minutes old the data is"""
    if not last_sync:
        return None
    
    age = datetime.now(last_sync.tzinfo) - last_sync
    return int(age.total_seconds() / 60)


async def _process_user_background(cron_service: RolledOptionsCronService, user_info: Dict[str, Any]):
    """Background task to process a single user"""
    try:
        await cron_service._process_user_rolled_options(user_info)
    except Exception as e:
        logger.error(f"Background processing failed for user {user_info.get('user_id')}: {e}")
