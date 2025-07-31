"""
Rolled Options Debug API Endpoints

This module provides debugging endpoints to investigate gaps in rolled options identification.
"""

from fastapi import APIRouter, Depends, Query
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import logging

from app.services.robinhood_service import RobinhoodService
from app.services.rolled_options_service import RolledOptionsService
from app.schemas.common import DataResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rolled-options-debug", tags=["rolled-options-debug"])

async def get_robinhood_service() -> RobinhoodService:
    """Dependency to get RobinhoodService instance"""
    return RobinhoodService()

@router.get("/analyze-robinhood-fields")
async def analyze_robinhood_fields(
    symbol: str = Query(default="ASTS", description="Symbol to analyze"),
    days_back: int = Query(default=365, description="Days to look back for orders"),
    rh_service: RobinhoodService = Depends(get_robinhood_service)
):
    """
    Analyze Robinhood API fields to understand roll identification
    """
    try:
        # Get all orders for the symbol
        since_time = datetime.now() - timedelta(days=days_back)
        orders_response = await rh_service.get_options_orders(
            limit=1000,
            since_time=since_time
        )
        
        if not orders_response["success"]:
            return DataResponse(
                success=False,
                message=f"Failed to fetch {symbol} orders",
                data={"error": orders_response.get("message", "Unknown error")}
            )
        
        all_orders = orders_response["data"]
        
        # Filter for the specific symbol
        symbol_orders = []
        for order in all_orders:
            # Check both underlying_symbol and chain_symbol fields
            order_symbol = order.get("underlying_symbol", "") or order.get("chain_symbol", "")
            if order_symbol.upper() == symbol.upper():
                symbol_orders.append(order)
        
        analysis = {
            "symbol": symbol,
            "total_orders": len(symbol_orders),
            "chain_id_analysis": {},
            "strategy_analysis": {
                "orders_with_both_strategies": [],
                "orders_with_closing_only": [],
                "orders_with_opening_only": [],
                "unique_closing_strategies": set(),
                "unique_opening_strategies": set()
            },
            "potential_rolls_by_chain_id": {},
            "potential_rolls_by_strategy": []
        }
        
        # Group by chain_id to see if related orders share the same chain_id
        chain_groups = {}
        for order in symbol_orders:
            chain_id = order.get("chain_id")
            if chain_id:
                if chain_id not in chain_groups:
                    chain_groups[chain_id] = []
                chain_groups[chain_id].append({
                    "order_id": order.get("id"),
                    "created_at": order.get("created_at"),
                    "strategy": order.get("strategy"),
                    "closing_strategy": order.get("closing_strategy"),
                    "opening_strategy": order.get("opening_strategy"),
                    "state": order.get("state"),
                    "direction": order.get("direction"),
                    "underlying_symbol": order.get("underlying_symbol"),
                    "strike_price": order.get("strike_price"),
                    "expiration_date": order.get("expiration_date"),
                    "quantity": order.get("quantity")
                })
        
        # Analyze chain_id groupings
        for chain_id, orders in chain_groups.items():
            if len(orders) > 1:
                analysis["potential_rolls_by_chain_id"][chain_id] = {
                    "order_count": len(orders),
                    "orders": sorted(orders, key=lambda x: x["created_at"]),
                    "time_span_hours": 0
                }
                
                # Calculate time span
                if len(orders) >= 2:
                    try:
                        first_time = datetime.fromisoformat(orders[0]["created_at"].replace('Z', '+00:00'))
                        last_time = datetime.fromisoformat(orders[-1]["created_at"].replace('Z', '+00:00'))
                        time_span = (last_time - first_time).total_seconds() / 3600
                        analysis["potential_rolls_by_chain_id"][chain_id]["time_span_hours"] = time_span
                    except:
                        pass
        
        # Analyze strategy combinations
        for order in symbol_orders:
            closing_strategy = order.get("closing_strategy")
            opening_strategy = order.get("opening_strategy")
            
            order_summary = {
                "order_id": order.get("id"),
                "chain_id": order.get("chain_id"),
                "created_at": order.get("created_at"),
                "strategy": order.get("strategy"),
                "closing_strategy": closing_strategy,
                "opening_strategy": opening_strategy,
                "state": order.get("state"),
                "direction": order.get("direction"),
                "strike_price": order.get("strike_price"),
                "expiration_date": order.get("expiration_date"),
                "quantity": order.get("quantity")
            }
            
            if closing_strategy and opening_strategy:
                analysis["strategy_analysis"]["orders_with_both_strategies"].append(order_summary)
                analysis["strategy_analysis"]["potential_rolls_by_strategy"].append(order_summary)
            elif closing_strategy:
                analysis["strategy_analysis"]["orders_with_closing_only"].append(order_summary)
            elif opening_strategy:
                analysis["strategy_analysis"]["orders_with_opening_only"].append(order_summary)
            
            if closing_strategy:
                analysis["strategy_analysis"]["unique_closing_strategies"].add(closing_strategy)
            if opening_strategy:
                analysis["strategy_analysis"]["unique_opening_strategies"].add(opening_strategy)
        
        # Convert sets to lists for JSON serialization
        analysis["strategy_analysis"]["unique_closing_strategies"] = list(analysis["strategy_analysis"]["unique_closing_strategies"])
        analysis["strategy_analysis"]["unique_opening_strategies"] = list(analysis["strategy_analysis"]["unique_opening_strategies"])
        
        return DataResponse(
            success=True,
            message=f"Analyzed {len(symbol_orders)} {symbol} orders using Robinhood fields",
            data=analysis
        )
        
    except Exception as e:
        logger.error(f"Error analyzing Robinhood fields: {str(e)}", exc_info=True)
        return DataResponse(
            success=False,
            message=f"Failed to analyze Robinhood fields: {str(e)}",
            data={"error": str(e)}
        )

