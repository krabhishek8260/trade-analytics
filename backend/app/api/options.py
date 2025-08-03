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
    include_chains: bool = Query(False, description="Include rolled options chain information for positions"),
    rh_service: RobinhoodService = Depends(get_robinhood_service),
    db = Depends(get_db)
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
        
        # Optionally enhance positions with chain information
        if include_chains:
            try:
                # Use the database service directly to get enhanced chains
                from sqlalchemy import select
                from app.models.rolled_options_chain import RolledOptionsChain
                # Use the same user ID as rolled-options-v2 API for consistency
                USER_ID = "123e4567-e89b-12d3-a456-426614174000"
                
                try:
                    # Get chains directly from database
                    query = select(RolledOptionsChain).where(
                        RolledOptionsChain.user_id == USER_ID,
                        RolledOptionsChain.status == "active"
                    ).limit(1000)
                    
                    result = await db.execute(query)
                    chain_records = result.scalars().all()
                    
                    # Convert to API format similar to rolled_options_v2.py
                    chains = []
                    for record in chain_records:
                        chain_data = record.chain_data or {}
                        
                        # Determine latest position for active chains
                        latest_position = None
                        if record.status == "active":
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
                        
                        chain_api = {
                            "chain_id": record.chain_id,
                            "underlying_symbol": record.underlying_symbol,
                            "status": record.status,
                            "roll_count": record.roll_count,
                            "total_pnl": float(record.total_pnl or 0),
                            "net_premium": float(record.net_premium or 0),
                            "start_date": record.start_date.isoformat() if record.start_date else None,
                            "total_orders": record.total_orders,
                            "latest_position": latest_position
                        }
                        chains.append(chain_api)
                    
                    chains_result = {
                        "success": True,
                        "data": {"chains": chains}
                    }
                    
                except Exception as e:
                    logger.warning(f"Failed to fetch enhanced chains from database: {str(e)}")
                    chains_result = {"success": False}
                
                if chains_result.get("success", False):
                    chains_data = chains_result["data"]
                    chains = chains_data.get("chains", [])
                    
                    logger.info(f"Chain lookup: Found {len(chains)} chains for enhancement")
                    
                    # Create lookup map for positions to chain info
                    position_chain_map = {}
                    logger.info(f"Starting chain position mapping process...")
                    
                    for chain in chains:
                        # Only consider active chains for position matching
                        if chain.get("status") != "active":
                            continue
                            
                        # Get the latest position from the enhanced chain data
                        chain_data = chain.get("chain_data", {})
                        latest_position = chain_data.get("latest_position") or chain.get("latest_position")
                        
                        if latest_position:
                            # Create a key to match with current positions (normalize option_type to lowercase)
                            option_type = str(latest_position['option_type']).lower()
                            key = f"{chain['underlying_symbol']}_{latest_position['strike_price']}_{latest_position['expiration_date']}_{option_type}"
                            
                            logger.info(f"Adding chain {chain['chain_id']} to position map with key: {key}")
                            
                            position_chain_map[key] = {
                                "chain_id": chain["chain_id"],
                                "is_latest_in_chain": True,
                                "chain_roll_count": chain.get("roll_count", 0),
                                "chain_total_pnl": chain.get("total_pnl", 0),
                                "chain_status": chain.get("status", "unknown"),
                                "chain_net_premium": chain.get("net_premium", 0),
                                "chain_start_date": chain.get("start_date"),
                                "chain_total_orders": chain.get("total_orders", 0)
                            }
                    
                    # Enhance positions with chain information
                    for position in positions:
                        # Normalize option_type to lowercase for consistent matching
                        pos_option_type = str(position.get('option_type', '')).lower()
                        pos_key = f"{position.get('underlying_symbol')}_{position.get('strike_price')}_{position.get('expiration_date')}_{pos_option_type}"
                        
                        if pos_key in position_chain_map:
                            logger.info(f"Found chain match for position: {pos_key}")
                            position.update(position_chain_map[pos_key])
                        else:
                            # Mark as not part of a chain
                            position["chain_id"] = None
                            position["is_latest_in_chain"] = False
                    
                    logger.info(f"Chain enhancement complete. Enhanced {sum(1 for p in positions if p.get('chain_id'))} out of {len(positions)} positions")
                
            except Exception as e:
                logger.warning(f"Failed to fetch chain information: {str(e)}")
                # Continue without chain info if there's an error
        
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


