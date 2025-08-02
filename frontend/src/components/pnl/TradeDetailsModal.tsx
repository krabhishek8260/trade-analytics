import React, { useState } from 'react';
import { Download, X, Calendar, DollarSign, TrendingUp, TrendingDown } from 'lucide-react';
import { SummaryCard } from '../ui/SummaryCard';

interface TradeDetail {
  trade_id: string;
  strategy: string;
  open_date: string | null;
  close_date?: string | null;
  strike_price: number;
  expiration_date: string | null;
  option_type: string;
  contracts: number;
  opening_premium: number;
  closing_premium?: number;
  pnl: number;
  pnl_percentage?: number;
  days_held?: number | null;
  status: 'realized' | 'unrealized';
}

interface TradeDetailsModalProps {
  isOpen: boolean;
  symbol: string;
  trades: TradeDetail[];
  onClose: () => void;
}

export const TradeDetailsModal: React.FC<TradeDetailsModalProps> = ({
  isOpen,
  symbol,
  trades,
  onClose,
}) => {
  const [activeTab, setActiveTab] = useState<'all' | 'realized' | 'unrealized'>('all');
  const [sortBy, setSortBy] = useState<'date' | 'pnl' | 'strike'>('date');

  const formatCurrency = (amount: number) => {
    const isNegative = amount < 0;
    const formatted = new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(Math.abs(amount));
    
    return isNegative ? `-${formatted}` : formatted;
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleDateString();
    } catch {
      return dateString;
    }
  };

  const formatPercentage = (value: number | undefined) => {
    if (value === undefined || value === null) return 'N/A';
    return `${value.toFixed(1)}%`;
  };

  const getPnLColor = (value: number) => {
    if (value > 0) return 'text-green-600 dark:text-green-400';
    if (value < 0) return 'text-red-600 dark:text-red-400';
    return 'text-gray-600 dark:text-gray-400';
  };

  const getPnLIcon = (value: number) => {
    if (value > 0) return <TrendingUp className="h-3 w-3 inline" />;
    if (value < 0) return <TrendingDown className="h-3 w-3 inline" />;
    return null;
  };

  const getStatusBadge = (status: string) => {
    const baseClasses = "px-2 py-1 rounded-full text-xs font-medium";
    const colorClasses = status === 'realized' 
      ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100' 
      : 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100';
    
    return (
      <span className={`${baseClasses} ${colorClasses}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  // Filter trades based on active tab
  const filteredTrades = trades.filter(trade => {
    if (activeTab === 'all') return true;
    return trade.status === activeTab;
  });

  // Sort trades
  const sortedTrades = [...filteredTrades].sort((a, b) => {
    switch (sortBy) {
      case 'date':
        const dateA = a.close_date || a.open_date || '';
        const dateB = b.close_date || b.open_date || '';
        return new Date(dateB).getTime() - new Date(dateA).getTime();
      case 'pnl':
        return b.pnl - a.pnl;
      case 'strike':
        return b.strike_price - a.strike_price;
      default:
        return 0;
    }
  });

  // Calculate summary statistics
  const summary = {
    total: filteredTrades.length,
    totalPnL: filteredTrades.reduce((sum, trade) => sum + trade.pnl, 0),
    winners: filteredTrades.filter(trade => trade.pnl > 0).length,
    losers: filteredTrades.filter(trade => trade.pnl < 0).length,
    avgPnL: filteredTrades.length > 0 ? filteredTrades.reduce((sum, trade) => sum + trade.pnl, 0) / filteredTrades.length : 0,
    winRate: filteredTrades.length > 0 ? (filteredTrades.filter(trade => trade.pnl > 0).length / filteredTrades.length) * 100 : 0,
  };

  const exportToCsv = () => {
    const headers = [
      'Trade ID', 'Symbol', 'Strategy', 'Open Date', 'Close Date', 
      'Strike Price', 'Expiration', 'Option Type', 'Contracts',
      'Opening Premium', 'Closing Premium', 'P&L', 'P&L %', 'Days Held', 'Status'
    ];
    
    const csvData = [
      headers.join(','),
      ...sortedTrades.map(trade => [
        trade.trade_id,
        symbol,
        trade.strategy,
        trade.open_date || '',
        trade.close_date || '',
        trade.strike_price,
        trade.expiration_date || '',
        trade.option_type,
        trade.contracts,
        trade.opening_premium,
        trade.closing_premium || '',
        trade.pnl,
        trade.pnl_percentage || '',
        trade.days_held || '',
        trade.status
      ].map(field => `"${field}"`).join(','))
    ].join('\n');

    const blob = new Blob([csvData], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${symbol}_trades_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-background rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div>
            <h2 className="text-xl font-semibold">{symbol} - Trade Details</h2>
            <p className="text-sm text-muted-foreground">
              Detailed view of all trades for {symbol}
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={exportToCsv}
              className="flex items-center gap-2 px-4 py-2 text-sm bg-secondary hover:bg-secondary/80 rounded-md transition-colors"
            >
              <Download className="h-4 w-4" />
              Export CSV
            </button>
            <button
              onClick={onClose}
              className="p-2 hover:bg-muted rounded-md transition-colors"
              aria-label="Close"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-6 bg-muted/30">
          <SummaryCard
            title="Total Trades"
            value={summary.total}
            variant="compact"
            className="bg-background border"
          />
          <SummaryCard
            title="Total P&L"
            value={formatCurrency(summary.totalPnL)}
            valueColor={summary.totalPnL >= 0 ? 'profit' : 'loss'}
            variant="compact"
            className="bg-background border"
          />
          <SummaryCard
            title="Win Rate"
            value={`${summary.winRate.toFixed(1)}%`}
            valueColor={summary.winRate >= 50 ? 'profit' : 'loss'}
            variant="compact"
            className="bg-background border"
          />
          <SummaryCard
            title="Avg P&L"
            value={formatCurrency(summary.avgPnL)}
            valueColor={summary.avgPnL >= 0 ? 'profit' : 'loss'}
            variant="compact"
            className="bg-background border"
          />
        </div>

        {/* Controls */}
        <div className="flex items-center justify-between p-6 border-b">
          <div className="flex">
            {(['all', 'realized', 'unrealized'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 text-sm rounded-md mr-2 transition-colors ${
                  activeTab === tab
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
                }`}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)} ({
                  tab === 'all' ? trades.length : 
                  trades.filter(t => t.status === tab).length
                })
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Sort by:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="px-3 py-1 border rounded-md text-sm bg-background"
            >
              <option value="date">Date</option>
              <option value="pnl">P&L</option>
              <option value="strike">Strike Price</option>
            </select>
          </div>
        </div>

        {/* Trade Table */}
        <div className="flex-1 overflow-auto p-6">
          <table className="w-full">
            <thead className="sticky top-0 bg-background border-b">
              <tr>
                <th className="text-left p-3 text-sm font-medium">Strategy</th>
                <th className="text-left p-3 text-sm font-medium">Strike/Exp</th>
                <th className="text-left p-3 text-sm font-medium">Dates</th>
                <th className="text-left p-3 text-sm font-medium">Contracts</th>
                <th className="text-left p-3 text-sm font-medium">Premiums</th>
                <th className="text-left p-3 text-sm font-medium">P&L</th>
                <th className="text-left p-3 text-sm font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {sortedTrades.map((trade) => (
                <tr key={trade.trade_id} className="border-b hover:bg-muted/50">
                  <td className="p-3">
                    <div className="font-medium">{trade.strategy}</div>
                    <div className="text-xs text-muted-foreground uppercase">
                      {trade.option_type}
                    </div>
                  </td>
                  <td className="p-3">
                    <div className="font-medium">${trade.strike_price}</div>
                    <div className="text-xs text-muted-foreground">
                      {formatDate(trade.expiration_date)}
                    </div>
                  </td>
                  <td className="p-3">
                    <div className="text-sm">
                      <div className="flex items-center gap-1">
                        <Calendar className="h-3 w-3" />
                        {formatDate(trade.open_date)}
                      </div>
                      {trade.close_date && (
                        <div className="text-xs text-muted-foreground">
                          → {formatDate(trade.close_date)}
                        </div>
                      )}
                      {trade.days_held && (
                        <div className="text-xs text-muted-foreground">
                          {trade.days_held}d
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="p-3">
                    <div className="font-medium">{trade.contracts}</div>
                  </td>
                  <td className="p-3">
                    <div className="text-sm">
                      <div className="flex items-center gap-1">
                        <DollarSign className="h-3 w-3" />
                        {formatCurrency(trade.opening_premium)}
                      </div>
                      {trade.closing_premium !== undefined && (
                        <div className="text-xs text-muted-foreground">
                          → {formatCurrency(trade.closing_premium)}
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="p-3">
                    <div className={`font-medium ${getPnLColor(trade.pnl)}`}>
                      <div className="flex items-center gap-1">
                        {getPnLIcon(trade.pnl)}
                        {formatCurrency(trade.pnl)}
                      </div>
                      {trade.pnl_percentage !== undefined && (
                        <div className="text-xs">
                          {formatPercentage(trade.pnl_percentage)}
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="p-3">
                    {getStatusBadge(trade.status)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          
          {sortedTrades.length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
              No trades found for the selected filter
            </div>
          )}
        </div>
      </div>
    </div>
  );
};