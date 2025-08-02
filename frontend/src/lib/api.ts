/**
 * API client functions for interacting with the backend
 */

const API_BASE = '/api/backend'

interface ApiResponse<T> {
  success?: boolean
  data?: T
  message?: string
  detail?: string
}

interface ListResponse<T> {
  data: T[]
  count: number
  total: number
}

export interface PortfolioSummary {
  total_value: number
  total_return: number
  day_return: number
  raw_data?: any
}

export interface StockPosition {
  symbol: string
  quantity: number
  average_buy_price: number
  current_price: number
  market_value: number
  total_cost: number
  total_return: number
  percent_change: number
}

export interface OptionPosition {
  underlying_symbol: string
  strike_price: number
  expiration_date: string
  option_type: string
  transaction_side: string
  position_effect: string
  direction: string
  quantity: number
  contracts: number
  position_type: string
  average_price: number
  current_price: number
  market_value: number
  total_cost: number
  total_return: number
  percent_change: number
  days_to_expiry: number
  strategy: string
  greeks?: {
    delta: number
    gamma: number
    theta: number
    vega: number
    rho: number
    implied_volatility: number
    open_interest: number
  }
  // Chain information (optional, included when chains are requested)
  chain_id?: string | null
  is_latest_in_chain?: boolean
  chain_roll_count?: number
  chain_total_pnl?: number
  chain_status?: string
  chain_net_premium?: number
  chain_start_date?: string
  chain_total_orders?: number
}

export interface StocksSummary {
  total_positions: number
  total_value: number
  total_cost: number
  total_return: number
  total_return_percent: number
  winners: number
  losers: number
  win_rate: number
  positions: StockPosition[]
}

export interface OptionsPnLAnalytics {
  total_pnl: number
  realized_pnl: number
  unrealized_pnl: number
  total_trades: number
  realized_trades: number
  open_positions: number
  win_rate: number
  largest_winner: number
  largest_loser: number
  avg_trade_pnl: number
}

// P&L Analytics interfaces for the new P&L service
export interface PnLSummary {
  total_pnl: number
  realized_pnl: number
  unrealized_pnl: number
  total_trades: number
  winning_trades: number
  losing_trades: number
  win_rate: number
  largest_winner: number
  largest_loser: number
  avg_trade_pnl: number
  time_period: {
    start_date: string | null
    end_date: string
  }
  calculation_info?: {
    status: string
    message?: string
    last_calculated?: string
  }
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
  total_trades: number
  winning_trades: number
  losing_trades: number
  win_rate: number
  avg_trade_pnl: number
  largest_winner?: number
  largest_loser?: number
}

export interface TradeDetail {
  trade_id: string
  strategy: string
  open_date: string | null
  close_date?: string | null
  strike_price: number
  expiration_date: string | null
  option_type: string
  contracts: number
  opening_premium: number
  closing_premium?: number
  pnl: number
  pnl_percentage?: number
  days_held?: number | null
  status: 'realized' | 'unrealized'
}

export interface YearlyPerformance {
  year: number
  realized_pnl: number
  trade_count: number
  winning_trades: number
  losing_trades: number
  win_rate: number
}

export interface SymbolPerformance {
  symbol: string
  total_pnl: number
  realized_pnl: number
  unrealized_pnl: number
  total_trades: number
  realized_trades: number
  open_positions: number
  winning_trades: number
  losing_trades: number
  win_rate: number
  avg_trade_pnl: number
}

export interface OptionsSummary {
  total_positions: number
  total_value: number
  total_cost: number
  total_return: number
  total_return_percent: number
  long_positions: number
  short_positions: number
  calls_count: number
  puts_count: number
  expiring_this_week: number
  expiring_this_month: number
  winners: number
  losers: number
  win_rate: number
  strategies: Record<string, any>
  positions: OptionPosition[]
  
  // Enhanced P&L Analytics
  pnl_analytics?: OptionsPnLAnalytics
  yearly_performance?: YearlyPerformance[]
  top_symbols?: SymbolPerformance[]
}

export interface PortfolioGreeks {
  net_delta: number
  net_gamma: number
  net_theta: number
  net_vega: number
  net_rho: number
  total_positions: number
  long_delta: number
  short_delta: number
  daily_theta_decay: number
  vega_exposure: number
  delta_neutral: boolean
  theta_positive: boolean
}

