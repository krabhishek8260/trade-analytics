#!/usr/bin/env python3

import asyncio
import sys
import os
sys.path.append('/Users/abhishek/tradeanalytics-v2/backend')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
from dotenv import load_dotenv
import json

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+asyncpg://postgres:postgres@localhost:5432/tradeanalytics')

engine = create_async_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def debug_chain_creation():
    """Debug what happened to the September 5th order during chain creation"""
    
    jwt_user_id = '123e4567-e89b-12d3-a456-426614174000'
    sept_5_order_id = '68baf90b-7b3a-4cff-a04d-bf3e9e8a24de'
    
    print('=== CHAIN CREATION DEBUG ===')
    print(f'User ID: {jwt_user_id}')
    print(f'September 5th Order: {sept_5_order_id}')
    print()
    
    async with SessionLocal() as db:
        # 1. Check if September 5th order exists in any stored chains
        print('1. SEARCHING FOR SEPTEMBER 5TH ORDER IN STORED CHAINS:')
        
        result = await db.execute(text('''
            SELECT 
                chain_id,
                underlying_symbol,
                total_orders,
                chain_data
            FROM rolled_options_chains 
            WHERE user_id = :user_id
        '''), {'user_id': jwt_user_id})
        
        all_chains = result.fetchall()
        found_in_chains = []
        
        print(f'   Checking {len(all_chains)} stored chains for order {sept_5_order_id[:8]}...')
        
        for chain in all_chains:
            chain_data = chain.chain_data or {}
            orders_in_chain = chain_data.get('orders', [])
            
            for order in orders_in_chain:
                if order.get('id') == sept_5_order_id:
                    found_in_chains.append(chain.chain_id)
                    print(f'   ✅ FOUND in chain {chain.chain_id} ({chain.underlying_symbol})')
                    
        if not found_in_chains:
            print(f'   ❌ September 5th order NOT FOUND in any stored chain')
            print()
            
            # 2. Check which chains have the matching strategy code
            print('2. CHECKING CHAINS WITH MATCHING STRATEGY CODES:')
            target_strategy_codes = [
                'a63ad35e-fc16-40a6-beaf-dd8f470b843d_L1',
                'a63ad35e-fc16-40a6-beaf-dd8f470b843d_S1'
            ]
            
            matching_strategy_chains = []
            
            for chain in all_chains:
                chain_data = chain.chain_data or {}
                orders_in_chain = chain_data.get('orders', [])
                
                # Check if any order in this chain has the matching strategy codes
                has_matching_strategy = False
                
                for order in orders_in_chain:
                    legs = order.get('legs', [])
                    for leg in legs:
                        long_code = leg.get('long_strategy_code')
                        short_code = leg.get('short_strategy_code')
                        
                        if long_code in target_strategy_codes or short_code in target_strategy_codes:
                            has_matching_strategy = True
                            break
                    
                    if has_matching_strategy:
                        break
                
                if has_matching_strategy:
                    matching_strategy_chains.append((chain.chain_id, chain.underlying_symbol, len(orders_in_chain)))
                    print(f'   Chain {chain.chain_id}: {chain.underlying_symbol} - {len(orders_in_chain)} orders')
                    
                    # Show orders in this matching chain
                    for i, order in enumerate(orders_in_chain):
                        order_date = order.get('created_at', '')[:10]
                        order_id = order.get('id', 'N/A')[:8]
                        marker = ' <--- JULY 31ST' if order_date == '2025-07-31' else ''
                        print(f'     {i+1}. {order_date}: {order_id}...{marker}')
            
            print(f'   Found {len(matching_strategy_chains)} chains with matching strategy codes')
            print()
            
            # 3. Test the detection algorithm directly
            print('3. TESTING CHAIN DETECTION WITH SPECIFIC ORDER:')
            
            try:
                from app.services.rolled_options_chain_detector import RolledOptionsChainDetector
                from app.services.options_order_service import OptionsOrderService
                from app.services.robinhood_service import RobinhoodService
                
                rh_service = RobinhoodService()
                options_service = OptionsOrderService(rh_service)
                detector = RolledOptionsChainDetector(options_service)
                
                # Get just MSFT orders for testing
                db_orders = await options_service.get_orders_for_chain_detection(
                    user_id=jwt_user_id,
                    days_back=90,
                    symbol='MSFT'
                )
                
                print(f'   Detector loaded {len(db_orders)} MSFT orders')
                
                # Convert to dict format
                order_dicts = [detector._convert_db_order_to_dict(order) for order in db_orders]
                print(f'   Converted to {len(order_dicts)} order dicts')
                
                # Check if September 5th order is in the converted data
                sept_5_found = False
                for order_dict in order_dicts:
                    if order_dict.get('id') == sept_5_order_id:
                        sept_5_found = True
                        print(f'   ✅ September 5th order found in converted data')
                        print(f'     Date: {order_dict.get("created_at")}')
                        print(f'     Premium: {order_dict.get("processed_premium")}')
                        print(f'     Legs: {len(order_dict.get("legs", []))}')
                        
                        # Check strategy codes
                        legs = order_dict.get('legs', [])
                        for i, leg in enumerate(legs):
                            long_code = leg.get('long_strategy_code')
                            short_code = leg.get('short_strategy_code')
                            print(f'       Leg {i+1}: long={long_code}, short={short_code}')
                        break
                
                if not sept_5_found:
                    print(f'   ❌ September 5th order NOT found in converted data')
                
                # Test strategy code detection
                strategy_chains = detector._detect_chains_by_strategy_codes(order_dicts)
                print(f'   Strategy detection found {len(strategy_chains)} chains')
                
                sept_5_in_strategies = []
                for strategy_code, chain_orders in strategy_chains.items():
                    if strategy_code in target_strategy_codes:
                        has_sept = any(o.get('id') == sept_5_order_id for o in chain_orders)
                        has_july = any(o.get('created_at', '')[:10] == '2025-07-31' for o in chain_orders)
                        
                        print(f'   Strategy {strategy_code}: {len(chain_orders)} orders')
                        print(f'     Contains Sept 5th: {"✅" if has_sept else "❌"}')
                        print(f'     Contains July 31st: {"✅" if has_july else "❌"}')
                        
                        if has_sept:
                            sept_5_in_strategies.append(strategy_code)
                        
                        # Show all orders in this strategy
                        for order in chain_orders:
                            order_date = order.get('created_at', '')[:10]
                            order_id = order.get('id', 'N/A')[:8]
                            marker = ''
                            if order_date == '2025-09-05':
                                marker = ' <--- SEPTEMBER 5TH'
                            elif order_date == '2025-07-31':
                                marker = ' <--- JULY 31ST'
                            
                            print(f'       {order_date}: {order_id}...{marker}')
                
                print(f'   September 5th found in {len(sept_5_in_strategies)} strategies: {sept_5_in_strategies}')
                
            except Exception as e:
                print(f'   ❌ Error testing detection algorithm: {e}')
                import traceback
                traceback.print_exc()
            
        else:
            print(f'   ✅ September 5th order found in {len(found_in_chains)} chains: {found_in_chains}')

if __name__ == "__main__":
    asyncio.run(debug_chain_creation())