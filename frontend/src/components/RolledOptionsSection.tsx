'use client'

import { useState, useEffect } from 'react'
import { getRolledOptionsChains, OptionsChain, RolledOptionsResponse, OptionsOrder } from '@/lib/api'
import { ChainSummary } from './ui/ChainSummary'

interface RolledOptionsSectionProps {
  formatCurrency: (value: number) => string
  formatPercent: (value: number) => string
}

export function RolledOptionsSection({ formatCurrency, formatPercent }: RolledOptionsSectionProps) {
  const [rolledOptions, setRolledOptions] = useState<RolledOptionsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expandedChains, setExpandedChains] = useState<Set<string>>(new Set())
  const [selectedStatus, setSelectedStatus] = useState<'all' | 'active' | 'closed' | 'expired'>('all')
  const [selectedSymbol, setSelectedSymbol] = useState<string>('')
  const [currentPage, setCurrentPage] = useState(1)
  const [daysBack, setDaysBack] = useState(30) // Default to 30 days for faster loading
  const [pageSize, setPageSize] = useState(25)
  const [sectionExpanded, setSectionExpanded] = useState(false)

  useEffect(() => {
    setCurrentPage(1)
    setExpandedChains(new Set()) // Reset expanded chains when filters change
    fetchRolledOptions(1)
  }, [selectedStatus, selectedSymbol, daysBack, pageSize])

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

      const data = await getRolledOptionsChains(params)
      setRolledOptions(data)
      setCurrentPage(page)
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

  const uniqueSymbols = rolledOptions?.chains.map(chain => chain.underlying_symbol)
    .filter((value, index, self) => self.indexOf(value) === index)
    .sort() || []

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
            {/* Summary Cards */}
            <ChainSummary 
              summary={rolledOptions.summary} 
              formatCurrency={formatCurrency}
              className="mb-6"
            />

            {/* Performance Warning */}
            {daysBack > 90 && (
              <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                <div className="flex items-center">
                  <svg className="w-5 h-5 text-yellow-400 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                  <div className="text-sm">
                    <p className="text-yellow-800 font-medium">
                      Large date range selected ({daysBack} days)
                    </p>
                    <p className="text-yellow-700">
                      This may take 2-5 minutes to load. Consider using smaller date ranges or pagination for better performance.
                    </p>
                  </div>
                </div>
              </div>
            )}

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
                  <option value={30}>30 days (recommended)</option>
                  <option value={60}>60 days</option>
                  <option value={90}>90 days (slow)</option>
                  <option value={180}>180 days (very slow)</option>
                  <option value={365}>365 days (may timeout)</option>
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
              <div className="flex items-end">
                <button
                  onClick={() => fetchRolledOptions(1)}
                  className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
                >
                  Refresh
                </button>
              </div>
            </div>

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
                            <div className="font-medium text-lg">{chain.underlying_symbol}</div>
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(chain.status)}`}>
                              {chain.status.toUpperCase()}
                            </span>
                            <div className="text-sm text-muted-foreground">
                              {chain.orders.length} orders ({chain.roll_count || 0} rolls)
                            </div>
                          </div>
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
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
                            <div>
                              <span className="text-muted-foreground">Total P&L:</span>
                              <span className={`font-medium ml-1 ${chain.total_pnl >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                                {formatCurrency(chain.total_pnl)}
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
                          {/* Orders History */}
                          <div>
                            <h4 className="font-medium mb-2">
                              Orders History ({chain.orders.length})
                              {chain.status === 'active' && (
                                <span className="ml-2 text-xs px-2 py-1 rounded bg-green-100 text-green-800">
                                  ACTIVE CHAIN - DEBUG
                                </span>
                              )}
                            </h4>
                            <div className="space-y-2">
                              {chain.orders.map((order, index) => {
                                let isLatestPosition = false
                                
                                if (chain.status === 'active') {
                                  const latestPosition = (chain as any).latest_position || 
                                                        (chain as any).chain_data?.latest_position ||
                                                        (chain as any).current_position
                                  
                                  if (latestPosition) {
                                    if (order.roll_details) {
                                      const openPos = order.roll_details.open_position
                                      isLatestPosition = openPos && 
                                        openPos.strike_price === latestPosition.strike_price &&
                                        openPos.expiration_date === latestPosition.expiration_date &&
                                        openPos.option_type === latestPosition.option_type
                                    } else {
                                      isLatestPosition = order.strike_price === latestPosition.strike_price &&
                                        order.expiration_date === latestPosition.expiration_date &&
                                        order.option_type === latestPosition.option_type
                                    }
                                  } else {
                                    const potentialCurrentPositions = chain.orders.map((o, i) => {
                                      if (o.roll_details) {
                                        return {
                                          index: i,
                                          strike: o.roll_details.open_position.strike_price,
                                          expiry: o.roll_details.open_position.expiration_date,
                                          type: o.roll_details.open_position.option_type,
                                          date: new Date(o.created_at)
                                        }
                                      } else if (o.position_effect === 'open') {
                                        return {
                                          index: i,
                                          strike: o.strike_price,
                                          expiry: o.expiration_date,
                                          type: o.option_type,
                                          date: new Date(o.created_at)
                                        }
                                      }
                                      return null
                                    }).filter(Boolean)
                                    
                                    const currentPosition = potentialCurrentPositions.sort((a, b) => 
                                      (b?.date?.getTime() || 0) - (a?.date?.getTime() || 0)
                                    )[0]
                                    
                                    isLatestPosition = Boolean(currentPosition && index === currentPosition.index)
                                  }
                                }

                                return (
                                  <div key={index} className={`p-3 rounded border ${isLatestPosition ? 'border-green-500 bg-green-50' : 'border-border'}`}>
                                    <div className="flex justify-between items-start">
                                      <div className="flex-1">
                                        <div className="flex items-center gap-2 mb-1">
                                          <span className="text-sm font-medium">
                                            {order.position_effect === 'open' ? 'OPEN' : 'CLOSE'}
                                          </span>
                                          {isLatestPosition && (
                                            <span className="text-xs px-2 py-1 rounded bg-green-100 text-green-800">
                                              CURRENT
                                            </span>
                                          )}
                                          {order.roll_details && (
                                            <span className="text-xs px-2 py-1 rounded bg-blue-100 text-blue-800">
                                              ROLL
                                            </span>
                                          )}
                                        </div>
                                        <div className="text-sm">
                                          {order.quantity} {order.option_type.toUpperCase()} {order.strike_price} @ {formatDate(order.expiration_date)}
                                        </div>
                                        <div className="text-sm text-muted-foreground">
                                          {order.quantity} contracts @ {formatCurrency(order.price)}
                                        </div>
                                      </div>
                                      <div>
                                        <div className="text-muted-foreground text-xs mb-1">STATUS</div>
                                        <div className="capitalize">
                                          {order.state}
                                        </div>
                                        <div className="text-xs text-muted-foreground">
                                          {order.strategy || 'Single Leg'}
                                        </div>
                                      </div>
                                    </div>
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