@router.post("/positions/refresh",
    response_model=DataResponse,
    summary="Force options positions refresh",
    description="Clear cache and force fresh options positions fetch",
    responses={
        200: {"description": "Positions refresh triggered successfully"},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def force_positions_refresh(
    rh_service: RobinhoodService = Depends(get_robinhood_service)
):
    """Force fresh options positions fetch by clearing cache"""
    try:
        # Clear the options positions cache
        from app.core.redis import cache
        cache_key = "options:positions"
        await cache.delete(cache_key)
        
        # Force a fresh fetch
        result = await rh_service.get_options_positions()
        
        return DataResponse(data={
            "success": True,
            "message": "Options positions cache cleared and refreshed",
            "positions_count": len(result.get("data", [])),
            "fresh_data": result.get("success", False)
        })
        
    except Exception as e:
        logger.error(f"Error forcing positions refresh: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/history",
    response_model=ListResponse,
    responses={
        200: {"description": "Closed options history retrieved successfully"},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_closed_options_history(
    limit: int = Query(50, ge=1, le=500, description="Number of closed positions to retrieve"),
    days_back: Optional[int] = Query(365, description="Get closed positions from N days back"),
    underlying_symbol: Optional[str] = Query(None, description="Filter by underlying symbol"),
    strategy: Optional[str] = Query(None, description="Filter by strategy"),
    option_type: Optional[str] = Query(None, regex="^(call|put)$", description="Filter by option type"),
    sort_by: Optional[str] = Query("close_date", description="Sort by field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    include_chains: bool = Query(True, description="Include chain information for closed positions"),
    current_user_id: UUID = Depends(get_current_user_id),
    db = Depends(get_db),
    rh_service: RobinhoodService = Depends(get_robinhood_service)
):
    """Get closed options positions by comparing filled orders with current open positions"""
    try:
        # Ensure demo user exists for development/testing
        await ensure_demo_user_exists(db)
        
        # Get all filled orders
        since_time = None
        if days_back is not None:
            since_time = datetime.now() - timedelta(days=days_back)
        
        orders_result = await rh_service.get_options_orders(limit=1000, since_time=since_time)
        if not orders_result.get("success", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=orders_result.get("message", "Failed to fetch options orders")
            )
        
        all_orders = orders_result["data"]
        filled_orders = [order for order in all_orders if order.get("state") == "filled"]
        
        # Get current open positions
        positions_result = await rh_service.get_options_positions()
        if not positions_result.get("success", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=positions_result.get("message", "Failed to fetch current positions")
            )
        
        current_positions = positions_result["data"]
        
        # Create a set of currently open position keys (symbol + strike + expiry + type)
        open_position_keys = set()
        for pos in current_positions:
            key = f"{pos.get('underlying_symbol')}_{pos.get('strike_price')}_{pos.get('expiration_date')}_{pos.get('option_type', '').lower()}"
            open_position_keys.add(key)
        
        # Group orders by position key to identify opening/closing pairs
        position_orders = {}
        for order in filled_orders:
            key = f"{order.get('underlying_symbol')}_{order.get('strike_price')}_{order.get('expiration_date')}_{order.get('option_type', '').lower()}"
            
            if key not in position_orders:
                position_orders[key] = []
            position_orders[key].append(order)
        
        # Identify closed positions (positions that were opened but are no longer current)
        closed_positions = []
        
        logger.info(f"Found {len(position_orders)} unique positions from orders")
        logger.info(f"Found {len(open_position_keys)} currently open positions")
        
        for position_key, orders in position_orders.items():
            # Skip if this position is still open
            if position_key in open_position_keys:
                logger.debug(f"Skipping {position_key} - still open")
                continue
            
            logger.info(f"Found closed position: {position_key}")
            
            # Sort orders by date to get chronological order
            orders.sort(key=lambda x: x.get('created_at', ''))
            
            # Find opening and closing orders
            opening_orders = [order for order in orders if order.get('position_effect') == 'open']
            closing_orders = [order for order in orders if order.get('position_effect') == 'close']
            
            if not opening_orders:
                continue  # No opening order, skip
            
            # Get the first opening order for position details
            opening_order = opening_orders[0]
            
            # Calculate total opening premium
            opening_premium = 0
            for order in opening_orders:
                premium = order.get('processed_premium', 0)
                if order.get('processed_premium_direction') == 'credit':
                    opening_premium += premium
                else:
                    opening_premium -= premium
            
            # Calculate total closing premium
            closing_premium = 0
            close_date = None
            for order in closing_orders:
                premium = order.get('processed_premium', 0)
                if order.get('processed_premium_direction') == 'credit':
                    closing_premium += premium
                else:
                    closing_premium -= premium
                close_date = order.get('updated_at', order.get('created_at'))
            
            # If no explicit closing orders, assume expired worthless or assigned
            if not closing_orders:
                close_date = opening_order.get('expiration_date')
                # For short positions, expiring worthless is good (keep the premium)
                # For long positions, expiring worthless is bad (lose the premium)
                if opening_order.get('transaction_side') == 'sell':
                    # Short position expired worthless - keep the credit
                    closing_premium = 0
                else:
                    # Long position expired worthless - lose the debit paid
                    closing_premium = 0
            
            # Calculate total P&L
            total_pnl = opening_premium + closing_premium
            
            # Calculate days held
            days_held = None
            start_date = opening_order.get('created_at')
            if start_date and close_date:
                try:
                    start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    if close_date.endswith('Z') or '+' in close_date:
                        close_dt = datetime.fromisoformat(close_date.replace('Z', '+00:00'))
                    else:
                        # Assume it's just a date for expiration
                        close_dt = datetime.strptime(close_date, '%Y-%m-%d')
                    days_held = (close_dt - start_dt).days
                except:
                    pass
            
            # Create closed position entry
            closed_position = {
                "underlying_symbol": opening_order.get('underlying_symbol'),
                "strike_price": opening_order.get('strike_price'),
                "expiration_date": opening_order.get('expiration_date'),
                "option_type": opening_order.get('option_type'),
                "strategy": opening_order.get('strategy', opening_order.get('opening_strategy', 'UNKNOWN')),
                "initial_strategy": opening_order.get('opening_strategy', opening_order.get('strategy', 'UNKNOWN')),
                "start_date": start_date,
                "close_date": close_date,
                "opening_premium": opening_premium,
                "closing_premium": closing_premium,
                "net_premium": opening_premium,
                "total_pnl": total_pnl,
                "total_orders": len(orders),
                "opening_orders": len(opening_orders),
                "closing_orders": len(closing_orders),
                "days_held": days_held,
                "win_loss": "win" if total_pnl > 0 else "loss",
                "position_type": "short" if opening_order.get('transaction_side') == 'sell' else "long",
                "closed_explicitly": len(closing_orders) > 0,
                "chain_id": opening_order.get('chain_id'),
                
                # For backwards compatibility with frontend
                "final_strike": opening_order.get('strike_price'),
                "final_expiry": opening_order.get('expiration_date'),
                "final_option_type": opening_order.get('option_type'),
                "total_credits_collected": max(0, opening_premium) if opening_premium > 0 else 0,
                "total_debits_paid": abs(min(0, opening_premium)) if opening_premium < 0 else 0,
                "enhanced_chain": False,
                "chain_type": "regular"
            }
            
            closed_positions.append(closed_position)
        
        # Apply filters
        if underlying_symbol:
            closed_positions = [pos for pos in closed_positions if pos.get("underlying_symbol", "").upper() == underlying_symbol.upper()]
        
        if strategy:
            closed_positions = [pos for pos in closed_positions if strategy.upper() in pos.get("strategy", "").upper()]
        
        if option_type:
            closed_positions = [pos for pos in closed_positions if pos.get("option_type", "").lower() == option_type.lower()]
        
        # Sort positions
        reverse = sort_order == "desc"
        valid_sort_fields = [
            "underlying_symbol", "close_date", "start_date", "total_pnl", 
            "net_premium", "total_orders", "days_held", "strike_price"
        ]
        
        if sort_by in valid_sort_fields:
            try:
                closed_positions.sort(
                    key=lambda x: x.get(sort_by, 0) if isinstance(x.get(sort_by, 0), (int, float)) else str(x.get(sort_by, "")),
                    reverse=reverse
                )
            except Exception as e:
                logger.warning(f"Error sorting closed positions by {sort_by}: {str(e)}")
        
        # Apply limit
        if limit and len(closed_positions) > limit:
            closed_positions = closed_positions[:limit]
        
        return ListResponse(
            data=closed_positions,
            count=len(closed_positions),
            total=len(closed_positions)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching closed options history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )