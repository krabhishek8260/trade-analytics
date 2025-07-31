-- Additional Row Level Security (RLS) policies and security functions
-- Ensures data isolation and security for multi-tenant application

-- Create function to check if user can access data
CREATE OR REPLACE FUNCTION auth.can_access_user_data(target_user_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    -- Users can access their own data
    IF auth.uid() = target_user_id THEN
        RETURN TRUE;
    END IF;
    
    -- Admin users can access all data (implement if needed)
    -- You can add admin role checks here in the future
    
    RETURN FALSE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to automatically set user_id on insert
CREATE OR REPLACE FUNCTION auto_set_user_id()
RETURNS TRIGGER AS $$
BEGIN
    -- Set user_id to current authenticated user
    NEW.user_id := auth.uid();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Apply auto_set_user_id trigger to all user-scoped tables
CREATE TRIGGER set_user_id_portfolios 
    BEFORE INSERT ON portfolios 
    FOR EACH ROW EXECUTE FUNCTION auto_set_user_id();

CREATE TRIGGER set_user_id_stock_positions 
    BEFORE INSERT ON stock_positions 
    FOR EACH ROW EXECUTE FUNCTION auto_set_user_id();

CREATE TRIGGER set_user_id_options_positions 
    BEFORE INSERT ON options_positions 
    FOR EACH ROW EXECUTE FUNCTION auto_set_user_id();

CREATE TRIGGER set_user_id_options_orders 
    BEFORE INSERT ON options_orders 
    FOR EACH ROW EXECUTE FUNCTION auto_set_user_id();

CREATE TRIGGER set_user_id_portfolio_performance 
    BEFORE INSERT ON portfolio_performance 
    FOR EACH ROW EXECUTE FUNCTION auto_set_user_id();

CREATE TRIGGER set_user_id_options_strategies 
    BEFORE INSERT ON options_strategies 
    FOR EACH ROW EXECUTE FUNCTION auto_set_user_id();

CREATE TRIGGER set_user_id_trade_journal 
    BEFORE INSERT ON trade_journal 
    FOR EACH ROW EXECUTE FUNCTION auto_set_user_id();

CREATE TRIGGER set_user_id_alerts 
    BEFORE INSERT ON alerts 
    FOR EACH ROW EXECUTE FUNCTION auto_set_user_id();

-- Enhanced RLS policies for better security

-- Users table - allow users to read their profile and update certain fields
DROP POLICY IF EXISTS "Users can only access their own data" ON users;

CREATE POLICY "Users can read their own profile" ON users
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update their own profile" ON users
    FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Users can insert their own profile" ON users
    FOR INSERT WITH CHECK (auth.uid() = id);

-- Cache entries - allow users to manage their own cache
ALTER TABLE cache_entries ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their own cache" ON cache_entries
    FOR ALL USING (auth.uid() = user_id OR user_id IS NULL);

-- Function to clean expired cache entries
CREATE OR REPLACE FUNCTION clean_expired_cache()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM cache_entries WHERE expires_at < NOW();
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create a function to validate option data
CREATE OR REPLACE FUNCTION validate_option_data()
RETURNS TRIGGER AS $$
BEGIN
    -- Validate option type
    IF NEW.option_type NOT IN ('call', 'put') THEN
        RAISE EXCEPTION 'Invalid option_type: %', NEW.option_type;
    END IF;
    
    -- Validate strike price is positive
    IF NEW.strike_price <= 0 THEN
        RAISE EXCEPTION 'Strike price must be positive: %', NEW.strike_price;
    END IF;
    
    -- Validate expiration date is in the future (allow same day for day trading)
    IF NEW.expiration_date < CURRENT_DATE THEN
        RAISE EXCEPTION 'Expiration date cannot be in the past: %', NEW.expiration_date;
    END IF;
    
    -- Calculate days to expiry
    NEW.days_to_expiry := (NEW.expiration_date - CURRENT_DATE);
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply validation trigger to options_positions
CREATE TRIGGER validate_options_position_data 
    BEFORE INSERT OR UPDATE ON options_positions 
    FOR EACH ROW EXECUTE FUNCTION validate_option_data();

-- Function to validate stock data
CREATE OR REPLACE FUNCTION validate_stock_data()
RETURNS TRIGGER AS $$
BEGIN
    -- Validate symbol format (basic check)
    IF NEW.symbol !~ '^[A-Z]{1,6}$' THEN
        RAISE EXCEPTION 'Invalid symbol format: %', NEW.symbol;
    END IF;
    
    -- Validate quantity is not zero
    IF NEW.quantity = 0 THEN
        RAISE EXCEPTION 'Quantity cannot be zero';
    END IF;
    
    -- Validate prices are non-negative
    IF NEW.average_buy_price IS NOT NULL AND NEW.average_buy_price < 0 THEN
        RAISE EXCEPTION 'Average buy price cannot be negative: %', NEW.average_buy_price;
    END IF;
    
    IF NEW.current_price IS NOT NULL AND NEW.current_price < 0 THEN
        RAISE EXCEPTION 'Current price cannot be negative: %', NEW.current_price;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply validation trigger to stock_positions
CREATE TRIGGER validate_stock_position_data 
    BEFORE INSERT OR UPDATE ON stock_positions 
    FOR EACH ROW EXECUTE FUNCTION validate_stock_data();

-- Create indexes for frequently queried combinations
CREATE INDEX IF NOT EXISTS idx_options_positions_user_expiry_type ON options_positions(user_id, expiration_date, option_type);
CREATE INDEX IF NOT EXISTS idx_options_positions_underlying_strategy ON options_positions(underlying_symbol, strategy) WHERE strategy IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_portfolio_performance_user_date_value ON portfolio_performance(user_id, date, total_value);

-- Create partial indexes for active data only
CREATE INDEX IF NOT EXISTS idx_alerts_active ON alerts(user_id, type, created_at) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_options_strategies_active ON options_strategies(user_id, underlying_symbol) WHERE status = 'active';

-- Create composite indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_options_positions_comprehensive ON options_positions(user_id, underlying_symbol, expiration_date, option_type, transaction_side);
CREATE INDEX IF NOT EXISTS idx_options_orders_comprehensive ON options_orders(user_id, underlying_symbol, state, order_created_at DESC);

-- Add comments to tables for documentation
COMMENT ON TABLE users IS 'User profiles extending Supabase auth.users';
COMMENT ON TABLE portfolios IS 'Portfolio snapshots for historical tracking';
COMMENT ON TABLE stock_positions IS 'Current stock positions';
COMMENT ON TABLE options_positions IS 'Current options positions with full Greeks and risk metrics';
COMMENT ON TABLE options_orders IS 'Historical options orders with multi-leg support';
COMMENT ON TABLE portfolio_performance IS 'Daily portfolio performance metrics for analytics';
COMMENT ON TABLE options_strategies IS 'Grouped options positions forming strategies';
COMMENT ON TABLE trade_journal IS 'Trade notes and lessons learned';
COMMENT ON TABLE alerts IS 'User alerts and notifications';
COMMENT ON TABLE cache_entries IS 'Application cache for performance optimization';

-- Add comments to important columns
COMMENT ON COLUMN options_positions.clearing_cost_basis IS 'Robinhood clearing cost basis for accurate P&L calculation';
COMMENT ON COLUMN options_positions.strategy IS 'Determined strategy type (LONG CALL, SHORT PUT, etc.)';
COMMENT ON COLUMN options_orders.legs IS 'Multi-leg order details as JSONB';
COMMENT ON COLUMN options_orders.executions IS 'Order execution details as JSONB';
COMMENT ON COLUMN options_strategies.position_ids IS 'Array of related options_positions.id';

-- Grant necessary permissions for application user
-- Note: In Supabase, these permissions are managed through the dashboard
-- but we document them here for reference

/*
-- These would be run in Supabase SQL editor or via admin API:

-- Grant usage on schema
GRANT USAGE ON SCHEMA public TO authenticated;

-- Grant CRUD permissions on tables to authenticated users
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO authenticated;

-- Grant usage on sequences
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO authenticated;

-- Grant execute on functions
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO authenticated;
*/