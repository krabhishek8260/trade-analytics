-- SQL script to update latest_position in chain_data for all rolled_options_chains
-- This extracts the latest position from roll_details.open_position

UPDATE rolled_options_chains
SET chain_data = jsonb_set(
    chain_data,
    '{latest_position}',
    jsonb_build_object(
        'strike_price', (chain_data->'orders'->-1->'roll_details'->'open_position'->>'strike_price')::float,
        'option_type', upper(chain_data->'orders'->-1->'roll_details'->'open_position'->>'option_type'),
        'expiration_date', chain_data->'orders'->-1->'roll_details'->'open_position'->>'expiration_date',
        'side', lower(chain_data->'orders'->-1->'roll_details'->'open_position'->>'side'),
        'quantity', (chain_data->'orders'->-1->>'quantity')::float,
        'last_updated', chain_data->'orders'->-1->>'created_at'
    )
),
updated_at = NOW()
WHERE user_id = '123e4567-e89b-12d3-a456-426614174000'
  AND chain_data->'orders'->-1->'roll_details'->'open_position' IS NOT NULL;

-- Check results
SELECT 
    underlying_symbol,
    chain_data->'latest_position' as latest_position
FROM rolled_options_chains 
WHERE user_id = '123e4567-e89b-12d3-a456-426614174000'
LIMIT 5;