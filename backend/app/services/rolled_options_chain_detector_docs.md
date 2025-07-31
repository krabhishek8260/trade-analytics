# Rolled Options Chain Detection Algorithm Documentation

## Overview

This document explains the precise algorithms used to detect and validate rolled options chains in trading data. The system identifies when a trader has "rolled" an options position - closing an existing position and opening a new one with different terms (strike price, expiration date) to manage risk or capture additional premium.

## Chain Pattern Definitions

### 1. Sell-to-Open Chain Pattern
This pattern occurs when a trader initially sells options to open a short position, then rolls the position multiple times, and finally closes it.

```
Pattern Structure:
┌─────────────┬──────────────┬─────────────────┬──────────────┐
│ Order Type  │ Leg Count    │ Leg Details     │ Purpose      │
├─────────────┼──────────────┼─────────────────┼──────────────┤
│ Initial     │ 1 leg        │ SELL TO OPEN    │ Open short   │
│ Roll 1      │ 2 legs       │ BUY TO CLOSE +  │ Roll position│
│             │              │ SELL TO OPEN    │              │
│ Roll 2      │ 2 legs       │ BUY TO CLOSE +  │ Roll position│
│             │              │ SELL TO OPEN    │              │
│ ...         │ 2 legs       │ (more rolls)    │ Roll position│
│ Final       │ 1 leg        │ BUY TO CLOSE    │ Close short  │
└─────────────┴──────────────┴─────────────────┴──────────────┘
```

**Example Sell-to-Open Chain:**
1. Day 1: SELL TO OPEN 1 TSLA $250 Call (collect $500 premium)
2. Day 15: BUY TO CLOSE TSLA $250 Call + SELL TO OPEN TSLA $260 Call (net $200 debit)
3. Day 30: BUY TO CLOSE TSLA $260 Call + SELL TO OPEN TSLA $270 Call (net $150 debit)
4. Day 45: BUY TO CLOSE TSLA $270 Call (pay $100 premium)

**Net Result:** $500 - $200 - $150 - $100 = $50 profit

### 2. Buy-to-Open Chain Pattern
This pattern occurs when a trader initially buys options to open a long position, then rolls the position multiple times, and finally closes it.

```
Pattern Structure:
┌─────────────┬──────────────┬─────────────────┬──────────────┐
│ Order Type  │ Leg Count    │ Leg Details     │ Purpose      │
├─────────────┼──────────────┼─────────────────┼──────────────┤
│ Initial     │ 1 leg        │ BUY TO OPEN     │ Open long    │
│ Roll 1      │ 2 legs       │ SELL TO CLOSE + │ Roll position│
│             │              │ BUY TO OPEN     │              │
│ Roll 2      │ 2 legs       │ SELL TO CLOSE + │ Roll position│
│             │              │ BUY TO OPEN     │              │
│ ...         │ 2 legs       │ (more rolls)    │ Roll position│
│ Final       │ 1 leg        │ SELL TO CLOSE   │ Close long   │
└─────────────┴──────────────┴─────────────────┴──────────────┘
```

**Example Buy-to-Open Chain:**
1. Day 1: BUY TO OPEN 1 AAPL $150 Put (pay $300 premium)
2. Day 15: SELL TO CLOSE AAPL $150 Put + BUY TO OPEN AAPL $145 Put (net $100 credit)
3. Day 30: SELL TO CLOSE AAPL $145 Put + BUY TO OPEN AAPL $140 Put (net $50 credit)
4. Day 45: SELL TO CLOSE AAPL $140 Put (collect $400 premium)

**Net Result:** -$300 + $100 + $50 + $400 = $250 profit

## Validation Rules

### 1. Pattern Validation

#### First Order Rules:
- Must have exactly 1 leg
- Must be an OPEN order (position_effect = 'open')
- Must be either SELL TO OPEN or BUY TO OPEN
- Determines the chain type for all subsequent validation

#### Middle Order Rules (Rolls):
- Must have exactly 2 legs
- Must have 1 CLOSE leg and 1 OPEN leg
- For Sell-to-Open chains: BUY TO CLOSE + SELL TO OPEN
- For Buy-to-Open chains: SELL TO CLOSE + BUY TO OPEN
- CLOSE leg must exactly match the previous order's OPEN leg

#### Final Order Rules:
- Can have 1 leg (final close) OR 2 legs (final roll that stays open)
- If 1 leg: must be opposite of initial order
  - Sell-to-Open chain → BUY TO CLOSE
  - Buy-to-Open chain → SELL TO CLOSE
- If 2 legs: follows same rules as middle orders

### 2. Strike Price Matching Rules

#### Exact Matching for Closes:
When closing a position, the strike price must match exactly with the position being closed.

```python
# Example: If we SELL TO OPEN TSLA $250 Call
# The closing order must BUY TO CLOSE TSLA $250 Call (same strike)

current_open_leg = {
    'strike_price': 250.0,
    'option_type': 'call',
    'expiration_date': '2024-01-19'
}

valid_close_leg = {
    'strike_price': 250.0,  # Must match exactly
    'option_type': 'call',   # Must match exactly
    'expiration_date': '2024-01-19'  # Must match exactly
}
```

#### Rolling Strike Prices:
When rolling a position, the new OPEN leg can have a different strike price (rolling up or down).

```python
# Valid roll example:
# Close: BUY TO CLOSE TSLA $250 Call
# Open:  SELL TO OPEN TSLA $260 Call (rolled up $10)

roll_order = {
    'closes': [{
        'strike_price': 250.0,  # Matches previous open
        'option_type': 'call'
    }],
    'opens': [{
        'strike_price': 260.0,  # Different strike (roll up)
        'option_type': 'call'   # Same option type
    }]
}
```

### 3. Time Window Constraints

#### Maximum Chain Duration:
Chains cannot span more than 8 months (240 days) from first to last order.

```python
max_chain_duration = timedelta(days=240)  # 8 months

def validate_time_window(chain):
    first_order_time = chain[0].created_at
    last_order_time = chain[-1].created_at
    duration = last_order_time - first_order_time
    
    return duration <= max_chain_duration
```

#### Order Sequencing:
Orders must be chronologically sequential - each order must come after the previous one.

### 4. Symbol and Option Type Consistency

#### Symbol Matching:
All orders in a chain must be for the same underlying symbol.

```python
# Valid chain - all TSLA
orders = [
    {'underlying_symbol': 'TSLA', ...},
    {'underlying_symbol': 'TSLA', ...},
    {'underlying_symbol': 'TSLA', ...}
]

# Invalid chain - mixed symbols
orders = [
    {'underlying_symbol': 'TSLA', ...},
    {'underlying_symbol': 'AAPL', ...},  # Different symbol!
    {'underlying_symbol': 'TSLA', ...}
]
```

#### Option Type Consistency:
All legs in a chain must be the same option type (all calls or all puts).

```python
# Valid chain - all calls
chain_orders = [
    {'legs': [{'option_type': 'call'}]},
    {'legs': [{'option_type': 'call'}, {'option_type': 'call'}]},
    {'legs': [{'option_type': 'call'}]}
]
```

## Financial Calculations

### 1. Premium Calculations

#### Credits and Debits:
Each order has a direction (credit or debit) and a processed premium amount.

```python
def calculate_chain_financials(chain):
    total_credits = 0.0
    total_debits = 0.0
    
    for order in chain:
        direction = order.get('direction', '')
        premium = float(order.get('processed_premium', 0) or 0)
        
        if direction == 'credit':
            total_credits += premium
        elif direction == 'debit':
            total_debits += premium
    
    net_premium = total_credits - total_debits
    return {
        'total_credits_collected': total_credits,
        'total_debits_paid': total_debits,
        'net_premium': net_premium
    }
```

