'use client'

import { useEffect, useState } from 'react'

interface SyncProgressData {
  status: string
  progress: number
  current_batch?: number
  total_batches?: number
  orders_processed?: number
  orders_stored?: number
  message?: string
  timestamp?: string
}

interface SyncProgressIndicatorProps {
  isVisible: boolean
  onComplete?: () => void
  className?: string
}

export default function SyncProgressIndicator({ 
  isVisible, 
  onComplete,
  className = ""
}: SyncProgressIndicatorProps) {
  const [progress, setProgress] = useState<SyncProgressData | null>(null)
  const [isAnimating, setIsAnimating] = useState(false)

  // Simulate progress updates (in real implementation, this would come from API/WebSocket)
  useEffect(() => {
    if (!isVisible) {
      setProgress(null)
      setIsAnimating(false)
      return
    }

    setIsAnimating(true)
    let currentProgress = 0
    
    const interval = setInterval(() => {
      currentProgress += Math.random() * 15 + 5 // Random progress increment
      
      if (currentProgress >= 100) {
        currentProgress = 100
        setProgress({
          status: 'completed',
          progress: 100,
          message: 'Sync completed successfully',
          timestamp: new Date().toISOString()
        })
        
        clearInterval(interval)
        
        // Call completion callback after a brief delay
        setTimeout(() => {
          onComplete?.()
          setIsAnimating(false)
        }, 1500)
        
        return
      }

      setProgress({
        status: 'processing',
        progress: Math.min(currentProgress, 100),
        current_batch: Math.floor(currentProgress / 12.5) + 1,
        total_batches: 8,
        orders_processed: Math.floor(currentProgress * 5.7),
        orders_stored: Math.floor(currentProgress * 4.2),
        message: 'Processing options orders...',
        timestamp: new Date().toISOString()
      })
    }, 800)

    return () => clearInterval(interval)
  }, [isVisible, onComplete])

  if (!isVisible || !progress) return null

  const isComplete = progress.status === 'completed'
  const progressPercentage = Math.max(0, Math.min(100, progress.progress))

  return (
    <div className={`bg-muted/80 backdrop-blur-sm rounded-lg p-4 border ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          {!isComplete ? (
            <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
          ) : (
            <div className="w-4 h-4 bg-green-500 rounded-full flex items-center justify-center">
              <svg className="w-2.5 h-2.5 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
            </div>
          )}
          <span className="font-medium text-sm">
            {isComplete ? 'Sync Complete' : 'Syncing Orders'}
          </span>
        </div>
        <span className="text-sm text-muted-foreground">
          {progressPercentage.toFixed(0)}%
        </span>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-muted rounded-full h-2 mb-3">
        <div 
          className={`h-2 rounded-full transition-all duration-300 ${
            isComplete ? 'bg-green-500' : 'bg-primary'
          }`}
          style={{ width: `${progressPercentage}%` }}
        />
      </div>

      {/* Progress Details */}
      {progress.message && (
        <p className="text-sm text-muted-foreground mb-2">
          {progress.message}
        </p>
      )}

      <div className="flex justify-between text-xs text-muted-foreground">
        <div className="flex space-x-4">
          {progress.current_batch && progress.total_batches && (
            <span>
              Batch {progress.current_batch} of {progress.total_batches}
            </span>
          )}
          {progress.orders_processed !== undefined && (
            <span>
              Processed: {progress.orders_processed}
            </span>
          )}
          {progress.orders_stored !== undefined && (
            <span>
              Stored: {progress.orders_stored}
            </span>
          )}
        </div>
        {progress.timestamp && (
          <span>
            {new Date(progress.timestamp).toLocaleTimeString()}
          </span>
        )}
      </div>
    </div>
  )
}