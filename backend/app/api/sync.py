"""
Background Sync API Endpoints

Provides endpoints for background synchronization of data to avoid blocking user requests.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Optional
import logging
import uuid

from app.services.robinhood_service import RobinhoodService
from app.services.options_order_service import OptionsOrderService
from app.schemas.common import DataResponse, ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["sync"])

def get_robinhood_service() -> RobinhoodService:
    """Dependency to get Robinhood service instance"""
    return RobinhoodService()

def get_options_order_service(rh_service: RobinhoodService = Depends(get_robinhood_service)) -> OptionsOrderService:
    """Dependency to get options order service instance"""
    return OptionsOrderService(rh_service)

@router.post(
    "/options-orders",
    response_model=DataResponse,
    responses={
        200: {"description": "Sync started successfully"},
        400: {"description": "Bad request", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def sync_options_orders(
    background_tasks: BackgroundTasks,
    days_back: int = 365,
    user_id: Optional[str] = None,
    force_full_sync: bool = False,
    options_order_service: OptionsOrderService = Depends(get_options_order_service)
):
    """
    Start background sync of options orders
    
    This endpoint initiates a background sync of options orders from Robinhood API
    to the local database. The sync runs asynchronously to avoid blocking the API.
    """
    try:
        # Use default user_id for demo
        if not user_id:
            user_id = str(uuid.uuid4())
        
        # Add sync task to background
        background_tasks.add_task(
            sync_options_orders_background,
            options_order_service,
            user_id,
            None,  # ignore lookback and fetch full history
            force_full_sync
        )
        
        return DataResponse(data={
            "message": "Options orders sync started in background",
            "user_id": user_id,
            "days_back": days_back,
            "force_full_sync": force_full_sync
        })
        
    except Exception as e:
        logger.error(f"Error starting options orders sync: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to start sync"
        )

async def sync_options_orders_background(
    options_order_service: OptionsOrderService,
    user_id: str,
    days_back: Optional[int],
    force_full_sync: bool
):
    """Background task to sync options orders"""
    try:
        logger.info(f"Starting background sync for user {user_id}")
        
        result = await options_order_service.sync_options_orders(
            user_id=user_id,
            days_back=days_back,
            force_full_sync=force_full_sync
        )
        
        if result["success"]:
            logger.info(f"Background sync completed: {result['data']['orders_stored']} orders stored")
        else:
            logger.error(f"Background sync failed: {result['message']}")
            
    except Exception as e:
        logger.error(f"Background sync error: {str(e)}", exc_info=True)

@router.get(
    "/status",
    response_model=DataResponse,
    responses={
        200: {"description": "Sync status retrieved successfully"},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_sync_status():
    """
    Get the status of background sync operations
    
    Returns information about ongoing and completed sync operations.
    """
    try:
        # This would typically check a sync status table or cache
        # For now, return a simple status
        return DataResponse(data={
            "message": "Sync status endpoint - not yet implemented",
            "active_syncs": 0,
            "last_sync": None
        })
        
    except Exception as e:
        logger.error(f"Error getting sync status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get sync status"
        )
