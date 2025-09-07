#!/usr/bin/env python3
"""
Analyze long_strategy_code and short_strategy_code patterns in debug data
to understand how they can be used for chain detection.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

def analyze_strategy_codes():
    """Analyze strategy codes across all debug files"""
    debug_data_dir = Path(__file__).parent / "debug_data"
    options_files = list(debug_data_dir.glob("*options_orders*.json"))
    
    print(f"Found {len(options_files)} options orders files")
    
    # Data structures to analyze patterns
    strategy_code_patterns = defaultdict(list)  # strategy_code -> list of orders
    chain_symbol_codes = defaultdict(set)  # chain_symbol -> set of strategy codes seen
    multi_leg_orders = []  # Orders with multiple legs
    roll_orders = []  # Orders identified as rolls by current logic
    
    total_orders = 0
    orders_with_codes = 0
    
    # Process recent files (last 5)
    for file_path in sorted(options_files, reverse=True)[:5]:
        print(f"\nProcessing {file_path.name}...")
        
        try:
            with open(file_path, 'r') as f:
                orders = json.load(f)
            
            file_orders = 0
            file_with_codes = 0
            
            for order in orders:
                total_orders += 1
                file_orders += 1
                
                if order.get('state') != 'filled':
                    continue  # Only analyze filled orders
                
                legs = order.get('legs', [])
                if not legs:
                    continue
                
                chain_symbol = order.get('chain_symbol', '')
                order_id = order.get('id', '')
                created_at = order.get('created_at', '')
                
                # Analyze each leg's strategy codes
                leg_codes = []
                has_codes = False
                
                for i, leg in enumerate(legs):
                    long_code = leg.get('long_strategy_code', '')
                    short_code = leg.get('short_strategy_code', '')
                    
                    if long_code or short_code:
                        has_codes = True
                        orders_with_codes += 1
                        file_with_codes += 1
                        
                        leg_info = {
                            'leg_index': i,
                            'long_strategy_code': long_code,
                            'short_strategy_code': short_code,
                            'position_effect': leg.get('position_effect', ''),
                            'side': leg.get('side', ''),
                            'option_type': leg.get('option_type', ''),
                            'strike_price': leg.get('strike_price', ''),
                            'expiration_date': leg.get('expiration_date', '')
                        }
                        leg_codes.append(leg_info)
                        
                        # Track strategy codes by chain symbol
                        if chain_symbol:
                            chain_symbol_codes[chain_symbol].add(long_code)
                            chain_symbol_codes[chain_symbol].add(short_code)
                        
                        # Store in strategy code patterns
                        if long_code:
                            strategy_code_patterns[long_code].append({
                                'order_id': order_id,
                                'created_at': created_at,
                                'chain_symbol': chain_symbol,
                                'leg_index': i,
                                'position_effect': leg.get('position_effect', ''),
                                'side': leg.get('side', ''),
                                'is_multi_leg': len(legs) > 1
                            })
                        
                        if short_code:
                            strategy_code_patterns[short_code].append({
                                'order_id': order_id,
                                'created_at': created_at,
                                'chain_symbol': chain_symbol,
                                'leg_index': i,
                                'position_effect': leg.get('position_effect', ''),
                                'side': leg.get('side', ''),
                                'is_multi_leg': len(legs) > 1
                            })
                
                if has_codes:
                    order_analysis = {
                        'order_id': order_id,
                        'created_at': created_at,
                        'chain_symbol': chain_symbol,
                        'legs_count': len(legs),
                        'leg_codes': leg_codes,
                        'strategy': order.get('strategy', ''),
                        'form_source': order.get('form_source', ''),
                        'opening_strategy': order.get('opening_strategy', ''),
                        'closing_strategy': order.get('closing_strategy', '')
                    }
                    
                    # Check if multi-leg
                    if len(legs) > 1:
                        multi_leg_orders.append(order_analysis)
                    
                    # Check if roll using current logic
                    if is_roll_order_current_logic(order):
                        roll_orders.append(order_analysis)
            
            print(f"  {file_orders} orders, {file_with_codes} with strategy codes")
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    # Analysis results
    print(f"\n=== STRATEGY CODE ANALYSIS ===")
    print(f"Total orders processed: {total_orders}")
    print(f"Orders with strategy codes: {orders_with_codes}")
    print(f"Multi-leg orders with codes: {len(multi_leg_orders)}")
    print(f"Roll orders with codes: {len(roll_orders)}")
    
    # Analyze code patterns
    print(f"\n=== CODE PATTERNS ===")
    unique_long_codes = set()
    unique_short_codes = set()
    
    for code, occurrences in strategy_code_patterns.items():
        if '_L' in code:
            unique_long_codes.add(code)
        elif '_S' in code:
            unique_short_codes.add(code)
    
    print(f"Unique long strategy codes: {len(unique_long_codes)}")
    print(f"Unique short strategy codes: {len(unique_short_codes)}")
    
    # Look for codes that appear in multiple orders (potential chain indicators)
    reused_codes = {}
    for code, occurrences in strategy_code_patterns.items():
        if len(occurrences) > 1:
            reused_codes[code] = occurrences
    
    print(f"\nStrategy codes appearing in multiple orders: {len(reused_codes)}")
    
    if reused_codes:
        print("\nTop reused strategy codes:")
        sorted_reused = sorted(reused_codes.items(), key=lambda x: len(x[1]), reverse=True)
        
        for code, occurrences in sorted_reused[:5]:
            print(f"\n  Code: {code}")
            print(f"  Appears in {len(occurrences)} orders:")
            
            for occ in occurrences:
                print(f"    Order {occ['order_id'][:8]}... - {occ['created_at']} - {occ['chain_symbol']} - {occ['position_effect']} {occ['side']}")
                
                # Check if this looks like a roll pattern
                same_code_orders = [o for o in occurrences if o['chain_symbol'] == occ['chain_symbol']]
                if len(same_code_orders) > 1:
                    print(f"      ^ Potential chain: {len(same_code_orders)} orders for {occ['chain_symbol']}")
    
    # Analyze multi-leg patterns
    print(f"\n=== MULTI-LEG ORDERS ===")
    if multi_leg_orders:
        print(f"Found {len(multi_leg_orders)} multi-leg orders")
        
        # Look for patterns in multi-leg orders
        for order in multi_leg_orders[:3]:  # Show first 3 examples
            print(f"\nOrder {order['order_id'][:8]}... - {order['chain_symbol']}")
            print(f"  Strategy: {order['strategy']}")
            print(f"  Form source: {order['form_source']}")
            print(f"  Legs: {order['legs_count']}")
            
            for leg in order['leg_codes']:
                print(f"    Leg {leg['leg_index']}: {leg['position_effect']} {leg['side']} - Long: {leg['long_strategy_code']}, Short: {leg['short_strategy_code']}")
    
    # Chain symbol analysis
    print(f"\n=== CHAIN SYMBOL PATTERNS ===")
    for symbol, codes in list(chain_symbol_codes.items())[:5]:
        print(f"{symbol}: {len(codes)} unique strategy codes")
        if len(codes) > 3:  # Show symbols with multiple codes (potential chains)
            print(f"  Codes: {list(codes)[:3]}...")

def is_roll_order_current_logic(order):
    """Replicate current roll detection logic"""
    form_source = order.get('form_source', '').lower()
    strategy = order.get('strategy', '').lower()
    
    # Current logic checks
    if form_source == 'strategy_roll':
        return True
    
    if 'roll' in strategy or 'calendar_spread' in strategy:
        return True
    
    # Check for both open and close position effects
    legs = order.get('legs', [])
    if len(legs) >= 2:
        has_open = any(leg.get('position_effect') == 'open' for leg in legs)
        has_close = any(leg.get('position_effect') == 'close' for leg in legs)
        if has_open and has_close:
            return True
    
    return False

if __name__ == "__main__":
    analyze_strategy_codes()