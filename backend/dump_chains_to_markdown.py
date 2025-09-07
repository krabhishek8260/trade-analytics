#!/usr/bin/env python3
"""
Dump all detected chains with their orders into a markdown file.
This provides a complete view of all chains for analysis.
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any

def analyze_chain_position_flow(orders):
    """Analyze the position flow of a chain to identify opening/closing orders"""
    opening_quantity = 0
    closing_quantity = 0
    opening_orders = []
    closing_orders = []
    
    for order in orders:
        legs = order.get('legs', [])
        for leg in legs:
            effect = leg.get('position_effect', '')
            side = leg.get('side', '')
            quantity = float(order.get('processed_quantity', 0))
            
            if effect == 'open':
                if side == 'buy':
                    opening_quantity += quantity
                    opening_orders.append(order)
                elif side == 'sell':
                    opening_quantity -= quantity
                    opening_orders.append(order)
            elif effect == 'close':
                if side == 'sell':
                    closing_quantity += quantity
                    closing_orders.append(order)
                elif side == 'buy':
                    closing_quantity -= quantity
                    closing_orders.append(order)
    
    return {
        'opening_quantity': opening_quantity,
        'closing_quantity': closing_quantity,
        'net_position': opening_quantity - closing_quantity,
        'opening_orders': opening_orders,
        'closing_orders': closing_orders,
        'is_complete': abs(opening_quantity - closing_quantity) < 0.01  # Within rounding error
    }

def dump_chains_to_markdown():
    """Dump all detected chains to a markdown file"""
    debug_data_dir = Path(__file__).parent / "debug_data"
    options_files = list(debug_data_dir.glob("*options_orders*.json"))
    
    if not options_files:
        print("No options orders files found")
        return
    
    # Use only the latest file
    latest_file = sorted(options_files, reverse=True)[0]
    print(f"📁 Processing latest file: {latest_file.name}")
    
    # Data structures
    strategy_chains = defaultdict(list)
    symbol_chains = defaultdict(set)
    
    try:
        with open(latest_file, 'r') as f:
            orders = json.load(f)
        
        print(f"📊 Processing {len(orders)} orders...")
        
        # Process all orders
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
                        'order_id': order.get('id', ''),
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
        
        print(f"✅ Found {len(strategy_chains)} unique chains")
        
        # Sort chains by complexity (number of orders)
        sorted_chains = sorted(strategy_chains.items(), key=lambda x: len(x[1]), reverse=True)
        
        # Generate markdown file
        output_file = f"detected_chains_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        with open(output_file, 'w') as f:
            f.write("# Detected Options Trading Chains\n\n")
            f.write(f"Generated from: {latest_file.name}\n")
            f.write(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total chains: {len(strategy_chains)}\n")
            f.write(f"Total symbols: {len(symbol_chains)}\n\n")
            
            # Summary statistics
            f.write("## Summary Statistics\n\n")
            f.write(f"- **Total Strategy Codes**: {len(strategy_chains):,}\n")
            f.write(f"- **Total Symbols**: {len(symbol_chains)}\n")
            f.write(f"- **Total Orders**: {sum(len(orders) for orders in strategy_chains.values()):,}\n")
            f.write(f"- **Average Orders per Chain**: {sum(len(orders) for orders in strategy_chains.values()) / len(strategy_chains):.1f}\n\n")
            
            # Chain length distribution
            chain_lengths = defaultdict(int)
            for code, orders in strategy_chains.items():
                chain_lengths[len(orders)] += 1
            
            f.write("### Chain Length Distribution\n\n")
            for length in sorted(chain_lengths.keys()):
                count = chain_lengths[length]
                percentage = (count / len(strategy_chains)) * 100
                f.write(f"- **{length} orders**: {count} chains ({percentage:.1f}%)\n")
            f.write("\n")
            
            # Top symbols
            sorted_symbols = sorted(symbol_chains.items(), key=lambda x: len(x[1]), reverse=True)
            f.write("### Top Symbols by Chain Count\n\n")
            for i, (symbol, codes) in enumerate(sorted_symbols[:20]):
                f.write(f"{i+1}. **{symbol}**: {len(codes)} chains\n")
            f.write("\n")
            
            # Detailed chains
            f.write("## Detailed Chain Analysis\n\n")
            
            for i, (code, orders) in enumerate(sorted_chains):
                if len(orders) < 2:
                    continue
                
                # Sort orders by date
                orders.sort(key=lambda x: x.get('created_at', ''))
                
                # Analyze position flow
                position_analysis = analyze_chain_position_flow(orders)
                
                f.write(f"### Chain {i+1}: {code}\n\n")
                f.write(f"**Symbol**: {orders[0]['chain_symbol']}\n")
                f.write(f"**Total Orders**: {len(orders)}\n")
                f.write(f"**Strategy**: {orders[0].get('strategy', 'N/A')}\n")
                f.write(f"**Form Source**: {orders[0].get('form_source', 'N/A')}\n")
                
                # Position flow summary
                f.write(f"**Position Flow**:\n")
                f.write(f"- Opening Quantity: {position_analysis['opening_quantity']:+.2f}\n")
                f.write(f"- Closing Quantity: {position_analysis['closing_quantity']:+.2f}\n")
                f.write(f"- Net Position: {position_analysis['net_position']:+.2f}\n")
                f.write(f"- Chain Status: {'✅ COMPLETE' if position_analysis['is_complete'] else '🔄 INCOMPLETE'}\n")
                
                if len(orders) >= 2:
                    try:
                        first_date = datetime.fromisoformat(orders[0]['created_at'].replace('Z', '+00:00'))
                        last_date = datetime.fromisoformat(orders[-1]['created_at'].replace('Z', '+00:00'))
                        duration = (last_date - first_date).days
                        f.write(f"**Duration**: {duration} days\n")
                        f.write(f"**Date Range**: {first_date.strftime('%Y-%m-%d')} to {last_date.strftime('%Y-%m-%d')}\n")
                    except:
                        pass
                
                f.write("\n")
                
                # Order details with opening/closing indicators
                f.write("#### Orders\n\n")
                f.write("| # | Date | Time | Direction | Quantity | Premium | Strategy | Legs | Type |\n")
                f.write("|---|------|------|-----------|----------|---------|----------|------|------|\n")
                
                for j, order in enumerate(orders):
                    date = order['created_at'][:10] if order['created_at'] else 'N/A'
                    time = order['created_at'][11:19] if order['created_at'] and len(order['created_at']) > 19 else 'N/A'
                    direction = order['direction'].upper() if order['direction'] else 'N/A'
                    quantity = order['processed_quantity'] if order['processed_quantity'] else 0
                    premium = order['processed_premium'] if order['processed_premium'] else 0
                    strategy = order.get('strategy', 'N/A')
                    legs_count = order['legs_count']
                    
                    # Determine order type
                    order_type = "N/A"
                    for leg in order['legs']:
                        effect = leg.get('position_effect', '')
                        if effect == 'open':
                            order_type = "🟢 OPEN"
                        elif effect == 'close':
                            order_type = "🔴 CLOSE"
                    
                    f.write(f"| {j+1} | {date} | {time} | {direction} | {quantity} | ${float(premium):,.2f} | {strategy} | {legs_count} | {order_type} |\n")
                
                f.write("\n")
                
                # Position flow analysis
                f.write("#### Position Flow Analysis\n\n")
                f.write(f"- **Opening Orders**: {len(position_analysis['opening_orders'])} orders\n")
                f.write(f"- **Closing Orders**: {len(position_analysis['closing_orders'])} orders\n")
                
                if position_analysis['opening_orders']:
                    f.write(f"- **Opening Dates**: {position_analysis['opening_orders'][0]['created_at'][:10]} to {position_analysis['opening_orders'][-1]['created_at'][:10]}\n")
                
                if position_analysis['closing_orders']:
                    f.write(f"- **Closing Dates**: {position_analysis['closing_orders'][0]['created_at'][:10]} to {position_analysis['closing_orders'][-1]['created_at'][:10]}\n")
                
                f.write(f"- **Net Result**: {position_analysis['net_position']:+.2f} contracts\n")
                
                if position_analysis['is_complete']:
                    f.write(f"- **Status**: ✅ Chain is complete - all positions closed\n")
                else:
                    f.write(f"- **Status**: 🔄 Chain is incomplete - {abs(position_analysis['net_position']):.2f} contracts still open\n")
                
                f.write("\n")
                
                # Leg details for first few orders
                f.write("#### Leg Details (First 3 Orders)\n\n")
                
                for j, order in enumerate(orders[:3]):
                    f.write(f"**Order {j+1}** ({order['created_at'][:10]}):\n")
                    
                    for leg in order['legs']:
                        effect = leg.get('position_effect', '')
                        side = leg.get('side', '')
                        option_type = leg.get('option_type', '')
                        strike = leg.get('strike_price', '')
                        expiry = leg.get('expiration_date', '')
                        
                        # Add visual indicators
                        effect_icon = "🟢" if effect == 'open' else "🔴"
                        f.write(f"- {effect_icon} Leg {leg['index']}: {side} {effect} {option_type} {strike} {expiry}\n")
                        
                        if leg.get('long_strategy_code'):
                            f.write(f"  - Long Strategy Code: {leg['long_strategy_code']}\n")
                        if leg.get('short_strategy_code'):
                            f.write(f"  - Short Strategy Code: {leg['short_strategy_code']}\n")
                    
                    f.write("\n")
                
                if len(orders) > 3:
                    f.write(f"*... and {len(orders) - 3} more orders*\n\n")
                
                f.write("---\n\n")
        
        print(f"✅ Markdown file generated: {output_file}")
        print(f"📊 Wrote {len(sorted_chains)} chains with detailed order information")
        
        # Show some statistics
        print(f"\n📈 CHAIN STATISTICS:")
        print(f"  - Chains with 2 orders: {sum(1 for orders in strategy_chains.values() if len(orders) == 2)}")
        print(f"  - Chains with 3+ orders: {sum(1 for orders in strategy_chains.values() if len(orders) >= 3)}")
        print(f"  - Chains with 10+ orders: {sum(1 for orders in strategy_chains.values() if len(orders) >= 10)}")
        
        return output_file
        
    except Exception as e:
        print(f"❌ Error processing file: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Main function"""
    print("🚀 DUMPING ALL DETECTED CHAINS TO MARKDOWN")
    print("=" * 80)
    
    output_file = dump_chains_to_markdown()
    
    if output_file:
        print(f"\n✅ Successfully generated markdown file: {output_file}")
        print(f"📁 File location: {Path.cwd() / output_file}")
        print(f"📖 Open the file to view all detected chains with order details")
        print(f"🔍 Enhanced with position flow analysis and closing order identification")
    else:
        print("❌ Failed to generate markdown file")

if __name__ == "__main__":
    main()