@router.get("/compare-roll-methods")
async def compare_roll_methods(
    symbol: str = Query(default="NVDL", description="Symbol to analyze"),
    days_back: int = Query(default=365, description="Days to look back for orders"),
    rh_service: RobinhoodService = Depends(get_robinhood_service)
):
    """
    Compare different methods of identifying rolled options
    """
    try:
        # Get all orders for the symbol
        since_time = datetime.now() - timedelta(days=days_back)
        orders_response = await rh_service.get_options_orders(
            limit=1000,
            since_time=since_time
        )
        
        if not orders_response["success"]:
            return DataResponse(
                success=False,
                message=f"Failed to fetch {symbol} orders",
                data={"error": orders_response.get("message", "Unknown error")}
            )
        
        all_orders = orders_response["data"]
        
        # Filter for the specific symbol
        symbol_orders = []
        for order in all_orders:
            # Check both underlying_symbol and chain_symbol fields
            order_symbol = order.get("underlying_symbol", "") or order.get("chain_symbol", "")
            if order_symbol.upper() == symbol.upper():
                symbol_orders.append(order)
        
        comparison = {
            "symbol": symbol,
            "total_orders": len(symbol_orders),
            "method_1_robinhood_strategies": {
                "description": "Orders with both closing_strategy and opening_strategy fields",
                "rolls_found": [],
                "criteria": "closing_strategy != null AND opening_strategy != null"
            },
            "method_2_chain_id_grouping": {
                "description": "Multiple orders sharing the same chain_id",
                "rolls_found": [],
                "criteria": "Multiple orders with same chain_id"
            },
            "method_3_current_algorithm": {
                "description": "Current pattern matching algorithm",
                "rolls_found": [],
                "criteria": "Close/open pairs within time window"
            },
            "detailed_examples": []
        }
        
        # Method 1: Robinhood strategy fields
        for order in symbol_orders:
            if order.get("closing_strategy") and order.get("opening_strategy"):
                comparison["method_1_robinhood_strategies"]["rolls_found"].append({
                    "order_id": order.get("id"),
                    "chain_id": order.get("chain_id"),
                    "created_at": order.get("created_at"),
                    "closing_strategy": order.get("closing_strategy"),
                    "opening_strategy": order.get("opening_strategy"),
                    "strategy": order.get("strategy"),
                    "strike_price": order.get("strike_price"),
                    "expiration_date": order.get("expiration_date"),
                    "quantity": order.get("quantity"),
                    "direction": order.get("direction")
                })
        
        # Method 2: Chain ID grouping
        chain_groups = {}
        for order in symbol_orders:
            chain_id = order.get("chain_id")
            if chain_id:
                if chain_id not in chain_groups:
                    chain_groups[chain_id] = []
                chain_groups[chain_id].append(order)
        
        for chain_id, orders in chain_groups.items():
            if len(orders) > 1:
                comparison["method_2_chain_id_grouping"]["rolls_found"].append({
                    "chain_id": chain_id,
                    "order_count": len(orders),
                    "orders": [{
                        "order_id": o.get("id"),
                        "created_at": o.get("created_at"),
                        "strategy": o.get("strategy"),
                        "closing_strategy": o.get("closing_strategy"),
                        "opening_strategy": o.get("opening_strategy"),
                        "strike_price": o.get("strike_price"),
                        "expiration_date": o.get("expiration_date"),
                        "quantity": o.get("quantity")
                    } for o in sorted(orders, key=lambda x: x.get("created_at", ""))]
                })
        
        # Method 3: Current algorithm (simplified version)
        # Sort orders by time
        sorted_orders = sorted(symbol_orders, key=lambda x: x.get("created_at", ""))
        
        for i in range(len(sorted_orders) - 1):
            order1 = sorted_orders[i]
            order2 = sorted_orders[i + 1]
            
            strategy1 = order1.get("strategy", "").upper()
            strategy2 = order2.get("strategy", "").upper()
            
            # Simple close/open pattern
            is_close = any(pattern in strategy1 for pattern in ["CLOSE", "BTC", "STC"])
            is_open = any(pattern in strategy2 for pattern in ["OPEN", "SELL", "BUY"]) and "CLOSE" not in strategy2
            
            if is_close and is_open:
                # Check time window (within 7 days)
                try:
                    time1 = datetime.fromisoformat(order1.get("created_at", "").replace('Z', '+00:00'))
                    time2 = datetime.fromisoformat(order2.get("created_at", "").replace('Z', '+00:00'))
                    time_diff_hours = abs((time2 - time1).total_seconds()) / 3600
                    
                    if time_diff_hours <= (7 * 24):  # Within 7 days
                        comparison["method_3_current_algorithm"]["rolls_found"].append({
                            "close_order": {
                                "order_id": order1.get("id"),
                                "strategy": strategy1,
                                "created_at": order1.get("created_at"),
                                "strike_price": order1.get("strike_price"),
                                "quantity": order1.get("quantity")
                            },
                            "open_order": {
                                "order_id": order2.get("id"),
                                "strategy": strategy2,
                                "created_at": order2.get("created_at"),
                                "strike_price": order2.get("strike_price"),
                                "quantity": order2.get("quantity")
                            },
                            "time_diff_hours": time_diff_hours
                        })
                except:
                    pass
        
        # Create detailed examples for comparison
        comparison["detailed_examples"] = []
        
        # Take first few examples from each method
        for method_name, method_data in comparison.items():
            if isinstance(method_data, dict) and "rolls_found" in method_data:
                for roll in method_data["rolls_found"][:3]:  # First 3 examples
                    comparison["detailed_examples"].append({
                        "method": method_name,
                        "example": roll
                    })
        
        return DataResponse(
            success=True,
            message=f"Compared roll identification methods for {symbol}",
            data=comparison
        )
        
    except Exception as e:
        logger.error(f"Error comparing roll methods: {str(e)}", exc_info=True)
        return DataResponse(
            success=False,
            message=f"Failed to compare roll methods: {str(e)}",
            data={"error": str(e)}
        )

