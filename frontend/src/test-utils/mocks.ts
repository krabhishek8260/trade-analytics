import { HistoricalOptionsOrder, OptionPosition, PaginatedOptionsOrdersResponse, OptionsSummary } from '@/lib/api'

// Mock data for testing
export const mockOptionsOrder: HistoricalOptionsOrder = {
  order_id: 'test-order-123',
  chain_symbol: 'AAPL',
  underlying_symbol: 'AAPL',
  strike_price: 150,
  expiration_date: '2024-12-20',
  option_type: 'call',
  transaction_side: 'buy',
  position_effect: 'open',
  direction: 'debit',
  quantity: 1,
  price: 5.50,
  premium: 5.50,
  processed_premium: 550,
  processed_premium_direction: 'debit',
  state: 'filled',
  created_at: '2024-01-15T10:30:00Z',
  updated_at: '2024-01-15T10:35:00Z',
  type: 'limit',
  legs_count: 1,
  legs_details: [],
  executions_count: 1,
  strategy: 'long_call'
}

export const mockMultiLegOrder: HistoricalOptionsOrder = {
  order_id: 'test-spread-456',
  chain_symbol: 'TSLA',
  underlying_symbol: 'TSLA',
  strike_price: 200,
  expiration_date: '2024-12-20',
  option_type: 'call',
  transaction_side: 'buy',
  position_effect: 'open',
  direction: 'debit',
  quantity: 1,
  price: 10.00,
  premium: 10.00,
  processed_premium: 1000,
  processed_premium_direction: 'debit',
  state: 'filled',
  created_at: '2024-01-15T11:00:00Z',
  updated_at: '2024-01-15T11:05:00Z',
  type: 'limit',
  legs_count: 2,
  legs_details: [
    {
      leg_index: 0,
      id: 'leg-1',
      side: 'buy',
      position_effect: 'open',
      option_type: 'call',
      strike_price: 200,
      expiration_date: '2024-12-20',
      long_strategy_code: '',
      short_strategy_code: ''
    },
    {
      leg_index: 1,
      id: 'leg-2',
      side: 'sell',
      position_effect: 'open',
      option_type: 'call',
      strike_price: 210,
      expiration_date: '2024-12-20',
      long_strategy_code: '',
      short_strategy_code: ''
    }
  ],
  executions_count: 2,
  strategy: 'call_spread'
}

export const mockOptionPosition: OptionPosition = {
  chain_symbol: 'AAPL',
  strike_price: 150,
  expiration_date: '2024-12-20',
  option_type: 'call',
  transaction_side: 'buy',
  position_effect: 'open',
  direction: 'debit',
  quantity: 1,
  contracts: 1,
  position_type: 'long',
  average_price: 5.50,
  current_price: 6.00,
  market_value: 600,
  total_cost: 550,
  total_return: 50,
  percent_change: 9.09,
  days_to_expiry: 45,
  strategy: 'long_call',
  greeks: {
    delta: 0.65,
    gamma: 0.05,
    theta: -0.02,
    vega: 0.15,
    rho: 0.08,
    implied_volatility: 0.25,
    open_interest: 1000
  }
}

export const mockPaginatedOrdersResponse: PaginatedOptionsOrdersResponse = {
  data: [mockOptionsOrder, mockMultiLegOrder],
  pagination: {
    page: 1,
    limit: 20,
    total: 2,
    total_pages: 1,
    has_next: false,
    has_prev: false
  },
  filters_applied: {
    state: 'filled',
    sort_by: 'created_at',
    sort_order: 'desc'
  },
  data_source: 'database'
}

export const mockOptionsSummary: OptionsSummary = {
  total_positions: 5,
  total_value: 10000,
  total_cost: 9500,
  total_return: 500,
  total_return_percent: 5.26,
  long_positions: 3,
  short_positions: 2,
  calls_count: 4,
  puts_count: 1,
  expiring_this_week: 1,
  expiring_this_month: 3,
  winners: 3,
  losers: 2,
  win_rate: 60,
  strategies: {
    'long_call': 2,
    'call_spread': 1,
    'iron_condor': 1,
    'covered_call': 1
  },
  positions: [mockOptionPosition]
}

// API Response mocks
export const createMockApiResponse = <T>(data: T) => ({
  success: true,
  data,
  message: null,
  timestamp: new Date().toISOString()
})

// Error response mock
export const mockApiError = {
  success: false,
  data: null,
  message: 'API Error occurred',
  timestamp: new Date().toISOString()
}

// Mock functions for testing
export const mockApiCalls = {
  getOptionsOrders: jest.fn().mockResolvedValue(mockPaginatedOrdersResponse),
  getOptionsSummary: jest.fn().mockResolvedValue(mockOptionsSummary),
  getOptionsOrdersSyncStatus: jest.fn().mockResolvedValue({
    user_id: 'test-user',
    total_orders: 100,
    last_sync: '2024-01-15T10:00:00Z',
    last_order_date: '2024-01-15T10:30:00Z',
    needs_sync: false,
    sync_reason: 'Up to date',
    sync_status: 'up_to_date'
  }),
  triggerOptionsOrdersSync: jest.fn().mockResolvedValue({
    orders_processed: 10,
    orders_stored: 10,
    sync_time: '2024-01-15T11:00:00Z',
    sync_type: 'incremental'
  })
}