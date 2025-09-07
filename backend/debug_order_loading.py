#!/usr/bin/env python3

import asyncio
import sys
import os
sys.path.append('/Users/abhishek/tradeanalytics-v2/backend')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+asyncpg://postgres:postgres@localhost:5432/tradeanalytics')

engine = create_async_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def debug_order_loading():
    """Debug why get_orders_for_chain_detection returns fewer orders than expected"""
    
    jwt_user_id = '123e4567-e89b-12d3-a456-426614174000'
    days_back = 90
    
    print('=== ORDER LOADING DEBUG ===')
    print(f'User ID: {jwt_user_id}')
    print(f'Days back: {days_back}')
    print()
    
    async with SessionLocal() as db:
        # 1. Test the exact query used by get_orders_for_chain_detection
        print('1. TESTING get_orders_for_chain_detection() QUERY:')
        
        since_time = datetime.now() - timedelta(days=days_back)
        print(f'   Since time: {since_time}')
        
        from app.models.options_order import OptionsOrder
        from sqlalchemy import and_
        
        conditions = [
            OptionsOrder.user_id == jwt_user_id,
            OptionsOrder.created_at >= since_time,
            OptionsOrder.state == "filled"
        ]
        conditions.append(OptionsOrder.chain_symbol == 'MSFT')
        
        stmt = select(OptionsOrder).where(
            and_(*conditions)
        ).order_by(OptionsOrder.created_at.asc())
        
        result = await db.execute(stmt)
        method_orders = result.scalars().all()
        
        print(f'   Method query returned: {len(method_orders)} orders')
        for i, order in enumerate(method_orders):
            date_str = str(order.created_at)[:10]
            marker = ' <--- SEPTEMBER 5TH' if date_str == '2025-09-05' else ''
            print(f'     {i+1:2d}. {date_str}: {order.position_effect:5s} ${order.strike_price:6.2f} - {order.direction:5s} ${order.processed_premium:7.2f}{marker}')
        
        print()
        
        # 2. Test broader query to see all MSFT orders
        print('2. TESTING BROADER QUERY (all MSFT orders):')
        
        result = await db.execute(text('''
            SELECT 
                order_id,
                created_at,
                position_effect,
                strike_price,
                direction,
                processed_premium,
                state,
                user_id
            FROM options_orders 
            WHERE user_id = :user_id 
            AND chain_symbol = 'MSFT'
            ORDER BY created_at ASC
        '''), {'user_id': jwt_user_id})
        
        all_orders = result.fetchall()
        print(f'   Broad query returned: {len(all_orders)} orders')
        
        # Count by state
        state_counts = {}
        for order in all_orders:
            state = order.state
            state_counts[state] = state_counts.get(state, 0) + 1
        
        print(f'   Orders by state: {state_counts}')
        
        # Show all orders
        for i, order in enumerate(all_orders):
            date_str = str(order.created_at)[:10]
            marker = ' <--- SEPTEMBER 5TH' if date_str == '2025-09-05' else ''
            state_marker = f' ({order.state})' if order.state != 'filled' else ''
            print(f'     {i+1:2d}. {date_str}: {order.position_effect:5s} ${order.strike_price:6.2f} - {order.direction:5s} ${order.processed_premium:7.2f}{state_marker}{marker}')
        
        print()
        
        # 3. Test date filtering impact
        print('3. TESTING DATE FILTERING:')
        
        result = await db.execute(text('''
            SELECT 
                DATE(created_at) as order_date,
                COUNT(*) as order_count
            FROM options_orders 
            WHERE user_id = :user_id 
            AND chain_symbol = 'MSFT'
            AND state = 'filled'
            GROUP BY DATE(created_at)
            ORDER BY order_date ASC
        '''), {'user_id': jwt_user_id})
        
        date_counts = result.fetchall()
        print(f'   Orders by date (filled only):')
        
        cutoff_orders = 0
        within_range_orders = 0
        
        for row in date_counts:
            date_str = str(row.order_date)
            count = row.order_count
            
            # Convert date back to datetime for comparison
            row_date = datetime.combine(row.order_date, datetime.min.time())
            if row_date.tzinfo is None:
                row_date = row_date.replace(tzinfo=since_time.tzinfo) if since_time.tzinfo else row_date
            
            if row_date >= since_time:
                within_range_orders += count
                marker = ' ✅ WITHIN RANGE'
            else:
                cutoff_orders += count
                marker = ' ❌ OUTSIDE RANGE (too old)'
            
            print(f'     {date_str}: {count} orders{marker}')
        
        print(f'   Total within {days_back} days: {within_range_orders}')
        print(f'   Total outside range: {cutoff_orders}')
        
        print()
        
        # 4. Test using the actual service method
        print('4. TESTING ACTUAL SERVICE METHOD:')
        try:
            from app.services.options_order_service import OptionsOrderService
            from app.services.robinhood_service import RobinhoodService
            
            rh_service = RobinhoodService()
            options_service = OptionsOrderService(rh_service)
            
            service_orders = await options_service.get_orders_for_chain_detection(
                user_id=jwt_user_id,
                days_back=days_back,
                symbol='MSFT'
            )
            
            print(f'   Service method returned: {len(service_orders)} orders')
            
            if len(service_orders) != len(method_orders):
                print(f'   ⚠️  DISCREPANCY: Service returned {len(service_orders)}, manual query returned {len(method_orders)}')
            else:
                print(f'   ✅ Service method matches manual query')
            
            # Show service method results
            for i, order in enumerate(service_orders):
                date_str = str(order.created_at)[:10]
                marker = ' <--- SEPTEMBER 5TH' if date_str == '2025-09-05' else ''
                print(f'     {i+1:2d}. {date_str}: {order.position_effect:5s} ${order.strike_price:6.2f} - {order.direction:5s} ${order.processed_premium:7.2f}{marker}')
            
        except Exception as e:
            print(f'   ❌ Error testing service method: {e}')
            import traceback
            traceback.print_exc()
        
        print()
        
        # 5. Check if September 5th order meets all criteria
        print('5. SEPTEMBER 5TH ORDER ANALYSIS:')
        
        result = await db.execute(text('''
            SELECT 
                order_id,
                created_at,
                state,
                chain_symbol,
                position_effect,
                strike_price,
                user_id
            FROM options_orders 
            WHERE order_id = '68baf90b-7b3a-4cff-a04d-bf3e9e8a24de'
        '''))
        
        sept_order = result.fetchone()
        if sept_order:
            print(f'   Order ID: {sept_order.order_id}')
            print(f'   Created: {sept_order.created_at}')
            print(f'   State: {sept_order.state}')
            print(f'   Chain Symbol: {sept_order.chain_symbol}')
            print(f'   User ID: {sept_order.user_id}')
            
            # Check each filter condition
            print(f'   Matches user filter: {"✅" if str(sept_order.user_id) == jwt_user_id else "❌"}')
            print(f'   Matches state filter: {"✅" if sept_order.state == "filled" else "❌"}')
            print(f'   Matches symbol filter: {"✅" if sept_order.chain_symbol == "MSFT" else "❌"}')
            print(f'   Matches date filter: {"✅" if sept_order.created_at >= since_time else "❌"}')
            
            if sept_order.created_at >= since_time:
                days_ago = (datetime.now(sept_order.created_at.tzinfo) - sept_order.created_at).days
                print(f'   Days ago: {days_ago} (cutoff: {days_back})')
            
        else:
            print(f'   ❌ September 5th order not found!')

if __name__ == "__main__":
    asyncio.run(debug_order_loading())