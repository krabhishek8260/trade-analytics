#!/usr/bin/env python3

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
import json
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+asyncpg://postgres:postgres@localhost:5432/tradeanalytics')

engine = create_async_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def debug_msft_chain_detection():
    async with SessionLocal() as db:
        print('=== MSFT CHAIN DETECTION DEBUG ===')
        print()
        
        # 1. Get the September 5th closing order with full details
        result = await db.execute(text('''
            SELECT 
                order_id,
                chain_symbol,
                strike_price,
                expiration_date,
                option_type,
                state,
                created_at,
                position_effect,
                processed_premium,
                direction,
                legs_count,
                legs_details,
                raw_data
            FROM options_orders 
            WHERE chain_symbol = 'MSFT' 
            AND created_at >= '2025-09-01'
            ORDER BY created_at DESC
        '''))
        
        sept_order = result.fetchone()
        print('1. SEPTEMBER 5TH MSFT ORDER:')
        print(f'   Order ID: {sept_order.order_id}')
        print(f'   Date: {sept_order.created_at}')
        print(f'   Strike: ${sept_order.strike_price} {sept_order.option_type}')
        print(f'   Expiration: {sept_order.expiration_date}')
        print(f'   Position Effect: {sept_order.position_effect}')
        print(f'   State: {sept_order.state}')
        print(f'   Premium: ${sept_order.processed_premium} ({sept_order.direction})')
        print(f'   Legs Count: {sept_order.legs_count}')
        
        if sept_order.legs_details:
            print('   Legs Details:')
            legs = sept_order.legs_details if isinstance(sept_order.legs_details, list) else json.loads(sept_order.legs_details)
            for i, leg in enumerate(legs):
                print(f'     Leg {i}:')
                print(f'       Strategy codes: {leg.get("long_strategy_code")} / {leg.get("short_strategy_code")}')
                print(f'       Side: {leg.get("side")}')
                print(f'       Position effect: {leg.get("position_effect")}')
                print(f'       Strike/Type: ${leg.get("strike_price")} {leg.get("option_type")}')
        print()
        
        # 2. Get all MSFT orders for analysis
        result = await db.execute(text('''
            SELECT 
                order_id,
                created_at,
                strike_price,
                expiration_date,
                option_type,
                position_effect,
                processed_premium,
                direction,
                state,
                legs_details
            FROM options_orders 
            WHERE chain_symbol = 'MSFT'
            AND option_type = 'call'
            AND state = 'filled'
            ORDER BY created_at DESC
            LIMIT 25
        '''))
        
        all_orders = result.fetchall()
        print('2. ALL MSFT CALL ORDERS (last 25 filled):')
        for i, order in enumerate(all_orders):
            date_str = order.created_at.date().strftime('%Y-%m-%d')
            marker = ' <--- SEPTEMBER 5TH ORDER' if date_str == '2025-09-05' else ''
            print(f'   {i+1:2d}. {date_str}: ${order.strike_price:6.2f} {order.option_type} {order.position_effect:5s} - {order.direction:5s} ${order.processed_premium:7.2f}{marker}')
        print()
        
        # 3. Look for potential chain starts (opening orders)
        result = await db.execute(text('''
            SELECT 
                order_id,
                created_at,
                strike_price,
                expiration_date,
                position_effect,
                processed_premium,
                direction,
                legs_details
            FROM options_orders 
            WHERE chain_symbol = 'MSFT'
            AND option_type = 'call'
            AND position_effect = 'open'
            AND state = 'filled'
            ORDER BY created_at DESC
            LIMIT 15
        '''))
        
        opening_orders = result.fetchall()
        print('3. MSFT CALL OPENING ORDERS (last 15):')
        for i, order in enumerate(opening_orders):
            date_str = order.created_at.date().strftime('%Y-%m-%d')
            exp_str = str(order.expiration_date) if order.expiration_date else 'N/A'
            print(f'   {i+1:2d}. {date_str}: OPEN ${order.strike_price:6.2f} call exp {exp_str} - {order.direction} ${order.processed_premium}')
            
            # Check strategy codes in legs
            if order.legs_details:
                legs = order.legs_details if isinstance(order.legs_details, list) else json.loads(order.legs_details)
                for leg in legs:
                    long_code = leg.get('long_strategy_code', 'N/A')
                    short_code = leg.get('short_strategy_code', 'N/A')
                    print(f'        Strategy codes: {long_code} / {short_code}')
        print()
        
        # 4. Check what's in the current MSFT chains in the database
        result = await db.execute(text('''
            SELECT 
                chain_id,
                underlying_symbol,
                status,
                start_date,
                last_activity_date,
                total_orders,
                chain_data
            FROM rolled_options_chains 
            WHERE underlying_symbol = 'MSFT'
            AND user_id = '123e4567-e89b-12d3-a456-426614174000'
            ORDER BY last_activity_date DESC
        '''))
        
        chains = result.fetchall()
        print(f'4. CURRENT MSFT CHAINS IN DATABASE ({len(chains)}):')
        for i, chain in enumerate(chains):
            print(f'   Chain {i+1}: {chain.chain_id}')
            print(f'     Status: {chain.status}')
            print(f'     Start: {chain.start_date}')
            print(f'     Last Activity: {chain.last_activity_date}')
            print(f'     Total Orders: {chain.total_orders}')
            
            # Parse and display orders in the chain
            if chain.chain_data and 'orders' in chain.chain_data:
                orders = chain.chain_data['orders']
                print(f'     Orders in chain ({len(orders)}):')
                for j, order in enumerate(orders):
                    order_date = order.get('created_at', 'Unknown')[:10] if order.get('created_at') else 'Unknown'
                    strike = order.get('strike_price', 'Unknown')
                    effect = order.get('position_effect', 'Unknown')
                    premium = order.get('processed_premium', 0)
                    direction = order.get('direction', 'Unknown')
                    print(f'       {j+1}. {order_date}: {effect:5s} ${strike:6} - {direction} ${premium}')
                    
                    # Check if September 5th order is in this chain
                    if order_date == '2025-09-05':
                        print('         ^^^ FOUND SEPTEMBER 5TH ORDER IN THIS CHAIN!')
            print()
        
        # 5. Check strategy codes matching
        print('5. STRATEGY CODE ANALYSIS:')
        sept_order_strategy_codes = []
        if sept_order.legs_details:
            legs = sept_order.legs_details if isinstance(sept_order.legs_details, list) else json.loads(sept_order.legs_details)
            for leg in legs:
                long_code = leg.get('long_strategy_code')
                short_code = leg.get('short_strategy_code')
                sept_order_strategy_codes.extend([long_code, short_code])
        
        print(f'   September 5th order strategy codes: {sept_order_strategy_codes}')
        
        # Find orders with matching strategy codes
        result = await db.execute(text('''
            SELECT 
                order_id,
                created_at,
                strike_price,
                position_effect,
                legs_details
            FROM options_orders 
            WHERE chain_symbol = 'MSFT'
            AND option_type = 'call'
            AND state = 'filled'
            AND created_at < '2025-09-01'
            ORDER BY created_at DESC
            LIMIT 20
        '''))
        
        prev_orders = result.fetchall()
        print('   Checking previous orders for matching strategy codes:')
        
        for order in prev_orders:
            if order.legs_details:
                legs = order.legs_details if isinstance(order.legs_details, list) else json.loads(order.legs_details)
                for leg in legs:
                    long_code = leg.get('long_strategy_code')
                    short_code = leg.get('short_strategy_code')
                    
                    # Check if any strategy codes match
                    if any(code in sept_order_strategy_codes for code in [long_code, short_code] if code):
                        date_str = order.created_at.date().strftime('%Y-%m-%d')
                        print(f'     MATCH: {date_str}: ${order.strike_price} {order.position_effect} - codes: {long_code}/{short_code}')

if __name__ == "__main__":
    asyncio.run(debug_msft_chain_detection())