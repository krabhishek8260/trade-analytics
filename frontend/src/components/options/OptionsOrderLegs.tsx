'use client'

import { HistoricalOptionsOrder } from '@/lib/api'

interface OptionsOrderLegsProps {
  order: HistoricalOptionsOrder
  formatCurrency: (value: number) => string
}

export default function OptionsOrderLegs({
  order,
  formatCurrency
}: OptionsOrderLegsProps) {
  return (
    <div className="border-t bg-muted/30 p-4">
      <h4 className="font-medium mb-3">Order Details ({order.legs_count} legs)</h4>
      
      {/* Order Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4 text-sm">
        <div>
          <span className="text-muted-foreground">Order ID: </span>
          <span className="font-mono text-xs">{order.order_id}</span>
        </div>
        <div>
          <span className="text-muted-foreground">Type: </span>
          <span>{order.type || 'N/A'}</span>
        </div>
        <div>
          <span className="text-muted-foreground">Quantity: </span>
          <span>{order.processed_quantity || 0} contracts</span>
        </div>
      </div>
      
      {/* Strategy Information */}
      {(order.strategy || order.opening_strategy || order.closing_strategy) && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4 text-sm">
          {order.strategy && (
            <div>
              <span className="text-muted-foreground">Strategy: </span>
              <span className="capitalize">{order.strategy}</span>
            </div>
          )}
          {order.opening_strategy && (
            <div>
              <span className="text-muted-foreground">Opening: </span>
              <span className="capitalize">{order.opening_strategy}</span>
            </div>
          )}
          {order.closing_strategy && (
            <div>
              <span className="text-muted-foreground">Closing: </span>
              <span className="capitalize">{order.closing_strategy}</span>
            </div>
          )}
        </div>
      )}
      
      {/* Legs Details */}
      {order.legs_details && order.legs_details.length > 0 && (
        <div>
          <h5 className="font-medium mb-2">Legs:</h5>
          <div className="space-y-2">
            {order.legs_details.map((leg: any, idx: number) => (
              <div key={idx} className="flex items-center p-3 bg-background rounded border">
                <div className="flex items-center space-x-4 text-sm">
                  <span className="font-medium bg-muted px-2 py-1 rounded text-xs">
                    Leg {idx + 1}
                  </span>
                  <div className="flex items-center space-x-2">
                    <span className={`px-2 py-1 rounded text-xs ${
                      leg.side === 'buy' 
                        ? 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200'
                        : 'bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200'
                    }`}>
                      {leg.side?.toUpperCase()}
                    </span>
                    <span className={`px-2 py-1 rounded text-xs ${
                      leg.position_effect === 'open'
                        ? 'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200'
                        : 'bg-orange-100 dark:bg-orange-900 text-orange-800 dark:text-orange-200'
                    }`}>
                      {leg.position_effect?.toUpperCase()}
                    </span>
                  </div>
                  <div className="font-mono text-sm">
                    <span className="font-medium">${leg.strike_price}</span>
                    <span className="ml-1 text-muted-foreground">
                      {leg.option_type?.toUpperCase()}
                    </span>
                  </div>
                  <span className="text-muted-foreground text-xs">
                    {leg.expiration_date}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Single Leg Fallback */}
      {(!order.legs_details || order.legs_details.length === 0) && order.legs_count === 1 && (
        <div>
          <h5 className="font-medium mb-2">Single Leg Order:</h5>
          <div className="flex items-center p-3 bg-background rounded border">
            <div className="flex items-center space-x-4 text-sm">
              <span className="font-medium bg-muted px-2 py-1 rounded text-xs">
                Single Leg
              </span>
              <div className="font-mono">
                <span className="font-medium">${order.strike_price}</span>
                <span className="ml-1 text-muted-foreground">
                  {order.option_type?.toUpperCase()}
                </span>
              </div>
              <span className="text-muted-foreground text-xs">
                {order.expiration_date}
              </span>
            </div>
          </div>
        </div>
      )}
      
      {/* Premium Breakdown */}
      <div className="mt-4 pt-4 border-t">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div>
            <span className="text-muted-foreground">Premium per Contract: </span>
            <span className="font-medium">
              {formatCurrency(order.premium || 0)}
            </span>
          </div>
          <div>
            <span className="text-muted-foreground">Total Premium: </span>
            <span className="font-medium">
              {formatCurrency(order.processed_premium || 0)}
            </span>
          </div>
          <div>
            <span className="text-muted-foreground">Direction: </span>
            <span className={`font-medium capitalize ${
              order.direction === 'credit' ? 'text-green-600' : 'text-red-600'
            }`}>
              {order.direction}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}