-- Migration 005: Rolled Options Background Processing
-- Add tables and infrastructure for background processing of rolled options chains

-- Table to store pre-computed rolled options chains
CREATE TABLE IF NOT EXISTS rolled_options_chains (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    chain_id VARCHAR(100) NOT NULL,
    underlying_symbol VARCHAR(10) NOT NULL,
    
    -- Chain status and metadata
    status VARCHAR(20) NOT NULL DEFAULT 'active', -- 'active', 'closed', 'expired'
    initial_strategy VARCHAR(50),
    start_date TIMESTAMP WITH TIME ZONE,
    last_activity_date TIMESTAMP WITH TIME ZONE,
    
    -- Order tracking
    total_orders INTEGER NOT NULL DEFAULT 0,
    roll_count INTEGER NOT NULL DEFAULT 0,
    
    -- Financial metrics
    total_credits_collected NUMERIC(12, 2) DEFAULT 0.0,
    total_debits_paid NUMERIC(12, 2) DEFAULT 0.0,
    net_premium NUMERIC(12, 2) DEFAULT 0.0,
    total_pnl NUMERIC(12, 2) DEFAULT 0.0,
    
    -- Full chain data as JSON for detailed analysis
    chain_data JSONB NOT NULL DEFAULT '{}',
    
    -- Summary metrics for quick access
    summary_metrics JSONB NOT NULL DEFAULT '{}',
    
    -- Processing metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT unique_user_chain UNIQUE(user_id, chain_id),
    CONSTRAINT valid_status CHECK (status IN ('active', 'closed', 'expired'))
);

-- Table to track user sync status for rolled options
CREATE TABLE IF NOT EXISTS user_rolled_options_sync (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    
    -- Processing timestamps
    last_processed_at TIMESTAMP WITH TIME ZONE,
    last_successful_sync TIMESTAMP WITH TIME ZONE,
    next_sync_after TIMESTAMP WITH TIME ZONE,
    
    -- Statistics
    total_chains INTEGER DEFAULT 0,
    active_chains INTEGER DEFAULT 0,
    closed_chains INTEGER DEFAULT 0,
    total_orders_processed INTEGER DEFAULT 0,
    
    -- Processing status
    processing_status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'error'
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- Configuration
    full_sync_required BOOLEAN DEFAULT true,
    incremental_sync_enabled BOOLEAN DEFAULT true,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_processing_status CHECK (processing_status IN ('pending', 'processing', 'completed', 'error'))
);

