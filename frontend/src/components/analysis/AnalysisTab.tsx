'use client'

import { useState, useEffect } from 'react'
import { OptionsOrder, HistoricalOptionsOrder, TickerPerformance, OptionPosition } from '@/lib/api'
import { getOptionsOrders, getTickerPerformance, getOptionsPositions, getFilteredOptionsPositions } from '@/lib/api'
import AnalysisFilters from './AnalysisFilters'
import TickerPerformanceSection from './TickerPerformanceSection'
import FilteredPositionsSection from './FilteredPositionsSection'
import TradingHistorySection from './TradingHistorySection'

interface AnalysisTabProps {
  formatCurrency: (value: number) => string
  formatPercent: (value: number) => string
}

interface AnalysisFilters {
  ticker: string
  strategy: string
  positionType: string
  daysBack: number
  orderState: string
}

export default function AnalysisTab({ formatCurrency, formatPercent }: AnalysisTabProps) {
  // UI State
  const [historyExpanded, setHistoryExpanded] = useState(false)
  const [positionsExpanded, setPositionsExpanded] = useState(false)
  
  // Data state
  const [orders, setOrders] = useState<HistoricalOptionsOrder[]>([])
  const [tickerPerformance, setTickerPerformance] = useState<TickerPerformance[]>([])
  const [allPositions, setAllPositions] = useState<OptionPosition[]>([])
  const [filteredPositions, setFilteredPositions] = useState<OptionPosition[]>([])
  const [dataErrors, setDataErrors] = useState<{[key: string]: string}>({})

  // Loading states
  const [isInitialLoading, setIsInitialLoading] = useState(true)
  const [isFiltering, setIsFiltering] = useState(false)

  // Filter state
  const [filters, setFilters] = useState<AnalysisFilters>({
    ticker: '',
    strategy: '',
    positionType: '',
    daysBack: 90,
    orderState: ''
  })

  // New data detection state
  const [hasNewData, setHasNewData] = useState(false)
  const [newDataCheckEnabled, setNewDataCheckEnabled] = useState(true)
  const [checkInterval, setCheckInterval] = useState(30000) // 30 seconds default
  const [lastDataHash, setLastDataHash] = useState<string>('')

  // Auto-refresh state (keeping for backward compatibility but disabled by default)
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(false)
  const [refreshInterval, setRefreshInterval] = useState(30000) // 30 seconds default
  
  // Centralized data loading with proper error handling
  const loadAnalysisData = async (withFilters = false) => {
    const errors: {[key: string]: string} = {}

    try {
      if (withFilters) {
        setIsFiltering(true)
      } else {
        setIsInitialLoading(true)
      }
      
      // Clear previous errors
      setDataErrors({})
      
      // Load orders with current filters
      let ordersData: HistoricalOptionsOrder[] = []
      try {
        ordersData = await getOptionsOrders({
          limit: 100,
          days_back: withFilters ? filters.daysBack : 90,
          underlying_symbol: withFilters ? (filters.ticker || undefined) : undefined,
          state: withFilters ? (filters.orderState || undefined) : undefined,
          strategy: withFilters ? (filters.strategy || undefined) : undefined
        })
      } catch (error) {
        console.error('Failed to fetch orders:', error)
        errors.orders = 'Failed to load trading history'
        ordersData = []
      }
      
      // Load ticker performance
      let performanceData: TickerPerformance[] = []
      try {
        performanceData = await getTickerPerformance()
      } catch (error) {
        console.error('Failed to fetch performance:', error)
        errors.performance = 'Failed to load ticker performance'
        performanceData = []
      }
      
      // Load current positions
      let currentPositions: OptionPosition[] = []
      try {
        currentPositions = await getOptionsPositions()
      } catch (error) {
        console.error('Failed to fetch positions:', error)
        errors.positions = 'Failed to load current positions'
        currentPositions = []
      }
      
      // Load filtered positions if filters are applied
      let filteredData: OptionPosition[] = []
      if (withFilters && (filters.ticker || filters.strategy || filters.positionType)) {
        try {
          filteredData = await getFilteredOptionsPositions({
            underlying_symbol: filters.ticker || undefined,
            strategy: filters.strategy || undefined,
            position_type: filters.positionType || undefined,
            sort_by: 'market_value',
            sort_order: 'desc'
          })
        } catch (error) {
          console.error('Failed to fetch filtered positions:', error)
          errors.filtered = 'Failed to apply position filters'
          filteredData = []
        }
      }
      
      // Update state
      setOrders(ordersData)
      setTickerPerformance(performanceData)
      setAllPositions(currentPositions)
      setFilteredPositions(filteredData)
      setDataErrors(errors)
      
      // Update data hash for change detection
      const dataHash = generateAnalysisDataHash(ordersData, performanceData, currentPositions, filteredData)
      setLastDataHash(dataHash)
      
      console.log('Analysis data loaded:', {
        orders: ordersData.length,
        performance: performanceData.length,
        positions: currentPositions.length,
        filtered: filteredData.length,
        errors: Object.keys(errors)
      })
      
    } catch (error) {
      console.error('Critical error loading analysis data:', error)
      setDataErrors({ critical: 'Failed to load analysis data' })
    } finally {
      setIsInitialLoading(false)
      setIsFiltering(false)
    }
  }

  // Generate a hash of the current analysis data to detect changes
  const generateAnalysisDataHash = (orders: HistoricalOptionsOrder[], performance: TickerPerformance[], positions: OptionPosition[], filtered: OptionPosition[]): string => {
    const dataString = JSON.stringify({
      ordersCount: orders.length,
      performanceCount: performance.length,
      positionsCount: positions.length,
      filteredCount: filtered.length,
      // Use some key metrics that would change when new data arrives
      totalOrdersValue: orders.reduce((sum, order) => sum + (order.premium || 0), 0),
      totalPositionsValue: positions.reduce((sum, pos) => sum + (pos.market_value || 0), 0)
    })
    return btoa(dataString).slice(0, 16) // Simple hash for comparison
  }

  // Check for new data without updating the UI
  const checkForNewAnalysisData = async () => {
    if (!newDataCheckEnabled || isInitialLoading || isFiltering) return

    try {
      // Load minimal data for comparison
      const [ordersData, performanceData, currentPositions] = await Promise.all([
        getOptionsOrders({ limit: 100, days_back: filters.daysBack }),
        getTickerPerformance(),
        getOptionsPositions()
      ])
      
      const newDataHash = generateAnalysisDataHash(ordersData, performanceData, currentPositions, [])
      
      if (lastDataHash && newDataHash !== lastDataHash) {
        console.log('New analysis data detected!')
        setHasNewData(true)
      }
    } catch (error) {
      console.error('Failed to check for new analysis data:', error)
    }
  }

  // Auto-refresh effect
  useEffect(() => {
    if (!autoRefreshEnabled || isInitialLoading || isFiltering) return

    const interval = setInterval(() => {
      console.log('Auto-refreshing analysis data...')
      loadAnalysisData(true)
    }, refreshInterval)

    return () => clearInterval(interval)
  }, [autoRefreshEnabled, refreshInterval, isInitialLoading, isFiltering])

  // New data check effect
  useEffect(() => {
    if (!newDataCheckEnabled || isInitialLoading || isFiltering) return

    const interval = setInterval(() => {
      console.log('Checking for new analysis data...')
      checkForNewAnalysisData()
    }, checkInterval)

    return () => clearInterval(interval)
  }, [newDataCheckEnabled, checkInterval, isInitialLoading, isFiltering, lastDataHash, filters.daysBack])

  // Manual refresh function
  const handleManualRefresh = () => {
    setHasNewData(false) // Clear new data indicator when manually refreshing
    loadAnalysisData(true)
  }

  // Initial data load
  useEffect(() => {
    loadAnalysisData(false)
  }, [])

  // Reload with filters when filters change
  useEffect(() => {
    if (!isInitialLoading) {
      const timeoutId = setTimeout(() => {
        loadAnalysisData(true)
      }, 300) // Debounce filter changes
      
      return () => clearTimeout(timeoutId)
    }
  }, [filters.ticker, filters.strategy, filters.positionType, filters.daysBack, filters.orderState, isInitialLoading])

  const uniqueTickers = Array.from(new Set([
    ...orders.map(order => order.underlying_symbol).filter((s): s is string => Boolean(s)),
    ...allPositions.map(pos => pos.underlying_symbol).filter((s): s is string => Boolean(s))
  ])).sort()
  
  const uniqueStrategies = Array.from(new Set([
    ...orders.map(order => order.strategy).filter((s): s is string => Boolean(s)),
    ...allPositions.map(pos => pos.strategy).filter((s): s is string => Boolean(s))
  ])).sort()

  return (
    <div className="space-y-6">
      <div>
        <div className="flex justify-between items-center mb-4">
          <div className="flex items-center space-x-2">
            <h2 className="text-xl font-semibold">Trading Analysis & History</h2>
            {autoRefreshEnabled && (
              <span className="text-xs text-muted-foreground flex items-center">
                <span className="w-2 h-2 bg-blue-500 rounded-full mr-1 animate-pulse"></span>
                Auto-refresh: {refreshInterval / 1000}s
              </span>
            )}
            {newDataCheckEnabled && (
              <span className="text-xs text-muted-foreground flex items-center">
                <span className="w-2 h-2 bg-green-500 rounded-full mr-1 animate-pulse"></span>
                Checking: {checkInterval / 1000}s
              </span>
            )}
          </div>
          
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2">
              <label className="flex items-center text-xs text-muted-foreground">
                <input
                  type="checkbox"
                  checked={newDataCheckEnabled}
                  onChange={(e) => setNewDataCheckEnabled(e.target.checked)}
                  className="mr-1"
                />
                Check for new data
              </label>
              <select
                value={checkInterval / 1000}
                onChange={(e) => setCheckInterval(Number(e.target.value) * 1000)}
                className="text-xs bg-secondary text-secondary-foreground rounded px-2 py-1"
                disabled={!newDataCheckEnabled}
              >
                <option value={15}>15s</option>
                <option value={30}>30s</option>
                <option value={60}>1m</option>
                <option value={120}>2m</option>
                <option value={300}>5m</option>
              </select>
            </div>
            <div className="flex items-center space-x-2">
              <label className="flex items-center text-xs text-muted-foreground">
                <input
                  type="checkbox"
                  checked={autoRefreshEnabled}
                  onChange={(e) => setAutoRefreshEnabled(e.target.checked)}
                  className="mr-1"
                />
                Auto-refresh
              </label>
              <select
                value={refreshInterval / 1000}
                onChange={(e) => setRefreshInterval(Number(e.target.value) * 1000)}
                className="text-xs bg-secondary text-secondary-foreground rounded px-2 py-1"
                disabled={!autoRefreshEnabled}
              >
                <option value={30}>30s</option>
                <option value={60}>1m</option>
                <option value={120}>2m</option>
                <option value={300}>5m</option>
              </select>
            </div>
            <button
              onClick={handleManualRefresh}
              disabled={isFiltering}
              className="px-3 py-1 text-sm bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/80 disabled:opacity-50 relative"
            >
              {isFiltering ? 'Refreshing...' : 'Refresh'}
              {hasNewData && (
                <span className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full animate-pulse"></span>
              )}
            </button>
          </div>
        </div>

        {/* New Data Notification */}
        {hasNewData && (
          <div className="bg-green-500/10 border border-green-500/20 rounded-md p-3 mb-6 animate-in slide-in-from-top-2">
            <p className="text-green-600 text-sm flex items-center justify-between">
              <span className="flex items-center">
                <span className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></span>
                New analysis data available
              </span>
              <button
                onClick={handleManualRefresh}
                className="text-xs bg-green-500 text-white px-2 py-1 rounded hover:bg-green-600 transition-colors"
              >
                Refresh Now
              </button>
            </p>
          </div>
        )}
        
        <AnalysisFilters
          filters={filters}
          setFilters={setFilters}
          uniqueTickers={uniqueTickers}
          uniqueStrategies={uniqueStrategies}
          isInitialLoading={isInitialLoading}
          isFiltering={isFiltering}
        />

        {/* Error Messages */}
        {Object.keys(dataErrors).length > 0 && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <h4 className="text-sm font-medium text-red-800 mb-2">Data Loading Issues</h4>
            <div className="text-xs text-red-700 space-y-1">
              {Object.entries(dataErrors).map(([key, error]) => (
                <p key={key}>• {error}</p>
              ))}
            </div>
            <button
              onClick={() => loadAnalysisData(true)}
              className="mt-2 text-xs text-red-700 hover:text-red-900 underline"
              disabled={isFiltering}
            >
              {isFiltering ? 'Retrying...' : 'Retry Loading'}
            </button>
          </div>
        )}

        {/* Debug Info - Development Only */}
        {process.env.NODE_ENV === 'development' && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
            <h4 className="text-sm font-medium text-yellow-800 mb-2">Debug Info</h4>
            <div className="text-xs text-yellow-700 space-y-1">
              <p>Loading: Initial={isInitialLoading.toString()}, Filtering={isFiltering.toString()}</p>
              <p>Data: Orders={orders.length} | Positions={allPositions.length} | Performance={tickerPerformance.length} | Filtered={filteredPositions.length}</p>
              <p>Tickers: {uniqueTickers.length > 0 ? uniqueTickers.slice(0, 5).join(', ') + (uniqueTickers.length > 5 ? '...' : '') : 'None'}</p>
              <p>Strategies: {uniqueStrategies.length > 0 ? uniqueStrategies.slice(0, 3).join(', ') + (uniqueStrategies.length > 3 ? '...' : '') : 'None'}</p>
              <p>Filters: {JSON.stringify(filters)}</p>
              <p>Errors: {Object.keys(dataErrors).join(', ') || 'None'}</p>
            </div>
          </div>
        )}

        <TickerPerformanceSection
          tickerPerformance={tickerPerformance}
          dataErrors={dataErrors}
          isInitialLoading={isInitialLoading}
          isFiltering={isFiltering}
          formatCurrency={formatCurrency}
          formatPercent={formatPercent}
          onRetry={() => loadAnalysisData(true)}
        />

        <FilteredPositionsSection
          filters={filters}
          filteredPositions={filteredPositions}
          dataErrors={dataErrors}
          isFiltering={isFiltering}
          positionsExpanded={positionsExpanded}
          setPositionsExpanded={setPositionsExpanded}
          formatCurrency={formatCurrency}
          formatPercent={formatPercent}
          onRetry={() => loadAnalysisData(true)}
        />

        <TradingHistorySection
          orders={orders}
          dataErrors={dataErrors}
          isInitialLoading={isInitialLoading}
          isFiltering={isFiltering}
          historyExpanded={historyExpanded}
          setHistoryExpanded={setHistoryExpanded}
          formatCurrency={formatCurrency}
          onRetry={() => loadAnalysisData(true)}
        />
      </div>
    </div>
  )
}