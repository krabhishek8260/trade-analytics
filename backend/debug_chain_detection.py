#!/usr/bin/env python3

import asyncio
import sys
import os
sys.path.append('/Users/abhishek/tradeanalytics-v2/backend')

from app.services.rolled_options_chain_detector import RolledOptionsChainDetector
from app.services.options_order_service import OptionsOrderService
from app.core.database import get_db
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+asyncpg://postgres:postgres@localhost:5432/tradeanalytics')

engine = create_async_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def debug_chain_detection():
    async with SessionLocal() as db:
        print('=== CHAIN DETECTION DEBUG ===')
        print()
        
        # Create the detector and service
        from app.services.robinhood_service import RobinhoodService
        rh_service = RobinhoodService()
        options_service = OptionsOrderService(rh_service)
        detector = RolledOptionsChainDetector(options_service)
        
        user_id = '123e4567-e89b-12d3-a456-426614174000'
        
        # Get raw orders from database first
        print('1. RAW ORDERS FROM DATABASE:')
        
        # Test with broader query first to see what's available
        print('   Testing broad query (all MSFT orders):')
        from sqlalchemy import select, and_
        from app.models.options_order import OptionsOrder
        from datetime import datetime, timedelta
        
        since_time = datetime.now() - timedelta(days=90)
        stmt = select(OptionsOrder).where(
            and_(
                OptionsOrder.chain_symbol == 'MSFT',
                OptionsOrder.state == 'filled'
            )
        ).order_by(OptionsOrder.created_at.asc())
        
        result = await db.execute(stmt)
        all_msft_orders = result.scalars().all()
        
        print(f'   Found {len(all_msft_orders)} total filled MSFT orders:')
        for i, order in enumerate(all_msft_orders):
            date_str = str(order.created_at)[:10]
            position_effect = order.position_effect or 'N/A'
            marker = ' <--- SEPTEMBER 5TH' if date_str == '2025-09-05' else ''
            print(f'     {i+1:2d}. {date_str}: {position_effect:5s} ${order.strike_price:6.2f} {order.option_type} - {order.direction} ${order.processed_premium:7.2f} (ID: {order.order_id}) (User: {order.user_id}){marker}')
        
        print()
        print('   Testing with date filter (90 days):')
        stmt_filtered = select(OptionsOrder).where(
            and_(
                OptionsOrder.user_id == user_id,
                OptionsOrder.chain_symbol == 'MSFT',
                OptionsOrder.state == 'filled',
                OptionsOrder.created_at >= since_time
            )
        ).order_by(OptionsOrder.created_at.asc())
        
        result_filtered = await db.execute(stmt_filtered)
        filtered_orders = result_filtered.scalars().all()
        
        print(f'   Found {len(filtered_orders)} filtered MSFT orders (within 90 days):')
        for i, order in enumerate(filtered_orders):
            date_str = str(order.created_at)[:10]
            position_effect = order.position_effect or 'N/A'
            marker = ' <--- SEPTEMBER 5TH' if date_str == '2025-09-05' else ''
            print(f'     {i+1:2d}. {date_str}: {position_effect:5s} ${order.strike_price:6.2f} {order.option_type} - {order.direction} ${order.processed_premium:7.2f} (ID: {order.order_id}){marker}')
        
        print()
        print('   Using service method:')
        orders = await options_service.get_orders_for_chain_detection(
            user_id=user_id,
            days_back=90,
            symbol='MSFT'
        )
        
        print(f'   Found {len(orders)} MSFT orders:')
        for i, order in enumerate(orders):
            date_str = str(order.created_at)[:10]
            position_effect = order.position_effect or 'N/A'
            marker = ' <--- SEPTEMBER 5TH' if date_str == '2025-09-05' else ''
            print(f'     {i+1:2d}. {date_str}: {position_effect:5s} ${order.strike_price:6.2f} {order.option_type} - {order.direction} ${order.processed_premium:7.2f} (ID: {order.order_id}){marker}')
        
        print()
        
        # Convert to chain detection format
        print('2. CONVERTING TO CHAIN DETECTION FORMAT:')
        order_dicts = []
        for order in orders:
            # Convert database order to the format expected by chain detector
            order_dict = {
                'id': order.order_id,
                'order_id': order.order_id,
                'created_at': order.created_at.isoformat() if order.created_at else None,
                'direction': order.direction,
                'processed_premium': float(order.processed_premium or 0),
                'chain_symbol': order.chain_symbol,
                'strike_price': float(order.strike_price or 0),
                'option_type': order.option_type,
                'position_effect': order.position_effect,
                'state': order.state,
                'legs': order.legs_details if order.legs_details else [],
                'long_strategy_code': getattr(order, 'long_strategy_code', None),
                'short_strategy_code': getattr(order, 'short_strategy_code', None),
            }
            order_dicts.append(order_dict)
        
        # Check strategy codes in each order
        print('3. STRATEGY CODES IN ORDERS:')
        for i, order_dict in enumerate(order_dicts):
            date_str = order_dict.get('created_at', '')[:10]
            order_id = order_dict.get('order_id')
            
            # Get strategy codes from order and legs
            strategy_codes = set()
            if order_dict.get("long_strategy_code"):
                strategy_codes.add(order_dict["long_strategy_code"])
            if order_dict.get("short_strategy_code"):
                strategy_codes.add(order_dict["short_strategy_code"])
            
            # From legs
            for leg in order_dict.get("legs", []):
                if leg.get("long_strategy_code"):
                    strategy_codes.add(leg["long_strategy_code"])
                if leg.get("short_strategy_code"):
                    strategy_codes.add(leg["short_strategy_code"])
            
            marker = ' <--- SEPTEMBER 5TH' if date_str == '2025-09-05' else ''
            print(f'     {i+1:2d}. {date_str}: {order_id[:8]}... - Strategy codes: {list(strategy_codes)}{marker}')
        
        print()
        
        # Now test the chain detection
        print('4. RUNNING STRATEGY CODE CHAIN DETECTION:')
        strategy_chains = detector._detect_chains_by_strategy_codes(order_dicts)
        
        print(f'   Found {len(strategy_chains)} strategy code groups:')
        for code, chain_orders in strategy_chains.items():
            print(f'     Strategy Code: {code}')
            print(f'     Orders in chain: {len(chain_orders)}')
            for j, order in enumerate(chain_orders):
                date_str = order.get('created_at', '')[:10]
                position_effect = order.get('position_effect', 'N/A')
                order_id = order.get('order_id', 'N/A')[:8]
                marker = ' <--- SEPTEMBER 5TH' if date_str == '2025-09-05' else ''
                print(f'       {j+1}. {date_str}: {position_effect:5s} ${order.get("strike_price", 0):6.2f} - {order_id}...{marker}')
            print()
        
        # Test full chain detection
        print('5. RUNNING FULL CHAIN DETECTION:')
        chains = await detector.detect_chains_from_database(
            user_id=user_id,
            days_back=90,
            symbol='MSFT'
        )
        
        print(f'   Final chains detected: {len(chains)}')
        for i, chain in enumerate(chains):
            print(f'     Chain {i+1}: {chain.get("chain_id")}')
            print(f'       Detection method: {chain.get("detection_method")}')
            print(f'       Total orders: {chain.get("total_orders")}')
            print(f'       Status: {chain.get("status")}')
            chain_orders = chain.get("orders", [])
            for j, order in enumerate(chain_orders):
                date_str = order.get('created_at', '')[:10]
                position_effect = order.get('position_effect', 'N/A')
                order_id = order.get('order_id', 'N/A')[:8]
                marker = ' <--- SEPTEMBER 5TH' if date_str == '2025-09-05' else ''
                print(f'         {j+1}. {date_str}: {position_effect:5s} ${order.get("strike_price", 0):6.2f} - {order_id}...{marker}')
            print()

if __name__ == "__main__":
    asyncio.run(debug_chain_detection())