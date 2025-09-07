#!/usr/bin/env python3

import asyncio
import sys
import os
sys.path.append('/Users/abhishek/tradeanalytics-v2/backend')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+asyncpg://postgres:postgres@localhost:5432/tradeanalytics')

engine = create_async_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def migrate_user_ids_fixed():
    """Migrate all orders from old user ID to JWT user ID with proper constraint handling"""
    
    old_user_id = '13461768-f848-4c04-aea2-46817bc9a3a5'  # Development fallback user
    new_user_id = '123e4567-e89b-12d3-a456-426614174000'  # JWT authenticated user
    
    print('=== USER ID MIGRATION (FIXED) ===')
    print(f'Migrating from: {old_user_id}')
    print(f'Migrating to:   {new_user_id}')
    print()
    
    async with SessionLocal() as db:
        try:
            # 1. Check current state
            print('1. CURRENT STATE:')
            result = await db.execute(text('''
                SELECT user_id, COUNT(*) as order_count
                FROM options_orders 
                GROUP BY user_id 
                ORDER BY order_count DESC
            '''))
            
            current_state = result.fetchall()
            total_old_orders = 0
            total_new_orders = 0
            
            for row in current_state:
                user_id = row.user_id
                count = row.order_count
                marker = ''
                if str(user_id) == old_user_id:
                    marker = ' <-- OLD USER ID'
                    total_old_orders = count
                elif str(user_id) == new_user_id:
                    marker = ' <-- JWT USER ID'
                    total_new_orders = count
                    
                print(f'   {user_id}: {count} orders{marker}')
            
            if total_old_orders == 0:
                print('   ℹ️  No orders found for old user - already migrated?')
                return
            
            print()
            
            # 2. Show MSFT orders specifically
            print('2. MSFT ORDERS BY USER:')
            result = await db.execute(text('''
                SELECT user_id, COUNT(*) as msft_orders
                FROM options_orders 
                WHERE chain_symbol = 'MSFT'
                GROUP BY user_id 
                ORDER BY msft_orders DESC
            '''))
            
            msft_state = result.fetchall()
            for row in msft_state:
                user_id = row.user_id
                count = row.msft_orders
                marker = ' <-- OLD USER ID' if str(user_id) == old_user_id else ' <-- JWT USER ID' if str(user_id) == new_user_id else ''
                print(f'   {user_id}: {count} MSFT orders{marker}')
            
            print()
            
            # 3. Create new user if it doesn't exist
            print('3. ENSURING TARGET USER EXISTS:')
            from app.models.user import User
            from sqlalchemy.dialects.postgresql import insert
            
            user_record = {
                "id": new_user_id,
                "full_name": "Authenticated User",
                "email": f"user-{new_user_id}@tradeanalytics.local",
                "is_active": True,
                "robinhood_username": f"rh_user_{new_user_id[:8]}"
            }
            
            insert_user_stmt = insert(User).values(user_record)
            upsert_user_stmt = insert_user_stmt.on_conflict_do_nothing(index_elements=["id"])
            await db.execute(upsert_user_stmt)
            
            print(f'   ✅ Ensured user {new_user_id} exists')
            print()
            
            # 4. Delete existing chains and sync data for both users first
            print('4. CLEANING UP EXISTING CHAINS TO AVOID CONFLICTS:')
            
            tables_to_clean = [
                'rolled_options_chains',
                'user_rolled_options_sync'
            ]
            
            for table_name in tables_to_clean:
                try:
                    # Delete for both users to avoid conflicts
                    result = await db.execute(text(f'''
                        DELETE FROM {table_name} 
                        WHERE user_id IN (:old_user_id, :new_user_id)
                    '''), {
                        'old_user_id': old_user_id,
                        'new_user_id': new_user_id
                    })
                    
                    rows_deleted = result.rowcount
                    print(f'   🗑️  Deleted {rows_deleted} records from {table_name}')
                    
                except Exception as e:
                    print(f'   ⚠️  Error cleaning {table_name}: {e}')
            
            print()
            
            # 5. Migrate options_orders
            print('5. MIGRATING OPTIONS_ORDERS:')
            
            result = await db.execute(text('''
                UPDATE options_orders 
                SET user_id = :new_user_id 
                WHERE user_id = :old_user_id
            '''), {
                'old_user_id': old_user_id,
                'new_user_id': new_user_id
            })
            
            rows_updated = result.rowcount
            print(f'   ✅ Updated {rows_updated} options_orders records')
            print()
            
            # 6. Migrate options_positions if any
            print('6. MIGRATING OPTIONS_POSITIONS:')
            try:
                result = await db.execute(text('''
                    UPDATE options_positions
                    SET user_id = :new_user_id 
                    WHERE user_id = :old_user_id
                '''), {
                    'old_user_id': old_user_id,
                    'new_user_id': new_user_id
                })
                
                rows_updated = result.rowcount
                print(f'   ✅ Updated {rows_updated} options_positions records')
                
            except Exception as e:
                print(f'   ⚠️  Error migrating options_positions: {e}')
            
            print()
            
            # 7. Commit the transaction
            await db.commit()
            print('7. ✅ TRANSACTION COMMITTED')
            print()
            
            # 8. Verify final state
            print('8. FINAL STATE VERIFICATION:')
            result = await db.execute(text('''
                SELECT user_id, COUNT(*) as order_count
                FROM options_orders 
                GROUP BY user_id 
                ORDER BY order_count DESC
            '''))
            
            final_state = result.fetchall()
            for row in final_state:
                user_id = row.user_id
                count = row.order_count
                marker = ' <-- JWT USER ID (TARGET)' if str(user_id) == new_user_id else ''
                print(f'   {user_id}: {count} orders{marker}')
            
            print()
            
            # 9. Verify MSFT orders specifically
            print('9. MSFT ORDERS VERIFICATION:')
            result = await db.execute(text('''
                SELECT user_id, COUNT(*) as msft_orders,
                       MIN(created_at) as earliest_order,
                       MAX(created_at) as latest_order
                FROM options_orders 
                WHERE chain_symbol = 'MSFT'
                GROUP BY user_id 
                ORDER BY msft_orders DESC
            '''))
            
            final_msft_state = result.fetchall()
            total_msft_orders = 0
            for row in final_msft_state:
                user_id = row.user_id
                count = row.msft_orders
                earliest = str(row.earliest_order)[:10]
                latest = str(row.latest_order)[:10]
                marker = ' <-- JWT USER ID (ALL ORDERS NOW!)' if str(user_id) == new_user_id else ''
                if str(user_id) == new_user_id:
                    total_msft_orders = count
                print(f'   {user_id}: {count} MSFT orders ({earliest} to {latest}){marker}')
            
            print()
            
            if total_msft_orders >= 29:  # 28 old + 1 new = 29 total
                print('🎉 MIGRATION COMPLETED SUCCESSFULLY!')
                print(f'✅ All {total_msft_orders} MSFT orders are now under JWT user ID')
                print('✅ September 5th order should now connect to other MSFT orders')
            else:
                print(f'⚠️  Expected 29+ MSFT orders but only found {total_msft_orders}')
            
            print()
            print('Next steps:')
            print('1. Trigger a new rolled options sync to rebuild chains')
            print('2. Check that September 5th order now appears in MSFT chains with 4 orders')
            
        except Exception as e:
            await db.rollback()
            print(f'❌ MIGRATION FAILED: {e}')
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(migrate_user_ids_fixed())