-- Initial database schema for Trading Analytics v2
-- Compatible with Supabase/PostgreSQL

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable RLS (Row Level Security)
ALTER DEFAULT PRIVILEGES REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;

-- Users table (extends Supabase auth.users)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    username VARCHAR(50) UNIQUE,
    full_name VARCHAR(100),
    email VARCHAR(255),
    robinhood_username VARCHAR(100),
    settings JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS on users table
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Create policy for users to only access their own data
CREATE POLICY "Users can only access their own data" ON users
    FOR ALL USING (auth.uid() = id);

-- Portfolio snapshots table
CREATE TABLE IF NOT EXISTS portfolios (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    snapshot_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Portfolio metrics
    total_value NUMERIC(15, 2),
    total_return NUMERIC(15, 2),
    total_return_percent NUMERIC(8, 4),
    day_return NUMERIC(15, 2),
    day_return_percent NUMERIC(8, 4),
    
    -- Asset allocation
    stocks_value NUMERIC(15, 2),
    options_value NUMERIC(15, 2),
    cash_value NUMERIC(15, 2),
    
    -- Raw data from API
    raw_data JSONB,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS on portfolios table
ALTER TABLE portfolios ENABLE ROW LEVEL SECURITY;

-- Create policy for portfolios
CREATE POLICY "Users can only access their own portfolios" ON portfolios
    FOR ALL USING (auth.uid() = user_id);

-- Stock positions table
CREATE TABLE IF NOT EXISTS stock_positions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Stock details
    symbol VARCHAR(10) NOT NULL,
    quantity NUMERIC(12, 4) NOT NULL,
    average_buy_price NUMERIC(12, 4),
    current_price NUMERIC(12, 4),
    
    -- Financial metrics
    market_value NUMERIC(15, 2),
    total_cost NUMERIC(15, 2),
    total_return NUMERIC(15, 2),
    total_return_percent NUMERIC(8, 4),
    
    -- Raw data from API
    raw_data JSONB,
    
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS on stock_positions table
ALTER TABLE stock_positions ENABLE ROW LEVEL SECURITY;

-- Create policy for stock_positions
CREATE POLICY "Users can only access their own stock positions" ON stock_positions
    FOR ALL USING (auth.uid() = user_id);

-- Options positions table
CREATE TABLE IF NOT EXISTS options_positions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Option contract details
    underlying_symbol VARCHAR(10) NOT NULL,
    option_type VARCHAR(4) NOT NULL CHECK (option_type IN ('call', 'put')),
    strike_price NUMERIC(12, 4) NOT NULL,
    expiration_date DATE NOT NULL,
    
    -- Position details
    quantity NUMERIC(12, 4) NOT NULL,
    contracts INTEGER GENERATED ALWAYS AS (ABS(quantity::INTEGER)) STORED,
    transaction_side VARCHAR(4) NOT NULL CHECK (transaction_side IN ('buy', 'sell')),
    position_effect VARCHAR(5) NOT NULL CHECK (position_effect IN ('open', 'close')),
    direction VARCHAR(6) NOT NULL CHECK (direction IN ('credit', 'debit')),
    
    -- Pricing
    average_price NUMERIC(12, 4),
    current_price NUMERIC(12, 4),
    clearing_cost_basis NUMERIC(12, 2),
    clearing_direction VARCHAR(6) CHECK (clearing_direction IN ('credit', 'debit')),
    
    -- Financial metrics
    market_value NUMERIC(15, 2),
    total_cost NUMERIC(15, 2),
    total_return NUMERIC(15, 2),
    total_return_percent NUMERIC(8, 4),
    
    -- Strategy and analysis
    strategy VARCHAR(20),
    strategy_type VARCHAR(20),
    
    -- Greeks (options pricing sensitivities)
    delta NUMERIC(8, 6),
    gamma NUMERIC(8, 6),
    theta NUMERIC(8, 6),
    vega NUMERIC(8, 6),
    rho NUMERIC(8, 6),
    implied_volatility NUMERIC(8, 4),
    
    -- Risk metrics
    days_to_expiry INTEGER,
    break_even_price NUMERIC(12, 4),
    max_profit NUMERIC(15, 2),
    max_loss NUMERIC(15, 2),
    probability_of_profit NUMERIC(5, 2),
    
    -- Timestamps
    opened_at TIMESTAMP WITH TIME ZONE,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Raw data from API
    raw_data JSONB
);

