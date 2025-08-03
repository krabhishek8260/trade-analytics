"use client";

import React, { useState, useEffect } from 'react';
import { PnLSummaryCards } from '@/components/pnl/PnLSummaryCards';
import { YearlyPnLChart } from '@/components/pnl/YearlyPnLChart';
import { SymbolPnLTable } from '@/components/pnl/SymbolPnLTable';
import { TradeDetailsModal } from '@/components/pnl/TradeDetailsModal';
import { getPnLSummary, getYearlyPnL, getSymbolPnL, getSymbolTrades } from '@/lib/api';
import { PnLSummary, YearlyPnL, SymbolPnL, TradeDetail } from '@/lib/api';

const LoadingSkeleton = () => (
  <div className="container mx-auto p-6 space-y-6">
    <div className="flex items-center justify-between">
      <div>
        <h1 className="text-3xl font-bold">P&L Analytics</h1>
        <p className="text-muted-foreground mt-2">
          Comprehensive profit and loss analysis for your options trading
        </p>
      </div>
    </div>
    
    {/* Loading skeletons */}
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {[...Array(8)].map((_, i) => (
        <div key={i} className="bg-background border rounded-lg shadow-sm">
          <div className="p-6 pb-2">
            <div className="h-4 w-24 bg-gray-200 dark:bg-gray-700 rounded animate-pulse"></div>
          </div>
          <div className="p-6 pt-0">
            <div className="h-8 w-32 bg-gray-200 dark:bg-gray-700 rounded animate-pulse mb-2"></div>
            <div className="h-3 w-20 bg-gray-200 dark:bg-gray-700 rounded animate-pulse"></div>
          </div>
        </div>
      ))}
    </div>
    
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-background border rounded-lg shadow-sm">
        <div className="p-6 border-b">
          <div className="h-6 w-40 bg-gray-200 dark:bg-gray-700 rounded animate-pulse"></div>
        </div>
        <div className="p-6">
          <div className="h-64 w-full bg-gray-200 dark:bg-gray-700 rounded animate-pulse"></div>
        </div>
      </div>
      
      <div className="bg-background border rounded-lg shadow-sm">
        <div className="p-6 border-b">
          <div className="h-6 w-40 bg-gray-200 dark:bg-gray-700 rounded animate-pulse"></div>
        </div>
        <div className="p-6">
          <div className="h-64 w-full bg-gray-200 dark:bg-gray-700 rounded animate-pulse"></div>
        </div>
      </div>
    </div>
  </div>
);

const ErrorAlert = ({ error, onRetry }: { error: string; onRetry: () => void }) => (
  <div className="container mx-auto p-6">
    <div className="border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/10 rounded-lg p-4">
      <div className="text-red-800 dark:text-red-200">{error}</div>
    </div>
    <button 
      onClick={onRetry}
      className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
    >
      Retry
    </button>
  </div>
);

