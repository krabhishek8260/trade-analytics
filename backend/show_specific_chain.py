#!/usr/bin/env python3
"""
Show detailed information about a specific chain.
This script demonstrates how the chain detection works with a real example.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

def show_nvda_chain_example():
    """Show detailed information about the NVDA chain with 30 orders"""
    debug_data_dir = Path(__file__).parent / "debug_data"
    
    # Target strategy code from the analysis
    target_code = "c23aa70d-f0c0-4c5f-bfad-52e9905e75b4"
    
    print(f"🔍 ANALYZING NVDA CHAIN: {target_code}")
    print("=" * 80)
    
    # Find the most recent file
    options_files = list(debug_data_dir.glob("*options_orders*.json"))
    if not options_files:
        print("No options orders files found")
        return
    
    latest_file = sorted(options_files, reverse=True)[0]
    print(f"📁 Using file: {latest_file.name}")
    
    try:
        with open(latest_file, 'r') as f:
            orders = json.load(f)
        
        # Find all orders with this strategy code
        chain_orders = []
        for order in orders:
            if order.get('state') != 'filled':
                continue
                
            legs = order.get('legs', [])
            for leg in legs:
                long_code = leg.get('long_strategy_code', '')
                short_code = leg.get('short_strategy_code', '')
                
                if target_code in long_code or target_code in short_code:
                    chain_orders.append(order)
                    break
        
        if not chain_orders:
            print(f"❌ No orders found with strategy code: {target_code}")
            return
        
        print(f"✅ Found {len(chain_orders)} orders in this chain")
        print()
        
        # Sort orders by date
        chain_orders.sort(key=lambda x: x.get('created_at', ''))
        
        # Analyze the chain
        print("📊 CHAIN ANALYSIS")
        print("-" * 60)
        
        # Group by position effect and side
        position_summary = defaultdict(int)
        total_quantity = 0
        total_premium = 0
        
        for order in chain_orders:
            legs = order.get('legs', [])
            for leg in legs:
                if target_code in leg.get('long_strategy_code', '') or target_code in leg.get('short_strategy_code', ''):
                    position_key = f"{leg.get('side', '')} {leg.get('position_effect', '')}"
                    position_summary[position_key] += 1
                    
                    # Calculate totals
                    quantity = float(order.get('processed_quantity', 0))
                    premium = float(order.get('processed_premium', 0))
                    total_quantity += quantity
                    total_premium += premium
        
        print("Position Summary:")
        for position, count in sorted(position_summary.items()):
            print(f"  {position}: {count} occurrences")
        
        print(f"\nTotal Quantity: {total_quantity}")
        print(f"Total Premium: ${total_premium:,.2f}")
        
        # Show detailed order timeline
        print(f"\n📅 ORDER TIMELINE")
        print("-" * 60)
        
        for i, order in enumerate(chain_orders):
            date = order.get('created_at', '')[:10]
            time = order.get('created_at', '')[11:19]
            direction = order.get('direction', '')
            quantity = order.get('processed_quantity', 0)
            premium = order.get('processed_premium', 0)
            strategy = order.get('strategy', '')
            
            print(f"{i+1:2d}. {date} {time} - {direction.upper()} {quantity} contracts (${float(premium):,.2f})")
            
            # Show leg details
            legs = order.get('legs', [])
            for j, leg in enumerate(legs):
                if target_code in leg.get('long_strategy_code', '') or target_code in leg.get('short_strategy_code', ''):
                    side = leg.get('side', '')
                    effect = leg.get('position_effect', '')
                    option_type = leg.get('option_type', '')
                    strike = leg.get('strike_price', '')
                    expiry = leg.get('expiration_date', '')
                    
                    print(f"     Leg {j}: {side} {effect} {option_type} {strike} {expiry}")
            
            print()
        
        # Show chain characteristics
        print("🔗 CHAIN CHARACTERISTICS")
        print("-" * 60)
        
        first_order = chain_orders[0]
        last_order = chain_orders[-1]
        
        first_date = datetime.fromisoformat(first_order.get('created_at', '').replace('Z', '+00:00'))
        last_date = datetime.fromisoformat(last_order.get('created_at', '').replace('Z', '+00:00'))
        duration = last_date - first_date
        
        print(f"Start Date: {first_date.strftime('%Y-%m-%d')}")
        print(f"End Date: {last_date.strftime('%Y-%m-%d')}")
        print(f"Duration: {duration.days} days")
        print(f"Orders per month: {len(chain_orders) / (duration.days / 30):.1f}")
        
        # Analyze strategy evolution
        strategies = [order.get('strategy', '') for order in chain_orders]
        unique_strategies = set(strategies)
        
        print(f"\nStrategy Evolution:")
        for strategy in unique_strategies:
            count = strategies.count(strategy)
            print(f"  {strategy}: {count} orders")
        
        print(f"\n✅ Chain analysis complete!")
        
    except Exception as e:
        print(f"❌ Error analyzing chain: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function"""
    print("🚀 SPECIFIC CHAIN ANALYSIS")
    print("=" * 80)
    
    show_nvda_chain_example()

if __name__ == "__main__":
    main()
