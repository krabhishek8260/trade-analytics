'use client'

import React from 'react'

interface Props {
  children: React.ReactNode
  fallback?: React.ComponentType<ErrorBoundaryFallbackProps>
}

interface State {
  hasError: boolean
  error?: Error
  errorInfo?: React.ErrorInfo
}

interface ErrorBoundaryFallbackProps {
  error?: Error
  errorInfo?: React.ErrorInfo
  onRetry: () => void
}

const DefaultErrorFallback: React.FC<ErrorBoundaryFallbackProps> = ({ 
  error, 
  onRetry 
}) => (
  <div className="p-8 bg-red-50 dark:bg-red-950/20 rounded-lg border border-red-200 dark:border-red-800">
    <div className="flex items-start space-x-4">
      <div className="flex-shrink-0">
        <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.464 0L4.35 16.5c-.77.833.192 2.5 1.732 2.5z" />
        </svg>
      </div>
      <div className="flex-1">
        <h3 className="text-lg font-medium text-red-800 dark:text-red-200 mb-2">
          Something went wrong with the options history
        </h3>
        <p className="text-sm text-red-700 dark:text-red-300 mb-4">
          {error?.message || 'An unexpected error occurred while loading your options orders.'}
        </p>
        <div className="flex space-x-3">
          <button
            onClick={onRetry}
            className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 text-sm font-medium"
          >
            Try Again
          </button>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 border border-red-300 text-red-700 dark:text-red-300 rounded-md hover:bg-red-50 dark:hover:bg-red-950/30 text-sm"
          >
            Reload Page
          </button>
        </div>
        {process.env.NODE_ENV === 'development' && error && (
          <details className="mt-4">
            <summary className="text-sm text-red-600 cursor-pointer">
              Error Details (Development)
            </summary>
            <pre className="mt-2 text-xs bg-red-100 dark:bg-red-900/20 p-3 rounded overflow-auto">
              {error.stack}
            </pre>
          </details>
        )}
      </div>
    </div>
  </div>
)

class OptionsErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      error
    }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    this.setState({
      error,
      errorInfo
    })

    // Log error to monitoring service in production
    if (process.env.NODE_ENV === 'production') {
      console.error('Options History Error Boundary:', error, errorInfo)
      // Example: logErrorToService(error, errorInfo)
    }
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: undefined, errorInfo: undefined })
  }

  render() {
    if (this.state.hasError) {
      const FallbackComponent = this.props.fallback || DefaultErrorFallback
      
      return (
        <FallbackComponent
          error={this.state.error}
          errorInfo={this.state.errorInfo}
          onRetry={this.handleRetry}
        />
      )
    }

    return this.props.children
  }
}

export default OptionsErrorBoundary