@router.get("/analyze-nvdl-orders")
async def analyze_nvdl_orders(
    days_back: int = Query(default=365, description="Days to look back for orders"),
    rh_service: RobinhoodService = Depends(get_robinhood_service)
):
    """
    Analyze all NVDL orders to find potential missing rolled options
    """
    try:
        # Get all NVDL orders for a longer period
        since_time = datetime.now() - timedelta(days=days_back)
        orders_response = await rh_service.get_options_orders(
            limit=1000,  # Increase limit to get more orders
            since_time=since_time
        )
        
        if not orders_response["success"]:
            return DataResponse(
                success=False,
                message="Failed to fetch NVDL orders",
                data={"error": orders_response.get("message", "Unknown error")}
            )
        
        orders = orders_response["data"]
        
        # Filter for NVDL orders
        nvdl_orders = [order for order in orders if order.get("underlying_symbol", "").upper() == "NVDL"]
        
        # Analyze patterns
        analysis = {
            "total_orders": len(nvdl_orders),
            "call_orders": [],
            "put_orders": [],
            "potential_roll_pairs": [],
            "strategy_breakdown": {},
            "time_analysis": {
                "earliest_order": None,
                "latest_order": None,
                "orders_by_month": {}
            }
        }
        
        # Categorize orders
        for order in nvdl_orders:
            option_type = order.get("option_type", "").lower()
            strategy = order.get("strategy", "")
            created_at = order.get("created_at", "")
            
            # Track strategies
            if strategy not in analysis["strategy_breakdown"]:
                analysis["strategy_breakdown"][strategy] = 0
            analysis["strategy_breakdown"][strategy] += 1
            
            # Track time distribution
            if created_at:
                try:
                    order_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    month_key = order_date.strftime("%Y-%m")
                    
                    if analysis["time_analysis"]["earliest_order"] is None or order_date < analysis["time_analysis"]["earliest_order"]:
                        analysis["time_analysis"]["earliest_order"] = order_date
                    if analysis["time_analysis"]["latest_order"] is None or order_date > analysis["time_analysis"]["latest_order"]:
                        analysis["time_analysis"]["latest_order"] = order_date
                    
                    if month_key not in analysis["time_analysis"]["orders_by_month"]:
                        analysis["time_analysis"]["orders_by_month"][month_key] = 0
                    analysis["time_analysis"]["orders_by_month"][month_key] += 1
                except:
                    pass
            
            # Categorize by option type
            order_summary = {
                "order_id": order.get("order_id"),
                "strategy": strategy,
                "strike_price": order.get("strike_price"),
                "expiration_date": order.get("expiration_date"),
                "quantity": order.get("quantity"),
                "price": order.get("price"),
                "created_at": created_at,
                "state": order.get("state")
            }
            
            if option_type == "call":
                analysis["call_orders"].append(order_summary)
            elif option_type == "put":
                analysis["put_orders"].append(order_summary)
        
        # Sort by date
        analysis["call_orders"].sort(key=lambda x: x["created_at"])
        analysis["put_orders"].sort(key=lambda x: x["created_at"])
        
        # Look for potential roll pairs with relaxed constraints
        call_orders = [o for o in nvdl_orders if o.get("option_type", "").lower() == "call"]
        call_orders.sort(key=lambda x: x.get("created_at", ""))
        
        for i in range(len(call_orders) - 1):
            order1 = call_orders[i]
            order2 = call_orders[i + 1]
            
            strategy1 = order1.get("strategy", "").upper()
            strategy2 = order2.get("strategy", "").upper()
            
            # Look for any close followed by open pattern
            is_close = any(pattern in strategy1 for pattern in ["CLOSE", "BTC", "STC"])
            is_open = any(pattern in strategy2 for pattern in ["OPEN", "SELL CALL", "BUY CALL"]) and "CLOSE" not in strategy2
            
            if is_close and is_open:
                # Calculate time difference
                time_diff_hours = 0
                try:
                    time1 = datetime.fromisoformat(order1.get("created_at", "").replace('Z', '+00:00'))
                    time2 = datetime.fromisoformat(order2.get("created_at", "").replace('Z', '+00:00'))
                    time_diff_hours = abs((time2 - time1).total_seconds()) / 3600
                except:
                    pass
                
                analysis["potential_roll_pairs"].append({
                    "close_order": {
                        "order_id": order1.get("order_id"),
                        "strategy": strategy1,
                        "strike": order1.get("strike_price"),
                        "expiry": order1.get("expiration_date"),
                        "quantity": order1.get("quantity"),
                        "created_at": order1.get("created_at")
                    },
                    "open_order": {
                        "order_id": order2.get("order_id"),
                        "strategy": strategy2,
                        "strike": order2.get("strike_price"),
                        "expiry": order2.get("expiration_date"),
                        "quantity": order2.get("quantity"),
                        "created_at": order2.get("created_at")
                    },
                    "time_diff_hours": time_diff_hours,
                    "quantity_ratio": abs(float(order1.get("quantity", 0)) - float(order2.get("quantity", 0))) / max(float(order1.get("quantity", 1)), float(order2.get("quantity", 1))) if order1.get("quantity") and order2.get("quantity") else 0
                })
        
        # Convert datetime objects to strings for JSON serialization
        if analysis["time_analysis"]["earliest_order"]:
            analysis["time_analysis"]["earliest_order"] = analysis["time_analysis"]["earliest_order"].isoformat()
        if analysis["time_analysis"]["latest_order"]:
            analysis["time_analysis"]["latest_order"] = analysis["time_analysis"]["latest_order"].isoformat()
        
        return DataResponse(
            success=True,
            message=f"Analyzed {len(nvdl_orders)} NVDL orders",
            data=analysis
        )
        
    except Exception as e:
        logger.error(f"Error analyzing NVDL orders: {str(e)}", exc_info=True)
        return DataResponse(
            success=False,
            message=f"Failed to analyze NVDL orders: {str(e)}",
            data={"error": str(e)}
        )

