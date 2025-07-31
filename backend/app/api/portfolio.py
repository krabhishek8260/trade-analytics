"""
Portfolio API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
import logging

from app.services.robinhood_service import RobinhoodService
from app.schemas.common import DataResponse, ErrorResponse
from app.schemas.portfolio import PortfolioSummary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


def get_robinhood_service() -> RobinhoodService:
    """Dependency to get Robinhood service instance"""
    return RobinhoodService()


@router.get(
    "/summary",
    response_model=DataResponse,
    responses={
        200: {"description": "Portfolio summary retrieved successfully"},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_portfolio_summary(
    rh_service: RobinhoodService = Depends(get_robinhood_service)
):
    """Get portfolio summary including total value, returns, and breakdown"""
    try:
        result = await rh_service.get_portfolio_summary()
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "Failed to fetch portfolio summary")
            )
        
        return DataResponse(data=result["data"])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching portfolio summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/performance",
    response_model=DataResponse,
    responses={
        200: {"description": "Portfolio performance retrieved successfully"},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_portfolio_performance(
    days: int = 30,
    rh_service: RobinhoodService = Depends(get_robinhood_service)
):
    """Get portfolio performance over time"""
    try:
        # This will be implemented when we add historical data tracking
        performance_data = {
            "message": "Portfolio performance tracking not yet implemented",
            "requested_days": days,
            "note": "This will be available after implementing historical data collection"
        }
        
        return DataResponse(data=performance_data)
        
    except Exception as e:
        logger.error(f"Error fetching portfolio performance: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/allocation",
    response_model=DataResponse,
    responses={
        200: {"description": "Portfolio allocation retrieved successfully"},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_portfolio_allocation(
    rh_service: RobinhoodService = Depends(get_robinhood_service)
):
    """Get portfolio allocation breakdown by asset type"""
    try:
        # Get both stocks and options positions to calculate allocation
        portfolio_summary = await rh_service.get_portfolio_summary()
        stocks_positions = await rh_service.get_stock_positions()
        options_positions = await rh_service.get_options_positions()
        
        if not all([
            portfolio_summary.get("success"),
            stocks_positions.get("success"),
            options_positions.get("success")
        ]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to fetch portfolio data for allocation analysis"
            )
        
        # Calculate allocation
        stocks_value = sum(pos.get("market_value", 0) for pos in stocks_positions["data"])
        options_value = sum(pos.get("market_value", 0) for pos in options_positions["data"])
        total_portfolio_value = float(portfolio_summary["data"].get("total_value", 0))
        
        if total_portfolio_value > 0:
            stocks_percent = (stocks_value / total_portfolio_value) * 100
            options_percent = (options_value / total_portfolio_value) * 100
            cash_percent = max(0, 100 - stocks_percent - options_percent)
        else:
            stocks_percent = options_percent = cash_percent = 0
        
        allocation_data = {
            "stocks_percent": round(stocks_percent, 2),
            "options_percent": round(options_percent, 2),
            "cash_percent": round(cash_percent, 2),
            "stocks_value": stocks_value,
            "options_value": options_value,
            "total_value": total_portfolio_value,
            "stocks_count": len(stocks_positions["data"]),
            "options_count": len(options_positions["data"])
        }
        
        return DataResponse(data=allocation_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating portfolio allocation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )