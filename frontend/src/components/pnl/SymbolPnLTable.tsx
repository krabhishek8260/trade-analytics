import React from 'react';
import { ArrowUpDown, ArrowUp, ArrowDown, TrendingUp, TrendingDown } from 'lucide-react';
import { SymbolLogo } from '@/components/ui/SymbolLogo';

interface SymbolPnL {
  symbol: string;
  total_pnl: number;
  realized_pnl: number;
  unrealized_pnl: number;
  total_trades: number;
  win_rate: number;
  avg_trade_pnl: number;
  largest_winner?: number;
  largest_loser?: number;
}

interface SymbolPnLTableProps {
  symbolData: SymbolPnL[];
  onSymbolClick: (symbol: string) => void;
  sortBy: string;
  sortOrder: 'asc' | 'desc';
  onSort: (field: string) => void;
}

export const SymbolPnLTable: React.FC<SymbolPnLTableProps> = ({
  symbolData,
  onSymbolClick,
  sortBy,
  sortOrder,
  onSort,
}) => {
  const formatCurrency = (amount: number) => {
    const isNegative = amount < 0;
    const formatted = new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(Math.abs(amount));
    
    return isNegative ? `-${formatted}` : formatted;
  };

  const formatPercentage = (value: number) => {
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

  const getSortIcon = (field: string) => {
    if (sortBy !== field) {
      return <ArrowUpDown className="ml-2 h-4 w-4" />;
    }
    return sortOrder === 'asc' ? 
      <ArrowUp className="ml-2 h-4 w-4" /> : 
      <ArrowDown className="ml-2 h-4 w-4" />;
  };

  const SortableHeader = ({ field, label }: { field: string; label: string }) => (
    <th className="text-left p-3">
      <button
        className="flex items-center text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100"
        onClick={() => onSort(field)}
      >
        {label}
        {getSortIcon(field)}
      </button>
    </th>
  );

  if (!symbolData || symbolData.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No symbol data available
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-md border bg-background">
        <table className="w-full">
          <thead className="border-b bg-muted/50">
            <tr>
              <th className="text-left p-3">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Symbol</span>
              </th>
              <SortableHeader field="total_pnl" label="Total P&L" />
              <SortableHeader field="realized_pnl" label="Realized" />
              <SortableHeader field="unrealized_pnl" label="Unrealized" />
              <SortableHeader field="total_trades" label="Trades" />
              <SortableHeader field="win_rate" label="Win Rate" />
              <SortableHeader field="avg_trade_pnl" label="Avg P&L" />
            </tr>
          </thead>
          <tbody>
            {symbolData.map((symbol, index) => (
              <tr
                key={symbol.symbol}
                className={`
                  cursor-pointer hover:bg-muted/50 transition-colors border-b
                  ${index === symbolData.length - 1 ? 'border-b-0' : ''}
                `}
                onClick={() => onSymbolClick(symbol.symbol)}
              >
                <td className="p-3">
                  <div className="flex items-center">
                    <SymbolLogo 
                      symbol={symbol.symbol} 
                      size="md" 
                      showText={true}
                      className="text-blue-600 dark:text-blue-400"
                    />
                  </div>
                </td>
                <td className={`p-3 font-medium ${getPnLColor(symbol.total_pnl)}`}>
                  <div className="flex items-center gap-1">
                    {getPnLIcon(symbol.total_pnl)}
                    {formatCurrency(symbol.total_pnl)}
                  </div>
                </td>
                <td className={`p-3 ${getPnLColor(symbol.realized_pnl)}`}>
                  {formatCurrency(symbol.realized_pnl)}
                </td>
                <td className={`p-3 ${getPnLColor(symbol.unrealized_pnl)}`}>
                  {formatCurrency(symbol.unrealized_pnl)}
                </td>
                <td className="p-3">
                  {symbol.total_trades.toLocaleString()}
                </td>
                <td className={`p-3 ${symbol.win_rate >= 50 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                  {formatPercentage(symbol.win_rate)}
                </td>
                <td className={`p-3 ${getPnLColor(symbol.avg_trade_pnl)}`}>
                  {formatCurrency(symbol.avg_trade_pnl)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      <div className="text-sm text-gray-500 text-center">
        Showing {symbolData.length} symbols. Click any row to view individual trades.
      </div>
    </div>
  );
};