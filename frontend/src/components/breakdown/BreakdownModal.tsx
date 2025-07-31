'use client'

import { useState, useEffect } from 'react'
import { X, ChevronDown, ChevronRight, TrendingUp, TrendingDown, BarChart3, Filter, Download } from 'lucide-react'
import { 
  BreakdownResponse, 
  BreakdownRequest, 
  GroupingType, 
  SortType, 
  getTotalValueBreakdown, 
  getTotalReturnBreakdown,
  getGreeksBreakdown,
  FilterOptions
} from '@/lib/api'

interface BreakdownModalProps {
  isOpen: boolean
  onClose: () => void
  metricType: string
  metricDisplayName: string
  initialGrouping?: GroupingType
  initialSortBy?: SortType
}

export function BreakdownModal({
  isOpen,
  onClose,
  metricType,
  metricDisplayName,
  initialGrouping = GroupingType.SYMBOL,
  initialSortBy = SortType.VALUE
}: BreakdownModalProps) {
  const [breakdownData, setBreakdownData] = useState<BreakdownResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [currentGrouping, setCurrentGrouping] = useState(initialGrouping)
  const [currentSortBy, setCurrentSortBy] = useState(initialSortBy)
  const [sortDescending, setSortDescending] = useState(true)
  const [showCalculationDetails, setShowCalculationDetails] = useState(false)
  const [expandedComponents, setExpandedComponents] = useState<Set<string>>(new Set())
  const [filters, setFilters] = useState<FilterOptions>({})

  useEffect(() => {
    if (isOpen) {
      fetchBreakdownData()
    }
  }, [isOpen, metricType, currentGrouping, currentSortBy, sortDescending])

  const fetchBreakdownData = async () => {
    setLoading(true)
    setError(null)

    try {
      const request: BreakdownRequest = {
        metric_type: metricType,
        grouping: currentGrouping,
        sort_by: currentSortBy,
        sort_descending: sortDescending,
        include_calculation_details: true,
        filters: Object.keys(filters).length > 0 ? filters : undefined
      }

      let data: BreakdownResponse
      
      if (metricType === 'total_value') {
        data = await getTotalValueBreakdown(request)
      } else if (metricType === 'total_return') {
        data = await getTotalReturnBreakdown(request)
      } else if (metricType.includes('delta') || metricType.includes('gamma') || 
                 metricType.includes('theta') || metricType.includes('vega') || 
                 metricType.includes('rho')) {
        const greekType = metricType.replace('_breakdown', '')
        data = await getGreeksBreakdown(greekType, request)
      } else {
        throw new Error(`Unsupported metric type: ${metricType}`)
      }

      setBreakdownData(data)
    } catch (err) {
      console.error('Failed to fetch breakdown data:', err)
      setError(err instanceof Error ? err.message : 'Failed to load breakdown data')
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value)
  }

  const formatPercent = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'percent',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value / 100)
  }

  const toggleComponentExpanded = (componentId: string) => {
    const newExpanded = new Set(expandedComponents)
    if (newExpanded.has(componentId)) {
      newExpanded.delete(componentId)
    } else {
      newExpanded.add(componentId)
    }
    setExpandedComponents(newExpanded)
  }

  const handleGroupingChange = (newGrouping: GroupingType) => {
    setCurrentGrouping(newGrouping)
    setExpandedComponents(new Set()) // Reset expanded state
  }

  const handleSortChange = (newSort: SortType) => {
    if (newSort === currentSortBy) {
      setSortDescending(!sortDescending)
    } else {
      setCurrentSortBy(newSort)
      setSortDescending(true)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-background rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div className="flex items-center space-x-3">
            <BarChart3 className="w-6 h-6 text-primary" />
            <div>
              <h2 className="text-xl font-semibold">{metricDisplayName} Breakdown</h2>
              {breakdownData && (
                <p className="text-sm text-muted-foreground">
                  {breakdownData.total_positions} positions • {breakdownData.data_freshness} data
                </p>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-muted rounded-lg transition-colors"
            aria-label="Close breakdown"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Controls */}
        <div className="p-6 border-b bg-muted/20">
          <div className="flex flex-wrap items-center gap-4">
            {/* Grouping Controls */}
            <div className="flex items-center space-x-2">
              <label className="text-sm font-medium">Group by:</label>
              <select
                value={currentGrouping}
                onChange={(e) => handleGroupingChange(e.target.value as GroupingType)}
                className="px-3 py-1 border rounded-md text-sm bg-background"
              >
                <option value={GroupingType.SYMBOL}>Symbol</option>
                <option value={GroupingType.STRATEGY}>Strategy</option>
                <option value={GroupingType.POSITION_TYPE}>Position Type</option>
                <option value={GroupingType.EXPIRY}>Expiration</option>
              </select>
            </div>

            {/* Sort Controls */}
            <div className="flex items-center space-x-2">
              <label className="text-sm font-medium">Sort by:</label>
              <button
                onClick={() => handleSortChange(SortType.VALUE)}
                className={`px-3 py-1 text-sm rounded-md transition-colors ${
                  currentSortBy === SortType.VALUE 
                    ? 'bg-primary text-primary-foreground' 
                    : 'bg-muted hover:bg-muted/80'
                }`}
              >
                Value {currentSortBy === SortType.VALUE && (sortDescending ? '↓' : '↑')}
              </button>
              <button
                onClick={() => handleSortChange(SortType.RETURN)}
                className={`px-3 py-1 text-sm rounded-md transition-colors ${
                  currentSortBy === SortType.RETURN 
                    ? 'bg-primary text-primary-foreground' 
                    : 'bg-muted hover:bg-muted/80'
                }`}
              >
                Return {currentSortBy === SortType.RETURN && (sortDescending ? '↓' : '↑')}
              </button>
              <button
                onClick={() => handleSortChange(SortType.PERCENTAGE)}
                className={`px-3 py-1 text-sm rounded-md transition-colors ${
                  currentSortBy === SortType.PERCENTAGE 
                    ? 'bg-primary text-primary-foreground' 
                    : 'bg-muted hover:bg-muted/80'
                }`}
              >
                % {currentSortBy === SortType.PERCENTAGE && (sortDescending ? '↓' : '↑')}
              </button>
            </div>

            {/* Action buttons */}
            <div className="flex items-center space-x-2 ml-auto">
              <button
                onClick={() => setShowCalculationDetails(!showCalculationDetails)}
                className="px-3 py-1 text-sm bg-muted hover:bg-muted/80 rounded-md transition-colors flex items-center space-x-1"
              >
                <BarChart3 className="w-4 h-4" />
                <span>Calculation Details</span>
              </button>
              <button
                onClick={fetchBreakdownData}
                disabled={loading}
                className="px-3 py-1 text-sm bg-primary text-primary-foreground hover:bg-primary/90 rounded-md transition-colors disabled:opacity-50"
              >
                {loading ? 'Refreshing...' : 'Refresh'}
              </button>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading && (
            <div className="space-y-4">
              <div className="animate-pulse">
                <div className="h-4 bg-muted rounded w-1/4 mb-4"></div>
                <div className="space-y-2">
                  <div className="h-16 bg-muted rounded"></div>
                  <div className="h-16 bg-muted rounded"></div>
                  <div className="h-16 bg-muted rounded"></div>
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className="bg-destructive/10 border border-destructive/20 rounded-md p-4">
              <p className="text-destructive text-sm">{error}</p>
              <button
                onClick={fetchBreakdownData}
                className="mt-2 text-xs text-destructive hover:underline"
              >
                Try again
              </button>
            </div>
          )}

          {breakdownData && !loading && (
            <div className="space-y-6">
              {/* Summary */}
              <div className="bg-muted/20 rounded-lg p-4">
                <h3 className="text-lg font-semibold mb-3">Summary</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Total Value</p>
                    <p className="text-xl font-bold">{formatCurrency(breakdownData.total_value)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Method</p>
                    <p className="text-lg font-medium">{breakdownData.calculation_method}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Components</p>
                    <p className="text-lg font-medium">{breakdownData.components.length}</p>
                  </div>
                </div>
              </div>

              {/* Calculation Details */}
              {showCalculationDetails && breakdownData.calculation_details && (
                <div className="bg-blue-50 dark:bg-blue-950/20 rounded-lg p-4">
                  <h3 className="text-lg font-semibold mb-3">Calculation Details</h3>
                  <div className="space-y-4">
                    <div>
                      <p className="text-sm font-medium">Formula:</p>
                      <code className="text-sm bg-muted px-2 py-1 rounded">
                        {breakdownData.calculation_details.final_formula}
                      </code>
                    </div>
                    <div>
                      <p className="text-sm font-medium">Example:</p>
                      <p className="text-sm text-muted-foreground">
                        {breakdownData.calculation_details.example}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm font-medium">Methodology Notes:</p>
                      <ul className="text-sm text-muted-foreground list-disc list-inside space-y-1">
                        {breakdownData.calculation_details.methodology_notes.map((note, index) => (
                          <li key={index}>{note}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              )}

              {/* Components */}
              <div>
                <h3 className="text-lg font-semibold mb-3">
                  Breakdown by {currentGrouping.charAt(0).toUpperCase() + currentGrouping.slice(1)}
                </h3>
                <div className="space-y-2">
                  {breakdownData.components.map((component) => (
                    <div key={component.id} className="border rounded-lg overflow-hidden">
                      <div
                        className="p-4 bg-muted/10 cursor-pointer hover:bg-muted/20 transition-colors"
                        onClick={() => toggleComponentExpanded(component.id)}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-3">
                            {expandedComponents.has(component.id) ? (
                              <ChevronDown className="w-5 h-5" />
                            ) : (
                              <ChevronRight className="w-5 h-5" />
                            )}
                            <div>
                              <h4 className="font-medium">{component.display_name}</h4>
                              <p className="text-sm text-muted-foreground">
                                {component.position_count} positions
                              </p>
                            </div>
                          </div>
                          <div className="text-right">
                            <p className="font-bold">{formatCurrency(component.value)}</p>
                            <div className="flex items-center space-x-2 text-sm">
                              <span className="text-muted-foreground">
                                {formatPercent(component.percentage)}
                              </span>
                              {component.total_return !== 0 && (
                                <span className={component.total_return >= 0 ? 'text-green-600' : 'text-red-600'}>
                                  {component.total_return >= 0 ? (
                                    <TrendingUp className="w-4 h-4 inline mr-1" />
                                  ) : (
                                    <TrendingDown className="w-4 h-4 inline mr-1" />
                                  )}
                                  {formatCurrency(component.total_return)}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Expanded Positions */}
                      {expandedComponents.has(component.id) && (
                        <div className="border-t bg-background">
                          <div className="p-4">
                            <div className="space-y-2">
                              {component.positions.map((position, index) => (
                                <div key={index} className="flex justify-between items-center p-3 bg-muted/20 rounded-md text-sm">
                                  <div>
                                    <div className="font-medium">
                                      {position.underlying_symbol} {position.option_type?.toUpperCase()} 
                                      ${position.strike_price} {position.expiration_date}
                                    </div>
                                    <div className="text-muted-foreground">
                                      {position.contracts} contracts • {position.strategy}
                                    </div>
                                  </div>
                                  <div className="text-right">
                                    <div className="font-medium">
                                      {formatCurrency(position.market_value)}
                                    </div>
                                    <div className={position.total_return >= 0 ? 'text-green-600' : 'text-red-600'}>
                                      {formatCurrency(position.total_return)} ({formatPercent(position.percent_change)})
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}