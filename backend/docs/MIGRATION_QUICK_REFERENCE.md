# Migration Quick Reference

Quick reference for common database migration operations in the Trading Analytics v2 application.

## Quick Commands

### Run Migration
```bash
# Method 1: Supabase Dashboard
# Copy SQL to Supabase SQL Editor and run

# Method 2: Application script
python run_migration.py

# Method 3: Supabase CLI
supabase db push

# Method 4: Direct SQL (if local)
psql $DATABASE_URL -f migrations/XXX_migration_name.sql
```

### Check Migration Status
```bash
# Check if column exists
psql $DATABASE_URL -c "
SELECT column_name 
FROM information_schema.columns 
WHERE table_name = 'users' AND column_name = 'robinhood_user_id';
"

# List all tables
psql $DATABASE_URL -c "\dt"

# Describe table structure
psql $DATABASE_URL -c "\d users"
```

## Common Migration Templates

### 1. Add Column
```sql
-- Migration: Add new column
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'new_column'
    ) THEN
        ALTER TABLE users ADD COLUMN new_column VARCHAR(255);
    END IF;
END $$;
```

### 2. Add Index
```sql
-- Migration: Add index for performance
CREATE INDEX IF NOT EXISTS idx_users_new_column ON users(new_column);
```

### 3. Add RLS Policy
```sql
-- Migration: Enable RLS and add policy
ALTER TABLE table_name ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can only access their own data" ON table_name
    FOR ALL USING (auth.uid() = user_id);
```

### 4. Create New Table
```sql
-- Migration: Create new table
CREATE TABLE IF NOT EXISTS new_table (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_new_table_user_id ON new_table(user_id);

-- Enable RLS
ALTER TABLE new_table ENABLE ROW LEVEL SECURITY;

-- Add policy
CREATE POLICY "Users can only access their own data" ON new_table
    FOR ALL USING (auth.uid() = user_id);
```

### 5. Update Data
```sql
-- Migration: Update existing data
UPDATE users 
SET new_column = 'default_value' 
WHERE new_column IS NULL;
```

## Rollback Templates

### 1. Remove Column
```sql
-- Rollback: Remove column
ALTER TABLE users DROP COLUMN IF EXISTS new_column;
```

### 2. Remove Index
```sql
-- Rollback: Remove index
DROP INDEX IF EXISTS idx_users_new_column;
```

### 3. Remove Table
```sql
-- Rollback: Remove table
DROP TABLE IF EXISTS new_table CASCADE;
```

### 4. Remove Policy
```sql
-- Rollback: Remove RLS policy
DROP POLICY IF EXISTS "Users can only access their own data" ON table_name;
```

## Application Migration Script Template

```python
#!/usr/bin/env python3
"""
Migration script template
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
            logger.info("Starting migration: [Description]")
            
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

## Troubleshooting Commands

### Check Database Connection
```bash
# Test connection
psql $DATABASE_URL -c "SELECT version();"

# Check current user
psql $DATABASE_URL -c "SELECT current_user;"

# List databases
psql $DATABASE_URL -c "\l"
```

### Check Table Structure
```bash
# List all columns in table
psql $DATABASE_URL -c "
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'users' 
ORDER BY ordinal_position;
"

# Check indexes
psql $DATABASE_URL -c "
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'users';
"

# Check constraints
psql $DATABASE_URL -c "
SELECT conname, contype, pg_get_constraintdef(oid) 
FROM pg_constraint 
WHERE conrelid = 'users'::regclass;
"
```

### Check RLS Policies
```bash
# List RLS policies
psql $DATABASE_URL -c "
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual 
FROM pg_policies 
WHERE tablename = 'users';
"

# Check if RLS is enabled
psql $DATABASE_URL -c "
SELECT schemaname, tablename, rowsecurity 
FROM pg_tables 
WHERE tablename = 'users';
"
```

## Environment Variables

```bash
# Set database URL
export DATABASE_URL="postgresql://username:password@localhost:5432/database"

# Set Supabase URL and keys
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_ANON_KEY="your-anon-key"
export SUPABASE_SERVICE_KEY="your-service-key"
```

## Common Error Solutions

### 1. "Column already exists"
```sql
-- Use IF NOT EXISTS
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'new_column'
    ) THEN
        ALTER TABLE users ADD COLUMN new_column VARCHAR(255);
    END IF;
END $$;
```

### 2. "Permission denied"
- Check database permissions
- Use service role key for Supabase
- Verify RLS policies

### 3. "Foreign key violation"
- Ensure referenced tables exist
- Check data integrity
- Use appropriate ON DELETE actions

### 4. "Connection refused"
- Check database URL
- Verify database is running
- Check firewall settings

## Migration Checklist

### Before Migration
- [ ] Backup database (production)
- [ ] Test on development
- [ ] Verify SQL syntax
- [ ] Check for breaking changes
- [ ] Update models (if needed)
- [ ] Plan rollback strategy

### After Migration
- [ ] Verify schema changes
- [ ] Test application
- [ ] Monitor for errors
- [ ] Update documentation
- [ ] Clean up temporary files

## File Locations

```
backend/
├── migrations/                    # SQL migration files
│   ├── 001_initial_schema.sql
│   ├── 002_portfolio_analytics.sql
│   ├── 003_rls_policies.sql
│   ├── 004_add_robinhood_user_id.sql
│   └── 005_rolled_options_background_processing.sql
├── docs/                         # Documentation
│   ├── DATABASE_MIGRATIONS.md
│   └── MIGRATION_QUICK_REFERENCE.md
├── run_migration.py              # Migration script template
└── app/
    ├── models/                   # SQLAlchemy models
    └── core/
        └── database.py           # Database configuration
``` 