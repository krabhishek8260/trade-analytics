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
  
  // Data State
  const [orders, setOrders] = useState<HistoricalOptionsOrder[]>([])
  const [tickerPerformance, setTickerPerformance] = useState<TickerPerformance[]>([])
  const [filteredPositions, setFilteredPositions] = useState<OptionPosition[]>([])
  const [allPositions, setAllPositions] = useState<OptionPosition[]>([])
  
  // Loading States
  const [isInitialLoading, setIsInitialLoading] = useState(true)
  const [isFiltering, setIsFiltering] = useState(false)
  const [dataErrors, setDataErrors] = useState<{[key: string]: string}>({})
  
  // Filters
  const [filters, setFilters] = useState<AnalysisFilters>({
    ticker: '',
    strategy: '',
    positionType: '',
    daysBack: 30,
    orderState: 'filled'
  })

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
        <h2 className="text-xl font-semibold mb-4">Trading Analysis & History</h2>
        
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