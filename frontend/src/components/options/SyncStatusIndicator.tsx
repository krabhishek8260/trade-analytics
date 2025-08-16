'use client'

import { useEffect, useState } from 'react'
import { OptionsOrdersSyncStatus, getOptionsOrdersSyncStatus } from '@/lib/api'

interface SyncStatusIndicatorProps {
  onSyncNeeded?: () => void
  className?: string
}

export default function SyncStatusIndicator({ 
  onSyncNeeded,
  className = ""
}: SyncStatusIndicatorProps) {
  const [syncStatus, setSyncStatus] = useState<OptionsOrdersSyncStatus | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchSyncStatus = async () => {
    try {
      const status = await getOptionsOrdersSyncStatus()
      setSyncStatus(status)
      
      // Notify parent if sync is needed
      if (status.sync_status === 'sync_needed' && onSyncNeeded) {
        onSyncNeeded()
      }
    } catch (error) {
      console.warn('Failed to fetch sync status:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchSyncStatus()
    // Refresh status every 30 seconds
    const interval = setInterval(fetchSyncStatus, 30000)
    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return (
      <div className={`flex items-center space-x-2 ${className}`}>
        <div className="w-2 h-2 bg-muted rounded-full animate-pulse"></div>
        <span className="text-xs text-muted-foreground">Checking sync status...</span>
      </div>
    )
  }

  if (!syncStatus) return null

  const getStatusIndicator = () => {
    switch (syncStatus.sync_status) {
      case 'up_to_date':
        return {
          color: 'bg-green-500',
          text: 'Up to date',
          textColor: 'text-green-600 dark:text-green-400'
        }
      case 'sync_needed':
        return {
          color: 'bg-yellow-500 animate-pulse',
          text: 'Sync needed',
          textColor: 'text-yellow-600 dark:text-yellow-400'
        }
      default:
        return {
          color: 'bg-gray-500',
          text: 'Unknown',
          textColor: 'text-gray-600 dark:text-gray-400'
        }
    }
  }

  const indicator = getStatusIndicator()

  return (
    <div className={`flex items-center space-x-2 ${className}`}>
      <div className={`w-2 h-2 rounded-full ${indicator.color}`}></div>
      <div className="text-xs">
        <span className={`font-medium ${indicator.textColor}`}>
          {indicator.text}
        </span>
        {syncStatus.last_sync && (
          <span className="text-muted-foreground ml-1">
            • Last: {new Date(syncStatus.last_sync).toLocaleString()}
          </span>
        )}
      </div>
    </div>
  )
}