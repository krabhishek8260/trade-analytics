"""
Stocks API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
import logging

from app.services.robinhood_service import RobinhoodService
from app.schemas.common import DataResponse, ErrorResponse, ListResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stocks", tags=["stocks"])


def get_robinhood_service() -> RobinhoodService:
    """Dependency to get Robinhood service instance"""
    return RobinhoodService()


@router.get(
    "/positions",
    response_model=ListResponse,
    responses={
        200: {"description": "Stock positions retrieved successfully"},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_stock_positions(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    sort_by: Optional[str] = Query("market_value", description="Sort by field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    rh_service: RobinhoodService = Depends(get_robinhood_service)
):
    """Get all stock positions"""
    try:
        result = await rh_service.get_stock_positions()
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "Failed to fetch stock positions")
            )
        
        positions = result["data"]
        
        # Filter by symbol if provided
        if symbol:
            positions = [pos for pos in positions if pos.get("symbol", "").upper() == symbol.upper()]
        
        # Sort positions
        reverse = sort_order == "desc"
        if sort_by in ["symbol", "quantity", "average_buy_price", "current_price", "market_value", "total_return", "percent_change"]:
            try:
                positions.sort(
                    key=lambda x: x.get(sort_by, 0) if isinstance(x.get(sort_by, 0), (int, float)) else str(x.get(sort_by, "")),
                    reverse=reverse
                )
            except Exception as e:
                logger.warning(f"Error sorting positions by {sort_by}: {str(e)}")
        
        return ListResponse(
            data=positions,
            count=len(positions),
            total=len(positions)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching stock positions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/positions/{symbol}",
    response_model=DataResponse,
    responses={
        200: {"description": "Stock position retrieved successfully"},
        404: {"description": "Position not found", "model": ErrorResponse},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_stock_position(
    symbol: str,
    rh_service: RobinhoodService = Depends(get_robinhood_service)
):
    """Get specific stock position by symbol"""
    try:
        result = await rh_service.get_stock_positions()
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "Failed to fetch stock positions")
            )
        
        positions = result["data"]
        
        # Find position by symbol
        position = next(
            (pos for pos in positions if pos.get("symbol", "").upper() == symbol.upper()),
            None
        )
        
        if not position:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No position found for symbol {symbol}"
            )
        
        return DataResponse(data=position)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching stock position for {symbol}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/summary",
    response_model=DataResponse,
    responses={
        200: {"description": "Stocks summary retrieved successfully"},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_stocks_summary(
    rh_service: RobinhoodService = Depends(get_robinhood_service)
):
    """Get stocks portfolio summary"""
    try:
        result = await rh_service.get_stock_positions()
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "Failed to fetch stock positions")
            )
        
        positions = result["data"]
        
        # Calculate summary metrics
        total_value = sum(pos.get("market_value", 0) for pos in positions)
        total_cost = sum(pos.get("total_cost", 0) for pos in positions)
        total_return = sum(pos.get("total_return", 0) for pos in positions)
        
        winners = sum(1 for pos in positions if pos.get("total_return", 0) > 0)
        losers = sum(1 for pos in positions if pos.get("total_return", 0) < 0)
        
        summary = {
            "total_positions": len(positions),
            "total_value": total_value,
            "total_cost": total_cost,
            "total_return": total_return,
            "total_return_percent": (total_return / total_cost * 100) if total_cost > 0 else 0,
            "winners": winners,
            "losers": losers,
            "win_rate": (winners / len(positions) * 100) if positions else 0,
            "positions": positions
        }
        
        return DataResponse(data=summary)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating stocks summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )