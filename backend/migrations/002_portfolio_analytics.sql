-- Portfolio analytics and performance tracking
-- Additional tables and functions for advanced analytics

-- Portfolio performance history table
CREATE TABLE IF NOT EXISTS portfolio_performance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Time series data
    date DATE NOT NULL,
    total_value NUMERIC(15, 2) NOT NULL,
    total_return NUMERIC(15, 2),
    day_return NUMERIC(15, 2),
    
    -- Asset breakdown
    stocks_value NUMERIC(15, 2) DEFAULT 0,
    options_value NUMERIC(15, 2) DEFAULT 0,
    cash_value NUMERIC(15, 2) DEFAULT 0,
    
    -- Performance metrics
    volatility NUMERIC(8, 4),
    sharpe_ratio NUMERIC(8, 4),
    max_drawdown NUMERIC(8, 4),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(user_id, date)
);

-- Enable RLS on portfolio_performance table
ALTER TABLE portfolio_performance ENABLE ROW LEVEL SECURITY;

-- Create policy for portfolio_performance
CREATE POLICY "Users can only access their own portfolio performance" ON portfolio_performance
    FOR ALL USING (auth.uid() = user_id);

-- Options strategies tracking table
CREATE TABLE IF NOT EXISTS options_strategies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Strategy details
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL, -- single_leg, spread, combination
    underlying_symbol VARCHAR(10) NOT NULL,
    
    -- Strategy legs (related positions)
    position_ids UUID[] NOT NULL,
    legs_data JSONB NOT NULL,
    
    -- Risk/Reward analysis
    max_profit NUMERIC(15, 2),
    max_loss NUMERIC(15, 2),
    break_even_points NUMERIC(12, 4)[],
    
    -- Greeks aggregation
    net_delta NUMERIC(8, 6),
    net_gamma NUMERIC(8, 6),
    net_theta NUMERIC(8, 6),
    net_vega NUMERIC(8, 6),
    
    -- Analysis
    probability_of_profit NUMERIC(5, 2),
    risk_reward_ratio NUMERIC(8, 4),
    recommended_action VARCHAR(20),
    
    -- Status
    status VARCHAR(20) DEFAULT 'active', -- active, closed, expired
    opened_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS on options_strategies table
ALTER TABLE options_strategies ENABLE ROW LEVEL SECURITY;

-- Create policy for options_strategies
CREATE POLICY "Users can only access their own options strategies" ON options_strategies
    FOR ALL USING (auth.uid() = user_id);

