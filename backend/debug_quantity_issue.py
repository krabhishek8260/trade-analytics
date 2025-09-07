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

async def debug_quantity_issue():
    """Check how widespread the quantity issue is across orders"""
    
    jwt_user_id = '123e4567-e89b-12d3-a456-426614174000'
    
    print('=== QUANTITY ISSUE DEBUG ===')
    print(f'User ID: {jwt_user_id}')
    print()
    
    async with SessionLocal() as db:
        # Check MSFT orders to see processed_quantity vs raw_data quantity
        result = await db.execute(text('''
            SELECT 
                order_id,
                processed_quantity,
                processed_premium,
                direction,
                raw_data
            FROM options_orders 
            WHERE user_id = :user_id
            AND chain_symbol = 'MSFT'
            AND state = 'filled'
            ORDER BY created_at DESC
            LIMIT 10
        '''), {'user_id': jwt_user_id})
        
        orders = result.fetchall()
        
        print(f'1. MSFT ORDERS QUANTITY ANALYSIS ({len(orders)} orders):')
        print(f'   {"Order ID":<10} {"DB Qty":<8} {"Raw Qty":<8} {"Premium":<10} {"Direction":<8} {"Issue"}')
        print(f'   {"-"*60}')
        
        issues_found = 0
        
        for order in orders:
            order_id_short = order.order_id[:8]
            db_qty = float(order.processed_quantity or 0)
            raw_qty = float(order.raw_data.get('processed_quantity', 0)) if order.raw_data else 0
            premium = float(order.processed_premium or 0)
            direction = order.direction or 'N/A'
            
            # Check if there's a mismatch
            issue = ""
            if db_qty != raw_qty:
                issues_found += 1
                issue = "MISMATCH"
            elif db_qty == 0:
                issue = "ZERO_QTY"
            
            print(f'   {order_id_short:<10} {db_qty:<8.1f} {raw_qty:<8.1f} ${premium:<9.0f} {direction:<8} {issue}')
        
        print(f'   {"-"*60}')
        print(f'   Issues found: {issues_found} orders with quantity mismatches')
        print()
        
        # Check if this is a systemic issue across all symbols
        print('2. SYSTEMIC QUANTITY ISSUE CHECK:')
        result = await db.execute(text('''
            SELECT 
                COUNT(*) as total_orders,
                COUNT(CASE WHEN processed_quantity = 0 OR processed_quantity IS NULL THEN 1 END) as zero_quantity_orders,
                COUNT(CASE WHEN raw_data->>'processed_quantity' != processed_quantity::text THEN 1 END) as mismatched_orders
            FROM options_orders 
            WHERE user_id = :user_id
            AND state = 'filled'
            AND raw_data IS NOT NULL
        '''), {'user_id': jwt_user_id})
        
        stats = result.fetchone()
        if stats:
            total = stats.total_orders
            zero = stats.zero_quantity_orders
            mismatched = stats.mismatched_orders
            
            print(f'   Total filled orders: {total}')
            print(f'   Orders with zero quantity: {zero} ({zero/total*100:.1f}%)')
            print(f'   Orders with mismatched quantity: {mismatched} ({mismatched/total*100:.1f}%)')
        
        print()
        
        # Show a few examples of correct raw data
        print('3. RAW DATA QUANTITY EXAMPLES:')
        result = await db.execute(text('''
            SELECT 
                order_id,
                raw_data->>'processed_quantity' as raw_quantity,
                raw_data->>'premium' as raw_premium,
                processed_quantity as db_quantity,
                processed_premium as db_premium
            FROM options_orders 
            WHERE user_id = :user_id
            AND chain_symbol = 'MSFT'
            AND state = 'filled'
            ORDER BY created_at DESC
            LIMIT 5
        '''), {'user_id': jwt_user_id})
        
        examples = result.fetchall()
        for example in examples:
            order_id_short = example.order_id[:8]
            raw_qty = example.raw_quantity
            raw_prem = example.raw_premium
            db_qty = example.db_quantity
            db_prem = example.db_premium
            
            print(f'   {order_id_short}: Raw({raw_qty} @ ${raw_prem}) -> DB({db_qty} @ ${db_prem})')

if __name__ == "__main__":
    asyncio.run(debug_quantity_issue())