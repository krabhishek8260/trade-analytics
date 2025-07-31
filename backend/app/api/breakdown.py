"""
Portfolio Breakdown API Endpoints

This module provides API endpoints for detailed portfolio metric breakdowns
with interactive drill-down capabilities and calculation transparency.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from typing import Optional
import logging

from app.services.robinhood_service import RobinhoodService
from app.services.breakdown_service import BreakdownCalculator
from app.schemas.breakdown import (
    BreakdownResponse, BreakdownRequest, GreeksBreakdownRequest,
    GroupingType, SortType, FilterOptions
)
from app.schemas.common import DataResponse, ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/breakdown", tags=["breakdown"])

def get_robinhood_service() -> RobinhoodService:
    """Dependency to get Robinhood service instance"""
    return RobinhoodService()

def get_breakdown_calculator(rh_service: RobinhoodService = Depends(get_robinhood_service)) -> BreakdownCalculator:
    """Dependency to get breakdown calculator instance"""
    return BreakdownCalculator(rh_service)

@router.post(
    "/total-value",
    response_model=DataResponse,
    responses={
        200: {"description": "Portfolio total value breakdown retrieved successfully"},
        400: {"description": "Bad request", "model": ErrorResponse},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_total_value_breakdown(
    request: BreakdownRequest = Body(...),
    calculator: BreakdownCalculator = Depends(get_breakdown_calculator)
):
    """
    Get detailed breakdown of portfolio total value
    
    Returns comprehensive breakdown showing:
    - Long positions (assets) vs short positions (liabilities)
    - Grouping by symbol, strategy, expiry, or position type
    - Calculation methodology and formulas
    - Drill-down capabilities for further analysis
    """
    try:
        breakdown = await calculator.calculate_total_value_breakdown(request)
        return DataResponse(data=breakdown)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error calculating total value breakdown: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post(
    "/total-return",
    response_model=DataResponse,
    responses={
        200: {"description": "Portfolio total return breakdown retrieved successfully"},
        400: {"description": "Bad request", "model": ErrorResponse},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_total_return_breakdown(
    request: BreakdownRequest = Body(...),
    calculator: BreakdownCalculator = Depends(get_breakdown_calculator)
):
    """
    Get detailed breakdown of portfolio total return
    
    Returns comprehensive breakdown showing:
    - Individual position P&L contributions
    - Winners vs losers analysis
    - Return percentage calculations
    - Grouping options for detailed analysis
    """
    try:
        breakdown = await calculator.calculate_total_return_breakdown(request)
        return DataResponse(data=breakdown)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error calculating total return breakdown: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.post(
    "/greeks/{greek_type}",
    response_model=DataResponse,
    responses={
        200: {"description": "Portfolio Greeks breakdown retrieved successfully"},
        400: {"description": "Bad request", "model": ErrorResponse},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_greeks_breakdown(
    greek_type: str,
    request: BreakdownRequest = Body(...),
    calculator: BreakdownCalculator = Depends(get_breakdown_calculator)
):
    """
    Get detailed breakdown of portfolio Greeks
    
    Available greek_types: delta, gamma, theta, vega, rho
    
    Returns comprehensive breakdown showing:
    - Individual position Greek contributions
    - Portfolio-level Greek exposure
    - Risk sensitivity analysis
    - Position sizing impact on Greeks
    """
    try:
        # Validate Greek type
        valid_greeks = ["delta", "gamma", "theta", "vega", "rho"]
        if greek_type.lower() not in valid_greeks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid Greek type. Must be one of: {', '.join(valid_greeks)}"
            )
        
        breakdown = await calculator.calculate_greeks_breakdown(greek_type.lower(), request)
        return DataResponse(data=breakdown)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error calculating {greek_type} breakdown: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get(
    "/quick/{metric_type}",
    response_model=DataResponse,
    responses={
        200: {"description": "Quick breakdown retrieved successfully"},
        400: {"description": "Bad request", "model": ErrorResponse},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_quick_breakdown(
    metric_type: str,
    grouping: GroupingType = Query(GroupingType.SYMBOL, description="Grouping type for breakdown"),
    sort_by: SortType = Query(SortType.VALUE, description="Sort breakdown by"),
    limit: Optional[int] = Query(10, description="Limit number of results"),
    calculator: BreakdownCalculator = Depends(get_breakdown_calculator)
):
    """
    Get quick breakdown for common metrics
    
    Supported metric_types:
    - total_value: Portfolio total value breakdown
    - total_return: Portfolio total return breakdown
    - long_short: Long vs short positions breakdown
    
    This endpoint provides faster access to common breakdowns with default settings.
    """
    try:
        # Create request with defaults
        request = BreakdownRequest(
            metric_type=metric_type,
            grouping=grouping,
            sort_by=sort_by,
            limit=limit,
            include_calculation_details=False  # Skip for quick response
        )
        
        if metric_type == "total_value":
            breakdown = await calculator.calculate_total_value_breakdown(request)
        elif metric_type == "total_return":
            breakdown = await calculator.calculate_total_return_breakdown(request)
        elif metric_type == "long_short":
            # Special case for long/short breakdown
            request.grouping = GroupingType.POSITION_TYPE
            breakdown = await calculator.calculate_total_value_breakdown(request)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported metric type: {metric_type}"
            )
        
        return DataResponse(data=breakdown)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error calculating quick breakdown for {metric_type}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get(
    "/available-groups",
    response_model=DataResponse,
    responses={
        200: {"description": "Available grouping options retrieved successfully"},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_available_groupings(
    calculator: BreakdownCalculator = Depends(get_breakdown_calculator)
):
    """
    Get available grouping options and metadata
    
    Returns information about available:
    - Grouping types (symbol, strategy, expiry, etc.)
    - Unique values for each grouping type
    - Suggested drill-down paths
    """
    try:
        # Get positions to analyze available groupings
        positions_result = await calculator.rh_service.get_options_positions()
        if not positions_result.get("success", False):
            raise ValueError("Failed to fetch positions data")
        
        positions = positions_result["data"]
        
        # Analyze available groupings
        symbols = sorted(set(pos.get("underlying_symbol", "UNKNOWN") for pos in positions))
        strategies = sorted(set(pos.get("strategy", "UNKNOWN") for pos in positions))
        expiries = sorted(set(pos.get("expiration_date", "unknown") for pos in positions))
        position_types = sorted(set(pos.get("position_type", "unknown") for pos in positions))
        
        available_groupings = {
            "symbol": {
                "display_name": "By Symbol",
                "description": "Group positions by underlying symbol",
                "available_values": symbols,
                "count": len(symbols)
            },
            "strategy": {
                "display_name": "By Strategy", 
                "description": "Group positions by options strategy",
                "available_values": strategies,
                "count": len(strategies)
            },
            "expiry": {
                "display_name": "By Expiration",
                "description": "Group positions by expiration date",
                "available_values": expiries,
                "count": len(expiries)
            },
            "position_type": {
                "display_name": "By Position Type",
                "description": "Group positions by long/short type",
                "available_values": position_types,
                "count": len(position_types)
            }
        }
        
        return DataResponse(data={
            "available_groupings": available_groupings,
            "total_positions": len(positions),
            "suggested_drill_paths": [
                ["symbol", "strategy"],
                ["strategy", "expiry"],
                ["position_type", "symbol"]
            ]
        })
        
    except Exception as e:
        logger.error(f"Error getting available groupings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )