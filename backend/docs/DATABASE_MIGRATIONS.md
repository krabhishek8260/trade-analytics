# Database Migration Process

This document describes the database migration process for the Trading Analytics v2 application.

## Overview

The application uses PostgreSQL with Supabase and follows a manual migration approach. Migrations are SQL files that modify the database schema and are applied in sequence.

## Migration Files Location

```
backend/
├── migrations/
│   ├── 001_initial_schema.sql
│   ├── 002_portfolio_analytics.sql
│   ├── 003_rls_policies.sql
│   ├── 004_add_robinhood_user_id.sql
│   └── 005_rolled_options_background_processing.sql
└── database/
    └── init/
        └── 005_rolled_options_background_processing.sql
```

## Migration Naming Convention

- **Format**: `XXX_descriptive_name.sql`
- **Example**: `004_add_robinhood_user_id.sql`
- **Numbering**: Sequential numbers starting from 001
- **Description**: Use underscores and descriptive names

## Running Migrations

### Method 1: Manual SQL Execution (Recommended)

#### Using Supabase Dashboard
1. Go to your Supabase project dashboard
2. Navigate to **SQL Editor**
3. Copy and paste the migration SQL
4. Click **Run** to execute

#### Using Supabase CLI
```bash
# Apply all migrations
supabase db push

# Reset database and apply all migrations
supabase db reset --linked

# Run specific migration
supabase db reset --linked --schema-only
```

#### Using psql (if local database)
```bash
# Set environment variable
export DATABASE_URL="postgresql://username:password@localhost:5432/database"

# Run migration
psql $DATABASE_URL -f migrations/004_add_robinhood_user_id.sql
```

### Method 2: Application-Level Migration Script

For migrations that need to be run through the application (e.g., when using Supabase):

```bash
# Create migration script
python run_migration.py
```

Example migration script:
```python
#!/usr/bin/env python3
"""
Script to run database migrations manually
"""

import asyncio
import logging
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def run_migration():
    async with AsyncSessionLocal() as db:
        try:
            # Check if migration already applied
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'robinhood_user_id'
            """)
            
            result = await db.execute(check_query)
            if result.scalar():
                logger.info("Migration already applied")
                return
            
            # Apply migration
            migration_query = text("""
                ALTER TABLE users ADD COLUMN robinhood_user_id VARCHAR(255)
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

## Creating New Migrations

### Step 1: Create Migration File

Create a new SQL file in the `migrations/` directory:

```sql
-- Migration: Add new feature table
-- Description: Creates a new table for storing user preferences
-- Date: 2025-08-02

-- Add new table
CREATE TABLE IF NOT EXISTS user_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    preference_key VARCHAR(100) NOT NULL,
    preference_value JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON user_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_user_preferences_key ON user_preferences(preference_key);

-- Enable RLS
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;

-- Create RLS policy
CREATE POLICY "Users can only access their own preferences" ON user_preferences
    FOR ALL USING (auth.uid() = user_id);

-- Add comment
COMMENT ON TABLE user_preferences IS 'Stores user-specific preferences and settings';
```

### Step 2: Update Models (if needed)

If the migration adds new tables or columns, update the corresponding SQLAlchemy models:

```python
# app/models/user_preferences.py
from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.core.database import Base

class UserPreference(Base):
    __tablename__ = "user_preferences"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    preference_key = Column(String(100), nullable=False)
    preference_value = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

### Step 3: Test Migration

1. **Backup database** (if production)
2. **Test on development environment**
3. **Verify schema changes**
4. **Test application functionality**

## Migration Best Practices

### 1. **Idempotent Migrations**
Make migrations safe to run multiple times:

```sql
-- Good: Check if column exists
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'robinhood_user_id'
    ) THEN
        ALTER TABLE users ADD COLUMN robinhood_user_id VARCHAR(255);
    END IF;
END $$;

-- Good: Use IF NOT EXISTS
CREATE INDEX IF NOT EXISTS idx_users_robinhood_user_id ON users(robinhood_user_id);
```

### 2. **Backward Compatibility**
- Don't drop columns without deprecation period
- Use `ALTER TABLE ... ADD COLUMN` instead of recreating tables
- Consider data migration for breaking changes

### 3. **Documentation**
Include clear comments in migration files:

