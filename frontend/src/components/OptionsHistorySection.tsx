'use client'

import { useState, useEffect } from 'react'
import { getRolledOptionsChains, OptionsChain } from '@/lib/api'

interface OptionsHistorySectionProps {
  formatCurrency: (value: number) => string
  formatPercent: (value: number) => string
  onChainClick?: (chainId: string) => void
}

export default function OptionsHistorySection({ 
  formatCurrency, 
  formatPercent, 
  onChainClick 
}: OptionsHistorySectionProps) {
  const [closedChains, setClosedChains] = useState<OptionsChain[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [historyExpanded, setHistoryExpanded] = useState(false)
  const [showChainInfo, setShowChainInfo] = useState(true)

  useEffect(() => {
    const fetchClosedHistory = async () => {
      try {
        setLoading(true)
        setError(null)
        
        const response = await getRolledOptionsChains({
          status: 'closed',
          limit: 100,
          days_back: 365
        })
        
        setClosedChains(response.chains || [])
      } catch (err) {
        console.error('Error loading closed options history:', err)
        setError(err instanceof Error ? err.message : 'Failed to fetch closed options history')
      } finally {
        setLoading(false)
      }
    }

    fetchClosedHistory()
  }, [])

  if (loading) {
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

  if (error) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-medium">Options History</h3>
        </div>
        <div className="text-center py-8">
          <p className="text-red-600 mb-2">Error loading closed options history</p>
          <p className="text-sm text-muted-foreground">{error}</p>
        </div>
      </div>
    )
  }

  if (closedChains.length === 0) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-medium">Options History</h3>
        </div>
        <div className="text-center py-8">
          <p className="text-muted-foreground mb-4">No closed options positions found.</p>
          <p className="text-sm text-muted-foreground">Closed options positions will appear here when available.</p>
        </div>
      </div>
    )
  }

  // Calculate summary statistics
  const totalClosed = closedChains.length
  const totalPnl = closedChains.reduce((sum, chain) => sum + (chain.total_pnl || 0), 0)
  const winningTrades = closedChains.filter(chain => (chain.total_pnl || 0) > 0).length
  const winRate = totalClosed > 0 ? (winningTrades / totalClosed) * 100 : 0
  const avgDaysHeld = closedChains.reduce((sum, chain) => {
    if (chain.start_date && chain.last_activity_date) {
      const start = new Date(chain.start_date)
      const end = new Date(chain.last_activity_date)
      return sum + Math.floor((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24))
    }
    return sum
  }, 0) / totalClosed
  const enhancedChains = closedChains.filter(chain => chain.orders?.[0]?.legs?.length === 1).length
  const chainsWithRolls = closedChains.filter(chain => (chain.roll_count || 0) > 0).length

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-3">
        <button
          onClick={() => setHistoryExpanded(!historyExpanded)}
          className="flex items-center space-x-2 p-4 bg-muted/50 rounded-lg hover:bg-muted transition-colors flex-1 mr-3"
        >
          <h3 className="text-lg font-medium">
            Options History ({totalClosed} closed positions)
          </h3>
          <svg
            className={`w-5 h-5 transition-transform ${historyExpanded ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m19 9-7 7-7-7" />
          </svg>
        </button>
        
        {/* Chain Information Toggle */}
        <div className="flex items-center space-x-2 bg-muted/50 rounded-lg p-3">
          <label className="text-sm font-medium text-muted-foreground">Show Chain Info</label>
          <button
            onClick={() => setShowChainInfo(!showChainInfo)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              showChainInfo ? 'bg-primary' : 'bg-input'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-background transition-transform ${
                showChainInfo ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-4">
        <div className="bg-muted/50 rounded-lg p-4">
          <h4 className="text-sm font-medium text-muted-foreground mb-1">Total P&L</h4>
          <p className={`text-2xl font-bold ${totalPnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {formatCurrency(totalPnl)}
          </p>
        </div>
        <div className="bg-muted/50 rounded-lg p-4">
          <h4 className="text-sm font-medium text-muted-foreground mb-1">Win Rate</h4>
          <p className="text-2xl font-bold">{formatPercent(winRate)}</p>
          <p className="text-sm text-muted-foreground">{winningTrades}/{totalClosed} wins</p>
        </div>
        <div className="bg-muted/50 rounded-lg p-4">
          <h4 className="text-sm font-medium text-muted-foreground mb-1">Avg Days Held</h4>
          <p className="text-2xl font-bold">{Math.round(avgDaysHeld)}</p>
          <p className="text-sm text-muted-foreground">days</p>
        </div>
        <div className="bg-muted/50 rounded-lg p-4">
          <h4 className="text-sm font-medium text-muted-foreground mb-1">Enhanced Chains</h4>
          <p className="text-2xl font-bold">{enhancedChains}</p>
          <p className="text-sm text-muted-foreground">of {totalClosed} total</p>
        </div>
        <div className="bg-muted/50 rounded-lg p-4">
          <h4 className="text-sm font-medium text-muted-foreground mb-1">Rolled Chains</h4>
          <p className="text-2xl font-bold">{chainsWithRolls}</p>
          <p className="text-sm text-muted-foreground">with rolls</p>
        </div>
      </div>

      {/* Closed Chains List */}
      <div className="space-y-2">
        {(historyExpanded ? closedChains : closedChains.slice(0, 5)).map((chain, index) => {
          const lastOrder = chain.orders?.[chain.orders.length - 1]
          const firstOrder = chain.orders?.[0]
          const isEnhanced = firstOrder?.legs?.length === 1
          const daysHeld = chain.start_date && chain.last_activity_date ? 
            Math.floor((new Date(chain.last_activity_date).getTime() - new Date(chain.start_date).getTime()) / (1000 * 60 * 60 * 24)) : 0
          
          return (
            <div 
              key={chain.chain_id || index} 
              className="flex justify-between items-center p-4 bg-muted/50 rounded-lg"
            >
              <div className="flex-1">
                <div className="flex items-center space-x-2 mb-2">
                  <span className="font-medium text-lg">{chain.underlying_symbol}</span>
                  
                  {/* Chain Indicators */}
                  {showChainInfo && chain.chain_id && (
                    <>
                      <button
                        onClick={() => onChainClick?.(chain.chain_id)}
                        className="text-xs px-2 py-1 rounded bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 border border-blue-300 dark:border-blue-700 hover:bg-blue-200 dark:hover:bg-blue-800 transition-colors cursor-pointer"
                        title="Click to view chain details"
                      >
                        🔗 CHAIN
                      </button>
                      {(chain.roll_count || 0) > 0 && (
                        <span className="text-xs px-2 py-1 rounded bg-orange-100 dark:bg-orange-900 text-orange-800 dark:text-orange-200 border border-orange-300 dark:border-orange-700">
                          🔄 {chain.roll_count} ROLLS
                        </span>
                      )}
                      {isEnhanced && (
                        <span className="text-xs px-2 py-1 rounded bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200 border border-purple-300 dark:border-purple-700" title="Enhanced chain with complete trading history">
                          ✨ ENHANCED
                        </span>
                      )}
                    </>
                  )}
                  
                  <span className={`text-xs px-2 py-1 rounded ${
                    (chain.total_pnl || 0) > 0
                      ? 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 border border-green-300 dark:border-green-700' 
                      : 'bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 border border-red-300 dark:border-red-700'
                  }`}>
                    {(chain.total_pnl || 0) > 0 ? 'WIN' : 'LOSS'}
                  </span>
                </div>
                
                <div className="text-sm text-muted-foreground mb-2">
                  <span className="font-medium">{chain.initial_strategy}</span>
                  {lastOrder && (
                    <span> • Final: {lastOrder.strike_price} {lastOrder.option_type?.toUpperCase()}</span>
                  )}
                  {daysHeld > 0 && (
                    <span> • Held: {daysHeld} days</span>
                  )}
                  <span> • {new Date(chain.last_activity_date).toLocaleDateString()}</span>
                </div>

                {/* Enhanced Chain Information */}
                {showChainInfo && chain.chain_id && (
                  <div className="mt-2 p-3 bg-muted/30 rounded border border-border">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-muted-foreground">
                      <div className="flex items-center space-x-2">
                        <span>📅 Started: {new Date(chain.start_date).toLocaleDateString()}</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <span>📊 {chain.total_orders} orders</span>
                        {(chain.roll_count || 0) > 0 && (
                          <span>• {chain.roll_count} rolls</span>
                        )}
                      </div>
                      <div className="flex items-center space-x-2">
                        <span>💰 Net Premium: {formatCurrency(chain.net_premium || 0)}</span>
                      </div>
                    </div>
                    
                    {/* Chain Performance Summary */}
                    <div className="mt-2 pt-2 border-t border-border/50">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-4 text-xs">
                          <span>Credits: {formatCurrency(chain.total_credits_collected || 0)}</span>
                          <span>Debits: {formatCurrency(chain.total_debits_paid || 0)}</span>
                        </div>
                        <div className={`text-sm font-medium ${(chain.total_pnl || 0) >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                          Chain P&L: {formatCurrency(chain.total_pnl || 0)}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
              
              <div className="text-right ml-4">
                <div className={`font-medium text-lg ${(chain.total_pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {formatCurrency(chain.total_pnl || 0)}
                </div>
                <div className="text-sm text-muted-foreground">
                  Net: {formatCurrency(chain.net_premium || 0)}
                </div>
                <div className="text-xs text-muted-foreground">
                  {chain.total_orders} orders
                </div>
                
                {/* Chain P&L Information */}
                {showChainInfo && chain.chain_id && chain.total_pnl !== undefined && (
                  <div className="text-xs text-muted-foreground mt-1">
                    Chain: <span className={`${(chain.total_pnl || 0) >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                      {formatCurrency(chain.total_pnl || 0)}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )
        })}
        
        {!historyExpanded && closedChains.length > 5 && (
          <button
            onClick={() => setHistoryExpanded(true)}
            className="w-full text-center text-sm text-primary hover:text-primary/80 pt-2 py-2 rounded hover:bg-muted/30 transition-colors"
          >
            Show {closedChains.length - 5} more closed positions
          </button>
        )}
      </div>
    </div>
  )
} 