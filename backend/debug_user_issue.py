#!/usr/bin/env python3
"""
Debug script to investigate user foreign key violation issue
"""

import asyncio
import uuid
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.options_pnl_cache import UserOptionsPnLCache, OptionsPnLProcessingLog

async def debug_user_issue():
    """Debug the user foreign key violation issue"""
    
    async with AsyncSessionLocal() as db:
        print("=== Database Debug Information ===")
        
        # Check what users exist in the database
        print("\n1. Checking existing users:")
        stmt = select(User)
        result = await db.execute(stmt)
        users = result.scalars().all()
        
        if users:
            for user in users:
                print(f"  - User ID: {user.id}")
                print(f"    Email: {user.email}")
                print(f"    Robinhood Username: {user.robinhood_username}")
                print(f"    Active: {user.is_active}")
                print()
        else:
            print("  No users found in database")
        
        # Check the specific user IDs from the error
        error_user_ids = [
            "28e01f67-7141-4978-b9f8-9e9973591aed",
            "55ace719-edf5-44c5-bc51-fa244e008153"
        ]
        
        print("\n2. Checking specific error user IDs:")
        for user_id_str in error_user_ids:
            try:
                user_id = uuid.UUID(user_id_str)
                stmt = select(User).where(User.id == user_id)
                result = await db.execute(stmt)
                user = result.scalar_one_or_none()
                
                if user:
                    print(f"  ✓ User {user_id_str} EXISTS")
                    print(f"    Email: {user.email}")
                    print(f"    Robinhood Username: {user.robinhood_username}")
                else:
                    print(f"  ✗ User {user_id_str} DOES NOT EXIST")
            except Exception as e:
                print(f"  ✗ Error checking user {user_id_str}: {e}")
        
        # Check demo user
        demo_user_id = "00000000-0000-0000-0000-000000000001"
        print(f"\n3. Checking demo user ({demo_user_id}):")
        try:
            demo_uuid = uuid.UUID(demo_user_id)
            stmt = select(User).where(User.id == demo_uuid)
            result = await db.execute(stmt)
            demo_user = result.scalar_one_or_none()
            
            if demo_user:
                print(f"  ✓ Demo user EXISTS")
                print(f"    Email: {demo_user.email}")
                print(f"    Robinhood Username: {demo_user.robinhood_username}")
            else:
                print(f"  ✗ Demo user DOES NOT EXIST")
        except Exception as e:
            print(f"  ✗ Error checking demo user: {e}")
        
        # Check P&L cache entries
        print("\n4. Checking P&L cache entries:")
        stmt = select(UserOptionsPnLCache)
        result = await db.execute(stmt)
        cache_entries = result.scalars().all()
        
        if cache_entries:
            for entry in cache_entries:
                print(f"  - Cache for user: {entry.user_id}")
                print(f"    Status: {entry.calculation_status}")
                print(f"    Last calculated: {entry.last_calculated_at}")
        else:
            print("  No P&L cache entries found")
        
        # Check P&L processing logs
        print("\n5. Checking P&L processing logs:")
        stmt = select(OptionsPnLProcessingLog)
        result = await db.execute(stmt)
        log_entries = result.scalars().all()
        
        if log_entries:
            for entry in log_entries:
                print(f"  - Log for user: {entry.user_id}")
                print(f"    Status: {entry.status}")
                print(f"    Started: {entry.started_at}")
                print(f"    Completed: {entry.completed_at}")
        else:
            print("  No P&L processing logs found")

if __name__ == "__main__":
    asyncio.run(debug_user_issue()) 