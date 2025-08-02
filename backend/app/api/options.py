"""
Options API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from datetime import datetime, timedelta
from uuid import UUID
import logging

from app.services.robinhood_service import RobinhoodService
from app.services.options_pnl_service import OptionsPnLService
from app.schemas.common import DataResponse, ErrorResponse, ListResponse
from app.schemas.options import OptionsSummary
from app.core.security import get_current_user_id, ensure_demo_user_exists
from app.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/options", tags=["options"])


def get_robinhood_service() -> RobinhoodService:
    """Dependency to get Robinhood service instance"""
    return RobinhoodService()


@router.get(
    "/positions",
    response_model=ListResponse,
    responses={
        200: {"description": "Options positions retrieved successfully"},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_options_positions(
    underlying_symbol: Optional[str] = Query(None, description="Filter by underlying symbol"),
    option_type: Optional[str] = Query(None, regex="^(call|put)$", description="Filter by option type"),
    strategy: Optional[str] = Query(None, description="Filter by strategy"),
    position_type: Optional[str] = Query(None, regex="^(long|short)$", description="Filter by position type"),
    expiring_days: Optional[int] = Query(None, description="Filter positions expiring within N days"),
    sort_by: Optional[str] = Query("market_value", description="Sort by field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    rh_service: RobinhoodService = Depends(get_robinhood_service)
):
    """Get all options positions with filtering and sorting"""
    try:
        result = await rh_service.get_options_positions()
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "Failed to fetch options positions")
            )
        
        positions = result["data"]
        
        # Apply filters
        if underlying_symbol:
            positions = [pos for pos in positions if pos.get("underlying_symbol", "").upper() == underlying_symbol.upper()]
        
        if option_type:
            positions = [pos for pos in positions if pos.get("option_type", "").lower() == option_type.lower()]
        
        if strategy:
            positions = [pos for pos in positions if strategy.upper() in pos.get("strategy", "").upper()]
        
        if position_type:
            positions = [pos for pos in positions if pos.get("position_type", "").lower() == position_type.lower()]
        
        if expiring_days is not None:
            positions = [pos for pos in positions if pos.get("days_to_expiry", 999) <= expiring_days]
        
        # Sort positions
        reverse = sort_order == "desc"
        valid_sort_fields = [
            "underlying_symbol", "strike_price", "expiration_date", "option_type", 
            "quantity", "average_price", "current_price", "market_value", 
            "total_return", "percent_change", "days_to_expiry"
        ]
        
        if sort_by in valid_sort_fields:
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
        logger.error(f"Error fetching options positions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/orders",
    response_model=ListResponse,
    responses={
        200: {"description": "Options orders retrieved successfully"},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_options_orders(
    limit: int = Query(50, ge=1, le=500, description="Number of orders to retrieve"),
    days_back: Optional[int] = Query(None, description="Get orders from N days back"),
    underlying_symbol: Optional[str] = Query(None, description="Filter by underlying symbol"),
    state: Optional[str] = Query(None, description="Filter by order state"),
    strategy: Optional[str] = Query(None, description="Filter by strategy"),
    option_type: Optional[str] = Query(None, regex="^(call|put)$", description="Filter by option type (call/put)"),
    transaction_side: Optional[str] = Query(None, regex="^(buy|sell)$", description="Filter by transaction side (buy/sell)"),
    rh_service: RobinhoodService = Depends(get_robinhood_service)
):
    """Get options orders with legs and executions"""
    try:
        # Calculate since_time if days_back is provided
        since_time = None
        if days_back is not None:
            since_time = datetime.now() - timedelta(days=days_back)
        
        result = await rh_service.get_options_orders(limit=limit, since_time=since_time)
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "Failed to fetch options orders")
            )
        
        orders = result["data"]
        
        # Apply filters
        if underlying_symbol:
            orders = [order for order in orders if order.get("underlying_symbol", "").upper() == underlying_symbol.upper()]
        
        if state:
            orders = [order for order in orders if order.get("state", "").lower() == state.lower()]
        
        if strategy:
            orders = [order for order in orders if strategy.upper() in order.get("strategy", "").upper()]
        
        if option_type:
            orders = [order for order in orders if order.get("option_type", "").lower() == option_type.lower()]
        
        if transaction_side:
            orders = [order for order in orders if order.get("transaction_side", "").lower() == transaction_side.lower()]
        
        return ListResponse(
            data=orders,
            count=len(orders),
            total=len(orders)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching options orders: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/orders/{order_id}",
    response_model=DataResponse,
    responses={
        200: {"description": "Options order retrieved successfully"},
        404: {"description": "Order not found", "model": ErrorResponse},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_options_order(
    order_id: str,
    rh_service: RobinhoodService = Depends(get_robinhood_service)
):
    """Get specific options order by ID with full details"""
    try:
        result = await rh_service.get_options_orders(limit=1000)  # Get more orders to find the specific one
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "Failed to fetch options orders")
            )
        
        orders = result["data"]
        
        # Find order by ID
        order = next(
            (order for order in orders if order.get("order_id") == order_id),
            None
        )
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No order found with ID {order_id}"
            )
        
        return DataResponse(data=order)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching options order {order_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/summary",
    response_model=DataResponse,
    responses={
        200: {"description": "Options summary retrieved successfully"},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_options_summary(
    rh_service: RobinhoodService = Depends(get_robinhood_service)
):
    """Get comprehensive options portfolio summary with enhanced P&L analytics"""
    try:
        # Get enhanced P&L summary
        pnl_result = await rh_service.calculate_options_pnl_summary()
        if not pnl_result.get("success", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=pnl_result.get("message", "Failed to calculate P&L summary")
            )
        
        pnl_data = pnl_result["data"]
        
        # Get current positions for additional metrics
        result = await rh_service.get_options_positions()
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "Failed to fetch options positions")
            )
        
        positions = result["data"]
        
        # Calculate portfolio value metrics with proper options portfolio accounting
        total_long_value = 0
        total_short_value = 0
        total_cost = 0
        
        for pos in positions:
            market_value = pos.get("market_value", 0)
            cost = pos.get("total_cost", 0)
            position_type = pos.get("position_type", "")
            
            if position_type == "long":
                # Long positions: market_value is an asset (what you can sell for)
                total_long_value += market_value
                total_cost += abs(cost)  # Cost is positive (money paid)
            else:
                # Short positions: market_value is a liability (cost to close)
                total_short_value += market_value
                total_cost += abs(cost)  # Cost basis (absolute value)
        
        # Net portfolio value = Long assets - Short liabilities
        total_value = total_long_value - total_short_value
        
        logger.info(f"Enhanced Options Portfolio Calculation:")
        logger.info(f"  Long positions value (assets): ${total_long_value:,.2f}")
        logger.info(f"  Short positions value (liabilities): ${total_short_value:,.2f}")
        logger.info(f"  Net portfolio value: ${total_value:,.2f}")
        logger.info(f"  Total P&L (realized + unrealized): ${pnl_data['total_pnl']:,.2f}")
        logger.info(f"  Realized P&L: ${pnl_data['realized_pnl']:,.2f}")
        logger.info(f"  Unrealized P&L: ${pnl_data['unrealized_pnl']:,.2f}")
        
        # Strategy breakdown
        long_positions = sum(1 for pos in positions if pos.get("position_type") == "long")
        short_positions = sum(1 for pos in positions if pos.get("position_type") == "short")
        calls_count = sum(1 for pos in positions if pos.get("option_type", "").lower() == "call")
        puts_count = sum(1 for pos in positions if pos.get("option_type", "").lower() == "put")
        
        # Expiry analysis
        expiring_this_week = sum(1 for pos in positions if pos.get("days_to_expiry", 999) <= 7)
        expiring_this_month = sum(1 for pos in positions if pos.get("days_to_expiry", 999) <= 30)
        
        # Strategy analysis
        strategies = {}
        for pos in positions:
            strategy = pos.get("strategy", "UNKNOWN")
            if strategy not in strategies:
                strategies[strategy] = {"count": 0, "value": 0, "return": 0}
            strategies[strategy]["count"] += 1
            strategies[strategy]["value"] += pos.get("market_value", 0)
            strategies[strategy]["return"] += pos.get("total_return", 0)
        
        # Enhanced summary with P&L analytics
        summary = {
            # Portfolio values
            "total_positions": len(positions),
            "total_value": total_value,
            "total_cost": total_cost,
            "total_return": pnl_data["unrealized_pnl"],  # Current unrealized P&L
            "total_return_percent": (pnl_data["unrealized_pnl"] / total_cost * 100) if total_cost > 0 else 0,
            
            # Enhanced P&L Analytics
            "pnl_analytics": {
                "total_pnl": pnl_data["total_pnl"],
                "realized_pnl": pnl_data["realized_pnl"],
                "unrealized_pnl": pnl_data["unrealized_pnl"],
                "total_trades": pnl_data["total_trades"],
                "realized_trades": pnl_data["realized_trades"],
                "open_positions": pnl_data["open_positions"],
                "win_rate": pnl_data["win_rate"],
                "largest_winner": pnl_data["largest_winner"],
                "largest_loser": pnl_data["largest_loser"],
                "avg_trade_pnl": pnl_data["avg_trade_pnl"]
            },
            
            # Yearly performance breakdown
            "yearly_performance": pnl_data["realized_breakdown"],
            
            # Top performing symbols
            "top_symbols": pnl_data["symbol_breakdown"][:10],  # Top 10 symbols
            
            # Breakdown by strategy
            "long_positions": long_positions,
            "short_positions": short_positions,
            "calls_count": calls_count,
            "puts_count": puts_count,
            
            # Expiry analysis
            "expiring_this_week": expiring_this_week,
            "expiring_this_month": expiring_this_month,
            
            # Performance (now using enhanced P&L data)
            "winners": pnl_data["winning_trades"],
            "losers": pnl_data["losing_trades"],
            "win_rate": pnl_data["win_rate"],
            
            # Strategy breakdown
            "strategies": strategies,
            
            "last_updated": datetime.utcnow(),
            "positions": positions
        }
        
        return DataResponse(data=summary)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating enhanced options summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/pnl/summary",
    response_model=DataResponse,
    responses={
        200: {"description": "P&L summary retrieved successfully"},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_pnl_summary(
    current_user_id: UUID = Depends(get_current_user_id),
    db = Depends(get_db)
):
    """Get comprehensive P&L summary with realized and unrealized breakdown"""
    try:
        from app.services.options_pnl_service import options_pnl_service
        
        # Ensure demo user exists for development/testing
        await ensure_demo_user_exists(db)
        
        result = await options_pnl_service.calculate_total_pnl(current_user_id)
        
        return DataResponse(data=result)
        
    except Exception as e:
        logger.error(f"Error fetching P&L summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/pnl/by-year",
    response_model=DataResponse,
    responses={
        200: {"description": "Yearly P&L breakdown retrieved successfully"},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_yearly_pnl(
    start_year: Optional[int] = Query(None, description="Start year for analysis"),
    end_year: Optional[int] = Query(None, description="End year for analysis"),
    current_user_id: UUID = Depends(get_current_user_id),
    db = Depends(get_db)
):
    """Get year-over-year P&L breakdown"""
    try:
        from app.services.options_pnl_service import options_pnl_service
        
        # Ensure demo user exists for development/testing
        await ensure_demo_user_exists(db)
        
        result = await options_pnl_service.calculate_yearly_pnl(current_user_id, start_year, end_year)
        
        return DataResponse(data=result)
        
    except Exception as e:
        logger.error(f"Error fetching yearly P&L: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/pnl/by-symbol",
    response_model=DataResponse,
    responses={
        200: {"description": "Symbol P&L breakdown retrieved successfully"},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_symbol_pnl(
    year: Optional[int] = Query(None, description="Filter by specific year"),
    limit: Optional[int] = Query(20, ge=1, le=100, description="Number of symbols to return"),
    sort_by: str = Query("total_pnl", description="Field to sort by (total_pnl, win_rate, total_trades)"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    current_user_id: UUID = Depends(get_current_user_id),
    db = Depends(get_db)
):
    """Get symbol-level P&L breakdown"""
    try:
        from app.services.options_pnl_service import options_pnl_service
        
        # Ensure demo user exists for development/testing
        await ensure_demo_user_exists(db)
        
        result = await options_pnl_service.calculate_symbol_pnl(
            current_user_id, year, limit, sort_by, sort_order
        )
        
        return DataResponse(data=result)
        
    except Exception as e:
        logger.error(f"Error fetching symbol P&L: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/pnl/trades/{symbol}",
    response_model=DataResponse,
    responses={
        200: {"description": "Symbol trades retrieved successfully"},
        404: {"description": "No trades found for symbol", "model": ErrorResponse},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_symbol_trades(
    symbol: str,
    year: Optional[int] = Query(None, description="Filter by specific year"),
    trade_type: Optional[str] = Query(None, regex="^(realized|unrealized)$", description="Filter by trade type"),
    current_user_id: UUID = Depends(get_current_user_id),
    db = Depends(get_db)
):
    """Get individual trades for a specific symbol"""
    try:
        from app.services.options_pnl_service import options_pnl_service
        
        # Ensure demo user exists for development/testing
        await ensure_demo_user_exists(db)
        
        result = await options_pnl_service.get_symbol_trades(current_user_id, symbol, year, trade_type)
        
        if not result["trades"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No trades found for symbol {symbol.upper()}"
            )
        
        return DataResponse(data=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching trades for symbol {symbol}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post(
    "/pnl/process",
    response_model=DataResponse,
    responses={
        200: {"description": "P&L processing triggered successfully"},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def trigger_pnl_processing(
    force: bool = Query(False, description="Force recalculation even if cache is fresh"),
    current_user_id: UUID = Depends(get_current_user_id),
    db = Depends(get_db),
    rh_service: RobinhoodService = Depends(get_robinhood_service)
):
    """Trigger background P&L processing for the current user"""
    try:
        from app.services.options_pnl_background_service import pnl_background_service
        
        # Ensure demo user exists for testing
        await ensure_demo_user_exists(db)
        
        result = await pnl_background_service.trigger_user_pnl_processing(current_user_id)
        
        return DataResponse(data=result)
        
    except Exception as e:
        logger.error(f"Error triggering P&L processing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/pnl/status",
    response_model=DataResponse,
    responses={
        200: {"description": "P&L processing status retrieved successfully"},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_pnl_processing_status(
    current_user_id: UUID = Depends(get_current_user_id),
    db = Depends(get_db),
    rh_service: RobinhoodService = Depends(get_robinhood_service)
):
    """Get P&L processing status for the current user"""
    try:
        from app.services.options_pnl_background_service import pnl_background_service
        
        # Ensure demo user exists for testing
        await ensure_demo_user_exists(db)
        
        cached_data = await pnl_background_service.get_cached_pnl(current_user_id)
        
        if cached_data:
            status_info = cached_data["calculation_info"]
        else:
            status_info = {
                "status": "pending",
                "message": "No P&L processing has been initiated yet"
            }
        
        return DataResponse(data=status_info)
        
    except Exception as e:
        logger.error(f"Error getting P&L processing status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/analysis/performance",
    response_model=DataResponse,
    responses={
        200: {"description": "Ticker performance analysis retrieved successfully"},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_ticker_performance_analysis(
    rh_service: RobinhoodService = Depends(get_robinhood_service)
):
    """Get comprehensive performance analysis by ticker"""
    try:
        result = await rh_service.get_ticker_performance_analysis()
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "Failed to analyze ticker performance")
            )
        
        return DataResponse(data=result["data"])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching ticker performance analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/analysis/{underlying_symbol}",
    response_model=DataResponse,
    responses={
        200: {"description": "Options analysis retrieved successfully"},
        404: {"description": "No positions found for symbol", "model": ErrorResponse},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_options_analysis(
    underlying_symbol: str,
    rh_service: RobinhoodService = Depends(get_robinhood_service)
):
    """Get detailed options analysis for a specific underlying symbol"""
    try:
        result = await rh_service.get_options_positions()
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "Failed to fetch options positions")
            )
        
        all_positions = result["data"]
        
        # Filter positions for the specific symbol
        positions = [pos for pos in all_positions if pos.get("underlying_symbol", "").upper() == underlying_symbol.upper()]
        
        if not positions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No options positions found for {underlying_symbol}"
            )
        
        # Analyze positions
        total_value = sum(pos.get("market_value", 0) for pos in positions)
        total_return = sum(pos.get("total_return", 0) for pos in positions)
        
        calls = [pos for pos in positions if pos.get("option_type", "").lower() == "call"]
        puts = [pos for pos in positions if pos.get("option_type", "").lower() == "put"]
        
        long_positions = [pos for pos in positions if pos.get("position_type") == "long"]
        short_positions = [pos for pos in positions if pos.get("position_type") == "short"]
        
        # Expiry breakdown
        expiry_breakdown = {}
        for pos in positions:
            exp_date = pos.get("expiration_date", "Unknown")
            if exp_date not in expiry_breakdown:
                expiry_breakdown[exp_date] = {"count": 0, "value": 0, "return": 0}
            expiry_breakdown[exp_date]["count"] += 1
            expiry_breakdown[exp_date]["value"] += pos.get("market_value", 0)
            expiry_breakdown[exp_date]["return"] += pos.get("total_return", 0)
        
        # Strike price analysis
        strikes = sorted(set(pos.get("strike_price", 0) for pos in positions))
        
        analysis = {
            "symbol": underlying_symbol.upper(),
            "total_positions": len(positions),
            "total_value": total_value,
            "total_return": total_return,
            "total_return_percent": (total_return / abs(sum(pos.get("total_cost", 0) for pos in positions)) * 100) if positions else 0,
            
            # Breakdown
            "calls_count": len(calls),
            "puts_count": len(puts),
            "long_count": len(long_positions),
            "short_count": len(short_positions),
            
            # Analysis
            "expiry_breakdown": expiry_breakdown,
            "strike_prices": strikes,
            "strategies": list(set(pos.get("strategy", "UNKNOWN") for pos in positions)),
            
            # Risk metrics
            "net_delta_equivalent": 0,  # To be calculated when Greeks are available
            "days_to_nearest_expiry": min((pos.get("days_to_expiry", 999) for pos in positions), default=0),
            
            "positions": positions
        }
        
        return DataResponse(data=analysis)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing options for {underlying_symbol}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/greeks",
    response_model=DataResponse,
    responses={
        200: {"description": "Portfolio Greeks retrieved successfully"},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_portfolio_greeks(
    rh_service: RobinhoodService = Depends(get_robinhood_service)
):
    """Get portfolio-level Greeks exposure and risk metrics"""
    try:
        result = await rh_service.get_portfolio_greeks()
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "Failed to calculate portfolio Greeks")
            )
        
        return DataResponse(data=result["data"])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching portfolio Greeks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/pnl/recalculate",
    response_model=DataResponse,
    summary="Force P&L recalculation",
    description="Force a fresh P&L calculation by invalidating cache",
    responses={
        200: {"description": "Recalculation triggered successfully"},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def force_pnl_recalculation(
    current_user_id: UUID = Depends(get_current_user_id),
    db = Depends(get_db)
):
    """Force P&L recalculation for debugging"""
    try:
        await ensure_demo_user_exists(db)
        
        # Get P&L service and force recalculation
        pnl_service = OptionsPnLService()
        result = await pnl_service.invalidate_cache_and_recalculate(current_user_id)
        
        return DataResponse(data=result)
        
    except Exception as e:
        logger.error(f"Error forcing P&L recalculation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )