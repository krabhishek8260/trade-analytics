#!/usr/bin/env python3
"""
Test different database connection strings to find the correct one
"""

import asyncio
import psycopg2
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_sync_connections():
    """Test synchronous connections with different parameters"""
    
    connection_strings = [
        # Main postgres container (port 5432)
        'postgresql://postgres:postgres@localhost:5432/tradeanalytics',
        'postgresql+psycopg2://postgres:postgres@localhost:5432/tradeanalytics', 
        
        # Supabase postgres container (port 54322)
        'postgresql://postgres:postgres@localhost:54322/postgres',
        'postgresql+psycopg2://postgres:postgres@localhost:54322/postgres',
        
        # Try with different database names
        'postgresql://postgres:postgres@localhost:5432/postgres',
        'postgresql+psycopg2://postgres:postgres@localhost:5432/postgres',
    ]
    
    for conn_str in connection_strings:
        try:
            logger.info(f"Testing sync: {conn_str}")
            engine = create_engine(conn_str)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                version = result.fetchone()[0]
                logger.info(f"✅ SUCCESS: {conn_str}")
                logger.info(f"   Version: {version[:50]}...")
                
                # Test if rolled_options_chains table exists
                try:
                    result = conn.execute(text("SELECT COUNT(*) FROM rolled_options_chains"))
                    count = result.fetchone()[0]
                    logger.info(f"   rolled_options_chains table: {count} records")
                except Exception as e:
                    logger.info(f"   rolled_options_chains table: not found ({e})")
                
        except Exception as e:
            logger.error(f"❌ FAILED: {conn_str} - {e}")
        
        print("-" * 60)

async def test_async_connections():
    """Test async connections with different parameters"""
    
    connection_strings = [
        # Main postgres container (port 5432) 
        'postgresql+asyncpg://postgres:postgres@localhost:5432/tradeanalytics',
        'postgresql+psycopg://postgres:postgres@localhost:5432/tradeanalytics',
        
        # Supabase postgres container (port 54322)
        'postgresql+asyncpg://postgres:postgres@localhost:54322/postgres',
        'postgresql+psycopg://postgres:postgres@localhost:54322/postgres',
        
        # Try with different database names
        'postgresql+asyncpg://postgres:postgres@localhost:5432/postgres',
        'postgresql+psycopg://postgres:postgres@localhost:5432/postgres',
    ]
    
    for conn_str in connection_strings:
        try:
            logger.info(f"Testing async: {conn_str}")
            engine = create_async_engine(conn_str, pool_timeout=5)
            
            async with engine.begin() as conn:
                result = await conn.execute(text("SELECT version()"))
                version = result.fetchone()[0]
                logger.info(f"✅ SUCCESS: {conn_str}")
                logger.info(f"   Version: {version[:50]}...")
                
                # Test if rolled_options_chains table exists
                try:
                    result = await conn.execute(text("SELECT COUNT(*) FROM rolled_options_chains"))
                    count = result.fetchone()[0]
                    logger.info(f"   rolled_options_chains table: {count} records")
                except Exception as e:
                    logger.info(f"   rolled_options_chains table: not found ({e})")
            
            await engine.dispose()
            
        except Exception as e:
            logger.error(f"❌ FAILED: {conn_str} - {e}")
        
        print("-" * 60)

if __name__ == "__main__":
    print("=" * 60)
    print("TESTING SYNCHRONOUS CONNECTIONS")
    print("=" * 60)
    test_sync_connections()
    
    print("=" * 60)
    print("TESTING ASYNCHRONOUS CONNECTIONS")
    print("=" * 60)
    asyncio.run(test_async_connections())