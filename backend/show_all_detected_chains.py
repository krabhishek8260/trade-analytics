#!/usr/bin/env python3
"""
Show all detected chains from debug files with comprehensive details.
This script analyzes strategy codes and builds complete chain information.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime
from typing import Dict, List, Any

def load_and_analyze_chains():
    """Load debug files and analyze all detected chains"""
    debug_data_dir = Path(__file__).parent / "debug_data"
    options_files = list(debug_data_dir.glob("*options_orders*.json"))
    
    print(f"🔍 Analyzing {len(options_files)} options orders files...")
    print("=" * 80)
    
    # Data structures
    strategy_chains = defaultdict(list)  # strategy_code -> list of orders
    symbol_chains = defaultdict(set)     # symbol -> set of strategy codes
    all_orders = []
    
    # Process recent files (last 3 to avoid duplicates)
    for file_path in sorted(options_files, reverse=True)[:3]:
        print(f"📁 Processing {file_path.name}...")
        
        try:
            with open(file_path, 'r') as f:
                orders = json.load(f)
            
            file_orders = 0
            for order in orders:
                if order.get('state') != 'filled':
                    continue  # Only analyze filled orders
                
                legs = order.get('legs', [])
                if not legs:
                    continue
                
                # Extract strategy codes from all legs
                strategy_codes = set()
                for leg in legs:
                    long_code = leg.get('long_strategy_code', '')
                    short_code = leg.get('short_strategy_code', '')
                    if long_code:
                        strategy_codes.add(long_code)
                    if short_code:
                        strategy_codes.add(short_code)
                
                # Add order to each strategy code chain
                for code in strategy_codes:
                    if code:
                        order_info = {
                            'order_id': order.get('id', '')[:8] + '...',
                            'created_at': order.get('created_at', ''),
                            'chain_symbol': order.get('chain_symbol', ''),
                            'strategy': order.get('strategy', ''),
                            'form_source': order.get('form_source', ''),
                            'legs_count': len(legs),
                            'direction': order.get('direction', ''),
                            'processed_quantity': order.get('processed_quantity', 0),
                            'processed_premium': order.get('processed_premium', 0),
                            'legs': []
                        }
                        
                        # Extract leg details
                        for i, leg in enumerate(legs):
                            leg_info = {
                                'index': i,
                                'side': leg.get('side', ''),
                                'position_effect': leg.get('position_effect', ''),
                                'option_type': leg.get('option_type', ''),
                                'strike_price': leg.get('strike_price', ''),
                                'expiration_date': leg.get('expiration_date', ''),
                                'long_strategy_code': leg.get('long_strategy_code', ''),
                                'short_strategy_code': leg.get('short_strategy_code', '')
                            }
                            order_info['legs'].append(leg_info)
                        
                        strategy_chains[code].append(order_info)
                        symbol_chains[order.get('chain_symbol', '')].add(code)
                        file_orders += 1
                
                all_orders.append(order)
            
            print(f"   ✅ Processed {file_orders} orders")
            
        except Exception as e:
            print(f"   ❌ Error processing {file_path}: {e}")
    
    print(f"\n📊 ANALYSIS SUMMARY")
    print("=" * 80)
    print(f"Total orders processed: {len(all_orders)}")
    print(f"Unique strategy codes found: {len(strategy_chains)}")
    print(f"Symbols with chains: {len(symbol_chains)}")
    
    return strategy_chains, symbol_chains

def analyze_chain_patterns(strategy_chains: Dict[str, List[Dict[str, Any]]]):
    """Analyze patterns in the detected chains"""
    print(f"\n🔗 CHAIN PATTERNS ANALYSIS")
    print("=" * 80)
    
    # Group chains by length
    chains_by_length = defaultdict(list)
    for code, orders in strategy_chains.items():
        chains_by_length[len(orders)].append((code, orders))
    
    print(f"Chain length distribution:")
    for length in sorted(chains_by_length.keys()):
        count = len(chains_by_length[length])
        print(f"  {length} orders: {count} chains")
    
    # Find the most complex chains
    print(f"\n🏆 MOST COMPLEX CHAINS (10+ orders):")
    print("-" * 60)
    
    complex_chains = [(code, orders) for code, orders in strategy_chains.items() if len(orders) >= 10]
    complex_chains.sort(key=lambda x: len(x[1]), reverse=True)
    
    for i, (code, orders) in enumerate(complex_chains[:10]):
        symbol = orders[0]['chain_symbol'] if orders else 'Unknown'
        print(f"{i+1:2d}. {code[:20]}... - {len(orders)} orders for {symbol}")
    
    return chains_by_length

def show_detailed_chains(strategy_chains: Dict[str, List[Dict[str, Any]]], max_chains: int = 5):
    """Show detailed information for selected chains"""
    print(f"\n📋 DETAILED CHAIN EXAMPLES")
    print("=" * 80)
    
    # Sort chains by complexity (number of orders)
    sorted_chains = sorted(strategy_chains.items(), key=lambda x: len(x[1]), reverse=True)
    
    for i, (code, orders) in enumerate(sorted_chains[:max_chains]):
        if len(orders) < 2:
            continue
            
        print(f"\n🔗 CHAIN {i+1}: {code[:30]}...")
        print(f"   Symbol: {orders[0]['chain_symbol']}")
        print(f"   Total Orders: {len(orders)}")
        print(f"   Date Range: {orders[-1]['created_at'][:10]} to {orders[0]['created_at'][:10]}")
        print(f"   Strategy: {orders[0]['strategy']}")
        print(f"   Form Source: {orders[0]['form_source']}")
        
        # Show first few orders
        print(f"   Orders:")
        for j, order in enumerate(orders[:3]):  # Show first 3 orders
            date = order['created_at'][:10] if order['created_at'] else 'Unknown'
            print(f"     {j+1:2d}. {date} - {order['direction']} {order['processed_quantity']} contracts")
            if order['legs']:
                for leg in order['legs']:
                    print(f"        Leg {leg['index']}: {leg['side']} {leg['position_effect']} {leg['option_type']} {leg['strike_price']} {leg['expiration_date']}")
        
        if len(orders) > 3:
            print(f"     ... and {len(orders) - 3} more orders")
        
        print("-" * 60)

def show_symbol_summary(symbol_chains: Dict[str, set]):
    """Show summary of chains by symbol"""
    print(f"\n📈 CHAINS BY SYMBOL")
    print("=" * 80)
    
    # Sort symbols by number of chains
    sorted_symbols = sorted(symbol_chains.items(), key=lambda x: len(x[1]), reverse=True)
    
    print(f"Top symbols by number of chains:")
    for i, (symbol, codes) in enumerate(sorted_symbols[:15]):
        print(f"{i+1:2d}. {symbol:6s}: {len(codes):3d} chains")
    
    # Show some examples of symbols with many chains
    print(f"\n🔍 SYMBOLS WITH MOST COMPLEX TRADING:")
    print("-" * 50)
    
    for symbol, codes in sorted_symbols[:10]:
        if len(codes) >= 20:  # Only show symbols with significant chains
            print(f"{symbol}: {len(codes)} unique strategy codes")
            # Show a few example codes
            example_codes = list(codes)[:3]
            for code in example_codes:
                print(f"  - {code[:30]}...")

def main():
    """Main function to run the chain analysis"""
    print("🚀 ROLLED OPTIONS CHAIN DETECTION ANALYSIS")
    print("=" * 80)
    
    try:
        # Load and analyze chains
        strategy_chains, symbol_chains = load_and_analyze_chains()
        
        # Analyze patterns
        chains_by_length = analyze_chain_patterns(strategy_chains)
        
        # Show detailed examples
        show_detailed_chains(strategy_chains, max_chains=8)
        
        # Show symbol summary
        show_symbol_summary(symbol_chains)
        
        print(f"\n✅ Analysis complete!")
        print(f"Found {len(strategy_chains)} potential chains across {len(symbol_chains)} symbols")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