#### Example Calculation:
```
Order 1: SELL TO OPEN  → $500 credit
Order 2: Roll          → $200 debit  
Order 3: Roll          → $150 debit
Order 4: BUY TO CLOSE  → $100 debit

Total Credits: $500
Total Debits:  $450
Net Premium:   $50 profit
```

### 2. P&L Calculations

#### Current Implementation:
For now, P&L equals net premium collected. This will be enhanced to include unrealized gains/losses based on current market prices.

```python
def calculate_pnl(chain, current_market_data=None):
    net_premium = calculate_net_premium(chain)
    
    # Future enhancement: add unrealized P&L for active chains
    if current_market_data and chain_status == 'active':
        unrealized_pnl = calculate_unrealized_pnl(chain, current_market_data)
        total_pnl = net_premium + unrealized_pnl
    else:
        total_pnl = net_premium
    
    return total_pnl
```

### 3. Chain Status Determination

#### Status Rules:
- **Active**: Chain ends with 2-leg order (still has open position)
- **Closed**: Chain ends with 1-leg CLOSE order (position fully closed)
- **Expired**: Open position has expired (future enhancement)

```python
def determine_chain_status(chain):
    last_order = chain[-1]
    
    if len(last_order['legs']) == 1 and last_order['closes']:
        return 'closed'  # Final close order
    elif len(last_order['legs']) == 2:
        return 'active'  # Still has open position
    else:
        return 'unknown'
```

## Algorithm Flow

### 1. Order Analysis Phase
```
Input: Raw options orders
↓
Parse and validate each order
↓
Extract leg information (strike, type, expiration, side, effect)
↓
Create OrderInfo objects with structured data
```

### 2. Grouping Phase
```
OrderInfo objects
↓
Group by underlying_symbol + option_type
↓
Sort each group chronologically
↓
Grouped orders ready for chain detection
```

### 3. Chain Detection Phase
```
For each group:
  ↓
  Find potential chain starts (1-leg OPEN orders)
  ↓
  For each start:
    ↓
    Build chain by following pattern rules
    ↓
    Validate complete chain
    ↓
    If valid, add to results
```

### 4. Validation Phase
```
For each detected chain:
  ↓
  Validate pattern structure
  ↓
  Validate strike price matching
  ↓
  Validate time constraints
  ↓
  Validate symbol/type consistency
  ↓
  Calculate financial metrics
```

## Error Handling

### 1. Malformed Data
- Skip orders with missing required fields
- Log warnings for partial data
- Continue processing remaining orders

### 2. Invalid Patterns
- Log detected but invalid chains for debugging
- Don't include partial chains in results
- Provide detailed validation failure reasons

### 3. Performance Limits
- Limit maximum chain length (prevent infinite loops)
- Timeout protection for large datasets
- Memory usage monitoring

## Performance Considerations

### 1. Time Complexity
- Order analysis: O(n) where n = number of orders
- Grouping: O(n log n) due to sorting
- Chain detection: O(n²) worst case per group
- Overall: O(n²) where n = orders in largest group

### 2. Memory Usage
- Linear memory usage relative to input size
- Temporary OrderInfo objects created for processing
- Result chains contain references to original order data

### 3. Optimization Strategies
- Early termination for invalid patterns
- Efficient data structures for lookups
- Caching of frequently accessed data
- Background processing to avoid user-facing delays

## Testing Strategy

### 1. Unit Tests
- Test individual functions with known inputs
- Validate edge cases and error conditions
- Test financial calculations with precise examples

### 2. Integration Tests
- Test complete chain detection with real data
- Validate complex multi-roll scenarios
- Test performance with large datasets

### 3. Validation Tests
- Compare results with manually identified chains
- Verify financial calculations match broker statements
- Test boundary conditions (8-month limits, etc.)