-- Enable RLS on options_positions table
ALTER TABLE options_positions ENABLE ROW LEVEL SECURITY;

-- Create policy for options_positions
CREATE POLICY "Users can only access their own options positions" ON options_positions
    FOR ALL USING (auth.uid() = user_id);

-- Options orders table
CREATE TABLE IF NOT EXISTS options_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Order identification
    order_id VARCHAR(50) NOT NULL,
    underlying_symbol VARCHAR(10) NOT NULL,
    
    -- Order details
    strategy VARCHAR(50),
    direction VARCHAR(6) NOT NULL CHECK (direction IN ('credit', 'debit')),
    state VARCHAR(20) NOT NULL,
    type VARCHAR(20) DEFAULT 'limit',
    quantity NUMERIC(12, 4) NOT NULL,
    
    -- Pricing
    price NUMERIC(12, 4),
    premium NUMERIC(15, 2),
    processed_premium NUMERIC(15, 2),
    processed_premium_direction VARCHAR(6) CHECK (processed_premium_direction IN ('credit', 'debit')),
    
    -- Multi-leg information
    legs_count INTEGER DEFAULT 1,
    legs JSONB, -- Detailed legs data
    executions_count INTEGER DEFAULT 0,
    executions JSONB, -- All executions
    
    -- Single leg info (for compatibility and quick access)
    option_type VARCHAR(4) CHECK (option_type IN ('call', 'put')),
    strike_price NUMERIC(12, 4),
    expiration_date VARCHAR(20),
    transaction_side VARCHAR(4) CHECK (transaction_side IN ('buy', 'sell')),
    position_effect VARCHAR(5) CHECK (position_effect IN ('open', 'close')),
    
    -- Financial summary
    total_cost NUMERIC(15, 2),
    fees NUMERIC(10, 2),
    net_amount NUMERIC(15, 2),
    
    -- Timestamps
    order_created_at TIMESTAMP WITH TIME ZONE,
    order_updated_at TIMESTAMP WITH TIME ZONE,
    filled_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Raw data from API
    raw_data JSONB
);

-- Enable RLS on options_orders table
ALTER TABLE options_orders ENABLE ROW LEVEL SECURITY;

-- Create policy for options_orders
CREATE POLICY "Users can only access their own options orders" ON options_orders
    FOR ALL USING (auth.uid() = user_id);

-- Cache entries table for performance optimization
CREATE TABLE IF NOT EXISTS cache_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    cache_key VARCHAR(255) NOT NULL,
    cache_value JSONB NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_portfolios_user_id_date ON portfolios(user_id, snapshot_date DESC);
CREATE INDEX IF NOT EXISTS idx_stock_positions_user_symbol ON stock_positions(user_id, symbol);
CREATE INDEX IF NOT EXISTS idx_options_positions_user_symbol ON options_positions(user_id, underlying_symbol);
CREATE INDEX IF NOT EXISTS idx_options_positions_expiry ON options_positions(user_id, expiration_date);
CREATE INDEX IF NOT EXISTS idx_options_orders_user_state ON options_orders(user_id, state);
CREATE INDEX IF NOT EXISTS idx_cache_entries_key_expires ON cache_entries(cache_key, expires_at);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_stock_positions_updated_at BEFORE UPDATE ON stock_positions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_options_positions_updated_at BEFORE UPDATE ON options_positions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();