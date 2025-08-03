# Migration Process Summary

This document summarizes the database migration process we completed to fix the foreign key violation issue and provides a template for future migrations.

## Recent Migration: Add Robinhood User ID

### Problem
The application was experiencing foreign key violations because:
- Random UUIDs were being generated for Robinhood users
- P&L processing tried to create records for non-existent user IDs
- Race conditions between user creation and P&L processing

### Solution
We implemented a comprehensive solution using Robinhood API user IDs:

1. **Database Schema Changes**
   - Added `robinhood_user_id` column to `users` table
   - Created index for performance
   - Added documentation comment

2. **Application Logic Changes**
   - Modified `RobinhoodService` to fetch API user ID
   - Updated authentication flow to use deterministic UUIDs
   - Improved error handling in P&L background service

3. **Migration Process**
   - Created migration script `run_migration.py`
   - Successfully applied migration to database
   - Updated SQLAlchemy models

### Files Modified

#### Database
- `migrations/004_add_robinhood_user_id.sql` - Migration SQL
- `run_migration.py` - Migration execution script

#### Application Code
- `app/models/user.py` - Added robinhood_user_id field
- `app/services/robinhood_service.py` - Added user ID fetching
- `app/api/rolled_options.py` - Updated authentication flow
- `app/services/options_pnl_background_service.py` - Improved error handling

#### Documentation
- `docs/DATABASE_MIGRATIONS.md` - Comprehensive migration guide
- `docs/MIGRATION_QUICK_REFERENCE.md` - Quick reference guide
- `docs/MIGRATION_SUMMARY.md` - This summary document

## Migration Process Template

### Step 1: Identify the Problem
```markdown
## Problem Description
- What issue are you trying to solve?
- What error messages are you seeing?
- What is the root cause?

## Investigation
- Check database schema
- Review application logs
- Test with debug scripts
```

### Step 2: Plan the Solution
```markdown
## Solution Design
- What database changes are needed?
- What application code changes are required?
- How will this affect existing data?

## Migration Strategy
- Is the migration backward compatible?
- What is the rollback plan?
- How will you test the migration?
```

### Step 3: Create Migration Files

#### SQL Migration File
```sql
-- Migration: XXX_description.sql
-- Purpose: Brief description of what this migration does
-- Date: YYYY-MM-DD
-- Author: Your Name
-- Breaking Changes: None/List any breaking changes
-- Rollback: SQL commands to rollback this migration

-- Check if migration already applied
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'table_name' AND column_name = 'column_name'
    ) THEN
        -- Your migration SQL here
        ALTER TABLE table_name ADD COLUMN column_name VARCHAR(255);
    END IF;
END $$;

-- Create indexes if needed
CREATE INDEX IF NOT EXISTS idx_table_column ON table_name(column_name);

-- Add comments
COMMENT ON COLUMN table_name.column_name IS 'Description of the column';
```

#### Application Migration Script
```python
#!/usr/bin/env python3
"""
Migration script for XXX_description
"""

import asyncio
import logging
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_migration():
    """Run the migration"""
    
    async with AsyncSessionLocal() as db:
        try:
            logger.info("Starting migration: XXX_description")
            
            # Check if migration already applied
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'table_name' AND column_name = 'column_name'
            """)
            
            result = await db.execute(check_query)
            if result.scalar():
                logger.info("Migration already applied")
                return
            
            # Apply migration
            migration_query = text("""
                -- Your migration SQL here
                ALTER TABLE table_name ADD COLUMN column_name VARCHAR(255);
            """)
            
            await db.execute(migration_query)
            await db.commit()
            
            logger.info("Migration completed successfully!")
            
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            await db.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(run_migration())
```

### Step 4: Update Application Code

#### SQLAlchemy Models
```python
# app/models/example.py
from sqlalchemy import Column, String
from app.core.database import Base

class Example(Base):
    __tablename__ = "example"
    
    # Add new fields
    new_column = Column(String(255), nullable=True, index=True)
```

#### Application Logic
```python
# Update relevant service files
# Add new methods or modify existing ones
# Update API endpoints if needed
```

### Step 5: Test the Migration

#### Create Test Script
```python
#!/usr/bin/env python3
"""
Test script for migration
"""

import asyncio
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def test_migration():
    """Test that migration was applied correctly"""
    
    async with AsyncSessionLocal() as db:
        # Test queries
        result = await db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'table_name' AND column_name = 'column_name'
        """))
        
        if result.scalar():
            print("✓ Migration applied successfully")
        else:
            print("✗ Migration not applied")

if __name__ == "__main__":
    asyncio.run(test_migration())
```

### Step 6: Run the Migration

```bash
# Method 1: Application script
python run_migration.py

# Method 2: Supabase Dashboard
# Copy SQL to Supabase SQL Editor and run

# Method 3: Supabase CLI
supabase db push

# Method 4: Direct SQL
psql $DATABASE_URL -f migrations/XXX_migration_name.sql
```

### Step 7: Verify and Document

#### Verify Migration
```bash
# Check if migration was applied
python test_migration.py

# Check database schema
psql $DATABASE_URL -c "\d table_name"
```

#### Update Documentation
- Update `docs/DATABASE_MIGRATIONS.md` if needed
- Add migration to the list of completed migrations
- Document any lessons learned

## Best Practices Learned

### 1. **Idempotent Migrations**
Always make migrations safe to run multiple times:
```sql
-- Good: Check before applying
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'robinhood_user_id'
    ) THEN
        ALTER TABLE users ADD COLUMN robinhood_user_id VARCHAR(255);
    END IF;
END $$;
```

### 2. **Application-Level Migration Scripts**
Use application-level scripts when:
- You need to use the application's database connection
- You're using Supabase and can't access the database directly
- You need to perform complex logic during migration

### 3. **Comprehensive Testing**
- Test migrations on development environment first
- Create test scripts to verify migration success
- Test application functionality after migration

### 4. **Documentation**
- Document the problem and solution
- Include rollback procedures
- Update relevant documentation files

### 5. **Error Handling**
- Include proper error handling in migration scripts
- Provide clear error messages
- Have rollback procedures ready

## Common Migration Patterns

### Adding a Column
```sql
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'table_name' AND column_name = 'new_column'
    ) THEN
        ALTER TABLE table_name ADD COLUMN new_column VARCHAR(255);
    END IF;
END $$;
```

### Adding an Index
```sql
CREATE INDEX IF NOT EXISTS idx_table_column ON table_name(column_name);
```

### Adding RLS Policy
```sql
ALTER TABLE table_name ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can only access their own data" ON table_name
    FOR ALL USING (auth.uid() = user_id);
```

### Data Migration
```sql
UPDATE table_name 
SET new_column = 'default_value' 
WHERE new_column IS NULL;
```

## Troubleshooting

### Common Issues
1. **Column already exists**: Use `IF NOT EXISTS` checks
2. **Permission denied**: Check database permissions and RLS policies
3. **Foreign key violations**: Ensure referenced tables exist
4. **Connection issues**: Verify database URL and connectivity

### Debug Commands
```bash
# Check database connection
psql $DATABASE_URL -c "SELECT version();"

# Check table structure
psql $DATABASE_URL -c "\d table_name"

# Check if column exists
psql $DATABASE_URL -c "
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'table_name' AND column_name = 'column_name';
"
```

## Conclusion

The migration process we completed successfully resolved the foreign key violation issue by:

1. **Using consistent user IDs** based on Robinhood API
2. **Improving error handling** in the P&L background service
3. **Adding proper database constraints** and indexes
4. **Documenting the process** for future reference

This template provides a structured approach for future migrations, ensuring they are:
- **Safe and reliable**
- **Well-documented**
- **Easy to test and verify**
- **Simple to rollback if needed**

Always follow these practices to maintain database integrity and application reliability. 