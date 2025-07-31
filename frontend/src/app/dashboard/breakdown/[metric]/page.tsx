'use client'

import { useState, useEffect } from 'react'
import { useRouter, useParams, useSearchParams } from 'next/navigation'
import { ArrowLeft, BarChart3, Download, RefreshCw, Settings, Share } from 'lucide-react'
import { 
  BreakdownResponse, 
  BreakdownRequest, 
  GroupingType, 
  SortType, 
  getTotalValueBreakdown, 
  getTotalReturnBreakdown,
  getGreeksBreakdown,
  checkAuthStatus
} from '@/lib/api'
import { BreakdownComponents } from '@/components/breakdown/BreakdownComponents'

export default function BreakdownPage() {
  const router = useRouter()
  const params = useParams()
  const searchParams = useSearchParams()
  
  const metric = params.metric as string
  const [breakdownData, setBreakdownData] = useState<BreakdownResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  
  // State from URL parameters
  const [currentGrouping, setCurrentGrouping] = useState<GroupingType>(
    (searchParams.get('grouping') as GroupingType) || GroupingType.SYMBOL
  )
  const [currentSortBy, setCurrentSortBy] = useState<SortType>(
    (searchParams.get('sortBy') as SortType) || SortType.VALUE
  )
  const [sortDescending, setSortDescending] = useState(
    searchParams.get('sortDesc') !== 'false'
  )
  const [showCalculationDetails, setShowCalculationDetails] = useState(
    searchParams.get('showCalc') === 'true'
  )
  const [expandedComponents, setExpandedComponents] = useState<Set<string>>(new Set())

  // Auth check
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const authStatus = localStorage.getItem('robinhood_authenticated')
        if (authStatus === 'true') {
          const backendAuth = await checkAuthStatus()
          setIsAuthenticated(backendAuth.authenticated)
          if (!backendAuth.authenticated) {
            router.push('/login')
          }
        } else {
          router.push('/login')
        }
      } catch (error) {
        console.error('Auth check failed:', error)
        router.push('/login')
      }
    }
    checkAuth()
  }, [router])

  // Update URL when state changes
  useEffect(() => {
    if (!isAuthenticated) return
    
    const params = new URLSearchParams()
    params.set('grouping', currentGrouping)
    params.set('sortBy', currentSortBy)
    params.set('sortDesc', sortDescending.toString())
    if (showCalculationDetails) params.set('showCalc', 'true')
    
    const newUrl = `/dashboard/breakdown/${metric}?${params.toString()}`
    window.history.replaceState({}, '', newUrl)
  }, [metric, currentGrouping, currentSortBy, sortDescending, showCalculationDetails, isAuthenticated])

  // Fetch breakdown data
  useEffect(() => {
    if (!isAuthenticated) return
    fetchBreakdownData()
  }, [metric, currentGrouping, currentSortBy, sortDescending, isAuthenticated])

  const fetchBreakdownData = async () => {
    setLoading(true)
    setError(null)

    try {
      const request: BreakdownRequest = {
        metric_type: metric,
        grouping: currentGrouping,
        sort_by: currentSortBy,
        sort_descending: sortDescending,
        include_calculation_details: true
      }

      let data: BreakdownResponse
      
      if (metric === 'total_value') {
        data = await getTotalValueBreakdown(request)
      } else if (metric === 'total_return') {
        data = await getTotalReturnBreakdown(request)
      } else if (['delta', 'gamma', 'theta', 'vega', 'rho'].includes(metric)) {
        data = await getGreeksBreakdown(metric, request)
      } else {
        throw new Error(`Unsupported metric type: ${metric}`)
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

  const getMetricDisplayName = (metric: string) => {
    const names: Record<string, string> = {
      'total_value': 'Portfolio Total Value',
      'total_return': 'Portfolio Total Return',
      'delta': 'Portfolio Delta',
      'gamma': 'Portfolio Gamma',
      'theta': 'Portfolio Theta', 
      'vega': 'Portfolio Vega',
      'rho': 'Portfolio Rho'
    }
    return names[metric] || metric.charAt(0).toUpperCase() + metric.slice(1)
  }

  const handleGroupingChange = (newGrouping: GroupingType) => {
    setCurrentGrouping(newGrouping)
    setExpandedComponents(new Set())
  }

  const handleSortChange = (newSort: SortType) => {
    if (newSort === currentSortBy) {
      setSortDescending(!sortDescending)
    } else {
      setCurrentSortBy(newSort)
      setSortDescending(true)
    }
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

  const handleShare = async () => {
    try {
      await navigator.share({
        title: `${getMetricDisplayName(metric)} Breakdown`,
        url: window.location.href
      })
    } catch (err) {
      // Fallback to clipboard
      await navigator.clipboard.writeText(window.location.href)
      // Could add a toast notification here
    }
  }

  const handleExport = () => {
    // TODO: Implement export functionality
    console.log('Export functionality to be implemented')
  }

  if (!isAuthenticated) {
    return null // Will redirect to login
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-40">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            {/* Left: Navigation and Title */}
            <div className="flex items-center space-x-4">
              <button
                onClick={() => router.push('/dashboard')}
                className="flex items-center space-x-2 text-muted-foreground hover:text-foreground transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>Dashboard</span>
              </button>
              <div className="text-muted-foreground">/</div>
              <div className="flex items-center space-x-2">
                <BarChart3 className="w-5 h-5 text-primary" />
                <h1 className="text-xl font-semibold">{getMetricDisplayName(metric)} Breakdown</h1>
              </div>
            </div>

            {/* Right: Actions */}
            <div className="flex items-center space-x-2">
              {breakdownData && (
                <div className="text-sm text-muted-foreground hidden md:block">
                  {breakdownData.total_positions} positions • {breakdownData.data_freshness} data
                </div>
              )}
              <button
                onClick={handleShare}
                className="p-2 hover:bg-muted rounded-lg transition-colors"
                title="Share breakdown"
              >
                <Share className="w-4 h-4" />
              </button>
              <button
                onClick={handleExport}
                className="p-2 hover:bg-muted rounded-lg transition-colors"
                title="Export data"
              >
                <Download className="w-4 h-4" />
              </button>
              <button
                onClick={fetchBreakdownData}
                disabled={loading}
                className="p-2 hover:bg-muted rounded-lg transition-colors disabled:opacity-50"
                title="Refresh data"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="border-b bg-muted/20">
        <div className="container mx-auto px-4 py-4">
          <div className="flex flex-wrap items-center gap-4">
            {/* Metric Switcher */}
            <div className="flex items-center space-x-2">
              <label className="text-sm font-medium">Metric:</label>
              <select
                value={metric}
                onChange={(e) => router.push(`/dashboard/breakdown/${e.target.value}`)}
                className="px-3 py-1 border rounded-md text-sm bg-background"
              >
                <option value="total_value">Total Value</option>
                <option value="total_return">Total Return</option>
                <option value="delta">Delta</option>
                <option value="gamma">Gamma</option>
                <option value="theta">Theta</option>
                <option value="vega">Vega</option>
                <option value="rho">Rho</option>
              </select>
            </div>

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

            {/* Calculation Details Toggle */}
            <div className="flex items-center space-x-2 ml-auto">
              <button
                onClick={() => setShowCalculationDetails(!showCalculationDetails)}
                className={`px-3 py-1 text-sm rounded-md transition-colors flex items-center space-x-1 ${
                  showCalculationDetails
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted hover:bg-muted/80'
                }`}
              >
                <Settings className="w-4 h-4" />
                <span>Calculation Details</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-6">
        {loading && (
          <div className="space-y-6">
            {/* Summary skeleton */}
            <div className="bg-muted/20 rounded-lg p-6">
              <div className="animate-pulse">
                <div className="h-5 bg-muted rounded w-1/6 mb-4"></div>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                  <div className="space-y-2">
                    <div className="h-4 bg-muted rounded w-3/4"></div>
                    <div className="h-8 bg-muted rounded w-full"></div>
                  </div>
                  <div className="space-y-2">
                    <div className="h-4 bg-muted rounded w-3/4"></div>
                    <div className="h-6 bg-muted rounded w-full"></div>
                  </div>
                  <div className="space-y-2">
                    <div className="h-4 bg-muted rounded w-3/4"></div>
                    <div className="h-6 bg-muted rounded w-1/2"></div>
                  </div>
                  <div className="space-y-2">
                    <div className="h-4 bg-muted rounded w-3/4"></div>
                    <div className="h-6 bg-muted rounded w-full"></div>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Components skeleton */}
            <div className="space-y-3">
              <div className="h-5 bg-muted rounded w-1/4 mb-4"></div>
              <div className="space-y-3">
                <div className="border rounded-lg p-4 bg-card">
                  <div className="animate-pulse flex justify-between items-center">
                    <div className="flex items-center space-x-3">
                      <div className="w-5 h-5 bg-muted rounded"></div>
                      <div className="space-y-2">
                        <div className="h-5 bg-muted rounded w-32"></div>
                        <div className="h-4 bg-muted rounded w-24"></div>
                      </div>
                    </div>
                    <div className="space-y-2 text-right">
                      <div className="h-6 bg-muted rounded w-24"></div>
                      <div className="h-4 bg-muted rounded w-16"></div>
                    </div>
                  </div>
                </div>
                <div className="border rounded-lg p-4 bg-card">
                  <div className="animate-pulse flex justify-between items-center">
                    <div className="flex items-center space-x-3">
                      <div className="w-5 h-5 bg-muted rounded"></div>
                      <div className="space-y-2">
                        <div className="h-5 bg-muted rounded w-28"></div>
                        <div className="h-4 bg-muted rounded w-20"></div>
                      </div>
                    </div>
                    <div className="space-y-2 text-right">
                      <div className="h-6 bg-muted rounded w-24"></div>
                      <div className="h-4 bg-muted rounded w-16"></div>
                    </div>
                  </div>
                </div>
                <div className="border rounded-lg p-4 bg-card">
                  <div className="animate-pulse flex justify-between items-center">
                    <div className="flex items-center space-x-3">
                      <div className="w-5 h-5 bg-muted rounded"></div>
                      <div className="space-y-2">
                        <div className="h-5 bg-muted rounded w-36"></div>
                        <div className="h-4 bg-muted rounded w-28"></div>
                      </div>
                    </div>
                    <div className="space-y-2 text-right">
                      <div className="h-6 bg-muted rounded w-24"></div>
                      <div className="h-4 bg-muted rounded w-16"></div>
                    </div>
                  </div>
                </div>
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
            <div className="bg-muted/20 rounded-lg p-6">
              <h2 className="text-lg font-semibold mb-4">Summary</h2>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <div>
                  <p className="text-sm text-muted-foreground">Total Value</p>
                  <p className="text-2xl font-bold">{formatCurrency(breakdownData.total_value)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Calculation Method</p>
                  <p className="text-lg font-medium">{breakdownData.calculation_method}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Components</p>
                  <p className="text-lg font-medium">{breakdownData.components.length}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Last Updated</p>
                  <p className="text-lg font-medium">
                    {new Date(breakdownData.last_updated).toLocaleTimeString()}
                  </p>
                </div>
              </div>
            </div>

            {/* Calculation Details */}
            {showCalculationDetails && breakdownData.calculation_details && (
              <div className="bg-blue-50 dark:bg-blue-950/20 rounded-lg p-6">
                <h3 className="text-lg font-semibold mb-4">Calculation Details</h3>
                <div className="space-y-4">
                  <div>
                    <p className="text-sm font-medium mb-1">Formula:</p>
                    <code className="text-sm bg-muted px-2 py-1 rounded block">
                      {breakdownData.calculation_details.final_formula}
                    </code>
                  </div>
                  <div>
                    <p className="text-sm font-medium mb-1">Example:</p>
                    <p className="text-sm text-muted-foreground">
                      {breakdownData.calculation_details.example}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm font-medium mb-1">Methodology Notes:</p>
                    <ul className="text-sm text-muted-foreground list-disc list-inside space-y-1">
                      {breakdownData.calculation_details.methodology_notes.map((note, index) => (
                        <li key={index}>{note}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* Components Breakdown */}
            <div>
              <h3 className="text-lg font-semibold mb-4">
                Breakdown by {currentGrouping.charAt(0).toUpperCase() + currentGrouping.slice(1)}
              </h3>
              
              <BreakdownComponents
                components={breakdownData.components}
                expandedComponents={expandedComponents}
                onToggleExpanded={toggleComponentExpanded}
                formatCurrency={formatCurrency}
                formatPercent={formatPercent}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}