# Supabase Setup Guide

This guide walks through setting up Supabase for the Trading Analytics v2 application.

## Prerequisites

1. [Supabase CLI](https://supabase.com/docs/guides/cli) installed
2. Supabase account created
3. Node.js and npm installed

## Setup Steps

### 1. Initialize Supabase Project

```bash
# Navigate to project directory
cd /Users/abhishek/tradeanalytics-v2/backend

# Initialize Supabase
supabase init

# Link to your Supabase project (replace PROJECT_ID)
supabase link --project-ref PROJECT_ID
```

### 2. Database Setup

#### Option A: Using Supabase Dashboard
1. Go to your Supabase project dashboard
2. Navigate to SQL Editor
3. Run the migration files in order:
   - `migrations/001_initial_schema.sql`
   - `migrations/002_portfolio_analytics.sql`
   - `migrations/003_rls_policies.sql`

#### Option B: Using Supabase CLI
```bash
# Apply migrations
supabase db push

# Or run individual migrations
supabase db reset --linked
```

### 3. Environment Configuration

Create a `.env` file in the backend directory:

```env
# Supabase Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key

# Database (automatically configured by Supabase)
DATABASE_URL=postgresql://postgres:your-password@db.your-project-id.supabase.co:5432/postgres

# Redis (if using external Redis)
REDIS_URL=redis://localhost:6379

# Robinhood (for development)
ROBINHOOD_USERNAME=
ROBINHOOD_PASSWORD=

# Application Settings
DEBUG=true
ALLOWED_HOSTS=["http://localhost:3000", "http://localhost:8000"]
SECRET_KEY=your-secret-key-here
```

### 4. Authentication Setup

1. In Supabase Dashboard, go to Authentication > Settings
2. Configure the following:
   - Site URL: `http://localhost:3000` (for development)
   - Additional redirect URLs: `http://localhost:3000/auth/callback`
   - Disable email confirmations for development (optional)

### 5. Row Level Security (RLS)

The migrations automatically enable RLS and create policies. Verify in the Supabase dashboard:

1. Go to Database > Tables
2. Check that RLS is enabled on all user-data tables
3. Review policies in the "Policies" tab

### 6. API Keys and Security

1. **Anon Key**: Safe for client-side use, respects RLS policies
2. **Service Role Key**: Bypass RLS, server-side only
3. Store service role key securely and never expose to clients

### 7. Testing Database Connection

```bash
# Install dependencies
cd /Users/abhishek/tradeanalytics-v2/backend
pip install -r requirements.txt

# Test database connection
python -c "
from app.core.database import init_db
import asyncio
asyncio.run(init_db())
print('Database connection successful!')
"
```

## Database Schema Overview

### Core Tables
- `users`: User profiles (extends auth.users)
- `portfolios`: Portfolio snapshots
- `stock_positions`: Stock holdings
- `options_positions`: Options contracts with Greeks
- `options_orders`: Order history with multi-leg support

### Analytics Tables
- `portfolio_performance`: Daily performance metrics
- `options_strategies`: Grouped strategies
- `trade_journal`: Trade notes and analysis
- `alerts`: User notifications

### Utility Tables
- `cache_entries`: Application cache

## Key Features

### 1. Row Level Security
- Users can only access their own data
- Automatic user_id assignment on inserts
- Secure multi-tenant architecture

### 2. Options Trading Support
- Full options chain data
- Multi-leg strategies
- Greeks calculation
- Risk/reward analysis

### 3. Performance Analytics
- Historical portfolio tracking
- Risk metrics calculation
- Strategy performance analysis

### 4. Data Validation
- Type safety with constraints
- Business logic validation triggers
- Comprehensive error handling

## Development Tips

### 1. Local Development
```bash
# Start local Supabase (optional)
supabase start

# Run migrations
supabase db reset

# Generate TypeScript types
supabase gen types typescript --local > types/database.types.ts
```

### 2. Data Seeding
```sql
-- Example: Insert test user data
INSERT INTO users (id, username, full_name, email) 
VALUES (auth.uid(), 'testuser', 'Test User', 'test@example.com');
```

### 3. Debugging
```bash
# View logs
supabase logs

# Access database directly
supabase db shell
```

## Production Deployment

### 1. Environment Variables
- Update all URLs to production domains
- Use strong passwords and secrets
- Enable email confirmations

### 2. Security Checklist
- [ ] RLS enabled on all tables
- [ ] Service role key secured
- [ ] CORS configured properly
- [ ] Rate limiting enabled
- [ ] Backup strategy in place

### 3. Performance Optimization
- [ ] Database indexes reviewed
- [ ] Connection pooling configured
- [ ] Cache TTL values optimized
- [ ] Monitoring setup

## Troubleshooting

### Common Issues

1. **Connection Failed**
   - Check DATABASE_URL format
   - Verify Supabase project is active
   - Confirm network connectivity

2. **RLS Policy Errors**
   - Ensure user is authenticated
   - Check policy conditions
   - Verify auth.uid() returns valid UUID

3. **Migration Errors**
   - Run migrations in correct order
   - Check for syntax errors
   - Verify permissions

### Getting Help
- [Supabase Documentation](https://supabase.com/docs)
- [Supabase Discord](https://discord.supabase.com)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)