@router.get("/test-detection-parameters")
async def test_detection_parameters(
    symbol: str = Query(default="NVDL", description="Symbol to test"),
    max_time_diff_days: int = Query(default=7, description="Maximum days between close/open"),
    max_quantity_diff_percent: float = Query(default=20.0, description="Maximum quantity difference percentage"),
    min_orders: int = Query(default=3, description="Minimum orders required for chain"),
    days_back: int = Query(default=365, description="Days to look back"),
    rh_service: RobinhoodService = Depends(get_robinhood_service)
):
    """
    Test different parameters for rolled options detection
    """
    try:
        # Get orders for the symbol
        since_time = datetime.now() - timedelta(days=days_back)
        orders_response = await rh_service.get_options_orders(
            limit=1000,  # Increase limit to get more orders
            since_time=since_time
        )
        
        if not orders_response["success"]:
            return DataResponse(
                success=False,
                message=f"Failed to fetch {symbol} orders",
                data={"error": orders_response.get("message", "Unknown error")}
            )
        
        orders = orders_response["data"]
        
        # Test with different parameters
        results = {
            "symbol": symbol,
            "total_orders": len(orders),
            "parameters_tested": {
                "max_time_diff_days": max_time_diff_days,
                "max_quantity_diff_percent": max_quantity_diff_percent,
                "min_orders": min_orders
            },
            "detection_results": {}
        }
        
        # Test with current parameters
        rolled_service = RolledOptionsService(rh_service)
        
        # Group orders by option type
        call_orders = [o for o in orders if o.get("option_type", "").lower() == "call"]
        put_orders = [o for o in orders if o.get("option_type", "").lower() == "put"]
        
        call_orders.sort(key=lambda x: x.get("created_at", ""))
        put_orders.sort(key=lambda x: x.get("created_at", ""))
        
        results["detection_results"]["calls"] = _test_chain_detection(
            call_orders, max_time_diff_days, max_quantity_diff_percent, min_orders
        )
        
        results["detection_results"]["puts"] = _test_chain_detection(
            put_orders, max_time_diff_days, max_quantity_diff_percent, min_orders
        )
        
        return DataResponse(
            success=True,
            message=f"Tested detection parameters for {symbol}",
            data=results
        )
        
    except Exception as e:
        logger.error(f"Error testing detection parameters: {str(e)}", exc_info=True)
        return DataResponse(
            success=False,
            message=f"Failed to test detection parameters: {str(e)}",
            data={"error": str(e)}
        )

