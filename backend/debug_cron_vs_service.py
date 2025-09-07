#!/usr/bin/env python3

import asyncio
import sys
import os
sys.path.append('/Users/abhishek/tradeanalytics-v2/backend')

from app.services.rolled_options_cron_service import RolledOptionsCronService
from app.services.options_order_service import OptionsOrderService
from app.services.robinhood_service import RobinhoodService
from app.services.rolled_options_chain_detector import RolledOptionsChainDetector

async def debug_cron_vs_service():
    """Debug the difference between cron service and options service data loading"""
    
    jwt_user_id = '123e4567-e89b-12d3-a456-426614174000'
    sept_5_order_id = '68baf90b-7b3a-4cff-a04d-bf3e9e8a24de'
    days_back = 90
    
    print('=== CRON SERVICE VS OPTIONS SERVICE DEBUG ===')
    print(f'User ID: {jwt_user_id}')
    print(f'Days back: {days_back}')
    print()
    
    try:
        # Initialize services
        rh_service = RobinhoodService()
        options_service = OptionsOrderService(rh_service)
        cron_service = RolledOptionsCronService()  # No args needed
        detector = RolledOptionsChainDetector(options_service)
        
        # 1. Load data using options service (working method)
        print('1. OPTIONS SERVICE DATA LOADING:')
        service_orders = await options_service.get_orders_for_chain_detection(
            user_id=jwt_user_id,
            days_back=days_back,
            symbol='MSFT'
        )
        
        print(f'   Service loaded {len(service_orders)} orders')
        
        service_sept_5_found = False
        for order in service_orders:
            if order.order_id == sept_5_order_id:
                service_sept_5_found = True
                print(f'   ✅ September 5th order found via service')
                print(f'     Strategy codes: long={order.long_strategy_code}, short={order.short_strategy_code}')
                print(f'     Legs: {len(order.legs_details or [])}')
                if order.legs_details:
                    for i, leg in enumerate(order.legs_details):
                        print(f'       Leg {i+1}: long={leg.get("long_strategy_code")}, short={leg.get("short_strategy_code")}')
                break
        
        if not service_sept_5_found:
            print(f'   ❌ September 5th order NOT found via service')
        
        print()
        
        # 2. Load data using cron service method (potentially broken)
        print('2. CRON SERVICE DATA LOADING:')
        cron_orders = await cron_service._load_orders_from_database(jwt_user_id, days_back)
        
        print(f'   Cron service loaded {len(cron_orders)} orders')
        
        cron_sept_5_found = False
        for order_dict in cron_orders:
            if order_dict.get('id') == sept_5_order_id:
                cron_sept_5_found = True
                print(f'   ✅ September 5th order found via cron service')
                print(f'     Premium: {order_dict.get("processed_premium")}')
                print(f'     Legs: {len(order_dict.get("legs", []))}')
                
                legs = order_dict.get('legs', [])
                for i, leg in enumerate(legs):
                    print(f'       Leg {i+1}: long={leg.get("long_strategy_code")}, short={leg.get("short_strategy_code")}')
                break
        
        if not cron_sept_5_found:
            print(f'   ❌ September 5th order NOT found via cron service')
        
        print()
        
        # 3. Convert service orders to dict format and test strategy detection
        print('3. SERVICE DATA CONVERTED TO DICT FORMAT:')
        service_dicts = [detector._convert_db_order_to_dict(order) for order in service_orders]
        
        service_dict_sept_5_found = False
        for order_dict in service_dicts:
            if order_dict.get('id') == sept_5_order_id:
                service_dict_sept_5_found = True
                print(f'   ✅ September 5th order found in converted service data')
                
                legs = order_dict.get('legs', [])
                for i, leg in enumerate(legs):
                    print(f'       Leg {i+1}: long={leg.get("long_strategy_code")}, short={leg.get("short_strategy_code")}')
                break
        
        if not service_dict_sept_5_found:
            print(f'   ❌ September 5th order NOT found in converted service data')
        
        print()
        
        # 4. Test strategy detection with both datasets
        print('4. STRATEGY DETECTION COMPARISON:')
        
        # Service data strategy detection
        service_strategy_chains = detector._detect_chains_by_strategy_codes(service_dicts)
        service_sept_5_strategies = []
        
        for strategy_code, chain_orders in service_strategy_chains.items():
            if strategy_code in ['a63ad35e-fc16-40a6-beaf-dd8f470b843d_L1', 'a63ad35e-fc16-40a6-beaf-dd8f470b843d_S1']:
                has_sept = any(o.get('id') == sept_5_order_id for o in chain_orders)
                if has_sept:
                    service_sept_5_strategies.append(strategy_code)
        
        print(f'   Service data: September 5th found in {len(service_sept_5_strategies)} strategies: {service_sept_5_strategies}')
        
        # Cron data strategy detection
        cron_strategy_chains = detector._detect_chains_by_strategy_codes(cron_orders)
        cron_sept_5_strategies = []
        
        for strategy_code, chain_orders in cron_strategy_chains.items():
            if strategy_code in ['a63ad35e-fc16-40a6-beaf-dd8f470b843d_L1', 'a63ad35e-fc16-40a6-beaf-dd8f470b843d_S1']:
                has_sept = any(o.get('id') == sept_5_order_id for o in chain_orders)
                if has_sept:
                    cron_sept_5_strategies.append(strategy_code)
        
        print(f'   Cron data: September 5th found in {len(cron_sept_5_strategies)} strategies: {cron_sept_5_strategies}')
        
        # 5. Compare the total number of strategies found
        print()
        print('5. STRATEGY DETECTION SUMMARY:')
        print(f'   Service data found {len(service_strategy_chains)} strategy chains')
        print(f'   Cron data found {len(cron_strategy_chains)} strategy chains')
        
        if len(service_sept_5_strategies) > 0 and len(cron_sept_5_strategies) == 0:
            print(f'   🎯 ROOT CAUSE: Cron service data loading is missing September 5th order!')
        elif len(service_sept_5_strategies) == 0 and len(cron_sept_5_strategies) == 0:
            print(f'   🤔 Both methods missing September 5th order - conversion issue?')
        else:
            print(f'   ✅ Both methods find September 5th order correctly')
        
    except Exception as e:
        print(f'❌ Error in comparison debug: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_cron_vs_service())