'use client'

import { useState } from 'react'
import { SymbolLogo } from '@/components/ui/SymbolLogo'
import { clearLogoCache, getLogoCacheStats } from '@/lib/logoUtils'

const testSymbols = [
  'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX', 'AMD', 'INTC',
  'SPY', 'QQQ', 'IWM', 'VTI', 'VOO', 'ARKK', 'TQQQ', 'SQQQ', 'UVXY', 'VIX'
]

export default function TestLogosPage() {
  const [customSymbol, setCustomSymbol] = useState('')
  const [cacheStats, setCacheStats] = useState(getLogoCacheStats())

  const handleClearCache = () => {
    clearLogoCache()
    setCacheStats(getLogoCacheStats())
  }

  const handleRefreshStats = () => {
    setCacheStats(getLogoCacheStats())
  }

  return (
    <div className="container mx-auto p-6 space-y-8">
      <div className="text-center">
        <h1 className="text-3xl font-bold mb-4">Logo Test Page</h1>
        <p className="text-muted-foreground mb-6">
          Test the stock logo fetching functionality
        </p>
      </div>

      {/* Cache Stats */}
      <div className="bg-muted/50 rounded-lg p-4">
        <h2 className="text-lg font-semibold mb-3">Cache Statistics</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <span className="text-sm text-muted-foreground">Total Cached:</span>
            <div className="font-medium">{cacheStats.totalEntries}</div>
          </div>
          <div>
            <span className="text-sm text-muted-foreground">Symbols:</span>
            <div className="font-medium text-sm">{cacheStats.symbols.join(', ')}</div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleClearCache}
              className="px-3 py-1 bg-red-500 text-white rounded text-sm hover:bg-red-600"
            >
              Clear Cache
            </button>
            <button
              onClick={handleRefreshStats}
              className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
            >
              Refresh Stats
            </button>
          </div>
        </div>
      </div>

      {/* Custom Symbol Test */}
      <div className="bg-muted/50 rounded-lg p-4">
        <h2 className="text-lg font-semibold mb-3">Test Custom Symbol</h2>
        <div className="flex gap-4 items-center">
          <input
            type="text"
            value={customSymbol}
            onChange={(e) => setCustomSymbol(e.target.value.toUpperCase())}
            placeholder="Enter symbol (e.g., AAPL)"
            className="px-3 py-2 border rounded flex-1"
          />
          {customSymbol && (
            <div className="flex items-center gap-2">
              <SymbolLogo symbol={customSymbol} size="lg" showText={true} />
            </div>
          )}
        </div>
      </div>

      {/* Test Symbols Grid */}
      <div className="bg-muted/50 rounded-lg p-4">
        <h2 className="text-lg font-semibold mb-3">Test Symbols</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {testSymbols.map((symbol) => (
            <div key={symbol} className="flex items-center gap-3 p-3 bg-background rounded border">
              <SymbolLogo symbol={symbol} size="md" showText={true} />
              <div className="text-sm text-muted-foreground">
                {symbol}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Different Sizes */}
      <div className="bg-muted/50 rounded-lg p-4">
        <h2 className="text-lg font-semibold mb-3">Different Sizes</h2>
        <div className="flex items-center gap-6">
          <div className="text-center">
            <SymbolLogo symbol="AAPL" size="sm" showText={false} />
            <div className="text-xs text-muted-foreground mt-1">Small</div>
          </div>
          <div className="text-center">
            <SymbolLogo symbol="AAPL" size="md" showText={false} />
            <div className="text-xs text-muted-foreground mt-1">Medium</div>
          </div>
          <div className="text-center">
            <SymbolLogo symbol="AAPL" size="lg" showText={false} />
            <div className="text-xs text-muted-foreground mt-1">Large</div>
          </div>
        </div>
      </div>

      {/* With and Without Text */}
      <div className="bg-muted/50 rounded-lg p-4">
        <h2 className="text-lg font-semibold mb-3">With and Without Text</h2>
        <div className="flex items-center gap-6">
          <div className="text-center">
            <SymbolLogo symbol="MSFT" size="md" showText={true} />
            <div className="text-xs text-muted-foreground mt-1">With Text</div>
          </div>
          <div className="text-center">
            <SymbolLogo symbol="MSFT" size="md" showText={false} />
            <div className="text-xs text-muted-foreground mt-1">Without Text</div>
          </div>
        </div>
      </div>
    </div>
  )
} 