'use client'

import { useState, useEffect } from 'react'
import { triggerOptionsOrdersSync, getOptionsOrdersSyncStatus } from '@/lib/api'
import SyncProgressIndicator from './SyncProgressIndicator'

interface NewUserOnboardingProps {
  isVisible: boolean
  onComplete: () => void
  onDismiss?: () => void
}

export default function NewUserOnboarding({
  isVisible,
  onComplete,
  onDismiss
}: NewUserOnboardingProps) {
  const [step, setStep] = useState<'welcome' | 'syncing' | 'completed'>('welcome')
  const [syncStarted, setSyncStarted] = useState(false)

  const handleStartSync = async () => {
    try {
      setStep('syncing')
      setSyncStarted(true)
      
      // Trigger full sync for new users
      await triggerOptionsOrdersSync(true, 365)
      
    } catch (error) {
      console.error('Error starting initial sync:', error)
      // Handle error but don't stop the onboarding
    }
  }

  const handleSyncComplete = () => {
    setStep('completed')
    
    // Auto-complete after showing success message
    setTimeout(() => {
      onComplete()
    }, 2000)
  }

  const handleSkip = () => {
    if (onDismiss) {
      onDismiss()
    } else {
      onComplete()
    }
  }

  if (!isVisible) return null

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-background rounded-lg shadow-xl max-w-md w-full p-6">
        {step === 'welcome' && (
          <>
            <div className="text-center mb-6">
              <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <h2 className="text-2xl font-bold mb-2">Welcome to Options History!</h2>
              <p className="text-muted-foreground">
                Let's sync your options trading history to get started. This will take a few minutes 
                but only needs to happen once.
              </p>
            </div>

            <div className="bg-muted/50 rounded-lg p-4 mb-6">
              <h3 className="font-medium mb-2">What we'll sync:</h3>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• Up to 1 year of options orders</li>
                <li>• Multi-leg strategies and individual trades</li>
                <li>• Complete order details and executions</li>
                <li>• Real-time progress tracking</li>
              </ul>
            </div>

            <div className="flex space-x-3">
              <button
                onClick={handleStartSync}
                className="flex-1 px-4 py-3 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 font-medium"
              >
                Sync My Orders
              </button>
              <button
                onClick={handleSkip}
                className="px-4 py-3 text-muted-foreground hover:text-foreground border border-border rounded-md"
              >
                Skip for Now
              </button>
            </div>

            <p className="text-xs text-muted-foreground text-center mt-4">
              You can always sync later from the Options History section
            </p>
          </>
        )}

        {step === 'syncing' && (
          <>
            <div className="text-center mb-6">
              <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center mx-auto mb-4">
                <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
              </div>
              <h2 className="text-xl font-bold mb-2">Syncing Your Options History</h2>
              <p className="text-muted-foreground">
                We're loading your trading history. This may take a few minutes for accounts with lots of activity.
              </p>
            </div>

            <SyncProgressIndicator
              isVisible={true}
              onComplete={handleSyncComplete}
              className="mb-4"
            />

            <div className="bg-muted/50 rounded-lg p-4">
              <h3 className="font-medium mb-2 text-sm">While you wait:</h3>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• Orders are being processed in chronological order</li>
                <li>• Multi-leg strategies are automatically detected</li>
                <li>• You'll see real-time progress updates above</li>
                <li>• The sync will continue in the background</li>
              </ul>
            </div>
          </>
        )}

        {step === 'completed' && (
          <>
            <div className="text-center mb-6">
              <div className="w-16 h-16 bg-green-100 dark:bg-green-900 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-green-600 dark:text-green-400" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              </div>
              <h2 className="text-xl font-bold mb-2">All Set!</h2>
              <p className="text-muted-foreground">
                Your options history has been successfully synced. You can now explore your trades, 
                analyze strategies, and track performance.
              </p>
            </div>

            <div className="bg-muted/50 rounded-lg p-4 mb-6">
              <h3 className="font-medium mb-2 text-sm">What's Next:</h3>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>• Browse your options orders in the history section</li>
                <li>• Use filters to find specific trades or strategies</li>
                <li>• View detailed multi-leg order breakdowns</li>
                <li>• Orders will auto-sync every 15 minutes</li>
              </ul>
            </div>

            <div className="text-center">
              <div className="inline-flex items-center space-x-2 text-sm text-muted-foreground">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <span>Redirecting to your options history...</span>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}