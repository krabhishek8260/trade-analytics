'use client'

import { useState, useEffect, useCallback } from 'react'
import { 
  getOptionsOrders, 
  getOptionsOrdersSyncStatus, 
  triggerOptionsOrdersSync,
  PaginatedOptionsOrdersResponse, 
  HistoricalOptionsOrder,
  OptionsOrdersSyncStatus 
} from '@/lib/api'
import { 
  OptionsOrdersList, 
  SyncStatusIndicator, 
  SyncProgressIndicator 
} from './options'
import { SymbolLogo } from '@/components/ui/SymbolLogo'

interface OptionsHistorySectionProps {
  formatCurrency: (value: number) => string
  formatPercent: (value: number) => string
}

interface ExpandedOrderState {
  [orderId: string]: boolean
}

export default function OptionsHistorySection({ 
  formatCurrency, 
  formatPercent
}: OptionsHistorySectionProps) {
  console.log('OptionsHistorySection: Component mounted')
  console.log('OptionsHistorySection: props received', { formatCurrency: !!formatCurrency, formatPercent: !!formatPercent })

  
  // Core data state
  const [ordersData, setOrdersData] = useState<PaginatedOptionsOrdersResponse | null>(null)
  const [syncStatus, setSyncStatus] = useState<OptionsOrdersSyncStatus | null>(null)
  const [loading, setLoading] = useState(false) // Start as false since we don't load until expanded
  
  console.log('OptionsHistorySection: Every render - current state:', { 
    loading, 
    hasOrdersData: !!ordersData,
    ordersDataKeys: ordersData ? Object.keys(ordersData) : null
  })
  const [syncing, setSyncing] = useState(false)
  const [showProgress, setShowProgress] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // UI state - starts collapsed, can be toggled
  const [historyExpanded, setHistoryExpanded] = useState(false)
  const [expandedOrders, setExpandedOrders] = useState<ExpandedOrderState>({})
  const [currentPage, setCurrentPage] = useState(1)
  
  // Filters
  const [filters, setFilters] = useState({
    symbol: '',
    state: 'filled', // Still filter to filled orders in API, just don't show the badge
    strategy: '',
    sort_by: 'created_at',
    sort_order: 'desc'
  })
  
  console.log('OptionsHistorySection: State initialized', { 
    currentPage, 
    filters, 
    loading, 
    ordersData: ordersData,
    ordersDataType: typeof ordersData,
    ordersDataLength: ordersData?.data?.length
  })

  const fetchOrdersData = useCallback(async (page = 1) => {
    try {
      console.log('OptionsHistorySection: fetchOrdersData called', { page, filters })
      setLoading(true)
      setError(null)
      
      const [ordersResponse, statusResponse] = await Promise.all([
        getOptionsOrders({
          page,
          limit: 20,
          underlying_symbol: filters.symbol || undefined,
          state: filters.state || undefined,
          strategy: filters.strategy || undefined,
          sort_by: filters.sort_by,
          sort_order: filters.sort_order
        }),
        getOptionsOrdersSyncStatus().catch(() => null) // Don't fail if sync status unavailable
      ])
      
      console.log('OptionsHistorySection: API response received', { 
        ordersCount: ordersResponse?.data?.length || 0, 
        total: ordersResponse?.pagination?.total || 0,
        hasData: !!ordersResponse?.data,
        fullResponse: ordersResponse
      })
      setOrdersData(ordersResponse)
      if (statusResponse) {
        setSyncStatus(statusResponse)
      }
    } catch (err) {
      console.error('Error loading options orders:', err)
      setError(err instanceof Error ? err.message : 'Failed to fetch options orders')
    } finally {
      setLoading(false)
    }
  }, [filters])

  // Auto-load data only when expanded
  const [autoLoaded, setAutoLoaded] = useState(false)
  
  console.log('OptionsHistorySection: Auto-load check', { autoLoaded, loading, historyExpanded })
  
  useEffect(() => {
    try {
      if (!autoLoaded && historyExpanded) {
        console.log('OptionsHistorySection: Triggering auto-load (expanded)')
        setAutoLoaded(true)
        // Use the proper API function instead of direct fetch
        fetchOrdersData(1)
      }
    } catch (error) {
      console.error('OptionsHistorySection: Error in useEffect:', error)
    }
  }, [autoLoaded, historyExpanded, fetchOrdersData])

  const handleSync = async (forceFullSync = false) => {
    try {
      setSyncing(true)
      setShowProgress(true)
      setError(null)
      
      await triggerOptionsOrdersSync(forceFullSync, forceFullSync ? 365 : 30)
      
      // Note: Progress indicator will handle completion and data refresh
      
    } catch (err) {
      console.error('Error triggering sync:', err)
      setError(err instanceof Error ? err.message : 'Failed to sync orders')
      setSyncing(false)
      setShowProgress(false)
    }
  }

  const handleSyncComplete = () => {
    setSyncing(false)
    setShowProgress(false)
    fetchOrdersData(currentPage)
  }

  const toggleHistoryExpanded = () => {
    setHistoryExpanded(prev => !prev)
    // Load data when expanding for the first time
    if (!historyExpanded && !autoLoaded) {
      setAutoLoaded(true)
      fetchOrdersData(1)
    }
  }

  const toggleOrderExpansion = (orderId: string) => {
    setExpandedOrders(prev => ({
      ...prev,
      [orderId]: !prev[orderId]
    }))
  }

  const handleFilterChange = (key: string, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }))
    setCurrentPage(1) // Reset to first page when filtering
  }

  const formatDateTime = (dateStr: string | null) => {
    if (!dateStr) return 'N/A'
    try {
      return new Date(dateStr).toLocaleString()
    } catch {
      return dateStr
    }
  }

  if (loading && !ordersData) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between mb-3">
          <div className="h-6 bg-muted/50 rounded w-48 animate-pulse"></div>
          <div className="h-6 bg-muted/50 rounded w-32 animate-pulse"></div>
        </div>
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-16 bg-muted/50 rounded animate-pulse"></div>
          ))}
        </div>
      </div>
    )
  }

  if (error && !ordersData) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-medium">Options History</h3>
          <button
            onClick={() => handleSync(true)}
            disabled={syncing}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50"
          >
            {syncing ? 'Syncing...' : 'Sync Orders'}
          </button>
        </div>
        <div className="text-center py-8">
          <p className="text-red-600 mb-2">Error loading options orders</p>
          <p className="text-sm text-muted-foreground">{error}</p>
        </div>
      </div>
    )
  }

  // Show collapsed state if not expanded
  if (!historyExpanded) {
    return (
      <div className="space-y-4">
        <div 
          className="flex items-center justify-between p-4 bg-gradient-to-r from-muted/10 to-muted/20 rounded-xl border border-muted/30 cursor-pointer hover:bg-muted/30 transition-all"
          onClick={toggleHistoryExpanded}
        >
          <div className="flex items-center space-x-3">
            <div className="text-xl">📈</div>
            <div>
              <h3 className="text-lg font-semibold text-foreground">
                Options History
              </h3>
              <p className="text-sm text-muted-foreground">
                View your options trading history and orders
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2 text-muted-foreground">
            <span className="text-sm">Click to expand</span>
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </div>
      </div>
    )
  }

  const orders = ordersData?.data || []
  const pagination = ordersData?.pagination || { total: 0, page: 1, total_pages: 1, has_next: false, has_prev: false }

  if (orders.length === 0 && !syncing) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-medium">Options History</h3>
          <button
            onClick={() => handleSync(true)}
            disabled={syncing}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50"
          >
            Sync Orders
          </button>
        </div>
        <div className="text-center py-8">
          <p className="text-muted-foreground mb-4">No options orders found.</p>
          <p className="text-sm text-muted-foreground">
            {syncStatus?.sync_status === 'sync_needed' 
              ? 'Click "Sync Orders" to load your trading history.'
              : 'Your options orders will appear here when available.'
            }
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header with sync controls */}
      <div className="flex items-center justify-between mb-6">
        <div 
          className="flex-1 cursor-pointer"
          onClick={toggleHistoryExpanded}
        >
          <div className="flex items-center space-x-2">
            <svg className="w-4 h-4 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
            </svg>
            <h3 className="text-xl font-semibold text-foreground">
              Options History
            </h3>
          </div>
          <p className="text-sm text-muted-foreground mt-1 ml-6">
            {pagination.total} total orders • Page {currentPage} of {pagination.total_pages}
          </p>
        </div>
        
        {/* Sync controls */}
        <div className="flex items-center space-x-2">
          <SyncStatusIndicator />
          <button
            onClick={() => {
              console.log('OptionsHistorySection: Refresh button clicked')
              fetchOrdersData(currentPage)
            }}
            disabled={loading}
            className="px-3 py-2 text-sm bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/80 disabled:opacity-50"
          >
            {loading ? 'Loading...' : 'Refresh'}
          </button>
          <button
            onClick={() => handleSync(true)}
            disabled={syncing}
            className="px-3 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50"
          >
            Full Sync
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 p-4 bg-gradient-to-r from-muted/20 to-muted/30 rounded-xl border border-muted/40">
        <input
          type="text"
          placeholder="🔍 Symbol (e.g., AAPL)"
          value={filters.symbol}
          onChange={(e) => handleFilterChange('symbol', e.target.value)}
          className="px-4 py-2 border-2 border-muted/40 rounded-lg focus:border-primary/50 focus:ring-2 focus:ring-primary/20 transition-all"
        />
        <select
          value={filters.strategy}
          onChange={(e) => handleFilterChange('strategy', e.target.value)}
          className="px-4 py-2 border-2 border-muted/40 rounded-lg focus:border-primary/50 focus:ring-2 focus:ring-primary/20 transition-all"
        >
          <option value="">📊 All Strategies</option>
          <option value="covered_call">Covered Call</option>
          <option value="cash_secured_put">Cash Secured Put</option>
          <option value="iron_condor">Iron Condor</option>
          <option value="straddle">Straddle</option>
        </select>
        <input
          type="date"
          placeholder="📅 Date Range"
          className="px-4 py-2 border-2 border-muted/40 rounded-lg focus:border-primary/50 focus:ring-2 focus:ring-primary/20 transition-all"
        />
        <select
          value={`${filters.sort_by}_${filters.sort_order}`}
          onChange={(e) => {
            const [sortBy, sortOrder] = e.target.value.split('_')
            setFilters(prev => ({ ...prev, sort_by: sortBy, sort_order: sortOrder }))
            setCurrentPage(1)
          }}
          className="px-4 py-2 border-2 border-muted/40 rounded-lg focus:border-primary/50 focus:ring-2 focus:ring-primary/20 transition-all"
        >
          <option value="created_at_desc">⬇️ Newest First</option>
          <option value="created_at_asc">⬆️ Oldest First</option>
          <option value="processed_premium_desc">💰 Highest Premium</option>
          <option value="processed_premium_asc">💸 Lowest Premium</option>
        </select>
      </div>

      {/* Sync Progress Indicator */}
      {showProgress && (
        <SyncProgressIndicator 
          isVisible={showProgress}
          onComplete={handleSyncComplete}
          className="mb-4"
        />
      )}

      {/* Orders List */}
      <div className="space-y-3">
        <OptionsOrdersList
          orders={orders}
          loading={loading}
          expandedOrders={expandedOrders}
          onOrderToggle={toggleOrderExpansion}
          formatCurrency={formatCurrency}
          formatDateTime={formatDateTime}
        />
          
        {/* Pagination */}
        {pagination.total_pages > 1 && (
          <div className="flex items-center justify-between mt-6 p-4 bg-gradient-to-r from-muted/10 to-muted/20 rounded-xl border border-muted/30">
            <div className="text-sm text-muted-foreground">
              📄 Showing <span className="font-medium">{((currentPage - 1) * 20) + 1}</span> to <span className="font-medium">{Math.min(currentPage * 20, pagination.total)}</span> of <span className="font-medium">{pagination.total}</span> orders
            </div>
            <div className="flex space-x-2">
                <button
                  onClick={() => {
                    const newPage = Math.max(1, currentPage - 1)
                    console.log('OptionsHistorySection: Previous page clicked, going to page:', newPage)
                    setCurrentPage(newPage)
                    fetchOrdersData(newPage)
                  }}
                  disabled={!pagination.has_prev || loading}
                  className="px-4 py-2 text-sm bg-secondary/80 hover:bg-secondary text-secondary-foreground rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm hover:shadow-md"
                >
                  ← Previous
                </button>
                <span className="px-4 py-2 text-sm bg-primary/10 text-primary rounded-lg font-medium">
                  {currentPage} of {pagination.total_pages}
                </span>
                <button
                  onClick={() => {
                    const newPage = Math.min(pagination.total_pages, currentPage + 1)
                    console.log('OptionsHistorySection: Next page clicked, going to page:', newPage)
                    setCurrentPage(newPage)
                    fetchOrdersData(newPage)
                  }}
                  disabled={!pagination.has_next || loading}
                  className="px-4 py-2 text-sm bg-secondary/80 hover:bg-secondary text-secondary-foreground rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm hover:shadow-md"
                >
                  Next →
                </button>
            </div>
          </div>
        )}
          
        {/* Data source indicator */}
        {ordersData?.data_source && (
          <div className="text-xs text-muted-foreground text-center mt-3 p-2 bg-muted/20 rounded-lg border border-muted/30">
            💾 Data source: {ordersData.data_source === 'database' ? 'Local database' : ordersData.data_source === 'api_fallback' ? 'Robinhood API (fallback)' : ordersData.data_source}
          </div>
        )}
      </div>
    </div>
  )
}