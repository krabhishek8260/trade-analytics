#!/usr/bin/env python3
"""
Test database connection
"""

import psycopg2
from sqlalchemy import create_engine, text

def test_sync_connection():
    """Test synchronous PostgreSQL connection"""
    try:
        # Test with psycopg2 directly
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="tradeanalytics",
            user="postgres",
            password="postgres"
        )
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✅ Direct psycopg2 connection successful: {version[0]}")
        cursor.close()
        conn.close()
        
        # Test with SQLAlchemy synchronous engine
        engine = create_engine('postgresql://postgres:postgres@localhost:5432/tradeanalytics')
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM rolled_options_chains"))
            count = result.fetchone()[0]
            print(f"✅ SQLAlchemy sync connection successful: {count} chains in database")
            
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    test_sync_connection()