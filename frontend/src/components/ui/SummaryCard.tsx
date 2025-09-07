'use client'

interface SummaryCardProps {
  title: string
  value: string | number
  subtitle?: string
  valueColor?: 'profit' | 'loss' | 'neutral'
  variant?: 'default' | 'compact'
  className?: string
  onClick?: () => void
}

export function SummaryCard({ 
  title, 
  value, 
  subtitle, 
  valueColor = 'neutral',
  variant = 'default',
  className = '',
  onClick
}: SummaryCardProps) {
  const colorClasses = {
    profit: 'profit',
    loss: 'loss', 
    neutral: 'neutral'
  }

  const sizeClasses = variant === 'compact' 
    ? 'p-3 text-lg' 
    : 'p-4 text-2xl'

  const clickable = typeof onClick === 'function'
  const common = (
    <>
      <h4 className="text-sm font-medium text-muted-foreground mb-1">{title}</h4>
      <p className={`font-bold ${colorClasses[valueColor]} ${variant === 'compact' ? 'text-lg' : 'text-2xl'}`}>
        {value}
      </p>
      {subtitle && (
        <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
      )}
    </>
  )

  return clickable ? (
    <button
      type="button"
      onClick={onClick}
      className={`w-full text-left bg-muted/50 rounded-lg ${sizeClasses} ${className} hover:bg-muted transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-ring`}
    >
      {common}
    </button>
  ) : (
    <div className={`bg-muted/50 rounded-lg ${sizeClasses} ${className}`}>
      {common}
    </div>
  )
}