// Rolled Options Types - Chain ID Based
export interface OptionsOrder {
  order_id: string
  underlying_symbol?: string
  chain_symbol?: string
  strike_price: number
  expiration_date: string
  option_type: string
  transaction_side: string
  position_effect: string
  direction: string
  quantity: number
  price: number
  premium: number
  processed_premium: number
  processed_premium_direction: string
  state: string
  created_at: string
  updated_at: string
  strategy: string
  chain_id: string
  closing_strategy?: string
  opening_strategy?: string
  legs?: Array<{
    strike_price: number
    option_type: string
    expiration_date: string
    side: string
    position_effect: string
    quantity: number
  }>
  roll_details?: {
    type: 'roll'
    close_position: {
      strike_price: number
      option_type: string
      expiration_date: string
      side: string
    }
    open_position: {
      strike_price: number
      option_type: string
      expiration_date: string
      side: string
    }
  }
}

export interface OptionsChain {
  chain_id: string
  underlying_symbol: string
  initial_strategy: string
  start_date: string
  last_activity_date: string
  status: string // "active", "closed", "unknown"
  total_orders: number
  total_credits_collected: number
  total_debits_paid: number
  net_premium: number
  total_pnl: number
  orders: OptionsOrder[]
  roll_count: number
}

export interface RolledOptionsSummary {
  total_chains: number
  active_chains: number
  closed_chains: number
  total_orders: number
  net_premium_collected: number
  total_pnl: number
  avg_orders_per_chain: number
  most_active_symbol: string | null
  symbol_distribution: Record<string, number>
}

export interface RolledOptionsResponse {
  chains: OptionsChain[]
  summary: RolledOptionsSummary
  pagination?: {
    page: number
    limit: number
    total_chains: number
    total_pages: number
    has_next: boolean
    has_prev: boolean
  }
  filters_applied: {
    symbol?: string
    status?: string
    min_orders?: number
  }
  analysis_period_days: number
  total_chains_found?: number
  rolled_chains_identified?: number
  filtered_chains_count: number
}

export interface HistoricalOptionsOrder {
  order_id: string
  underlying_symbol: string
  strike_price: number
  expiration_date: string
  option_type: string
  transaction_side: string
  position_effect: string
  direction: string
  quantity: number
  price: number
  premium: number
  processed_premium: number
  processed_premium_direction: string
  state: string
  created_at: string
  updated_at: string
  type: string
  legs_count: number
  legs_details: any[]
  executions_count: number
  strategy?: string
}

export interface TickerPerformance {
  symbol: string
  total_trades: number
  total_return: number
  total_cost: number
  return_percentage: number
  win_rate: number
  winners: number
  losers: number
  avg_return_per_trade: number
  current_positions: number
  historical_positions: number
}

class ApiError extends Error {
  constructor(public statusCode: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

async function apiRequest<T>(endpoint: string, timeout: number = 60000): Promise<T> {
  try {
    // Create an AbortController for timeout handling
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), timeout)
    
    const response = await fetch(`${API_BASE}${endpoint}`, {
      signal: controller.signal,
      headers: {
        'Cache-Control': 'no-cache',
      }
    })
    
    clearTimeout(timeoutId)
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      const message = errorData.detail || errorData.message || `HTTP ${response.status}`
      throw new ApiError(response.status, message)
    }
    
    const data = await response.json()
    return data
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    if (error && typeof error === 'object' && 'name' in error && error.name === 'AbortError') {
      throw new ApiError(408, 'Request timeout - try reducing the date range or use pagination')
    }
    throw new ApiError(0, error instanceof Error ? error.message : 'Network error')
  }
}

// Portfolio API functions
export async function getPortfolioSummary(): Promise<PortfolioSummary> {
  const response = await apiRequest<ApiResponse<PortfolioSummary>>('/portfolio/summary')
  if (!response.data) {
    throw new ApiError(500, 'No portfolio data received')
  }
  return response.data
}

// Stocks API functions
export async function getStockPositions(): Promise<StockPosition[]> {
  const response = await apiRequest<ListResponse<StockPosition>>('/stocks/positions')
  return response.data || []
}

export async function getStocksSummary(): Promise<StocksSummary> {
  const response = await apiRequest<ApiResponse<StocksSummary>>('/stocks/summary')
  if (!response.data) {
    throw new ApiError(500, 'No stocks summary data received')
  }
  return response.data
}

// Options API functions
export async function getOptionsPositions(): Promise<OptionPosition[]> {
  const response = await apiRequest<ListResponse<OptionPosition>>('/options/positions')
  return response.data || []
}

export async function getOptionsSummary(includeChains: boolean = false): Promise<OptionsSummary> {
  const url = includeChains ? '/options/summary?include_chains=true' : '/options/summary'
  const response = await apiRequest<ApiResponse<OptionsSummary>>(url)
  if (!response.data) {
    throw new ApiError(500, 'No options summary data received')
  }
  return response.data
}

export async function getPortfolioGreeks(): Promise<PortfolioGreeks> {
  const response = await apiRequest<ApiResponse<PortfolioGreeks>>('/options/greeks')
  if (!response.data) {
    throw new ApiError(500, 'No portfolio Greeks data received')
  }
  return response.data
}

// Historical Options Orders API
export async function getOptionsOrders(params?: {
  limit?: number
  days_back?: number
  underlying_symbol?: string
  state?: string
  strategy?: string
  option_type?: string
  transaction_side?: string
}): Promise<HistoricalOptionsOrder[]> {
  const queryParams = new URLSearchParams()
  if (params?.limit) queryParams.append('limit', params.limit.toString())
  if (params?.days_back) queryParams.append('days_back', params.days_back.toString())
  if (params?.underlying_symbol) queryParams.append('underlying_symbol', params.underlying_symbol)
  if (params?.state) queryParams.append('state', params.state)
  if (params?.strategy) queryParams.append('strategy', params.strategy)
  if (params?.option_type) queryParams.append('option_type', params.option_type)
  if (params?.transaction_side) queryParams.append('transaction_side', params.transaction_side)
  
  const url = `/options/orders${queryParams.toString() ? '?' + queryParams.toString() : ''}`
  const response = await apiRequest<ListResponse<HistoricalOptionsOrder>>(url)
  return response.data || []
}

// Closed Options History API
export interface ClosedOptionsPosition {
  underlying_symbol: string
  chain_id: string
  initial_strategy: string
  start_date: string
  close_date: string
  total_orders: number
  roll_count: number
  total_credits_collected: number
  total_debits_paid: number
  net_premium: number
  total_pnl: number
  final_strike?: number
  final_expiry?: string
  final_option_type?: string
  days_held?: number
  win_loss: 'win' | 'loss'
  enhanced_chain?: boolean
  chain_type?: 'enhanced' | 'regular'
}

export async function getClosedOptionsHistory(params?: {
  limit?: number
  days_back?: number
  underlying_symbol?: string
  strategy?: string
  option_type?: string
  sort_by?: string
  sort_order?: string
  include_chains?: boolean
}): Promise<ClosedOptionsPosition[]> {
  const queryParams = new URLSearchParams()
  if (params?.limit) queryParams.append('limit', params.limit.toString())
  if (params?.days_back) queryParams.append('days_back', params.days_back.toString())
  if (params?.underlying_symbol) queryParams.append('underlying_symbol', params.underlying_symbol)
  if (params?.strategy) queryParams.append('strategy', params.strategy)
  if (params?.option_type) queryParams.append('option_type', params.option_type)
  if (params?.sort_by) queryParams.append('sort_by', params.sort_by)
  if (params?.sort_order) queryParams.append('sort_order', params.sort_order)
  if (params?.include_chains !== undefined) queryParams.append('include_chains', params.include_chains.toString())
  
  const url = `/options/history${queryParams.toString() ? '?' + queryParams.toString() : ''}`
  const response = await apiRequest<ListResponse<ClosedOptionsPosition>>(url)
  return response.data || []
}

// Performance Analysis by Ticker
export async function getTickerPerformance(symbol?: string): Promise<TickerPerformance[]> {
  const url = symbol ? `/options/analysis/${symbol}` : '/options/analysis/performance'
  const response = await apiRequest<ApiResponse<TickerPerformance[]>>(url)
  if (!response.data) {
    throw new ApiError(500, 'No ticker performance data received')
  }
  return Array.isArray(response.data) ? response.data : [response.data]
}

// Filtered Options Positions
export async function getFilteredOptionsPositions(params?: {
  underlying_symbol?: string
  option_type?: string
  strategy?: string
  position_type?: string
  expiring_days?: number
  sort_by?: string
  sort_order?: string
}): Promise<OptionPosition[]> {
  const queryParams = new URLSearchParams()
  if (params?.underlying_symbol) queryParams.append('underlying_symbol', params.underlying_symbol)
  if (params?.option_type) queryParams.append('option_type', params.option_type)
  if (params?.strategy) queryParams.append('strategy', params.strategy)
  if (params?.position_type) queryParams.append('position_type', params.position_type)
  if (params?.expiring_days) queryParams.append('expiring_days', params.expiring_days.toString())
  if (params?.sort_by) queryParams.append('sort_by', params.sort_by)
  if (params?.sort_order) queryParams.append('sort_order', params.sort_order)
  
  const url = `/options/positions${queryParams.toString() ? '?' + queryParams.toString() : ''}`
  const response = await apiRequest<ListResponse<OptionPosition>>(url)
  return response.data || []
}

// Rolled Options API functions
export async function getRolledOptionsChains(params?: {
  days_back?: number
  symbol?: string
  status?: 'active' | 'closed' | 'expired'
  min_rolls?: number
  page?: number
  limit?: number
}): Promise<RolledOptionsResponse> {
  const queryParams = new URLSearchParams()
  if (params?.days_back) queryParams.append('days_back', params.days_back.toString())
  if (params?.symbol) queryParams.append('symbol', params.symbol)
  if (params?.status) queryParams.append('status', params.status)
  if (params?.min_rolls) queryParams.append('min_rolls', params.min_rolls.toString())
  if (params?.page) queryParams.append('page', params.page.toString())
  if (params?.limit) queryParams.append('limit', params.limit.toString())
  
  const url = `/rolled-options-v2/chains${queryParams.toString() ? '?' + queryParams.toString() : ''}`
  
  // Use dynamic timeout based on days_back and pagination
  // Rolled options processing is complex and can take longer
  let timeout = 120000 // Default 2 minutes
  
  if (params?.days_back) {
    if (params.days_back <= 30) {
      timeout = params?.page ? 60000 : 120000 // 1-2 minutes for small range
    } else if (params.days_back <= 90) {
      timeout = params?.page ? 120000 : 180000 // 2-3 minutes for medium range
    } else {
      timeout = params?.page ? 180000 : 300000 // 3-5 minutes for large range
    }
  }
  const response = await apiRequest<ApiResponse<RolledOptionsResponse>>(url, timeout)
  if (!response.data) {
    throw new ApiError(500, 'No rolled options data received')
  }
  return response.data
}

export async function getRolledOptionsChainDetails(chainId: string): Promise<OptionsChain> {
  const response = await apiRequest<ApiResponse<OptionsChain>>(`/rolled-options-v2/chains/${chainId}`)
  if (!response.data) {
    throw new ApiError(500, 'No chain details received')
  }
  return response.data
}

export async function getRolledOptionsSummary(daysBack?: number): Promise<RolledOptionsSummary> {
  const queryParams = new URLSearchParams()
  if (daysBack) queryParams.append('days_back', daysBack.toString())
  
  const url = `/rolled-options-v2/summary${queryParams.toString() ? '?' + queryParams.toString() : ''}`
  const response = await apiRequest<ApiResponse<RolledOptionsSummary>>(url)
  if (!response.data) {
    throw new ApiError(500, 'No rolled options summary received')
  }
  return response.data
}

export async function getSymbolRolledChains(symbol: string, params?: {
  days_back?: number
  status?: 'active' | 'closed' | 'expired'
}): Promise<RolledOptionsResponse> {
  const queryParams = new URLSearchParams()
  if (params?.days_back) queryParams.append('days_back', params.days_back.toString())
  if (params?.status) queryParams.append('status', params.status)
  
  const url = `/rolled-options-v2/symbols/${symbol}/chains${queryParams.toString() ? '?' + queryParams.toString() : ''}`
  const response = await apiRequest<ApiResponse<RolledOptionsResponse>>(url)
  if (!response.data) {
    throw new ApiError(500, 'No symbol rolled chains data received')
  }
  return response.data
}

// Auth API functions
export async function checkAuthStatus(): Promise<{authenticated: boolean, username?: string, message: string}> {
  const response = await apiRequest<ApiResponse<{authenticated: boolean, username?: string, message: string}>>('/auth/status')
  if (!response.data) {
    throw new ApiError(500, 'No auth status data received')
  }
  return response.data
}

// Combined dashboard data fetch
export async function getDashboardData(includeChains: boolean = false) {
  try {
    const [portfolioSummary, stocksSummary, optionsSummary] = await Promise.all([
      getPortfolioSummary().catch(err => {
        console.warn('Failed to fetch portfolio summary:', err)
        return null
      }),
      getStocksSummary().catch(err => {
        console.warn('Failed to fetch stocks summary:', err)
        return null
      }),
      getOptionsSummary(includeChains).catch(err => {
        console.warn('Failed to fetch options summary:', err)
        return null
      })
    ])

    return {
      portfolio: portfolioSummary,
      stocks: stocksSummary,
      options: optionsSummary
    }
  } catch (error) {
    console.error('Error fetching dashboard data:', error)
    throw error
  }
}

// Breakdown API types and functions
export enum GroupingType {
  SYMBOL = "symbol",
  STRATEGY = "strategy",
  EXPIRY = "expiry",
  GREEKS = "greeks",
  POSITION_TYPE = "position_type"
}

export enum SortType {
  VALUE = "value",
  RETURN = "return",
  PERCENTAGE = "percentage",
  ALPHABETICAL = "alphabetical",
  DATE = "date"
}

export interface PositionBreakdown {
  position_id: string
  underlying_symbol: string
  option_type: string
  strike_price: number
  expiration_date: string
  contracts: number
  market_value: number
  total_cost: number
  total_return: number
  percent_change: number
  strategy: string
}

export interface BreakdownComponent {
  id: string
  name: string
  display_name: string
  value: number
  percentage: number
  position_count: number
  component_type: string
  underlying_symbol?: string
  strategy?: string
  positions: PositionBreakdown[]
  total_return: number
  return_percentage: number
  market_value: number
  cost_basis: number
}

export interface CalculationStep {
  step_number: number
  description: string
  formula: string
  values: Record<string, number | string>
  result: number
}

export interface CalculationDetails {
  metric_name: string
  final_formula: string
  explanation: string
  example: string
  calculation_steps: CalculationStep[]
  components_used: string[]
  methodology_notes: string[]
}

export interface DrillDownLevel {
  level: number
  name: string
  description: string
  grouping: GroupingType
  total_groups: number
  data: BreakdownComponent[]
}

export interface BreakdownResponse {
  metric_name: string
  metric_display_name: string
  total_value: number
  calculation_method: string
  last_updated: string
  summary: Record<string, any>
  calculation_details: CalculationDetails
  components: BreakdownComponent[]
  available_groupings: GroupingType[]
  drill_down_levels: DrillDownLevel[]
  total_positions: number
  data_freshness: string
  cache_expires?: string
}

export interface FilterOptions {
  symbols?: string[]
  strategies?: string[]
  position_types?: string[]
  min_value?: number
  max_value?: number
  min_return?: number
  max_return?: number
  expiry_start?: string
  expiry_end?: string
}

export interface BreakdownRequest {
  metric_type: string
  grouping?: GroupingType
  sort_by?: SortType
  sort_descending?: boolean
  limit?: number
  filters?: FilterOptions
  include_calculation_details?: boolean
  drill_down_level?: number
}

// Enhanced API request function for POST requests
async function apiPostRequest<T>(endpoint: string, data: any): Promise<T> {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    })
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      const message = errorData.detail || errorData.message || `HTTP ${response.status}`
      throw new ApiError(response.status, message)
    }
    
    const responseData = await response.json()
    return responseData
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    throw new ApiError(0, error instanceof Error ? error.message : 'Network error')
  }
}

// Breakdown API functions
export async function getTotalValueBreakdown(request: BreakdownRequest): Promise<BreakdownResponse> {
  const response = await apiPostRequest<ApiResponse<BreakdownResponse>>('/breakdown/total-value', request)
  if (!response.data) {
    throw new ApiError(500, 'No breakdown data received')
  }
  return response.data
}

export async function getTotalReturnBreakdown(request: BreakdownRequest): Promise<BreakdownResponse> {
  const response = await apiPostRequest<ApiResponse<BreakdownResponse>>('/breakdown/total-return', request)
  if (!response.data) {
    throw new ApiError(500, 'No breakdown data received')
  }
  return response.data
}

export async function getGreeksBreakdown(greekType: string, request: BreakdownRequest): Promise<BreakdownResponse> {
  const response = await apiPostRequest<ApiResponse<BreakdownResponse>>(`/breakdown/greeks/${greekType}`, request)
  if (!response.data) {
    throw new ApiError(500, 'No breakdown data received')
  }
  return response.data
}