-- Create indexes for efficient querying
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_rolled_options_chains_user_id 
    ON rolled_options_chains(user_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_rolled_options_chains_user_symbol 
    ON rolled_options_chains(user_id, underlying_symbol);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_rolled_options_chains_status 
    ON rolled_options_chains(user_id, status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_rolled_options_chains_activity 
    ON rolled_options_chains(user_id, last_activity_date DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_rolled_options_chains_chain_id 
    ON rolled_options_chains(chain_id) 
    WHERE chain_id IS NOT NULL;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_rolled_options_sync_status 
    ON user_rolled_options_sync(processing_status);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_rolled_options_sync_next_sync 
    ON user_rolled_options_sync(next_sync_after) 
    WHERE next_sync_after IS NOT NULL;

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_rolled_options_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers to automatically update timestamps
DROP TRIGGER IF EXISTS trigger_rolled_options_chains_updated_at ON rolled_options_chains;
CREATE TRIGGER trigger_rolled_options_chains_updated_at
    BEFORE UPDATE ON rolled_options_chains
    FOR EACH ROW
    EXECUTE FUNCTION update_rolled_options_updated_at();

DROP TRIGGER IF EXISTS trigger_user_rolled_options_sync_updated_at ON user_rolled_options_sync;
CREATE TRIGGER trigger_user_rolled_options_sync_updated_at
    BEFORE UPDATE ON user_rolled_options_sync
    FOR EACH ROW
    EXECUTE FUNCTION update_rolled_options_updated_at();

-- Enhanced materialized view for better performance
DROP MATERIALIZED VIEW IF EXISTS rolled_options_summary;
CREATE MATERIALIZED VIEW rolled_options_summary AS
SELECT 
    roc.user_id,
    roc.underlying_symbol,
    COUNT(*) as total_chains,
    COUNT(CASE WHEN roc.status = 'active' THEN 1 END) as active_chains,
    COUNT(CASE WHEN roc.status = 'closed' THEN 1 END) as closed_chains,
    COUNT(CASE WHEN roc.status = 'expired' THEN 1 END) as expired_chains,
    SUM(roc.total_orders) as total_orders,
    SUM(roc.total_credits_collected) as net_premium_collected,
    SUM(roc.total_pnl) as total_pnl,
    AVG(roc.total_orders::DECIMAL) as avg_orders_per_chain,
    MIN(roc.start_date) as earliest_chain_date,
    MAX(roc.last_activity_date) as latest_activity_date,
    MAX(roc.processed_at) as last_updated
FROM rolled_options_chains roc
GROUP BY roc.user_id, roc.underlying_symbol;

-- Create unique index on the materialized view
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_rolled_options_summary_pk 
    ON rolled_options_summary(user_id, underlying_symbol);

-- Additional indexes for the materialized view
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_rolled_options_summary_user 
    ON rolled_options_summary(user_id, latest_activity_date DESC);

-- Function to refresh the materialized view concurrently
CREATE OR REPLACE FUNCTION refresh_rolled_options_summary()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY rolled_options_summary;
END;
$$ LANGUAGE plpgsql;

-- Function to get users that need rolled options processing
CREATE OR REPLACE FUNCTION get_users_needing_rolled_options_processing()
RETURNS TABLE(
    user_id UUID,
    last_processed_at TIMESTAMP WITH TIME ZONE,
    processing_status VARCHAR(20),
    full_sync_required BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        u.id,
        urs.last_processed_at,
        COALESCE(urs.processing_status, 'pending'),
        COALESCE(urs.full_sync_required, true)
    FROM users u
    LEFT JOIN user_rolled_options_sync urs ON u.id = urs.user_id
    WHERE 
        u.is_active = true
        AND (
            urs.user_id IS NULL  -- Never processed
            OR urs.processing_status = 'pending'  -- Waiting to be processed
            OR urs.processing_status = 'error'    -- Failed and needs retry
            OR (urs.next_sync_after IS NOT NULL AND urs.next_sync_after <= NOW())  -- Due for sync
        );
END;
$$ LANGUAGE plpgsql;

-- Function to update user sync status
CREATE OR REPLACE FUNCTION update_user_rolled_options_sync_status(
    p_user_id UUID,
    p_status VARCHAR(20),
    p_error_message TEXT DEFAULT NULL,
    p_total_chains INTEGER DEFAULT NULL,
    p_active_chains INTEGER DEFAULT NULL,
    p_closed_chains INTEGER DEFAULT NULL,
    p_orders_processed INTEGER DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO user_rolled_options_sync (
        user_id,
        processing_status,
        error_message,
        total_chains,
        active_chains,
        closed_chains,
        total_orders_processed,
        last_processed_at,
        last_successful_sync,
        next_sync_after,
        full_sync_required,
        retry_count,
        updated_at
    ) VALUES (
        p_user_id,
        p_status,
        p_error_message,
        COALESCE(p_total_chains, 0),
        COALESCE(p_active_chains, 0),
        COALESCE(p_closed_chains, 0),
        COALESCE(p_orders_processed, 0),
        NOW(),
        CASE WHEN p_status = 'completed' THEN NOW() ELSE NULL END,
        CASE WHEN p_status = 'completed' THEN NOW() + INTERVAL '30 minutes' ELSE NULL END,
        CASE WHEN p_status = 'completed' THEN false ELSE true END,
        CASE WHEN p_status = 'error' THEN 1 ELSE 0 END,
        NOW()
    )
    ON CONFLICT (user_id) DO UPDATE SET
        processing_status = EXCLUDED.processing_status,
        error_message = EXCLUDED.error_message,
        total_chains = COALESCE(EXCLUDED.total_chains, user_rolled_options_sync.total_chains),
        active_chains = COALESCE(EXCLUDED.active_chains, user_rolled_options_sync.active_chains),
        closed_chains = COALESCE(EXCLUDED.closed_chains, user_rolled_options_sync.closed_chains),
        total_orders_processed = COALESCE(EXCLUDED.total_orders_processed, user_rolled_options_sync.total_orders_processed),
        last_processed_at = EXCLUDED.last_processed_at,
        last_successful_sync = EXCLUDED.last_successful_sync,
        next_sync_after = EXCLUDED.next_sync_after,
        full_sync_required = EXCLUDED.full_sync_required,
        retry_count = CASE 
            WHEN EXCLUDED.processing_status = 'error' THEN user_rolled_options_sync.retry_count + 1
            WHEN EXCLUDED.processing_status = 'completed' THEN 0
            ELSE user_rolled_options_sync.retry_count
        END,
        updated_at = EXCLUDED.updated_at;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON rolled_options_chains TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON user_rolled_options_sync TO anon, authenticated;
GRANT SELECT ON rolled_options_summary TO anon, authenticated;
GRANT EXECUTE ON FUNCTION refresh_rolled_options_summary() TO authenticated;
GRANT EXECUTE ON FUNCTION get_users_needing_rolled_options_processing() TO authenticated;
GRANT EXECUTE ON FUNCTION update_user_rolled_options_sync_status(UUID, VARCHAR, TEXT, INTEGER, INTEGER, INTEGER, INTEGER) TO authenticated;

-- Add comments for documentation
COMMENT ON TABLE rolled_options_chains IS 'Pre-computed rolled options chains data for fast API responses';
COMMENT ON TABLE user_rolled_options_sync IS 'Tracks the processing status and sync metadata for each user';
COMMENT ON MATERIALIZED VIEW rolled_options_summary IS 'Aggregated summary statistics for rolled options by user and symbol';
COMMENT ON FUNCTION get_users_needing_rolled_options_processing() IS 'Returns users who need rolled options processing';
COMMENT ON FUNCTION update_user_rolled_options_sync_status(UUID, VARCHAR, TEXT, INTEGER, INTEGER, INTEGER, INTEGER) IS 'Updates the sync status for a user';