'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'

export default function LoginPage() {
  const [credentials, setCredentials] = useState({
    username: '',
    password: '',
    mfaCode: ''
  })
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [showMfa, setShowMfa] = useState(false)
  const router = useRouter()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')

    try {
      const response = await fetch('/api/backend/auth/robinhood/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: credentials.username,
          password: credentials.password,
          mfa_code: credentials.mfaCode || undefined
        }),
      })

      const data = await response.json()

      if (response.ok && data.success) {
        // Store authentication status and JWT token in localStorage
        localStorage.setItem('robinhood_authenticated', 'true')
        if (data.access_token) {
          localStorage.setItem('auth_token', data.access_token)
        }
        if (data.user_info) {
          localStorage.setItem('user_info', JSON.stringify(data.user_info))
        }
        router.push('/dashboard')
      } else {
        let errorMessage = data.message || 'Login failed'
        
        // Handle specific error cases
        if (errorMessage.includes('connection') || errorMessage.includes('connectivity')) {
          errorMessage = 'Unable to connect to Robinhood API. This could be due to:\n• Network connectivity issues\n• Robinhood API maintenance\n• API rate limiting\n\nPlease try again later.'
        } else if (errorMessage.includes('400')) {
          errorMessage = 'Invalid credentials or authentication issue. Please check your username and password.'
        }
        
        setError(errorMessage)
      }
    } catch (err) {
      setError('Network error connecting to the backend. Please check your internet connection and try again.')
    } finally {
      setIsLoading(false)
    }
  }


  const handleInputChange = (field: string, value: string) => {
    setCredentials(prev => ({ ...prev, [field]: value }))
    setError('')
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="bg-card rounded-lg border p-8 shadow-soft">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold tracking-tight">Connect Robinhood</h1>
            <p className="text-muted-foreground mt-2">
              Enter your Robinhood credentials to access your portfolio
            </p>
          </div>

          {error && (
            <div className="bg-destructive/10 border border-destructive/20 rounded-md p-3 mb-6">
              <p className="text-destructive text-sm">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="username" className="block text-sm font-medium mb-2">
                Username
              </label>
              <input
                id="username"
                type="text"
                required
                value={credentials.username}
                onChange={(e) => handleInputChange('username', e.target.value)}
                className="w-full px-3 py-2 border border-input rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
                placeholder="Enter your Robinhood username"
                disabled={isLoading}
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium mb-2">
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                value={credentials.password}
                onChange={(e) => handleInputChange('password', e.target.value)}
                className="w-full px-3 py-2 border border-input rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
                placeholder="Enter your Robinhood password"
                disabled={isLoading}
              />
            </div>

            {showMfa && (
              <div>
                <label htmlFor="mfaCode" className="block text-sm font-medium mb-2">
                  MFA Code
                </label>
                <input
                  id="mfaCode"
                  type="text"
                  value={credentials.mfaCode}
                  onChange={(e) => handleInputChange('mfaCode', e.target.value)}
                  className="w-full px-3 py-2 border border-input rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent"
                  placeholder="Enter 6-digit MFA code"
                  disabled={isLoading}
                  maxLength={6}
                />
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-primary text-primary-foreground py-2 px-4 rounded-md font-medium hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? 'Waiting for approval - check your Robinhood app for push notification...' : 'Connect Account'}
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-border">
            <div className="text-xs text-muted-foreground space-y-2">
              <p className="flex items-center">
                <span className="w-2 h-2 bg-success rounded-full mr-2"></span>
                Your credentials are encrypted and stored securely
              </p>
              <p className="flex items-center">
                <span className="w-2 h-2 bg-success rounded-full mr-2"></span>
                We use read-only access to your account
              </p>
              <p className="flex items-center">
                <span className="w-2 h-2 bg-success rounded-full mr-2"></span>
                You can disconnect at any time
              </p>
            </div>
            
            {error && error.includes('connect') && (
              <div className="mt-4 p-3 bg-muted rounded-md">
                <p className="text-xs text-muted-foreground mb-2 font-medium">Troubleshooting Tips:</p>
                <ul className="text-xs text-muted-foreground space-y-1">
                  <li>• Ensure you have a stable internet connection</li>
                  <li>• Try again in a few minutes (API may be temporarily down)</li>
                  <li>• Check if Robinhood's website is accessible</li>
                  <li>• Make sure your credentials are correct</li>
                </ul>
              </div>
            )}
          </div>

          <div className="mt-6 text-center">
            <button
              onClick={() => router.push('/dashboard')}
              className="text-sm text-muted-foreground hover:text-foreground underline"
            >
              Skip for now
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}