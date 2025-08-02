'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { getDashboardData, checkAuthStatus, PortfolioSummary, StocksSummary, OptionsSummary, PortfolioGreeks, getPortfolioGreeks, ApiError } from '@/lib/api'
import { AnalysisTab } from '@/components/analysis'
import { InteractiveMetricCard } from '@/components/breakdown'
import { RolledOptionsSection } from '@/components/RolledOptionsSection'

interface DashboardData {
  portfolio: PortfolioSummary | null
  stocks: StocksSummary | null
  options: OptionsSummary | null
  greeks: PortfolioGreeks | null
}

type TabType = 'portfolio' | 'stocks' | 'options' | 'analysis'

// Portfolio Tab Component
function PortfolioTab({ dashboardData, formatCurrency, formatPercent }: {
  dashboardData: DashboardData
  formatCurrency: (value: number) => string
  formatPercent: (value: number) => string
}) {
  const totalStockValue = dashboardData.stocks?.total_value || 0
  const totalOptionsValue = dashboardData.options?.total_value || 0
  const totalValue = totalStockValue + totalOptionsValue
  
  const totalStockReturn = dashboardData.stocks?.total_return || 0
  const totalOptionsReturn = dashboardData.options?.total_return || 0
  const totalReturn = totalStockReturn + totalOptionsReturn
  
  const totalStockCost = dashboardData.stocks?.total_cost || 0
  const totalOptionsCost = dashboardData.options?.total_cost || 0
  const totalCost = totalStockCost + totalOptionsCost
  
  const totalReturnPercent = totalCost > 0 ? (totalReturn / totalCost) * 100 : 0

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-4">Portfolio Overview</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <InteractiveMetricCard
            title="Total Value"
            value={totalValue}
            formatValue={formatCurrency}
            metricType="total_value"
          />
          <InteractiveMetricCard
            title="Total Return"
            value={totalReturn}
            subtitle={formatPercent(totalReturnPercent)}
            isPositive={totalReturn >= 0}
            formatValue={formatCurrency}
            metricType="total_return"
          />
          <div className="bg-muted/50 rounded-lg p-4">
            <h3 className="text-sm font-medium text-muted-foreground mb-1">Positions</h3>
            <p className="text-2xl font-bold">
              {(dashboardData.stocks?.total_positions || 0) + (dashboardData.options?.total_positions || 0)}
            </p>
            <p className="text-sm text-muted-foreground">
              {dashboardData.stocks?.total_positions || 0} stocks, {dashboardData.options?.total_positions || 0} options
            </p>
          </div>
          <div className="bg-muted/50 rounded-lg p-4">
            <h3 className="text-sm font-medium text-muted-foreground mb-1">Win Rate</h3>
            <p className="text-2xl font-bold">
              {(() => {
                const stockWinners = dashboardData.stocks?.winners || 0
                const optionWinners = dashboardData.options?.winners || 0
                const totalWinners = stockWinners + optionWinners
                const totalPositions = (dashboardData.stocks?.total_positions || 0) + (dashboardData.options?.total_positions || 0)
                const winRate = totalPositions > 0 ? (totalWinners / totalPositions) * 100 : 0
                return formatPercent(winRate)
              })()}
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <h3 className="text-lg font-medium mb-3">Asset Allocation</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span>Stocks</span>
              <div className="text-right">
                <div className="font-medium">{formatCurrency(totalStockValue)}</div>
                <div className="text-sm text-muted-foreground">
                  {totalValue > 0 ? formatPercent((totalStockValue / totalValue) * 100) : '0%'}
                </div>
              </div>
            </div>
            <div className="flex justify-between items-center">
              <span>Options</span>
              <div className="text-right">
                <div className="font-medium">{formatCurrency(totalOptionsValue)}</div>
                <div className="text-sm text-muted-foreground">
                  {totalValue > 0 ? formatPercent((totalOptionsValue / totalValue) * 100) : '0%'}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div>
          <h3 className="text-lg font-medium mb-3">Performance Summary</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span>Stock Return</span>
              <div className={`font-medium ${totalStockReturn >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {formatCurrency(totalStockReturn)}
              </div>
            </div>
            <div className="flex justify-between items-center">
              <span>Options Return</span>
              <div className={`font-medium ${totalOptionsReturn >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {formatCurrency(totalOptionsReturn)}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// Stocks Tab Component
function StocksTab({ stocks, formatCurrency, formatPercent }: {
  stocks: StocksSummary | null
  formatCurrency: (value: number) => string
  formatPercent: (value: number) => string
}) {
  if (!stocks || stocks.positions.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-muted-foreground mb-4">No stock positions found.</p>
        <p className="text-sm text-muted-foreground">Stock positions will appear here when available.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-4">Stock Positions ({stocks.total_positions})</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <InteractiveMetricCard
            title="Total Value"
            value={stocks.total_value}
            formatValue={formatCurrency}
            metricType="total_value"
          />
          <InteractiveMetricCard
            title="Total Return"
            value={stocks.total_return}
            subtitle={formatPercent(stocks.total_return_percent)}
            isPositive={stocks.total_return >= 0}
            formatValue={formatCurrency}
            metricType="total_return"
          />
          <div className="bg-muted/50 rounded-lg p-4">
            <h3 className="text-sm font-medium text-muted-foreground mb-1">Win Rate</h3>
            <p className="text-2xl font-bold">{formatPercent(stocks.win_rate)}</p>
            <p className="text-sm text-muted-foreground">{stocks.winners}W / {stocks.losers}L</p>
          </div>
        </div>
      </div>

      <div>
        <h3 className="text-lg font-medium mb-3">Positions</h3>
        <div className="space-y-2">
          {stocks.positions.map((position, index) => (
            <div key={index} className="flex justify-between items-center p-4 bg-muted/50 rounded-lg">
              <div>
                <span className="font-medium text-lg">{position.symbol}</span>
                <div className="text-sm text-muted-foreground">
                  {position.quantity} shares @ {formatCurrency(position.average_buy_price)}
                </div>
                <div className="text-sm text-muted-foreground">
                  Current: {formatCurrency(position.current_price)}
                </div>
              </div>
              <div className="text-right">
                <div className="font-medium text-lg">{formatCurrency(position.market_value)}</div>
                <div className={`text-sm ${position.total_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {formatCurrency(position.total_return)}
                </div>
                <div className={`text-sm ${position.percent_change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {formatPercent(position.percent_change)}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// Options Tab Component
function OptionsTab({ options, greeks, formatCurrency, formatPercent }: {
  options: OptionsSummary | null
  greeks: PortfolioGreeks | null
  formatCurrency: (value: number) => string
  formatPercent: (value: number) => string
}) {
  const [optionsExpanded, setOptionsExpanded] = useState(false)
  const [symbolsExpanded, setSymbolsExpanded] = useState(false)
  const [yearlyExpanded, setYearlyExpanded] = useState(false)
  
  if (!options || options.positions.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-muted-foreground mb-4">No options positions found.</p>
        <p className="text-sm text-muted-foreground">Options positions will appear here when available.</p>
      </div>
    )
  }

  // Extract P&L analytics data
  const pnlAnalytics = options.pnl_analytics || {
    total_pnl: options.total_return || 0,
    realized_pnl: 0,
    unrealized_pnl: options.total_return || 0,
    total_trades: options.total_positions || 0,
    realized_trades: 0,
    open_positions: options.total_positions || 0,
    win_rate: options.win_rate || 0,
    largest_winner: 0,
    largest_loser: 0,
    avg_trade_pnl: 0
  }

  const yearlyPerformance = options.yearly_performance || []
  const topSymbols = options.top_symbols || []

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold mb-4">Options Portfolio ({options.total_positions} positions)</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <InteractiveMetricCard
            title="Total Value"
            value={options.total_value}
            formatValue={formatCurrency}
            metricType="total_value"
          />
          <InteractiveMetricCard
            title="Current P&L"
            value={options.total_return}
            subtitle={formatPercent(options.total_return_percent)}
            isPositive={options.total_return >= 0}
            formatValue={formatCurrency}
            metricType="total_return"
          />
          <div className="bg-muted/50 rounded-lg p-4">
            <h3 className="text-sm font-medium text-muted-foreground mb-1">Long/Short</h3>
            <p className="text-2xl font-bold">{options.long_positions}/{options.short_positions}</p>
            <p className="text-sm text-muted-foreground">Long / Short</p>
          </div>
          <div className="bg-muted/50 rounded-lg p-4">
            <h3 className="text-sm font-medium text-muted-foreground mb-1">Expiring Soon</h3>
            <p className="text-2xl font-bold">{options.expiring_this_week}</p>
            <p className="text-sm text-muted-foreground">This week</p>
          </div>
        </div>
      </div>

      {/* Enhanced P&L Analytics Section */}
      <div>
        <h3 className="text-lg font-medium mb-4">P&L Analytics</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="bg-muted/50 rounded-lg p-4">
            <h4 className="text-sm font-medium text-muted-foreground mb-1">Total P&L</h4>
            <p className={`text-xl font-bold ${pnlAnalytics.total_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {formatCurrency(pnlAnalytics.total_pnl)}
            </p>
            <p className="text-xs text-muted-foreground">All-time performance</p>
          </div>
          <div className="bg-muted/50 rounded-lg p-4">
            <h4 className="text-sm font-medium text-muted-foreground mb-1">Realized P&L</h4>
            <p className={`text-xl font-bold ${pnlAnalytics.realized_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {formatCurrency(pnlAnalytics.realized_pnl)}
            </p>
            <p className="text-xs text-muted-foreground">{pnlAnalytics.realized_trades} closed trades</p>
          </div>
          <div className="bg-muted/50 rounded-lg p-4">
            <h4 className="text-sm font-medium text-muted-foreground mb-1">Unrealized P&L</h4>
            <p className={`text-xl font-bold ${pnlAnalytics.unrealized_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {formatCurrency(pnlAnalytics.unrealized_pnl)}
            </p>
            <p className="text-xs text-muted-foreground">{pnlAnalytics.open_positions} open positions</p>
          </div>
          <div className="bg-muted/50 rounded-lg p-4">
            <h4 className="text-sm font-medium text-muted-foreground mb-1">Win Rate</h4>
            <p className="text-xl font-bold">{formatPercent(pnlAnalytics.win_rate)}</p>
            <p className="text-xs text-muted-foreground">{pnlAnalytics.total_trades} total trades</p>
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-muted/50 rounded-lg p-4">
            <h4 className="text-sm font-medium text-muted-foreground mb-1">Largest Winner</h4>
            <p className="text-lg font-bold text-green-600">
              {formatCurrency(pnlAnalytics.largest_winner)}
            </p>
          </div>
          <div className="bg-muted/50 rounded-lg p-4">
            <h4 className="text-sm font-medium text-muted-foreground mb-1">Largest Loser</h4>
            <p className="text-lg font-bold text-red-600">
              {formatCurrency(pnlAnalytics.largest_loser)}
            </p>
          </div>
          <div className="bg-muted/50 rounded-lg p-4">
            <h4 className="text-sm font-medium text-muted-foreground mb-1">Avg Trade P&L</h4>
            <p className={`text-lg font-bold ${pnlAnalytics.avg_trade_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {formatCurrency(pnlAnalytics.avg_trade_pnl)}
            </p>
          </div>
        </div>
      </div>

      {/* Yearly Performance Section */}
      {yearlyPerformance.length > 0 && (
        <div>
          <button
            onClick={() => setYearlyExpanded(!yearlyExpanded)}
            className="flex items-center justify-between w-full p-4 bg-muted/50 rounded-lg hover:bg-muted transition-colors mb-3"
          >
            <h3 className="text-lg font-medium">Yearly Performance ({yearlyPerformance.length} years)</h3>
            <svg
              className={`w-5 h-5 transition-transform ${yearlyExpanded ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m19 9-7 7-7-7" />
            </svg>
          </button>
          {yearlyExpanded && (
            <div className="space-y-2">
              {yearlyPerformance.map((year, index) => (
                <div key={index} className="flex justify-between items-center p-4 bg-muted/50 rounded-lg">
                  <div>
                    <span className="font-medium text-lg">{year.year}</span>
                    <div className="text-sm text-muted-foreground">
                      {year.trade_count} trades • {formatPercent(year.win_rate)} win rate
                    </div>
                  </div>
                  <div className="text-right">
                    <div className={`font-medium text-lg ${year.realized_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {formatCurrency(year.realized_pnl)}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {year.winning_trades}W / {year.losing_trades}L
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Symbol Performance Section */}
      {topSymbols.length > 0 && (
        <div>
          <button
            onClick={() => setSymbolsExpanded(!symbolsExpanded)}
            className="flex items-center justify-between w-full p-4 bg-muted/50 rounded-lg hover:bg-muted transition-colors mb-3"
          >
            <h3 className="text-lg font-medium">Top Performing Symbols ({topSymbols.length})</h3>
            <svg
              className={`w-5 h-5 transition-transform ${symbolsExpanded ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m19 9-7 7-7-7" />
            </svg>
          </button>
          {symbolsExpanded && (
            <div className="space-y-2">
              {topSymbols.slice(0, 10).map((symbol, index) => (
                <div key={index} className="flex justify-between items-center p-4 bg-muted/50 rounded-lg">
                  <div>
                    <span className="font-medium text-lg">{symbol.symbol}</span>
                    <div className="text-sm text-muted-foreground">
                      {symbol.total_trades} trades • {formatPercent(symbol.win_rate)} win rate
                    </div>
                    <div className="text-xs text-muted-foreground">
                      R: {formatCurrency(symbol.realized_pnl)} | U: {formatCurrency(symbol.unrealized_pnl)}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className={`font-medium text-lg ${symbol.total_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {formatCurrency(symbol.total_pnl)}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      Avg: {formatCurrency(symbol.avg_trade_pnl)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {greeks && (
        <div>
          <h3 className="text-lg font-medium mb-3">Portfolio Greeks</h3>
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
            <div className="bg-muted/50 rounded-lg p-4">
              <h4 className="text-sm font-medium text-muted-foreground mb-1">Delta</h4>
              <p className={`text-xl font-bold ${greeks.net_delta >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {greeks.net_delta.toFixed(2)}
              </p>
              <p className="text-xs text-muted-foreground">
                {greeks.delta_neutral ? 'Neutral' : greeks.net_delta > 0 ? 'Bullish' : 'Bearish'}
              </p>
            </div>
            <div className="bg-muted/50 rounded-lg p-4">
              <h4 className="text-sm font-medium text-muted-foreground mb-1">Gamma</h4>
              <p className="text-xl font-bold">{greeks.net_gamma.toFixed(4)}</p>
              <p className="text-xs text-muted-foreground">Acceleration</p>
            </div>
            <div className="bg-muted/50 rounded-lg p-4">
              <h4 className="text-sm font-medium text-muted-foreground mb-1">Theta</h4>
              <p className={`text-xl font-bold ${greeks.net_theta >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {greeks.net_theta.toFixed(2)}
              </p>
              <p className="text-xs text-muted-foreground">
                {greeks.theta_positive ? 'Income' : 'Decay'}
              </p>
            </div>
            <div className="bg-muted/50 rounded-lg p-4">
              <h4 className="text-sm font-medium text-muted-foreground mb-1">Vega</h4>
              <p className="text-xl font-bold">{greeks.net_vega.toFixed(2)}</p>
              <p className="text-xs text-muted-foreground">IV Risk</p>
            </div>
            <div className="bg-muted/50 rounded-lg p-4">
              <h4 className="text-sm font-medium text-muted-foreground mb-1">Daily Decay</h4>
              <p className="text-xl font-bold text-amber-600">
                {formatCurrency(greeks.daily_theta_decay)}
              </p>
              <p className="text-xs text-muted-foreground">Per day</p>
            </div>
          </div>
        </div>
      )}

      <div>
        <h3 className="text-lg font-medium mb-3">Strategy Breakdown</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div className="bg-muted/50 rounded-lg p-4">
            <h4 className="text-sm font-medium text-muted-foreground mb-2">Option Types</h4>
            <div className="space-y-1">
              <div className="flex justify-between">
                <span className="text-sm">Calls</span>
                <span className="text-sm font-medium">{options.calls_count}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm">Puts</span>
                <span className="text-sm font-medium">{options.puts_count}</span>
              </div>
            </div>
          </div>
          <div className="bg-muted/50 rounded-lg p-4">
            <h4 className="text-sm font-medium text-muted-foreground mb-2">Expiration</h4>
            <div className="space-y-1">
              <div className="flex justify-between">
                <span className="text-sm">This Week</span>
                <span className="text-sm font-medium">{options.expiring_this_week}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm">This Month</span>
                <span className="text-sm font-medium">{options.expiring_this_month}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div>
        <button
          onClick={() => setOptionsExpanded(!optionsExpanded)}
          className="flex items-center justify-between w-full p-4 bg-muted/50 rounded-lg hover:bg-muted transition-colors mb-3"
        >
          <h3 className="text-lg font-medium">
            Current Positions ({options.positions.length})
          </h3>
          <svg
            className={`w-5 h-5 transition-transform ${optionsExpanded ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m19 9-7 7-7-7" />
          </svg>
        </button>
        <div className="space-y-2">
          {(optionsExpanded ? options.positions : options.positions.slice(0, 5)).map((position, index) => (
            <div key={index} className="flex justify-between items-center p-4 bg-muted/50 rounded-lg">
              <div>
                <div className="flex items-center space-x-2">
                  <span className="font-medium text-lg">{position.underlying_symbol}</span>
                  <span className={`text-xs px-2 py-1 rounded ${
                    position.strategy.includes('BUY') ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                  }`}>
                    {position.strategy}
                  </span>
                </div>
                <div className="text-sm text-muted-foreground">
                  {position.contracts} × {position.option_type.toUpperCase()} ${position.strike_price}
                </div>
                <div className="text-sm text-muted-foreground">
                  Exp: {position.expiration_date} ({position.days_to_expiry}d)
                </div>
                {position.greeks && (
                  <div className="text-xs text-muted-foreground mt-1">
                    Δ: {position.greeks.delta.toFixed(3)} | Θ: {position.greeks.theta.toFixed(3)} | IV: {(position.greeks.implied_volatility * 100).toFixed(1)}%
                  </div>
                )}
              </div>
              <div className="text-right">
                <div className="font-medium text-lg">{formatCurrency(position.market_value)}</div>
                <div className={`text-sm ${position.total_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {formatCurrency(position.total_return)}
                </div>
                <div className={`text-sm ${position.percent_change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {formatPercent(position.percent_change)}
                </div>
              </div>
            </div>
          ))}
          {!optionsExpanded && options.positions.length > 5 && (
            <button
              onClick={() => setOptionsExpanded(true)}
              className="w-full text-center text-sm text-primary hover:text-primary/80 pt-2 py-2 rounded hover:bg-muted/30 transition-colors"
            >
              Show {options.positions.length - 5} more positions
            </button>
          )}
        </div>
      </div>

      {/* Rolled Options Section */}
      <RolledOptionsSection formatCurrency={formatCurrency} formatPercent={formatPercent} />
    </div>
  )
}


export default function Dashboard() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<TabType>('portfolio')
  const [dashboardData, setDashboardData] = useState<DashboardData>({
    portfolio: null,
    stocks: null,
    options: null,
    greeks: null
  })
  const [dataLoading, setDataLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const router = useRouter()

  useEffect(() => {
    // Check authentication status
    const checkAuth = async () => {
      try {
        const authStatus = localStorage.getItem('robinhood_authenticated')
        if (authStatus === 'true') {
          // Verify with backend
          const backendAuth = await checkAuthStatus()
          setIsAuthenticated(backendAuth.authenticated)
          
          if (backendAuth.authenticated) {
            // Fetch dashboard data
            await fetchDashboardData()
          }
        } else {
          setIsAuthenticated(false)
        }
      } catch (error) {
        console.error('Auth check failed:', error)
        setIsAuthenticated(false)
        localStorage.removeItem('robinhood_authenticated')
      } finally {
        setIsLoading(false)
      }
    }

    checkAuth()
  }, [])

  const fetchDashboardData = async () => {
    if (!isAuthenticated) return

    setDataLoading(true)
    setError(null)
    
    try {
      const [data, greeks] = await Promise.all([
        getDashboardData(),
        getPortfolioGreeks().catch(err => {
          console.warn('Failed to fetch portfolio Greeks:', err)
          return null
        })
      ])
      setDashboardData({ ...data, greeks })
      setLastUpdated(new Date())
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error)
      if (error instanceof ApiError && error.statusCode === 401) {
        // Authentication expired
        localStorage.removeItem('robinhood_authenticated')
        setIsAuthenticated(false)
        router.push('/login')
      } else {
        setError(error instanceof Error ? error.message : 'Failed to load data')
      }
    } finally {
      setDataLoading(false)
    }
  }

  const handleConnectAccount = () => {
    router.push('/login')
  }

  const handleDisconnect = () => {
    localStorage.removeItem('robinhood_authenticated')
    setIsAuthenticated(false)
    setDashboardData({ portfolio: null, stocks: null, options: null, greeks: null })
    setError(null)
    setLastUpdated(null)
  }

  const handleRefresh = () => {
    fetchDashboardData()
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value)
  }

  const formatPercent = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'percent',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value / 100)
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="animate-pulse">Loading...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          <div className="flex justify-between items-center mb-8">
            <h1 className="text-3xl font-bold tracking-tight">Trading Analytics Dashboard</h1>
            <div className="flex items-center space-x-4">
              {isAuthenticated ? (
                <div className="flex items-center space-x-3">
                  <div className="flex items-center text-sm text-success">
                    <span className="w-2 h-2 bg-success rounded-full mr-2"></span>
                    Connected to Robinhood
                  </div>
                  {lastUpdated && (
                    <div className="text-xs text-muted-foreground">
                      Updated: {lastUpdated.toLocaleTimeString()}
                    </div>
                  )}
                  <button
                    onClick={handleRefresh}
                    disabled={dataLoading}
                    className="px-3 py-1 text-sm bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/80 disabled:opacity-50"
                  >
                    {dataLoading ? 'Refreshing...' : 'Refresh'}
                  </button>
                  <button
                    onClick={handleDisconnect}
                    className="px-4 py-2 text-sm bg-destructive text-destructive-foreground rounded-md hover:bg-destructive/90"
                  >
                    Disconnect
                  </button>
                </div>
              ) : (
                <button
                  onClick={handleConnectAccount}
                  className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
                >
                  Connect Robinhood
                </button>
              )}
            </div>
          </div>

          {error && (
            <div className="bg-destructive/10 border border-destructive/20 rounded-md p-4 mb-6">
              <p className="text-destructive text-sm">{error}</p>
              <button
                onClick={handleRefresh}
                className="mt-2 text-xs text-destructive hover:underline"
              >
                Try again
              </button>
            </div>
          )}
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
            <div className="bg-card rounded-lg border p-6">
              <h3 className="text-lg font-semibold mb-2">Portfolio Value</h3>
              {dataLoading ? (
                <div className="animate-pulse">
                  <div className="h-8 bg-muted rounded mb-2"></div>
                  <div className="h-4 bg-muted rounded w-3/4"></div>
                </div>
              ) : dashboardData.portfolio ? (
                <InteractiveMetricCard
                  title=""
                  value={dashboardData.portfolio.total_value || 0}
                  subtitle="Total portfolio value"
                  formatValue={formatCurrency}
                  metricType="total_value"
                  className="bg-transparent p-0"
                />
              ) : (
                <>
                  <p className="text-2xl font-bold text-muted-foreground">$0.00</p>
                  <p className="text-sm text-muted-foreground">No portfolio data</p>
                </>
              )}
            </div>
            
            <div className="bg-card rounded-lg border p-6">
              <h3 className="text-lg font-semibold mb-2">Active Positions</h3>
              {dataLoading ? (
                <div className="animate-pulse">
                  <div className="h-8 bg-muted rounded mb-2"></div>
                  <div className="h-4 bg-muted rounded w-3/4"></div>
                </div>
              ) : (
                <>
                  <p className="text-2xl font-bold">
                    {(dashboardData.stocks?.total_positions || 0) + (dashboardData.options?.total_positions || 0)}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {dashboardData.stocks?.total_positions || 0} stocks, {dashboardData.options?.total_positions || 0} options
                  </p>
                </>
              )}
            </div>
            
            <div className="bg-card rounded-lg border p-6">
              <h3 className="text-lg font-semibold mb-2">Total Return</h3>
              {dataLoading ? (
                <div className="animate-pulse">
                  <div className="h-8 bg-muted rounded mb-2"></div>
                  <div className="h-4 bg-muted rounded w-3/4"></div>
                </div>
              ) : (
                <>
                  {(() => {
                    const totalReturn = (dashboardData.stocks?.total_return || 0) + (dashboardData.options?.total_return || 0)
                    const totalCost = (dashboardData.stocks?.total_cost || 0) + (dashboardData.options?.total_cost || 0)
                    const returnPercent = totalCost > 0 ? (totalReturn / totalCost) * 100 : 0
                    const isPositive = totalReturn >= 0
                    
                    return (
                      <InteractiveMetricCard
                        title=""
                        value={totalReturn}
                        subtitle={`${formatPercent(returnPercent)} total return`}
                        isPositive={isPositive}
                        formatValue={formatCurrency}
                        metricType="total_return"
                        className="bg-transparent p-0"
                      />
                    )
                  })()}
                </>
              )}
            </div>
          </div>
          
          {!isAuthenticated ? (
            <div className="bg-card rounded-lg border p-6">
              <h2 className="text-xl font-semibold mb-4">Getting Started</h2>
              <div className="space-y-4">
                <div className="flex items-start space-x-3">
                  <div className="w-6 h-6 bg-primary rounded-full flex items-center justify-center text-primary-foreground text-sm font-bold">1</div>
                  <div>
                    <h3 className="font-medium">Connect Your Trading Account</h3>
                    <p className="text-sm text-muted-foreground">Set up your Robinhood credentials to start tracking your portfolio.</p>
                  </div>
                </div>
                
                <div className="flex items-start space-x-3">
                  <div className="w-6 h-6 bg-muted rounded-full flex items-center justify-center text-muted-foreground text-sm font-bold">2</div>
                  <div>
                    <h3 className="font-medium">View Portfolio Analytics</h3>
                    <p className="text-sm text-muted-foreground">Access detailed analytics for your stock and options positions.</p>
                  </div>
                </div>
                
                <div className="flex items-start space-x-3">
                  <div className="w-6 h-6 bg-muted rounded-full flex items-center justify-center text-muted-foreground text-sm font-bold">3</div>
                  <div>
                    <h3 className="font-medium">Track Performance</h3>
                    <p className="text-sm text-muted-foreground">Monitor your trading performance with real-time updates and historical data.</p>
                  </div>
                </div>
              </div>
              
              <div className="mt-6 pt-6 border-t border-border">
                <button
                  onClick={handleConnectAccount}
                  className="w-full bg-primary text-primary-foreground py-3 px-4 rounded-md font-medium hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                >
                  Connect Robinhood Account
                </button>
              </div>
            </div>
          ) : (
            <>
              {/* Tab Navigation */}
              <div className="bg-card rounded-lg border overflow-hidden">
                <div className="border-b border-border">
                  <nav className="flex space-x-8 px-6" aria-label="Tabs">
                    {(['portfolio', 'stocks', 'options', 'analysis'] as TabType[]).map((tab) => (
                      <button
                        key={tab}
                        onClick={() => setActiveTab(tab)}
                        className={`${
                          activeTab === tab
                            ? 'border-primary text-primary'
                            : 'border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground'
                        } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm capitalize transition-colors`}
                      >
                        {tab}
                        {tab === 'stocks' && dashboardData.stocks && (
                          <span className="ml-1 text-xs bg-muted rounded-full px-2 py-0.5">
                            {dashboardData.stocks.total_positions}
                          </span>
                        )}
                        {tab === 'options' && dashboardData.options && (
                          <span className="ml-1 text-xs bg-muted rounded-full px-2 py-0.5">
                            {dashboardData.options.total_positions}
                          </span>
                        )}
                      </button>
                    ))}
                    
                    {/* P&L Analytics Link */}
                    <a
                      href="/dashboard/pnl"
                      className="border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors"
                    >
                      P&L Analytics
                      <span className="ml-1 text-xs bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-full px-2 py-0.5">
                        NEW
                      </span>
                    </a>
                  </nav>
                </div>

                <div className="p-6">
                  {dataLoading ? (
                    <div className="space-y-4">
                      <div className="animate-pulse">
                        <div className="h-4 bg-muted rounded w-1/4 mb-4"></div>
                        <div className="space-y-2">
                          <div className="h-12 bg-muted rounded"></div>
                          <div className="h-12 bg-muted rounded"></div>
                          <div className="h-12 bg-muted rounded"></div>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <>
                      {activeTab === 'portfolio' && <PortfolioTab dashboardData={dashboardData} formatCurrency={formatCurrency} formatPercent={formatPercent} />}
                      {activeTab === 'stocks' && <StocksTab stocks={dashboardData.stocks} formatCurrency={formatCurrency} formatPercent={formatPercent} />}
                      {activeTab === 'options' && <OptionsTab options={dashboardData.options} greeks={dashboardData.greeks} formatCurrency={formatCurrency} formatPercent={formatPercent} />}
                      {activeTab === 'analysis' && <AnalysisTab formatCurrency={formatCurrency} formatPercent={formatPercent} />}
                    </>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}