'use client'

import { HistoricalOptionsOrder } from '@/lib/api'
import { SymbolLogo } from '@/components/ui/SymbolLogo'
import OptionsOrderLegs from './OptionsOrderLegs'

interface OptionsOrderRowProps {
  order: HistoricalOptionsOrder
  isExpanded: boolean
  onToggle: () => void
  formatCurrency: (value: number) => string
  formatDateTime: (dateStr: string | null) => string
}

export default function OptionsOrderRow({
  order,
  isExpanded,
  onToggle,
  formatCurrency,
  formatDateTime
}: OptionsOrderRowProps) {
  return (
    <div className="bg-gradient-to-r from-card/50 to-card/80 rounded-xl overflow-hidden border border-muted/30 shadow-sm hover:shadow-md transition-all duration-200">
      {/* Order Summary Row */}
      <button
        onClick={onToggle}
        className="w-full p-4 text-left hover:bg-muted/30 transition-all duration-200 flex items-center justify-between group"
      >
        <div className="flex-1">
          <div className="flex items-center mb-2">
            <SymbolLogo 
              symbol={order.chain_symbol || order.underlying_symbol}
              size="sm" 
              showText={true}
              className="font-semibold text-base"
            />
          </div>
          
          <div className="flex flex-wrap items-center gap-1.5 mb-2">
            {/* Action Badge */}
            {(order.side || order.legs_details?.[0]?.side) && (
              <span className={`text-xs px-2 py-0.5 rounded font-medium ${
                (order.side || order.legs_details?.[0]?.side)?.toLowerCase() === 'buy'
                  ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
                  : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'
              }`}>
                {(order.side || order.legs_details?.[0]?.side)?.toUpperCase()} {(order.position_effect || order.legs_details?.[0]?.position_effect)?.toUpperCase()}
              </span>
            )}
            
            {/* Contracts Badge */}
            {order.processed_quantity && (
              <span className="text-xs px-2 py-0.5 rounded font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300">
                {order.processed_quantity} contracts
              </span>
            )}
            
            {/* Strike Price Badge */}
            {order.strike_price && (
              <span className="text-xs px-2 py-0.5 rounded font-medium bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300">
                ${order.strike_price} {order.option_type?.toUpperCase()}
              </span>
            )}
            
            {/* Expiration Badge */}
            {(order.expiration_date || order.legs_details?.[0]?.expiration_date) && (
              <span className="text-xs px-2 py-0.5 rounded font-medium bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300">
                {order.expiration_date || order.legs_details?.[0]?.expiration_date}
              </span>
            )}
            
            {/* Strategy Badge */}
            {order.strategy && (
              <span className="text-xs px-2 py-0.5 rounded font-medium bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-300">
                {order.strategy}
              </span>
            )}
            
            {/* Legs Badge */}
            <span className="text-xs px-2 py-0.5 rounded font-medium bg-slate-100 text-slate-800 dark:bg-slate-900/30 dark:text-slate-300">
              {order.legs_count} {order.legs_count === 1 ? 'leg' : 'legs'}
            </span>
          </div>
          
          <div className="text-xs text-muted-foreground mt-1">
            {formatDateTime(order.created_at)}
          </div>
        </div>
        
        <div className="text-right space-y-1">
          <div className={`font-bold text-lg ${
            (order.direction === 'credit' ? 1 : -1) * (order.processed_premium || 0) >= 0 
              ? 'text-green-600 dark:text-green-400' 
              : 'text-red-600 dark:text-red-400'
          }`}>
            {order.direction === 'credit' ? '+' : '-'}{formatCurrency(order.processed_premium || 0)}
          </div>
          <div className="text-xs text-muted-foreground">
            {formatCurrency((order.processed_premium || 0) / Math.max(order.processed_quantity || 1, 1))}/contract
          </div>
        </div>
        
        <svg
          className={`w-5 h-5 ml-3 transition-all duration-200 group-hover:scale-110 ${
            isExpanded ? 'rotate-180' : ''
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="m19 9-7 7-7-7" />
        </svg>
      </button>
      
      {/* Expanded Details */}
      {isExpanded && (
        <OptionsOrderLegs 
          order={order}
          formatCurrency={formatCurrency}
        />
      )}
    </div>
  )
}