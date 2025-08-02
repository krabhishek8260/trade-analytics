import React from 'react';
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface YearlyPnL {
  year: number;
  realized_pnl: number;
  unrealized_pnl: number;
  total_pnl: number;
  trade_count: number;
  win_rate: number;
}

interface YearlyPnLChartProps {
  yearlyData: YearlyPnL[];
  selectedYear?: number | null;
  onYearClick: (year: number) => void;
}

export const YearlyPnLChart: React.FC<YearlyPnLChartProps> = ({
  yearlyData,
  selectedYear,
  onYearClick,
}) => {
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatPercentage = (value: number) => {
    return `${value.toFixed(1)}%`;
  };

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-white dark:bg-gray-800 p-4 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg">
          <p className="font-semibold text-gray-900 dark:text-gray-100">{`Year: ${label}`}</p>
          <p className="text-green-600">
            {`Realized P&L: ${formatCurrency(data.realized_pnl)}`}
          </p>
          <p className="text-blue-600">
            {`Unrealized P&L: ${formatCurrency(data.unrealized_pnl)}`}
          </p>
          <p className="font-medium text-gray-700 dark:text-gray-300">
            {`Total P&L: ${formatCurrency(data.total_pnl)}`}
          </p>
          <p className="text-gray-600 dark:text-gray-400">
            {`Trades: ${data.trade_count}`}
          </p>
          <p className="text-gray-600 dark:text-gray-400">
            {`Win Rate: ${formatPercentage(data.win_rate)}`}
          </p>
          <p className="text-xs text-gray-500 mt-2">Click to filter symbol table</p>
        </div>
      );
    }
    return null;
  };

  const handleBarClick = (data: any) => {
    if (data && data.year) {
      onYearClick(data.year);
    }
  };

  // Prepare data for the chart
  const chartData = yearlyData.map(item => ({
    ...item,
    // Ensure all P&L values are numbers
    realized_pnl: Number(item.realized_pnl) || 0,
    unrealized_pnl: Number(item.unrealized_pnl) || 0,
    total_pnl: Number(item.total_pnl) || 0,
    // Highlight selected year
    fillOpacity: selectedYear === item.year ? 1 : 0.8,
  }));

  if (!chartData || chartData.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-gray-500">
        No yearly data available
      </div>
    );
  }

  return (
    <div className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart
          data={chartData}
          margin={{
            top: 20,
            right: 30,
            left: 20,
            bottom: 5,
          }}
        >
          <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
          <XAxis 
            dataKey="year" 
            tick={{ fontSize: 12 }}
            axisLine={{ stroke: '#374151' }}
            tickLine={{ stroke: '#374151' }}
          />
          <YAxis 
            yAxisId="pnl"
            tick={{ fontSize: 12 }}
            axisLine={{ stroke: '#374151' }}
            tickLine={{ stroke: '#374151' }}
            tickFormatter={formatCurrency}
          />
          <YAxis 
            yAxisId="trades"
            orientation="right"
            tick={{ fontSize: 12 }}
            axisLine={{ stroke: '#374151' }}
            tickLine={{ stroke: '#374151' }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend />
          
          {/* Realized P&L Bar */}
          <Bar
            yAxisId="pnl"
            dataKey="realized_pnl"
            name="Realized P&L"
            fill="#10b981"
            fillOpacity={0.8}
            stroke="#059669"
            strokeWidth={1}
            onClick={handleBarClick}
            className="cursor-pointer hover:fill-opacity-100"
          />
          
          {/* Unrealized P&L Bar */}
          <Bar
            yAxisId="pnl"
            dataKey="unrealized_pnl"
            name="Unrealized P&L"
            fill="#3b82f6"
            fillOpacity={0.8}
            stroke="#2563eb"
            strokeWidth={1}
            onClick={handleBarClick}
            className="cursor-pointer hover:fill-opacity-100"
          />
          
          {/* Trade Count Line */}
          <Line
            yAxisId="trades"
            type="monotone"
            dataKey="trade_count"
            name="Trade Count"
            stroke="#f59e0b"
            strokeWidth={2}
            dot={{ fill: '#f59e0b', r: 4 }}
            activeDot={{ r: 6, fill: '#f59e0b' }}
          />
        </ComposedChart>
      </ResponsiveContainer>
      
      {selectedYear && (
        <div className="mt-2 text-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">
            Selected: {selectedYear}
          </span>
        </div>
      )}
    </div>
  );
};