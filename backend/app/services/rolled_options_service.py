"""
Rolled Options Chain Analysis Service

This service identifies and tracks rolled options positions by analyzing the order history
to find sequences of close/open transactions that indicate a roll strategy.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import asyncio

from app.services.robinhood_service import RobinhoodService

logger = logging.getLogger(__name__)

@dataclass
class RollTransaction:
    """Represents a single roll transaction (close + open)"""
    roll_id: str
    underlying_symbol: str
    roll_date: datetime
    
    # Close leg (ending the old position)
    close_order_id: str
    close_strike: float
    close_expiry: str
    close_option_type: str
    close_quantity: float
    close_price: float
    close_premium: float
    
    # Open leg (starting the new position)
    open_order_id: str
    open_strike: float
    open_expiry: str
    open_option_type: str
    open_quantity: float
    open_price: float
    open_premium: float
    
    # Roll analysis
    net_credit: float  # positive if collected money, negative if paid
    strike_direction: str  # "up", "down", "same"
    expiry_extension: int  # days extended
    roll_type: str  # "defensive", "aggressive", "time"
    
@dataclass
class OptionsChain:
    """Represents a complete rolled options chain"""
    chain_id: str
    underlying_symbol: str
    initial_strategy: str  # "SELL PUT", "SELL CALL", etc.
    
    # Chain metadata
    start_date: datetime
    last_roll_date: Optional[datetime]
    status: str  # "active", "closed", "expired"
    total_rolls: int
    
    # Current position (if still active)
    current_strike: Optional[float]
    current_expiry: Optional[str]
    current_option_type: str
    current_quantity: float
    
    # Financial summary
    total_credits_collected: float
    total_debits_paid: float
    net_premium: float
    unrealized_pnl: float
    realized_pnl: float
    total_pnl: float
    
    # Roll history
    rolls: List[RollTransaction]
    
    # Current market data
    current_price: float
    mark_price: float
    days_to_expiry: int

class RolledOptionsService:
    """Service for identifying and analyzing rolled options chains"""
    
    def __init__(self, robinhood_service: RobinhoodService):
        self.rh_service = robinhood_service
        
    async def get_rolled_options_chains(self, days_back: int = 365) -> Dict[str, Any]:
        """
        Identify and analyze all rolled options chains
        
        Algorithm:
        1. Get all options orders for the specified period
        2. Group orders by underlying symbol
        3. For each symbol, identify close/open pairs that indicate rolls
        4. Build chains by linking consecutive rolls
        5. Calculate P&L and performance metrics for each chain
        """
        try:
            # Get all options orders
            since_time = datetime.now() - timedelta(days=days_back)
            orders_result = await self.rh_service.get_options_orders(limit=1000, since_time=since_time)
            
            if not orders_result.get("success", False):
                return {"success": False, "message": "Failed to fetch options orders"}
                
            orders = orders_result["data"]
            logger.info(f"Analyzing {len(orders)} orders for rolled options chains")
            
            # Filter to only closed orders (filled/executed)
            executed_orders = [order for order in orders if order.get("state", "").lower() == "filled"]
            logger.info(f"Found {len(executed_orders)} executed orders")
            
            # Group orders by underlying symbol
            orders_by_symbol = self._group_orders_by_symbol(executed_orders)
            
            # Identify rolled chains for each symbol
            all_chains = []
            for symbol, symbol_orders in orders_by_symbol.items():
                chains = await self._identify_chains_for_symbol(symbol, symbol_orders)
                all_chains.extend(chains)
            
            logger.info(f"Identified {len(all_chains)} rolled options chains")
            
            # Calculate summary statistics
            summary = self._calculate_chain_summary(all_chains)
            
            return {
                "success": True,
                "data": {
                    "chains": [self._chain_to_dict(chain) for chain in all_chains],
                    "summary": summary,
                    "analysis_period_days": days_back,
                    "total_orders_analyzed": len(orders),
                    "executed_orders": len(executed_orders)
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing rolled options chains: {str(e)}")
            return {"success": False, "message": str(e)}
    
    def _group_orders_by_symbol(self, orders: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group orders by underlying symbol"""
        groups = defaultdict(list)
        for order in orders:
            symbol = order.get("underlying_symbol", "UNKNOWN")
            if symbol != "UNKNOWN":
                groups[symbol].append(order)
        
        # Sort each group by creation time
        for symbol in groups:
            groups[symbol].sort(key=lambda x: x.get("created_at", ""))
            
        return dict(groups)
    
    async def _identify_chains_for_symbol(self, symbol: str, orders: List[Dict[str, Any]]) -> List[OptionsChain]:
        """
        Identify rolled options chains for a specific symbol
        
        Roll identification logic:
        1. Look for "BUY TO CLOSE" followed by "SELL TO OPEN" (for short positions)
        2. Look for "SELL TO CLOSE" followed by "BUY TO OPEN" (for long positions)
        3. Must occur within reasonable time window (same day or next trading day)
        4. Usually same or similar contract quantity
        """
        chains = []
        
        # Group orders by strategy type (puts/calls, buy/sell)
        strategy_groups = self._group_orders_by_strategy_type(orders)
        
        for strategy_type, strategy_orders in strategy_groups.items():
            if len(strategy_orders) < 2:
                continue
                
            # Look for roll patterns in this strategy group
            chain_orders = self._find_roll_patterns(strategy_orders)
            
            if chain_orders:
                # Determine initial strategy from first order
                initial_order = chain_orders[0]
                initial_strategy = self._determine_initial_strategy(initial_order)
                
                chain = await self._build_chain_from_orders(symbol, initial_strategy, chain_orders)
                if chain:
                    chains.append(chain)
        
        return chains
    
    def _group_orders_by_strategy_type(self, orders: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group orders by option type to identify potential roll sequences"""
        groups = defaultdict(list)
        
        for order in orders:
            option_type = order.get("option_type", "").lower()
            
            # Group by option type only (PUT or CALL) to allow roll detection
            # across different transaction sides (buy/sell)
            if option_type == "put":
                key = "PUT"
            elif option_type == "call":
                key = "CALL"
            else:
                key = option_type.upper()
            
            groups[key].append(order)
        
        # Sort each group by creation time for proper sequence detection
        for group_orders in groups.values():
            group_orders.sort(key=lambda x: x.get("created_at", ""))
        
        return dict(groups)
    
    def _determine_initial_strategy(self, initial_order: Dict[str, Any]) -> str:
        """Determine initial strategy type from the first order"""
        strategy = initial_order.get("strategy", "").upper()
        option_type = initial_order.get("option_type", "").lower()
        
        if "SELL" in strategy and option_type == "put":
            return "SELL_PUT"
        elif "SELL" in strategy and option_type == "call":
            return "SELL_CALL"
        elif "BUY" in strategy and option_type == "put":
            return "BUY_PUT"
        elif "BUY" in strategy and option_type == "call":
            return "BUY_CALL"
        else:
            return f"{strategy}_{option_type.upper()}"
    
    def _find_roll_patterns(self, orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Find roll patterns in a sequence of orders
        
        Roll pattern criteria:
        1. Start with an opening position (SELL PUT, SELL CALL, BUY PUT, BUY CALL)
        2. Followed by close/open pairs (rolls)
        3. Within reasonable time window (typically same day to 7 days)
        4. Same or similar quantity
        """
        if len(orders) < 3:  # Need at least 3 orders: initial open + close + new open
            return []
        
        # Find potential chain starting points (initial opening positions)
        chain_orders = []
        
        for i in range(len(orders)):
            order = orders[i]
            strategy = order.get("strategy", "").upper()
            
            # Check if this is an initial opening position
            is_initial_open = any(pattern in strategy for pattern in [
                "SELL PUT", "SELL CALL", "BUY PUT", "BUY CALL",
                "SELL TO OPEN", "BUY TO OPEN"
            ]) and "CLOSE" not in strategy
            
            if is_initial_open:
                # Try to build a roll chain starting from this position
                potential_chain = self._build_roll_chain_from_position(orders, i)
                if len(potential_chain) >= 3:  # At least initial + one roll (close + open)
                    chain_orders = potential_chain
                    break
        
        return chain_orders
    
    def _build_roll_chain_from_position(self, orders: List[Dict[str, Any]], start_idx: int) -> List[Dict[str, Any]]:
        """Build a roll chain starting from an initial position"""
        if start_idx >= len(orders):
            return []
        
        chain = [orders[start_idx]]  # Start with initial position
        current_idx = start_idx + 1
        
        # Look for subsequent close/open pairs
        while current_idx < len(orders) - 1:
            close_order = orders[current_idx]
            open_order = orders[current_idx + 1]
            
            # Check if this is a valid roll pair
            if self._is_roll_pair(close_order, open_order):
                chain.extend([close_order, open_order])
                current_idx += 2
            else:
                # Try to find the next close order
                found_close = False
                for j in range(current_idx, len(orders)):
                    if self._is_closing_order(orders[j]):
                        # Check if there's a corresponding open order after it
                        if j + 1 < len(orders) and self._is_roll_pair(orders[j], orders[j + 1]):
                            chain.extend([orders[j], orders[j + 1]])
                            current_idx = j + 2
                            found_close = True
                            break
                
                if not found_close:
                    break
        
        return chain
    
    def _is_closing_order(self, order: Dict[str, Any]) -> bool:
        """Check if an order is a closing order"""
        strategy = order.get("strategy", "").upper()
        return any(pattern in strategy for pattern in [
            "BUY TO CLOSE", "SELL TO CLOSE", "CLOSE"
        ])
    
    def _is_roll_pair(self, order1: Dict[str, Any], order2: Dict[str, Any]) -> bool:
        """
        Determine if two orders form a roll pair
        
        Roll pair criteria:
        - First order closes a position (BUY TO CLOSE or SELL TO CLOSE)
        - Second order opens a position (SELL TO OPEN or BUY TO OPEN)
        - Same option type (both puts or both calls)
        - Within time window (0-7 days apart)
        - Similar quantities (within 20% difference)
        """
        try:
            # Parse order details
            strategy1 = order1.get("strategy", "").upper()
            strategy2 = order2.get("strategy", "").upper()
            
            # Define close patterns
            close_patterns = [
                "BUY TO CLOSE PUT", "BUY TO CLOSE CALL", 
                "SELL TO CLOSE PUT", "SELL TO CLOSE CALL",
                "BTC PUT", "BTC CALL", "STC PUT", "STC CALL"  # Common abbreviations
            ]
            
            # Define open patterns  
            open_patterns = [
                "SELL PUT", "SELL CALL", "BUY PUT", "BUY CALL",
                "SELL TO OPEN PUT", "SELL TO OPEN CALL",
                "BUY TO OPEN PUT", "BUY TO OPEN CALL",
                "STO PUT", "STO CALL", "BTO PUT", "BTO CALL"  # Common abbreviations
            ]
            
            # Check if first order is close and second is open
            is_first_close = any(pattern in strategy1 for pattern in close_patterns)
            is_second_open = any(pattern in strategy2 for pattern in open_patterns)
            
            # Also check basic CLOSE/OPEN pattern
            if not is_first_close:
                is_first_close = "CLOSE" in strategy1 or "TO CLOSE" in strategy1
            if not is_second_open:
                is_second_open = ("OPEN" in strategy2 and "TO CLOSE" not in strategy2) or strategy2 in ["SELL PUT", "SELL CALL", "BUY PUT", "BUY CALL"]
            
            if not (is_first_close and is_second_open):
                return False
            
            # Check same option type
            type1 = order1.get("option_type", "").lower()
            type2 = order2.get("option_type", "").lower()
            if type1 != type2:
                return False
            
            # Check time window (0-7 days)
            time1_str = order1.get("created_at", "")
            time2_str = order2.get("created_at", "")
            
            if time1_str and time2_str:
                time1 = datetime.fromisoformat(time1_str.replace('Z', '+00:00'))
                time2 = datetime.fromisoformat(time2_str.replace('Z', '+00:00'))
                time_diff = abs((time2 - time1).total_seconds())
                
                # Must be within 7 days
                if time_diff > (7 * 24 * 3600):
                    return False
            
            # Check quantity similarity (within 20%)
            qty1 = float(order1.get("quantity", 0))
            qty2 = float(order2.get("quantity", 0))
            
            if qty1 > 0 and qty2 > 0:
                qty_ratio = abs(qty1 - qty2) / max(qty1, qty2)
                if qty_ratio > 0.2:  # More than 20% difference
                    return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Error checking roll pair: {str(e)}")
            return False
    
    async def _build_chain_from_orders(self, symbol: str, strategy_type: str, orders: List[Dict[str, Any]]) -> Optional[OptionsChain]:
        """Build a complete options chain from the roll sequence"""
        try:
            if len(orders) < 3:  # Need at least initial position + close + open
                return None
            
            # First order should be the initial position
            initial_order = orders[0]
            
            # Process remaining orders in pairs to create roll transactions
            rolls = []
            for i in range(1, len(orders) - 1, 2):
                if i + 1 < len(orders):
                    close_order = orders[i]
                    open_order = orders[i + 1]
                    
                    roll = self._create_roll_transaction(close_order, open_order)
                    if roll:
                        rolls.append(roll)
            
            if not rolls:
                return None
            
            # Calculate chain metadata
            first_roll = rolls[0]
            last_roll = rolls[-1]
            
            # Get initial position details for chain start date
            initial_date_str = initial_order.get("created_at", "")
            if initial_date_str:
                start_date = datetime.fromisoformat(initial_date_str.replace('Z', '+00:00'))
            else:
                start_date = first_roll.roll_date
            
            # Determine chain status
            status = await self._determine_chain_status(symbol, last_roll)
            
            # Calculate financial metrics including initial position
            initial_premium = float(initial_order.get("processed_premium", 0))
            initial_direction = initial_order.get("processed_premium_direction", "")
            
            # Initial position contribution to P&L
            if initial_direction == "credit":
                initial_contribution = initial_premium  # Received money
            else:
                initial_contribution = -initial_premium  # Paid money
                
            # Roll contributions
            total_credits = sum(roll.net_credit for roll in rolls if roll.net_credit > 0)
            total_debits = sum(abs(roll.net_credit) for roll in rolls if roll.net_credit < 0)
            roll_net = sum(roll.net_credit for roll in rolls)
            
            net_premium = initial_contribution + roll_net
            
            # Get current market data
            current_market_data = await self._get_current_market_data(symbol, last_roll)
            
            # Calculate P&L including initial position
            pnl_data = await self._calculate_chain_pnl(symbol, initial_order, rolls, current_market_data, status)
            
            chain = OptionsChain(
                chain_id=f"{symbol}_{start_date.strftime('%Y%m%d')}_{len(rolls)}",
                underlying_symbol=symbol,
                initial_strategy=strategy_type,
                start_date=start_date,
                last_roll_date=last_roll.roll_date if len(rolls) > 0 else None,
                status=status,
                total_rolls=len(rolls),
                current_strike=last_roll.open_strike if status == "active" else None,
                current_expiry=last_roll.open_expiry if status == "active" else None,
                current_option_type=last_roll.open_option_type,
                current_quantity=last_roll.open_quantity,
                total_credits_collected=total_credits + (initial_premium if initial_direction == "credit" else 0),
                total_debits_paid=total_debits + (initial_premium if initial_direction == "debit" else 0),
                net_premium=net_premium,
                unrealized_pnl=pnl_data["unrealized_pnl"],
                realized_pnl=pnl_data["realized_pnl"],
                total_pnl=pnl_data["total_pnl"],
                rolls=rolls,
                current_price=current_market_data["current_price"],
                mark_price=current_market_data["mark_price"],
                days_to_expiry=current_market_data["days_to_expiry"]
            )
            
            return chain
            
        except Exception as e:
            logger.error(f"Error building chain for {symbol}: {str(e)}")
            return None
    
    def _create_roll_transaction(self, close_order: Dict[str, Any], open_order: Dict[str, Any]) -> Optional[RollTransaction]:
        """Create a roll transaction from close and open orders"""
        try:
            close_date_str = close_order.get("created_at", "")
            open_date_str = open_order.get("created_at", "")
            
            # Use the later date as the roll date
            if close_date_str and open_date_str:
                close_date = datetime.fromisoformat(close_date_str.replace('Z', '+00:00'))
                open_date = datetime.fromisoformat(open_date_str.replace('Z', '+00:00'))
                roll_date = max(close_date, open_date)
            else:
                roll_date = datetime.now()
            
            # Extract order details
            close_strike = float(close_order.get("strike_price", 0))
            open_strike = float(open_order.get("strike_price", 0))
            
            close_expiry = close_order.get("expiration_date", "")
            open_expiry = open_order.get("expiration_date", "")
            
            # Calculate net credit/debit
            close_premium = float(close_order.get("processed_premium", 0))
            open_premium = float(open_order.get("processed_premium", 0))
            
            # For a typical roll: pay to close (debit) and collect to open (credit)
            close_direction = close_order.get("processed_premium_direction", "debit")
            open_direction = open_order.get("processed_premium_direction", "credit")
            
            close_amount = close_premium if close_direction == "credit" else -close_premium
            open_amount = open_premium if open_direction == "credit" else -open_premium
            
            net_credit = open_amount + close_amount
            
            # Analyze roll characteristics
            strike_direction = "same"
            if open_strike > close_strike:
                strike_direction = "up"
            elif open_strike < close_strike:
                strike_direction = "down"
            
            expiry_extension = 0
            if close_expiry and open_expiry:
                try:
                    close_exp_date = datetime.strptime(close_expiry, '%Y-%m-%d')
                    open_exp_date = datetime.strptime(open_expiry, '%Y-%m-%d')
                    expiry_extension = (open_exp_date - close_exp_date).days
                except ValueError:
                    pass
            
            # Determine roll type
            roll_type = self._classify_roll_type(strike_direction, expiry_extension, net_credit)
            
            roll = RollTransaction(
                roll_id=f"{close_order.get('order_id', '')}_{open_order.get('order_id', '')}",
                underlying_symbol=close_order.get("underlying_symbol", ""),
                roll_date=roll_date,
                close_order_id=close_order.get("order_id", ""),
                close_strike=close_strike,
                close_expiry=close_expiry,
                close_option_type=close_order.get("option_type", ""),
                close_quantity=float(close_order.get("quantity", 0)),
                close_price=float(close_order.get("price", 0)),
                close_premium=close_premium,
                open_order_id=open_order.get("order_id", ""),
                open_strike=open_strike,
                open_expiry=open_expiry,
                open_option_type=open_order.get("option_type", ""),
                open_quantity=float(open_order.get("quantity", 0)),
                open_price=float(open_order.get("price", 0)),
                open_premium=open_premium,
                net_credit=net_credit,
                strike_direction=strike_direction,
                expiry_extension=expiry_extension,
                roll_type=roll_type
            )
            
            return roll
            
        except Exception as e:
            logger.error(f"Error creating roll transaction: {str(e)}")
            return None
    
    def _classify_roll_type(self, strike_direction: str, expiry_extension: int, net_credit: float) -> str:
        """Classify the type of roll based on strike and expiry changes"""
        if strike_direction == "down" and net_credit < 0:
            return "defensive"  # Rolling down and out for a debit (protecting against loss)
        elif strike_direction == "up" and net_credit > 0:
            return "aggressive"  # Rolling up and out for credit (capturing more premium)
        elif strike_direction == "same" and expiry_extension > 0:
            return "time"  # Rolling out in time only
        else:
            return "mixed"  # Complex roll with mixed characteristics
    
    async def _determine_chain_status(self, symbol: str, last_roll: RollTransaction) -> str:
        """Determine if the chain is still active, closed, or expired"""
        try:
            # Check if there's a current position for this symbol/strike/expiry
            positions_result = await self.rh_service.get_options_positions()
            if not positions_result.get("success", False):
                return "unknown"
            
            positions = positions_result["data"]
            
            # Look for matching position
            for position in positions:
                if (position.get("underlying_symbol") == symbol and
                    abs(float(position.get("strike_price", 0)) - last_roll.open_strike) < 0.01 and
                    position.get("expiration_date") == last_roll.open_expiry):
                    return "active"
            
            # Check if expired
            if last_roll.open_expiry:
                try:
                    expiry_date = datetime.strptime(last_roll.open_expiry, '%Y-%m-%d')
                    if expiry_date < datetime.now():
                        return "expired"
                except ValueError:
                    pass
            
            return "closed"
            
        except Exception as e:
            logger.warning(f"Error determining chain status: {str(e)}")
            return "unknown"
    
    async def _get_current_market_data(self, symbol: str, last_roll: RollTransaction) -> Dict[str, Any]:
        """Get current market data for the position"""
        try:
            # This would need to be implemented based on available market data
            # For now, return placeholder values
            days_to_expiry = 0
            if last_roll.open_expiry:
                try:
                    expiry_date = datetime.strptime(last_roll.open_expiry, '%Y-%m-%d')
                    days_to_expiry = max(0, (expiry_date - datetime.now()).days)
                except ValueError:
                    pass
            
            return {
                "current_price": 0.0,
                "mark_price": last_roll.open_price,
                "days_to_expiry": days_to_expiry
            }
            
        except Exception as e:
            logger.warning(f"Error getting market data: {str(e)}")
            return {"current_price": 0.0, "mark_price": 0.0, "days_to_expiry": 0}
    
    async def _calculate_chain_pnl(self, symbol: str, initial_order: Dict[str, Any], rolls: List[RollTransaction], 
                                 market_data: Dict[str, Any], status: str) -> Dict[str, float]:
        """Calculate P&L for the entire chain including initial position"""
        try:
            # Initial position contribution
            initial_premium = float(initial_order.get("processed_premium", 0))
            initial_direction = initial_order.get("processed_premium_direction", "")
            
            if initial_direction == "credit":
                initial_pnl = initial_premium  # Received money
            else:
                initial_pnl = -initial_premium  # Paid money
            
            # Sum all roll credits/debits
            roll_pnl = sum(roll.net_credit for roll in rolls)
            
            # Total realized P&L includes initial position + all rolls
            realized_pnl = initial_pnl + roll_pnl
            
            # Calculate unrealized P&L if position is still active
            unrealized_pnl = 0.0
            if status == "active" and rolls:
                last_roll = rolls[-1]
                current_mark = market_data.get("mark_price", last_roll.open_price)
                
                # Determine if final position is long or short based on initial strategy
                initial_strategy = initial_order.get("strategy", "").upper()
                is_short_position = "SELL" in initial_strategy
                
                # For short positions, unrealized gain when option price decreases
                # For long positions, unrealized gain when option price increases
                if is_short_position:
                    unrealized_pnl = (last_roll.open_price - current_mark) * last_roll.open_quantity * 100
                else:
                    unrealized_pnl = (current_mark - last_roll.open_price) * last_roll.open_quantity * 100
            
            total_pnl = realized_pnl + unrealized_pnl
            
            return {
                "realized_pnl": realized_pnl,
                "unrealized_pnl": unrealized_pnl,
                "total_pnl": total_pnl
            }
            
        except Exception as e:
            logger.warning(f"Error calculating P&L: {str(e)}")
            return {"realized_pnl": 0.0, "unrealized_pnl": 0.0, "total_pnl": 0.0}
    
    def _calculate_chain_summary(self, chains: List[OptionsChain]) -> Dict[str, Any]:
        """Calculate summary statistics for all chains"""
        if not chains:
            return {
                "total_chains": 0,
                "active_chains": 0,
                "closed_chains": 0,
                "expired_chains": 0,
                "total_rolls": 0,
                "net_premium_collected": 0.0,
                "total_pnl": 0.0,
                "avg_rolls_per_chain": 0.0,
                "most_active_symbol": None
            }
        
        active_chains = [c for c in chains if c.status == "active"]
        closed_chains = [c for c in chains if c.status == "closed"]
        expired_chains = [c for c in chains if c.status == "expired"]
        
        total_rolls = sum(c.total_rolls for c in chains)
        net_premium = sum(c.net_premium for c in chains)
        total_pnl = sum(c.total_pnl for c in chains)
        
        # Find most active symbol
        symbol_counts = defaultdict(int)
        for chain in chains:
            symbol_counts[chain.underlying_symbol] += 1
        
        most_active_symbol = max(symbol_counts.items(), key=lambda x: x[1])[0] if symbol_counts else None
        
        return {
            "total_chains": len(chains),
            "active_chains": len(active_chains),
            "closed_chains": len(closed_chains),
            "expired_chains": len(expired_chains),
            "total_rolls": total_rolls,
            "net_premium_collected": net_premium,
            "total_pnl": total_pnl,
            "avg_rolls_per_chain": total_rolls / len(chains) if chains else 0.0,
            "most_active_symbol": most_active_symbol,
            "symbol_distribution": dict(symbol_counts)
        }
    
    def _chain_to_dict(self, chain: OptionsChain) -> Dict[str, Any]:
        """Convert OptionsChain to dictionary for JSON serialization"""
        return {
            "chain_id": chain.chain_id,
            "underlying_symbol": chain.underlying_symbol,
            "initial_strategy": chain.initial_strategy,
            "start_date": chain.start_date.isoformat(),
            "last_roll_date": chain.last_roll_date.isoformat() if chain.last_roll_date else None,
            "status": chain.status,
            "total_rolls": chain.total_rolls,
            "current_strike": chain.current_strike,
            "current_expiry": chain.current_expiry,
            "current_option_type": chain.current_option_type,
            "current_quantity": chain.current_quantity,
            "total_credits_collected": chain.total_credits_collected,
            "total_debits_paid": chain.total_debits_paid,
            "net_premium": chain.net_premium,
            "unrealized_pnl": chain.unrealized_pnl,
            "realized_pnl": chain.realized_pnl,
            "total_pnl": chain.total_pnl,
            "current_price": chain.current_price,
            "mark_price": chain.mark_price,
            "days_to_expiry": chain.days_to_expiry,
            "rolls": [self._roll_to_dict(roll) for roll in chain.rolls]
        }
    
    def _roll_to_dict(self, roll: RollTransaction) -> Dict[str, Any]:
        """Convert RollTransaction to dictionary for JSON serialization"""
        return {
            "roll_id": roll.roll_id,
            "underlying_symbol": roll.underlying_symbol,
            "roll_date": roll.roll_date.isoformat(),
            "close_order_id": roll.close_order_id,
            "close_strike": roll.close_strike,
            "close_expiry": roll.close_expiry,
            "close_option_type": roll.close_option_type,
            "close_quantity": roll.close_quantity,
            "close_price": roll.close_price,
            "close_premium": roll.close_premium,
            "open_order_id": roll.open_order_id,
            "open_strike": roll.open_strike,
            "open_expiry": roll.open_expiry,
            "open_option_type": roll.open_option_type,
            "open_quantity": roll.open_quantity,
            "open_price": roll.open_price,
            "open_premium": roll.open_premium,
            "net_credit": roll.net_credit,
            "strike_direction": roll.strike_direction,
            "expiry_extension": roll.expiry_extension,
            "roll_type": roll.roll_type
        }