def _test_chain_detection(orders: List[Dict[str, Any]], max_time_diff_days: int, max_quantity_diff_percent: float, min_orders: int) -> Dict[str, Any]:
    """Test chain detection with given parameters"""
    result = {
        "total_orders": len(orders),
        "potential_chains": [],
        "roll_pairs_found": [],
        "strategies_seen": set()
    }
    
    if len(orders) < min_orders:
        result["reason_rejected"] = f"Less than {min_orders} orders required"
        return result
    
    # Look for potential chains
    for i in range(len(orders)):
        order = orders[i]
        strategy = order.get("strategy", "").upper()
        result["strategies_seen"].add(strategy)
        
        # Check if this could be an initial opening
        is_initial_open = any(pattern in strategy for pattern in [
            "SELL PUT", "SELL CALL", "BUY PUT", "BUY CALL", "SELL TO OPEN", "BUY TO OPEN"
        ]) and "CLOSE" not in strategy
        
        if is_initial_open:
            # Look for subsequent close/open pairs
            chain = [order]
            j = i + 1
            
            while j < len(orders) - 1:
                close_candidate = orders[j]
                open_candidate = orders[j + 1]
                
                if _is_roll_pair_relaxed(close_candidate, open_candidate, max_time_diff_days, max_quantity_diff_percent):
                    chain.extend([close_candidate, open_candidate])
                    result["roll_pairs_found"].append({
                        "close": {
                            "strategy": close_candidate.get("strategy"),
                            "strike": close_candidate.get("strike_price"),
                            "quantity": close_candidate.get("quantity"),
                            "created_at": close_candidate.get("created_at")
                        },
                        "open": {
                            "strategy": open_candidate.get("strategy"),
                            "strike": open_candidate.get("strike_price"),
                            "quantity": open_candidate.get("quantity"),
                            "created_at": open_candidate.get("created_at")
                        }
                    })
                    j += 2
                else:
                    j += 1
            
            if len(chain) >= min_orders:
                result["potential_chains"].append({
                    "chain_length": len(chain),
                    "initial_order": {
                        "strategy": chain[0].get("strategy"),
                        "strike": chain[0].get("strike_price"),
                        "created_at": chain[0].get("created_at")
                    },
                    "rolls_count": (len(chain) - 1) // 2
                })
    
    # Convert set to list for JSON serialization
    result["strategies_seen"] = list(result["strategies_seen"])
    
    return result

