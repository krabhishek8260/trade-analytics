'use client'

import { useState } from 'react'
import { ChevronDown, ChevronRight, TrendingUp, TrendingDown } from 'lucide-react'
import { BreakdownComponent } from '@/lib/api'

interface BreakdownComponentsProps {
  components: BreakdownComponent[]
  expandedComponents: Set<string>
  onToggleExpanded: (componentId: string) => void
  formatCurrency: (value: number) => string
  formatPercent: (value: number) => string
}

export function BreakdownComponents({
  components,
  expandedComponents,
  onToggleExpanded,
  formatCurrency,
  formatPercent
}: BreakdownComponentsProps) {
  
  if (components.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-muted-foreground">No breakdown data available</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {components.map((component) => (
        <div key={component.id} className="border rounded-lg overflow-hidden bg-card">
          {/* Component Header */}
          <div
            className="p-4 cursor-pointer hover:bg-muted/50 transition-colors"
            onClick={() => onToggleExpanded(component.id)}
          >
            <div className="flex items-center justify-between">
              {/* Left: Name and metadata */}
              <div className="flex items-center space-x-3">
                {expandedComponents.has(component.id) ? (
                  <ChevronDown className="w-5 h-5 text-muted-foreground" />
                ) : (
                  <ChevronRight className="w-5 h-5 text-muted-foreground" />
                )}
                <div>
                  <h4 className="font-semibold text-lg">{component.display_name}</h4>
                  <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                    <span>{component.position_count} position{component.position_count !== 1 ? 's' : ''}</span>
                    <span>•</span>
                    <span>{component.component_type}</span>
                  </div>
                </div>
              </div>

              {/* Right: Values and metrics */}
              <div className="text-right">
                <div className="flex items-center space-x-4">
                  {/* Main Value */}
                  <div>
                    <p className="text-xl font-bold">{formatCurrency(component.value)}</p>
                    <p className="text-sm text-muted-foreground">
                      {formatPercent(component.percentage)} of total
                    </p>
                  </div>

                  {/* Return/P&L */}
                  {component.total_return !== 0 && (
                    <div className="text-right">
                      <div className={`flex items-center space-x-1 ${
                        component.total_return >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {component.total_return >= 0 ? (
                          <TrendingUp className="w-4 h-4" />
                        ) : (
                          <TrendingDown className="w-4 h-4" />
                        )}
                        <span className="font-medium">
                          {formatCurrency(component.total_return)}
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        return
                      </p>
                    </div>
                  )}

                  {/* Market Value (if different from main value) */}
                  {component.market_value !== component.value && (
                    <div className="text-right">
                      <p className="font-medium">{formatCurrency(component.market_value)}</p>
                      <p className="text-sm text-muted-foreground">market value</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Expanded Position Details */}
          {expandedComponents.has(component.id) && (
            <div className="border-t bg-muted/10">
              <div className="p-4">
                {component.positions.length === 0 ? (
                  <p className="text-muted-foreground text-sm">No individual position details available</p>
                ) : (
                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <h5 className="font-medium text-sm text-muted-foreground">
                        Individual Positions ({component.positions.length})
                      </h5>
                      <div className="text-sm text-muted-foreground">
                        Cost Basis: {formatCurrency(component.cost_basis)}
                      </div>
                    </div>
                    
                    <div className="space-y-2">
                      {component.positions.map((position, index) => (
                        <div 
                          key={`${position.position_id}-${index}`} 
                          className="flex justify-between items-center p-3 bg-background rounded-md border text-sm"
                        >
                          {/* Position Details */}
                          <div className="flex-1">
                            <div className="flex items-center space-x-2">
                              <span className="font-medium">
                                {position.underlying_symbol}
                              </span>
                              {position.option_type && (
                                <>
                                  <span className="text-muted-foreground">
                                    {position.option_type.toUpperCase()}
                                  </span>
                                  <span className="text-muted-foreground">
                                    ${position.strike_price}
                                  </span>
                                </>
                              )}
                              {position.strategy && (
                                <span className="text-xs px-2 py-1 bg-muted rounded">
                                  {position.strategy}
                                </span>
                              )}
                            </div>
                            <div className="text-muted-foreground mt-1 flex items-center space-x-4">
                              <span>{position.contracts} contracts</span>
                              {position.expiration_date && (
                                <span>Exp: {position.expiration_date}</span>
                              )}
                            </div>
                          </div>

                          {/* Position Values */}
                          <div className="text-right space-y-1">
                            <div className="font-medium">
                              {formatCurrency(position.market_value)}
                            </div>
                            <div className={`text-sm flex items-center space-x-2 ${
                              position.total_return >= 0 ? 'text-green-600' : 'text-red-600'
                            }`}>
                              <span>{formatCurrency(position.total_return)}</span>
                              <span>({formatPercent(position.percent_change)})</span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}