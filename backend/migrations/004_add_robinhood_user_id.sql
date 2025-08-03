-- Migration to add robinhood_user_id field to users table
-- This allows us to store the actual Robinhood API user ID for better consistency

-- Add robinhood_user_id column to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS robinhood_user_id VARCHAR(255);

-- Create index on robinhood_user_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_robinhood_user_id ON users(robinhood_user_id);

-- Add comment to document the field
COMMENT ON COLUMN users.robinhood_user_id IS 'Stores the actual Robinhood API user ID for consistent user identification'; 