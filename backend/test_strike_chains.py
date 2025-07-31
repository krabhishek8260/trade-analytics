#!/usr/bin/env python3
"""
Test strike-based chain logic directly without full app dependencies
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict

def extract_roll_info(order: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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

def build_chain_from_start(start_info: Dict[str, Any], all_infos: List[Dict[str, Any]], used_orders: Set[str]) -> List[Dict[str, Any]]:
    """Build a chain starting from an initial SELL TO OPEN order"""
    chain = [start_info]
    current_opens = start_info["opens"]
    
    print(f"  Starting chain with order {start_info['order_id'][:8]}...")
    print(f"    Initial opens: {[(leg['strike_price'], leg['option_type']) for leg in current_opens]}")
    
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
                        print(f"    Found next: {info['order_id'][:8]} closes {close_leg['strike_price']} {close_leg['option_type']}")
                        break
                if next_order:
                    break
            if next_order:
                break
        
        if not next_order:
            print(f"    No more orders found for current opens")
            break
        
        chain.append(next_order)
        
        # Update current opens for next iteration
        # Remove the strikes that were closed and add newly opened strikes
        new_opens = []
        
        # Add any opens from this order
        new_opens.extend(next_order["opens"])
        print(f"    Added new opens: {[(leg['strike_price'], leg['option_type']) for leg in next_order['opens']]}")
        
        # Remove closed strikes from previous opens
        for open_leg in current_opens:
            was_closed = False
            for close_leg in next_order["closes"]:
                if (close_leg["strike_price"] == open_leg["strike_price"] and
                    close_leg["option_type"] == open_leg["option_type"]):
                    was_closed = True
                    print(f"    Closed strike: {close_leg['strike_price']} {close_leg['option_type']}")
                    break
            if not was_closed:
                new_opens.append(open_leg)
        
        current_opens = new_opens
        print(f"    Current opens after processing: {[(leg['strike_price'], leg['option_type']) for leg in current_opens]}")
    
    return chain

def build_strike_based_chains(orders: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """Build chains based on strike price progressions and leg patterns"""
    if not orders:
        return []
    
    print(f"Building chains from {len(orders)} orders")
    
    # Sort orders chronologically
    sorted_orders = sorted(
        orders, 
        key=lambda x: datetime.fromisoformat(x.get("created_at", "").replace('Z', '+00:00'))
    )
    
    # Extract roll information from each order
    roll_info = []
    for order in sorted_orders:
        info = extract_roll_info(order)
        if info:
            roll_info.append(info)
    
    print(f"Extracted roll info from {len(roll_info)} orders:")
    for info in roll_info:
        print(f"  Order {info['order_id'][:8]}: {info['legs_count']} legs, {len(info['opens'])} opens, {len(info['closes'])} closes")
    
    chains = []
    used_orders = set()
    
    # Start with orders that have SELL TO OPEN but no BUY TO CLOSE (initial positions)
    starting_orders = [
        info for info in roll_info 
        if info["opens"] and not info["closes"] and info["order_id"] not in used_orders
    ]
    
    print(f"\nFound {len(starting_orders)} potential starting orders")
    
    for start_info in starting_orders:
        print(f"\nTrying to build chain from order {start_info['order_id'][:8]}...")
        chain = build_chain_from_start(start_info, roll_info, used_orders)
        if len(chain) >= 2:  # At least 2 orders to be considered a chain
            print(f"  ✓ Built chain with {len(chain)} orders")
            chains.append([info["order"] for info in chain])
            used_orders.update(info["order_id"] for info in chain)
        else:
            print(f"  ✗ Chain too short ({len(chain)} orders)")
    
    print(f"\nBuilt {len(chains)} chains from starting orders")
    return chains

def test_tsll_chains():
    """Test TSLL chain building"""
    
    # Load one JSON file
    debug_data_dir = Path(__file__).parent / "debug_data"
    test_file = debug_data_dir / "20250728_050310_options_orders.json"
    
    print(f"=== Testing TSLL Strike-Based Chains ===")
    print(f"Loading from: {test_file}")
    
    with open(test_file, 'r') as f:
        orders = json.load(f)
    
    print(f"Total orders in file: {len(orders)}")
    
    # Filter for TSLL filled orders
    tsll_orders = []
    for order in orders:
        if (order.get("chain_symbol") == "TSLL" and 
            order.get("state") == "filled"):
            tsll_orders.append(order)
    
    print(f"TSLL filled orders: {len(tsll_orders)}")
    
    if not tsll_orders:
        print("No TSLL orders found!")
        return
    
    # Show some sample orders
    print(f"\nSample TSLL orders:")
    for i, order in enumerate(tsll_orders[:3]):
        legs = order.get("legs", [])
        print(f"  Order {i+1}: {order.get('id', 'unknown')[:8]} - {len(legs)} legs")
        for j, leg in enumerate(legs):
            effect = leg.get("position_effect", "unknown")
            side = leg.get("side", "unknown")
            strike = leg.get("strike_price", "unknown")
            opt_type = leg.get("option_type", "unknown")
            print(f"    Leg {j+1}: {side} to {effect} {strike} {opt_type}")
    
    # Build chains
    chains = build_strike_based_chains(tsll_orders)
    
    print(f"\n=== Chain Analysis Results ===")
    print(f"Found {len(chains)} TSLL chains")
    
    for i, chain in enumerate(chains):
        print(f"\nChain {i+1}: {len(chain)} orders")
        for j, order in enumerate(chain):
            legs = order.get("legs", [])
            print(f"  Order {j+1}: {order.get('id', 'unknown')[:8]} ({len(legs)} legs)")
            for k, leg in enumerate(legs):
                effect = leg.get("position_effect", "unknown")
                side = leg.get("side", "unknown")
                strike = leg.get("strike_price", "unknown")
                opt_type = leg.get("option_type", "unknown")
                print(f"    Leg {k+1}: {side} to {effect} {strike} {opt_type}")

if __name__ == "__main__":
    test_tsll_chains()