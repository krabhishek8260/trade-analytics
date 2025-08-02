-- Options P&L Analytics Performance Indexes
-- Adds indexes specifically designed for P&L calculation queries

-- Index for P&L calculations on options_orders
-- Used for: user-specific filled orders with premium data, sorted by fill time
CREATE INDEX IF NOT EXISTS idx_options_orders_pnl_calc 
ON options_orders (user_id, filled_at, underlying_symbol, position_effect)
WHERE state = 'filled' AND processed_premium IS NOT NULL;

-- Index for chain-based P&L calculations (for rolled positions)
-- Used for: matching orders by chain_id for comprehensive P&L tracking
CREATE INDEX IF NOT EXISTS idx_options_orders_chain_pnl 
ON options_orders (user_id, chain_id, filled_at)
WHERE chain_id IS NOT NULL AND state = 'filled';

-- Index for yearly P&L analysis
-- Used for: year-over-year P&L breakdown queries
CREATE INDEX IF NOT EXISTS idx_options_orders_year_pnl 
ON options_orders (user_id, EXTRACT(YEAR FROM filled_at), underlying_symbol)
WHERE state = 'filled' AND filled_at IS NOT NULL;

-- Index for symbol-specific P&L queries
-- Used for: symbol-level P&L aggregation and trade drilling
CREATE INDEX IF NOT EXISTS idx_options_orders_symbol_pnl
ON options_orders (user_id, underlying_symbol, position_effect, filled_at)
WHERE state = 'filled';

-- Index for position matching (strike + expiration + type)
-- Used for: matching opening and closing orders for the same option contract
CREATE INDEX IF NOT EXISTS idx_options_orders_position_match
ON options_orders (user_id, underlying_symbol, strike_price, expiration_date, option_type, position_effect)
WHERE state = 'filled';

-- Index for options_positions P&L calculations
-- Used for: unrealized P&L calculations and current portfolio value
CREATE INDEX IF NOT EXISTS idx_options_positions_pnl_calc
ON options_positions (user_id, underlying_symbol, total_return)
WHERE total_return IS NOT NULL;

-- Index for position analysis by expiration
-- Used for: expiry-based analysis and risk management
CREATE INDEX IF NOT EXISTS idx_options_positions_expiry_analysis
ON options_positions (user_id, expiration_date, total_return)
WHERE total_return IS NOT NULL;

-- Composite index for comprehensive position queries
-- Used for: complex position filtering and analysis
CREATE INDEX IF NOT EXISTS idx_options_positions_comprehensive
ON options_positions (user_id, underlying_symbol, option_type, expiration_date, total_return);

-- Index for transaction-based analysis
-- Used for: buy/sell transaction analysis and strategy breakdown
CREATE INDEX IF NOT EXISTS idx_options_orders_transaction_analysis
ON options_orders (user_id, transaction_side, direction, underlying_symbol, filled_at)
WHERE state = 'filled';

-- Index for premium-based queries
-- Used for: cost basis and premium analysis
CREATE INDEX IF NOT EXISTS idx_options_orders_premium_analysis
ON options_orders (user_id, processed_premium_direction, processed_premium, filled_at)
WHERE processed_premium IS NOT NULL AND state = 'filled';

-- Partial index for multi-leg strategy analysis
-- Used for: complex strategy P&L calculations
CREATE INDEX IF NOT EXISTS idx_options_orders_multileg
ON options_orders (user_id, strategy, legs_count, filled_at)
WHERE legs_count > 1 AND state = 'filled';

-- Index for execution-based analysis
-- Used for: execution quality and timing analysis
CREATE INDEX IF NOT EXISTS idx_options_orders_execution_analysis
ON options_orders (user_id, executions_count, filled_at, total_cost)
WHERE executions_count > 0 AND state = 'filled';

-- Comments explaining the rationale for each index:

-- Performance indexes for P&L calculations are critical because:
-- 1. P&L calculations involve complex matching of opening/closing orders
-- 2. Queries often filter by user_id, symbol, date ranges, and order state
-- 3. Sorting by fill time is common for FIFO matching algorithms
-- 4. Chain-based queries are essential for tracking rolled positions
-- 5. Year-based aggregations are frequently requested for tax and performance analysis

-- These indexes are designed to support the specific query patterns in:
-- - OptionsPnLService.calculate_total_pnl()
-- - OptionsPnLService.calculate_yearly_pnl()
-- - OptionsPnLService.calculate_symbol_pnl()
-- - OptionsPnLService.get_symbol_trades()
-- - OptionsPnLBackgroundService._match_opening_closing_orders_optimized()

-- Index maintenance notes:
-- - These are partial indexes where possible to reduce storage overhead
-- - WHERE clauses filter out non-essential rows (unfilled orders, null premiums)
-- - Composite indexes are ordered by selectivity (user_id first, then more specific fields)
-- - Expression indexes (EXTRACT(YEAR...)) are used for common date-based queries