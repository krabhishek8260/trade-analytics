interface AnalysisFiltersProps {
  filters: {
    ticker: string
    strategy: string
    positionType: string
    daysBack: number
    orderState: string
  }
  setFilters: React.Dispatch<React.SetStateAction<{
    ticker: string
    strategy: string
    positionType: string
    daysBack: number
    orderState: string
  }>>
  uniqueTickers: string[]
  uniqueStrategies: string[]
  isInitialLoading: boolean
  isFiltering: boolean
}

export default function AnalysisFilters({
  filters,
  setFilters,
  uniqueTickers,
  uniqueStrategies,
  isInitialLoading,
  isFiltering
}: AnalysisFiltersProps) {
  return (
    <div className="bg-muted/50 rounded-lg p-4 mb-6">
      <h3 className="text-lg font-medium mb-3">Filters & Search</h3>
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <div>
          <label className="block text-sm font-medium text-muted-foreground mb-1">Ticker</label>
          <select
            value={filters.ticker}
            onChange={(e) => setFilters(prev => ({ ...prev, ticker: e.target.value }))}
            className="w-full p-2 border border-border rounded-md bg-background"
            disabled={isInitialLoading || isFiltering || uniqueTickers.length === 0}
          >
            <option value="">
              {isInitialLoading ? 'Loading tickers...' : uniqueTickers.length === 0 ? 'No tickers available' : 'All Tickers'}
            </option>
            {uniqueTickers.map(ticker => (
              <option key={ticker} value={ticker}>{ticker}</option>
            ))}
          </select>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-muted-foreground mb-1">Strategy Type</label>
          <select
            value={filters.strategy}
            onChange={(e) => setFilters(prev => ({ ...prev, strategy: e.target.value }))}
            className="w-full p-2 border border-border rounded-md bg-background"
            disabled={isInitialLoading || isFiltering || uniqueStrategies.length === 0}
          >
            <option value="">
              {isInitialLoading ? 'Loading strategies...' : uniqueStrategies.length === 0 ? 'All Strategies' : 'All Strategies'}
            </option>
            {uniqueStrategies.map(strategy => (
              <option key={strategy} value={strategy}>{strategy}</option>
            ))}
          </select>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-muted-foreground mb-1">Position</label>
          <select
            value={filters.positionType}
            onChange={(e) => setFilters(prev => ({ ...prev, positionType: e.target.value }))}
            className="w-full p-2 border border-border rounded-md bg-background"
          >
            <option value="">All Positions</option>
            <option value="long">Long</option>
            <option value="short">Short</option>
          </select>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-muted-foreground mb-1">Days Back</label>
          <select
            value={filters.daysBack}
            onChange={(e) => setFilters(prev => ({ ...prev, daysBack: Number(e.target.value) }))}
            className="w-full p-2 border border-border rounded-md bg-background"
          >
            <option value={7}>7 Days</option>
            <option value={30}>30 Days</option>
            <option value={90}>90 Days</option>
            <option value={365}>1 Year</option>
          </select>
        </div>
        
        <div>
          <label className="block text-sm font-medium text-muted-foreground mb-1">Order State</label>
          <select
            value={filters.orderState}
            onChange={(e) => setFilters(prev => ({ ...prev, orderState: e.target.value }))}
            className="w-full p-2 border border-border rounded-md bg-background"
          >
            <option value="">All States</option>
            <option value="filled">Filled</option>
            <option value="cancelled">Cancelled</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>
      </div>
    </div>
  )
}