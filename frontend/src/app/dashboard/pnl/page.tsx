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

  useEffect(() => {
    loadPnLData();
  }, []);

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
      
    } catch (err) {
      console.error('Error loading P&L data:', err);
      setError('Failed to load P&L data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

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
      </div>

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