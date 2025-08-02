import { OptionPosition } from '@/lib/api'

interface FilteredPositionsSectionProps {
  filters: {
    ticker: string
    strategy: string
    positionType: string
    daysBack: number
    orderState: string
  }
  filteredPositions: OptionPosition[]
  dataErrors: {[key: string]: string}
  isFiltering: boolean
  positionsExpanded: boolean
  setPositionsExpanded: (expanded: boolean) => void
  formatCurrency: (value: number) => string
  formatPercent: (value: number) => string
  onRetry: () => void
}

export default function FilteredPositionsSection({
  filters,
  filteredPositions,
  dataErrors,
  isFiltering,
  positionsExpanded,
  setPositionsExpanded,
  formatCurrency,
  formatPercent,
  onRetry
}: FilteredPositionsSectionProps) {
  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-medium">Filtered Current Positions</h3>
        {isFiltering && <span className="text-xs text-muted-foreground animate-pulse">Filtering...</span>}
      </div>
      
      {(filters.ticker || filters.strategy || filters.positionType) ? (
        dataErrors.filtered ? (
          <div className="text-center py-8 text-muted-foreground">
            <p>{dataErrors.filtered}</p>
            <button
              onClick={onRetry}
              className="mt-2 text-xs text-primary hover:underline"
              disabled={isFiltering}
            >
              Retry
            </button>
          </div>
        ) : filteredPositions.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <p>No positions match the current filters</p>
            <p className="text-xs mt-1">Try adjusting your filter criteria</p>
          </div>
        ) : (
          <>
            <button
              onClick={() => setPositionsExpanded(!positionsExpanded)}
              className="flex items-center justify-between w-full p-4 bg-muted/50 rounded-lg hover:bg-muted transition-colors mb-3"
            >
              <span className="font-medium">
                {filteredPositions.length} position{filteredPositions.length !== 1 ? 's' : ''} found
              </span>
              <svg
                className={`w-5 h-5 transition-transform ${positionsExpanded ? 'rotate-180' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m19 9-7 7-7-7" />
              </svg>
            </button>
            <div className="space-y-2">
              {(positionsExpanded ? filteredPositions : filteredPositions.slice(0, 5)).map((position, index) => (
                <div key={index} className="flex justify-between items-center p-4 bg-muted/50 rounded-lg">
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="font-medium text-lg">{position.underlying_symbol}</span>
                      <span className={`text-xs px-2 py-1 rounded ${
                        position.strategy.includes('BUY') ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                      }`}>
                        {position.strategy}
                      </span>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {position.contracts} × {position.option_type.toUpperCase()} ${position.strike_price} • Exp: {position.expiration_date}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-medium text-lg">{formatCurrency(position.market_value)}</div>
                    <div className={`text-sm ${position.total_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {formatCurrency(position.total_return)} ({formatPercent(position.percent_change)})
                    </div>
                  </div>
                </div>
              ))}
              {!positionsExpanded && filteredPositions.length > 5 && (
                <button
                  onClick={() => setPositionsExpanded(true)}
                  className="w-full text-center text-sm text-primary hover:text-primary/80 pt-2 py-2 rounded hover:bg-muted/30 transition-colors"
                >
                  Show {filteredPositions.length - 5} more positions
                </button>
              )}
            </div>
          </>
        )
      ) : (
        <div className="text-center py-8 text-muted-foreground">
          <p>Apply filters above to see filtered positions</p>
          <p className="text-xs mt-1">Select a ticker, strategy, or position type to filter your current positions</p>
        </div>
      )}
    </div>
  )
}