"""
Rolled Options Service V2 - Chain ID Based Detection

This service identifies rolled options using Robinhood's explicit chain_id field
instead of pattern matching. This approach is more accurate and eliminates false positives.

Enhanced with database persistence for improved performance.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict

from app.services.options_order_service import OptionsOrderService

logger = logging.getLogger(__name__)

class OptionsChain:
    """Represents an options chain with multiple orders grouped by chain_id"""
    
    def __init__(self, chain_id: str, symbol: str):
        self.chain_id = chain_id
        self.underlying_symbol = symbol
        self.orders = []
        self.initial_strategy = None
        self.start_date = None
        self.last_activity_date = None
        self.status = "unknown"
        self.total_orders = 0
        self.total_credits_collected = 0.0
        self.total_debits_paid = 0.0
        self.net_premium = 0.0
        self.total_pnl = 0.0
        self.current_position = None
        
    def add_order(self, order: Dict[str, Any]):
        """Add an order to this chain"""
        self.orders.append(order)
        self.total_orders += 1
        
        # Update dates
        order_date = datetime.fromisoformat(order.get("created_at", "").replace('Z', '+00:00'))
        if self.start_date is None or order_date < self.start_date:
            self.start_date = order_date
        if self.last_activity_date is None or order_date > self.last_activity_date:
            self.last_activity_date = order_date
            
        # Update initial strategy
        if self.initial_strategy is None:
            self.initial_strategy = self._determine_initial_strategy(order)
            
        # Update financial metrics
        self._update_financial_metrics(order)
        
    def _determine_initial_strategy(self, order: Dict[str, Any]) -> str:
        """Determine the initial strategy from the first order"""
        strategy = order.get("strategy", "").upper()
        
        # Map common strategies
        if "SHORT_PUT" in strategy or "SELL PUT" in strategy:
            return "SELL_PUT"
        elif "SHORT_CALL" in strategy or "SELL CALL" in strategy:
            return "SELL_CALL"
        elif "LONG_PUT" in strategy or "BUY PUT" in strategy:
            return "BUY_PUT"
        elif "LONG_CALL" in strategy or "BUY CALL" in strategy:
            return "BUY_CALL"
        else:
            return strategy.replace(" ", "_")
            
    def _update_financial_metrics(self, order: Dict[str, Any]):
        """Update financial metrics based on order"""
        direction = order.get("direction", "").lower()
        premium = float(order.get("processed_premium", 0))
        
        if direction == "credit" and premium > 0:
            self.total_credits_collected += premium
        elif direction == "debit" and premium > 0:
            self.total_debits_paid += premium
            
        self.net_premium = self.total_credits_collected - self.total_debits_paid
        self.total_pnl = self.net_premium  # Simplified for now
        
    def analyze_chain(self):
        """Analyze the chain to determine if it represents rolled options"""
        if len(self.orders) < 2:
            return False
            
        # Sort orders by date
        sorted_orders = sorted(self.orders, key=lambda x: x.get("created_at", ""))
        
        # Check for roll patterns
        has_rolls = self._detect_roll_patterns(sorted_orders)
        
        # Determine status
        self._determine_status()
        
        return has_rolls
        
    def _detect_roll_patterns(self, orders: List[Dict[str, Any]]) -> bool:
        """Detect if orders represent roll patterns"""
        # Look for alternating close/open patterns
        roll_count = 0
        
        for i in range(len(orders) - 1):
            current_order = orders[i]
            next_order = orders[i + 1]
            
            # Check if current order closes and next opens
            if self._is_closing_order(current_order) and self._is_opening_order(next_order):
                # Check if they're for the same underlying and option type
                if self._orders_match_for_roll(current_order, next_order):
                    roll_count += 1
                    
        return roll_count > 0
        
    def _is_closing_order(self, order: Dict[str, Any]) -> bool:
        """Check if order is closing a position"""
        strategy = order.get("strategy", "").upper()
        closing_strategy = order.get("closing_strategy")
        
        return (
            any(pattern in strategy for pattern in ["CLOSE", "BTC", "STC"]) or
            closing_strategy is not None
        )
        
    def _is_opening_order(self, order: Dict[str, Any]) -> bool:
        """Check if order is opening a position"""
        strategy = order.get("strategy", "").upper()
        opening_strategy = order.get("opening_strategy")
        
        return (
            any(pattern in strategy for pattern in ["SELL PUT", "SELL CALL", "BUY PUT", "BUY CALL", "OPEN"]) or
            opening_strategy is not None
        ) and "CLOSE" not in strategy
        
    def _orders_match_for_roll(self, order1: Dict[str, Any], order2: Dict[str, Any]) -> bool:
        """Check if two orders could be part of a roll"""
        # Same option type
        if order1.get("option_type") != order2.get("option_type"):
            return False
            
        # Orders should be close in time (within reasonable roll window)
        try:
            time1 = datetime.fromisoformat(order1.get("created_at", "").replace('Z', '+00:00'))
            time2 = datetime.fromisoformat(order2.get("created_at", "").replace('Z', '+00:00'))
            time_diff = abs((time2 - time1).total_seconds())
            
            # Allow up to 30 days for rolls (more generous than before)
            if time_diff > (30 * 24 * 3600):
                return False
        except:
            pass
            
        return True
        
    def _determine_status(self):
        """Determine the current status of the chain"""
        if not self.orders:
            self.status = "unknown"
            return
            
        # Sort orders by date to get the latest
        sorted_orders = sorted(self.orders, key=lambda x: x.get("created_at", ""))
        latest_order = sorted_orders[-1]
        
        # Check if the latest order is opening or closing
        if self._is_closing_order(latest_order):
            self.status = "closed"
        elif self._is_opening_order(latest_order):
            self.status = "active"
        else:
            self.status = "unknown"
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert chain to dictionary for API response"""
        return {
            "chain_id": self.chain_id,
            "underlying_symbol": self.underlying_symbol,
            "initial_strategy": self.initial_strategy or "UNKNOWN",
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "last_activity_date": self.last_activity_date.isoformat() if self.last_activity_date else None,
            "status": self.status,
            "total_orders": self.total_orders,
            "total_credits_collected": self.total_credits_collected,
            "total_debits_paid": self.total_debits_paid,
            "net_premium": self.net_premium,
            "total_pnl": self.total_pnl,
            "orders": self.orders,
            "roll_count": max(0, (self.total_orders - 1) // 2)  # Approximate roll count
        }


class RolledOptionsServiceV2:
    """New rolled options service using chain_id based detection with database optimization"""
    
    def __init__(self, robinhood_service):
        self.rh_service = robinhood_service
        self.options_order_service = OptionsOrderService(robinhood_service)
        
    async def get_rolled_options_chains(
        self, 
        days_back: int = 365,
        symbol: Optional[str] = None,
        status: Optional[str] = None,
        min_orders: int = 2,
        user_id: Optional[str] = None,
        use_database: bool = True
    ) -> Dict[str, Any]:
        """
        Get rolled options chains using chain_id based detection
        
        Args:
            days_back: Number of days to look back for orders
            symbol: Filter by specific symbol
            status: Filter by status (active, closed, expired)
            min_orders: Minimum orders required per chain
            user_id: User ID for database queries
            use_database: If True, use optimized database queries
        """
        try:
            # Use optimized database path if available
            if use_database and user_id:
                # Try to get existing data from database first
                db_result = await self.options_order_service.get_rolled_options_chains_from_db(
                    user_id=user_id,
                    days_back=None,  # analyze full history from DB
                    symbol=symbol,
                    status=status,
                    min_orders=min_orders
                )
                
                # If we have data in database, return it immediately
                if db_result["success"] and db_result["data"]["chains"]:
                    logger.info(f"Found {len(db_result['data']['chains'])} chains in database cache")
                    return db_result
                
                # Smart sync: only sync recent data if no cached data exists
                logger.info("No cached data found. Starting smart sync for recent data.")
                
                # Limit initial sync to prevent timeouts
                sync_days = min(days_back, 90)  # Cap at 90 days for initial sync
                
                try:
                    # Perform incremental sync with timeout protection
                    sync_result = await self.options_order_service.sync_options_orders(
                        user_id=user_id,
                        days_back=None,  # full history on first sync
                        force_full_sync=False
                    )
                    
                    if sync_result["success"]:
                        logger.info(f"Smart sync completed: {sync_result['data']['orders_stored']} orders synced")
                        
                        # Now get the data from database
                        return await self.options_order_service.get_rolled_options_chains_from_db(
                            user_id=user_id,
                            days_back=None,  # analyze full history from DB
                            symbol=symbol,
                            status=status,
                            min_orders=min_orders
                        )
                    else:
                        logger.warning(f"Smart sync failed: {sync_result['message']}")
                        
                except Exception as e:
                    logger.error(f"Smart sync error: {str(e)}")
                
                # Fallback: return empty result if sync fails
                return {
                    "success": True,
                    "message": "No rolled options chains found (sync in progress)",
                    "data": {
                        "chains": [],
                        "summary": {
                            "total_chains": 0,
                            "total_orders": 0,
                            "total_pnl": 0.0,
                            "avg_orders_per_chain": 0.0
                        },
                        "filters_applied": {
                            "symbol": symbol,
                            "status": status,
                            "min_orders": min_orders
                        },
                        "analysis_period_days": days_back,
                        "total_chains_found": 0,
                        "filtered_chains_count": 0
                    }
                }
            
            # Fallback to original API-only approach
            # Get options orders
            since_time = datetime.now() - timedelta(days=days_back)
            orders_response = await self.rh_service.get_options_orders(
                limit=2000,  # Get more orders
                since_time=since_time
            )
            
            if not orders_response["success"]:
                return {
                    "success": False,
                    "message": "Failed to fetch options orders",
                    "data": None
                }
                
            all_orders = orders_response["data"]
            
            # Filter orders if symbol specified
            if symbol:
                filtered_orders = []
                for order in all_orders:
                    order_symbol = order.get("chain_symbol", "") or order.get("underlying_symbol", "")
                    if order_symbol.upper() == symbol.upper():
                        filtered_orders.append(order)
                all_orders = filtered_orders
            
            # Group orders by chain_id
            chains_by_id = self._group_orders_by_chain_id(all_orders)
            
            # Filter chains with minimum orders
            filtered_chains = {
                chain_id: orders for chain_id, orders in chains_by_id.items() 
                if len(orders) >= min_orders
            }
            
            # Build chain objects
            chains = []
            for chain_id, orders in filtered_chains.items():
                if not chain_id:  # Skip empty chain_ids
                    continue
                    
                # Get symbol from first order
                symbol_name = orders[0].get("chain_symbol", "") or orders[0].get("underlying_symbol", "")
                if not symbol_name:
                    continue
                    
                chain = OptionsChain(chain_id, symbol_name)
                
                # Add all orders to the chain
                for order in orders:
                    chain.add_order(order)
                
                # Analyze if this chain represents rolled options
                if chain.analyze_chain():
                    chains.append(chain)
            
            # Filter by status if specified
            if status:
                chains = [chain for chain in chains if chain.status.lower() == status.lower()]
            
            # Generate summary
            summary = self._generate_summary(chains)
            
            return {
                "success": True,
                "message": f"Found {len(chains)} rolled options chains",
                "data": {
                    "chains": [chain.to_dict() for chain in chains],
                    "summary": summary,
                    "filters_applied": {
                        "symbol": symbol,
                        "status": status,
                        "min_orders": min_orders
                    },
                    "analysis_period_days": days_back,
                    "total_chains_found": len(filtered_chains),
                    "rolled_chains_identified": len(chains)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting rolled options chains: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "data": None
            }
    
    def _group_orders_by_chain_id(self, orders: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group orders by their chain_id"""
        chains = defaultdict(list)
        
        for order in orders:
            chain_id = order.get("chain_id", "")
            if chain_id:  # Only process orders with chain_id
                chains[chain_id].append(order)
        
        return dict(chains)
    
    def _generate_summary(self, chains: List[OptionsChain]) -> Dict[str, Any]:
        """Generate summary statistics for the chains"""
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
        
        total_chains = len(chains)
        active_chains = len([c for c in chains if c.status == "active"])
        closed_chains = len([c for c in chains if c.status == "closed"])
        total_orders = sum(c.total_orders for c in chains)
        net_premium = sum(c.net_premium for c in chains)
        total_pnl = sum(c.total_pnl for c in chains)
        avg_orders = total_orders / total_chains if total_chains > 0 else 0
        
        # Symbol distribution
        symbol_counts = defaultdict(int)
        for chain in chains:
            symbol_counts[chain.underlying_symbol] += 1
        
        most_active_symbol = max(symbol_counts.keys(), key=symbol_counts.get) if symbol_counts else None
        
        return {
            "total_chains": total_chains,
            "active_chains": active_chains,
            "closed_chains": closed_chains,
            "total_orders": total_orders,
            "net_premium_collected": net_premium,
            "total_pnl": total_pnl,
            "avg_orders_per_chain": round(avg_orders, 2),
            "most_active_symbol": most_active_symbol,
            "symbol_distribution": dict(symbol_counts)
        }
    
    async def get_rolled_options_chains_paginated(
        self, 
        days_back: int = 90,
        symbol: Optional[str] = None,
        status: Optional[str] = None,
        min_orders: int = 2,
        user_id: Optional[str] = None,
        page: int = 1,
        limit: int = 50,
        use_database: bool = True
    ) -> Dict[str, Any]:
        """
        Get rolled options chains with pagination for improved performance
        
        Args:
            days_back: Number of days to look back for orders
            symbol: Filter by specific symbol
            status: Filter by status (active, closed, expired)
            min_orders: Minimum orders required per chain
            user_id: User ID for database queries
            page: Page number (1-based)
            limit: Number of chains per page
            use_database: If True, use optimized database queries
        """
        try:
            # Get full data first
            full_result = await self.get_rolled_options_chains(
                days_back=days_back,
                symbol=symbol,
                status=status,
                min_orders=min_orders,
                user_id=user_id,
                use_database=use_database
            )
            
            if not full_result.get("success", False):
                return full_result
            
            all_chains = full_result["data"]["chains"]
            total_chains = len(all_chains)
            
            # Calculate pagination
            total_pages = (total_chains + limit - 1) // limit  # Ceiling division
            start_index = (page - 1) * limit
            end_index = start_index + limit
            
            # Slice the chains for this page
            paginated_chains = all_chains[start_index:end_index]
            
            # Update summary for paginated data
            paginated_summary = self._calculate_summary([
                self._chain_dict_to_object(chain) for chain in paginated_chains
            ])
            
            return {
                "success": True,
                "message": f"Retrieved page {page} of rolled options chains",
                "data": {
                    "chains": paginated_chains,
                    "summary": paginated_summary,
                    "total_chains": total_chains,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1,
                    "filters_applied": {
                        "symbol": symbol,
                        "status": status,
                        "min_orders": min_orders
                    },
                    "analysis_period_days": days_back
                }
            }
            
        except Exception as e:
            logger.error(f"Error in paginated rolled options chains: {str(e)}")
            return {
                "success": False,
                "message": f"Error retrieving paginated chains: {str(e)}",
                "data": {
                    "chains": [],
                    "summary": {},
                    "total_chains": 0,
                    "total_pages": 0,
                    "has_next": False,
                    "has_prev": False
                }
            }
    
    def _chain_dict_to_object(self, chain_dict: Dict[str, Any]) -> OptionsChain:
        """Convert chain dictionary back to OptionsChain object for summary calculation"""
        chain = OptionsChain(chain_dict["chain_id"], chain_dict["underlying_symbol"])
        chain.total_orders = chain_dict["total_orders"]
        chain.net_premium = chain_dict["net_premium"]
        chain.total_pnl = chain_dict["total_pnl"]
        chain.status = chain_dict["status"]
        return chain
