# Options Portfolio Value Calculation Guide

## Overview

This document explains how options portfolio values are calculated in the Trade Analytics application, ensuring accurate representation of both long positions (assets) and short positions (liabilities).

## Core Principles

### 1. Market Value Definition
- **Market Value**: Always positive, represents the current market price of the position
- **Long Positions**: Market value = what you can sell the options for (asset)
- **Short Positions**: Market value = what it costs to buy back the options (liability)

### 2. Portfolio Net Value Formula
```
Net Portfolio Value = Long Positions Value - Short Positions Value
```

### 3. Position Types

#### Long Positions (Assets)
- **Definition**: Options you bought (paid debit)
- **Market Value**: `contracts × current_price × 100`
- **Total Cost**: `contracts × purchase_price × 100` (positive)
- **P&L**: `market_value - total_cost`

#### Short Positions (Liabilities)  
- **Definition**: Options you sold (received credit)
- **Market Value**: `contracts × current_price × 100` 
- **Total Cost**: `-(contracts × credit_received × 100)` (negative)
- **P&L**: `credit_received - market_value`

## Calculation Examples

### Example 1: Simple Positions

**Position A (Long AAPL Calls)**
- Bought 10 contracts at $5.00
- Current price: $7.00
- Market Value: 10 × $7.00 × 100 = **$7,000** (asset)
- Total Cost: 10 × $5.00 × 100 = **$5,000** (debit paid)
- P&L: $7,000 - $5,000 = **+$2,000**

**Position B (Short TSLA Puts)**
- Sold 5 contracts at $8.00
- Current price: $3.00
- Market Value: 5 × $3.00 × 100 = **$1,500** (liability)
- Total Cost: -(5 × $8.00 × 100) = **-$4,000** (credit received)
- P&L: $4,000 - $1,500 = **+$2,500**

**Portfolio Net Value**: $7,000 - $1,500 = **$5,500**
**Total P&L**: $2,000 + $2,500 = **$4,500**

### Example 2: Option Spread

**Bull Call Spread on NVDA**

**Long Leg (Buy 140 Call)**
- Bought 1 contract at $10.00
- Current price: $12.00
- Market Value: 1 × $12.00 × 100 = **$1,200** (asset)
- Total Cost: 1 × $10.00 × 100 = **$1,000** (debit)
- P&L: $1,200 - $1,000 = **+$200**

**Short Leg (Sell 145 Call)**
- Sold 1 contract at $7.00  
- Current price: $5.00
- Market Value: 1 × $5.00 × 100 = **$500** (liability)
- Total Cost: -(1 × $7.00 × 100) = **-$700** (credit)
- P&L: $700 - $500 = **+$200**

**Spread Net Value**: $1,200 - $500 = **$700**
**Total Spread P&L**: $200 + $200 = **$400**

## Implementation Details

### Backend Calculation (Python)

```python
def calculate_portfolio_value(positions):
    total_long_value = 0
    total_short_value = 0
    total_return = 0
    
    for position in positions:
        market_value = position.get("market_value", 0)
        position_type = position.get("position_type", "")
        total_return += position.get("total_return", 0)
        
        if position_type == "long":
            # Long positions are assets
            total_long_value += market_value
        else:
            # Short positions are liabilities  
            total_short_value += market_value
    
    # Net portfolio value = Assets - Liabilities
    net_portfolio_value = total_long_value - total_short_value
    
    return {
        "total_value": net_portfolio_value,
        "long_value": total_long_value,
        "short_value": total_short_value,
        "total_return": total_return
    }
```

### Individual Position Calculation

```python
def calculate_position_metrics(position_data):
    contracts = abs(position_data["quantity"])
    current_price = position_data["current_price"]
    position_type = position_data["type"]  # "long" or "short"
    
    # Market value is always positive
    market_value = contracts * current_price * 100
    
    if position_type == "long":
        # Long position: you paid debit
        average_price = position_data["average_price"]
        total_cost = contracts * average_price * 100
        total_return = market_value - total_cost
    else:
        # Short position: you received credit
        credit_received = abs(position_data["average_price"])
        total_cost = -(contracts * credit_received * 100)
        total_return = (contracts * credit_received * 100) - market_value
    
    return {
        "market_value": market_value,
        "total_cost": total_cost,
        "total_return": total_return,
        "position_type": position_type
    }
```

## Why This Approach is Correct

### 1. Financial Accuracy
- **Long positions** represent money you can receive (assets)
- **Short positions** represent money you owe (liabilities)
- Net value shows true portfolio worth

### 2. Spread Handling
- Multi-leg strategies automatically calculate correctly
- Each leg valued independently then netted
- Proper risk representation

### 3. P&L Consistency  
- Long P&L: current value - money paid
- Short P&L: money received - current obligation
- Matches actual trading profit/loss

## Common Mistakes to Avoid

### ❌ Wrong: Adding All Market Values
```python
# INCORRECT - treats liabilities as assets
total_value = sum(position["market_value"] for position in positions)
```

### ✅ Correct: Netting Assets and Liabilities
```python
# CORRECT - proper portfolio accounting
long_value = sum(pos["market_value"] for pos in positions if pos["position_type"] == "long")
short_value = sum(pos["market_value"] for pos in positions if pos["position_type"] == "short")
net_value = long_value - short_value
```

## Validation and Testing

### Test Cases Covered
1. **Simple long positions** - buying calls/puts
2. **Simple short positions** - selling calls/puts  
3. **Mixed portfolios** - combination of long and short
4. **Option spreads** - multi-leg strategies
5. **Edge cases** - empty portfolios, all long, all short

### Expected Behaviors
- Portfolio value decreases when short position prices increase
- Portfolio value increases when long position prices increase
- Spread values reflect net exposure correctly
- P&L calculations match actual trading outcomes

## Debug Information

The application logs detailed calculation breakdowns:

```
Options Portfolio Calculation:
  Long positions value (assets): $507,137.00
  Short positions value (liabilities): $297,609.00  
  Net portfolio value: $209,528.00
  Total cost basis: $488,133.00
  Total return: $88,521.00
```

This helps verify calculations and troubleshoot any discrepancies.

## API Response Format

```json
{
  "total_positions": 30,
  "total_value": 209528.0,
  "total_return": 88521.0,
  "total_return_percent": 18.13,
  "long_positions": 18,
  "short_positions": 12
}
```

The `total_value` field represents the correctly calculated net portfolio value using the methodology described in this document.