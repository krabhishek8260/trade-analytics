# Options P&L Analytics - Implementation Plan

## Overview

This document outlines the comprehensive implementation plan for adding Options Profit & Loss (P&L) analytics to the tradeanalytics-v2 application. The feature will provide detailed realized and unrealized P&L calculations over all time, broken down by year, with symbol-level drill-downs showing individual trades.

## Business Requirements

### Core Features
1. **Total P&L Summary**: Display overall realized and unrealized profit/loss
2. **Year-over-Year Breakdown**: Show P&L performance by calendar year
3. **Symbol-Level Analysis**: Aggregate P&L by underlying symbol
4. **Trade-Level Details**: Drill down to individual trades for each symbol
5. **Interactive UI**: Clickable charts and tables for exploration

### User Stories
- As a trader, I want to see my total options P&L so I can understand my overall performance
- As a trader, I want to see yearly breakdowns so I can track performance trends over time
- As a trader, I want to see which symbols are most/least profitable
- As a trader, I want to click on a symbol to see all individual trades for that symbol
- As a trader, I want to filter results by date ranges and symbols

## Technical Architecture

### Data Sources
The implementation will utilize existing data models:
- **`options_orders`**: Historical order data with executed trades
- **`options_positions`**: Current open positions for unrealized P&L
- **`rolled_options_chain`**: For tracking rolled positions and chains

### Key Data Fields
From `options_orders` table:
- `processed_premium` and `processed_premium_direction`: Accurate cost basis
- `chain_id`: For linking related orders (rolls, closes)
- `underlying_symbol`: For symbol-level aggregation
- `created_at`, `filled_at`: For time-based analysis
- `position_effect`: "open" vs "close" for P&L matching
- `legs`: Multi-leg strategy details

From `options_positions` table:
- `total_return`: Current unrealized P&L
- `market_value`, `total_cost`: For validation and calculation

## Backend Implementation

### 1. API Endpoints

#### `/api/v1/options/pnl/summary`
- **Method**: GET
- **Description**: Overall P&L summary with realized/unrealized breakdown
- **Response**:
```json
{
  "total_pnl": 12500.00,
  "realized_pnl": 8200.00,
  "unrealized_pnl": 4300.00,
  "total_trades": 156,
  "winning_trades": 89,
  "losing_trades": 67,
  "win_rate": 57.05,
  "largest_winner": 2400.00,
  "largest_loser": -1800.00,
  "avg_trade_pnl": 80.13,
  "time_period": {
    "start_date": "2023-01-01",
    "end_date": "2025-07-31"
  }
}
```

#### `/api/v1/options/pnl/by-year`
- **Method**: GET
- **Query Parameters**: `start_year`, `end_year`
- **Description**: Year-over-year P&L breakdown
- **Response**:
```json
{
  "yearly_breakdown": [
    {
      "year": 2023,
      "realized_pnl": 3200.00,
      "unrealized_pnl": 0.00,
      "total_pnl": 3200.00,
      "trade_count": 45,
      "win_rate": 62.22
    },
    {
      "year": 2024,
      "realized_pnl": 5000.00,
      "unrealized_pnl": 0.00,
      "total_pnl": 5000.00,
      "trade_count": 78,
      "win_rate": 55.13
    },
    {
      "year": 2025,
      "realized_pnl": 0.00,
      "unrealized_pnl": 4300.00,
      "total_pnl": 4300.00,
      "trade_count": 33,
      "win_rate": 54.55
    }
  ]
}
```

#### `/api/v1/options/pnl/by-symbol`
- **Method**: GET
- **Query Parameters**: `year`, `limit`, `sort_by`, `sort_order`
- **Description**: Symbol-level P&L aggregation
- **Response**:
```json
{
  "symbol_performance": [
    {
      "symbol": "AAPL",
      "total_pnl": 2400.00,
      "realized_pnl": 1800.00,
      "unrealized_pnl": 600.00,
      "trade_count": 23,
      "win_rate": 65.22,
      "avg_trade_pnl": 104.35,
      "largest_winner": 850.00,
      "largest_loser": -320.00
    }
  ]
}
```