export async function getQuickBreakdown(metricType: string, grouping?: GroupingType, sortBy?: SortType, limit?: number): Promise<BreakdownResponse> {
  const queryParams = new URLSearchParams()
  if (grouping) queryParams.append('grouping', grouping)
  if (sortBy) queryParams.append('sort_by', sortBy)
  if (limit) queryParams.append('limit', limit.toString())
  
  const response = await apiRequest<ApiResponse<BreakdownResponse>>(`/breakdown/quick/${metricType}?${queryParams.toString()}`)
  if (!response.data) {
    throw new ApiError(500, 'No breakdown data received')
  }
  return response.data
}

export async function getAvailableGroupings(): Promise<any> {
  const response = await apiRequest<ApiResponse<any>>('/breakdown/available-groups')
  if (!response.data) {
    throw new ApiError(500, 'No groupings data received')
  }
  return response.data
}

// P&L Analytics API functions
export async function getPnLSummary(): Promise<PnLSummary> {
  const response = await apiRequest<ApiResponse<PnLSummary>>('/options/pnl/summary')
  if (!response.data) {
    throw new ApiError(500, 'No P&L summary data received')
  }
  return response.data
}

export async function getYearlyPnL(startYear?: number, endYear?: number): Promise<YearlyPnL[]> {
  const queryParams = new URLSearchParams()
  if (startYear) queryParams.append('start_year', startYear.toString())
  if (endYear) queryParams.append('end_year', endYear.toString())
  
  const url = `/options/pnl/by-year${queryParams.toString() ? '?' + queryParams.toString() : ''}`
  const response = await apiRequest<ApiResponse<{ yearly_breakdown: YearlyPnL[] }>>(url)
  if (!response.data?.yearly_breakdown) {
    throw new ApiError(500, 'No yearly P&L data received')
  }
  return response.data.yearly_breakdown
}

export async function getSymbolPnL(
  year?: number | null,
  limit?: number,
  sortBy?: string,
  sortOrder?: string
): Promise<SymbolPnL[]> {
  const queryParams = new URLSearchParams()
  if (year) queryParams.append('year', year.toString())
  if (limit) queryParams.append('limit', limit.toString())
  if (sortBy) queryParams.append('sort_by', sortBy)
  if (sortOrder) queryParams.append('sort_order', sortOrder)
  
  const url = `/options/pnl/by-symbol${queryParams.toString() ? '?' + queryParams.toString() : ''}`
  const response = await apiRequest<ApiResponse<{ symbol_performance: SymbolPnL[] }>>(url)
  if (!response.data?.symbol_performance) {
    throw new ApiError(500, 'No symbol P&L data received')
  }
  return response.data.symbol_performance
}

export async function getSymbolTrades(
  symbol: string,
  year?: number | null,
  tradeType?: string
): Promise<TradeDetail[]> {
  const queryParams = new URLSearchParams()
  if (year) queryParams.append('year', year.toString())
  if (tradeType) queryParams.append('trade_type', tradeType)
  
  const url = `/options/pnl/trades/${symbol}${queryParams.toString() ? '?' + queryParams.toString() : ''}`
  const response = await apiRequest<ApiResponse<{ symbol: string; trades: TradeDetail[] }>>(url)
  if (!response.data?.trades) {
    throw new ApiError(500, 'No trade details received')
  }
  return response.data.trades
}

export async function triggerPnLProcessing(force = false): Promise<{ success: boolean; message: string }> {
  const queryParams = new URLSearchParams()
  if (force) queryParams.append('force', 'true')
  
  const url = `/options/pnl/process${queryParams.toString() ? '?' + queryParams.toString() : ''}`
  const response = await apiPostRequest<ApiResponse<{ success: boolean; message: string }>>(url, {})
  if (!response.data) {
    throw new ApiError(500, 'No processing status received')
  }
  return response.data
}

export async function getPnLProcessingStatus(): Promise<{ status: string; message?: string; last_calculated?: string }> {
  const response = await apiRequest<ApiResponse<{ status: string; message?: string; last_calculated?: string }>>('/options/pnl/status')
  if (!response.data) {
    throw new ApiError(500, 'No processing status received')
  }
  return response.data
}

export { ApiError }