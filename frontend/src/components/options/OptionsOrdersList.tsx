'use client'

import { useState } from 'react'
import { HistoricalOptionsOrder } from '@/lib/api'
import OptionsOrderRow from './OptionsOrderRow'

interface OptionsOrdersListProps {
  orders: HistoricalOptionsOrder[]
  loading?: boolean
  expandedOrders: { [orderId: string]: boolean }
  onOrderToggle: (orderId: string) => void
  formatCurrency: (value: number) => string
  formatDateTime: (dateStr: string | null) => string
}

export default function OptionsOrdersList({
  orders,
  loading = false,
  expandedOrders,
  onOrderToggle,
  formatCurrency,
  formatDateTime
}: OptionsOrdersListProps) {
  if (loading) {
    return (
      <div className="space-y-2">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-16 bg-muted/50 rounded animate-pulse"></div>
        ))}
      </div>
    )
  }

  if (orders.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-muted-foreground mb-2">No orders found</p>
        <p className="text-sm text-muted-foreground">
          Adjust your filters or sync your orders to see results.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {orders.map((order) => (
        <OptionsOrderRow
          key={order.order_id}
          order={order}
          isExpanded={expandedOrders[order.order_id] || false}
          onToggle={() => onOrderToggle(order.order_id)}
          formatCurrency={formatCurrency}
          formatDateTime={formatDateTime}
        />
      ))}
    </div>
  )
}