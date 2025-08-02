'use client'

import { Component, ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error?: Error
}

export class ChunkErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): State {
    // Update state so the next render will show the fallback UI
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: any) {
    // Log the error
    console.error('Chunk loading error:', error, errorInfo)
    
    // Check if it's a chunk loading error
    if (error.message.includes('Loading chunk') || error.message.includes('_next/static/chunks')) {
      // Force a page reload to fix chunk loading issues
      setTimeout(() => {
        window.location.reload()
      }, 1000)
    }
  }

  render() {
    if (this.state.hasError) {
      // You can render any custom fallback UI
      return this.props.fallback || (
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
            <h2 className="text-xl font-semibold mb-4">Loading Error</h2>
            <p className="text-muted-foreground mb-4">
              There was an issue loading the application. Reloading...
            </p>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90"
            >
              Reload Now
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
} 