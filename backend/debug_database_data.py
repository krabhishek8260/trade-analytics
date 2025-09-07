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

async def debug_database_data():
    """Check what's actually stored in the database for the September 5th order"""
    
    sept_5_order_id = '68baf90b-7b3a-4cff-a04d-bf3e9e8a24de'
    
    print('=== DATABASE DATA DEBUG ===')
    print(f'September 5th Order: {sept_5_order_id}')
    print()
    
    async with SessionLocal() as db:
        # Query the specific order from the database
        result = await db.execute(text('''
            SELECT 
                order_id,
                chain_symbol,
                strike_price,
                option_type,
                state,
                created_at,
                position_effect,
                processed_quantity,
                processed_premium,
                direction,
                legs_count,
                legs_details,
                strategy,
                raw_data
            FROM options_orders 
            WHERE order_id = :order_id
        '''), {'order_id': sept_5_order_id})
        
        order = result.fetchone()
        
        if not order:
            print(f'❌ Order not found in database!')
            return
        
        print('1. DATABASE RAW DATA:')
        print(f'   order_id: {order.order_id}')
        print(f'   chain_symbol: {order.chain_symbol}')
        print(f'   strike_price: {order.strike_price}')
        print(f'   option_type: {order.option_type}')
        print(f'   state: {order.state}')
        print(f'   position_effect: {order.position_effect}')
        print(f'   processed_quantity: {order.processed_quantity}')
        print(f'   processed_premium: {order.processed_premium}')
        print(f'   direction: {order.direction}')
        print(f'   legs_count: {order.legs_count}')
        print(f'   strategy: {order.strategy}')
        print()
        
        print('2. LEGS DETAILS:')
        if order.legs_details:
            for i, leg in enumerate(order.legs_details):
                print(f'   Leg {i+1}:')
                print(f'     side: {leg.get("side")}')
                print(f'     position_effect: {leg.get("position_effect")}')
                print(f'     quantity: {leg.get("quantity")}')
                print(f'     option_type: {leg.get("option_type")}')
                print(f'     strike_price: {leg.get("strike_price")}')
                print(f'     expiration_date: {leg.get("expiration_date")}')
                print(f'     long_strategy_code: {leg.get("long_strategy_code")}')
                print(f'     short_strategy_code: {leg.get("short_strategy_code")}')
        else:
            print('   No legs_details found')
        
        print()
        
        print('3. RAW_DATA ANALYSIS:')
        if order.raw_data:
            raw_data = order.raw_data
            print(f'   Raw data keys: {list(raw_data.keys())}')
            
            # Check key fields that might contain quantity info
            key_fields = ['processed_quantity', 'quantity', 'legs', 'premium', 'processed_premium']
            for field in key_fields:
                if field in raw_data:
                    print(f'   {field}: {raw_data[field]}')
            
            # Check legs in raw data
            if 'legs' in raw_data and raw_data['legs']:
                print(f'   Raw legs:')
                for i, leg in enumerate(raw_data['legs']):
                    print(f'     Leg {i+1}: {leg}')
        else:
            print('   No raw_data found')
        
        print()
        
        # Also check a comparison order (July 31st) to see the difference
        print('4. COMPARISON ORDER (July 31st):')
        result = await db.execute(text('''
            SELECT 
                order_id,
                processed_quantity,
                processed_premium,
                direction,
                legs_details
            FROM options_orders 
            WHERE order_id = '688b81ba-dc44-44c1-a1bf-6cf748398cc9'
        '''))
        
        july_order = result.fetchone()
        if july_order:
            print(f'   order_id: {july_order.order_id}')
            print(f'   processed_quantity: {july_order.processed_quantity}')
            print(f'   processed_premium: {july_order.processed_premium}')
            print(f'   direction: {july_order.direction}')
            
            if july_order.legs_details:
                for i, leg in enumerate(july_order.legs_details):
                    print(f'   Leg {i+1} quantity: {leg.get("quantity")}')
        else:
            print('   July 31st order not found')

if __name__ == "__main__":
    asyncio.run(debug_database_data())