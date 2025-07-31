import { TickerPerformance } from '@/lib/api'

interface TickerPerformanceSectionProps {
  tickerPerformance: TickerPerformance[]
  dataErrors: {[key: string]: string}
  isInitialLoading: boolean
  isFiltering: boolean
  formatCurrency: (value: number) => string
  formatPercent: (value: number) => string
  onRetry: () => void
}

export default function TickerPerformanceSection({
  tickerPerformance,
  dataErrors,
  isInitialLoading,
  isFiltering,
  formatCurrency,
  formatPercent,
  onRetry
}: TickerPerformanceSectionProps) {
  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-medium">Performance by Ticker</h3>
        {isFiltering && <span className="text-xs text-muted-foreground animate-pulse">Updating...</span>}
      </div>
      
      {dataErrors.performance ? (
        <div className="text-center py-8 text-muted-foreground">
          <p>{dataErrors.performance}</p>
          <button
            onClick={onRetry}
            className="mt-2 text-xs text-primary hover:underline"
            disabled={isFiltering}
          >
            Retry
          </button>
        </div>
      ) : isInitialLoading ? (
        <div className="animate-pulse space-y-2">
          <div className="h-12 bg-muted rounded"></div>
          <div className="h-12 bg-muted rounded"></div>
          <div className="h-12 bg-muted rounded"></div>
        </div>
      ) : tickerPerformance.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          <p>No ticker performance data available</p>
          <p className="text-xs mt-1">Performance data will appear when you have trading history</p>
        </div>
      ) : (
        <div className="space-y-2">
          {tickerPerformance.slice(0, 10).map((perf, index) => (
            <div key={index} className="flex justify-between items-center p-4 bg-muted/50 rounded-lg">
              <div>
                <span className="font-medium text-lg">{perf.symbol}</span>
                <div className="text-sm text-muted-foreground">
                  {perf.total_trades} trades • {perf.current_positions} current
                </div>
              </div>
              <div className="text-right">
                <div className={`font-medium text-lg ${perf.total_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {formatCurrency(perf.total_return)}
                </div>
                <div className="text-sm text-muted-foreground">
                  {formatPercent(perf.win_rate)} win rate
                </div>
              </div>
            </div>
          ))}
          {tickerPerformance.length > 10 && (
            <div className="text-center text-sm text-muted-foreground pt-2">
              Showing top 10 of {tickerPerformance.length} tickers
            </div>
          )}
        </div>
      )}
    </div>
  )
}