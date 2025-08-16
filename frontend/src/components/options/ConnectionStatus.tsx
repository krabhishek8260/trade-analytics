'use client'

import { useState, useEffect } from 'react'

interface ConnectionStatusProps {
  onReconnect?: () => void
  className?: string
}

type ConnectionState = 'online' | 'offline' | 'slow' | 'reconnecting'

export default function ConnectionStatus({ 
  onReconnect,
  className = ""
}: ConnectionStatusProps) {
  const [connectionState, setConnectionState] = useState<ConnectionState>('online')
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())

  useEffect(() => {
    const handleOnline = () => {
      setConnectionState('online')
      setLastUpdate(new Date())
    }

    const handleOffline = () => {
      setConnectionState('offline')
    }

    // Check connection speed by measuring API response time
    const checkConnectionSpeed = async () => {
      if (!navigator.onLine) {
        setConnectionState('offline')
        return
      }

      try {
        const start = Date.now()
        const response = await fetch('/api/backend/health', { 
          method: 'HEAD',
          cache: 'no-cache'
        })
        const duration = Date.now() - start

        if (response.ok) {
          if (duration > 3000) {
            setConnectionState('slow')
          } else {
            setConnectionState('online')
          }
          setLastUpdate(new Date())
        } else {
          setConnectionState('offline')
        }
      } catch (error) {
        setConnectionState('offline')
      }
    }

    // Initial check
    checkConnectionSpeed()

    // Set up event listeners
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    // Periodic connection checks
    const interval = setInterval(checkConnectionSpeed, 30000) // Every 30 seconds

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
      clearInterval(interval)
    }
  }, [])

  const handleRetry = async () => {
    setConnectionState('reconnecting')
    
    try {
      const response = await fetch('/api/backend/health', { cache: 'no-cache' })
      if (response.ok) {
        setConnectionState('online')
        setLastUpdate(new Date())
        onReconnect?.()
      } else {
        setConnectionState('offline')
      }
    } catch (error) {
      setConnectionState('offline')
    }
  }

  if (connectionState === 'online') {
    return null // Don't show anything when connection is good
  }

  const getStatusConfig = () => {
    switch (connectionState) {
      case 'offline':
        return {
          color: 'bg-red-500',
          textColor: 'text-red-600 dark:text-red-400',
          bgColor: 'bg-red-50 dark:bg-red-950/20',
          borderColor: 'border-red-200 dark:border-red-800',
          icon: (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 5.636l-12.728 12.728m0-12.728l12.728 12.728" />
            </svg>
          ),
          message: 'Connection lost',
          description: 'Unable to connect to server. Some features may not work properly.'
        }
      case 'slow':
        return {
          color: 'bg-yellow-500',
          textColor: 'text-yellow-600 dark:text-yellow-400',
          bgColor: 'bg-yellow-50 dark:bg-yellow-950/20',
          borderColor: 'border-yellow-200 dark:border-yellow-800',
          icon: (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.464 0L4.35 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          ),
          message: 'Slow connection',
          description: 'Connection is slower than usual. Data may take longer to load.'
        }
      case 'reconnecting':
        return {
          color: 'bg-blue-500 animate-pulse',
          textColor: 'text-blue-600 dark:text-blue-400',
          bgColor: 'bg-blue-50 dark:bg-blue-950/20',
          borderColor: 'border-blue-200 dark:border-blue-800',
          icon: (
            <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          ),
          message: 'Reconnecting...',
          description: 'Attempting to restore connection.'
        }
      default:
        return null
    }
  }

  const config = getStatusConfig()
  if (!config) return null

  return (
    <div className={`${config.bgColor} border ${config.borderColor} rounded-lg p-3 ${className}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className={`w-2 h-2 rounded-full ${config.color}`}></div>
          <div className="flex items-center space-x-2">
            <div className={config.textColor}>
              {config.icon}
            </div>
            <div>
              <span className={`font-medium ${config.textColor}`}>
                {config.message}
              </span>
              <p className="text-sm text-muted-foreground">
                {config.description}
              </p>
            </div>
          </div>
        </div>
        
        {connectionState !== 'reconnecting' && (
          <button
            onClick={handleRetry}
            className={`px-3 py-1 text-sm font-medium rounded ${config.textColor} hover:bg-opacity-20 hover:bg-current`}
          >
            Retry
          </button>
        )}
      </div>
      
      {lastUpdate && connectionState !== 'offline' && (
        <div className="text-xs text-muted-foreground mt-2">
          Last updated: {lastUpdate.toLocaleTimeString()}
        </div>
      )}
    </div>
  )
}