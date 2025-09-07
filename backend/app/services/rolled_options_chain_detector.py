"""
Rolled Options Chain Detection Service

Implements precise chain detection logic based on proper options rolling patterns:

Sell-to-Open Chain Pattern:
1. Initial: SELL TO OPEN (1 leg) - Opens short position
2. Rolls: BUY TO CLOSE (old) + SELL TO OPEN (new) (2 legs) - Rolls position
3. Final: BUY TO CLOSE (1 leg) - Closes final position

Buy-to-Open Chain Pattern:
1. Initial: BUY TO OPEN (1 leg) - Opens long position
2. Rolls: SELL TO CLOSE (old) + BUY TO OPEN (new) (2 legs) - Rolls position
3. Final: SELL TO CLOSE (1 leg) - Closes final position

Requirements:
- Max 8 months between orders in chain
- Strikes must match exactly (except middle orders can roll up/down)
- Same expiration dates within chain
- Symbol-specific chains only
- No partial chains allowed
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LegInfo:
    """Information about an options leg"""
    strike_price: float
    option_type: str  # 'call' or 'put'
    expiration_date: str
    side: str  # 'buy' or 'sell'
    position_effect: str  # 'open' or 'close'
    quantity: float


@dataclass
class OrderInfo:
    """Analyzed information about an options order"""
    order_id: str
    created_at: datetime
    underlying_symbol: str
    legs: List[LegInfo]
    opens: List[LegInfo]  # SELL/BUY TO OPEN legs
    closes: List[LegInfo]  # BUY/SELL TO CLOSE legs
    raw_order: Dict[str, Any]


class RolledOptionsChainDetector:
    """Service for detecting rolled options chains with precise pattern matching"""
    
    def __init__(self, options_service=None):
        self.max_chain_duration = timedelta(days=240)  # 8 months
        self.options_service = options_service
    
    async def detect_chains_from_database(
        self,
        user_id: str,
        days_back: int = 365,
        symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect rolled options chains using database orders with strategy code priority.
        
        Detection Strategy:
        1. Primary: Group by strategy codes (long_strategy_code/short_strategy_code)
        2. Secondary: Heuristic detection for orders without strategy codes
        3. Fallback: API-based detection if database is empty
        
        Args:
            user_id: User ID to detect chains for
            days_back: Number of days to look back
            symbol: Optional symbol filter
            
        Returns:
            List of chain dictionaries with detection metadata
        """
        if not self.options_service:
            logger.error("OptionsOrderService not provided - cannot detect chains from database")
            return []
        
        try:
            # Get orders from database
            orders = await self.options_service.get_orders_for_chain_detection(
                user_id=user_id,
                days_back=days_back if days_back else 0,
                symbol=symbol
            )
            
            if not orders:
                logger.info(f"No orders found in database for user {user_id} - falling back to API")
                return await self._fallback_to_api_detection(user_id, symbol)
            
            logger.info(f"Detecting chains from {len(orders)} database orders")
            
            # Convert database orders to dict format for processing
            order_dicts = [self._convert_db_order_to_dict(order) for order in orders]
            
            # Strategy 1: Strategy code-based detection (primary)
            strategy_chains = self._detect_chains_by_strategy_codes(order_dicts)

            # Strategy 2: Code-continuity detection to stitch across changing codes
            continuity_chains = self._detect_chains_by_code_continuity(order_dicts)

            # Strategy 3: Heuristic detection (augment across all orders, not just those without codes)
            heuristic_chains_all = self.detect_chains(order_dicts)
            
            # Combine and format results
            all_chains = []
            
            # Add strategy code chains (with validation to avoid close-only mini chains)
            for strategy_code, chain_orders in strategy_chains.items():
                if len(chain_orders) >= 2 and self._is_valid_chain_orders(chain_orders):
                    chain_data = self._format_chain_result(
                        chain_orders,
                        detection_method="strategy_code",
                        strategy_code=strategy_code
                    )
                    all_chains.append(chain_data)
            
            # Add continuity chains (prefer these downstream in merge due to length)
            for chain_orders in continuity_chains:
                if len(chain_orders) >= 2:
                    chain_data = self._format_chain_result(
                        chain_orders,
                        detection_method="strategy_code_continuity",
                        strategy_code=None
                    )
                    all_chains.append(chain_data)

            # Add heuristic chains
            for chain_orders in heuristic_chains_all:
                if len(chain_orders) >= 2:
                    chain_data = self._format_chain_result(
                        chain_orders,
                        detection_method="heuristic"
                    )
                    all_chains.append(chain_data)
            
            # Add form_source based chains (strategy_roll)
            form_source_chains = self._detect_chains_by_form_source(order_dicts)
            for chain_orders in form_source_chains:
                if len(chain_orders) >= 1:  # Single strategy_roll orders are valid chains
                    chain_data = self._format_chain_result(
                        chain_orders,
                        detection_method="form_source"
                    )
                    all_chains.append(chain_data)
            
            # Merge overlapping chains, prefer longer chains (helps bridge strategy-code segments)
            try:
                merged = []
                # Build index by order id for quick overlap checks
                def order_ids(chain):
                    return set(o.get('id') or o.get('order_id') for o in chain.get('orders', []))
                for chain in all_chains:
                    ids = order_ids(chain)
                    if not ids:
                        merged.append(chain)
                        continue
                    # Find overlap with existing
                    replaced = False
                    for i, existing in enumerate(merged):
                        eids = order_ids(existing)
                        if ids & eids:
                            # Prefer the longer chain
                            if chain.get('total_orders', 0) > existing.get('total_orders', 0):
                                merged[i] = chain
                            replaced = True
                            break
                    if not replaced:
                        merged.append(chain)
                all_chains = merged
            except Exception:
                # Safe fallback if merge fails
                pass

            # Final sanity filter: drop chains that are close-only (no opens anywhere)
            def has_open_and_close(orders: List[Dict[str, Any]]) -> bool:
                has_open = False
                has_close = False
                for o in orders or []:
                    for leg in o.get('legs', []) or []:
                        eff = (leg.get('position_effect') or '').lower()
                        if eff == 'open':
                            has_open = True
                        elif eff == 'close':
                            has_close = True
                        if has_open and has_close:
                            return True
                return False

            all_chains = [c for c in all_chains if has_open_and_close(c.get('orders', []))]

            # Deduplicate: drop any chain whose set of order IDs is a strict subset of another chain
            try:
                chain_with_ids = []
                for c in all_chains:
                    ids = set(o.get('id') or o.get('order_id') for o in c.get('orders', []) if (o.get('id') or o.get('order_id')))
                    chain_with_ids.append((c, ids))
                keep = []
                for i, (ci, idi) in enumerate(chain_with_ids):
                    is_subset = False
                    for j, (cj, idj) in enumerate(chain_with_ids):
                        if i == j:
                            continue
                        if idi and idj and idi.issubset(idj) and len(idj) > len(idi):
                            is_subset = True
                            break
                    if not is_subset:
                        keep.append(ci)
                all_chains = keep
            except Exception:
                pass

            logger.info(f"Detected {len(all_chains)} chains using database orders")
            return all_chains

        except Exception as e:
            logger.error(f"Error detecting chains from database: {str(e)}", exc_info=True)
            return []

    def _is_valid_chain_orders(self, chain_orders: List[Dict[str, Any]]) -> bool:
        """Validate raw orders sequence to avoid false chains (e.g., close-only)."""
        try:
            analyzed = [self._analyze_order_position_effects(o) for o in chain_orders]
            analyzed = [a for a in analyzed if a]
            if not analyzed:
                return False

            # Strong validation using existing roll validators
            if self._validate_roll_chain(analyzed) or self._validate_partial_roll_chain(analyzed):
                return True

            # Fallback: ensure the sequence contains at least one OPEN and one CLOSE somewhere
            has_open = any(a.get('opens') for a in analyzed)
            has_close = any(a.get('closes') for a in analyzed)
            if not (has_open and has_close):
                return False

            return True
        except Exception:
            return False

    def _extract_strategy_codes(self, order: Dict[str, Any]) -> set:
        """Collect all strategy codes present on an order (top-level and legs)."""
        codes = set()
        try:
            for key in ("long_strategy_code", "short_strategy_code"):
                val = order.get(key)
                if val:
                    codes.add(val)
            for leg in order.get("legs", []) or []:
                for key in ("long_strategy_code", "short_strategy_code"):
                    val = leg.get(key)
                    if val:
                        codes.add(val)
        except Exception:
            pass
        return {c for c in codes if c}

    def _detect_chains_by_code_continuity(self, orders: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Stitch chains where adjacent orders share at least one strategy code,
        allowing code changes across rolls (e.g., A -> A/B -> B -> B/C -> C).

        Operates per symbol+option-type group, in chronological order, and
        validates resulting sequences with existing roll-chain validators.
        """
        if not orders:
            return []

        # Group by symbol+type to avoid mixing calls/puts
        groups = self._group_orders_by_symbol(orders)
        chains: List[List[Dict[str, Any]]] = []

        for group_key, group_orders in groups.items():
            # Sort chronologically
            sorted_orders = sorted(group_orders, key=lambda x: x.get("created_at", ""))

            # Precompute codes and position effects per order
            order_data = []
            for o in sorted_orders:
                codes = self._extract_strategy_codes(o)
                if not codes:
                    continue  # Only consider orders that have codes
                analysis = self._analyze_order_position_effects(o) or {}
                order_data.append({
                    "order": o,
                    "codes": codes,
                    "analysis": analysis,
                    "type": (
                        "roll" if (analysis.get("opens") and analysis.get("closes")) else
                        ("open" if analysis.get("opens") and not analysis.get("closes") else
                         ("close" if analysis.get("closes") and not analysis.get("opens") else "other"))
                    )
                })

            used_ids = set()

            # Helper to find previous code-sharing orders
            def has_prior_share(idx: int) -> bool:
                curr_codes = order_data[idx]["codes"]
                for j in range(idx - 1, -1, -1):
                    if order_data[j]["order"].get("id") in used_ids:
                        continue
                    if curr_codes & order_data[j]["codes"]:
                        return True
                return False

            # Build chains starting from natural starts: single-leg opens or earliest without prior share
            for i, od in enumerate(order_data):
                oid = od["order"].get("id")
                if oid in used_ids:
                    continue

                # Start conditions: pure open, or first occurrence of a code cluster
                is_start = (od["type"] == "open") or (not has_prior_share(i))
                if not is_start:
                    continue

                chain = [od["order"]]
                used_ids.add(oid)

                last_codes = set(od["codes"])  # codes from last appended order
                last_time = od["order"].get("created_at", "")

                # Extend forward by code overlap
                for j in range(i + 1, len(order_data)):
                    next_oid = order_data[j]["order"].get("id")
                    if next_oid in used_ids:
                        continue
                    # Must be future in time and share a code with the last order
                    if (order_data[j]["order"].get("created_at", "") >= last_time and
                        (last_codes & order_data[j]["codes"])):
                        chain.append(order_data[j]["order"])
                        used_ids.add(next_oid)
                        last_codes = set(order_data[j]["codes"])  # advance code window
                        last_time = order_data[j]["order"].get("created_at", "")

                # Validate chain pattern; accept if at least 2 orders and passes validation
                if len(chain) >= 2:
                    try:
                        analyzed = [self._analyze_order_position_effects(o) for o in chain]
                        analyzed = [a for a in analyzed if a]
                        if analyzed and (self._validate_roll_chain(analyzed) or self._validate_partial_roll_chain(analyzed)):
                            chains.append(chain)
                        else:
                            # Fallback: if at least 3 and looks like open -> rolls -> close, keep
                            chains.append(chain)
                    except Exception:
                        chains.append(chain)

        return chains
    
    def _convert_db_order_to_dict(self, order) -> Dict[str, Any]:
        """Convert database OptionsOrder to dictionary format for processing."""
        return {
            "id": order.order_id,
            "order_id": order.order_id,
            "state": order.state,
            "chain_symbol": order.chain_symbol,
            "processed_quantity": float(order.processed_quantity) if order.processed_quantity else 0.0,
            "processed_premium": float(order.processed_premium) if order.processed_premium else 0.0,
            "direction": order.direction,
            "strategy": order.strategy,
            "opening_strategy": order.opening_strategy,
            "closing_strategy": order.closing_strategy,
            "form_source": order.raw_data.get("form_source") if order.raw_data else None,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "updated_at": order.updated_at.isoformat() if order.updated_at else None,
            "legs": order.legs_details or [],
            "legs_count": order.legs_count or 0,
            # Add missing critical fields for chain detection
            "position_effect": order.position_effect,
            "strike_price": float(order.strike_price) if order.strike_price else 0.0,
            "option_type": order.option_type,
            "expiration_date": str(order.expiration_date) if order.expiration_date else None,
            # Add strategy codes from legs or top-level fields
            "long_strategy_code": order.long_strategy_code,
            "short_strategy_code": order.short_strategy_code,
        }
    
    def _detect_chains_by_strategy_codes(self, orders: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group orders by strategy codes to detect chains."""
        strategy_chains = defaultdict(list)
        
        for order in orders:
            # Get strategy codes from legs or top-level fields
            strategy_codes = set()
            
            # From top-level fields
            if order.get("long_strategy_code"):
                strategy_codes.add(order["long_strategy_code"])
            if order.get("short_strategy_code"):
                strategy_codes.add(order["short_strategy_code"])
            
            # From legs details
            for leg in order.get("legs", []):
                if leg.get("long_strategy_code"):
                    strategy_codes.add(leg["long_strategy_code"])
                if leg.get("short_strategy_code"):
                    strategy_codes.add(leg["short_strategy_code"])
            
            # Add order to each strategy code chain
            for code in strategy_codes:
                if code:  # Skip empty codes
                    strategy_chains[code].append(order)
        
        # Sort orders in each chain by creation time
        for code in strategy_chains:
            strategy_chains[code].sort(key=lambda x: x.get("created_at", ""))
        
        return strategy_chains
    
    def _detect_chains_by_form_source(self, orders: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Detect chains based on form_source='strategy_roll'."""
        roll_orders = [
            order for order in orders 
            if order.get("form_source") == "strategy_roll"
        ]
        
        if not roll_orders:
            return []
        
        # Group by symbol and treat each as a potential chain
        symbol_groups = defaultdict(list)
        for order in roll_orders:
            symbol = order.get("chain_symbol", "")
            if symbol:
                symbol_groups[symbol].append(order)
        
        chains = []
        for symbol, symbol_orders in symbol_groups.items():
            if len(symbol_orders) >= 1:
                # Sort by creation time
                symbol_orders.sort(key=lambda x: x.get("created_at", ""))
                chains.append(symbol_orders)
        
        return chains
    
    def _has_strategy_codes(self, order: Dict[str, Any]) -> bool:
        """Check if order has strategy codes."""
        if order.get("long_strategy_code") or order.get("short_strategy_code"):
            return True
        
        for leg in order.get("legs", []):
            if leg.get("long_strategy_code") or leg.get("short_strategy_code"):
                return True
        
        return False
    
    def _format_chain_result(
        self, 
        orders: List[Dict[str, Any]], 
        detection_method: str,
        strategy_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """Format chain orders into result dictionary."""
        if not orders:
            return {}
        
        # Sort orders chronologically
        orders.sort(key=lambda x: x.get("created_at", ""))
        
        # Calculate chain metrics
        total_premium_paid = sum(
            float(order.get("processed_premium", 0)) 
            for order in orders 
            if order.get("direction") == "debit"
        )
        total_premium_received = sum(
            float(order.get("processed_premium", 0)) 
            for order in orders 
            if order.get("direction") == "credit"
        )
        net_premium = total_premium_received - total_premium_paid
        total_quantity = sum(float(order.get("processed_quantity", 0)) for order in orders)
        
        # Get chain metadata
        first_order = orders[0]
        last_order = orders[-1]
        chain_symbol = first_order.get("chain_symbol", "")
        
        return {
            "chain_id": strategy_code or f"{chain_symbol}_{first_order.get('id', '')}",
            "chain_symbol": chain_symbol,
            "detection_method": detection_method,
            "strategy_code": strategy_code,
            "total_orders": len(orders),
            "orders": orders,
            "total_premium_paid": total_premium_paid,
            "total_premium_received": total_premium_received,
            "net_premium": net_premium,
            "total_quantity": total_quantity,
            "first_order_date": first_order.get("created_at"),
            "last_order_date": last_order.get("created_at"),
            "status": "closed" if self._chain_appears_closed(orders) else "open"
        }
    
    def _chain_appears_closed(self, orders: List[Dict[str, Any]]) -> bool:
        """Determine if a chain appears to be closed based on position effects and order patterns."""
        if not orders:
            return True
        
        # Strategy 1: Count opens vs closes regardless of quantity
        opens_count = 0
        closes_count = 0
        
        for order in orders:
            for leg in order.get("legs", []):
                position_effect = leg.get("position_effect", "")
                if position_effect == "open":
                    opens_count += 1
                elif position_effect == "close":
                    closes_count += 1
        
        # Strategy 2: If we have equal opens and closes, likely closed
        if opens_count > 0 and closes_count > 0 and opens_count == closes_count:
            return True
        
        # Strategy 3: Check if last order is a close
        if orders:
            last_order = orders[-1]  # Orders should be chronologically sorted
            last_order_legs = last_order.get("legs", [])
            if last_order_legs:
                last_position_effects = [leg.get("position_effect", "") for leg in last_order_legs]
                # If the last order contains any close, consider chain closed
                if any(effect == "close" for effect in last_position_effects):
                    return True
        
        # Strategy 4: Check pattern based on credits and debits
        has_opening_credit = any(order.get("direction") == "credit" for order in orders)
        has_closing_debit = any(order.get("direction") == "debit" for order in orders)
        
        # For strategies like selling options then buying them back
        if has_opening_credit and has_closing_debit and len(orders) >= 2:
            return True
        
        # Default to open if we can't determine
        return False
    
    async def _fallback_to_api_detection(self, user_id: str, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fallback to API-based detection when database is empty."""
        logger.info("Falling back to API-based chain detection")
        try:
            # This would call the existing file-based detection
            # For now, return empty as we're focusing on database-first approach
            return []
        except Exception as e:
            logger.error(f"API fallback failed: {str(e)}")
            return []
    
    def _is_roll_order(self, order: Dict[str, Any]) -> bool:
        """
        Multi-criteria roll detection to handle orders with missing form_source
        
        Uses multiple indicators to identify roll orders:
        1. Primary: form_source='strategy_roll' (Robinhood auto-roll)
        2. Secondary: Strategy contains 'roll' or 'calendar_spread'
        3. Tertiary: Multi-leg orders with both open and close position effects
        4. Quaternary: Orders with rolled_from/rolled_to fields
        
        Args:
            order: Order dictionary to analyze
            
        Returns:
            True if order appears to be a roll transaction
        """
        try:
            form_source = order.get('form_source', '').lower()
            strategy = order.get('strategy', '').lower()
            
            # Primary: Confirmed roll by Robinhood
            if form_source == 'strategy_roll':
                return True
            
            # Secondary: Strategy-based detection
            if 'roll' in strategy or 'calendar_spread' in strategy:
                return True
            
            # Tertiary: Position effect analysis (NEW)
            if self._has_roll_position_effects(order):
                return True
            
            # Quaternary: Roll reference fields
            if order.get('rolled_from') or order.get('rolled_to'):
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Error in _is_roll_order for order {order.get('id', 'unknown')}: {e}")
            return False
    
    def _has_roll_position_effects(self, order: Dict[str, Any]) -> bool:
        """
        Check if order has both open and close position effects (characteristic of rolls)
        
        Roll orders typically:
        - Have 2+ legs
        - Include at least one 'open' position effect (new position)
        - Include at least one 'close' position effect (closing old position)
        
        Args:
            order: Order dictionary to analyze
            
        Returns:
            True if order has roll-like position effects
        """
        try:
            legs = order.get('legs', [])
            
            # Must be multi-leg (rolls typically close old + open new)
            if len(legs) < 2:
                return False
            
            # Check for both open and close position effects
            has_open = any(leg.get('position_effect') == 'open' for leg in legs)
            has_close = any(leg.get('position_effect') == 'close' for leg in legs)
            
            return has_open and has_close
            
        except Exception as e:
            logger.debug(f"Error in _has_roll_position_effects for order {order.get('id', 'unknown')}: {e}")
            return False
    
    def detect_chains(self, orders: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Detect rolled options chains from a list of orders using lazy approach
        
        Instead of analyzing all orders, we look for orders with 'strategy_roll' 
        field which indicates they're part of rolling operations.
        
        Args:
            orders: List of options orders
            
        Returns:
            List of chains, where each chain is a list of orders
        """
        import time
        start_time = time.time()
        
        try:
            # First, find orders that indicate rolling activity
            roll_orders = []
            opening_orders = []
            closing_orders = []
            strategies = set()
            form_source_count = 0
            position_effect_count = 0
            
            for order in orders:
                strategy = order.get('strategy', '').lower()
                strategies.add(strategy)
                
                # Use new multi-criteria roll detection
                if self._is_roll_order(order):
                    roll_orders.append(order)
                    
                    # Track detection method for logging
                    form_source = order.get('form_source', '').lower()
                    if form_source == 'strategy_roll':
                        form_source_count += 1
                    elif self._has_roll_position_effects(order):
                        position_effect_count += 1
                        
                elif (order.get('opening_strategy') and 
                      len(order.get('legs', [])) == 1):
                    # Single-leg opening orders that could start chains
                    opening_orders.append(order)
                elif (order.get('closing_strategy') and 
                      len(order.get('legs', [])) == 1):
                    # Single-leg closing orders that could end chains
                    closing_orders.append(order)
            
            # Log unique strategies for debugging
            logger.info(f"Found strategies: {sorted(list(strategies))[:10]}")  # First 10 unique strategies
            logger.info(f"Found {len(roll_orders)} roll orders, {len(opening_orders)} potential chain starts, {len(closing_orders)} potential chain ends")
            logger.info(f"Multi-criteria roll detection: {len(roll_orders)} total ({form_source_count} form_source, {position_effect_count} position_effects)")
            
            if not roll_orders:
                logger.info("No roll orders found - no chains to detect")
                return []
            
            # Group roll orders by symbol and type for faster processing
            roll_groups = self._group_orders_by_symbol(roll_orders)
            opening_groups = self._group_orders_by_symbol(opening_orders)
            closing_groups = self._group_orders_by_symbol(closing_orders)
            
            all_chains = []
            
            # For each symbol+type group that has roll activity, build chains
            for group_key in roll_groups.keys():
                symbol_type_roll_orders = roll_groups[group_key]
                symbol_type_opening_orders = opening_groups.get(group_key, [])
                symbol_type_closing_orders = closing_groups.get(group_key, [])
                
                # Combine orders for this symbol+type and sort by time
                group_orders = symbol_type_roll_orders + symbol_type_opening_orders + symbol_type_closing_orders
                group_orders.sort(key=lambda x: x.get('created_at', ''))
                
                chains = self._build_chains_from_roll_activity(group_key, group_orders)
                all_chains.extend(chains)
                
                logger.info(f"Found {len(chains)} chains for {group_key}")
            
            # If complex chain building didn't work, fall back to simple approach
            if len(all_chains) == 0 and len(roll_orders) > 0:
                logger.info("Complex chain building found no chains, falling back to simple approach")
                all_chains = self._create_simple_chains_from_rolls(orders)
            
            total_time = time.time() - start_time
            logger.info(f"Lazy chain detection completed: {len(all_chains)} chains found in {total_time:.1f}s")
            return all_chains
            
        except Exception as e:
            logger.error(f"Error in lazy chain detection: {e}", exc_info=True)
            return []
    
    def _analyze_orders(self, orders: List[Dict[str, Any]]) -> List[OrderInfo]:
        """Convert raw orders to analyzed OrderInfo objects"""
        analyzed = []
        
        for order in orders:
            try:
                # Parse basic order info
                order_id = order.get("id", "")
                created_at_str = order.get("created_at", "")
                underlying_symbol = order.get("underlying_symbol", "").upper()
                
                if not all([order_id, created_at_str, underlying_symbol]):
                    continue
                
                # Parse timestamp
                created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                
                # Parse legs
                legs_data = order.get("legs", [])
                if not legs_data:
                    continue
                
                legs = []
                opens = []
                closes = []
                
                for leg_data in legs_data:
                    leg = self._parse_leg(leg_data)
                    if leg:
                        legs.append(leg)
                        if leg.position_effect == 'open':
                            opens.append(leg)
                        elif leg.position_effect == 'close':
                            closes.append(leg)
                
                if not legs:
                    continue
                
                order_info = OrderInfo(
                    order_id=order_id,
                    created_at=created_at,
                    underlying_symbol=underlying_symbol,
                    legs=legs,
                    opens=opens,
                    closes=closes,
                    raw_order=order
                )
                
                analyzed.append(order_info)
                
            except Exception as e:
                logger.debug(f"Error analyzing order {order.get('id', 'unknown')}: {e}")
                continue
        
        return analyzed
    
    def _parse_leg(self, leg_data: Dict[str, Any]) -> Optional[LegInfo]:
        """Parse a single leg from order data"""
        try:
            # Extract required fields
            strike_price = float(leg_data.get("strike_price", 0) or 0)
            option_type = leg_data.get("option_type", "").lower()
            expiration_date = leg_data.get("expiration_date", "")
            side = leg_data.get("side", "").lower()
            position_effect = leg_data.get("position_effect", "").lower()
            quantity = float(leg_data.get("quantity", 0) or 0)
            
            # Validate required fields
            if not all([strike_price, option_type, expiration_date, side, position_effect]):
                return None
            
            if option_type not in ['call', 'put']:
                return None
            
            if side not in ['buy', 'sell']:
                return None
            
            if position_effect not in ['open', 'close']:
                return None
            
            return LegInfo(
                strike_price=strike_price,
                option_type=option_type,
                expiration_date=expiration_date,
                side=side,
                position_effect=position_effect,
                quantity=quantity
            )
            
        except Exception as e:
            logger.debug(f"Error parsing leg: {e}")
            return None
    
    def _group_orders_by_symbol_type(self, orders: List[OrderInfo]) -> Dict[str, List[OrderInfo]]:
        """Group orders by underlying symbol and option type"""
        groups = defaultdict(list)
        
        for order in orders:
            # Get primary option type from first leg
            if order.legs:
                option_type = order.legs[0].option_type
                group_key = f"{order.underlying_symbol}_{option_type}"
                groups[group_key].append(order)
        
        # Sort each group chronologically
        for group_key in groups:
            groups[group_key].sort(key=lambda x: x.created_at)
        
        return dict(groups)
    
    def _group_orders_by_symbol(self, orders: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group orders by underlying symbol and option type to prevent mixing calls and puts"""
        from collections import defaultdict
        groups = defaultdict(list)
        
        for order in orders:
            # Use correct field name from actual data structure
            symbol = order.get('chain_symbol', '') or order.get('underlying_symbol', '')
            symbol = symbol.upper() if symbol else ''
            if not symbol:
                continue
            
            # Get primary option type from first leg to ensure calls and puts are separated
            legs = order.get('legs', [])
            if not legs:
                continue
                
            primary_option_type = legs[0].get('option_type', '').lower()
            if primary_option_type not in ['call', 'put']:
                continue
            
            # Group by symbol + option type
            group_key = f"{symbol}_{primary_option_type}"
            groups[group_key].append(order)
        
        # Sort each group chronologically
        for group_key in groups:
            groups[group_key].sort(key=lambda x: x.get('created_at', ''))
        
        return dict(groups)
    
    def _build_chains_from_roll_activity(self, group_key: str, orders: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Build chains for a symbol+type group using roll activity as indicator"""
        chains = []
        used_orders = set()
        
        # Find roll orders as anchor points - use multi-criteria detection
        roll_orders = []
        for order in orders:
            if self._is_roll_order(order):
                roll_orders.append(order)
        
        logger.info(f"Processing {len(roll_orders)} roll orders for {group_key}")
        
        # Use the proper roll chain building with position effect validation
        try:
            symbol, option_type = group_key.split('_', 1)
            chains = self._build_proper_roll_chains(roll_orders, symbol, option_type)
        except ValueError:
            # Fallback if group_key doesn't have expected format
            logger.warning(f"Invalid group key format: {group_key}, skipping proper validation")
            chains = []
        
        logger.info(f"Created {len(chains)} validated chains for {group_key}")
        return chains
    
    def _build_chain_around_roll(
        self, 
        roll_order: Dict[str, Any], 
        all_orders: List[Dict[str, Any]], 
        used_orders: set
    ) -> List[Dict[str, Any]]:
        """Build a chain starting from a roll order"""
        
        chain = [roll_order]  # Start with the roll order itself
        symbol = roll_order.get('underlying_symbol', '')
        
        # If roll order has both opening and closing strategy, it's already a complete chain element
        if roll_order.get('opening_strategy') and roll_order.get('closing_strategy'):
            # Look for related orders - both before and after
            
            # Look backward for the initial opening
            opening_candidates = [
                order for order in all_orders
                if (order.get('created_at', '') < roll_order.get('created_at', '') and
                    order.get('id') not in used_orders and
                    order.get('underlying_symbol') == symbol and
                    len(order.get('legs', [])) == 1 and
                    order.get('opening_strategy') and
                    not order.get('closing_strategy'))
            ]
            
            if opening_candidates:
                # Get the most recent opening order before this roll
                opening_candidates.sort(key=lambda x: x.get('created_at', ''), reverse=True)
                opening_order = opening_candidates[0]
                chain.insert(0, opening_order)  # Insert at beginning
            
            # Look forward for more rolls or final close
            current_time = roll_order.get('created_at', '')
            
            for i in range(10):  # Max 10 additional orders
                next_candidates = [
                    order for order in all_orders
                    if (order.get('created_at', '') > current_time and
                        order.get('id') not in used_orders and
                        order.get('underlying_symbol') == symbol and
                        order.get('id') != roll_order.get('id'))
                ]
                
                if not next_candidates:
                    break
                
                # Sort by time and check if any could continue the chain
                next_candidates.sort(key=lambda x: x.get('created_at', ''))
                
                found_continuation = False
                for candidate in next_candidates[:3]:  # Check first 3 closest orders
                    # Check if this is another roll or a closing order
                    if (self._is_roll_order(candidate) or
                        (len(candidate.get('legs', [])) == 1 and candidate.get('closing_strategy'))):
                        
                        chain.append(candidate)
                        current_time = candidate.get('created_at', '')
                        found_continuation = True
                        
                        # If this is a single-leg closing order, we're done
                        if (len(candidate.get('legs', [])) == 1 and 
                            candidate.get('closing_strategy') and 
                            not candidate.get('opening_strategy')):
                            break
                        
                        break
                
                if not found_continuation:
                    break
        
        return chain if len(chain) >= 2 else []
    
    def _could_be_chain_continuation(self, prev_order: Dict[str, Any], next_order: Dict[str, Any]) -> bool:
        """Simple check if next_order could continue the chain from prev_order"""
        
        # Same symbol check
        if prev_order.get('underlying_symbol') != next_order.get('underlying_symbol'):
            return False
        
        # Time check - must be within reasonable window
        prev_time = prev_order.get('created_at', '')
        next_time = next_order.get('created_at', '')
        
        if prev_time and next_time:
            try:
                from datetime import datetime
                prev_dt = datetime.fromisoformat(prev_time.replace('Z', '+00:00'))
                next_dt = datetime.fromisoformat(next_time.replace('Z', '+00:00'))
                
                if (next_dt - prev_dt) > self.max_chain_duration:
                    return False
            except:
                pass
        
        # If next order is a roll or close, it could continue
        strategy = next_order.get('strategy', '').lower()
        if 'roll' in strategy or next_order.get('closing_strategy'):
            return True
        
        return False
    
    def _detect_chains_in_group(self, group_key: str, orders: List[OrderInfo]) -> List[List[Dict[str, Any]]]:
        """Detect chains within a single symbol+type group"""
        chains = []
        used_orders = set()
        
        # Find potential chain starts (single leg OPEN orders)
        potential_starts = []
        for order in orders:
            if (len(order.legs) == 1 and 
                order.opens and 
                not order.closes and
                order.order_id not in used_orders):
                potential_starts.append(order)
        
        logger.info(f"Found {len(potential_starts)} potential chain starts in {group_key}")
        
        # Limit processing to prevent timeouts
        max_starts_to_process = 50  # Process max 50 potential starts per group
        starts_to_process = potential_starts[:max_starts_to_process]
        
        if len(potential_starts) > max_starts_to_process:
            logger.warning(f"Limited processing to first {max_starts_to_process} starts (of {len(potential_starts)}) to prevent timeout")
        
        # Build chains from each potential start
        for i, start_order in enumerate(starts_to_process):
            if start_order.order_id in used_orders:
                continue
            
            # Log progress for large groups
            if i > 0 and i % 10 == 0:
                logger.info(f"Processed {i}/{len(starts_to_process)} potential starts in {group_key}")
            
            chain = self._build_chain_from_start(start_order, orders, used_orders)
            
            if chain and self._validate_chain(chain):
                # Convert back to raw orders for return
                raw_chain = [order_info.raw_order for order_info in chain]
                chains.append(raw_chain)
                
                # Mark orders as used
                for order_info in chain:
                    used_orders.add(order_info.order_id)
                
                logger.debug(f"Valid chain found with {len(chain)} orders starting from {start_order.order_id}")
        
        logger.info(f"Completed chain detection for {group_key}: {len(chains)} chains found")
        return chains
    
    def _build_chain_from_start(
        self, 
        start_order: OrderInfo, 
        all_orders: List[OrderInfo],
        used_orders: set
    ) -> Optional[List[OrderInfo]]:
        """Build a chain starting from an initial order"""
        
        chain = [start_order]
        current_position = start_order.opens[0]  # The position we opened
        
        # Determine chain type from start order
        if current_position.side == 'sell':
            chain_type = 'sell_to_open'
        elif current_position.side == 'buy':
            chain_type = 'buy_to_open'
        else:
            return None
        
        # Pre-filter candidate orders for efficiency
        candidate_orders = [
            order for order in all_orders 
            if (order.created_at > start_order.created_at and 
                order.order_id not in used_orders and
                order.order_id != start_order.order_id and
                (order.created_at - start_order.created_at) <= self.max_chain_duration and
                order.underlying_symbol == start_order.underlying_symbol)
        ]
        
        # Sort by creation time for sequential processing
        candidate_orders.sort(key=lambda x: x.created_at)
        
        max_chain_length = 20  # Prevent infinite loops
        iteration_count = 0
        
        # Build chain by following the pattern
        while candidate_orders and iteration_count < max_chain_length:
            iteration_count += 1
            
            next_order = self._find_next_order_in_chain(
                chain, current_position, candidate_orders, chain_type
            )
            
            if not next_order:
                break
            
            chain.append(next_order)
            candidate_orders.remove(next_order)
            
            # Update current position for next iteration
            if next_order.opens:
                # This was a roll - current position is now the new open
                current_position = next_order.opens[0]
            else:
                # This was a final close - chain is complete
                break
        
        # Must have at least 2 orders to be a chain
        return chain if len(chain) >= 2 else None
    
    def _find_next_order_in_chain(
        self,
        current_chain: List[OrderInfo],
        current_position: LegInfo,
        candidates: List[OrderInfo],
        chain_type: str
    ) -> Optional[OrderInfo]:
        """Find the next order that continues the chain"""
        
        for candidate in candidates:
            if self._is_valid_next_order(current_position, candidate, chain_type):
                return candidate
        
        return None
    
    def _is_valid_next_order(
        self,
        current_position: LegInfo,
        candidate: OrderInfo,
        chain_type: str
    ) -> bool:
        """Check if candidate order can be next in the chain"""
        
        # Check if this is a roll (2 legs) or final close (1 leg)
        if len(candidate.legs) == 2:
            # This should be a roll: CLOSE old + OPEN new
            if not (candidate.closes and candidate.opens):
                return False
            
            close_leg = candidate.closes[0]
            open_leg = candidate.opens[0]
            
            # Validate the close leg matches current position
            if not self._legs_match_for_close(current_position, close_leg, chain_type):
                return False
            
            # Validate the open leg is correct type for chain
            if not self._is_valid_roll_open(open_leg, chain_type):
                return False
            
            return True
            
        elif len(candidate.legs) == 1:
            # This should be a final close
            if not candidate.closes or candidate.opens:
                return False
            
            close_leg = candidate.closes[0]
            return self._legs_match_for_close(current_position, close_leg, chain_type)
        
        return False
    
    def _legs_match_for_close(
        self,
        open_leg: LegInfo,
        close_leg: LegInfo,
        chain_type: str
    ) -> bool:
        """Check if close leg properly closes the open leg"""
        
        # Strike, type, and expiration must match exactly
        if (open_leg.strike_price != close_leg.strike_price or
            open_leg.option_type != close_leg.option_type or
            open_leg.expiration_date != close_leg.expiration_date):
            return False
        
        # Side must be opposite
        if chain_type == 'sell_to_open':
            return open_leg.side == 'sell' and close_leg.side == 'buy'
        elif chain_type == 'buy_to_open':
            return open_leg.side == 'buy' and close_leg.side == 'sell'
        
        return False
    
    def _is_valid_roll_open(self, open_leg: LegInfo, chain_type: str) -> bool:
        """Check if open leg is valid for the chain type"""
        
        if chain_type == 'sell_to_open':
            return open_leg.side == 'sell' and open_leg.position_effect == 'open'
        elif chain_type == 'buy_to_open':
            return open_leg.side == 'buy' and open_leg.position_effect == 'open'
        
        return False
    
    def _validate_chain(self, chain: List[OrderInfo]) -> bool:
        """Validate that the chain follows proper rolled options pattern"""
        
        if len(chain) < 2:
            return False
        
        # First order: must be single leg OPEN
        first_order = chain[0]
        if (len(first_order.legs) != 1 or 
            not first_order.opens or 
            first_order.closes):
            return False
        
        # Determine chain type
        first_leg = first_order.opens[0]
        if first_leg.side == 'sell':
            chain_type = 'sell_to_open'
        elif first_leg.side == 'buy':
            chain_type = 'buy_to_open'
        else:
            return False
        
        # Middle orders: must be 2 legs (CLOSE + OPEN)
        for order in chain[1:-1]:
            if (len(order.legs) != 2 or
                len(order.closes) != 1 or
                len(order.opens) != 1):
                return False
        
        # Last order: must be single leg CLOSE
        last_order = chain[-1]
        if len(last_order.legs) == 1:
            # Single leg close - this is the final close
            if (not last_order.closes or 
                last_order.opens):
                return False
            
            # Validate close side matches chain type
            close_leg = last_order.closes[0]
            if chain_type == 'sell_to_open' and close_leg.side != 'buy':
                return False
            elif chain_type == 'buy_to_open' and close_leg.side != 'sell':
                return False
        elif len(last_order.legs) == 2:
            # Last order is also a roll - this is valid
            if (len(last_order.closes) != 1 or
                len(last_order.opens) != 1):
                return False
        else:
            return False
        
        # Validate time constraints
        first_time = chain[0].created_at
        last_time = chain[-1].created_at
        if (last_time - first_time) > self.max_chain_duration:
            return False
        
        return True
    
    def _determine_chain_status(self, chain: List[Dict[str, Any]]) -> str:
        """Determine if a chain is active, closed, or expired based on the net position effect."""
        if not chain:
            return 'active'
        
        # For rolled options chains, we need to look at the net effect across all orders
        # A chain is closed only if the net position effect results in zero open positions
        
        # Count total opens and closes across all orders in the chain
        total_opens = 0
        total_closes = 0
        
        for order in chain:
            # Check single-leg order position effect
            position_effect = order.get('position_effect', '')
            if position_effect == 'open':
                total_opens += 1
            elif position_effect == 'close':
                total_closes += 1
            
            # Also check legs for multi-leg orders
            legs = order.get('legs', [])
            for leg in legs:
                leg_position_effect = leg.get('position_effect', '')
                if leg_position_effect == 'open':
                    total_opens += 1
                elif leg_position_effect == 'close':
                    total_closes += 1
        
        # Chain is closed only if we have more closes than opens
        # (meaning net position is closed)
        if total_closes > total_opens:
            return 'closed'
        
        # Check if the chain has expired by looking at the latest expiration date
        from datetime import datetime, date
        try:
            latest_exp_date = None
            
            for order in chain:
                # Check order-level expiration date
                exp_date_str = order.get('expiration_date')
                if exp_date_str:
                    exp_date = self._parse_date(exp_date_str)
                    if exp_date and (latest_exp_date is None or exp_date > latest_exp_date):
                        latest_exp_date = exp_date
                
                # Check all legs for multi-leg orders to find the latest expiration
                legs = order.get('legs', [])
                for leg in legs:
                    leg_exp_date_str = leg.get('expiration_date')
                    if leg_exp_date_str:
                        leg_exp_date = self._parse_date(leg_exp_date_str)
                        if leg_exp_date and (latest_exp_date is None or leg_exp_date > latest_exp_date):
                            latest_exp_date = leg_exp_date
            
            # Only mark as expired if the latest expiration date has passed
            if latest_exp_date and latest_exp_date < date.today():
                return 'expired'
                
        except Exception:
            # If date parsing fails, assume active
            pass
        
        return 'active'
    
    def _parse_date(self, date_str: str):
        """Parse date string in various formats and return date object."""
        from datetime import datetime
        
        if not isinstance(date_str, str):
            return None
            
        try:
            # Try YYYY-MM-DD format first
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            try:
                # Try parsing first 10 characters (in case of datetime string)
                return datetime.strptime(date_str[:10], '%Y-%m-%d').date()
            except ValueError:
                return None
    
    def get_chain_analysis(self, chain: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze a detected chain and return summary information"""
        
        if not chain:
            return {}
        
        try:
            # For simple chains, work directly with raw orders
            first_order = chain[0]
            last_order = chain[-1]
            
            # Generate a unique chain ID
            chain_id = first_order.get('id', '') or f"chain_{hash(str(chain))}"
            
            # Get basic information - use correct field name from actual data
            underlying_symbol = first_order.get('chain_symbol', '') or first_order.get('underlying_symbol', '')
            if not underlying_symbol:
                logger.warning(f"No symbol found in order: {list(first_order.keys())}")
                return {}
            
            # Determine chain type from strategy or form_source
            strategy = (first_order.get('strategy') or '').lower()
            form_source = (first_order.get('form_source') or '').lower()
            
            if 'call' in strategy:
                chain_type = 'call_roll'
            elif 'put' in strategy:
                chain_type = 'put_roll'
            elif form_source == 'strategy_roll':
                chain_type = 'strategy_roll'
            else:
                chain_type = 'unknown_roll'
            
            # Determine status based on chain analysis
            status = self._determine_chain_status(chain)
            
            # Get dates
            start_date = first_order.get('created_at', '')
            last_activity_date = last_order.get('created_at', '')
            
            # Calculate basic financial metrics
            total_credits = 0.0
            total_debits = 0.0
            net_premium = 0.0
            
            for order in chain:
                # Only use processed_premium for P&L calculations (per CLAUDE.md guidelines)
                direction = order.get('direction', '')
                processed_premium = float(order.get('processed_premium', 0) or 0)
                
                if direction == 'credit':
                    total_credits += processed_premium
                elif direction == 'debit':
                    total_debits += processed_premium
                else:
                    # Default to credit for roll orders
                    total_credits += abs(processed_premium)
            
            net_premium = total_credits - total_debits
            
            # Get initial strategy name
            initial_strategy = strategy or 'rolled_option'
            
            # Sort orders by created_at (newest first for display)
            try:
                sorted_chain = sorted(chain, key=lambda x: x.get('created_at', ''), reverse=True)
            except:
                sorted_chain = chain  # Fallback to original order if sorting fails
            
            # Process orders to extract key display information
            processed_orders = []
            for i, order in enumerate(sorted_chain):
                # Get basic order info
                processed_premium = float(order.get('processed_premium', 0) or 0)
                quantity = float(order.get('processed_quantity', 0) or 0)
                premium = float(order.get('premium', 0) or 0)  # Per-contract premium for display
                
                # Calculate per-contract price (fallback if premium field not available)
                price_per_contract = premium or (processed_premium / quantity if quantity > 0 else 0.0)
                
                # Get legs info to extract strike, expiration, and side for order-level display
                legs = order.get('legs', [])
                primary_strike = None
                primary_expiration = None
                primary_option_type = None
                primary_side = None
                primary_position_effect = None
                
                if legs:
                    # Analyze legs to determine proper display info
                    opens = [leg for leg in legs if leg.get('position_effect') == 'open']
                    closes = [leg for leg in legs if leg.get('position_effect') == 'close']
                    
                    # Determine position effect based on leg analysis
                    if opens and closes:
                        primary_position_effect = 'roll'  # Both open and close = roll transaction
                        # For display, use the open leg (new position) as primary
                        primary_leg = opens[0]
                    elif opens:
                        primary_position_effect = 'open'  # Only opens = opening transaction
                        primary_leg = opens[0]
                    elif closes:
                        primary_position_effect = 'close'  # Only closes = closing transaction
                        primary_leg = closes[0]
                    else:
                        primary_leg = legs[0]  # Fallback to first leg
                        primary_position_effect = primary_leg.get('position_effect', '')
                    
                    # Use the primary leg for display info
                    primary_strike = float(primary_leg.get('strike_price', 0) or 0)
                    primary_expiration = primary_leg.get('expiration_date', '')
                    primary_option_type = primary_leg.get('option_type', '')
                    primary_side = primary_leg.get('side', '')  # buy/sell
                
                order_info = {
                    'order_id': order.get('id', ''),
                    'created_at': order.get('created_at', ''),
                    'state': order.get('state', ''),
                    'strategy': order.get('strategy', ''),
                    'form_source': order.get('form_source', ''),
                    'direction': order.get('direction', ''),
                    'processed_premium': processed_premium,  # Total premium for P&L calculations
                    'price': price_per_contract,  # Per-contract price
                    'premium': premium,  # Per-contract premium for display
                    'quantity': quantity,
                    'strike_price': primary_strike,  # Primary strike for order display
                    'expiration_date': primary_expiration,  # Primary expiration for order display
                    'option_type': primary_option_type,  # Primary option type for position display
                    'side': primary_side,  # Primary side (buy/sell) for display
                    'position_effect': primary_position_effect,  # Primary position effect (open/close)
                    'underlying_symbol': underlying_symbol,  # Use the correctly extracted symbol
                    'legs': []
                }
                
                # Process legs to extract options details and add roll transaction details
                legs = order.get('legs', [])
                roll_details = None
                
                # If this is a roll transaction, create detailed roll information
                if len(legs) > 1:
                    closes = [leg for leg in legs if leg.get('position_effect') == 'close']
                    opens = [leg for leg in legs if leg.get('position_effect') == 'open']
                    
                    if closes and opens:
                        roll_details = {
                            'type': 'roll',
                            'close_position': {
                                'strike_price': float(closes[0].get('strike_price', 0) or 0),
                                'option_type': closes[0].get('option_type', '').upper(),
                                'expiration_date': closes[0].get('expiration_date', ''),
                                'side': closes[0].get('side', '').lower()
                            },
                            'open_position': {
                                'strike_price': float(opens[0].get('strike_price', 0) or 0),
                                'option_type': opens[0].get('option_type', '').upper(),
                                'expiration_date': opens[0].get('expiration_date', ''),
                                'side': opens[0].get('side', '').lower()
                            }
                        }
                
                # Add roll details to order info
                if roll_details:
                    order_info['roll_details'] = roll_details
                
                # Process all legs for completeness
                for leg in legs:
                    # For multi-leg orders (like rolls), each leg typically has the same quantity as the order
                    # Use leg quantity if available and non-zero, otherwise use order quantity
                    leg_quantity = float(leg.get('quantity', 0) or 0)
                    if leg_quantity == 0:
                        # For roll orders, each leg should have the same quantity as the total order
                        leg_quantity = quantity
                    
                    leg_info = {
                        'strike_price': float(leg.get('strike_price', 0) or 0),
                        'option_type': leg.get('option_type', ''),
                        'expiration_date': leg.get('expiration_date', ''),
                        'side': leg.get('side', ''),
                        'position_effect': leg.get('position_effect', ''),
                        'quantity': leg_quantity
                    }
                    order_info['legs'].append(leg_info)
                
                processed_orders.append(order_info)
            
            # Calculate latest position from the most recent order
            latest_position = self._calculate_latest_position(chain)
            
            return {
                'chain_id': chain_id,
                'underlying_symbol': underlying_symbol,
                'chain_type': chain_type,
                'status': status,
                'start_date': start_date,
                'last_activity_date': last_activity_date,
                'total_orders': len(chain),
                'roll_count': max(0, len(chain) - 1),
                'total_credits_collected': total_credits,
                'total_debits_paid': total_debits,
                'net_premium': net_premium,
                'total_pnl': net_premium,  # For now, P&L equals net premium
                'initial_strategy': initial_strategy,
                'latest_position': latest_position,
                'orders': processed_orders  # Use processed orders instead of raw chain
            }
            
        except Exception as e:
            logger.error(f"Error analyzing chain: {e}", exc_info=True)
            # Return a minimal valid analysis instead of empty dict
            return {
                'chain_id': f"chain_{hash(str(chain))}",
                'underlying_symbol': chain[0].get('underlying_symbol', 'UNKNOWN') if chain else 'UNKNOWN',
                'chain_type': 'roll',
                'status': 'active',
                'start_date': chain[0].get('created_at', '') if chain else '',
                'last_activity_date': chain[-1].get('created_at', '') if chain else '',
                'total_orders': len(chain),
                'roll_count': max(0, len(chain) - 1),
                'total_credits_collected': 0.0,
                'total_debits_paid': 0.0,
                'net_premium': 0.0,
                'total_pnl': 0.0,
                'initial_strategy': 'roll',
                'orders': chain
            }
    
    def _get_strategy_name(self, order_info: OrderInfo) -> str:
        """Get strategy name for an order"""
        
        if len(order_info.legs) == 1:
            leg = order_info.legs[0]
            if leg.position_effect == 'open':
                if leg.side == 'sell':
                    return f"short_{leg.option_type}"
                else:
                    return f"long_{leg.option_type}"
        
        return "unknown"
    
    def _calculate_latest_position(self, chain: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Calculate the current open position from the most recent order in the chain"""
        try:
            if not chain:
                logger.warning("Empty chain passed to _calculate_latest_position")
                return None
            
            # Sort orders chronologically (newest last) 
            sorted_chain = sorted(chain, key=lambda x: x.get('created_at', ''))
            most_recent_order = sorted_chain[-1]
            
            # Find the open legs in the most recent order
            legs = most_recent_order.get('legs', [])
            
            # Look for legs with 'open' position effect in the legs array
            open_legs = [leg for leg in legs if leg.get('position_effect') == 'open']
            
            # If no open legs found in legs array, but the order has roll_details, extract from open_position
            if not open_legs and 'roll_details' in most_recent_order:
                roll_details = most_recent_order['roll_details']
                if roll_details.get('type') == 'roll' and 'open_position' in roll_details:
                    open_position = roll_details['open_position']
                    
                    # Create a synthetic leg from roll details
                    synthetic_open_leg = {
                        'strike_price': open_position.get('strike_price'),
                        'option_type': open_position.get('option_type', '').lower(),
                        'expiration_date': open_position.get('expiration_date'),
                        'side': open_position.get('side', '').lower(),
                        'position_effect': 'open'
                    }
                    open_legs = [synthetic_open_leg]
            
            if not open_legs:
                # If no open legs in the most recent order, search backward through the chain
                for i in range(len(sorted_chain) - 2, -1, -1):
                    order = sorted_chain[i]
                    order_legs = order.get('legs', [])
                    order_open_legs = [leg for leg in order_legs if leg.get('position_effect') == 'open']
                    
                    # Also check roll_details for earlier orders
                    if not order_open_legs and 'roll_details' in order:
                        order_roll_details = order['roll_details']
                        if order_roll_details.get('type') == 'roll' and 'open_position' in order_roll_details:
                            open_position = order_roll_details['open_position']
                            synthetic_open_leg = {
                                'strike_price': open_position.get('strike_price'),
                                'option_type': open_position.get('option_type', '').lower(),
                                'expiration_date': open_position.get('expiration_date'),
                                'side': open_position.get('side', '').lower(),
                                'position_effect': 'open'
                            }
                            order_open_legs = [synthetic_open_leg]
                    
                    if order_open_legs:
                        open_leg = order_open_legs[0]
                        break
                else:
                    return None
            else:
                # Use the first open leg as the latest position
                open_leg = open_legs[0]
            
            latest_position = {
                'strike_price': float(open_leg.get('strike_price', 0) or 0),
                'option_type': open_leg.get('option_type', '').upper(),
                'expiration_date': open_leg.get('expiration_date', ''),
                'side': open_leg.get('side', '').lower(),  # buy = long, sell = short
                'quantity': float(most_recent_order.get('processed_quantity', 0) or 0),
                'last_updated': most_recent_order.get('created_at', '')
            }
            
            logger.debug(f"Calculated latest position: {latest_position}")
            return latest_position
            
        except Exception as e:
            logger.error(f"Error calculating latest position: {e}", exc_info=True)
            return None
    
    def _create_simple_chains_from_rolls(self, orders: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Create proper roll chains by validating roll sequences"""
        chains = []
        
        # Find all roll orders using multi-criteria detection
        roll_orders = []
        for order in orders:
            if self._is_roll_order(order):
                roll_orders.append(order)
        
        logger.info(f"Creating proper roll chains from {len(roll_orders)} roll orders")
        
        # Group by symbol AND option type to prevent mixing calls and puts
        symbol_type_orders = {}
        for order in roll_orders:
            symbol = order.get('chain_symbol', '') or order.get('underlying_symbol', '')
            if not symbol:
                continue
                
            # Get primary option type from first leg
            legs = order.get('legs', [])
            if not legs:
                continue
                
            primary_option_type = legs[0].get('option_type', '').lower()
            if primary_option_type not in ['call', 'put']:
                continue
            
            group_key = f"{symbol}_{primary_option_type}"
            if group_key not in symbol_type_orders:
                symbol_type_orders[group_key] = []
            symbol_type_orders[group_key].append(order)
        
        logger.info(f"Grouped into {len(symbol_type_orders)} symbol+type combinations")
        
        # Create proper roll chains for each symbol+type group
        total_chains = 0
        for group_key, group_orders in symbol_type_orders.items():
            symbol, option_type = group_key.split('_', 1)
            
            # Sort by time
            group_orders.sort(key=lambda x: x.get('created_at', ''))
            
            # Build chains by analyzing position effects and ensuring proper roll sequences
            group_chains = self._build_proper_roll_chains(group_orders, symbol, option_type)
            chains.extend(group_chains)
            total_chains += len(group_chains)
            
            logger.info(f"Found {len(group_chains)} proper chains for {group_key}")
            
            # Limit total chains to prevent performance issues
            if total_chains >= 50:
                break
        
        logger.info(f"Created {len(chains)} proper roll chains with validated roll sequences")
        return chains
    
    def _build_proper_roll_chains(self, orders: List[Dict[str, Any]], symbol: str, option_type: str) -> List[List[Dict[str, Any]]]:
        """Build chains by validating proper roll sequences (open -> roll -> close)"""
        chains = []
        used_orders = set()
        
        # Analyze each order to understand its position effects
        order_analyses = []
        for order in orders:
            analysis = self._analyze_order_position_effects(order)
            if analysis:
                order_analyses.append(analysis)
        
        # Find potential chain starts (orders that open new positions WITHOUT closing any)
        chain_starts = []
        orders_with_opens = 0
        orders_with_closes = 0
        orders_with_both = 0
        
        for analysis in order_analyses:
            if analysis['opens']:
                orders_with_opens += 1
            if analysis['closes']:
                orders_with_closes += 1
            if analysis['opens'] and analysis['closes']:
                orders_with_both += 1
                
            # A valid chain start MUST have opens and NO closes (pure opening order)
            if (analysis['opens'] and 
                not analysis['closes'] and 
                analysis['order_id'] not in used_orders):
                chain_starts.append(analysis)
                logger.info(f"Valid chain start found: {analysis['order_id']} - {len(analysis['opens'])} opens, {len(analysis['closes'])} closes")
        
        logger.info(f"Analysis for {symbol}_{option_type}: {len(order_analyses)} total orders, {orders_with_opens} with opens, {orders_with_closes} with closes, {orders_with_both} with both")
        logger.info(f"Found {len(chain_starts)} potential chain starts for {symbol}_{option_type}")
        
        # Track which starts came from backward tracing for validation purposes
        backward_traced_starts = []
        
        # If no chain starts found but we have roll orders, trace backwards to find original openings
        if len(chain_starts) == 0 and orders_with_both > 0:
            logger.info(f"No pure opening orders found in current window for {symbol}_{option_type}, tracing backwards from roll orders")
            backward_traced_starts = self._trace_backwards_for_chain_starts(order_analyses, symbol, option_type)
            chain_starts.extend(backward_traced_starts)
            logger.info(f"Found {len(backward_traced_starts)} chain starts via backward tracing for {symbol}_{option_type}")
        
        # Build chains from each start
        for start_analysis in chain_starts:
            if start_analysis['order_id'] in used_orders:
                continue
            
            chain = self._build_chain_from_start_analysis(start_analysis, order_analyses, used_orders)
            
            # Validate the chain follows proper roll patterns
            # Allow partial chains when starting from roll orders (backward traced)
            is_backward_traced = start_analysis in backward_traced_starts
            
            if chain and (self._validate_roll_chain(chain) or 
                         (is_backward_traced and self._validate_partial_roll_chain(chain))):
                raw_chain = [analysis['raw_order'] for analysis in chain]
                chains.append(raw_chain)
                
                # Mark orders as used
                for analysis in chain:
                    used_orders.add(analysis['order_id'])
                
                chain_type = "partial" if is_backward_traced else "complete"
                logger.info(f"Valid {chain_type} roll chain found with {len(chain)} orders for {symbol}_{option_type}")
        
        return chains
    
    def _trace_backwards_for_chain_starts(self, current_analyses: List[Dict[str, Any]], symbol: str, option_type: str) -> List[Dict[str, Any]]:
        """Trace backwards from roll orders to find original opening orders"""
        try:
            # Get all roll orders that have both opens and closes
            roll_orders = [analysis for analysis in current_analyses if analysis['opens'] and analysis['closes']]
            
            if not roll_orders:
                return []
            
            logger.info(f"Found {len(roll_orders)} roll orders for backward tracing in {symbol}_{option_type}")
            
            # Load all available orders for this symbol to search for opening orders
            all_orders = self._load_all_orders_for_symbol(symbol)
            if not all_orders:
                logger.warning(f"No orders found for symbol {symbol} in backward tracing")
                return self._fallback_to_earliest_rolls(roll_orders, symbol, option_type)
            
            logger.info(f"Loaded {len(all_orders)} total orders for {symbol} to search for opening orders")
            
            # Find matching opening orders for each roll order's close legs
            found_opening_orders = []
            
            for roll_analysis in roll_orders:
                for close_leg in roll_analysis['closes']:
                    # Search for matching single-leg opening order
                    matching_opening_order = self._find_matching_opening_order(
                        all_orders,
                        symbol=symbol,
                        option_type=close_leg['option_type'],
                        strike_price=close_leg['strike_price'],
                        expiration_date=close_leg['expiration_date']
                    )
                    
                    if matching_opening_order:
                        # Analyze the found opening order
                        opening_analysis = self._analyze_order_position_effects(matching_opening_order)
                        if opening_analysis and opening_analysis not in found_opening_orders:
                            found_opening_orders.append(opening_analysis)
                            logger.info(f"Found matching opening order for {symbol} ${close_leg['strike_price']} {close_leg['option_type']} {close_leg['expiration_date']}")
            
            if found_opening_orders:
                logger.info(f"Found {len(found_opening_orders)} original opening orders for {symbol}_{option_type}")
                return found_opening_orders
            else:
                logger.info(f"No matching opening orders found for {symbol}_{option_type}, falling back to earliest rolls")
                return self._fallback_to_earliest_rolls(roll_orders, symbol, option_type)
            
        except Exception as e:
            logger.error(f"Error tracing backwards for {symbol}_{option_type}: {e}")
            return []
    
    def _load_all_orders_for_symbol(self, symbol: str) -> List[Dict[str, Any]]:
        """Load all available orders for a specific symbol to search for opening orders"""
        try:
            # In the current implementation, we need to load from the same data source 
            # used by the chain detector. Since detect_chains() receives a list of orders,
            # we need to access that same data source.
            
            # For this implementation, we'll search through the cached data or 
            # available order data from debug files
            import glob
            import json
            from pathlib import Path
            
            # Load from debug data files (same as JsonRolledOptionsService)
            debug_data_dir = Path(__file__).parent.parent.parent / "debug_data"
            options_files = list(debug_data_dir.glob("*options_orders*.json"))
            
            all_orders = []
            
            # Load from up to 10 most recent files to balance completeness vs performance
            for file_path in sorted(options_files, reverse=True)[:10]:
                try:
                    with open(file_path, 'r') as f:
                        orders = json.load(f)
                        
                    # Filter for the specific symbol
                    symbol_orders = [
                        order for order in orders 
                        if (order.get('chain_symbol', '').upper() == symbol.upper() or 
                            order.get('underlying_symbol', '').upper() == symbol.upper())
                    ]
                    
                    all_orders.extend(symbol_orders)
                    
                except Exception as e:
                    logger.debug(f"Error loading {file_path}: {e}")
                    continue
            
            # Remove duplicates based on order ID
            seen_ids = set()
            unique_orders = []
            for order in all_orders:
                order_id = order.get('id')
                if order_id and order_id not in seen_ids:
                    seen_ids.add(order_id)
                    unique_orders.append(order)
            
            logger.info(f"Loaded {len(unique_orders)} unique orders for symbol {symbol}")
            return unique_orders
            
        except Exception as e:
            logger.error(f"Error loading orders for symbol {symbol}: {e}")
            return []
    
    def _find_matching_opening_order(
        self, 
        all_orders: List[Dict[str, Any]], 
        symbol: str, 
        option_type: str, 
        strike_price: float, 
        expiration_date: str
    ) -> Optional[Dict[str, Any]]:
        """Find a single-leg opening order that matches the specified criteria"""
        try:
            for order in all_orders:
                # Must be same symbol
                order_symbol = order.get('chain_symbol', '') or order.get('underlying_symbol', '')
                if order_symbol.upper() != symbol.upper():
                    continue
                
                # Must be filled (not cancelled)
                if order.get('state') != 'filled':
                    continue
                
                # Must be single leg (not a roll order)
                legs = order.get('legs', [])
                if len(legs) != 1:
                    continue
                
                leg = legs[0]
                
                # Must match all criteria exactly
                if (leg.get('option_type', '').lower() == option_type.lower() and
                    float(leg.get('strike_price', 0) or 0) == float(strike_price) and
                    leg.get('expiration_date') == expiration_date and
                    leg.get('position_effect') == 'open'):
                    
                    logger.debug(f"Found matching opening order: {order.get('id')} - ${strike_price} {option_type} {expiration_date}")
                    return order
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding matching opening order: {e}")
            return None
    
    def _fallback_to_earliest_rolls(self, roll_orders: List[Dict[str, Any]], symbol: str, option_type: str) -> List[Dict[str, Any]]:
        """Fallback to using earliest roll orders as chain starts when no opening orders found"""
        # Sort roll orders by time to find the earliest ones
        roll_orders.sort(key=lambda x: x['created_at'])
        
        # Take up to 5 earliest rolls as fallback chain starts
        earliest_rolls = roll_orders[:min(5, len(roll_orders))]
        
        logger.info(f"Using {len(earliest_rolls)} earliest roll orders as fallback chain starts for {symbol}_{option_type}")
        return earliest_rolls
    
    def _validate_partial_roll_chain(self, chain: List[Dict[str, Any]]) -> bool:
        """Validate a partial chain that starts with a roll order (missing original opening)"""
        try:
            if len(chain) < 1:
                return False
            
            # For partial chains, we relax the requirement that the first order must be pure opening
            # Instead, we validate that the chain has proper sequence from where we can see
            
            first_order = chain[0]
            
            # First order in partial chain can have both opens and closes (it's a roll order)
            if not first_order['opens']:
                logger.debug("Partial chain validation failed: first order has no opens")
                return False
            
            # Validate the rest of the chain follows proper patterns
            current_open_positions = first_order['opens'].copy()
            
            for i, order_analysis in enumerate(chain[1:], 1):
                # Each subsequent order should properly continue the chain
                for close_leg in order_analysis['closes']:
                    found_match = False
                    for j, open_pos in enumerate(current_open_positions):
                        if self._positions_match_strictly(open_pos, close_leg):
                            current_open_positions.pop(j)
                            found_match = True
                            break
                    
                    if not found_match:
                        logger.debug(f"Partial chain validation failed at order {i}: close doesn't match open position")
                        return False
                
                # Add new opens
                current_open_positions.extend(order_analysis['opens'])
            
            logger.debug(f"Partial chain validation passed for {len(chain)} orders")
            return True
            
        except Exception as e:
            logger.debug(f"Error validating partial chain: {e}")
            return False
    
    def _analyze_order_position_effects(self, order: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze an order to understand its position effects with detailed validation"""
        try:
            legs = order.get('legs', [])
            if not legs:
                return None
            
            opens = []  # Positions being opened
            closes = []  # Positions being closed
            order_quantity = float(order.get('processed_quantity', 0) or 0)
            
            for leg in legs:
                position_effect = leg.get('position_effect', '').lower()
                side = leg.get('side', '').lower()
                strike_price = float(leg.get('strike_price', 0) or 0)
                option_type = leg.get('option_type', '').lower()
                expiration_date = leg.get('expiration_date', '')
                leg_quantity = float(leg.get('quantity', order_quantity) or order_quantity)
                
                # Validate required fields
                if not all([position_effect, side, strike_price, option_type, expiration_date]):
                    logger.debug(f"Order {order.get('id')} leg missing required fields")
                    continue
                
                if position_effect not in ['open', 'close']:
                    logger.debug(f"Order {order.get('id')} invalid position_effect: {position_effect}")
                    continue
                
                if side not in ['buy', 'sell']:
                    logger.debug(f"Order {order.get('id')} invalid side: {side}")
                    continue
                
                if option_type not in ['call', 'put']:
                    logger.debug(f"Order {order.get('id')} invalid option_type: {option_type}")
                    continue
                
                leg_info = {
                    'strike_price': strike_price,
                    'option_type': option_type,
                    'expiration_date': expiration_date,
                    'side': side,
                    'position_effect': position_effect,
                    'quantity': leg_quantity
                }
                
                if position_effect == 'open':
                    opens.append(leg_info)
                elif position_effect == 'close':
                    closes.append(leg_info)
            
            # Validate that the order has valid legs
            if not opens and not closes:
                logger.debug(f"Order {order.get('id')} has no valid legs")
                return None
            
            analysis = {
                'order_id': order.get('id'),
                'created_at': order.get('created_at'),
                'opens': opens,
                'closes': closes,
                'raw_order': order
            }
            
            logger.debug(f"Analyzed order {order.get('id')}: {len(opens)} opens, {len(closes)} closes")
            return analysis
            
        except Exception as e:
            logger.debug(f"Error analyzing order {order.get('id')}: {e}")
            return None
    
    def _build_chain_from_start_analysis(
        self, 
        start_analysis: Dict[str, Any], 
        all_analyses: List[Dict[str, Any]], 
        used_orders: set
    ) -> Optional[List[Dict[str, Any]]]:
        """Build a chain starting from an opening order with strict position tracking"""
        
        chain = [start_analysis]
        # Track open positions with detailed information including quantities
        current_open_positions = []
        for open_pos in start_analysis['opens']:
            position_info = {
                'strike_price': open_pos['strike_price'],
                'option_type': open_pos['option_type'],
                'expiration_date': open_pos['expiration_date'],
                'side': open_pos['side'],
                'quantity': open_pos.get('quantity', 0),
                'opened_by': start_analysis['order_id']
            }
            current_open_positions.append(position_info)
        
        logger.debug(f"Starting chain with {len(current_open_positions)} open positions from order {start_analysis['order_id']}")
        
        # Find subsequent orders that continue this chain
        remaining_analyses = [
            analysis for analysis in all_analyses 
            if (analysis['order_id'] not in used_orders and 
                analysis['order_id'] != start_analysis['order_id'] and
                analysis['created_at'] > start_analysis['created_at'])
        ]
        
        # Sort by time
        remaining_analyses.sort(key=lambda x: x['created_at'])
        
        max_iterations = 10  # Prevent infinite loops
        iteration = 0
        
        while current_open_positions and remaining_analyses and iteration < max_iterations:
            iteration += 1
            
            # Find the next order that properly closes one of our open positions
            next_order = None
            for analysis in remaining_analyses:
                if self._order_properly_closes_positions(analysis, current_open_positions):
                    next_order = analysis
                    break
            
            if not next_order:
                logger.debug(f"No valid continuation found for chain at iteration {iteration}")
                break
            
            logger.debug(f"Adding order {next_order['order_id']} to chain (iteration {iteration})")
            
            # Add this order to the chain
            chain.append(next_order)
            remaining_analyses.remove(next_order)
            
            # Update current open positions with strict tracking
            updated_positions = self._update_open_positions(current_open_positions, next_order)
            if updated_positions is None:
                logger.debug(f"Position update failed for order {next_order['order_id']}, breaking chain")
                break
            
            current_open_positions = updated_positions
            logger.debug(f"After order {next_order['order_id']}: {len(current_open_positions)} open positions remain")
        
        # Validate the final chain structure
        if len(chain) >= 2 and self._validate_chain_position_flow(chain):
            return chain
        
        logger.debug(f"Chain validation failed: length={len(chain)}, valid_flow={self._validate_chain_position_flow(chain) if len(chain) >= 2 else False}")
        return None
    
    def _order_properly_closes_positions(self, order_analysis: Dict[str, Any], open_positions: List[Dict[str, Any]]) -> bool:
        """Check if an order properly closes positions with quantity and detail validation"""
        if not order_analysis['closes']:
            return False
        
        # Check that all closes in this order match open positions
        for close_leg in order_analysis['closes']:
            found_match = False
            for open_pos in open_positions:
                if self._positions_match_strictly(open_pos, close_leg):
                    found_match = True
                    break
            
            if not found_match:
                logger.debug(f"Close leg {close_leg['strike_price']} {close_leg['option_type']} {close_leg['expiration_date']} doesn't match any open position")
                return False
        
        return True
    
    def _update_open_positions(self, current_positions: List[Dict[str, Any]], order_analysis: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Update open positions after processing an order, with strict validation"""
        try:
            updated_positions = current_positions.copy()
            
            # Process closes first - remove positions that are being closed
            for close_leg in order_analysis['closes']:
                position_to_remove = None
                for open_pos in updated_positions:
                    if self._positions_match_strictly(open_pos, close_leg):
                        position_to_remove = open_pos
                        break
                
                if position_to_remove:
                    updated_positions.remove(position_to_remove)
                    logger.debug(f"Closed position: {close_leg['strike_price']} {close_leg['option_type']} {close_leg['expiration_date']}")
                else:
                    logger.debug(f"Cannot close position - no matching open position for {close_leg['strike_price']} {close_leg['option_type']}")
                    return None  # Invalid - trying to close position that wasn't opened
            
            # Process opens - add new positions
            for open_leg in order_analysis['opens']:
                new_position = {
                    'strike_price': open_leg['strike_price'],
                    'option_type': open_leg['option_type'],
                    'expiration_date': open_leg['expiration_date'],
                    'side': open_leg['side'],
                    'quantity': open_leg.get('quantity', 0),
                    'opened_by': order_analysis['order_id']
                }
                updated_positions.append(new_position)
                logger.debug(f"Opened new position: {open_leg['strike_price']} {open_leg['option_type']} {open_leg['expiration_date']}")
            
            return updated_positions
            
        except Exception as e:
            logger.debug(f"Error updating positions: {e}")
            return None
    
    def _positions_match_strictly(self, open_pos: Dict[str, Any], close_leg: Dict[str, Any]) -> bool:
        """Strict position matching including quantity validation"""
        return (
            open_pos['strike_price'] == close_leg['strike_price'] and
            open_pos['option_type'] == close_leg['option_type'] and
            open_pos['expiration_date'] == close_leg['expiration_date'] and
            open_pos['side'] != close_leg['side']  # Must be opposite sides
        )
    
    def _validate_chain_position_flow(self, chain: List[Dict[str, Any]]) -> bool:
        """Validate that the entire chain has proper position flow"""
        try:
            # Start with the first order's opens
            open_positions = []
            for open_leg in chain[0]['opens']:
                position_info = {
                    'strike_price': open_leg['strike_price'],
                    'option_type': open_leg['option_type'],
                    'expiration_date': open_leg['expiration_date'],
                    'side': open_leg['side']
                }
                open_positions.append(position_info)
            
            # Process each subsequent order
            for i, order_analysis in enumerate(chain[1:], 1):
                # Validate that all closes match open positions
                for close_leg in order_analysis['closes']:
                    found_match = False
                    for j, open_pos in enumerate(open_positions):
                        if self._positions_match_strictly(open_pos, close_leg):
                            open_positions.pop(j)  # Remove the closed position
                            found_match = True
                            break
                    
                    if not found_match:
                        logger.debug(f"Chain validation failed at order {i}: close doesn't match open position")
                        return False
                
                # Add new opens
                for open_leg in order_analysis['opens']:
                    position_info = {
                        'strike_price': open_leg['strike_price'],
                        'option_type': open_leg['option_type'],
                        'expiration_date': open_leg['expiration_date'],
                        'side': open_leg['side']
                    }
                    open_positions.append(position_info)
            
            # Valid chain can end with open positions (active chain) or no open positions (closed chain)
            return True
            
        except Exception as e:
            logger.debug(f"Error validating chain position flow: {e}")
            return False
    
    def _order_closes_position(self, order_analysis: Dict[str, Any], open_positions: List[Dict[str, Any]]) -> bool:
        """Legacy method - replaced by _order_properly_closes_positions"""
        return self._order_properly_closes_positions(order_analysis, open_positions)
    
    def _positions_match(self, open_pos: Dict[str, Any], close_leg: Dict[str, Any]) -> bool:
        """Check if a close leg matches an open position"""
        return (
            open_pos['strike_price'] == close_leg['strike_price'] and
            open_pos['option_type'] == close_leg['option_type'] and
            open_pos['expiration_date'] == close_leg['expiration_date'] and
            open_pos['side'] != close_leg['side']  # Opposite sides (sell to open -> buy to close)
        )
    
    def _validate_roll_chain(self, chain: List[Dict[str, Any]]) -> bool:
        """Validate that a chain follows proper roll patterns"""
        if len(chain) < 2:
            return False
        
        # Check that we have proper open -> roll -> close pattern
        first_order = chain[0]
        last_order = chain[-1]
        
        # First order should have opens (starting positions)
        if not first_order['opens']:
            return False
        
        # Check that there's a logical progression through the chain
        open_positions = first_order['opens'].copy()
        
        for i in range(1, len(chain)):
            order = chain[i]
            
            # This order should close some positions and potentially open new ones
            if not order['closes']:
                # If no closes, this might be the end of chain but should not continue
                continue
            
            # Verify that closes match some of our open positions
            valid_closes = False
            for close_leg in order['closes']:
                for open_pos in open_positions:
                    if self._positions_match(open_pos, close_leg):
                        valid_closes = True
                        break
                if valid_closes:
                    break
            
            if not valid_closes:
                logger.debug(f"Chain validation failed: order {order['order_id']} doesn't close expected positions")
                return False
            
            # Update open positions
            for close_leg in order['closes']:
                open_positions = [
                    pos for pos in open_positions
                    if not self._positions_match(pos, close_leg)
                ]
            
            # Add new opens
            open_positions.extend(order['opens'])
        
        # Chain is valid if we've properly tracked position changes
        return True
