'use client'

import { SummaryCard } from './SummaryCard'

interface ChainSummaryData {
  total_chains: number
  active_chains: number
  closed_chains: number
  total_orders: number
  avg_orders_per_chain: number
  net_premium_collected: number
  total_pnl: number
}

interface ChainSummaryProps {
  summary: ChainSummaryData
  formatCurrency: (value: number) => string
  className?: string
  onNetPremiumClick?: () => void
}

export function ChainSummary({ summary, formatCurrency, className = '', onNetPremiumClick }: ChainSummaryProps) {
  return (
    <div className={`grid-responsive ${className}`}>
      <SummaryCard
        title="Total Chains"
        value={summary.total_chains}
        subtitle={`${summary.active_chains} active, ${summary.closed_chains} closed`}
      />
      <SummaryCard
        title="Total Orders"
        value={summary.total_orders}
        subtitle={`Avg: ${summary.avg_orders_per_chain.toFixed(1)} per chain`}
      />
      <SummaryCard
        title="Net Premium"
        value={formatCurrency(summary.net_premium_collected)}
        subtitle="Collected"
        valueColor={summary.net_premium_collected >= 0 ? 'profit' : 'loss'}
        onClick={onNetPremiumClick}
      />
    </div>
  )
}
