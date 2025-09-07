#!/usr/bin/env python3
"""
Generate a comprehensive summary report of all detected chains.
This provides an overview of the chain detection system's output.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime
from typing import Dict, List, Any

def generate_chain_summary():
    """Generate comprehensive summary of all detected chains"""
    debug_data_dir = Path(__file__).parent / "debug_data"
    options_files = list(debug_data_dir.glob("*options_orders*.json"))
    
    print("📊 COMPREHENSIVE CHAIN DETECTION SUMMARY REPORT")
    print("=" * 80)
    print(f"Generated from {len(options_files)} debug files")
    print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Data structures
    strategy_chains = defaultdict(list)
    symbol_chains = defaultdict(set)
    chain_lengths = Counter()
    strategy_types = Counter()
    form_sources = Counter()
    
    # Process recent files (last 2 to avoid duplicates)
    for file_path in sorted(options_files, reverse=True)[:2]:
        print(f"📁 Processing {file_path.name}...")
        
        try:
            with open(file_path, 'r') as f:
                orders = json.load(f)
            
            file_orders = 0
            for order in orders:
                if order.get('state') != 'filled':
                    continue
                
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
                            'processed_premium': order.get('processed_premium', 0)
                        }
                        
                        strategy_chains[code].append(order_info)
                        symbol_chains[order.get('chain_symbol', '')].add(code)
                        file_orders += 1
                
                # Track metadata
                if order.get('strategy'):
                    strategy_types[order.get('strategy')] += 1
                if order.get('form_source'):
                    form_sources[order.get('form_source')] += 1
            
            print(f"   ✅ Processed {file_orders} orders")
            
        except Exception as e:
            print(f"   ❌ Error processing {file_path}: {e}")
    
    # Analyze chain lengths
    for code, orders in strategy_chains.items():
        chain_lengths[len(orders)] += 1
    
    # Generate summary statistics
    total_chains = len(strategy_chains)
    total_symbols = len(symbol_chains)
    total_orders = sum(len(orders) for orders in strategy_chains.values())
    
    print(f"\n📈 SUMMARY STATISTICS")
    print("-" * 60)
    print(f"Total Strategy Codes: {total_chains:,}")
    print(f"Total Symbols: {total_symbols}")
    print(f"Total Orders in Chains: {total_orders:,}")
    print(f"Average Orders per Chain: {total_orders/total_chains:.1f}")
    
    # Chain length distribution
    print(f"\n🔗 CHAIN LENGTH DISTRIBUTION")
    print("-" * 60)
    for length in sorted(chain_lengths.keys()):
        count = chain_lengths[length]
        percentage = (count / total_chains) * 100
        print(f"{length:2d} orders: {count:4d} chains ({percentage:5.1f}%)")
    
    # Top symbols by chain count
    print(f"\n🏆 TOP SYMBOLS BY CHAIN COUNT")
    print("-" * 60)
    sorted_symbols = sorted(symbol_chains.items(), key=lambda x: len(x[1]), reverse=True)
    
    for i, (symbol, codes) in enumerate(sorted_symbols[:20]):
        print(f"{i+1:2d}. {symbol:6s}: {len(codes):3d} chains")
    
    # Most complex chains
    print(f"\n🔥 MOST COMPLEX CHAINS (15+ orders)")
    print("-" * 60)
    complex_chains = [(code, orders) for code, orders in strategy_chains.items() if len(orders) >= 15]
    complex_chains.sort(key=lambda x: len(x[1]), reverse=True)
    
    for i, (code, orders) in enumerate(complex_chains[:15]):
        symbol = orders[0]['chain_symbol'] if orders else 'Unknown'
        print(f"{i+1:2d}. {code[:25]}... - {len(orders):2d} orders for {symbol}")
    
    # Strategy type analysis
    print(f"\n📋 STRATEGY TYPE ANALYSIS")
    print("-" * 60)
    top_strategies = strategy_types.most_common(15)
    for strategy, count in top_strategies:
        print(f"{strategy:25s}: {count:4d} orders")
    
    # Form source analysis
    print(f"\n🏷️  FORM SOURCE ANALYSIS")
    print("-" * 60)
    top_sources = form_sources.most_common(10)
    for source, count in top_sources:
        print(f"{source:25s}: {count:4d} orders")
    
    # Chain examples by category
    print(f"\n💡 CHAIN EXAMPLES BY CATEGORY")
    print("-" * 60)
    
    # Single-leg chains
    single_leg_chains = [(code, orders) for code, orders in strategy_chains.items() 
                         if all(order['legs_count'] == 1 for order in orders)]
    if single_leg_chains:
        print(f"Single-leg chains: {len(single_leg_chains)}")
        example = single_leg_chains[0]
        print(f"  Example: {example[0][:25]}... - {len(example[1])} orders for {example[1][0]['chain_symbol']}")
    
    # Multi-leg chains
    multi_leg_chains = [(code, orders) for code, orders in strategy_chains.items() 
                        if any(order['legs_count'] > 1 for order in orders)]
    if multi_leg_chains:
        print(f"Multi-leg chains: {len(multi_leg_chains)}")
        example = multi_leg_chains[0]
        print(f"  Example: {example[0][:25]}... - {len(example[1])} orders for {example[1][0]['chain_symbol']}")
    
    # Long-term chains (6+ months)
    long_term_chains = []
    for code, orders in strategy_chains.items():
        if len(orders) >= 2:
            try:
                first_date = datetime.fromisoformat(orders[0]['created_at'].replace('Z', '+00:00'))
                last_date = datetime.fromisoformat(orders[-1]['created_at'].replace('Z', '+00:00'))
                duration = (last_date - first_date).days
                if duration >= 180:  # 6 months
                    long_term_chains.append((code, orders, duration))
            except:
                continue
    
    if long_term_chains:
        long_term_chains.sort(key=lambda x: x[2], reverse=True)
        print(f"Long-term chains (6+ months): {len(long_term_chains)}")
        example = long_term_chains[0]
        print(f"  Example: {example[0][:25]}... - {example[2]} days for {example[1][0]['chain_symbol']}")
    
    # Performance metrics
    print(f"\n⚡ PERFORMANCE METRICS")
    print("-" * 60)
    
    # Calculate average chain metrics
    avg_chain_length = total_orders / total_chains
    chains_with_rolls = sum(1 for orders in strategy_chains.values() if len(orders) >= 3)
    
    print(f"Average chain length: {avg_chain_length:.1f} orders")
    print(f"Chains with potential rolls (3+ orders): {chains_with_rolls:,}")
    print(f"Roll detection rate: {(chains_with_rolls/total_chains)*100:.1f}%")
    
    # Data quality metrics
    orders_with_strategy = sum(1 for orders in strategy_chains.values() 
                              if any(order.get('strategy') for order in orders))
    orders_with_form_source = sum(1 for orders in strategy_chains.values() 
                                 if any(order.get('form_source') for order in orders))
    
    print(f"Orders with strategy field: {orders_with_strategy:,}")
    print(f"Orders with form_source field: {orders_with_form_source:,}")
    
    print(f"\n✅ Summary report complete!")
    print(f"Found {total_chains:,} potential chains across {total_symbols} symbols")

def main():
    """Main function"""
    generate_chain_summary()

if __name__ == "__main__":
    main()
