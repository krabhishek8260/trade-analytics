import { render, screen, fireEvent, waitFor } from '@/test-utils'
import OptionsHistorySection from '../OptionsHistorySection'
import { mockApiCalls, mockPaginatedOrdersResponse } from '@/test-utils/mocks'
import * as api from '@/lib/api'

// Mock the API functions
jest.mock('@/lib/api', () => ({
  ...jest.requireActual('@/lib/api'),
  getOptionsOrders: jest.fn(),
  getOptionsOrdersSyncStatus: jest.fn(),
  triggerOptionsOrdersSync: jest.fn(),
}))

const mockProps = {
  formatCurrency: (value: number) => `$${value.toFixed(2)}`,
  formatPercent: (value: number) => `${(value * 100).toFixed(2)}%`
}

const mockedApi = {
  getOptionsOrders: api.getOptionsOrders as jest.MockedFunction<typeof api.getOptionsOrders>,
  getOptionsOrdersSyncStatus: api.getOptionsOrdersSyncStatus as jest.MockedFunction<typeof api.getOptionsOrdersSyncStatus>,
  triggerOptionsOrdersSync: api.triggerOptionsOrdersSync as jest.MockedFunction<typeof api.triggerOptionsOrdersSync>,
}

describe('OptionsHistorySection', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    mockedApi.getOptionsOrders.mockResolvedValue(mockPaginatedOrdersResponse)
    mockedApi.getOptionsOrdersSyncStatus.mockResolvedValue({
      user_id: 'test-user',
      total_orders: 100,
      last_sync: '2024-01-15T10:00:00Z',
      last_order_date: '2024-01-15T10:30:00Z',
      needs_sync: false,
      sync_reason: 'Up to date',
      sync_status: 'up_to_date'
    })
  })

  it('renders collapsed view by default', async () => {
    render(<OptionsHistorySection {...mockProps} />)

    await waitFor(() => {
      expect(screen.getByText('Options History (2 orders)')).toBeInTheDocument()
    })

    // Should show collapsed preview
    expect(screen.getByText('AAPL')).toBeInTheDocument()
    expect(screen.getByText('TSLA')).toBeInTheDocument()
  })

  it('expands when clicked', async () => {
    render(<OptionsHistorySection {...mockProps} />)

    await waitFor(() => {
      expect(screen.getByText('Options History (2 orders)')).toBeInTheDocument()
    })

    // Click to expand
    fireEvent.click(screen.getByText('Options History (2 orders)'))

    await waitFor(() => {
      // Should show filters
      expect(screen.getByPlaceholderText('Symbol (e.g., AAPL)')).toBeInTheDocument()
      expect(screen.getByDisplayValue('Filled')).toBeInTheDocument()
    })
  })

  it('applies filters correctly', async () => {
    render(<OptionsHistorySection {...mockProps} />)

    await waitFor(() => {
      expect(screen.getByText('Options History (2 orders)')).toBeInTheDocument()
    })

    // Expand section
    fireEvent.click(screen.getByText('Options History (2 orders)'))

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Symbol (e.g., AAPL)')).toBeInTheDocument()
    })

    // Enter symbol filter
    const symbolInput = screen.getByPlaceholderText('Symbol (e.g., AAPL)')
    fireEvent.change(symbolInput, { target: { value: 'AAPL' } })

    await waitFor(() => {
      expect(mockedApi.getOptionsOrders).toHaveBeenCalledWith(
        expect.objectContaining({
          page: 1,
          limit: 20,
          underlying_symbol: 'AAPL',
          state: 'filled',
          sort_by: 'created_at',
          sort_order: 'desc'
        })
      )
    })
  })

  it('handles pagination correctly', async () => {
    const paginatedResponse = {
      ...mockPaginatedOrdersResponse,
      pagination: {
        ...mockPaginatedOrdersResponse.pagination,
        total: 50,
        total_pages: 3,
        has_next: true,
        has_prev: false
      }
    }

    mockedApi.getOptionsOrders.mockResolvedValue(paginatedResponse)

    render(<OptionsHistorySection {...mockProps} />)

    await waitFor(() => {
      expect(screen.getByText('Options History (50 orders)')).toBeInTheDocument()
    })

    // Expand section
    fireEvent.click(screen.getByText('Options History (50 orders)'))

    await waitFor(() => {
      // Should show pagination controls
      expect(screen.getByText('Showing 1 to 20 of 50 orders')).toBeInTheDocument()
      expect(screen.getByText('Page 1 of 3')).toBeInTheDocument()
      expect(screen.getByText('Next')).toBeInTheDocument()
    })

    // Click next page
    fireEvent.click(screen.getByText('Next'))

    await waitFor(() => {
      expect(mockedApi.getOptionsOrders).toHaveBeenCalledWith(
        expect.objectContaining({
          page: 2,
          limit: 20,
          state: 'filled',
          sort_by: 'created_at',
          sort_order: 'desc'
        })
      )
    })
  })

  it('triggers sync when sync button is clicked', async () => {
    mockedApi.triggerOptionsOrdersSync.mockResolvedValue({
      orders_processed: 10,
      orders_stored: 10,
      sync_time: '2024-01-15T11:00:00Z',
      sync_type: 'incremental'
    })

    render(<OptionsHistorySection {...mockProps} />)

    await waitFor(() => {
      expect(screen.getByText('Options History (2 orders)')).toBeInTheDocument()
    })

    // Expand section to see sync buttons
    fireEvent.click(screen.getByText('Options History (2 orders)'))

    await waitFor(() => {
      expect(screen.getByText('Refresh')).toBeInTheDocument()
      expect(screen.getByText('Full Sync')).toBeInTheDocument()
    })

    // Click refresh button
    fireEvent.click(screen.getByText('Refresh'))

    await waitFor(() => {
      expect(mockedApi.triggerOptionsOrdersSync).toHaveBeenCalledWith(false, 30)
    })
  })

  it('handles loading states correctly', async () => {
    // Mock a delayed response
    mockedApi.getOptionsOrders.mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve(mockPaginatedOrdersResponse), 100))
    )

    render(<OptionsHistorySection {...mockProps} />)

    // Should show loading state initially (check for animate-pulse class)
    const loadingElements = document.querySelectorAll('.animate-pulse')
    expect(loadingElements.length).toBeGreaterThan(0)

    await waitFor(() => {
      expect(screen.getByText('Options History (2 orders)')).toBeInTheDocument()
    }, { timeout: 200 })
  })

  it('handles error states correctly', async () => {
    mockedApi.getOptionsOrders.mockRejectedValue(new Error('API Error'))

    render(<OptionsHistorySection {...mockProps} />)

    await waitFor(() => {
      expect(screen.getByText('Error loading options orders')).toBeInTheDocument()
      expect(screen.getByText('API Error')).toBeInTheDocument()
    })
  })

  it('shows empty state when no orders', async () => {
    const emptyResponse = {
      ...mockPaginatedOrdersResponse,
      data: [],
      pagination: {
        ...mockPaginatedOrdersResponse.pagination,
        total: 0
      }
    }

    mockedApi.getOptionsOrders.mockResolvedValue(emptyResponse)
    mockedApi.getOptionsOrdersSyncStatus.mockResolvedValue({
      user_id: 'test-user',
      total_orders: 0,
      last_sync: null,
      last_order_date: null,
      needs_sync: true,
      sync_reason: 'No orders found - full sync needed',
      sync_status: 'sync_needed'
    })

    render(<OptionsHistorySection {...mockProps} />)

    await waitFor(() => {
      expect(screen.getByText('No options orders found.')).toBeInTheDocument()
      expect(screen.getByText('Click "Sync Orders" to load your trading history.')).toBeInTheDocument()
    })
  })
})