'use client'

import { useState, useEffect } from 'react'
import { getRolledOptionsChains, OptionsChain, RolledOptionsResponse, OptionsOrder, triggerRolledOptionsSync, getRolledOptionsSyncStatus, getRolledOptionsSymbols } from '@/lib/api'
import { ChainSummary } from './ui/ChainSummary'
import { SymbolLogo } from './ui/SymbolLogo'
import OptionsOrderLegs from './options/OptionsOrderLegs'

interface RolledOptionsSectionProps {
  formatCurrency: (value: number) => string
  formatPercent: (value: number) => string
}

export function RolledOptionsSection({ formatCurrency, formatPercent }: RolledOptionsSectionProps) {
  const [rolledOptions, setRolledOptions] = useState<RolledOptionsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expandedChains, setExpandedChains] = useState<Set<string>>(new Set())
  const [expandedOrders, setExpandedOrders] = useState<Set<string>>(new Set())
  const [selectedStatus, setSelectedStatus] = useState<'all' | 'active' | 'closed' | 'expired'>('all')
  const [selectedSymbol, setSelectedSymbol] = useState<string>('')
  const [selectedStrategy, setSelectedStrategy] = useState<string>('')
  const [currentPage, setCurrentPage] = useState(1)
  const [daysBack, setDaysBack] = useState(180) // Default to 180 days for better chain detection
  const [pageSize, setPageSize] = useState(25)
  const [sectionExpanded, setSectionExpanded] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [syncStatus, setSyncStatus] = useState<any>(null)
  const [syncError, setSyncError] = useState<string | null>(null)
  const [availableSymbols, setAvailableSymbols] = useState<string[]>([])
  const [availableStrategies, setAvailableStrategies] = useState<string[]>([])
  // Derived strategy options: union of API-provided and those present in current data
  const [strategyOptions, setStrategyOptions] = useState<string[]>([])

  useEffect(() => {
    setCurrentPage(1)
    setExpandedChains(new Set()) // Reset expanded chains when filters change
    setExpandedOrders(new Set()) // Reset expanded orders when filters change
    fetchRolledOptions(1)
    fetchSyncStatus() // Also fetch sync status when filters change
  }, [selectedStatus, selectedSymbol, selectedStrategy, daysBack, pageSize])

  // Fetch available symbols when component loads
  useEffect(() => {
    fetchAvailableSymbols()
  }, [])

  const fetchAvailableSymbols = async () => {
    try {
      const symbolsData = await getRolledOptionsSymbols()
      setAvailableSymbols(symbolsData.symbols)
      setAvailableStrategies(symbolsData.strategies || [])
    } catch (err) {
      console.error('Failed to fetch available symbols:', err)
      // Don't show error for symbols fetch failures, just use empty array
      setAvailableSymbols([])
      setAvailableStrategies([])
    }
  }

  const fetchSyncStatus = async () => {
    try {
      const status = await getRolledOptionsSyncStatus()
      setSyncStatus(status)
    } catch (err) {
      console.error('Failed to fetch sync status:', err)
      // Don't show error for sync status failures
    }
  }

  const handleSync = async (forceFullSync = false) => {
    try {
      setSyncing(true)
      setSyncError(null)
      
      await triggerRolledOptionsSync(forceFullSync)
      
      // Refresh sync status after triggering
      await fetchSyncStatus()
      
      // Optionally refresh data after a delay
      setTimeout(() => {
        fetchRolledOptions(currentPage)
        fetchSyncStatus()
        fetchAvailableSymbols() // Also refresh available symbols
      }, 3000) // Wait 3 seconds for processing to start
      
    } catch (err) {
      console.error('Error triggering sync:', err)
      setSyncError(err instanceof Error ? err.message : 'Failed to trigger sync')
    } finally {
      setSyncing(false)
    }
  }

  const fetchRolledOptions = async (page: number = 1) => {
    setLoading(true)
    setError(null)

    try {
      const params: any = { 
        days_back: daysBack,
        page,
        limit: pageSize
      }
      if (selectedStatus !== 'all') params.status = selectedStatus
      if (selectedSymbol) params.symbol = selectedSymbol
      if (selectedStrategy) params.strategy = selectedStrategy

      const data = await getRolledOptionsChains(params)
      setRolledOptions(data)
      setCurrentPage(page)
      // Update strategy options to include any strategies present in the loaded data
      try {
        const pageStrategies = new Set<string>()
        // Include chain-level initial strategies only (matches backend filter semantics)
        data.chains.forEach((chain) => {
          const initial = (chain as any).initial_strategy
          if (initial && typeof initial === 'string') pageStrategies.add(initial)
        })
        // Merge with API-provided strategies
        const merged = Array.from(new Set([...(availableStrategies || []), ...Array.from(pageStrategies)]))
          .filter(Boolean)
          .sort()
        setStrategyOptions(merged)
      } catch {
        // If anything goes wrong, fall back to API-provided strategies
        setStrategyOptions([...(availableStrategies || [])].sort())
      }
      // Reset expanded chains when new data is loaded to keep them collapsed by default
      if (page === 1) {
        setExpandedChains(new Set())
      }
    } catch (err) {
      console.error('Failed to fetch rolled options:', err)
      setError(err instanceof Error ? err.message : 'Failed to load rolled options')
    } finally {
      setLoading(false)
    }
  }

  const toggleChainExpansion = (chainId: string) => {
    const newExpanded = new Set(expandedChains)
    if (newExpanded.has(chainId)) {
      newExpanded.delete(chainId)
    } else {
      newExpanded.add(chainId)
    }
    setExpandedChains(newExpanded)
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-800'
      case 'closed': return 'bg-gray-100 text-gray-800'
      case 'expired': return 'bg-red-100 text-red-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString()
  }

  const formatDateTime = (dateStr: string | null) => {
    if (!dateStr) return 'N/A'
    return new Date(dateStr).toLocaleString()
  }

  const toggleOrderExpansion = (orderId: string) => {
    const newExpanded = new Set(expandedOrders)
    if (newExpanded.has(orderId)) {
      newExpanded.delete(orderId)
    } else {
      newExpanded.add(orderId)
    }
    setExpandedOrders(newExpanded)
  }

  // Convert OptionsOrder to HistoricalOptionsOrder format for compatibility
  const convertToHistoricalOrder = (order: OptionsOrder): any => {
    return {
      order_id: order.order_id,
      underlying_symbol: order.underlying_symbol || order.chain_symbol,
      chain_symbol: order.chain_symbol || order.underlying_symbol,
      strike_price: order.strike_price,
      expiration_date: order.expiration_date,
      option_type: order.option_type,
      side: order.legs?.[0]?.side || 'buy',
      transaction_side: order.transaction_side,
      position_effect: order.position_effect,
      direction: order.direction,
      quantity: order.quantity,
      processed_quantity: order.quantity,
      price: order.price,
      premium: order.premium,
      processed_premium: order.processed_premium || order.premium * order.quantity,
      processed_premium_direction: order.direction,
      state: order.state,
      created_at: order.created_at,
      updated_at: order.updated_at,
      type: 'limit',
      legs_count: order.legs?.length || 1,
      legs_details: order.legs || [],
      executions_count: 1,
      strategy: order.strategy,
      opening_strategy: order.opening_strategy,
      closing_strategy: order.closing_strategy
    }
  }

  // Use availableSymbols state instead of deriving from current page data
  const uniqueSymbols = availableSymbols
  
  // Keep strategy options in sync when API-provided list changes (e.g., after sync)
  useEffect(() => {
    // If we already merged with page data, keep that; otherwise, seed from API list
    if (!rolledOptions) {
      setStrategyOptions([...(availableStrategies || [])].sort())
    } else {
      // Recompute merged list including current page (initial) strategies
      try {
        const pageStrategies = new Set<string>()
        rolledOptions.chains.forEach((chain) => {
          const initial = (chain as any).initial_strategy
          if (initial && typeof initial === 'string') pageStrategies.add(initial)
        })
        const merged = Array.from(new Set([...(availableStrategies || []), ...Array.from(pageStrategies)]))
          .filter(Boolean)
          .sort()
        setStrategyOptions(merged)
      } catch {
        setStrategyOptions([...(availableStrategies || [])].sort())
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [availableStrategies])

  if (loading && !rolledOptions) {
    const estimatedTime = daysBack <= 30 ? "1-2 minutes" : 
                         daysBack <= 90 ? "2-3 minutes" : 
                         "3-5 minutes"
    
    return (
      <div className="space-y-4">
        <h3 className="text-lg font-medium">Rolled Options Chains</h3>
        <div className="text-center py-8">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary mb-4"></div>
          <p className="text-muted-foreground mb-2">
            Analyzing rolled options chains for {daysBack} days...
          </p>
          <p className="text-sm text-muted-foreground">
            This complex analysis typically takes {estimatedTime}
          </p>
          <p className="text-xs text-muted-foreground mt-2">
            Processing historical orders and identifying roll patterns
          </p>
        </div>
      </div>
    )
  }

  if (error) {
    const isTimeout = error.includes("timeout") || error.includes("Request timeout")
    
    return (
      <div className="space-y-4">
        <h3 className="text-lg font-medium">Rolled Options Chains</h3>
        <div className="bg-destructive/10 border border-destructive/20 rounded-md p-4">
          <p className="text-destructive text-sm font-medium mb-2">{error}</p>
          
          {isTimeout && (
            <div className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded text-sm">
              <p className="text-blue-800 font-medium mb-2">Suggestions to avoid timeouts:</p>
              <ul className="text-blue-700 space-y-1 text-xs">
                <li>• Reduce the date range to 30 days or less</li>
                <li>• Use pagination with smaller page sizes (10-25 items)</li>
                <li>• Filter by specific symbol if analyzing one stock</li>
                <li>• Try refreshing - the data may be cached from previous requests</li>
              </ul>
            </div>
          )}
          
          <div className="flex gap-2">
            <button
              onClick={() => fetchRolledOptions(1)}
              className="text-xs text-destructive hover:underline"
            >
              Try again
            </button>
            {daysBack > 30 && (
              <button
                onClick={() => {
                  setDaysBack(30)
                  fetchRolledOptions(1)
                }}
                className="text-xs text-blue-600 hover:underline"
              >
                Reduce to 30 days and retry
              </button>
            )}
          </div>
        </div>
      </div>
    )
  }

  if (!rolledOptions) {
    return null
  }

  return (
    <div className="space-y-6">
      <div>
        <button
          onClick={() => setSectionExpanded(!sectionExpanded)}
          className="flex items-center justify-between w-full p-4 bg-muted/50 rounded-lg hover:bg-muted transition-colors"
        >
          <h3 className="text-lg font-medium">Rolled Options Chains</h3>
          <svg
            className={`w-5 h-5 transition-transform ${sectionExpanded ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m19 9-7 7-7-7" />
          </svg>
        </button>
        
        {sectionExpanded && (
          <div className="mt-4 space-y-6">
            {/* Performance Warning removed as requested */}

            {/* Filters */}
            <div className="flex flex-wrap gap-4 mb-6">
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">Days Back</label>
                <select
                  value={daysBack}
                  onChange={(e) => setDaysBack(Number(e.target.value))}
                  className="px-3 py-2 border border-input bg-background rounded-md text-sm"
                >
                  <option value={7}>7 days</option>
                  <option value={30}>30 days</option>
                  <option value={60}>60 days</option>
                  <option value={90}>90 days</option>
                  <option value={180}>180 days (recommended)</option>
                  <option value={365}>365 days (slower)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">Status</label>
                <select
                  value={selectedStatus}
                  onChange={(e) => setSelectedStatus(e.target.value as any)}
                  className="px-3 py-2 border border-input bg-background rounded-md text-sm"
                >
                  <option value="all">All Status</option>
                  <option value="active">Active</option>
                  <option value="closed">Closed</option>
                  <option value="expired">Expired</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">Symbol</label>
                <select
                  value={selectedSymbol}
                  onChange={(e) => setSelectedSymbol(e.target.value)}
                  className="px-3 py-2 border border-input bg-background rounded-md text-sm"
                >
                  <option value="">All Symbols</option>
                  {uniqueSymbols.map(symbol => (
                    <option key={symbol} value={symbol}>{symbol}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">Strategy</label>
                <select
                  value={selectedStrategy}
                  onChange={(e) => setSelectedStrategy(e.target.value)}
                  className="px-3 py-2 border border-input bg-background rounded-md text-sm"
                >
                  <option value="">All Strategies</option>
                  {strategyOptions.map(strategy => (
                    <option key={strategy} value={strategy}>{strategy}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-1">Per Page</label>
                <select
                  value={pageSize}
                  onChange={(e) => setPageSize(Number(e.target.value))}
                  className="px-3 py-2 border border-input bg-background rounded-md text-sm"
                >
                  <option value={10}>10</option>
                  <option value={25}>25</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                </select>
              </div>
              <div className="ml-auto flex flex-col items-end gap-1">
                <div className="flex items-end gap-2">
                  <button
                    onClick={() => fetchRolledOptions(1)}
                    className="px-3 py-1.5 text-xs md:text-sm bg-secondary text-secondary-foreground rounded-md border border-border hover:bg-secondary/80 transition-colors"
                  >
                    {loading ? 'Refreshing…' : 'Refresh'}
                  </button>
                  <button
                    onClick={() => handleSync(false)}
                    disabled={syncing}
                    className="px-3 py-1.5 text-xs md:text-sm bg-secondary text-secondary-foreground rounded-md border border-border hover:bg-secondary/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {syncing ? 'Syncing…' : 'Sync Chains'}
                  </button>
                  <button
                    onClick={() => handleSync(true)}
                    disabled={syncing}
                    className="px-3 py-1.5 text-xs md:text-sm bg-secondary text-secondary-foreground rounded-md border border-border hover:bg-secondary/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {syncing ? 'Syncing…' : 'Full Sync'}
                  </button>
                </div>
                {(syncing || syncError || syncStatus) && (
                  <div className="text-xs text-muted-foreground flex items-center gap-2 mt-1">
                    {syncing ? (
                      <>
                        <span className="inline-flex h-2 w-2 rounded-full bg-blue-500 animate-pulse"></span>
                        <span>Processing rolled options chains… (2–5 minutes)</span>
                      </>
                    ) : syncError ? (
                      <>
                        <span className="inline-flex h-2 w-2 rounded-full bg-red-500"></span>
                        <span className="text-red-600 dark:text-red-400">Sync error: {syncError}</span>
                      </>
                    ) : syncStatus ? (
                      <>
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-green-100 text-green-800 border border-green-200">🟢 Chains up to date</span>
                        {syncStatus.last_successful && (
                          <span>
                            Last sync: {new Date(syncStatus.last_successful).toLocaleString()} (
                            {syncStatus.data_age_minutes < 60 
                              ? `${syncStatus.data_age_minutes}m ago` 
                              : `${Math.round((syncStatus.data_age_minutes || 0) / 60)}h ago`}
                            )
                          </span>
                        )}
                      </>
                    ) : null}
                  </div>
                )}
              </div>
            </div>

            {/* Summary Cards (moved below filters) */}
            <ChainSummary 
              summary={rolledOptions.summary} 
              formatCurrency={formatCurrency}
              className="mb-6"
            />

            {/* Display Info */}
            <div className="flex justify-between items-center mb-4">
              <div className="text-sm text-muted-foreground">
                Showing {rolledOptions.chains.length} of {rolledOptions.summary.total_chains} chains
              </div>
              {rolledOptions.pagination && (
                <div className="text-sm text-muted-foreground">
                  Page {currentPage} of {rolledOptions.pagination.total_pages}
                </div>
              )}
            </div>

            {/* Sync Status Indicator */}
            {(syncStatus || syncError || syncing) && (
              <div className="mb-4 p-3 rounded-lg border">
                {syncing && (
                  <div className="flex items-center text-blue-600 dark:text-blue-400">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
                    <span className="text-sm font-medium">Processing rolled options chains...</span>
                    <span className="text-xs text-muted-foreground ml-2">(2-5 minutes)</span>
                  </div>
                )}
                {syncError && (
                  <div className="flex items-center text-red-600 dark:text-red-400">
                    <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                    <span className="text-sm font-medium">Sync Error: {syncError}</span>
                  </div>
                )}
                {syncStatus && !syncing && !syncError && (
                  <div className="flex items-center justify-between">
                    <div className="flex items-center text-green-600 dark:text-green-400">
                      <svg className="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      <span className="text-sm font-medium">Chains up to date</span>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {syncStatus.last_successful && (
                        <span>Last sync: {new Date(syncStatus.last_successful).toLocaleString()}</span>
                      )}
                      {syncStatus.data_age_minutes && (
                        <span className="ml-2">
                          ({syncStatus.data_age_minutes < 60 
                            ? `${syncStatus.data_age_minutes}m ago`
                            : `${Math.round(syncStatus.data_age_minutes / 60)}h ago`})
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Filtered Chains Summary removed as requested */}

            {/* Chains List */}
            {rolledOptions.chains.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-muted-foreground mb-4">No rolled options chains found.</p>
                <p className="text-sm text-muted-foreground">
                  {loading ? 'Loading chains...' : 'Try adjusting your filters or increasing the date range.'}
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                {rolledOptions.chains.map((chain) => (
                  <div key={chain.chain_id} className="bg-muted/50 rounded-lg overflow-hidden">
                    <button
                      onClick={() => toggleChainExpansion(chain.chain_id)}
                      className="w-full p-4 text-left hover:bg-muted transition-colors"
                    >
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <div className="flex items-center gap-4 mb-2">
                            <SymbolLogo 
                              symbol={chain.underlying_symbol} 
                              size="lg" 
                              showText={true}
                              className="font-medium text-lg"
                            />
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(chain.status)}`}>
                              {chain.status.toUpperCase()}
                            </span>
                            {/* Strategy Badge */}
                            {(() => {
                              // Use chain's initial_strategy if available, otherwise first order's strategy
                              const strategy = (chain as any).initial_strategy || 
                                              (chain.orders && chain.orders.length > 0 && chain.orders[0].strategy);
                              return strategy && (
                                <span className="px-2 py-1 rounded-full text-xs font-medium bg-purple-100 dark:bg-purple-900/40 text-purple-800 dark:text-purple-200 border border-purple-200 dark:border-purple-700">
                                  {strategy}
                                </span>
                              );
                            })()}
                            <div className="text-sm text-muted-foreground">
                              {chain.orders.length} orders ({chain.roll_count || 0} rolls)
                            </div>
                          </div>
                          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                            <div>
                              <span className="text-muted-foreground">Last Activity:</span>
                              <span className="font-medium ml-1">{formatDate(chain.last_activity_date)}</span>
                            </div>
                            <div>
                              <span className="text-muted-foreground">Started:</span>
                              <span className="font-medium ml-1">{formatDate(chain.start_date)}</span>
                            </div>
                            <div>
                              <span className="text-muted-foreground">Net Premium:</span>
                              <span className={`font-medium ml-1 ${chain.net_premium >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                                {formatCurrency(chain.net_premium)}
                              </span>
                            </div>
                          </div>
                        </div>
                        <svg
                          className={`w-5 h-5 transition-transform ${expandedChains.has(chain.chain_id) ? 'rotate-180' : ''}`}
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m19 9-7 7-7-7" />
                        </svg>
                      </div>
                    </button>

                    {/* Expanded Chain Details */}
                    {expandedChains.has(chain.chain_id) && (
                      <div className="border-t border-border p-4 bg-background/50">
                        <div className="space-y-4">
                          {/* Orders History - using exact OptionsOrderRow format */}
                          <div>
                            <h4 className="font-medium mb-4">
                              Orders in Chain ({chain.orders.length})
                              {chain.status === 'active' && (
                                <span className="ml-2 text-xs px-2 py-1 rounded bg-green-100 text-green-800">
                                  ACTIVE
                                </span>
                              )}
                            </h4>
                            <div className="space-y-3">
                              {chain.orders.map((order, index) => {
                                const historicalOrder = convertToHistoricalOrder(order)
                                const isExpanded = expandedOrders.has(order.order_id)
                                
                                return (
                                  <div key={index} className="bg-gradient-to-r from-card/50 to-card/80 rounded-xl overflow-hidden border border-muted/30 shadow-sm hover:shadow-md transition-all duration-200">
                                    {/* Order Summary Row */}
                                    <button
                                      onClick={() => toggleOrderExpansion(order.order_id)}
                                      className="w-full p-4 text-left hover:bg-muted/30 transition-all duration-200 flex items-center justify-between group"
                                    >
                                      <div className="flex-1">
                                        <div className="flex items-center mb-2">
                                          <SymbolLogo 
                                            symbol={order.chain_symbol || order.underlying_symbol}
                                            size="sm" 
                                            showText={true}
                                            className="font-semibold text-base"
                                          />
                                        </div>
                                        
                                        <div className="flex flex-wrap items-center gap-1.5 mb-2">
                                          {/* Action Badge - Show ROLL if roll_details exists, otherwise show side + position_effect */}
                                          {order.roll_details ? (
                                            <span className="text-xs px-2 py-0.5 rounded font-medium bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300">
                                              ROLL
                                            </span>
                                          ) : (historicalOrder.side || order.legs?.[0]?.side) && (
                                            <span className={`text-xs px-2 py-0.5 rounded font-medium ${
                                              (historicalOrder.side || order.legs?.[0]?.side)?.toLowerCase() === 'buy'
                                                ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
                                                : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'
                                            }`}>
                                              {(historicalOrder.side || order.legs?.[0]?.side)?.toUpperCase()} {(order.position_effect || order.legs?.[0]?.position_effect)?.toUpperCase()}
                                            </span>
                                          )}
                                          
                                          {/* Contracts Badge */}
                                          {order.quantity && (
                                            <span className="text-xs px-2 py-0.5 rounded font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300">
                                              {order.quantity} contracts
                                            </span>
                                          )}
                                          
                                          {/* Strike Price Badge */}
                                          {order.strike_price && (
                                            <span className="text-xs px-2 py-0.5 rounded font-medium bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300">
                                              ${order.strike_price} {order.option_type?.toUpperCase()}
                                            </span>
                                          )}
                                          
                                          {/* Expiration Badge */}
                                          {(order.expiration_date || order.legs?.[0]?.expiration_date) && (
                                            <span className="text-xs px-2 py-0.5 rounded font-medium bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300">
                                              {order.expiration_date || order.legs?.[0]?.expiration_date}
                                            </span>
                                          )}
                                          
                                          {/* Strategy Badge */}
                                          {order.strategy && (
                                            <span className="text-xs px-2 py-0.5 rounded font-medium bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300">
                                              {order.strategy}
                                            </span>
                                          )}
                                          
                                          {/* Legs Badge */}
                                          <span className="text-xs px-2 py-0.5 rounded font-medium bg-slate-100 text-slate-800 dark:bg-slate-900/30 dark:text-slate-300">
                                            {order.legs?.length || 1} {(order.legs?.length || 1) === 1 ? 'leg' : 'legs'}
                                          </span>
                                        </div>
                                        
                                        <div className="text-xs text-muted-foreground mt-1">
                                          {formatDateTime(order.created_at)}
                                        </div>
                                      </div>
                                      
                                      <div className="text-right space-y-1">
                                        <div className={`font-bold text-lg ${
                                          (order.direction === 'credit' ? 1 : -1) * (order.processed_premium || order.premium * order.quantity || 0) >= 0 
                                            ? 'text-green-600 dark:text-green-400' 
                                            : 'text-red-600 dark:text-red-400'
                                        }`}>
                                          {order.direction === 'credit' ? '+' : '-'}{formatCurrency(order.processed_premium || order.premium * order.quantity || 0)}
                                        </div>
                                        <div className="text-xs text-muted-foreground">
                                          {formatCurrency((order.processed_premium || order.premium * order.quantity || 0) / Math.max(order.quantity || 1, 1))}/contract
                                        </div>
                                      </div>
                                      
                                      <svg
                                        className={`w-5 h-5 ml-3 transition-all duration-200 group-hover:scale-110 ${
                                          isExpanded ? 'rotate-180' : ''
                                        }`}
                                        fill="none"
                                        stroke="currentColor"
                                        viewBox="0 0 24 24"
                                      >
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m19 9-7 7-7-7" />
                                      </svg>
                                    </button>
                                    
                                    {/* Expanded Details */}
                                    {isExpanded && (
                                      <OptionsOrderLegs 
                                        order={historicalOrder}
                                        formatCurrency={formatCurrency}
                                      />
                                    )}
                                  </div>
                                )
                              })}
                            </div>
                          </div>

                          {/* Premium & P&L Breakdown */}
                          <div>
                            <h4 className="font-medium mb-2">Premium & P&L Breakdown</h4>
                            <div className="bg-muted/30 rounded p-3 text-sm">
                              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                                <div>
                                  <span className="text-muted-foreground">Credits Collected:</span>
                                  <span className="font-medium ml-1 text-green-600 dark:text-green-400">
                                    {formatCurrency(chain.total_credits_collected)}
                                  </span>
                                </div>
                                <div>
                                  <span className="text-muted-foreground">Debits Paid:</span>
                                  <span className="font-medium ml-1 text-red-600 dark:text-red-400">
                                    {formatCurrency(chain.total_debits_paid)}
                                  </span>
                                </div>
                                <div>
                                  <span className="text-muted-foreground">Net Premium:</span>
                                  <span className={`font-medium ml-1 ${chain.net_premium >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                                    {formatCurrency(chain.net_premium)}
                                  </span>
                                </div>
                                <div>
                                  <span className="text-muted-foreground">Total P&L:</span>
                                  <span className={`font-medium ml-1 ${chain.total_pnl >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                                    {formatCurrency(chain.total_pnl)}
                                  </span>
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Bottom Pagination */}
            {rolledOptions.pagination && rolledOptions.chains.length > 0 && (
              <div className="flex justify-center items-center space-x-2 mt-6">
                <button
                  onClick={() => fetchRolledOptions(1)}
                  disabled={currentPage === 1 || loading}
                  className="px-3 py-1 text-sm border border-input rounded hover:bg-muted disabled:opacity-50"
                >
                  First
                </button>
                <button
                  onClick={() => fetchRolledOptions(currentPage - 1)}
                  disabled={!rolledOptions.pagination.has_prev || loading}
                  className="px-3 py-1 text-sm border border-input rounded hover:bg-muted disabled:opacity-50"
                >
                  Previous
                </button>
                <span className="text-sm px-2">
                  Page {currentPage} of {rolledOptions.pagination.total_pages}
                </span>
                <button
                  onClick={() => fetchRolledOptions(currentPage + 1)}
                  disabled={!rolledOptions.pagination.has_next || loading}
                  className="px-3 py-1 text-sm border border-input rounded hover:bg-muted disabled:opacity-50"
                >
                  Next
                </button>
                <button
                  onClick={() => fetchRolledOptions(rolledOptions.pagination?.total_pages || 1)}
                  disabled={currentPage === (rolledOptions.pagination?.total_pages || 1) || loading}
                  className="px-3 py-1 text-sm border border-input rounded hover:bg-muted disabled:opacity-50"
                >
                  Last
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
