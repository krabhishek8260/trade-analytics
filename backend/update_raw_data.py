#!/usr/bin/env python3
"""
Script to update the database with complete raw data from Robinhood API files
This will add the missing form_source field to existing orders
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add the app directory to Python path
sys.path.append(str(Path(__file__).parent))

from app.core.database import get_db
from app.models.options_order import OptionsOrder
from app.models.user import User  # Import User model to resolve relationship
from sqlalchemy import select, update


async def load_raw_orders_from_files() -> Dict[str, Dict[str, Any]]:
    """Load all raw orders from JSON files, indexed by order_id"""
    raw_orders = {}
    debug_data_dir = Path(__file__).parent / "debug_data"
    
    # Process all options_orders JSON files
    options_files = list(debug_data_dir.glob("*options_orders*.json"))
    print(f"Found {len(options_files)} options orders files")
    
    for file_path in options_files:
        try:
            with open(file_path, 'r') as f:
                orders = json.load(f)
                
            for order in orders:
                order_id = order.get("id")
                if order_id:
                    # Store the complete raw order data
                    raw_orders[order_id] = order
                    
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            continue
    
    print(f"Loaded {len(raw_orders)} raw orders from files")
    return raw_orders


async def update_database_with_raw_data():
    """Update existing database records with complete raw data"""
    print("Loading raw orders from JSON files...")
    raw_orders = await load_raw_orders_from_files()
    
    if not raw_orders:
        print("No raw orders found. Exiting.")
        return
    
    print("Connecting to database...")
    async for db in get_db():
        # Get all existing orders
        stmt = select(OptionsOrder.order_id, OptionsOrder.id)
        result = await db.execute(stmt)
        db_orders = result.fetchall()
        
        print(f"Found {len(db_orders)} orders in database")
        
        # Update orders with complete raw data
        updated_count = 0
        for db_order_id, db_id in db_orders:
            if db_order_id in raw_orders:
                raw_data = raw_orders[db_order_id]
                
                # Update the raw_data field with complete data
                update_stmt = update(OptionsOrder).where(
                    OptionsOrder.id == db_id
                ).values(raw_data=raw_data)
                
                await db.execute(update_stmt)
                updated_count += 1
                
                if updated_count % 100 == 0:
                    print(f"Updated {updated_count} orders...")
                    await db.commit()
        
        # Final commit
        await db.commit()
        print(f"Successfully updated {updated_count} orders with complete raw data")
        
        # Verify some orders have form_source now
        stmt = select(OptionsOrder.raw_data).limit(5)
        result = await db.execute(stmt)
        sample_orders = result.fetchall()
        
        form_source_count = 0
        strategy_roll_count = 0
        for (raw_data,) in sample_orders:
            if raw_data and isinstance(raw_data, dict):
                if "form_source" in raw_data:
                    form_source_count += 1
                    if raw_data.get("form_source") == "strategy_roll":
                        strategy_roll_count += 1
        
        print(f"Verification: {form_source_count}/5 sample orders have form_source")
        print(f"Verification: {strategy_roll_count}/5 sample orders have strategy_roll")


async def main():
    """Main function"""
    print("=== Database Update Script ===")
    print("This script will update existing orders with complete raw data from JSON files")
    
    response = input("Do you want to proceed? (y/N): ").strip().lower()
    if response != 'y':
        print("Operation cancelled.")
        return
    
    try:
        await update_database_with_raw_data()
        print("Database update completed successfully!")
    except Exception as e:
        print(f"Error updating database: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())