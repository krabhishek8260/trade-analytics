#!/usr/bin/env python3
"""
Script to run the robinhood_user_id migration manually
"""

import asyncio
import logging
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_migration():
    """Run the robinhood_user_id migration"""
    
    async with AsyncSessionLocal() as db:
        try:
            logger.info("Starting migration: Add robinhood_user_id column to users table")
            
            # Check if column already exists
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'robinhood_user_id'
            """)
            
            result = await db.execute(check_query)
            column_exists = result.scalar() is not None
            
            if column_exists:
                logger.info("Column robinhood_user_id already exists, skipping migration")
                return
            
            # Add the column
            add_column_query = text("""
                ALTER TABLE users ADD COLUMN robinhood_user_id VARCHAR(255)
            """)
            
            await db.execute(add_column_query)
            
            # Create index
            create_index_query = text("""
                CREATE INDEX idx_users_robinhood_user_id ON users(robinhood_user_id)
            """)
            
            await db.execute(create_index_query)
            
            # Add comment
            add_comment_query = text("""
                COMMENT ON COLUMN users.robinhood_user_id IS 'Stores the actual Robinhood API user ID for consistent user identification'
            """)
            
            await db.execute(add_comment_query)
            
            await db.commit()
            
            logger.info("Migration completed successfully!")
            
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            await db.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(run_migration()) 