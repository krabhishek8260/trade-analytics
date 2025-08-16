'use client'

import { useMemo, useState, useCallback } from 'react'
import { FixedSizeList as List, areEqual } from 'react-window'
import { memo } from 'react'
import { HistoricalOptionsOrder } from '@/lib/api'
import OptionsOrderRow from './OptionsOrderRow'

interface VirtualizedOrdersListProps {
  orders: HistoricalOptionsOrder[]
  height: number
  itemHeight?: number
  expandedOrders: { [orderId: string]: boolean }
  onOrderToggle: (orderId: string) => void
  formatCurrency: (value: number) => string
  formatDateTime: (dateStr: string | null) => string
}

interface OrderRowProps {
  index: number
  style: any
  data: {
    orders: HistoricalOptionsOrder[]
    expandedOrders: { [orderId: string]: boolean }
    onOrderToggle: (orderId: string) => void
    formatCurrency: (value: number) => string
    formatDateTime: (dateStr: string | null) => string
  }
}

// Memoized row component for better performance
const OrderRow = memo<OrderRowProps>(({ index, style, data }) => {
  const { orders, expandedOrders, onOrderToggle, formatCurrency, formatDateTime } = data
  const order = orders[index]

  if (!order) return null

  return (
    <div style={style}>
      <div className="px-2 pb-2">
        <OptionsOrderRow
          order={order}
          isExpanded={expandedOrders[order.order_id] || false}
          onToggle={() => onOrderToggle(order.order_id)}
          formatCurrency={formatCurrency}
          formatDateTime={formatDateTime}
        />
      </div>
    </div>
  )
}, areEqual)

OrderRow.displayName = 'OrderRow'

export default function VirtualizedOrdersList({
  orders,
  height,
  itemHeight = 120, // Estimated height per order row
  expandedOrders,
  onOrderToggle,
  formatCurrency,
  formatDateTime
}: VirtualizedOrdersListProps) {
  // Adjust item height based on whether orders are expanded
  const getItemSize = useCallback((index: number) => {
    const order = orders[index]
    if (!order) return itemHeight
    
    const isExpanded = expandedOrders[order.order_id]
    if (isExpanded) {
      // Expanded height includes legs details
      const baseExpandedHeight = 200
      const legsHeight = (order.legs_count || 1) * 60 // ~60px per leg
      return baseExpandedHeight + legsHeight
    }
    
    return itemHeight
  }, [orders, expandedOrders, itemHeight])

  const itemData = useMemo(() => ({
    orders,
    expandedOrders,
    onOrderToggle,
    formatCurrency,
    formatDateTime
  }), [orders, expandedOrders, onOrderToggle, formatCurrency, formatDateTime])

  if (orders.length === 0) {
    return (
      <div className="flex items-center justify-center h-48">
        <div className="text-center">
          <p className="text-muted-foreground mb-2">No orders found</p>
          <p className="text-sm text-muted-foreground">
            Adjust your filters or sync your orders to see results.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="border rounded-lg overflow-hidden">
      <List
        height={height}
        itemCount={orders.length}
        itemSize={getItemSize}
        itemData={itemData}
        className="scrollbar-thin scrollbar-thumb-muted scrollbar-track-transparent"
      >
        {OrderRow}
      </List>
    </div>
  )
}