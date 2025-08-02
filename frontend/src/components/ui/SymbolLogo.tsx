'use client'

import { useState, useEffect } from 'react'
import { cn } from '@/lib/utils'

interface SymbolLogoProps {
  symbol: string
  size?: 'sm' | 'md' | 'lg'
  showText?: boolean
  className?: string
}

const sizeClasses = {
  sm: 'w-4 h-4',
  md: 'w-6 h-6',
  lg: 'w-8 h-8'
}

const textSizeClasses = {
  sm: 'text-xs',
  md: 'text-sm',
  lg: 'text-base'
}

export function SymbolLogo({ 
  symbol, 
  size = 'md', 
  showText = true,
  className 
}: SymbolLogoProps) {
  const [imageLoaded, setImageLoaded] = useState(false)
  const [imageError, setImageError] = useState(false)

  // Simple direct URL generation without complex logic
  const getLogoUrl = (symbol: string): string => {
    const cleanSymbol = symbol.toUpperCase().replace(/[^A-Z]/g, '')
    const timestamp = Date.now()
    return `/logos/${cleanSymbol}.png?v=${timestamp}`
  }

  const logoUrl = getLogoUrl(symbol)

  const handleImageLoad = () => {
    console.log(`Image loaded successfully for ${symbol}:`, logoUrl)
    setImageLoaded(true)
    setImageError(false)
  }

  const handleImageError = () => {
    console.warn(`Image failed to load for ${symbol}:`, logoUrl)
    setImageError(true)
    setImageLoaded(false)
  }

  // Reset state when symbol changes
  useEffect(() => {
    setImageLoaded(false)
    setImageError(false)
  }, [symbol])

  if (imageError) {
    return (
      <div className="flex items-center gap-2">
        <div className={cn(
          'bg-blue-100 text-blue-600 rounded flex items-center justify-center font-semibold border border-blue-200',
          sizeClasses[size],
          textSizeClasses[size]
        )}>
          {symbol.charAt(0)}
        </div>
        {showText && (
          <span className={cn('font-medium', textSizeClasses[size], className)}>
            {symbol}
          </span>
        )}
      </div>
    )
  }

  return (
    <div className="flex items-center gap-2">
      <img
        src={logoUrl}
        alt={`${symbol} logo`}
        className={cn('rounded object-contain', sizeClasses[size])}
        onLoad={handleImageLoad}
        onError={handleImageError}
        style={{ display: imageLoaded ? 'block' : 'none' }}
      />
      {!imageLoaded && !imageError && (
        <div className={cn(
          'bg-gray-200 animate-pulse rounded',
          sizeClasses[size]
        )} />
      )}
      {showText && (
        <span className={cn('font-medium', textSizeClasses[size], className)}>
          {symbol}
        </span>
      )}
    </div>
  )
} 