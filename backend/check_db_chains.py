#!/usr/bin/env python3
"""
Check database contents to verify enhanced chains are stored
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from app.models.rolled_options_chain import RolledOptionsChain

async def check_database():
    engine = create_async_engine('postgresql+asyncpg://postgres:postgres@localhost:5432/tradeanalytics')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        result = await session.execute(select(RolledOptionsChain))
        chains = result.scalars().all()
        print(f'Database contains {len(chains)} chains')
        
        if chains:
            for i, chain in enumerate(chains[:5]):
                print(f'Chain {i+1}: {chain.underlying_symbol} - {chain.chain_id} - {chain.total_orders} orders')
                orders = chain.chain_data.get('orders', [])
                if orders:
                    first_order = orders[0]
                    legs = first_order.get('legs', [])
                    if len(legs) == 1 and legs[0].get('position_effect') == 'open':
                        print(f'  ✅ Starts with opening order: ${legs[0].get("strike_price")} {legs[0].get("option_type")} {legs[0].get("expiration_date")}')
                    else:
                        print(f'  Roll-based chain')

if __name__ == "__main__":
    asyncio.run(check_database())