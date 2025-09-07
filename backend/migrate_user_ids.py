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

async def migrate_user_ids():
    """Migrate all orders from old user ID to JWT user ID"""
    
    old_user_id = '13461768-f848-4c04-aea2-46817bc9a3a5'  # Development fallback user
    new_user_id = '123e4567-e89b-12d3-a456-426614174000'  # JWT authenticated user
    
    print('=== USER ID MIGRATION ===')
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
            for row in current_state:
                user_id = row.user_id
                count = row.order_count
                marker = ' <-- OLD USER ID' if str(user_id) == old_user_id else ' <-- JWT USER ID' if str(user_id) == new_user_id else ''
                print(f'   {user_id}: {count} orders{marker}')
            
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
            
            # 4. Migrate options_orders
            print('4. MIGRATING OPTIONS_ORDERS:')
            
            # Count orders to migrate
            result = await db.execute(text('''
                SELECT COUNT(*) FROM options_orders WHERE user_id = :old_user_id
            '''), {'old_user_id': old_user_id})
            orders_to_migrate = result.scalar()
            
            if orders_to_migrate == 0:
                print(f'   ℹ️  No orders found for user {old_user_id} - already migrated?')
            else:
                print(f'   Migrating {orders_to_migrate} orders...')
                
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
            
            # 5. Migrate other related tables
            print('5. MIGRATING RELATED TABLES:')
            
            # Check for other tables with user_id references
            tables_to_check = [
                'rolled_options_chains',
                'user_rolled_options_sync',
                'options_positions'
            ]
            
            for table_name in tables_to_check:
                try:
                    # Check if table exists and has records
                    result = await db.execute(text(f'''
                        SELECT COUNT(*) FROM {table_name} WHERE user_id = :old_user_id
                    '''), {'old_user_id': old_user_id})
                    records_to_migrate = result.scalar()
                    
                    if records_to_migrate > 0:
                        print(f'   Migrating {records_to_migrate} records from {table_name}...')
                        
                        result = await db.execute(text(f'''
                            UPDATE {table_name}
                            SET user_id = :new_user_id 
                            WHERE user_id = :old_user_id
                        '''), {
                            'old_user_id': old_user_id,
                            'new_user_id': new_user_id
                        })
                        
                        rows_updated = result.rowcount
                        print(f'   ✅ Updated {rows_updated} {table_name} records')
                    else:
                        print(f'   ℹ️  No records to migrate in {table_name}')
                        
                except Exception as e:
                    print(f'   ⚠️  Error checking {table_name}: {e}')
            
            print()
            
            # 6. Commit the transaction
            await db.commit()
            print('6. ✅ TRANSACTION COMMITTED')
            print()
            
            # 7. Verify final state
            print('7. FINAL STATE VERIFICATION:')
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
            
            # 8. Verify MSFT orders specifically
            print('8. MSFT ORDERS VERIFICATION:')
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
            for row in final_msft_state:
                user_id = row.user_id
                count = row.msft_orders
                earliest = str(row.earliest_order)[:10]
                latest = str(row.latest_order)[:10]
                marker = ' <-- JWT USER ID' if str(user_id) == new_user_id else ''
                print(f'   {user_id}: {count} MSFT orders ({earliest} to {latest}){marker}')
            
            print()
            print('🎉 MIGRATION COMPLETED SUCCESSFULLY!')
            print()
            print('Next steps:')
            print('1. Trigger a new rolled options sync to rebuild chains')
            print('2. Check that September 5th order now appears in MSFT chains')
            
        except Exception as e:
            await db.rollback()
            print(f'❌ MIGRATION FAILED: {e}')
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(migrate_user_ids())