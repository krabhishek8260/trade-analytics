"""
JSON-Based Rolled Options Service

This service reads directly from raw Robinhood API JSON files to identify
rolled options chains using proper roll indicators instead of relying on
database chain_id grouping.

Roll Detection Strategy:
- form_source = "strategy_roll" → Auto-rolled by Robinhood
- Matching open/close orders on same day → Manual rolls
- legs[].position_effect & legs[].side → Classify roll direction
- chain_symbol, option.instrument_id, expiration → Track changes
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from collections import defaultdict
import hashlib

from app.core.redis import cache

logger = logging.getLogger(__name__)


class JsonRolledOptionsService:
    """Service for analyzing rolled options chains directly from JSON files"""
    
    def __init__(self):
        self.debug_data_dir = Path(__file__).parent.parent.parent / "debug_data"
        
    async def get_rolled_chains_from_files(
        self,
        days_back: int = 30,
        symbol: Optional[str] = None,
        status: Optional[str] = None,
        min_orders: int = 2,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze rolled options chains directly from JSON files
        
        Args:
            days_back: Number of days to look back
            symbol: Filter by underlying symbol
            status: Filter by chain status (active/closed)
            min_orders: Minimum orders per chain
            use_cache: Use Redis caching
        """
        try:
            # Generate cache key
            cache_key = self._generate_cache_key(days_back, symbol, status, min_orders)
            
            # Check cache first
            if use_cache:
                cached_result = await cache.get(cache_key)
                if cached_result:
                    logger.info(f"Cache hit for JSON rolled options: {cache_key}")
                    return cached_result
            
            logger.info(f"Analyzing rolled options from JSON files (days_back={days_back}, symbol={symbol})")
            
            # Step 1: Load all orders from JSON files
            all_orders = await self._load_orders_from_files()
            logger.info(f"Loaded {len(all_orders)} total orders from JSON files")
            
            # Step 2: Filter by date range and symbol
            filtered_orders = self._filter_orders(all_orders, days_back, symbol)
            logger.info(f"Filtered to {len(filtered_orders)} orders for analysis")
            
            # Emergency fix: Limit to first 1000 orders to prevent hanging
            if len(filtered_orders) > 1000:
                filtered_orders = filtered_orders[:1000]
                logger.warning(f"Limited to first 1000 orders to prevent timeout")
            
            # Step 3: Identify roll orders using proper indicators
            roll_orders = self._identify_roll_orders(filtered_orders)
            logger.info(f"Identified {len(roll_orders)} roll-related orders")
            
            # Step 4: Group orders into chains by symbol + option_type
            chains_by_symbol_type = self._group_orders_by_symbol_type(roll_orders)
            logger.info(f"Grouped into {len(chains_by_symbol_type)} symbol+type combinations")
            
            # Step 5: Create logical chains by linking roll sequences (with timeout protection)
            try:
                chains = await asyncio.wait_for(
                    self._create_logical_chains(chains_by_symbol_type, min_orders),
                    timeout=120.0  # 2 minute timeout for chain creation
                )
                logger.info(f"Created {len(chains)} logical rolled options chains")
            except asyncio.TimeoutError:
                logger.error("Chain creation timed out after 2 minutes")
                chains = []
            except Exception as e:
                logger.error(f"Error in chain creation: {e}")
                chains = []
            
            # Step 6: Filter by status if specified
            if status:
                chains = [c for c in chains if c.get("status", "").lower() == status.lower()]
                logger.info(f"Filtered to {len(chains)} chains with status '{status}'")
            
            # Step 7: Calculate summary statistics
            summary = self._calculate_summary(chains)
            
            result = {
                "success": True,
                "message": f"Found {len(chains)} rolled options chains from JSON analysis",
                "data": {
                    "chains": chains,
                    "summary": summary
                }
            }
            
            # Cache the result
            if use_cache:
                # Cache longer for expensive operations based on date range
                cache_ttl = min(3600 + (days_back * 10), 7200)  # 1-2 hours depending on complexity
                await cache.set(cache_key, result, ttl=cache_ttl)
                logger.info(f"Cached JSON rolled options result: {cache_key}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing rolled options from JSON: {str(e)}", exc_info=True)
            # Return empty but valid response to prevent frontend crashes
            return {
                "success": True,
                "message": f"Analysis completed with errors (returned empty results): {str(e)}",
                "data": {
                    "chains": [],
                    "summary": {
                        "total_chains": 0,
                        "active_chains": 0,
                        "closed_chains": 0,
                        "total_orders": 0,
                        "net_premium_collected": 0.0,
                        "total_pnl": 0.0,
                        "avg_orders_per_chain": 0.0
                    }
                }
            }
    
    async def _load_orders_from_files(self) -> List[Dict[str, Any]]:
        """Load all orders from JSON files in debug_data directory with caching"""
        # Check cache for raw orders data first
        cache_key = "json_rolled_options:raw_orders_data"
        cached_orders = await cache.get(cache_key)
        
        if cached_orders:
            logger.info(f"Using cached raw orders data ({len(cached_orders)} orders)")
            return cached_orders
        
        all_orders = []
        
        # Find all options_orders JSON files
        options_files = list(self.debug_data_dir.glob("*options_orders*.json"))
        logger.info(f"Found {len(options_files)} options orders files")
        
        for file_path in options_files:
            try:
                with open(file_path, 'r') as f:
                    orders = json.load(f)
                    all_orders.extend(orders)
                    logger.debug(f"Loaded {len(orders)} orders from {file_path.name}")
                    
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")
                continue
        
        # Cache raw orders for 30 minutes (they don't change often)
        if all_orders:
            await cache.set(cache_key, all_orders, ttl=1800)
            logger.info(f"Cached {len(all_orders)} raw orders for 30 minutes")
        
        return all_orders
    
    def _filter_orders(
        self, 
        orders: List[Dict[str, Any]], 
        days_back: int, 
        symbol: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Filter orders by date range and symbol"""
        from datetime import timezone
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        filtered_orders = []
        
        for order in orders:
            try:
                # Parse created_at date
                created_at_str = order.get("created_at", "")
                if not created_at_str:
                    continue
                    
                created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                
                # Filter by date
                if created_at < cutoff_date:
                    continue
                
                # Filter by symbol if specified
                if symbol:
                    chain_symbol = order.get("chain_symbol", "").upper()
                    if chain_symbol != symbol.upper():
                        continue
                
                # Only include filled orders
                if order.get("state") != "filled":
                    continue
                
                filtered_orders.append(order)
                
            except Exception as e:
                logger.debug(f"Error filtering order {order.get('id', 'unknown')}: {e}")
                continue
        
        return filtered_orders
    
    def _identify_roll_orders(self, orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Identify orders that are part of rolled options using the indicators:
        - form_source = "strategy_roll" → Auto-rolled by Robinhood
        - Matching open/close orders on same day → Manual rolls
        """
        roll_orders = []
        orders_by_date_symbol = defaultdict(list)
        
        # First pass: identify obvious roll orders
        for order in orders:
            form_source = order.get("form_source", "")
            
            # Direct roll indicator
            if form_source == "strategy_roll":
                roll_orders.append(order)
                continue
            
            # Group potential manual rolls by date and symbol for analysis
            try:
                created_at_str = order.get("created_at", "")
                created_date = datetime.fromisoformat(created_at_str.replace('Z', '+00:00')).date()
                chain_symbol = order.get("chain_symbol", "").upper()
                
                if chain_symbol:
                    date_symbol_key = f"{created_date}_{chain_symbol}"
                    orders_by_date_symbol[date_symbol_key].append(order)
                    
            except Exception as e:
                logger.debug(f"Error grouping order for manual roll detection: {e}")
                continue
        
        # Second pass: identify manual rolls (open/close pairs on same day)
        for date_symbol_key, day_orders in orders_by_date_symbol.items():
            if len(day_orders) < 2:
                continue
                
            manual_rolls = self._detect_manual_rolls(day_orders)
            roll_orders.extend(manual_rolls)
        
        # Remove duplicates while preserving order
        seen_ids = set()
        unique_roll_orders = []
        for order in roll_orders:
            order_id = order.get("id")
            if order_id and order_id not in seen_ids:
                seen_ids.add(order_id)
                unique_roll_orders.append(order)
        
        return unique_roll_orders
    
    def _detect_manual_rolls(self, day_orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect manual rolls within orders from the same day
        Look for open/close pairs with matching option types
        """
        manual_rolls = []
        
        # Group orders by option type for this day
        orders_by_type = defaultdict(list)
        for order in day_orders:
            legs = order.get("legs", [])
            for leg in legs:
                option_type = leg.get("option_type", "").lower()
                if option_type in ["call", "put"]:
                    orders_by_type[option_type].append(order)
        
        # Look for open/close patterns within each option type
        for option_type, type_orders in orders_by_type.items():
            if len(type_orders) < 2:
                continue
                
            # Check for close/open pattern (typical roll)
            has_close = any(
                any(leg.get("position_effect") == "close" for leg in order.get("legs", []))
                for order in type_orders
            )
            has_open = any(
                any(leg.get("position_effect") == "open" for leg in order.get("legs", []))
                for order in type_orders
            )
            
            # If we have both close and open orders for same option type on same day,
            # likely a manual roll
            if has_close and has_open:
                manual_rolls.extend(type_orders)
        
        return manual_rolls
    
    def _group_orders_by_symbol_type(
        self, 
        orders: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group orders by chain_symbol + option_type combination"""
        groups = defaultdict(list)
        
        for order in orders:
            chain_symbol = order.get("chain_symbol", "").upper()
            if not chain_symbol:
                continue
            
            # Determine primary option type from legs
            legs = order.get("legs", [])
            if not legs:
                continue
            
            # Use the first leg's option type (most orders are single-type)
            primary_option_type = legs[0].get("option_type", "").lower()
            if primary_option_type not in ["call", "put"]:
                continue
            
            group_key = f"{chain_symbol}_{primary_option_type}"
            groups[group_key].append(order)
        
        return dict(groups)
    
    def _build_strike_based_chains(
        self, 
        orders: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """
        Build chains based on strike price progressions and leg patterns
        
        Chain structure:
        1. Start: 1 leg SELL TO OPEN (initial position)
        2. Rolls: 2 legs BUY TO CLOSE previous + SELL TO OPEN new  
        3. End: 1 leg BUY TO CLOSE (final close)
        """
        if not orders:
            return []
        
        # Sort orders chronologically
        sorted_orders = sorted(
            orders, 
            key=lambda x: datetime.fromisoformat(x.get("created_at", "").replace('Z', '+00:00'))
        )
        
        # Extract roll information from each order
        roll_info = []
        for order in sorted_orders:
            info = self._extract_roll_info(order)
            if info:
                roll_info.append(info)
        
        # Build chains by linking strike progressions
        chains = self._link_strike_progressions(roll_info)
        
        return chains
    
    def _extract_roll_info(self, order: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract roll information from an order"""
        legs = order.get("legs", [])
        if not legs:
            return None
        
        order_info = {
            "order": order,
            "order_id": order.get("id"),
            "created_at": order.get("created_at"),
            "legs_count": len(legs),
            "closes": [],  # BUY TO CLOSE legs
            "opens": []    # SELL TO OPEN legs
        }
        
        for leg in legs:
            position_effect = leg.get("position_effect", "").lower()
            side = leg.get("side", "").lower()
            strike_price = float(leg.get("strike_price", 0) or 0)
            option_type = leg.get("option_type", "").lower()
            expiration_date = leg.get("expiration_date", "")
            
            leg_info = {
                "strike_price": strike_price,
                "option_type": option_type,
                "expiration_date": expiration_date,
                "side": side,
                "position_effect": position_effect
            }
            
            if position_effect == "close" and side == "buy":
                order_info["closes"].append(leg_info)
            elif position_effect == "open" and side == "sell":
                order_info["opens"].append(leg_info)
        
        return order_info
    
    def _link_strike_progressions(
        self, 
        roll_infos: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """Link orders based on strike price continuity"""
        if not roll_infos:
            return []
        
        chains = []
        used_orders = set()
        
        # Start with orders that have SELL TO OPEN but no BUY TO CLOSE (initial positions)
        starting_orders = [
            info for info in roll_infos 
            if info["opens"] and not info["closes"] and info["order_id"] not in used_orders
        ]
        
        for start_info in starting_orders:
            chain = self._build_chain_from_start(start_info, roll_infos, used_orders)
            if len(chain) >= 2:  # At least 2 orders to be considered a chain
                chains.append([info["order"] for info in chain])
                used_orders.update(info["order_id"] for info in chain)
        
        # Also check for roll sequences that don't have a clear start
        # (in case the initial order is missing from our data)
        remaining_rolls = [
            info for info in roll_infos
            if info["order_id"] not in used_orders and len(info["closes"]) > 0 and len(info["opens"]) > 0
        ]
        
        if remaining_rolls:
            # Group remaining rolls by strike continuity
            additional_chains = self._group_remaining_rolls(remaining_rolls)
            for chain in additional_chains:
                if len(chain) >= 2:
                    chains.append([info["order"] for info in chain])
        
        return chains
    
    def _build_chain_from_start(
        self, 
        start_info: Dict[str, Any], 
        all_infos: List[Dict[str, Any]], 
        used_orders: Set[str]
    ) -> List[Dict[str, Any]]:
        """Build a chain starting from an initial SELL TO OPEN order"""
        chain = [start_info]
        current_opens = start_info["opens"]
        
        # Keep looking for next orders in the chain
        while current_opens:
            next_order = None
            
            # Look for an order that closes one of our current open strikes
            for info in all_infos:
                if (info["order_id"] in used_orders or 
                    info["order_id"] == start_info["order_id"]):
                    continue
                
                # Check if this order closes any of our open strikes
                for close_leg in info["closes"]:
                    for open_leg in current_opens:
                        if (close_leg["strike_price"] == open_leg["strike_price"] and
                            close_leg["option_type"] == open_leg["option_type"]):
                            next_order = info
                            break
                    if next_order:
                        break
                if next_order:
                    break
            
            if not next_order:
                break
            
            chain.append(next_order)
            
            # Update current opens for next iteration
            # Remove the strikes that were closed and add newly opened strikes
            new_opens = []
            
            # Add any opens from this order
            new_opens.extend(next_order["opens"])
            
            # Remove closed strikes from previous opens
            for open_leg in current_opens:
                was_closed = False
                for close_leg in next_order["closes"]:
                    if (close_leg["strike_price"] == open_leg["strike_price"] and
                        close_leg["option_type"] == open_leg["option_type"]):
                        was_closed = True
                        break
                if not was_closed:
                    new_opens.append(open_leg)
            
            current_opens = new_opens
        
        return chain
    
    def _group_remaining_rolls(
        self, 
        roll_infos: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """Group remaining roll orders that don't have clear starts"""
        # This is a simplified approach - in a full implementation,
        # we'd do more sophisticated strike matching
        
        if len(roll_infos) >= 2:
            # Sort by date and group as potential chain
            sorted_rolls = sorted(
                roll_infos,
                key=lambda x: x["created_at"]
            )
            return [sorted_rolls]
        
        return []
    
    async def _create_logical_chains(
        self, 
        groups: Dict[str, List[Dict[str, Any]]], 
        min_orders: int
    ) -> List[Dict[str, Any]]:
        """Create logical chains using strike-based chain building"""
        chains = []
        
        for group_key, orders in groups.items():
            if len(orders) < min_orders:
                continue
            
            try:
                # Build chains based on strike price progressions
                strike_chains = self._build_strike_based_chains(orders)
                
                for chain_orders in strike_chains:
                    if len(chain_orders) >= min_orders:
                        # Analyze the chain
                        chain_analysis = await self._analyze_strike_chain(group_key, chain_orders)
                        
                        if chain_analysis.get("is_rolled_chain", False):
                            chains.append(chain_analysis)
                    
            except Exception as e:
                logger.error(f"Error creating strike chains for {group_key}: {e}")
                continue
        
        # Sort chains by latest activity (most recent first)
        chains.sort(key=lambda x: x.get("last_activity", ""), reverse=True)
        
        return chains
    
    async def _analyze_strike_chain(
        self, 
        group_key: str, 
        orders: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze a strike-based chain to create chain details"""
        try:
            if not orders:
                return {"is_rolled_chain": False}
            
            # Extract symbol and option type from group key
            symbol, option_type = group_key.split("_", 1)
            
            # Calculate strike progression
            strike_progression = self._calculate_strike_progression(orders)
            
            # Calculate basic metrics
            total_credits = 0.0
            total_debits = 0.0
            
            for order in orders:
                direction = order.get("direction", "").lower()
                processed_premium = float(order.get("processed_premium", 0) or 0)
                
                if direction == "credit":
                    total_credits += processed_premium
                elif direction == "debit":
                    total_debits += processed_premium
            
            net_premium = total_credits - total_debits
            
            # Determine chain status
            status = self._determine_strike_chain_status(orders)
            
            # Get date range
            first_order = orders[0]
            last_order = orders[-1]
            
            start_date = first_order.get("created_at")
            last_activity = last_order.get("created_at")
            
            # Create order details for frontend with strike progression info
            order_details = []
            for i, order in enumerate(orders):
                legs = order.get("legs", [])
                
                # For multi-leg orders, show each leg separately
                if len(legs) > 1:
                    for j, leg in enumerate(legs):
                        order_details.append({
                            "order_id": f"{order.get('id')}_{j}",
                            "direction": order.get("direction", "").lower(),
                            "position_effect": leg.get("position_effect"),
                            "processed_premium": float(order.get("processed_premium", 0) or 0) / len(legs),
                            "premium": float(order.get("processed_premium", 0) or 0) / len(legs),
                            "price": float(order.get("processed_premium", 0) or 0) / max(float(order.get("quantity", 1) or 1), 1) / len(legs),
                            "created_at": order.get("created_at"),
                            "option_type": leg.get("option_type", "unknown"),
                            "strike_price": float(leg.get("strike_price", 0) or 0),
                            "expiration_date": leg.get("expiration_date", "unknown"),
                            "transaction_side": leg.get("side", "unknown"),
                            "state": order.get("state", "unknown"),
                            "strategy": f"{leg.get('side', '')} to {leg.get('position_effect', '')}".title(),
                            "quantity": float(order.get("quantity", 0) or 0),
                            "leg_type": f"Leg {j+1} of {len(legs)}"
                        })
                else:
                    # Single leg order
                    leg = legs[0] if legs else {}
                    order_details.append({
                        "order_id": order.get("id"),
                        "direction": order.get("direction", "").lower(),
                        "position_effect": leg.get("position_effect"),
                        "processed_premium": float(order.get("processed_premium", 0) or 0),
                        "premium": float(order.get("processed_premium", 0) or 0),
                        "price": float(order.get("processed_premium", 0) or 0) / max(float(order.get("quantity", 1) or 1), 1),
                        "created_at": order.get("created_at"),
                        "option_type": leg.get("option_type", "unknown"),
                        "strike_price": float(leg.get("strike_price", 0) or 0),
                        "expiration_date": leg.get("expiration_date", "unknown"),
                        "transaction_side": leg.get("side", "unknown"),
                        "state": order.get("state", "unknown"),
                        "strategy": order.get("strategy", "unknown"),
                        "quantity": float(order.get("quantity", 0) or 0)
                    })
            
            # Create unique chain ID based on strikes and dates
            initial_strike = strike_progression[0] if strike_progression else "unknown"
            chain_id = f"{symbol}_{option_type}_{initial_strike}_{first_order.get('created_at', '')[:10]}"
            
            # Determine the latest position (for active chains only)
            latest_position = None
            if status == "active" and order_details:
                # Find the most recent open position
                for order_detail in reversed(order_details):
                    if order_detail.get("position_effect") == "open":
                        latest_position = {
                            "strike_price": order_detail.get("strike_price"),
                            "expiration_date": order_detail.get("expiration_date"),
                            "option_type": order_detail.get("option_type")
                        }
                        break
            
            return {
                "is_rolled_chain": True,
                "chain_id": chain_id,
                "underlying_symbol": symbol,
                "option_type": option_type,
                "order_count": len(orders),
                "status": status,
                "total_credits": total_credits,
                "total_debits": total_debits,
                "net_premium": net_premium,
                "total_pnl": net_premium,  # Simplified P&L
                "start_date": start_date,
                "last_activity": last_activity,
                "strike_progression": strike_progression,
                "initial_strike": initial_strike,
                "final_strike": strike_progression[-1] if strike_progression else "unknown",
                "roll_count": len(orders) - 1,  # Number of rolls (orders - 1)
                "latest_position": latest_position,  # Add latest position for active chains
                "total_orders": len(order_details),
                "orders": order_details
            }
            
        except Exception as e:
            logger.error(f"Error analyzing strike chain {group_key}: {e}")
            return {"is_rolled_chain": False}
    
    def _calculate_strike_progression(self, orders: List[Dict[str, Any]]) -> List[float]:
        """Calculate the strike price progression through the chain"""
        progression = []
        
        for order in orders:
            legs = order.get("legs", [])
            
            # For single leg orders, use that strike
            if len(legs) == 1:
                strike = float(legs[0].get("strike_price", 0) or 0)
                if strike not in progression:
                    progression.append(strike)
            
            # For multi-leg orders, add the SELL TO OPEN strike (new position)
            elif len(legs) > 1:
                for leg in legs:
                    if (leg.get("position_effect", "").lower() == "open" and 
                        leg.get("side", "").lower() == "sell"):
                        strike = float(leg.get("strike_price", 0) or 0)
                        if strike not in progression:
                            progression.append(strike)
        
        return progression
    
    def _determine_strike_chain_status(self, orders: List[Dict[str, Any]]) -> str:
        """Determine if strike-based chain is active, closed, or expired"""
        # Look at the most recent order's legs
        latest_order = orders[-1]
        legs = latest_order.get("legs", [])
        
        # If latest order has only closing legs, chain is likely closed
        has_only_closes = (len(legs) > 0 and 
                          all(leg.get("position_effect") == "close" for leg in legs))
        if has_only_closes:
            return "closed"
        
        # If latest order has both close and open, it's likely still active
        has_open = any(leg.get("position_effect") == "open" for leg in legs)
        if has_open:
            return "active"
        
        # Check if any options have expired
        current_date = datetime.now().date()
        for leg in legs:
            try:
                exp_date_str = leg.get("expiration_date", "")
                if exp_date_str:
                    exp_date = datetime.strptime(exp_date_str, "%Y-%m-%d").date()
                    if exp_date < current_date:
                        return "expired"
            except ValueError:
                continue
        
        return "active"
    
    async def _analyze_chain(
        self, 
        group_key: str, 
        orders: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze a group of orders to create chain details"""
        try:
            if not orders:
                return {"is_rolled_chain": False}
            
            # Extract symbol and option type from group key
            symbol, option_type = group_key.split("_", 1)
            
            # Calculate basic metrics
            total_credits = 0.0
            total_debits = 0.0
            
            for order in orders:
                direction = order.get("direction", "").lower()
                processed_premium = float(order.get("processed_premium", 0) or 0)
                
                if direction == "credit":
                    total_credits += processed_premium
                elif direction == "debit":
                    total_debits += processed_premium
            
            net_premium = total_credits - total_debits
            
            # Determine chain status
            latest_order = orders[-1]  # Most recent
            status = self._determine_chain_status(orders)
            
            # Get date range
            first_order = orders[0]
            last_order = orders[-1]
            
            start_date = first_order.get("created_at")
            last_activity = last_order.get("created_at")
            
            # Create order details for frontend
            order_details = []
            for order in orders:
                legs = order.get("legs", [])
                for leg in legs:
                    order_details.append({
                        "order_id": order.get("id"),
                        "direction": order.get("direction", "").lower(),
                        "position_effect": leg.get("position_effect"),
                        "processed_premium": float(order.get("processed_premium", 0) or 0),
                        "premium": float(order.get("processed_premium", 0) or 0),
                        "price": float(order.get("processed_premium", 0) or 0) / max(float(order.get("quantity", 1) or 1), 1),
                        "created_at": order.get("created_at"),
                        "option_type": leg.get("option_type", "unknown"),
                        "strike_price": float(leg.get("strike_price", 0) or 0),
                        "expiration_date": leg.get("expiration_date", "unknown"),
                        "transaction_side": leg.get("side", "unknown"),
                        "state": order.get("state", "unknown"),
                        "strategy": order.get("strategy", "unknown"),
                        "quantity": float(order.get("quantity", 0) or 0)
                    })
            
            return {
                "is_rolled_chain": True,
                "chain_id": f"{group_key}_{first_order.get('created_at', '')[:10]}",
                "underlying_symbol": symbol,
                "option_type": option_type,
                "order_count": len(orders),
                "status": status,
                "total_credits": total_credits,
                "total_debits": total_debits,
                "net_premium": net_premium,
                "total_pnl": net_premium,  # Simplified P&L
                "start_date": start_date,
                "last_activity": last_activity,
                "orders": order_details
            }
            
        except Exception as e:
            logger.error(f"Error analyzing chain {group_key}: {e}")
            return {"is_rolled_chain": False}
    
    def _determine_chain_status(self, orders: List[Dict[str, Any]]) -> str:
        """Determine if chain is active, closed, or expired"""
        # Look at the most recent order's legs
        latest_order = orders[-1]
        legs = latest_order.get("legs", [])
        
        # If latest order has closing position effects, chain is likely closed
        has_close = any(leg.get("position_effect") == "close" for leg in legs)
        if has_close:
            return "closed"
        
        # Check if any options have expired
        current_date = datetime.now().date()
        for leg in legs:
            try:
                exp_date_str = leg.get("expiration_date", "")
                if exp_date_str:
                    exp_date = datetime.strptime(exp_date_str, "%Y-%m-%d").date()
                    if exp_date < current_date:
                        return "expired"
            except ValueError:
                continue
        
        return "active"
    
    def _calculate_summary(self, chains: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate summary statistics for all chains"""
        if not chains:
            return {
                "total_chains": 0,
                "active_chains": 0,
                "closed_chains": 0,
                "total_orders": 0,
                "net_premium_collected": 0.0,
                "total_pnl": 0.0,
                "avg_orders_per_chain": 0.0
            }
        
        active_chains = [c for c in chains if c.get("status") == "active"]
        closed_chains = [c for c in chains if c.get("status") == "closed"]
        
        total_orders = sum(c.get("order_count", 0) for c in chains)
        net_premium = sum(c.get("net_premium", 0) for c in chains)
        total_pnl = sum(c.get("total_pnl", 0) for c in chains)
        
        return {
            "total_chains": len(chains),
            "active_chains": len(active_chains),
            "closed_chains": len(closed_chains),
            "total_orders": total_orders,
            "net_premium_collected": net_premium,
            "total_pnl": total_pnl,
            "avg_orders_per_chain": total_orders / len(chains) if chains else 0.0
        }
    
    async def _load_raw_orders(self, days_back: int = 30) -> Dict[str, Any]:
        """
        Load raw orders directly from JSON files without any chain processing
        
        Args:
            days_back: Number of days to look back (for filtering)
            
        Returns:
            Dict with success flag and orders list
        """
        try:
            # Load all raw orders using existing method
            all_orders = await self._load_orders_from_files()
            
            if not all_orders:
                return {
                    'success': False,
                    'message': 'No orders found in JSON files',
                    'orders': []
                }
            
            # Filter by date if needed
            if days_back > 0:
                cutoff_date = datetime.now() - timedelta(days=days_back)
                filtered_orders = []
                
                for order in all_orders:
                    try:
                        created_at = order.get('created_at', '')
                        if created_at:
                            order_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            if order_date >= cutoff_date:
                                filtered_orders.append(order)
                    except:
                        # Include orders with invalid dates to be safe
                        filtered_orders.append(order)
                
                logger.info(f"Filtered {len(all_orders)} orders to {len(filtered_orders)} within {days_back} days")
                return {
                    'success': True,
                    'orders': filtered_orders,
                    'total_orders': len(all_orders),
                    'filtered_orders': len(filtered_orders)
                }
            else:
                return {
                    'success': True,
                    'orders': all_orders,
                    'total_orders': len(all_orders)
                }
                
        except Exception as e:
            logger.error(f"Error loading raw orders: {e}")
            return {
                'success': False,
                'message': str(e),
                'orders': []
            }
    
    def _generate_cache_key(
        self, 
        days_back: int, 
        symbol: Optional[str], 
        status: Optional[str], 
        min_orders: int
    ) -> str:
        """Generate cache key for request parameters"""
        key_data = f"json_rolled:{days_back}:{symbol or 'all'}:{status or 'all'}:{min_orders}"
        return f"json_rolled_options:{hashlib.md5(key_data.encode()).hexdigest()}"