def _is_roll_pair_relaxed(order1: Dict[str, Any], order2: Dict[str, Any], max_time_diff_days: int, max_quantity_diff_percent: float) -> bool:
    """Relaxed roll pair detection for testing"""
    try:
        strategy1 = order1.get("strategy", "").upper()
        strategy2 = order2.get("strategy", "").upper()
        
        # Check close/open pattern
        is_close = any(pattern in strategy1 for pattern in ["CLOSE", "BTC", "STC"])
        is_open = any(pattern in strategy2 for pattern in ["OPEN", "SELL", "BUY"]) and "CLOSE" not in strategy2
        
        if not (is_close and is_open):
            return False
        
        # Check time window
        time1_str = order1.get("created_at", "")
        time2_str = order2.get("created_at", "")
        
        if time1_str and time2_str:
            time1 = datetime.fromisoformat(time1_str.replace('Z', '+00:00'))
            time2 = datetime.fromisoformat(time2_str.replace('Z', '+00:00'))
            time_diff_days = abs((time2 - time1).total_seconds()) / (24 * 3600)
            
            if time_diff_days > max_time_diff_days:
                return False
        
        # Check quantity
        qty1 = float(order1.get("quantity", 0))
        qty2 = float(order2.get("quantity", 0))
        
        if qty1 > 0 and qty2 > 0:
            qty_diff_percent = abs(qty1 - qty2) / max(qty1, qty2) * 100
            if qty_diff_percent > max_quantity_diff_percent:
                return False
        
        return True
        
    except Exception:
        return False