```sql
-- Migration: 004_add_robinhood_user_id.sql
-- Purpose: Add robinhood_user_id column to users table for consistent user identification
-- Date: 2025-08-02
-- Author: Development Team
-- Breaking Changes: None
-- Rollback: ALTER TABLE users DROP COLUMN robinhood_user_id;
```

### 4. **Testing**
- Test migrations on development database
- Verify application still works after migration
- Test rollback procedures

## Common Migration Patterns

### Adding a Column
```sql
-- Check if column exists first
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

### Adding an Index
```sql
CREATE INDEX IF NOT EXISTS idx_table_column ON table_name(column_name);
```

### Adding RLS Policy
```sql
-- Enable RLS if not already enabled
ALTER TABLE table_name ENABLE ROW LEVEL SECURITY;

-- Create policy
CREATE POLICY "Users can only access their own data" ON table_name
    FOR ALL USING (auth.uid() = user_id);
```

### Data Migration
```sql
-- Update existing data
UPDATE users 
SET robinhood_user_id = 'default_value' 
WHERE robinhood_user_id IS NULL;
```

## Troubleshooting

### Common Issues

#### 1. **Column Already Exists**
```sql
-- Error: column "robinhood_user_id" already exists
-- Solution: Use IF NOT EXISTS or check before adding
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

#### 2. **Permission Denied**
- Ensure you have proper database permissions
- Use service role key for Supabase migrations
- Check RLS policies

#### 3. **Foreign Key Violations**
- Ensure referenced tables/columns exist
- Check data integrity before adding constraints
- Use `ON DELETE CASCADE` or `ON DELETE SET NULL` appropriately

### Rollback Procedures

#### Manual Rollback
```sql
-- Example: Rollback adding robinhood_user_id column
ALTER TABLE users DROP COLUMN IF EXISTS robinhood_user_id;
DROP INDEX IF EXISTS idx_users_robinhood_user_id;
```

#### Application Rollback
Create a rollback script:
```python
async def rollback_migration():
    async with AsyncSessionLocal() as db:
        try:
            # Rollback operations
            await db.execute(text("ALTER TABLE users DROP COLUMN IF EXISTS robinhood_user_id"))
            await db.execute(text("DROP INDEX IF EXISTS idx_users_robinhood_user_id"))
            await db.commit()
            logger.info("Rollback completed successfully!")
        except Exception as e:
            logger.error(f"Rollback failed: {str(e)}")
            await db.rollback()
            raise
```

## Migration Checklist

Before running a migration:

- [ ] **Backup database** (production only)
- [ ] **Test on development environment**
- [ ] **Verify SQL syntax**
- [ ] **Check for breaking changes**
- [ ] **Update application models** (if needed)
- [ ] **Test application functionality**
- [ ] **Document migration**
- [ ] **Plan rollback strategy**

After running a migration:

- [ ] **Verify schema changes**
- [ ] **Test application functionality**
- [ ] **Update documentation**
- [ ] **Monitor for errors**
- [ ] **Clean up temporary files**

## Environment-Specific Considerations

### Development
- Use local database for testing
- Frequent schema changes
- Less strict about data integrity

### Staging
- Mirror production environment
- Test migrations before production
- Validate data integrity

### Production
- Always backup before migration
- Run during maintenance windows
- Monitor closely for issues
- Have rollback plan ready

## Tools and Resources

### Supabase CLI
```bash
# Install Supabase CLI
npm install -g supabase

# Link to project
supabase link --project-ref YOUR_PROJECT_ID

# Apply migrations
supabase db push

# Generate types
supabase gen types typescript --local > types/database.types.ts
```

### Database Connection
```bash
# Test connection
psql $DATABASE_URL -c "SELECT version();"

# List tables
psql $DATABASE_URL -c "\dt"

# Describe table
psql $DATABASE_URL -c "\d users"
```

### Useful Queries
```sql
-- Check migration status
SELECT table_name, column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'users' 
ORDER BY ordinal_position;

-- Check indexes
SELECT indexname, tablename, indexdef 
FROM pg_indexes 
WHERE tablename = 'users';

-- Check RLS policies
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual 
FROM pg_policies 
WHERE tablename = 'users';
```

## Conclusion

Following these migration practices ensures:
- **Reliable deployments**
- **Easy rollbacks**
- **Minimal downtime**
- **Data integrity**
- **Team collaboration**

Always test migrations thoroughly and maintain proper documentation for future reference. 