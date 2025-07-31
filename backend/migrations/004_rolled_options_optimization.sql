-- Migration 004: Rolled Options Optimization
-- Add chain tracking fields and indexes for improved rolled options analysis

-- Add chain tracking fields to options_orders table
ALTER TABLE options_orders 
    ADD COLUMN IF NOT EXISTS chain_id VARCHAR(100),
    ADD COLUMN IF NOT EXISTS chain_symbol VARCHAR(20),
    ADD COLUMN IF NOT EXISTS closing_strategy VARCHAR(50),
    ADD COLUMN IF NOT EXISTS opening_strategy VARCHAR(50);

-- Create indexes for efficient chain queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_options_orders_chain_id 
    ON options_orders(chain_id) 
    WHERE chain_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_options_orders_chain_symbol 
    ON options_orders(chain_symbol) 
    WHERE chain_symbol IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_options_orders_user_chain 
    ON options_orders(user_id, chain_id) 
    WHERE chain_id IS NOT NULL;

-- Composite index for rolled options queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_options_orders_rolled_analysis 
    ON options_orders(user_id, underlying_symbol, chain_id, order_created_at DESC) 
    WHERE chain_id IS NOT NULL AND chain_id != '';

-- Add comments for new fields
COMMENT ON COLUMN options_orders.chain_id IS 'Robinhood chain ID for tracking rolled options';
COMMENT ON COLUMN options_orders.chain_symbol IS 'Chain symbol for grouping related orders';
COMMENT ON COLUMN options_orders.closing_strategy IS 'Strategy used when closing position';
COMMENT ON COLUMN options_orders.opening_strategy IS 'Strategy used when opening position';

-- Update the comprehensive index to include chain fields
DROP INDEX IF EXISTS idx_options_orders_comprehensive;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_options_orders_comprehensive_v2 
    ON options_orders(user_id, underlying_symbol, state, chain_id, order_created_at DESC);

-- Create a materialized view for rolled options summary (for future performance)
-- This will be populated by a background job
CREATE MATERIALIZED VIEW IF NOT EXISTS rolled_options_summary AS
SELECT 
    user_id,
    chain_id,
    underlying_symbol,
    COUNT(*) as order_count,
    MIN(order_created_at) as first_order_date,
    MAX(order_created_at) as last_order_date,
    SUM(CASE WHEN direction = 'credit' THEN COALESCE(processed_premium, 0) ELSE 0 END) as total_credits,
    SUM(CASE WHEN direction = 'debit' THEN COALESCE(processed_premium, 0) ELSE 0 END) as total_debits,
    SUM(CASE WHEN direction = 'credit' THEN COALESCE(processed_premium, 0) ELSE -COALESCE(processed_premium, 0) END) as net_premium,
    COUNT(CASE WHEN position_effect = 'close' THEN 1 END) as close_count,
    COUNT(CASE WHEN position_effect = 'open' THEN 1 END) as open_count,
    MAX(order_created_at) as last_updated
FROM options_orders 
WHERE chain_id IS NOT NULL 
    AND chain_id != ''
    AND state = 'filled'
GROUP BY user_id, chain_id, underlying_symbol
HAVING COUNT(*) >= 2;

-- Create unique index on the materialized view
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_rolled_options_summary_pk 
    ON rolled_options_summary(user_id, chain_id);

-- Add index for efficient querying
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_rolled_options_summary_user_symbol 
    ON rolled_options_summary(user_id, underlying_symbol, last_order_date DESC);

-- Comment on the materialized view
COMMENT ON MATERIALIZED VIEW rolled_options_summary IS 'Pre-computed summary of rolled options chains for performance optimization';

-- Function to refresh the materialized view
CREATE OR REPLACE FUNCTION refresh_rolled_options_summary()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY rolled_options_summary;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT SELECT ON rolled_options_summary TO anon, authenticated;
GRANT EXECUTE ON FUNCTION refresh_rolled_options_summary() TO authenticated;