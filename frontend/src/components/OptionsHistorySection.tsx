'use client'

import { useState, useEffect } from 'react'
import { getClosedOptionsHistory, ClosedOptionsPosition } from '@/lib/api'

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
  const [closedPositions, setClosedPositions] = useState<ClosedOptionsPosition[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [historyExpanded, setHistoryExpanded] = useState(false)
  const [showChains, setShowChains] = useState(true)

  useEffect(() => {
    const fetchClosedHistory = async () => {
      try {
        setLoading(true)
        const data = await getClosedOptionsHistory({
          limit: 100,
          days_back: 365,
          sort_by: 'close_date',
          sort_order: 'desc',
          include_chains: true
        })
        setClosedPositions(data)
      } catch (err) {
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

  if (closedPositions.length === 0) {
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
  const totalClosed = closedPositions.length
  const totalPnl = closedPositions.reduce((sum, pos) => sum + pos.total_pnl, 0)
  const winningTrades = closedPositions.filter(pos => pos.win_loss === 'win').length
  const winRate = totalClosed > 0 ? (winningTrades / totalClosed) * 100 : 0
  const avgDaysHeld = closedPositions.reduce((sum, pos) => sum + (pos.days_held || 0), 0) / totalClosed
  const enhancedChains = closedPositions.filter(pos => pos.enhanced_chain).length

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
            onClick={() => setShowChains(!showChains)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              showChains ? 'bg-primary' : 'bg-input'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-background transition-transform ${
                showChains ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
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
      </div>

      {/* Closed Positions List */}
      <div className="space-y-2">
        {(historyExpanded ? closedPositions : closedPositions.slice(0, 5)).map((position, index) => (
          <div 
            key={index} 
            className="flex justify-between items-center p-4 bg-muted/50 rounded-lg"
          >
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-medium text-lg">{position.underlying_symbol}</span>
                
                {/* Chain Indicators */}
                {showChains && position.chain_id && (
                  <>
                    <button
                      onClick={() => onChainClick?.(position.chain_id)}
                      className="text-xs px-2 py-1 rounded bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 border border-blue-300 dark:border-blue-700 hover:bg-blue-200 dark:hover:bg-blue-800 transition-colors cursor-pointer"
                      title="Click to view chain details"
                    >
                      🔗 CHAIN
                    </button>
                    <span className="text-xs px-2 py-1 rounded bg-gray-100 dark:bg-gray-900 text-gray-800 dark:text-gray-200 border border-gray-300 dark:border-gray-700">
                      📊 {position.roll_count} ROLLS
                    </span>
                    {position.enhanced_chain && (
                      <span className="text-xs px-2 py-1 rounded bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200 border border-purple-300 dark:border-purple-700" title="Enhanced chain with complete trading history">
                        ✨ ENHANCED
                      </span>
                    )}
                  </>
                )}
                
                <span className={`text-xs px-2 py-1 rounded ${
                  position.win_loss === 'win'
                    ? 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 border border-green-300 dark:border-green-700' 
                    : 'bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200 border border-red-300 dark:border-red-700'
                }`}>
                  {position.win_loss.toUpperCase()}
                </span>
              </div>
              
              <div className="text-sm text-muted-foreground mt-1">
                <span className="font-medium">{position.initial_strategy}</span>
                {position.final_strike && (
                  <span> • Final: {position.final_strike} {position.final_option_type?.toUpperCase()}</span>
                )}
                {position.days_held && (
                  <span> • Held: {position.days_held} days</span>
                )}
                <span> • {new Date(position.close_date).toLocaleDateString()}</span>
              </div>
            </div>
            
            <div className="text-right">
              <div className={`font-medium text-lg ${position.total_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {formatCurrency(position.total_pnl)}
              </div>
              <div className="text-sm text-muted-foreground">
                Net: {formatCurrency(position.net_premium)}
              </div>
              <div className="text-xs text-muted-foreground">
                {position.total_orders} orders
              </div>
            </div>
          </div>
        ))}
        
        {!historyExpanded && closedPositions.length > 5 && (
          <button
            onClick={() => setHistoryExpanded(true)}
            className="w-full text-center text-sm text-primary hover:text-primary/80 pt-2 py-2 rounded hover:bg-muted/30 transition-colors"
          >
            Show {closedPositions.length - 5} more closed positions
          </button>
        )}
      </div>
    </div>
  )
} 