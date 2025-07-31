#!/usr/bin/env python3
"""
Debug user chains and sync status
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from app.models.rolled_options_chain import RolledOptionsChain, UserRolledOptionsSync

async def debug_user_chains():
    engine = create_async_engine('postgresql+asyncpg://postgres:postgres@localhost:5432/tradeanalytics')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Check all chains in database
        result = await session.execute(select(RolledOptionsChain))
        all_chains = result.scalars().all()
        print(f'Total chains in database: {len(all_chains)}')
        
        if all_chains:
            for chain in all_chains[:3]:
                print(f'  Chain: {chain.user_id} - {chain.underlying_symbol} - {chain.chain_id}')
        
        # Check sync status table
        result = await session.execute(select(UserRolledOptionsSync))
        sync_records = result.scalars().all()
        print(f'Sync records: {len(sync_records)}')
        
        for sync in sync_records:
            print(f'  Sync: {sync.user_id} - {sync.processing_status} - {sync.last_successful_sync}')
        
        # Check the specific user ID that the API uses
        api_user_id = '123e4567-e89b-12d3-a456-426614174000'
        result = await session.execute(
            select(RolledOptionsChain).where(RolledOptionsChain.user_id == api_user_id)
        )
        api_chains = result.scalars().all()
        print(f'Chains for API user {api_user_id}: {len(api_chains)}')

if __name__ == "__main__":
    asyncio.run(debug_user_chains())