export default function PnLAnalyticsPage() {
  // State for P&L data
  const [pnlSummary, setPnlSummary] = useState<PnLSummary | null>(null);
  const [yearlyData, setYearlyData] = useState<YearlyPnL[]>([]);
  const [symbolData, setSymbolData] = useState<SymbolPnL[]>([]);
  const [selectedSymbolTrades, setSelectedSymbolTrades] = useState<TradeDetail[]>([]);
  
  // UI state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedYear, setSelectedYear] = useState<number | null>(null);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const [isTradeModalOpen, setIsTradeModalOpen] = useState(false);
  
  // Table sorting state
  const [symbolSortBy, setSymbolSortBy] = useState('total_pnl');
  const [symbolSortOrder, setSymbolSortOrder] = useState<'asc' | 'desc'>('desc');

  // New data detection state
  const [hasNewData, setHasNewData] = useState(false);
  const [newDataCheckEnabled, setNewDataCheckEnabled] = useState(true);
  const [checkInterval, setCheckInterval] = useState(30000) // 30 seconds default
  const [lastDataHash, setLastDataHash] = useState<string>('')

  useEffect(() => {
    loadPnLData();
  }, []);

  // New data check effect
  useEffect(() => {
    if (!newDataCheckEnabled || loading) return

    const interval = setInterval(() => {
      console.log('Checking for new P&L data...')
      checkForNewPnLData()
    }, checkInterval)

    return () => clearInterval(interval)
  }, [newDataCheckEnabled, checkInterval, loading, lastDataHash, selectedYear, symbolSortBy, symbolSortOrder])

  const loadPnLData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Load all P&L data concurrently
      const [summaryResult, yearlyResult, symbolResult] = await Promise.all([
        getPnLSummary(),
        getYearlyPnL(),
        getSymbolPnL(selectedYear, 20, symbolSortBy, symbolSortOrder)
      ]);
      
      setPnlSummary(summaryResult);
      setYearlyData(yearlyResult);
      setSymbolData(symbolResult);
      
      // Update data hash for change detection
      const dataHash = generatePnLDataHash(summaryResult, yearlyResult, symbolResult);
      setLastDataHash(dataHash);
      
    } catch (err) {
      console.error('Error loading P&L data:', err);
      setError('Failed to load P&L data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Generate a hash of the current P&L data to detect changes
  const generatePnLDataHash = (summary: PnLSummary | null, yearly: YearlyPnL[], symbols: SymbolPnL[]): string => {
    const dataString = JSON.stringify({
      summaryTotal: summary?.total_pnl || 0,
      summaryCount: summary?.total_trades || 0,
      yearlyCount: yearly.length,
      symbolsCount: symbols.length,
      // Use some key metrics that would change when new data arrives
      totalYearlyPnL: yearly.reduce((sum, year) => sum + (year.total_pnl || 0), 0),
      totalSymbolsPnL: symbols.reduce((sum, symbol) => sum + (symbol.total_pnl || 0), 0)
    })
    return btoa(dataString).slice(0, 16) // Simple hash for comparison
  }

  // Check for new data without updating the UI
  const checkForNewPnLData = async () => {
    if (!newDataCheckEnabled || loading) return

    try {
      // Load minimal data for comparison
      const [summaryResult, yearlyResult, symbolResult] = await Promise.all([
        getPnLSummary(),
        getYearlyPnL(),
        getSymbolPnL(selectedYear, 20, symbolSortBy, symbolSortOrder)
      ]);
      
      const newDataHash = generatePnLDataHash(summaryResult, yearlyResult, symbolResult)
      
      if (lastDataHash && newDataHash !== lastDataHash) {
        console.log('New P&L data detected!')
        setHasNewData(true)
      }
    } catch (error) {
      console.error('Failed to check for new P&L data:', error)
    }
  }

  // Manual refresh function
  const handleManualRefresh = () => {
    setHasNewData(false) // Clear new data indicator when manually refreshing
    loadPnLData()
  }

  const handleYearClick = async (year: number) => {
    setSelectedYear(year);
    
    try {
      // Reload symbol data for the selected year
      const symbolResult = await getSymbolPnL(year, 20, symbolSortBy, symbolSortOrder);
      setSymbolData(symbolResult);
    } catch (err) {
      console.error('Error loading year-specific data:', err);
      setError('Failed to load data for selected year.');
    }
  };

  const handleSymbolClick = async (symbol: string) => {
    setSelectedSymbol(symbol);
    
    try {
      // Load trades for the selected symbol
      const tradesResult = await getSymbolTrades(symbol, selectedYear);
      setSelectedSymbolTrades(tradesResult);
      setIsTradeModalOpen(true);
    } catch (err) {
      console.error('Error loading symbol trades:', err);
      setError('Failed to load trades for selected symbol.');
    }
  };

  const handleSymbolSort = async (field: string) => {
    const newSortOrder = symbolSortBy === field && symbolSortOrder === 'desc' ? 'asc' : 'desc';
    setSymbolSortBy(field);
    setSymbolSortOrder(newSortOrder);
    
    try {
      const symbolResult = await getSymbolPnL(selectedYear, 20, field, newSortOrder);
      setSymbolData(symbolResult);
    } catch (err) {
      console.error('Error sorting symbol data:', err);
      setError('Failed to sort symbol data.');
    }
  };

  const clearYearFilter = async () => {
    setSelectedYear(null);
    
    try {
      const symbolResult = await getSymbolPnL(null, 20, symbolSortBy, symbolSortOrder);
      setSymbolData(symbolResult);
    } catch (err) {
      console.error('Error clearing year filter:', err);
      setError('Failed to reload data.');
    }
  };

  if (loading) {
    return <LoadingSkeleton />;
  }

  if (error) {
    return <ErrorAlert error={error} onRetry={loadPnLData} />;
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">P&L Analytics</h1>
          <p className="text-muted-foreground mt-2">
            Comprehensive profit and loss analysis for your options trading
          </p>
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
          <button
            onClick={handleManualRefresh}
            disabled={loading}
            className="px-3 py-1 text-sm bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/80 disabled:opacity-50 relative"
          >
            {loading ? 'Refreshing...' : 'Refresh'}
            {hasNewData && (
              <span className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full animate-pulse"></span>
            )}
          </button>
        </div>
      </div>

      {/* Year Filter Display */}
      {selectedYear && (
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">
            Viewing data for {selectedYear}
          </span>
          <button
            onClick={clearYearFilter}
            className="px-3 py-1 text-xs bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
          >
            Clear Filter
          </button>
        </div>
      )}

      {/* New Data Notification */}
      {hasNewData && (
        <div className="bg-green-500/10 border border-green-500/20 rounded-md p-3 animate-in slide-in-from-top-2">
          <p className="text-green-600 text-sm flex items-center justify-between">
            <span className="flex items-center">
              <span className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></span>
              New P&L data available
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

      {/* Summary Cards */}
      {pnlSummary && (
        <PnLSummaryCards
          totalPnL={pnlSummary.total_pnl}
          realizedPnL={pnlSummary.realized_pnl}
          unrealizedPnL={pnlSummary.unrealized_pnl}
          winRate={pnlSummary.win_rate}
          totalTrades={pnlSummary.total_trades}
          largestWinner={pnlSummary.largest_winner}
          largestLoser={pnlSummary.largest_loser}
          avgTradePnL={pnlSummary.avg_trade_pnl}
        />
      )}

      {/* Charts and Tables */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Yearly P&L Chart */}
        <div className="bg-background border rounded-lg shadow-sm">
          <div className="p-6 border-b">
            <h3 className="text-lg font-semibold">Year-over-Year Performance</h3>
            <p className="text-sm text-muted-foreground">
              P&L breakdown by calendar year (click to filter symbol table)
            </p>
          </div>
          <div className="p-6">
            {yearlyData.length > 0 ? (
              <YearlyPnLChart
                yearlyData={yearlyData}
                selectedYear={selectedYear}
                onYearClick={handleYearClick}
              />
            ) : (
              <div className="h-64 flex items-center justify-center text-muted-foreground">
                No yearly data available
              </div>
            )}
          </div>
        </div>

        {/* Symbol Performance Table */}
        <div className="bg-background border rounded-lg shadow-sm">
          <div className="p-6 border-b">
            <h3 className="text-lg font-semibold">Symbol Performance</h3>
            <p className="text-sm text-muted-foreground">
              P&L breakdown by underlying symbol (click to view trades)
            </p>
          </div>
          <div className="p-6">
            {symbolData.length > 0 ? (
              <SymbolPnLTable
                symbolData={symbolData}
                onSymbolClick={handleSymbolClick}
                sortBy={symbolSortBy}
                sortOrder={symbolSortOrder}
                onSort={handleSymbolSort}
              />
            ) : (
              <div className="h-64 flex items-center justify-center text-muted-foreground">
                No symbol data available
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Trade Details Modal */}
      {selectedSymbol && (
        <TradeDetailsModal
          isOpen={isTradeModalOpen}
          symbol={selectedSymbol}
          trades={selectedSymbolTrades}
          onClose={() => {
            setIsTradeModalOpen(false);
            setSelectedSymbol(null);
            setSelectedSymbolTrades([]);
          }}
        />
      )}
    </div>
  );
}