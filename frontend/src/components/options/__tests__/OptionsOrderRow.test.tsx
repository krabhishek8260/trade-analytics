import { render, screen, fireEvent } from '@/test-utils'
import OptionsOrderRow from '../OptionsOrderRow'
import { mockOptionsOrder, mockMultiLegOrder } from '@/test-utils/mocks'

const mockProps = {
  isExpanded: false,
  onToggle: jest.fn(),
  formatCurrency: (value: number) => `$${value.toFixed(2)}`,
  formatDateTime: (dateStr: string | null) => dateStr ? new Date(dateStr).toLocaleDateString() : 'N/A'
}

describe('OptionsOrderRow', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders single leg order correctly', () => {
    render(
      <OptionsOrderRow
        order={mockOptionsOrder}
        {...mockProps}
      />
    )

    expect(screen.getByText('AAPL')).toBeInTheDocument()
    expect(screen.getByText('FILLED')).toBeInTheDocument()
    expect(screen.getByText('long_call')).toBeInTheDocument()
    expect(screen.getByText(/1.*leg/)).toBeInTheDocument()
    expect(screen.getByText('-$550.00')).toBeInTheDocument()
    expect(screen.getByText('$550.00 per contract')).toBeInTheDocument()
  })

  it('renders multi-leg order correctly', () => {
    render(
      <OptionsOrderRow
        order={mockMultiLegOrder}
        {...mockProps}
      />
    )

    expect(screen.getByText('TSLA')).toBeInTheDocument()
    expect(screen.getByText('call_spread')).toBeInTheDocument()
    expect(screen.getByText(/2.*legs/)).toBeInTheDocument()
  })

  it('toggles expansion when clicked', () => {
    render(
      <OptionsOrderRow
        order={mockOptionsOrder}
        {...mockProps}
      />
    )

    const button = screen.getByRole('button')
    fireEvent.click(button)

    expect(mockProps.onToggle).toHaveBeenCalledTimes(1)
  })

  it('shows expanded state correctly', () => {
    render(
      <OptionsOrderRow
        order={mockOptionsOrder}
        {...mockProps}
        isExpanded={true}
      />
    )

    // When expanded, OptionsOrderLegs component should be rendered
    // We'll verify this by checking if the button has the correct rotation class
    const svg = screen.getByRole('button').querySelector('svg')
    expect(svg).toHaveClass('rotate-180')
  })

  it('displays credit orders with positive styling', () => {
    const creditOrder = {
      ...mockOptionsOrder,
      direction: 'credit' as const,
      processed_premium: 500
    }

    render(
      <OptionsOrderRow
        order={creditOrder}
        {...mockProps}
      />
    )

    const premiumElement = screen.getByText('+$500.00')
    expect(premiumElement).toHaveClass('text-green-600')
  })

  it('displays debit orders with negative styling', () => {
    render(
      <OptionsOrderRow
        order={mockOptionsOrder}
        {...mockProps}
      />
    )

    const premiumElement = screen.getByText('-$550.00')
    expect(premiumElement).toHaveClass('text-red-600')
  })

  it('handles missing symbol gracefully', () => {
    const orderWithoutSymbol = {
      ...mockOptionsOrder,
      chain_symbol: undefined,
      underlying_symbol: undefined
    }

    render(
      <OptionsOrderRow
        order={orderWithoutSymbol}
        {...mockProps}
      />
    )

    // SymbolLogo should handle null/undefined symbols
    expect(screen.getByRole('button')).toBeInTheDocument()
  })

  it('formats dates correctly', () => {
    render(
      <OptionsOrderRow
        order={mockOptionsOrder}
        {...mockProps}
      />
    )

    expect(screen.getByText('1/15/2024')).toBeInTheDocument()
  })

  it('shows option details when available', () => {
    render(
      <OptionsOrderRow
        order={mockOptionsOrder}
        {...mockProps}
      />
    )

    expect(screen.getByText(/150.*CALL/)).toBeInTheDocument()
  })
})