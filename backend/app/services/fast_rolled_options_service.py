"""
Fast Rolled Options Service - Optimized for Performance

This service provides a much faster implementation of rolled options detection
by using simpler heuristics and aggressive caching.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)

class FastRolledOptionsService:
    """Fast rolled options service with optimized algorithms"""
    
    def __init__(self, robinhood_service):
        self.rh_service = robinhood_service
        self._cache = {}
        self._cache_expiry = {}
        
    async def get_rolled_options_chains_fast(
        self, 
        days_back: int = 30,
        symbol: Optional[str] = None,
        status: Optional[str] = None,
        min_orders: int = 2,
        page: int = 1,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Fast implementation of rolled options chains detection
        Uses simplified logic and aggressive caching
        """
        try:
            # Check cache first
            cache_key = f"{days_back}_{symbol}_{status}_{min_orders}"
            if self._is_cache_valid(cache_key):
                logger.info(f"Returning cached result for {cache_key}")
                cached_result = self._cache[cache_key]
                return self._paginate_result(cached_result, page, limit)
            
            # Fetch minimal data with strict limits
            since_time = datetime.now() - timedelta(days=days_back)
            
            # Use much smaller limit to prevent timeouts
            orders_response = await self.rh_service.get_options_orders(
                limit=min(500, days_back * 10),  # Much smaller limit
                since_time=since_time
            )
            
            if not orders_response.get("success", False):
                return self._empty_result(page, limit, days_back, symbol, status, min_orders)
                
            all_orders = orders_response["data"]
            
            # Fast filtering
            if symbol:
                all_orders = [
                    order for order in all_orders 
                    if symbol.upper() in (order.get("underlying_symbol", "").upper() or "")
                ]
            
            # Simple chain detection - just group by chain_id
            chains_by_id = defaultdict(list)
            for order in all_orders:
                chain_id = order.get("chain_id")
                if chain_id:
                    chains_by_id[chain_id].append(order)
            
            # Filter by minimum orders and build simple chain objects
            chains = []
            for chain_id, orders in chains_by_id.items():
                if len(orders) >= min_orders:
                    chain = self._build_simple_chain(chain_id, orders)
                    if chain:
                        chains.append(chain)
            
            # Apply status filter
            if status:
                chains = [c for c in chains if c.get("status", "").lower() == status.lower()]
            
            # Sort chains by latest activity first (most recent first)
            chains.sort(key=lambda x: x.get("last_activity_date", ""), reverse=True)
            
            # Generate simple summary
            summary = self._generate_simple_summary(chains)
            
            result = {
                "chains": chains,
                "summary": summary,
                "total_chains": len(chains),
                "analysis_period_days": days_back
            }
            
            # Cache the result
            self._cache[cache_key] = result
            self._cache_expiry[cache_key] = datetime.now() + timedelta(minutes=15)
            
            return self._paginate_result(result, page, limit)
            
        except Exception as e:
            logger.error(f"Error in fast rolled options service: {str(e)}")
            return self._empty_result(page, limit, days_back, symbol, status, min_orders, f"Error: {str(e)}")
    
    def _build_simple_chain(self, chain_id: str, orders: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Build a simple chain object without heavy analysis"""
        if not orders:
            return None
            
        try:
            # Get basic info from first order
            first_order = orders[0]
            symbol = self._extract_underlying_symbol(orders)
            
            # Simple financial calculations
            total_credits = sum(
                float(order.get("processed_premium", 0)) 
                for order in orders 
                if order.get("direction") == "credit"
            )
            total_debits = sum(
                float(order.get("processed_premium", 0)) 
                for order in orders 
                if order.get("direction") == "debit"
            )
            net_premium = total_credits - total_debits
            
            # Simple status determination - just check last order
            last_order = max(orders, key=lambda x: x.get("created_at", ""))
            status = "active" if "open" in last_order.get("strategy", "").lower() else "closed"
            
            # Get date range
            dates = [order.get("created_at") for order in orders if order.get("created_at")]
            start_date = min(dates) if dates else None
            end_date = max(dates) if dates else None
            
            return {
                "chain_id": chain_id,
                "underlying_symbol": symbol,
                "status": status,
                "total_orders": len(orders),
                "net_premium": round(net_premium, 2),
                "total_pnl": round(net_premium, 2),  # Simplified P&L
                "total_credits_collected": round(total_credits, 2),
                "total_debits_paid": round(total_debits, 2),
                "start_date": start_date,
                "last_activity_date": end_date,
                "roll_count": max(0, len(orders) - 1),
                "orders": sorted(orders, key=lambda x: x.get("created_at", ""), reverse=True)[-3:] if len(orders) > 3 else sorted(orders, key=lambda x: x.get("created_at", ""), reverse=True),  # Show latest orders first
                "initial_strategy": self._determine_strategy_from_order(first_order)
            }
            
        except Exception as e:
            logger.error(f"Error building simple chain: {str(e)}")
            return None
    
    def _determine_strategy_from_order(self, order: Dict[str, Any]) -> str:
        """Determine strategy from order details"""
        # First try the strategy field if it exists and isn't empty
        strategy = order.get("strategy", "").strip()
        if strategy and strategy.upper() != "NONE":
            strategy_upper = strategy.upper()
            
            # Map common strategies  
            if "SHORT_PUT" in strategy_upper or "SELL PUT" in strategy_upper:
                return "SELL_PUT"
            elif "SHORT_CALL" in strategy_upper or "SELL CALL" in strategy_upper:
                return "SELL_CALL"
            elif "LONG_PUT" in strategy_upper or "BUY PUT" in strategy_upper:
                return "BUY_PUT"
            elif "LONG_CALL" in strategy_upper or "BUY CALL" in strategy_upper:
                return "BUY_CALL"
            elif strategy_upper:
                return strategy_upper.replace(" ", "_")
        
        # Fall back to constructing from transaction details
        transaction_side = order.get("transaction_side", "").upper()
        option_type = order.get("option_type", "").upper()
        position_effect = order.get("position_effect", "").upper()
        
        # Construct strategy from components
        if transaction_side and option_type:
            if "SELL" in transaction_side and "PUT" in option_type:
                return "SELL_PUT"
            elif "SELL" in transaction_side and "CALL" in option_type:
                return "SELL_CALL"
            elif "BUY" in transaction_side and "PUT" in option_type:
                return "BUY_PUT"
            elif "BUY" in transaction_side and "CALL" in option_type:
                return "BUY_CALL"
        
        return "UNKNOWN"
    
    def _extract_underlying_symbol(self, orders: List[Dict[str, Any]]) -> str:
        """Extract underlying symbol from orders with fallback logic"""
        # Debug: log available fields in first order
        if orders:
            first_order = orders[0]
            logger.info(f"Available fields in order: {list(first_order.keys())}")
            logger.info(f"underlying_symbol value: '{first_order.get('underlying_symbol', 'NOT_FOUND')}'")
        
        # Try to find symbol from any order
        for order in orders:
            symbol = order.get("underlying_symbol", "").strip()
            if symbol and symbol.upper() != "NONE":
                return symbol.upper()
            
            # Try alternative field names
            symbol = order.get("symbol", "").strip()
            if symbol and symbol.upper() != "NONE":
                return symbol.upper()
                
            # Try to extract from instrument URL or other fields
            instrument = order.get("underlying_instrument", {})
            if isinstance(instrument, dict):
                symbol = instrument.get("symbol", "").strip()
                if symbol and symbol.upper() != "NONE":
                    return symbol.upper()
        
        logger.warning(f"Could not extract underlying symbol from {len(orders)} orders")
        return "UNKNOWN"
    
    def _generate_simple_summary(self, chains: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate simple summary without heavy calculations"""
        if not chains:
            return {
                "total_chains": 0,
                "active_chains": 0,
                "closed_chains": 0,
                "total_orders": 0,
                "net_premium_collected": 0.0,
                "total_pnl": 0.0,
                "avg_orders_per_chain": 0.0,
                "most_active_symbol": None,
                "symbol_distribution": {}
            }
        
        active_count = sum(1 for c in chains if c.get("status") == "active")
        closed_count = sum(1 for c in chains if c.get("status") == "closed")
        total_orders = sum(c.get("total_orders", 0) for c in chains)
        total_premium = sum(c.get("net_premium", 0) for c in chains)
        
        # Symbol distribution
        symbols = [c.get("underlying_symbol") for c in chains]
        symbol_counts = {symbol: symbols.count(symbol) for symbol in set(symbols)}
        most_active = max(symbol_counts.keys(), key=symbol_counts.get) if symbol_counts else None
        
        return {
            "total_chains": len(chains),
            "active_chains": active_count,
            "closed_chains": closed_count,
            "total_orders": total_orders,
            "net_premium_collected": round(total_premium, 2),
            "total_pnl": round(total_premium, 2),
            "avg_orders_per_chain": round(total_orders / len(chains), 2) if chains else 0,
            "most_active_symbol": most_active,
            "symbol_distribution": symbol_counts
        }
    
    def _paginate_result(self, result: Dict[str, Any], page: int, limit: int) -> Dict[str, Any]:
        """Apply pagination to result"""
        chains = result["chains"]
        total_chains = len(chains)
        total_pages = (total_chains + limit - 1) // limit
        
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_chains = chains[start_idx:end_idx]
        
        return {
            "success": True,
            "message": f"Retrieved {len(paginated_chains)} chains (page {page})",
            "data": {
                "chains": paginated_chains,
                "summary": result["summary"],
                "total_chains": total_chains,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
                "analysis_period_days": result["analysis_period_days"]
            }
        }
    
    def _empty_result(self, page: int, limit: int, days_back: int, symbol: Optional[str], 
                      status: Optional[str], min_orders: int, message: str = "No data found") -> Dict[str, Any]:
        """Return empty result structure"""
        return {
            "success": True,
            "message": message,
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
                "total_chains": 0,
                "total_pages": 0,
                "has_next": False,
                "has_prev": False,
                "analysis_period_days": days_back
            }
        }
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid"""
        if cache_key not in self._cache:
            return False
        
        expiry = self._cache_expiry.get(cache_key)
        if not expiry or datetime.now() > expiry:
            # Clean up expired cache
            self._cache.pop(cache_key, None)
            self._cache_expiry.pop(cache_key, None)
            return False
        
        return True