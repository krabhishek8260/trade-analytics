#!/usr/bin/env python3
"""
Script to drop and recreate options_orders and options_positions tables with new structure
"""

import asyncio
import logging
from app.core.database import AsyncSessionLocal, Base, engine
from sqlalchemy import text
from app.models.options_order import OptionsOrder
from app.models.options_position import OptionsPosition

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_migration():
    """Drop and recreate options tables with new structure"""
    
    async with AsyncSessionLocal() as db:
        try:
            logger.info("Starting options models migration: Drop and recreate tables")
            
            # Drop existing tables (this will also drop indexes and constraints)
            logger.info("Dropping existing options_orders table...")
            await db.execute(text("DROP TABLE IF EXISTS options_orders CASCADE"))
            
            logger.info("Dropping existing options_positions table...")
            await db.execute(text("DROP TABLE IF EXISTS options_positions CASCADE"))
            
            await db.commit()
            logger.info("Existing tables dropped successfully")
            
        except Exception as e:
            logger.error(f"Failed to drop tables: {str(e)}")
            await db.rollback()
            raise

    # Create new tables with updated models
    try:
        logger.info("Creating new tables with updated structure...")
        
        # Create tables using SQLAlchemy metadata
        async with engine.begin() as conn:
            # Only create the specific tables we updated
            await conn.run_sync(lambda sync_conn: Base.metadata.create_all(
                sync_conn, 
                tables=[OptionsOrder.__table__, OptionsPosition.__table__],
                checkfirst=True
            ))
        
        logger.info("New tables created successfully!")
        logger.info("Migration completed!")
        
    except Exception as e:
        logger.error(f"Failed to create new tables: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(run_migration())