-- Trade journal table for tracking individual trades and lessons learned
CREATE TABLE IF NOT EXISTS trade_journal (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Trade identification
    trade_type VARCHAR(20) NOT NULL, -- stock, option, strategy
    symbol VARCHAR(10) NOT NULL,
    strategy_name VARCHAR(100),
    
    -- Entry and exit
    entry_date DATE NOT NULL,
    exit_date DATE,
    entry_price NUMERIC(12, 4),
    exit_price NUMERIC(12, 4),
    quantity NUMERIC(12, 4),
    
    -- Trade outcome
    profit_loss NUMERIC(15, 2),
    profit_loss_percent NUMERIC(8, 4),
    fees NUMERIC(10, 2),
    holding_period_days INTEGER,
    
    -- Analysis and notes
    thesis TEXT, -- Why did you enter this trade?
    outcome TEXT, -- What happened?
    lessons_learned TEXT, -- What did you learn?
    tags VARCHAR(50)[], -- For categorization
    
    -- Related positions/orders
    related_position_ids UUID[],
    related_order_ids UUID[],
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS on trade_journal table
ALTER TABLE trade_journal ENABLE ROW LEVEL SECURITY;

-- Create policy for trade_journal
CREATE POLICY "Users can only access their own trade journal" ON trade_journal
    FOR ALL USING (auth.uid() = user_id);

-- Alerts and notifications table
CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Alert details
    type VARCHAR(50) NOT NULL, -- price_alert, expiry_warning, profit_target, stop_loss
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    priority VARCHAR(10) DEFAULT 'medium', -- low, medium, high, critical
    
    -- Alert conditions
    symbol VARCHAR(10),
    condition_type VARCHAR(50), -- price_above, price_below, profit_above, loss_below, days_to_expiry
    trigger_value NUMERIC(15, 4),
    current_value NUMERIC(15, 4),
    
    -- Status
    status VARCHAR(20) DEFAULT 'active', -- active, triggered, dismissed, expired
    triggered_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    
    -- Related entities
    related_position_id UUID,
    related_order_id UUID,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS on alerts table
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;

-- Create policy for alerts
CREATE POLICY "Users can only access their own alerts" ON alerts
    FOR ALL USING (auth.uid() = user_id);

-- Create additional indexes for analytics
CREATE INDEX IF NOT EXISTS idx_portfolio_performance_user_date ON portfolio_performance(user_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_options_strategies_user_symbol ON options_strategies(user_id, underlying_symbol);
CREATE INDEX IF NOT EXISTS idx_options_strategies_status ON options_strategies(user_id, status);
CREATE INDEX IF NOT EXISTS idx_trade_journal_user_date ON trade_journal(user_id, entry_date DESC);
CREATE INDEX IF NOT EXISTS idx_trade_journal_symbol ON trade_journal(user_id, symbol);
CREATE INDEX IF NOT EXISTS idx_alerts_user_status ON alerts(user_id, status);
CREATE INDEX IF NOT EXISTS idx_alerts_expires ON alerts(expires_at) WHERE status = 'active';

-- Apply updated_at triggers to new tables
CREATE TRIGGER update_options_strategies_updated_at BEFORE UPDATE ON options_strategies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_trade_journal_updated_at BEFORE UPDATE ON trade_journal
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_alerts_updated_at BEFORE UPDATE ON alerts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create functions for common analytics queries

-- Function to calculate portfolio performance metrics
CREATE OR REPLACE FUNCTION calculate_portfolio_metrics(
    p_user_id UUID,
    p_start_date DATE DEFAULT NULL,
    p_end_date DATE DEFAULT CURRENT_DATE
)
RETURNS TABLE (
    total_return NUMERIC,
    annualized_return NUMERIC,
    volatility NUMERIC,
    sharpe_ratio NUMERIC,
    max_drawdown NUMERIC,
    win_rate NUMERIC
) AS $$
DECLARE
    v_start_date DATE;
BEGIN
    -- Default to 1 year ago if no start date provided
    v_start_date := COALESCE(p_start_date, p_end_date - INTERVAL '1 year');
    
    RETURN QUERY
    WITH daily_returns AS (
        SELECT 
            date,
            total_value,
            LAG(total_value) OVER (ORDER BY date) as prev_value,
            CASE 
                WHEN LAG(total_value) OVER (ORDER BY date) > 0 
                THEN (total_value - LAG(total_value) OVER (ORDER BY date)) / LAG(total_value) OVER (ORDER BY date)
                ELSE 0 
            END as daily_return
        FROM portfolio_performance
        WHERE user_id = p_user_id 
        AND date BETWEEN v_start_date AND p_end_date
        ORDER BY date
    ),
    performance_stats AS (
        SELECT 
            COUNT(*) as trading_days,
            AVG(daily_return) as avg_daily_return,
            STDDEV(daily_return) as daily_volatility,
            MIN(total_value) as min_value,
            MAX(total_value) as max_value,
            FIRST_VALUE(total_value) OVER (ORDER BY date) as start_value,
            LAST_VALUE(total_value) OVER (ORDER BY date ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as end_value
        FROM daily_returns
        WHERE daily_return IS NOT NULL
    )
    SELECT 
        -- Total return
        CASE WHEN start_value > 0 THEN (end_value - start_value) / start_value ELSE 0 END,
        -- Annualized return (assuming 252 trading days per year)
        CASE WHEN trading_days > 0 AND start_value > 0 
             THEN POWER((end_value / start_value), (252.0 / trading_days)) - 1 
             ELSE 0 END,
        -- Volatility (annualized)
        COALESCE(daily_volatility * SQRT(252), 0),
        -- Sharpe ratio (assuming 2% risk-free rate)
        CASE WHEN daily_volatility > 0 
             THEN (avg_daily_return * 252 - 0.02) / (daily_volatility * SQRT(252))
             ELSE 0 END,
        -- Max drawdown
        CASE WHEN max_value > 0 THEN (max_value - min_value) / max_value ELSE 0 END,
        -- Win rate (simplified for portfolio level)
        CASE WHEN trading_days > 0 
             THEN (SELECT COUNT(*) * 100.0 / trading_days FROM daily_returns WHERE daily_return > 0)
             ELSE 0 END
    FROM performance_stats;
END;
$$ LANGUAGE plpgsql;

-- Function to get options expiry summary
CREATE OR REPLACE FUNCTION get_options_expiry_summary(p_user_id UUID)
RETURNS TABLE (
    expiring_this_week INTEGER,
    expiring_next_week INTEGER,
    expiring_this_month INTEGER,
    expiring_next_month INTEGER,
    total_positions INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*) FILTER (WHERE days_to_expiry <= 7)::INTEGER,
        COUNT(*) FILTER (WHERE days_to_expiry > 7 AND days_to_expiry <= 14)::INTEGER,
        COUNT(*) FILTER (WHERE days_to_expiry <= 30)::INTEGER,
        COUNT(*) FILTER (WHERE days_to_expiry > 30 AND days_to_expiry <= 60)::INTEGER,
        COUNT(*)::INTEGER
    FROM options_positions 
    WHERE user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;