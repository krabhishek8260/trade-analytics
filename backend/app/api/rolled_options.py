"""
Rolled Options API Endpoints

This module provides API endpoints for tracking and analyzing rolled options chains.
Rolled options are positions that have been "rolled" - closed and reopened with
different strikes or expiration dates to manage risk or capture additional premium.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
import logging
import asyncio

from app.core.database import get_db
from app.models.user import User
from app.services.robinhood_service import RobinhoodService
from app.services.rolled_options_service import RolledOptionsService
from app.services.json_rolled_options_service import JsonRolledOptionsService
from app.services.options_order_service import OptionsOrderService
from app.services.rolled_options_chain_detector import RolledOptionsChainDetector
from app.schemas.common import DataResponse, ListResponse, ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rolled-options", tags=["rolled-options"])

def get_robinhood_service() -> RobinhoodService:
    """Dependency to get Robinhood service instance"""
    return RobinhoodService()


def get_optimized_rolled_options_service(rh_service: RobinhoodService = Depends(get_robinhood_service)) -> RolledOptionsService:
    """Dependency to get optimized rolled options service instance"""
    return RolledOptionsService(rh_service)


def get_json_rolled_options_service() -> JsonRolledOptionsService:
    """Dependency to get JSON-based rolled options service instance"""
    return JsonRolledOptionsService()


def get_database_chain_detector(rh_service: RobinhoodService = Depends(get_robinhood_service)) -> RolledOptionsChainDetector:
    """Dependency to get database-first chain detector with strategy code support"""
    options_service = OptionsOrderService(rh_service)
    return RolledOptionsChainDetector(options_service)

async def get_authenticated_user_id(rh_service: RobinhoodService = Depends(get_robinhood_service)) -> str:
    """Get user ID for authenticated Robinhood user, create user if doesn't exist"""
    try:
        # Check if user is authenticated
        if not await rh_service.is_logged_in():
            # Return the real user with data for testing
            return "13461768-f848-4c04-aea2-46817bc9a3a5"
        
        # Get Robinhood user ID from API
        robinhood_user_id = rh_service.get_robinhood_user_id()
        if not robinhood_user_id:
            # Fallback to username-based lookup
            username = rh_service.get_username()
            if not username:
                return "13461768-f848-4c04-aea2-46817bc9a3a5"
            
            # Find or create user in database by username
            async for db in get_db():
                # Try to find existing user by Robinhood username
                stmt = select(User).where(User.robinhood_username == username)
                result = await db.execute(stmt)
                user = result.scalar_one_or_none()
                
                if user:
                    return str(user.id)
                
                # Create new user for this Robinhood account
                import uuid
                from sqlalchemy.dialects.postgresql import insert
                
                new_user_id = str(uuid.uuid4())
                user_record = {
                    "id": new_user_id,
                    "email": f"{username}@robinhood.local",
                    "full_name": f"Robinhood User ({username})",
                    "robinhood_username": username,
                    "robinhood_user_id": None,  # No Robinhood user ID available in fallback
                    "is_active": True
                }
                
                insert_stmt = insert(User).values(user_record)
                upsert_stmt = insert_stmt.on_conflict_do_nothing(index_elements=["id"])
                await db.execute(upsert_stmt)
                await db.commit()
                
                logger.info(f"Created new user {new_user_id} for Robinhood account {username}")
                return new_user_id
        
        # Use Robinhood user ID as the primary identifier
        # Convert to UUID format if needed
        try:
            import uuid
            # Try to parse as UUID first
            user_uuid = uuid.UUID(robinhood_user_id)
            user_id_str = str(user_uuid)
        except ValueError:
            # If not a valid UUID, create a deterministic UUID from the string
            import hashlib
            hash_obj = hashlib.md5(robinhood_user_id.encode())
            user_uuid = uuid.UUID(hash_obj.hexdigest())
            user_id_str = str(user_uuid)
        
        # Find or create user in database by Robinhood user ID
        async for db in get_db():
            # Try to find existing user by Robinhood user ID
            stmt = select(User).where(User.id == user_uuid)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                return user_id_str
            
            # Create new user for this Robinhood account
            username = rh_service.get_username() or "robinhood_user"
            user_record = {
                "id": user_id_str,
                "email": f"{username}@robinhood.local",
                "full_name": f"Robinhood User ({username})",
                "robinhood_username": username,
                "robinhood_user_id": robinhood_user_id,  # Store the original Robinhood user ID
                "is_active": True
            }
            
            insert_stmt = insert(User).values(user_record)
            upsert_stmt = insert_stmt.on_conflict_do_nothing(index_elements=["id"])
            await db.execute(upsert_stmt)
            await db.commit()
            
            logger.info(f"Created new user {user_id_str} for Robinhood user ID {robinhood_user_id}")
            return user_id_str
            
    except Exception as e:
        logger.error(f"Error getting authenticated user: {str(e)}")
        # Fallback to real user on error
        return "13461768-f848-4c04-aea2-46817bc9a3a5"

