# Enhanced Rolled Options Chains Database Process

## Overview
This document describes the correct process for regenerating and inserting enhanced rolled options chains into the database. Enhanced chains include single-leg opening orders found through backward tracing, providing complete chain histories.

## Key Components

### 1. Enhanced Chain Detection Algorithm
- **File**: `app/services/rolled_options_chain_detector.py`
- **Key Method**: `_trace_backwards_for_chain_starts()`
- **Enhanced Feature**: Finds original opening orders by searching debug data files for matching single-leg orders

### 2. Database Models
- **Main Table**: `rolled_options_chains`
- **Sync Status**: `user_rolled_options_sync`
- **User ID**: `123e4567-e89b-12d3-a456-426614174000` (test user)

### 3. Data Sources
- **Debug Data**: `/backend/debug_data/*options_orders*.json` files
- **Content**: Raw Robinhood API responses with all historical orders
- **Enhanced Detection**: Uses this full dataset to find opening orders missing from current processing window

## Methods to Insert Enhanced Chains

### Method 1: Manual Sync via API (RECOMMENDED)
```bash
# Trigger background processing with enhanced detection
curl -X POST "http://localhost:8000/api/v1/rolled-options-v2/sync"

# Wait 30-60 seconds for processing
sleep 30

# Verify chains are inserted
curl "http://localhost:8000/api/v1/rolled-options-v2/chains" | jq '.data.summary'
```

**Pros**: 
- Uses production code path
- Handles all sync status updates
- Works with existing cron service
- Includes proper error handling

**Cons**: 
- May not use enhanced backward tracing (depends on cron service implementation)

### Method 2: Direct Python Script (FOR TESTING)
```bash
python force_insert_chains.py
```

**Script Details**:
- Loads orders from debug data files
- Runs enhanced chain detection with backward tracing
- Uses synchronous database operations
- Commits each chain individually
- Provides detailed logging

**Pros**: 
- Guaranteed to use enhanced detection algorithm
- Direct control over the process
- Detailed logging for debugging

**Cons**: 
- Bypasses sync status updates
- Manual process only
- May not be visible to API if sync status is wrong

### Method 3: Force API Sync (CURRENT WORKING METHOD)
```bash
# Delete existing chains for clean slate
python -c "
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker
import sys
from pathlib import Path
sys.path.insert(0, str(Path('.').absolute()))
from app.models.rolled_options_chain import RolledOptionsChain

engine = create_engine('postgresql://postgres:postgres@localhost:5432/tradeanalytics')
Session = sessionmaker(bind=engine)
user_id = '123e4567-e89b-12d3-a456-426614174000'

with Session() as session:
    result = session.execute(delete(RolledOptionsChain).where(RolledOptionsChain.user_id == user_id))
    session.commit()
    print(f'Deleted {result.rowcount} chains')
"

# Trigger fresh sync
curl -X POST "http://localhost:8000/api/v1/rolled-options-v2/sync"
```

## Current Status & Issue

**Problem**: The cron service may not be using the enhanced backward tracing algorithm.

**Evidence**: 
- Manual script finds 69 enhanced chains with single-leg opening orders
- API sync generates 77 chains but they start with roll orders
- Enhanced backward tracing logic exists but may not be used by cron service

**Investigation Needed**:
1. Check if `RolledOptionsCronService` uses enhanced detection
2. Verify data source (debug files vs database orders)
3. Ensure backward tracing is enabled in production code path

## Verification Steps

### Check Database Contents
```bash
python debug_user_chains.py
```

### Check API Response
```bash
curl "http://localhost:8000/api/v1/rolled-options-v2/chains" | jq '.data.summary'
```

### Check for Enhanced Chains (Single-leg Opening Orders)
```bash
curl "http://localhost:8000/api/v1/rolled-options-v2/chains?symbol=HOOD" | jq '.data.chains[0].orders[0].legs | length'
# Should return 1 for single-leg opening order
# Should have position_effect: "open"
```

## Expected Results

**Enhanced Chain Example**:
- **HOOD CALL Chain**: Should start with single-leg opening order
- **Opening Order**: `$45.0 CALL 2025-05-16` from `2025-04-09`
- **Chain Length**: 6 total orders (1 opening + 5 rolls)
- **Total Enhanced**: ~43 out of 69 chains should start with opening orders

**Summary Metrics**:
- Total chains: 69-77 (depending on detection method)
- Enhanced chains: ~43 starting with single-leg opening orders
- Complete chain histories from actual opening orders

## Troubleshooting

### Database Empty After Script
- Check database connection string
- Verify Docker containers are running
- Check user ID matches API expectations

### API Returns Empty Chains
- Trigger manual sync via API
- Check sync status in `user_rolled_options_sync` table
- Verify processing completed successfully

### Chains Don't Show Single-leg Opening Orders
- Cron service may not use enhanced backward tracing
- Debug data files may not be accessible to cron service
- Enhanced detection logic may not be enabled in production path

## Next Steps

1. **Verify Enhanced Detection in Cron Service**: Check if backward tracing is used
2. **Fix Data Source**: Ensure cron service accesses debug data files
3. **Enable Enhanced Mode**: Add flag or configuration for enhanced detection
4. **Test Complete Flow**: Verify API sync generates enhanced chains with opening orders