#!/usr/bin/env python3
"""
Test simple database insertion to identify the issue
"""

import sys
import logging
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the app directory to the path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from app.models.rolled_options_chain import RolledOptionsChain
    print("✅ Successfully imported RolledOptionsChain model")
except Exception as e:
    print(f"❌ Failed to import model: {e}")
    exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_simple_insert():
    """Test inserting a simple record"""
    
    # Connect to database
    engine = create_engine('postgresql://postgres:postgres@localhost:5432/tradeanalytics')
    Session = sessionmaker(bind=engine)
    
    try:
        with Session() as session:
            # Check if table exists
            logger.info("Checking if table exists...")
            result = session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_name = 'rolled_options_chains'"))
            table_exists = result.fetchone()
            
            if table_exists:
                logger.info("✅ Table 'rolled_options_chains' exists")
            else:
                logger.error("❌ Table 'rolled_options_chains' does not exist")
                return
            
            # Check table structure
            logger.info("Checking table structure...")
            result = session.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'rolled_options_chains' ORDER BY ordinal_position"))
            columns = result.fetchall()
            
            logger.info("Table columns:")
            for col_name, data_type in columns:
                logger.info(f"  {col_name}: {data_type}")
            
            # Try to insert a minimal record
            logger.info("Attempting to insert a minimal record...")
            
            test_record = RolledOptionsChain(
                user_id='123e4567-e89b-12d3-a456-426614174000',
                chain_id='test-chain-001',
                underlying_symbol='TEST',
                status='active',
                initial_strategy='test_strategy',
                start_date=datetime.now(),
                last_activity_date=datetime.now(),
                total_orders=1,
                roll_count=0,
                total_credits_collected=100.0,
                total_debits_paid=0.0,
                net_premium=100.0,
                total_pnl=100.0,
                chain_data={'orders': [], 'test': True}
            )
            
            session.add(test_record)
            session.commit()
            
            logger.info("✅ Successfully inserted test record")
            
            # Verify the record was inserted
            result = session.execute(text("SELECT COUNT(*) FROM rolled_options_chains"))
            count = result.fetchone()[0]
            logger.info(f"Database now contains {count} chains")
            
            # Clean up test record
            session.execute(text("DELETE FROM rolled_options_chains WHERE chain_id = 'test-chain-001'"))
            session.commit()
            logger.info("✅ Cleaned up test record")
            
    except Exception as e:
        logger.error(f"❌ Error during test: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    test_simple_insert()