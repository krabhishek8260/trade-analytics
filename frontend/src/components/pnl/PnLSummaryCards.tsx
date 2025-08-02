import React from 'react';
import { TrendingUp, TrendingDown, Target, BarChart3, DollarSign, Trophy, AlertTriangle, Calculator } from 'lucide-react';

interface PnLSummaryCardsProps {
  totalPnL: number;
  realizedPnL: number;
  unrealizedPnL: number;
  winRate: number;
  totalTrades: number;
  largestWinner?: number;
  largestLoser?: number;
  avgTradePnL?: number;
}

export const PnLSummaryCards: React.FC<PnLSummaryCardsProps> = ({
  totalPnL,
  realizedPnL,
  unrealizedPnL,
  winRate,
  totalTrades,
  largestWinner = 0,
  largestLoser = 0,
  avgTradePnL = 0
}) => {
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

  const formatPercentage = (value: number) => {
    return `${value.toFixed(1)}%`;
  };

  const getPnLColor = (value: number) => {
    if (value > 0) return 'text-green-600 dark:text-green-400';
    if (value < 0) return 'text-red-600 dark:text-red-400';
    return 'text-gray-600 dark:text-gray-400';
  };

  const getPnLIcon = (value: number) => {
    if (value > 0) return <TrendingUp className="h-4 w-4" />;
    if (value < 0) return <TrendingDown className="h-4 w-4" />;
    return <BarChart3 className="h-4 w-4" />;
  };

  const SummaryCard = ({ title, value, subtitle, icon, valueClass }: {
    title: string;
    value: string;
    subtitle: string;
    icon: React.ReactNode;
    valueClass?: string;
  }) => (
    <div className="bg-background border rounded-lg shadow-sm">
      <div className="flex flex-row items-center justify-between space-y-0 p-6 pb-2">
        <h3 className="text-sm font-medium">{title}</h3>
        <div className={valueClass || 'text-gray-600'}>
          {icon}
        </div>
      </div>
      <div className="p-6 pt-0">
        <div className={`text-2xl font-bold ${valueClass || ''}`}>
          {value}
        </div>
        <p className="text-xs text-muted-foreground">
          {subtitle}
        </p>
      </div>
    </div>
  );

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <SummaryCard
        title="Total P&L"
        value={formatCurrency(totalPnL)}
        subtitle="Realized + Unrealized"
        icon={getPnLIcon(totalPnL)}
        valueClass={getPnLColor(totalPnL)}
      />
      
      <SummaryCard
        title="Realized P&L"
        value={formatCurrency(realizedPnL)}
        subtitle="From closed positions"
        icon={<DollarSign className="h-4 w-4" />}
        valueClass={getPnLColor(realizedPnL)}
      />
      
      <SummaryCard
        title="Unrealized P&L"
        value={formatCurrency(unrealizedPnL)}
        subtitle="From open positions"
        icon={<Target className="h-4 w-4" />}
        valueClass={getPnLColor(unrealizedPnL)}
      />
      
      <SummaryCard
        title="Win Rate"
        value={formatPercentage(winRate)}
        subtitle={`${totalTrades} total trades`}
        icon={<Trophy className="h-4 w-4" />}
        valueClass="text-blue-600 dark:text-blue-400"
      />
      
      <SummaryCard
        title="Avg Trade P&L"
        value={formatCurrency(avgTradePnL)}
        subtitle="Per trade average"
        icon={<Calculator className="h-4 w-4" />}
        valueClass={getPnLColor(avgTradePnL)}
      />
      
      <SummaryCard
        title="Largest Winner"
        value={formatCurrency(largestWinner)}
        subtitle="Best single trade"
        icon={<TrendingUp className="h-4 w-4" />}
        valueClass="text-green-600 dark:text-green-400"
      />
      
      <SummaryCard
        title="Largest Loser"
        value={formatCurrency(largestLoser)}
        subtitle="Worst single trade"
        icon={<AlertTriangle className="h-4 w-4" />}
        valueClass="text-red-600 dark:text-red-400"
      />
      
      <SummaryCard
        title="Total Trades"
        value={totalTrades.toLocaleString()}
        subtitle="All time trades"
        icon={<BarChart3 className="h-4 w-4" />}
      />
    </div>
  );
};