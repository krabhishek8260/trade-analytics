#!/usr/bin/env python3

import asyncio
import sys
import os
sys.path.append('/Users/abhishek/tradeanalytics-v2/backend')

from app.services.rolled_options_chain_detector import RolledOptionsChainDetector
from app.services.options_order_service import OptionsOrderService
from app.services.robinhood_service import RobinhoodService

async def debug_strategy_code_detection():
    """Debug the specific strategy code detection for MSFT orders"""
    
    jwt_user_id = '123e4567-e89b-12d3-a456-426614174000'
    
    print('=== STRATEGY CODE DETECTION DEBUG ===')
    print(f'User ID: {jwt_user_id}')
    print()
    
    try:
        # Initialize services
        rh_service = RobinhoodService()
        options_service = OptionsOrderService(rh_service)
        detector = RolledOptionsChainDetector(options_service)
        
        # Get MSFT orders
        db_orders = await options_service.get_orders_for_chain_detection(
            user_id=jwt_user_id,
            days_back=90,
            symbol='MSFT'
        )
        
        print(f'1. LOADED {len(db_orders)} MSFT ORDERS:')
        for i, order in enumerate(db_orders):
            date_str = str(order.created_at)[:10]
            marker = ' <--- SEPTEMBER 5TH' if date_str == '2025-09-05' else ''
            marker += ' <--- JULY 31ST' if date_str == '2025-07-31' else ''
            print(f'   {i+1:2d}. {date_str}: {order.position_effect:5s} ${order.strike_price:6.2f} - {order.direction:5s} ${order.processed_premium:7.2f}{marker}')
        
        print()
        
        # Convert to dict format for chain detection
        order_dicts = [detector._convert_db_order_to_dict(order) for order in db_orders]
        
        print(f'2. CONVERTED TO {len(order_dicts)} DICT ORDERS:')
        for i, order_dict in enumerate(order_dicts):
            date_str = order_dict.get('created_at', '')[:10]
            marker = ' <--- SEPTEMBER 5TH' if date_str == '2025-09-05' else ''
            marker += ' <--- JULY 31ST' if date_str == '2025-07-31' else ''
            
            position_effect = order_dict.get("position_effect") or "N/A"
            strike_price = order_dict.get("strike_price") or 0
            direction = order_dict.get("direction") or "N/A"
            processed_premium = order_dict.get("processed_premium") or 0
            
            print(f'   {i+1:2d}. {date_str}: {position_effect:5s} ${strike_price:6.2f} - {direction:5s} ${processed_premium:7.2f}{marker}')
        
        print()
        
        # Test strategy code detection
        print('3. STRATEGY CODE DETECTION:')
        strategy_chains = detector._detect_chains_by_strategy_codes(order_dicts)
        
        print(f'   Found {len(strategy_chains)} strategy code groups:')
        
        for i, (strategy_code, chain_orders) in enumerate(strategy_chains.items()):
            print(f'   Strategy Code {i+1}: {strategy_code}')
            print(f'   Orders: {len(chain_orders)}')
            
            # Check if this strategy contains both September 5th and July 31st
            has_sept = False
            has_july = False
            
            for order in chain_orders:
                order_date = order.get('created_at', '')[:10]
                if order_date == '2025-09-05':
                    has_sept = True
                elif order_date == '2025-07-31':
                    has_july = True
            
            print(f'   Contains Sept 5th: {"✅" if has_sept else "❌"}')
            print(f'   Contains July 31st: {"✅" if has_july else "❌"}')
            
            if has_sept and has_july:
                print('   🎯 THIS STRATEGY SHOULD CREATE A CHAIN!')
            elif len(chain_orders) >= 2:
                print('   ✅ Has 2+ orders - will be processed')
            else:
                print('   ❌ Only 1 order - will be FILTERED OUT by >= 2 condition')
            
            # Show all orders in this strategy group
            for j, order in enumerate(chain_orders):
                order_date = order.get('created_at', '')[:10]
                position_effect = order.get('position_effect', 'N/A')
                strike = order.get('strike_price', 0)
                premium = order.get('processed_premium', 0)
                order_id = order.get('id', 'N/A')[:8]
                
                sept_marker = ' <--- SEPTEMBER 5TH' if order_date == '2025-09-05' else ''
                july_marker = ' <--- JULY 31ST' if order_date == '2025-07-31' else ''
                marker = sept_marker + july_marker
                
                print(f'     {j+1}. {order_date}: {position_effect:5s} ${strike:6.2f} - ${premium:7.2f} ({order_id}...){marker}')
            
            print()
        
        # Test the full detection process to see what chains get created
        print('4. FULL CHAIN DETECTION PROCESS:')
        
        all_chains = []
        
        # Process strategy code chains with the same logic as the actual detector
        for strategy_code, chain_orders in strategy_chains.items():
            if len(chain_orders) >= 2:  # This is the critical filter!
                chain_data = detector._format_chain_result(
                    chain_orders, 
                    detection_method="strategy_code",
                    strategy_code=strategy_code
                )
                all_chains.append(chain_data)
                print(f'   ✅ Created chain for strategy {strategy_code}: {len(chain_orders)} orders')
            else:
                print(f'   ❌ FILTERED OUT strategy {strategy_code}: only {len(chain_orders)} orders (need 2+)')
        
        print()
        print(f'5. FINAL RESULT: {len(all_chains)} chains will be stored in database')
        
        # Show which orders are included in final chains
        included_order_ids = set()
        for chain in all_chains:
            orders = chain.get('orders', [])
            for order in orders:
                included_order_ids.add(order.get('id'))
        
        # Check if September 5th order is included
        sept_order_id = '68baf90b-7b3a-4cff-a04d-bf3e9e8a24de'
        if sept_order_id in included_order_ids:
            print('   ✅ September 5th order WILL be included in final chains')
        else:
            print('   ❌ September 5th order will NOT be included in final chains')
            print(f'      This explains why you only see 3 orders instead of 4!')
        
    except Exception as e:
        print(f'❌ Error in strategy code detection debug: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_strategy_code_detection())