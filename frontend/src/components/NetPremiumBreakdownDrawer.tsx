"use client"

import { useEffect, useMemo, useState } from 'react'
import { X } from 'lucide-react'
import { OptionsChain, getRolledOptionsChains } from '@/lib/api'

interface NetPremiumBreakdownDrawerProps {
  isOpen: boolean
  onClose: () => void
  formatCurrency: (value: number) => string
  daysBack?: number
  status?: 'active' | 'closed' | 'expired' | 'all'
}

type ViewMode = 'symbol' | 'strategy' | 'matrix'

export default function NetPremiumBreakdownDrawer({ isOpen, onClose, formatCurrency, daysBack = 180, status }: NetPremiumBreakdownDrawerProps) {
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>([])
  const [selectedStrategies, setSelectedStrategies] = useState<string[]>([])
  const [view, setView] = useState<ViewMode>('symbol')
  const [sortDesc, setSortDesc] = useState(true)
  const [loadingAll, setLoadingAll] = useState(false)
  const [error, setError] = useState<string | undefined>()
  const [progress, setProgress] = useState<{ current: number; total: number }>({ current: 0, total: 0 })
  const [allChains, setAllChains] = useState<OptionsChain[]>([])
  const [symbolQuery, setSymbolQuery] = useState('')
  const [strategyQuery, setStrategyQuery] = useState('')
  
  const bucketClass = (value: number, maxAbs: number, kind: 'cell' | 'chip' = 'cell') => {
    if (!value) return kind === 'cell' ? 'heatmap-cell empty' : 'heatmap-chip empty'
    const abs = Math.abs(value)
    const ratio = maxAbs > 0 ? abs / maxAbs : 0
    const level = Math.min(5, Math.max(1, Math.ceil(ratio * 5)))
    const base = value > 0 ? `hm-pos-${level}` : `hm-neg-${level}`
    return `${kind === 'cell' ? 'heatmap-cell' : 'heatmap-chip'} ${base}`
  }

  useEffect(() => {
    if (!isOpen) return
    let cancelled = false
    async function run() {
      try {
        setLoadingAll(true)
        setError(undefined)
        setProgress({ current: 0, total: 0 })
        const baseParams: any = { days_back: daysBack, page: 1, limit: 100, use_database: true }
        if (status && status !== 'all') baseParams.status = status
        const first = await getRolledOptionsChains(baseParams)
        if (cancelled) return
        const totalPages = first.pagination?.total_pages || 1
        const acc: OptionsChain[] = [...first.chains]
        setProgress({ current: Math.min(1, totalPages), total: totalPages })
        if (totalPages > 1) {
          const promises: Promise<OptionsChain[]>[] = []
          for (let p = 2; p <= totalPages; p++) {
            promises.push(getRolledOptionsChains({ ...baseParams, page: p }).then(r => r.chains))
          }
          const results = await Promise.all(promises.map(async pr => {
            const data = await pr
            if (!cancelled) setProgress(prev => ({ current: Math.min(prev.current + 1, totalPages), total: totalPages }))
            return data
          }))
          results.forEach(arr => acc.push(...arr))
        }
        if (!cancelled) setAllChains(acc)
      } catch (e: any) {
        if (!cancelled) setError(e?.message || 'Failed to load chains')
      } finally {
        if (!cancelled) setLoadingAll(false)
      }
    }
    run()
    return () => { cancelled = true }
  }, [isOpen, daysBack, status])

  const allSymbols = useMemo(() => {
    const base = Array.from(new Set(allChains.map(c => c.underlying_symbol))).sort()
    if (!symbolQuery) return base
    const q = symbolQuery.toUpperCase()
    return base.filter(s => s.toUpperCase().includes(q))
  }, [allChains, symbolQuery])

  const allStrategies = useMemo(() => {
    const base = Array.from(new Set(allChains.map(c => (c as any).initial_strategy).filter(Boolean))).sort()
    if (!strategyQuery) return base
    const q = strategyQuery.toLowerCase()
    return base.filter(s => s.toLowerCase().includes(q))
  }, [allChains, strategyQuery])

  const filteredChains = useMemo(() => {
    return allChains.filter(c => {
      const symbolOk = selectedSymbols.length === 0 || selectedSymbols.includes(c.underlying_symbol)
      const strategyOk = selectedStrategies.length === 0 || selectedStrategies.includes((c as any).initial_strategy)
      return symbolOk && strategyOk
    })
  }, [allChains, selectedSymbols, selectedStrategies])

  const totals = useMemo(() => {
    const totalNet = filteredChains.reduce((s, c) => s + (c.net_premium || 0), 0)
    const credits = filteredChains.reduce((s, c) => s + (c.total_credits_collected || 0), 0)
    const debits = filteredChains.reduce((s, c) => s + (c.total_debits_paid || 0), 0)
    return { totalNet, credits, debits, count: filteredChains.length }
  }, [filteredChains])

  const bySymbol = useMemo(() => {
    const map = new Map<string, { symbol: string; net: number; credits: number; debits: number; chains: number }>()
    filteredChains.forEach(c => {
      const m = map.get(c.underlying_symbol) || { symbol: c.underlying_symbol, net: 0, credits: 0, debits: 0, chains: 0 }
      m.net += c.net_premium || 0
      m.credits += c.total_credits_collected || 0
      m.debits += c.total_debits_paid || 0
      m.chains += 1
      map.set(c.underlying_symbol, m)
    })
    const arr = Array.from(map.values())
    arr.sort((a, b) => sortDesc ? b.net - a.net : a.net - b.net)
    return arr
  }, [filteredChains, sortDesc])

  const maxAbsBySymbol = useMemo(() => {
    return Math.max(0, ...bySymbol.map(r => Math.abs(r.net)))
  }, [bySymbol])

  const byStrategy = useMemo(() => {
    const map = new Map<string, { strategy: string; net: number; credits: number; debits: number; chains: number }>()
    filteredChains.forEach(c => {
      const strategy = (c as any).initial_strategy || 'UNKNOWN'
      const m = map.get(strategy) || { strategy, net: 0, credits: 0, debits: 0, chains: 0 }
      m.net += c.net_premium || 0
      m.credits += c.total_credits_collected || 0
      m.debits += c.total_debits_paid || 0
      m.chains += 1
      map.set(strategy, m)
    })
    const arr = Array.from(map.values())
    arr.sort((a, b) => sortDesc ? b.net - a.net : a.net - b.net)
    return arr
  }, [filteredChains, sortDesc])

  const maxAbsByStrategy = useMemo(() => {
    return Math.max(0, ...byStrategy.map(r => Math.abs(r.net)))
  }, [byStrategy])

  const matrix = useMemo(() => {
    // symbol -> strategy -> { net, credits, debits, chains }
    const map = new Map<string, Map<string, { net: number; credits: number; debits: number; chains: number }>>()
    filteredChains.forEach(c => {
      const sym = c.underlying_symbol
      const strat = (c as any).initial_strategy || 'UNKNOWN'
      if (!map.has(sym)) map.set(sym, new Map())
      const inner = map.get(sym)!
      const cell = inner.get(strat) || { net: 0, credits: 0, debits: 0, chains: 0 }
      cell.net += c.net_premium || 0
      cell.credits += c.total_credits_collected || 0
      cell.debits += c.total_debits_paid || 0
      cell.chains += 1
      inner.set(strat, cell)
    })
    return map
  }, [filteredChains])

  const toggleSel = (current: string[], value: string, set: (v: string[]) => void) => {
    if (current.includes(value)) set(current.filter(v => v !== value))
    else set([...current, value])
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="absolute right-0 top-0 h-full w-full max-w-5xl bg-background border-l border-border shadow-xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b">
          <div>
            <h3 className="text-lg font-semibold">Net Premium Breakdown</h3>
            <p className="text-xs text-muted-foreground">Slice by symbol and strategy; multi‑select supported</p>
          </div>
          <button aria-label="Close" className="p-2 rounded hover:bg-muted" onClick={onClose}>
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Load indicator */}
        <div className="px-4 py-2 border-b text-sm">
          {loadingAll ? (
            <div className="flex items-center gap-2">
              <span className="inline-flex h-2 w-2 rounded-full bg-blue-500 animate-pulse"></span>
              <span>Fetching all chains…</span>
              {progress.total > 1 && (
                <span className="text-xs text-muted-foreground">({progress.current}/{progress.total} pages)</span>
              )}
            </div>
          ) : error ? (
            <div className="text-red-600 dark:text-red-400">{error}</div>
          ) : null}
        </div>

        {/* Controls */}
        <div className="p-6 border-b grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-muted-foreground">Symbols</label>
              <div className="flex items-center gap-2">
                <button className="text-xs px-2 py-1 border rounded hover:bg-muted" onClick={() => setSelectedSymbols(allSymbols)}>Select All</button>
                <button className="text-xs px-2 py-1 border rounded hover:bg-muted" onClick={() => setSelectedSymbols([])}>Clear</button>
              </div>
            </div>
            <input
              value={symbolQuery}
              onChange={(e) => setSymbolQuery(e.target.value)}
              placeholder="Search symbols"
              className="form-input h-8 mb-2"
            />
            <div className="max-h-40 overflow-auto border rounded p-2 space-y-1">
              {allSymbols.map(sym => (
                <label key={sym} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={selectedSymbols.includes(sym)}
                    onChange={() => toggleSel(selectedSymbols, sym, setSelectedSymbols)}
                  />
                  <span>{sym}</span>
                </label>
              ))}
              {allSymbols.length === 0 && (
                <div className="text-xs text-muted-foreground">No symbols</div>
              )}
            </div>
          </div>
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-muted-foreground">Strategies</label>
              <div className="flex items-center gap-2">
                <button className="text-xs px-2 py-1 border rounded hover:bg-muted" onClick={() => setSelectedStrategies(allStrategies)}>Select All</button>
                <button className="text-xs px-2 py-1 border rounded hover:bg-muted" onClick={() => setSelectedStrategies([])}>Clear</button>
              </div>
            </div>
            <input
              value={strategyQuery}
              onChange={(e) => setStrategyQuery(e.target.value)}
              placeholder="Search strategies"
              className="form-input h-8 mb-2"
            />
            <div className="max-h-40 overflow-auto border rounded p-2 space-y-1">
              {allStrategies.map(st => (
                <label key={st} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={selectedStrategies.includes(st)}
                    onChange={() => toggleSel(selectedStrategies, st, setSelectedStrategies)}
                  />
                  <span>{st}</span>
                </label>
              ))}
              {allStrategies.length === 0 && (
                <div className="text-xs text-muted-foreground">No strategies</div>
              )}
            </div>
          </div>
          <div className="flex flex-col gap-3">
            <label className="text-sm font-medium text-muted-foreground">View</label>
            <div className="inline-flex rounded-md border overflow-hidden w-max">
              {(['symbol','strategy','matrix'] as ViewMode[]).map(v => (
                <button
                  key={v}
                  className={`px-3 py-1.5 text-sm border-r last:border-r-0 ${view === v ? 'bg-muted font-medium' : 'hover:bg-muted/60'}`}
                  onClick={() => setView(v)}
                >
                  {v === 'symbol' ? 'By Symbol' : v === 'strategy' ? 'By Strategy' : 'Matrix'}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-2">
              <button
                className="px-3 py-1.5 text-sm rounded border hover:bg-muted"
                onClick={() => { setSelectedSymbols([]); setSelectedStrategies([]) }}
              >
                Clear Filters
              </button>
              <button
                className="px-3 py-1.5 text-sm rounded border hover:bg-muted"
                onClick={() => setSortDesc(s => !s)}
                title="Toggle sort by Net Premium"
              >
                Sort: {sortDesc ? 'Desc' : 'Asc'}
              </button>
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span>Legend:</span>
              <span className="inline-block w-4 h-3 rounded bg-green-700"></span>
              <span>Profit</span>
              <span className="inline-block w-4 h-3 rounded bg-red-700 ml-2"></span>
              <span>Loss</span>
            </div>
          </div>
        </div>

        {/* Summary */}
        <div className="px-4 py-3 border-b flex flex-wrap items-center gap-4 text-sm">
          <div>
            <span className="text-muted-foreground">Total Net:</span>
            <span className={`ml-1 font-medium ${totals.totalNet >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>{formatCurrency(totals.totalNet)}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Credits:</span>
            <span className="ml-1 font-medium text-green-600 dark:text-green-400">{formatCurrency(totals.credits)}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Debits:</span>
            <span className="ml-1 font-medium text-red-600 dark:text-red-400">{formatCurrency(totals.debits)}</span>
          </div>
          <div className="text-muted-foreground">Chains: <span className="font-medium text-foreground ml-1">{totals.count}</span></div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-4 heatmap-grid">
          {view === 'symbol' && (
            <div>
              <table className="heatmap-table">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Net Premium</th>
                    <th>Credits</th>
                    <th>Debits</th>
                    <th>Chains</th>
                  </tr>
                </thead>
                <tbody>
                  {bySymbol.map(row => (
                    <tr key={row.symbol}>
                      <td className="font-medium">{row.symbol}</td>
                      <td>
                        <span className={bucketClass(row.net, maxAbsBySymbol, 'chip')}>
                          {formatCurrency(row.net)}
                        </span>
                      </td>
                      <td className="text-green-600 dark:text-green-300">{formatCurrency(row.credits)}</td>
                      <td className="text-red-600 dark:text-red-300">{formatCurrency(row.debits)}</td>
                      <td>{row.chains}</td>
                    </tr>
                  ))}
                  {bySymbol.length === 0 && (
                    <tr>
                      <td className="py-6 text-center text-muted-foreground" colSpan={5}>No data</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}

          {view === 'strategy' && (
            <div>
              <table className="heatmap-table">
                <thead>
                  <tr>
                    <th>Strategy</th>
                    <th>Net Premium</th>
                    <th>Credits</th>
                    <th>Debits</th>
                    <th>Chains</th>
                  </tr>
                </thead>
                <tbody>
                  {byStrategy.map(row => (
                    <tr key={row.strategy}>
                      <td className="font-medium">{row.strategy}</td>
                      <td>
                        <span className={bucketClass(row.net, maxAbsByStrategy, 'chip')}>
                          {formatCurrency(row.net)}
                        </span>
                      </td>
                      <td className="text-green-600 dark:text-green-300">{formatCurrency(row.credits)}</td>
                      <td className="text-red-600 dark:text-red-300">{formatCurrency(row.debits)}</td>
                      <td>{row.chains}</td>
                    </tr>
                  ))}
                  {byStrategy.length === 0 && (
                    <tr>
                      <td className="py-6 text-center text-muted-foreground" colSpan={5}>No data</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}

          {view === 'matrix' && (
            <div>
              <table className="heatmap-table">
                <thead>
                  <tr>
                    <th>Symbol \ Strategy</th>
                    {allStrategies.map(st => (
                      <th key={st} className="whitespace-nowrap">{st}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {allSymbols.map(sym => {
                    const row = matrix.get(sym)
                    if (!row) return (<tr key={sym}><td className="font-medium">{sym}</td></tr>)
                    return (
                      <tr key={sym} className="align-top">
                        <td className="font-medium whitespace-nowrap">{sym}</td>
                        {(() => {
                          const maxAbs = Math.max(0, ...allStrategies.map(s => Math.abs(row.get(s)?.net || 0)))
                          return allStrategies.map(st => {
                            const val = row.get(st)?.net || 0
                            return (
                              <td key={st} className={bucketClass(val, maxAbs, 'cell')}>
                                {val !== 0 ? formatCurrency(val) : '-'}
                              </td>
                            )
                          })
                        })()}
                      </tr>
                    )
                  })}
                  {allSymbols.length === 0 && (
                    <tr>
                      <td className="py-6 text-center text-muted-foreground" colSpan={1 + allStrategies.length}>No data</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
