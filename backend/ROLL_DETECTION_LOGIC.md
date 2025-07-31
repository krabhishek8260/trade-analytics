# Rolled Options Chain Detection Logic

This document defines the precise logic for detecting rolled options chains to ensure consistency and proper validation across all implementations.

## Core Principles

### 1. Chain Separation Requirements
- **Symbol Separation**: Each chain must contain orders for only ONE underlying symbol
- **Option Type Separation**: Calls and puts must NEVER be mixed in the same chain
- **Time Window**: Orders in a chain must be within 8 months of each other
- **Valid Orders Only**: Only process `state == 'filled'` orders

### 2. Proper Roll Sequence Patterns

#### Sell-to-Open Chain Pattern:
```
1. Initial Order: SELL TO OPEN (1 leg) - Opens short position
   - position_effect = 'open'
   - side = 'sell'
   - Single leg only

2. Roll Orders: BUY TO CLOSE (old) + SELL TO OPEN (new) (2 legs)
   - Leg 1: position_effect = 'close', side = 'buy' (closes previous position)
   - Leg 2: position_effect = 'open', side = 'sell' (opens new position)
   - Must close exact strike/expiration from previous order
   - New position can have different strike (rolling up/down)

3. Final Order: BUY TO CLOSE (1 leg) - Closes final position
   - position_effect = 'close'
   - side = 'buy'
   - Must match final open position exactly
```

#### Buy-to-Open Chain Pattern:
```
1. Initial Order: BUY TO OPEN (1 leg) - Opens long position
   - position_effect = 'open'
   - side = 'buy'
   - Single leg only

2. Roll Orders: SELL TO CLOSE (old) + BUY TO OPEN (new) (2 legs)
   - Leg 1: position_effect = 'close', side = 'sell' (closes previous position)
   - Leg 2: position_effect = 'open', side = 'buy' (opens new position)
   - Must close exact strike/expiration from previous order
   - New position can have different strike (rolling up/down)

3. Final Order: SELL TO CLOSE (1 leg) - Closes final position
   - position_effect = 'close'
   - side = 'sell'
   - Must match final open position exactly
```

### 3. Position Matching Rules

#### Exact Match Requirements:
- `strike_price`: Must be exactly equal (no tolerance)
- `option_type`: Must be exactly equal ('call' or 'put')
- `expiration_date`: Must be exactly equal
- `side`: Must be opposite (open 'sell' -> close 'buy')

#### Roll Tolerance (Middle Orders Only):
- Strike prices can change between rolls (rolling up/down)
- Expiration dates can change between rolls (rolling forward)
- Option type must remain the same throughout chain

### 4. Order Identification

#### Roll Order Indicators:
- `form_source == 'strategy_roll'` (Auto-rolled by Robinhood)
- `strategy` contains 'calendar_spread'
- `strategy` contains 'roll'

#### Chain Start Indicators:
- Single leg with `position_effect == 'open'`
- No closing legs in the order
- Must have valid strike, expiration, and option type

### 5. Validation Requirements

#### Chain Validation:
1. **Minimum Length**: At least 2 orders
2. **First Order**: Must have opens, no closes
3. **Middle Orders**: Must have both opens and closes
4. **Last Order**: Can have closes only, or both opens and closes
5. **Position Continuity**: Each close must match a previously opened position
6. **Option Type Consistency**: All legs must be same option type (call or put)
7. **Symbol Consistency**: All orders must be for same underlying symbol

#### Invalid Chain Patterns:
- Single order chains
- Orders with only opens and no closes (except first order)
- Orders that close positions not opened in the chain
- Mixed option types (calls and puts together)
- Mixed underlying symbols
- Time gaps > 8 months between orders
- Canceled or non-filled orders

### 6. Implementation Algorithm

#### Step 1: Order Filtering
```python
# Filter for valid orders
valid_orders = [
    order for order in all_orders
    if (order.get('state') == 'filled' and
        order.get('legs') and 
        len(order.get('legs')) > 0)
]
```

#### Step 2: Group by Symbol and Option Type
```python
# Group by symbol_optiontype to prevent mixing
groups = {}
for order in valid_orders:
    symbol = order.get('chain_symbol') or order.get('underlying_symbol')
    option_type = order['legs'][0]['option_type']
    key = f"{symbol}_{option_type}"
    groups[key] = groups.get(key, []) + [order]
```

#### Step 3: Identify Roll Orders
```python
# Find orders with roll indicators
roll_orders = [
    order for order in valid_orders
    if (order.get('form_source') == 'strategy_roll' or
        'calendar_spread' in order.get('strategy', '') or
        'roll' in order.get('strategy', ''))
]
```

#### Step 4: Build Chains with Position Tracking
```python
# For each group, build chains by tracking position opens/closes
for group_key, group_orders in groups.items():
    chains = build_position_tracked_chains(group_orders)
    validate_each_chain(chains)
```

#### Step 5: Position Effect Analysis
```python
# Analyze each order's position effects
def analyze_order(order):
    opens = []
    closes = []
    for leg in order['legs']:
        if leg['position_effect'] == 'open':
            opens.append(leg)
        elif leg['position_effect'] == 'close':
            closes.append(leg)
    return {'opens': opens, 'closes': closes}
```

#### Step 6: Chain Linking
```python
# Link orders by matching closes to opens
def build_chain(start_order, all_orders):
    chain = [start_order]
    open_positions = start_order['opens']
    
    for next_order in subsequent_orders:
        if closes_any_position(next_order, open_positions):
            chain.append(next_order)
            update_open_positions(open_positions, next_order)
            
    return chain if len(chain) >= 2 else None
```

### 7. Common Issues to Avoid

#### Mixing Option Types:
- ❌ Chain contains both calls and puts
- ✅ Separate chains for calls and puts

#### Incorrect Position Matching:
- ❌ Closing positions not opened in the chain
- ✅ Each close matches an exact previous open

#### Invalid Sequences:
- ❌ All orders show "open" with no "close"
- ✅ Proper open -> roll -> close progression

#### Grouping Unrelated Orders:
- ❌ Orders with different strikes grouped together
- ✅ Orders linked by actual position continuity

### 8. Testing Validation

#### Valid Chain Example:
```
Order 1: SELL TO OPEN 1 XYZ PUT $50 2024-01-15
Order 2: BUY TO CLOSE 1 XYZ PUT $50 2024-01-15 + SELL TO OPEN 1 XYZ PUT $55 2024-02-15
Order 3: BUY TO CLOSE 1 XYZ PUT $55 2024-02-15
```

#### Invalid Chain Example:
```
❌ Order 1: SELL TO OPEN 1 XYZ PUT $50 2024-01-15
❌ Order 2: SELL TO OPEN 1 XYZ PUT $26 2024-01-15  // No close, different strike
❌ Order 3: SELL TO OPEN 1 XYZ CALL $30 2024-01-15  // Wrong option type
```

### 9. Error Handling

#### Log Validation Failures:
- Chain validation failures with specific reasons
- Position matching failures with details
- Invalid order sequences with explanations

#### Graceful Degradation:
- Skip invalid orders rather than crashing
- Continue processing other chains if one fails
- Return partial results with error information

### 10. Performance Considerations

#### Optimization Strategies:
- Pre-filter orders by roll indicators
- Group by symbol+type before processing
- Limit chain length to prevent infinite loops
- Use early termination for invalid patterns
- Cache intermediate results where possible

---

**Last Updated**: 2025-01-30
**Version**: 1.0
**Implementation File**: `backend/app/services/rolled_options_chain_detector.py`