#### `/api/v1/options/pnl/trades/{symbol}`
- **Method**: GET
- **Query Parameters**: `year`, `trade_type` (realized/unrealized)
- **Description**: Individual trades for a specific symbol
- **Response**:
```json
{
  "symbol": "AAPL",
  "trades": [
    {
      "trade_id": "chain_12345",
      "strategy": "LONG CALL",
      "open_date": "2025-06-15",
      "close_date": "2025-07-20",
      "strike_price": 150.00,
      "expiration_date": "2025-08-15",
      "option_type": "call",
      "contracts": 5,
      "opening_premium": -750.00,
      "closing_premium": 1200.00,
      "pnl": 450.00,
      "pnl_percentage": 60.00,
      "days_held": 35,
      "status": "realized"
    }
  ]
}
```

### 2. Service Layer (`backend/app/services/options_pnl_service.py`)

#### Core Functions

```python
class OptionsPnLService:
    async def calculate_total_pnl(self, user_id: UUID) -> Dict[str, Any]
    async def calculate_yearly_pnl(self, user_id: UUID, start_year: int = None, end_year: int = None) -> Dict[str, Any]
    async def calculate_symbol_pnl(self, user_id: UUID, year: int = None) -> Dict[str, Any]
    async def get_symbol_trades(self, user_id: UUID, symbol: str, year: int = None) -> Dict[str, Any]
    
    # Helper functions
    async def _calculate_realized_pnl(self, user_id: UUID) -> List[Dict]
    async def _calculate_unrealized_pnl(self, user_id: UUID) -> List[Dict]
    async def _match_opening_closing_orders(self, orders: List[OptionsOrder]) -> List[Dict]
    async def _handle_multi_leg_strategies(self, orders: List[OptionsOrder]) -> Dict[str, Any]
    async def _handle_rolled_positions(self, chain_id: str, orders: List[OptionsOrder]) -> Dict[str, Any]
```

#### P&L Calculation Logic

##### Realized P&L Calculation
1. **Order Matching**: Match opening and closing orders by:
   - `chain_id` (for rolled positions)
   - `underlying_symbol` + `strike_price` + `expiration_date` + `option_type`
2. **Premium Calculation**: Use `processed_premium` and `processed_premium_direction`
3. **P&L Formula**: 
   ```
   For LONG positions: PnL = (Closing Premium - Opening Premium) * contracts * 100
   For SHORT positions: PnL = (Opening Premium - Closing Premium) * contracts * 100
   ```
4. **Multi-leg Handling**: Sum individual leg P&L for complex strategies

##### Unrealized P&L Calculation
1. **Current Positions**: Query `options_positions` table
2. **Use Existing Data**: Leverage `total_return` field
3. **Validation**: Cross-reference with `market_value` and `total_cost`

##### Chain Handling for Rolled Positions
1. **Chain Tracking**: Use `chain_id` to group related orders
2. **Net P&L**: Calculate cumulative P&L across all orders in chain
3. **Roll Attribution**: Track each roll's contribution to total P&L

### 3. Database Optimizations

#### New Indexes
```sql
-- Performance indexes for P&L queries
CREATE INDEX IF NOT EXISTS idx_options_orders_pnl_calc 
ON options_orders (user_id, filled_at, underlying_symbol, position_effect);

CREATE INDEX IF NOT EXISTS idx_options_orders_chain_pnl 
ON options_orders (user_id, chain_id, filled_at);

CREATE INDEX IF NOT EXISTS idx_options_orders_year_pnl 
ON options_orders (user_id, EXTRACT(YEAR FROM filled_at), underlying_symbol);
```

#### Potential Materialized View (Future Optimization)
```sql
-- For frequently accessed P&L calculations
CREATE MATERIALIZED VIEW options_pnl_summary AS
SELECT 
    user_id,
    underlying_symbol,
    EXTRACT(YEAR FROM filled_at) as year,
    SUM(CASE WHEN position_effect = 'close' THEN processed_premium ELSE 0 END) as realized_pnl,
    COUNT(*) as trade_count
FROM options_orders 
WHERE state = 'filled'
GROUP BY user_id, underlying_symbol, EXTRACT(YEAR FROM filled_at);
```

## Frontend Implementation

### 1. New Page Structure

#### Main P&L Page (`frontend/src/app/dashboard/pnl/page.tsx`)
- **Layout**: Full-width dashboard layout
- **Sections**:
  - Summary cards at top
  - Year-over-year chart
  - Symbol performance table
  - Filters sidebar

### 2. Component Architecture

#### Summary Components (`frontend/src/components/pnl/`)

##### `PnLSummaryCards.tsx`
```tsx
interface PnLSummaryProps {
  totalPnL: number
  realizedPnL: number
  unrealizedPnL: number
  winRate: number
  totalTrades: number
}

export const PnLSummaryCards: React.FC<PnLSummaryProps>
```

##### `YearlyPnLChart.tsx`
```tsx
interface YearlyChartProps {
  yearlyData: YearlyPnL[]
  onYearClick: (year: number) => void
}

export const YearlyPnLChart: React.FC<YearlyChartProps>
```
- **Chart Library**: Recharts (consistent with existing codebase)
- **Chart Type**: Combined bar/line chart showing P&L and trade count
- **Interactivity**: Click year to filter symbol table

##### `SymbolPnLTable.tsx`
```tsx
interface SymbolTableProps {
  symbolData: SymbolPnL[]
  onSymbolClick: (symbol: string) => void
  sortBy: string
  sortOrder: 'asc' | 'desc'
  onSort: (field: string) => void
}

export const SymbolPnLTable: React.FC<SymbolTableProps>
```
- **Features**: Sortable columns, clickable rows
- **Columns**: Symbol, Total P&L, Realized, Unrealized, Trade Count, Win Rate
- **Styling**: Consistent with existing table components

##### `TradeDetailsModal.tsx`
```tsx
interface TradeModalProps {
  isOpen: boolean
  symbol: string
  trades: TradeDetail[]
  onClose: () => void
}

export const TradeDetailsModal: React.FC<TradeModalProps>
```
- **Modal Library**: Headless UI (consistent with existing modals)
- **Content**: Detailed trade list with expand/collapse for trade details
- **Features**: Export to CSV, filter by trade type

### 3. API Integration (`frontend/src/lib/api.ts`)

#### New API Functions
```typescript
export interface PnLSummary {
  total_pnl: number
  realized_pnl: number
  unrealized_pnl: number
  total_trades: number
  win_rate: number
  // ... other fields
}

export interface YearlyPnL {
  year: number
  realized_pnl: number
  unrealized_pnl: number
  total_pnl: number
  trade_count: number
  win_rate: number
}

export interface SymbolPnL {
  symbol: string
  total_pnl: number
  realized_pnl: number
  unrealized_pnl: number
  trade_count: number
  win_rate: number
  avg_trade_pnl: number
}

export interface TradeDetail {
  trade_id: string
  strategy: string
  open_date: string
  close_date?: string
  strike_price: number
  expiration_date: string
  option_type: string
  contracts: number
  opening_premium: number
  closing_premium?: number
  pnl: number
  pnl_percentage: number
  status: 'realized' | 'unrealized'
}

// API Functions
export async function getPnLSummary(): Promise<PnLSummary>
export async function getYearlyPnL(startYear?: number, endYear?: number): Promise<YearlyPnL[]>
export async function getSymbolPnL(year?: number): Promise<SymbolPnL[]>
export async function getSymbolTrades(symbol: string, year?: number): Promise<TradeDetail[]>
```

### 4. Navigation Integration

#### Update Main Dashboard
- Add "P&L Analytics" tab to main navigation
- Update routing in `frontend/src/app/dashboard/page.tsx`
- Add P&L summary card to main dashboard overview

## Implementation Timeline

### Phase 1: Backend Foundation (Week 1)
- [ ] Create `OptionsPnLService` class
- [ ] Implement basic P&L calculation logic
- [ ] Add database indexes
- [ ] Create API endpoints
- [ ] Write unit tests for P&L calculations

### Phase 2: Frontend Basic Implementation (Week 2) 
- [ ] Create P&L page and basic components
- [ ] Implement API integration
- [ ] Add summary cards and basic table
- [ ] Integrate with main dashboard navigation

### Phase 3: Advanced Features (Week 3)
- [ ] Add interactive yearly chart
- [ ] Implement symbol drill-down modal
- [ ] Add filtering and sorting capabilities
- [ ] Implement export functionality

### Phase 4: Polish & Optimization (Week 4)
- [ ] Performance optimization and caching
- [ ] Comprehensive testing
- [ ] Error handling and edge cases
- [ ] Documentation and user guides

## Testing Strategy

### Backend Testing
1. **Unit Tests**: P&L calculation logic with known data sets
2. **Integration Tests**: API endpoints with realistic data
3. **Performance Tests**: Large dataset handling
4. **Edge Case Tests**: Complex multi-leg strategies, rolled positions

### Frontend Testing
1. **Component Tests**: Individual component functionality
2. **Integration Tests**: API integration and data flow
3. **E2E Tests**: Complete user workflows
4. **Visual Tests**: Chart rendering and responsiveness

## Performance Considerations

### Backend Optimizations
- Database indexing on key query fields
- Caching frequently accessed calculations
- Pagination for large result sets
- Background jobs for heavy calculations

### Frontend Optimizations
- Virtual scrolling for large trade lists
- Memoization of expensive calculations
- Lazy loading of detailed trade data
- Efficient re-rendering with React optimization

## Risk Mitigation

### Data Accuracy Risks
- **Validation**: Cross-reference with existing `total_return` calculations
- **Testing**: Comprehensive testing with known P&L scenarios
- **Audit Trail**: Log all P&L calculations for verification

### Performance Risks
- **Monitoring**: Add performance monitoring for P&L endpoints
- **Fallbacks**: Graceful degradation for large datasets
- **Caching**: Implement robust caching strategy

### User Experience Risks
- **Loading States**: Clear loading indicators for calculations
- **Error Handling**: Informative error messages
- **Progressive Enhancement**: Basic functionality first, advanced features second

## Success Metrics

### Functional Metrics
- [ ] Accurate P&L calculations validated against manual calculations
- [ ] All API endpoints respond within 5 seconds for typical datasets
- [ ] Frontend components render without errors
- [ ] Complete user workflows function end-to-end

### Performance Metrics
- [ ] P&L summary loads within 2 seconds
- [ ] Symbol breakdown loads within 3 seconds
- [ ] Trade details modal opens within 1 second
- [ ] Page remains responsive with 1000+ trades

### User Experience Metrics
- [ ] Intuitive navigation between summary and details
- [ ] Clear visual distinction between realized/unrealized P&L
- [ ] Responsive design works on mobile devices
- [ ] Export functionality works reliably

## Future Enhancements

### Advanced Analytics
- Sharpe ratio and other performance metrics
- Comparison with benchmark indices
- Risk-adjusted returns analysis
- Monthly and quarterly breakdowns

### Visualization Improvements
- Advanced charting with technical indicators
- Heat maps for symbol performance
- Interactive timeline for trade visualization
- Performance attribution analysis

### Integration Features
- Tax reporting integration
- Export to accounting software
- API for third-party tools
- Real-time P&L updates

---

This document serves as the definitive guide for implementing the Options P&L Analytics feature. All implementation decisions should reference this plan, and updates to requirements should be reflected in this document.