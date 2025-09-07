#!/usr/bin/env python3
"""
Extract and dump NVDA orders with strategy code c23aa70d-f0c0-4c5f-bfad-52e9905e75b4_L1
to analyze the chain pattern.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

def dump_nvda_chain():
    """Dump NVDA orders with specific strategy code to analyze chain pattern"""
    debug_data_dir = Path(__file__).parent / "debug_data"
    options_files = list(debug_data_dir.glob("*options_orders*.json"))
    
    target_strategy_code = "c23aa70d-f0c0-4c5f-bfad-52e9905e75b4_L1"
    matching_orders = []
    
    print(f"Searching for NVDA orders with strategy code: {target_strategy_code}")
    print("=" * 80)
    
    # Process recent files
    for file_path in sorted(options_files, reverse=True)[:5]:
        try:
            with open(file_path, 'r') as f:
                orders = json.load(f)
            
            for order in orders:
                if order.get('state') != 'filled':
                    continue
                
                chain_symbol = order.get('chain_symbol', '')
                if chain_symbol.upper() != 'NVDA':
                    continue
                
                # Check if any leg has the target strategy code
                legs = order.get('legs', [])
                has_target_code = False
                
                for leg in legs:
                    long_code = leg.get('long_strategy_code', '')
                    short_code = leg.get('short_strategy_code', '')
                    
                    if long_code == target_strategy_code or short_code == target_strategy_code:
                        has_target_code = True
                        break
                
                if has_target_code:
                    matching_orders.append(order)
                    
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    # Deduplicate orders by order ID (same orders appear in multiple debug files)
    seen_order_ids = set()
    unique_orders = []
    for order in matching_orders:
        order_id = order.get('id', '')
        if order_id not in seen_order_ids:
            seen_order_ids.add(order_id)
            unique_orders.append(order)
    
    matching_orders = unique_orders
    
    # Sort by created_at chronologically
    matching_orders.sort(key=lambda x: x.get('created_at', ''))
    
    print(f"Found {len(matching_orders)} NVDA orders with strategy code {target_strategy_code}")
    print("=" * 80)
    
    # Dump detailed order information
    for i, order in enumerate(matching_orders):
        print(f"\n🔸 ORDER {i+1}/{len(matching_orders)}")
        print(f"Order ID: {order.get('id', 'N/A')}")
        print(f"Created: {order.get('created_at', 'N/A')}")
        print(f"Updated: {order.get('updated_at', 'N/A')}")
        print(f"State: {order.get('state', 'N/A')}")
        print(f"Direction: {order.get('direction', 'N/A')}")
        print(f"Strategy: {order.get('strategy', 'N/A')}")
        print(f"Opening Strategy: {order.get('opening_strategy', 'N/A')}")
        print(f"Closing Strategy: {order.get('closing_strategy', 'N/A')}")
        print(f"Form Source: {order.get('form_source', 'N/A')}")
        print(f"Processed Premium: ${order.get('processed_premium', 'N/A')}")
        print(f"Processed Quantity: {order.get('processed_quantity', 'N/A')}")
        print(f"Chain Symbol: {order.get('chain_symbol', 'N/A')}")
        
        legs = order.get('legs', [])
        print(f"Legs Count: {len(legs)}")
        
        for j, leg in enumerate(legs):
            print(f"  LEG {j+1}:")
            print(f"    Strike: ${leg.get('strike_price', 'N/A')}")
            print(f"    Option Type: {leg.get('option_type', 'N/A')}")
            print(f"    Expiration: {leg.get('expiration_date', 'N/A')}")
            print(f"    Side: {leg.get('side', 'N/A')}")
            print(f"    Position Effect: {leg.get('position_effect', 'N/A')}")
            print(f"    Long Strategy Code: {leg.get('long_strategy_code', 'N/A')}")
            print(f"    Short Strategy Code: {leg.get('short_strategy_code', 'N/A')}")
            
            # Show executions if available
            executions = leg.get('executions', [])
            if executions:
                print(f"    Executions: {len(executions)}")
                for k, execution in enumerate(executions[:2]):  # Show first 2 executions
                    print(f"      Execution {k+1}: ${execution.get('price', 'N/A')} x {execution.get('quantity', 'N/A')} at {execution.get('timestamp', 'N/A')}")
        
        print("-" * 60)
    
    # Analysis summary
    print(f"\n📊 CHAIN ANALYSIS SUMMARY")
    print("=" * 80)
    
    if matching_orders:
        first_order = matching_orders[0]
        last_order = matching_orders[-1]
        
        print(f"Chain Span: {first_order.get('created_at', 'N/A')} to {last_order.get('created_at', 'N/A')}")
        
        # Option details
        first_leg = first_order.get('legs', [{}])[0] if first_order.get('legs') else {}
        print(f"\nOption Details:")
        print(f"  Symbol: {first_order.get('chain_symbol', 'N/A')}")
        print(f"  Strike Price: ${first_leg.get('strike_price', 'N/A')}")
        print(f"  Expiration Date: {first_leg.get('expiration_date', 'N/A')}")
        print(f"  Open Date: {first_order.get('created_at', 'N/A')[:10] if first_order.get('created_at') else 'N/A'}")
        
        # Quantity analysis
        total_buy_quantity = sum(float(order.get('processed_quantity', 0)) for order in matching_orders 
                               if any(leg.get('side') == 'buy' for leg in order.get('legs', [])))
        total_sell_quantity = sum(float(order.get('processed_quantity', 0)) for order in matching_orders 
                                if any(leg.get('side') == 'sell' for leg in order.get('legs', [])))
        net_position = total_buy_quantity - total_sell_quantity
        total_volume = total_buy_quantity + total_sell_quantity
        
        print(f"\nQuantity Analysis:")
        print(f"  Total Contracts Bought: {total_buy_quantity:,.0f}")
        print(f"  Total Contracts Sold: {total_sell_quantity:,.0f}")
        print(f"  Net Position: {net_position:,.0f}")
        print(f"  Total Volume: {total_volume:,.0f}")
        print(f"  Total Orders: {len(matching_orders)}")
        
        # Duration calculation
        from datetime import datetime
        try:
            start_date = datetime.fromisoformat(first_order.get('created_at', '').replace('Z', '+00:00'))
            end_date = datetime.fromisoformat(last_order.get('created_at', '').replace('Z', '+00:00'))
            duration_days = (end_date - start_date).days
            print(f"  Chain Duration: {duration_days} days")
        except:
            print(f"  Chain Duration: N/A")
        
        # Position effects summary
        position_effects = []
        for order in matching_orders:
            legs = order.get('legs', [])
            order_effects = []
            for leg in legs:
                effect = f"{leg.get('position_effect', 'N/A')} {leg.get('side', 'N/A')}"
                order_effects.append(effect)
            position_effects.append(' + '.join(order_effects))
        
        print("Position Effect Sequence:")
        for i, effects in enumerate(position_effects):
            print(f"  Order {i+1}: {effects}")
        
        # Financial summary
        total_credits = sum(float(order.get('processed_premium', 0)) for order in matching_orders if order.get('direction') == 'credit')
        total_debits = sum(float(order.get('processed_premium', 0)) for order in matching_orders if order.get('direction') == 'debit')
        net_premium = total_credits - total_debits
        
        print(f"\nFinancial Summary:")
        print(f"  Total Credits: ${total_credits:,.2f}")
        print(f"  Total Debits: ${total_debits:,.2f}")
        print(f"  Net Premium: ${net_premium:,.2f}")
        
        # Strategy progression
        strategies = [order.get('strategy', 'N/A') for order in matching_orders]
        opening_strategies = [order.get('opening_strategy', 'N/A') for order in matching_orders if order.get('opening_strategy')]
        closing_strategies = [order.get('closing_strategy', 'N/A') for order in matching_orders if order.get('closing_strategy')]
        
        print(f"\nStrategy Progression:")
        print(f"  Strategies: {' -> '.join(strategies)}")
        if opening_strategies:
            print(f"  Opening Strategies: {' -> '.join(opening_strategies)}")
        if closing_strategies:
            print(f"  Closing Strategies: {' -> '.join(closing_strategies)}")
        
        # Chain type determination
        has_opens = any(leg.get('position_effect') == 'open' for order in matching_orders for leg in order.get('legs', []))
        has_closes = any(leg.get('position_effect') == 'close' for order in matching_orders for leg in order.get('legs', []))
        
        print(f"\nChain Characteristics:")
        print(f"  Has Opens: {has_opens}")
        print(f"  Has Closes: {has_closes}")
        print(f"  Potential Chain: {'Yes' if has_opens and has_closes and len(matching_orders) >= 2 else 'Maybe'}")
        
    else:
        print("No matching orders found.")

if __name__ == "__main__":
    dump_nvda_chain()