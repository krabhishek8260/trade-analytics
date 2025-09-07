#!/usr/bin/env python3

import asyncio
import sys
import os
sys.path.append('/Users/abhishek/tradeanalytics-v2/backend')

from app.services.robinhood_service import RobinhoodService
from app.services.options_order_service import OptionsOrderService
from app.services.rolled_options_chain_detector import RolledOptionsChainDetector

async def debug_symbol_issue():
    """Debug why underlying_symbol shows as UNKNOWN"""
    
    jwt_user_id = '123e4567-e89b-12d3-a456-426614174000'
    sept_5_order_id = '68baf90b-7b3a-4cff-a04d-bf3e9e8a24de'
    
    print('=== SYMBOL ISSUE DEBUG ===')
    print(f'User ID: {jwt_user_id}')
    print(f'September 5th Order: {sept_5_order_id}')
    print()
    
    try:
        # Initialize services
        rh_service = RobinhoodService()
        options_service = OptionsOrderService(rh_service)
        detector = RolledOptionsChainDetector(options_service)
        
        # Get database orders for MSFT
        db_orders = await options_service.get_orders_for_chain_detection(
            user_id=jwt_user_id,
            days_back=90,
            symbol='MSFT'
        )
        
        print(f'1. DATABASE ORDERS LOADED: {len(db_orders)}')
        
        # Check if September 5th order has chain_symbol
        sept_order = None
        for order in db_orders:
            if order.order_id == sept_5_order_id:
                sept_order = order
                print(f'   ✅ September 5th order found in database')
                print(f'     chain_symbol: "{order.chain_symbol}"')
                print(f'     order_id: {order.order_id}')
                print(f'     strike_price: {order.strike_price}')
                break
        
        if not sept_order:
            print(f'   ❌ September 5th order not found in database query')
            return
        
        print()
        
        # Convert to dict format
        order_dicts = [detector._convert_db_order_to_dict(order) for order in db_orders]
        
        print(f'2. CONVERTED ORDER DICTS: {len(order_dicts)}')
        
        # Find September 5th order in dict format
        sept_order_dict = None
        for order_dict in order_dicts:
            if order_dict.get('id') == sept_5_order_id:
                sept_order_dict = order_dict
                print(f'   ✅ September 5th order found in dict format')
                print(f'     chain_symbol: "{order_dict.get("chain_symbol")}"')
                print(f'     id: {order_dict.get("id")}')
                print(f'     strike_price: {order_dict.get("strike_price")}')
                break
        
        if not sept_order_dict:
            print(f'   ❌ September 5th order not found in dict format')
            return
        
        print()
        
        # Test strategy detection
        strategy_chains = detector._detect_chains_by_strategy_codes(order_dicts)
        
        print(f'3. STRATEGY CHAINS: {len(strategy_chains)}')
        
        # Find chain containing September 5th order
        sept_chain = None
        for strategy_code, chain_orders in strategy_chains.items():
            if strategy_code in ['a63ad35e-fc16-40a6-beaf-dd8f470b843d_L1', 'a63ad35e-fc16-40a6-beaf-dd8f470b843d_S1']:
                has_sept = any(o.get('id') == sept_5_order_id for o in chain_orders)
                if has_sept:
                    sept_chain = chain_orders
                    print(f'   ✅ Found chain with September 5th order: {strategy_code}')
                    print(f'     Chain has {len(chain_orders)} orders')
                    
                    # Check symbol in chain orders
                    for i, order in enumerate(chain_orders):
                        symbol = order.get('chain_symbol') or order.get('underlying_symbol')
                        print(f'     Order {i+1}: id={order.get("id", "N/A")[:8]}, chain_symbol="{order.get("chain_symbol")}", symbol="{symbol}"')
                    break
        
        if not sept_chain:
            print(f'   ❌ September 5th order not found in strategy chains')
            return
        
        print()
        
        # Test chain analysis
        print(f'4. CHAIN ANALYSIS:')
        analysis = detector.get_chain_analysis(sept_chain)
        
        print(f'   Chain analysis result:')
        print(f'     underlying_symbol: "{analysis.get("underlying_symbol")}"')
        print(f'     chain_id: {analysis.get("chain_id")}')
        print(f'     total_orders: {analysis.get("total_orders")}')
        
        if analysis.get("underlying_symbol") == "UNKNOWN":
            print(f'   ❌ Symbol is still UNKNOWN after analysis!')
            print(f'   First order keys: {list(sept_chain[0].keys())}')
            print(f'   First order chain_symbol: "{sept_chain[0].get("chain_symbol")}"')
        else:
            print(f'   ✅ Symbol correctly detected: "{analysis.get("underlying_symbol")}"')
        
    except Exception as e:
        print(f'❌ Error in symbol debug: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_symbol_issue())