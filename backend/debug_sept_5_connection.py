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

async def debug_september_5_connection():
    """Debug why September 5th order isn't connecting to the chain"""
    
    jwt_user_id = '123e4567-e89b-12d3-a456-426614174000'
    
    print('=== SEPTEMBER 5TH CHAIN CONNECTION DEBUG ===')
    print(f'User ID: {jwt_user_id}')
    print()
    
    async with SessionLocal() as db:
        # 1. Check all MSFT orders for this user
        print('1. ALL MSFT ORDERS FOR JWT USER:')
        result = await db.execute(text('''
            SELECT 
                order_id,
                created_at,
                position_effect,
                strike_price,
                expiration_date,
                direction,
                processed_premium,
                legs_details
            FROM options_orders 
            WHERE user_id = :user_id 
            AND chain_symbol = 'MSFT'
            AND state = 'filled'
            ORDER BY created_at ASC
        '''), {'user_id': jwt_user_id})
        
        orders = result.fetchall()
        print(f'   Found {len(orders)} MSFT orders:')
        
        sept_5_order = None
        july_31_order = None
        
        for i, order in enumerate(orders):
            date_str = str(order.created_at)[:10]
            marker = ''
            if date_str == '2025-09-05':
                marker = ' <--- SEPTEMBER 5TH'
                sept_5_order = order
            elif date_str == '2025-07-31' and order.strike_price == 510.0:
                marker = ' <--- JULY 31ST ($510 close that should connect)'
                july_31_order = order
            
            print(f'     {i+1:2d}. {date_str}: {order.position_effect:5s} ${order.strike_price:6.2f} - {order.direction:5s} ${order.processed_premium:7.2f}{marker}')
        
        print()
        
        # 2. Analyze strategy codes in September 5th and July 31st orders
        print('2. STRATEGY CODES ANALYSIS:')
        
        if sept_5_order:
            print(f'   September 5th Order ({sept_5_order.order_id}):')
            legs = sept_5_order.legs_details if sept_5_order.legs_details else []
            sept_5_codes = set()
            
            for leg in legs:
                long_code = leg.get('long_strategy_code')
                short_code = leg.get('short_strategy_code')
                if long_code:
                    sept_5_codes.add(long_code)
                if short_code:
                    sept_5_codes.add(short_code)
                print(f'     Leg: long={long_code}, short={short_code}')
            
            print(f'     Unique strategy codes: {list(sept_5_codes)}')
        else:
            print('   ❌ September 5th order not found!')
        
        print()
        
        if july_31_order:
            print(f'   July 31st Order ({july_31_order.order_id}):')
            legs = july_31_order.legs_details if july_31_order.legs_details else []
            july_31_codes = set()
            
            for leg in legs:
                long_code = leg.get('long_strategy_code')
                short_code = leg.get('short_strategy_code')
                if long_code:
                    july_31_codes.add(long_code)
                if short_code:
                    july_31_codes.add(short_code)
                print(f'     Leg: long={long_code}, short={short_code}')
            
            print(f'     Unique strategy codes: {list(july_31_codes)}')
        else:
            print('   ❌ July 31st order not found!')
        
        print()
        
        # 3. Check for strategy code overlap
        if sept_5_order and july_31_order:
            print('3. STRATEGY CODE MATCHING:')
            common_codes = sept_5_codes.intersection(july_31_codes)
            print(f'   Common strategy codes: {list(common_codes)}')
            
            if common_codes:
                print('   ✅ Strategy codes match - these orders SHOULD be in same chain')
            else:
                print('   ❌ No matching strategy codes - this explains why they\'re not connected')
        
        print()
        
        # 4. Check what the current chains look like
        print('4. CURRENT MSFT CHAINS IN DATABASE:')
        result = await db.execute(text('''
            SELECT 
                chain_id,
                status,
                start_date,
                last_activity_date,
                total_orders,
                chain_data
            FROM rolled_options_chains 
            WHERE underlying_symbol = 'MSFT'
            AND user_id = :user_id
            ORDER BY last_activity_date DESC
        '''), {'user_id': jwt_user_id})
        
        chains = result.fetchall()
        print(f'   Found {len(chains)} MSFT chains:')
        
        for i, chain in enumerate(chains):
            print(f'   Chain {i+1}: {chain.chain_id}')
            print(f'     Status: {chain.status}')
            print(f'     Start: {chain.start_date}')
            print(f'     Last Activity: {chain.last_activity_date}')
            print(f'     Total Orders: {chain.total_orders}')
            
            # Check if this chain contains September 5th or July 31st orders
            chain_data = chain.chain_data or {}
            orders_in_chain = chain_data.get('orders', [])
            
            has_sept_5 = False
            has_july_31 = False
            
            for order in orders_in_chain:
                order_date = order.get('created_at', '')[:10]
                if order_date == '2025-09-05':
                    has_sept_5 = True
                elif order_date == '2025-07-31':
                    has_july_31 = True
            
            print(f'     Contains Sept 5th order: {"✅" if has_sept_5 else "❌"}')
            print(f'     Contains July 31st order: {"✅" if has_july_31 else "❌"}')
            
            if has_july_31 and not has_sept_5:
                print(f'     🎯 This is likely the chain missing September 5th order!')
                
                # Show all orders in this chain
                print(f'     Orders in this chain:')
                for j, order in enumerate(orders_in_chain):
                    order_date = order.get('created_at', '')[:10]
                    strike = order.get('strike_price', 0)
                    effect = order.get('position_effect', 'N/A')
                    premium = order.get('processed_premium', 0)
                    print(f'       {j+1}. {order_date}: {effect:5s} ${strike:6.2f} - ${premium:7.2f}')
            
            print()
        
        # 5. Test the chain detection algorithm directly
        print('5. TESTING CHAIN DETECTION ALGORITHM:')
        try:
            from app.services.rolled_options_chain_detector import RolledOptionsChainDetector
            from app.services.options_order_service import OptionsOrderService
            from app.services.robinhood_service import RobinhoodService
            
            rh_service = RobinhoodService()
            options_service = OptionsOrderService(rh_service)
            detector = RolledOptionsChainDetector(options_service)
            
            # Get orders in chain detection format
            db_orders = await options_service.get_orders_for_chain_detection(
                user_id=jwt_user_id,
                days_back=90,
                symbol='MSFT'
            )
            
            print(f'   Chain detector found {len(db_orders)} MSFT orders')
            
            # Convert to dict format for chain detection
            order_dicts = []
            for order in db_orders:
                order_dict = {
                    'id': order.order_id,
                    'created_at': order.created_at.isoformat() if order.created_at else None,
                    'direction': order.direction,
                    'processed_premium': float(order.processed_premium or 0),
                    'chain_symbol': order.chain_symbol,
                    'strike_price': float(order.strike_price or 0),
                    'option_type': order.option_type,
                    'position_effect': order.position_effect,
                    'legs': order.legs_details if order.legs_details else [],
                }
                order_dicts.append(order_dict)
            
            # Test strategy code grouping
            strategy_chains = detector._detect_chains_by_strategy_codes(order_dicts)
            print(f'   Strategy code detection found {len(strategy_chains)} chains')
            
            for code, chain_orders in strategy_chains.items():
                if len(chain_orders) >= 2:  # Only show chains with multiple orders
                    has_sept = any(o.get('created_at', '')[:10] == '2025-09-05' for o in chain_orders)
                    has_july = any(o.get('created_at', '')[:10] == '2025-07-31' for o in chain_orders)
                    
                    if has_july or has_sept:
                        print(f'     Strategy {code}: {len(chain_orders)} orders')
                        print(f'       Contains Sept 5th: {"✅" if has_sept else "❌"}')
                        print(f'       Contains July 31st: {"✅" if has_july else "❌"}')
                        
                        if has_july and has_sept:
                            print(f'       🎉 FOUND MATCHING CHAIN! Both orders should be connected.')
                        elif has_july and not has_sept:
                            print(f'       🤔 July 31st is in this chain but September 5th is not')
                        elif has_sept and not has_july:
                            print(f'       🤔 September 5th is in this chain but July 31st is not')
            
        except Exception as e:
            print(f'   ❌ Error testing chain detection: {e}')
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_september_5_connection())