@router.get(
    "/chains",
    response_model=DataResponse,
    responses={
        200: {"description": "Rolled options chains retrieved successfully"},
        400: {"description": "Bad request", "model": ErrorResponse},
        401: {"description": "Unauthorized", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_rolled_options_chains(
    days_back: int = Query(30, ge=7, le=365, description="Number of days back to analyze (7-365, default 30 for faster loading)"),
    symbol: Optional[str] = Query(None, description="Filter by underlying symbol"),
    status: Optional[str] = Query(None, regex="^(active|closed|expired)$", description="Filter by chain status"),
    min_rolls: Optional[int] = Query(None, ge=1, description="Minimum number of rolls in chain"),
    page: int = Query(1, ge=1, description="Page number for pagination"),
    limit: int = Query(50, ge=10, le=200, description="Number of chains per page"),
    use_json: bool = Query(False, description="Use JSON-based analysis (legacy)"),
    use_database: bool = Query(True, description="Use database-first analysis with strategy codes (recommended)"),
    json_service: JsonRolledOptionsService = Depends(get_json_rolled_options_service),
    optimized_service: RolledOptionsService = Depends(get_optimized_rolled_options_service),
    chain_detector: RolledOptionsChainDetector = Depends(get_database_chain_detector),
    user_id: str = Depends(get_authenticated_user_id)
):
    """
    Get all rolled options chains with detailed analysis
    
    This endpoint identifies options positions that have been "rolled" - where a trader
    closes an existing position and opens a new one with different terms (strike, expiry).
    
    **Chain Identification Logic:**
    1. Analyzes all options orders for the specified period
    2. Groups orders by underlying symbol
    3. Identifies close/open transaction pairs that indicate rolls
    4. Links consecutive rolls into chains
    5. Calculates comprehensive P&L and risk metrics
    
    **Roll Detection Criteria:**
    - Close transaction (BUY TO CLOSE/SELL TO CLOSE) followed by open (SELL TO OPEN/BUY TO OPEN)
    - Same option type (both puts or both calls)
    - Within reasonable time window (0-7 days)
    - Similar contract quantities (within 20% difference)
    
    **Returns:**
    - Complete chain history with all roll transactions
    - Financial analysis: credits collected, debits paid, total P&L
    - Current position status and market data
    - Roll classification: defensive, aggressive, time-based
    - Performance metrics and summary statistics
    """
    try:
        if use_database:
            # Use new database-first analysis with strategy code detection
            logger.info(f"Using database-first chain detection with strategy codes for days_back={days_back}, symbol={symbol}")
            
            try:
                chains = await chain_detector.detect_chains_from_database(
                    user_id=user_id,
                    days_back=days_back,
                    symbol=symbol
                )
                
                # Filter by status if specified
                if status:
                    chains = [chain for chain in chains if chain.get("status", "").lower() == status.lower()]
                
                # Filter by minimum rolls if specified
                if min_rolls:
                    chains = [chain for chain in chains if chain.get("total_orders", 0) >= min_rolls]
                
                # Apply pagination
                total_chains = len(chains)
                start_idx = (page - 1) * limit
                end_idx = start_idx + limit
                paginated_chains = chains[start_idx:end_idx]
                
                result = {
                    "success": True,
                    "message": f"Found {total_chains} chains using database detection",
                    "data": {
                        "chains": paginated_chains,
                        "pagination": {
                            "page": page,
                            "limit": limit,
                            "total": total_chains,
                            "pages": (total_chains + limit - 1) // limit
                        },
                        "summary": {
                            "total_chains": total_chains,
                            "strategy_code_chains": len([c for c in chains if c.get("detection_method") == "strategy_code"]),
                            "heuristic_chains": len([c for c in chains if c.get("detection_method") == "heuristic"]),
                            "form_source_chains": len([c for c in chains if c.get("detection_method") == "form_source"])
                        }
                    }
                }
                
            except Exception as e:
                logger.error(f"Database detection failed: {str(e)}, falling back to legacy service")
                # Fallback to legacy service
                result = await optimized_service.get_rolled_options_chains_optimized(
                    user_id=user_id,
                    days_back=days_back,
                    symbol=symbol,
                    status=status,
                    min_orders=min_rolls * 2 + 1 if min_rolls else 2,
                    page=page,
                    limit=limit,
                    use_cache=True
                )
                
        elif use_json:
            # Use JSON-based analysis for legacy support
            logger.info(f"Using JSON-based rolled options analysis for days_back={days_back}, symbol={symbol}")
            
            try:
                result = await asyncio.wait_for(
                    json_service.get_rolled_chains_from_files(
                        days_back=days_back,
                        symbol=symbol,
                        status=status,
                        min_orders=min_rolls if min_rolls else 2,
                        use_cache=True
                    ),
                    timeout=180.0  # 3 minute timeout for entire JSON analysis
                )
            except asyncio.TimeoutError:
                logger.error("JSON service timed out, falling back to database service")
                # Fallback to database service
                result = await optimized_service.get_rolled_options_chains_optimized(
                    user_id=user_id,
                    days_back=days_back,
                    symbol=symbol,
                    status=status,
                    min_orders=min_rolls * 2 + 1 if min_rolls else 2,
                    page=page,
                    limit=limit,
                    use_cache=True
                )
        else:
            # Fallback to legacy optimized service 
            logger.info(f"Using legacy database-based rolled options service for days_back={days_back}, user={user_id}")
            
            result = await optimized_service.get_rolled_options_chains_optimized(
                user_id=user_id,
                days_back=days_back,
                symbol=symbol,
                status=status,
                min_orders=min_rolls * 2 + 1 if min_rolls else 2,
                page=page,
                limit=limit,
                use_cache=True
            )
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "Failed to analyze rolled options chains")
            )
        
        chains_data = result["data"]
        all_chains = chains_data.get("chains", [])
        
        # Handle pagination for JSON service (which doesn't have built-in pagination)
        if use_json:
            # Calculate pagination
            total_chains = len(all_chains)
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            chains = all_chains[start_idx:end_idx]
            
            total_pages = (total_chains + limit - 1) // limit
            has_next = page < total_pages
            has_prev = page > 1
            
            pagination = {
                "page": page,
                "limit": limit,
                "total_chains": total_chains,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev
            }
        else:
            # Database service already has pagination
            chains = all_chains
            pagination = {
                "page": chains_data.get("current_page", page),
                "limit": chains_data.get("page_size", limit),
                "total_chains": chains_data.get("total_chains", 0),
                "total_pages": chains_data.get("total_pages", 0),
                "has_next": chains_data.get("has_next", False),
                "has_prev": chains_data.get("has_prev", False)
            }
        
        return DataResponse(data={
            "chains": chains,
            "summary": chains_data.get("summary", {}),
            "pagination": pagination,
            "filters_applied": {
                "symbol": symbol,
                "status": status,
                "min_rolls": min_rolls
            },
            "analysis_period_days": days_back,
            "filtered_chains_count": len(chains),
            "performance_optimized": True,
            "analysis_method": "json" if use_json else "database"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving rolled options chains: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get(
    "/chains/{chain_id}",
    response_model=DataResponse,
    responses={
        200: {"description": "Rolled options chain details retrieved successfully"},
        404: {"description": "Chain not found", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_rolled_options_chain_details(
    chain_id: str,
    optimized_service: RolledOptionsService = Depends(get_optimized_rolled_options_service)
):
    """
    Get detailed information about a specific rolled options chain
    
    **Provides:**
    - Complete roll history with transaction details
    - Financial performance analysis
    - Current position status and risk metrics
    - Market data and Greeks (if available)
    - Roll classification and strategy analysis
    """
    try:
        # Use optimized service to get all chains (no pagination)
        result = await optimized_service.get_rolled_options_chains_optimized(
            user_id="13461768-f848-4c04-aea2-46817bc9a3a5", # Real user with data
            days_back=1095, 
            page=1, 
            limit=10000
        )
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve chain data"
            )
        
        chains = result.get("data", {}).get("chains", [])
        chain = next((c for c in chains if c.get("chain_id") == chain_id), None)
        
        if not chain:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chain with ID {chain_id} not found"
            )
        
        # Add additional detailed analysis for this specific chain
        enhanced_chain = await _enhance_chain_details(chain, optimized_service)
        
        return DataResponse(data=enhanced_chain)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving chain details for {chain_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get(
    "/summary",
    response_model=DataResponse,
    responses={
        200: {"description": "Rolled options summary retrieved successfully"},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_rolled_options_summary(
    days_back: int = Query(365, ge=30, le=1095, description="Number of days back to analyze"),
    optimized_service: RolledOptionsService = Depends(get_optimized_rolled_options_service)
):
    """
    Get summary statistics for all rolled options activity
    
    **Summary Includes:**
    - Total number of chains and rolls
    - Active vs closed vs expired chains
    - Total premium collected and P&L
    - Most actively rolled symbols
    - Performance metrics and trends
    """
    try:
        # Use optimized service to get summary from cached data
        result = await optimized_service.get_rolled_options_chains_optimized(
            user_id="13461768-f848-4c04-aea2-46817bc9a3a5",  # Real user for summary
            days_back=days_back,
            page=1,
            limit=10000,  # Get all data for summary
            use_cache=True
        )
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "Failed to analyze rolled options")
            )
        
        return DataResponse(data=result.get("data", {}).get("summary", {}))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving rolled options summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get(
    "/symbols/{symbol}/chains",
    response_model=DataResponse,
    responses={
        200: {"description": "Symbol-specific rolled chains retrieved successfully"},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_symbol_rolled_chains(
    symbol: str,
    days_back: int = Query(365, ge=30, le=1095, description="Number of days back to analyze"),
    status: Optional[str] = Query(None, regex="^(active|closed|expired)$", description="Filter by chain status"),
    optimized_service: RolledOptionsService = Depends(get_optimized_rolled_options_service)
):
    """
    Get all rolled options chains for a specific underlying symbol
    
    **Useful for:**
    - Analyzing rolling behavior on specific stocks
    - Understanding symbol-specific performance
    - Tracking active positions by ticker
    """
    try:
        # Use optimized service with symbol filtering
        result = await optimized_service.get_rolled_options_chains_optimized(
            user_id="13461768-f848-4c04-aea2-46817bc9a3a5",  # Real user
            days_back=days_back,
            symbol=symbol,  # Pass symbol filter to optimized service
            status=status,
            page=1,
            limit=10000,  # Get all data for symbol
            use_cache=True
        )
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "Failed to analyze rolled options")
            )
        
        chains_data = result.get("data", {})
        chains = chains_data.get("chains", [])
        
        # Calculate symbol-specific summary
        symbol_summary = _calculate_symbol_summary(chains, symbol)
        
        return DataResponse(data={
            "symbol": symbol.upper(),
            "chains": chains,
            "summary": symbol_summary,
            "analysis_period_days": days_back
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving rolled chains for {symbol}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

def _calculate_filtered_summary(chains):
    """Calculate summary statistics for filtered chains"""
    if not chains:
        return {
            "total_chains": 0,
            "active_chains": 0,
            "closed_chains": 0,
            "expired_chains": 0,
            "total_rolls": 0,
            "net_premium_collected": 0.0,
            "total_pnl": 0.0,
            "avg_rolls_per_chain": 0.0
        }
    
    active_chains = [c for c in chains if c["status"] == "active"]
    closed_chains = [c for c in chains if c["status"] == "closed"]
    expired_chains = [c for c in chains if c["status"] == "expired"]
    
    total_rolls = sum(c["total_rolls"] for c in chains)
    net_premium = sum(c["net_premium"] for c in chains)
    total_pnl = sum(c["total_pnl"] for c in chains)
    
    return {
        "total_chains": len(chains),
        "active_chains": len(active_chains),
        "closed_chains": len(closed_chains),
        "expired_chains": len(expired_chains),
        "total_rolls": total_rolls,
        "net_premium_collected": net_premium,
        "total_pnl": total_pnl,
        "avg_rolls_per_chain": total_rolls / len(chains) if chains else 0.0
    }

def _calculate_symbol_summary(chains, symbol):
    """Calculate summary statistics for a specific symbol"""
    summary = _calculate_filtered_summary(chains)
    
    if chains:
        # Add symbol-specific metrics
        roll_types = {}
        for chain in chains:
            for roll in chain["rolls"]:
                roll_type = roll["roll_type"]
                roll_types[roll_type] = roll_types.get(roll_type, 0) + 1
        
        summary.update({
            "symbol": symbol.upper(),
            "roll_type_distribution": roll_types,
            "avg_chain_duration_days": _calculate_avg_chain_duration(chains),
            "most_common_roll_type": max(roll_types.items(), key=lambda x: x[1])[0] if roll_types else None
        })
    
    return summary

def _calculate_avg_chain_duration(chains):
    """Calculate average duration of chains in days"""
    durations = []
    for chain in chains:
        if chain["start_date"] and chain["last_roll_date"]:
            start = datetime.fromisoformat(chain["start_date"])
            end = datetime.fromisoformat(chain["last_roll_date"])
            durations.append((end - start).days)
        elif chain["start_date"]:
            start = datetime.fromisoformat(chain["start_date"])
            durations.append((datetime.now() - start).days)
    
    return sum(durations) / len(durations) if durations else 0

async def _enhance_chain_details(chain, rolled_options_service):
    """Add enhanced details for a specific chain"""
    # For now, return the chain as-is
    # Future enhancement: add real-time Greeks, implied volatility, etc.
    enhanced = chain.copy()
    enhanced["detailed_analysis"] = {
        "risk_metrics": {
            "max_roll_credit": max((roll["net_credit"] for roll in chain["rolls"]), default=0),
            "min_roll_credit": min((roll["net_credit"] for roll in chain["rolls"]), default=0),
            "avg_roll_credit": sum(roll["net_credit"] for roll in chain["rolls"]) / len(chain["rolls"]) if chain["rolls"] else 0,
            "roll_frequency_days": _calculate_roll_frequency(chain["rolls"])
        },
        "strategy_analysis": {
            "predominant_roll_direction": _analyze_roll_direction(chain["rolls"]),
            "defensive_rolls": len([r for r in chain["rolls"] if r["roll_type"] == "defensive"]),
            "aggressive_rolls": len([r for r in chain["rolls"] if r["roll_type"] == "aggressive"]),
            "time_rolls": len([r for r in chain["rolls"] if r["roll_type"] == "time"])
        }
    }
    
    return enhanced

def _calculate_roll_frequency(rolls):
    """Calculate average days between rolls"""
    if len(rolls) < 2:
        return 0
    
    intervals = []
    for i in range(1, len(rolls)):
        prev_date = datetime.fromisoformat(rolls[i-1]["roll_date"])
        curr_date = datetime.fromisoformat(rolls[i]["roll_date"])
        intervals.append((curr_date - prev_date).days)
    
    return sum(intervals) / len(intervals) if intervals else 0

def _analyze_roll_direction(rolls):
    """Analyze the predominant direction of rolls (up/down/same)"""
    directions = [roll["strike_direction"] for roll in rolls]
    if not directions:
        return "none"
    
    direction_counts = {"up": 0, "down": 0, "same": 0}
    for direction in directions:
        direction_counts[direction] = direction_counts.get(direction, 0) + 1
    
    return max(direction_counts.items(), key=lambda x: x[1])[0]

@router.get(
    "/symbols",
    response_model=DataResponse,
    responses={
        200: {"description": "Available symbols retrieved successfully"},
        500: {"description": "Internal server error", "model": ErrorResponse}
    }
)
async def get_available_symbols(
    days_back: int = Query(365, ge=30, le=1095, description="Number of days back to analyze for symbols"),
    chain_detector: RolledOptionsChainDetector = Depends(get_database_chain_detector),
    user_id: str = Depends(get_authenticated_user_id)
):
    """
    Get all available symbols that have rolled options chains
    
    **Returns:**
    - List of unique symbols sorted alphabetically
    - Symbol counts and metadata
    """
    try:
        # Get all chains without pagination to get all symbols
        chains = await chain_detector.detect_chains_from_database(
            user_id=user_id,
            days_back=days_back,
            symbol=None  # Get all symbols
        )
        
        # Extract unique symbols and sort them
        symbol_counts = {}
        for chain in chains:
            symbol = chain.get("underlying_symbol", "").upper()
            if symbol:
                symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
        
        symbols = sorted(symbol_counts.keys())
        
        return DataResponse(data={
            "symbols": symbols,
            "symbol_counts": symbol_counts,
            "total_symbols": len(symbols),
            "analysis_period_days": days_back
        })
        
    except Exception as e:
        logger.error(f"Error retrieving available symbols: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
