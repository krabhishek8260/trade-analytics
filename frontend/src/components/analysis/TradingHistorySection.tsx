import { HistoricalOptionsOrder } from '@/lib/api'
import { SymbolLogo } from '@/components/ui/SymbolLogo'

interface TradingHistorySectionProps {
  orders: HistoricalOptionsOrder[]
  dataErrors: {[key: string]: string}
  isInitialLoading: boolean
  isFiltering: boolean
  historyExpanded: boolean
  setHistoryExpanded: (expanded: boolean) => void
  formatCurrency: (value: number) => string
  onRetry: () => void
}

export default function TradingHistorySection({
  orders,
  dataErrors,
  isInitialLoading,
  isFiltering,
  historyExpanded,
  setHistoryExpanded,
  formatCurrency,
  onRetry
}: TradingHistorySectionProps) {
  return (
    <div>
      <button
        onClick={() => setHistoryExpanded(!historyExpanded)}
        className="flex items-center justify-between w-full p-4 bg-muted/50 rounded-lg hover:bg-muted transition-colors"
      >
        <div className="flex items-center space-x-2">
          <h3 className="text-lg font-medium">
            Options Trading History
          </h3>
          {isFiltering && <span className="text-xs text-muted-foreground animate-pulse">Updating...</span>}
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-sm text-muted-foreground">
            {orders.length} order{orders.length !== 1 ? 's' : ''}
          </span>
          <svg
            className={`w-5 h-5 transition-transform ${historyExpanded ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m19 9-7 7-7-7" />
          </svg>
        </div>
      </button>

      {historyExpanded && (
        <div className="mt-4 space-y-2">
          {dataErrors.orders ? (
            <div className="text-center py-8 text-muted-foreground">
              <p>{dataErrors.orders}</p>
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
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-16 bg-muted rounded-lg"></div>
              ))}
            </div>
          ) : orders.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <p>No trading history found</p>
              <p className="text-xs mt-1">Orders will appear here when you have trading activity</p>
            </div>
          ) : (
            orders.map((order, index) => (
              <div key={index} className="p-4 border border-border rounded-lg bg-card">
                <div className="flex justify-between items-start">
                  <div>
                    <div className="flex items-center space-x-2 mb-1">
                      <SymbolLogo 
                        symbol={order.underlying_symbol || 'Unknown'} 
                        size="lg" 
                        showText={true}
                        className="font-medium text-lg"
                      />
                      <span className={`text-xs px-2 py-1 rounded ${
                        order.state === 'filled' ? 'bg-green-100 text-green-800' :
                        order.state === 'cancelled' ? 'bg-red-100 text-red-800' :
                        'bg-yellow-100 text-yellow-800'
                      }`}>
                        {order.state?.toUpperCase() || 'UNKNOWN'}
                      </span>
                      {order.strategy && (
                        <span className="text-xs px-2 py-1 rounded bg-blue-100 text-blue-800">
                          {order.strategy}
                        </span>
                      )}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {order.quantity || 0} × {order.option_type?.toUpperCase() || 'Unknown'} ${order.strike_price || 0} • Exp: {order.expiration_date || 'Unknown'}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {order.transaction_side?.toUpperCase() || 'Unknown'} {order.position_effect?.toUpperCase() || ''} • 
                      {order.legs_count > 1 ? ` ${order.legs_count} legs` : ' Single leg'}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {order.created_at ? new Date(order.created_at).toLocaleDateString() : 'Unknown date'} {order.created_at ? new Date(order.created_at).toLocaleTimeString() : ''}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-medium">
                      {formatCurrency(order.processed_premium || order.premium || 0)}
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {order.processed_premium_direction || order.direction || 'Unknown'}
                    </div>
                    {order.price && order.price > 0 && (
                      <div className="text-sm text-muted-foreground">
                        @ {formatCurrency(order.price)}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}