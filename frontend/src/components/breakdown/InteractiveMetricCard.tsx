'use client'

import { useRouter } from 'next/navigation'

interface InteractiveMetricCardProps {
  title: string
  value: number
  subtitle?: string
  isPositive?: boolean | null
  formatValue: (value: number) => string
  metricType: string // 'total_value', 'total_return', etc.
  className?: string
  loading?: boolean
}

export function InteractiveMetricCard({
  title,
  value,
  subtitle,
  isPositive,
  formatValue,
  metricType,
  className = '',
  loading = false
}: InteractiveMetricCardProps) {
  const router = useRouter()

  const handleClick = () => {
    if (!loading) {
      router.push(`/dashboard/breakdown/${metricType}`)
    }
  }

  const getColorClass = () => {
    if (isPositive === null || isPositive === undefined) {
      return 'text-foreground'
    }
    return isPositive ? 'text-green-600' : 'text-red-600'
  }

  if (loading) {
    return (
      <div className={`bg-muted/50 rounded-lg p-4 ${className}`}>
        <div className="animate-pulse">
          <div className="h-4 bg-muted rounded mb-2"></div>
          <div className="h-8 bg-muted rounded mb-2"></div>
          {subtitle && <div className="h-3 bg-muted rounded w-3/4"></div>}
        </div>
      </div>
    )
  }

  return (
    <>
      <div 
        className={`bg-muted/50 rounded-lg p-4 cursor-pointer hover:bg-muted/70 transition-colors group ${className}`}
        onClick={handleClick}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            handleClick()
          }
        }}
        aria-label={`Click to see breakdown of ${title}`}
      >
        <div className="flex items-center justify-between mb-1">
          <h3 className="text-sm font-medium text-muted-foreground">{title}</h3>
          <svg
            className="w-4 h-4 text-muted-foreground group-hover:text-foreground transition-colors"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth={2} 
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" 
            />
          </svg>
        </div>
        <p className={`text-2xl font-bold ${getColorClass()}`}>
          {formatValue(value)}
        </p>
        {subtitle && (
          <p className="text-sm text-muted-foreground">{subtitle}</p>
        )}
        <div className="mt-2 text-xs text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity">
          Click for detailed breakdown
        </div>
      </div>
    </>
  )
}