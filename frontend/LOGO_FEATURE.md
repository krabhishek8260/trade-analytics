# Stock Logo Feature

This feature adds stock logos to the frontend wherever stock symbols are displayed, enhancing the visual appeal and user experience of the trading analytics dashboard.

## Features

- **Automatic Logo Fetching**: Logos are automatically fetched from multiple sources for better coverage
- **Caching**: Logos are cached in localStorage for 24 hours to improve performance
- **Fallback Support**: If no logo is found, a colored circle with the first letter is displayed
- **Multiple Sizes**: Support for small, medium, and large logo sizes
- **Flexible Display**: Option to show logos with or without text

## Components Updated

The following components now display stock logos alongside symbol text:

1. **SymbolPnLTable** - P&L table showing symbol performance
2. **TradingHistorySection** - Trading history with order details
3. **Dashboard** - Top performing symbols section
4. **RolledOptionsSection** - Rolled options chains
5. **FilteredPositionsSection** - Filtered current positions
6. **BreakdownModal** - Portfolio breakdown details
7. **BreakdownComponents** - Breakdown component details

## Usage

### Basic Usage

```tsx
import { SymbolLogo } from '@/components/ui/SymbolLogo'

// Display logo with text
<SymbolLogo symbol="AAPL" size="md" showText={true} />

// Display logo only
<SymbolLogo symbol="AAPL" size="sm" showText={false} />
```

### Props

- `symbol` (string): The stock symbol (e.g., "AAPL", "MSFT")
- `size` ('sm' | 'md' | 'lg'): Logo size - defaults to 'md'
- `showText` (boolean): Whether to display the symbol text - defaults to true
- `className` (string): Additional CSS classes
- `fallbackText` (string): Text to display if symbol is empty

## Logo Sources

The system tries multiple logo sources in order:

1. **Finnhub** - Free tier available for stock logos
2. **Clearbit** - Company logos (works for many companies)
3. **Twelve Data** - Free tier available for stock logos
4. **IEX Cloud** - Free tier available for stock logos

## Caching

Logos are cached in localStorage with the following characteristics:

- **Cache Key**: `stock_logos_cache`
- **Duration**: 24 hours
- **Automatic Cleanup**: Expired entries are automatically removed

### Cache Management

```tsx
import { clearLogoCache, getLogoCacheStats } from '@/lib/logoUtils'

// Clear all cached logos
clearLogoCache()

// Get cache statistics
const stats = getLogoCacheStats()
console.log(stats.totalEntries) // Number of cached logos
console.log(stats.symbols) // Array of cached symbols
```

## Testing

A test page is available at `/test-logos` to verify the logo functionality:

- Test custom symbols
- View cache statistics
- Test different sizes and configurations
- Clear cache and refresh stats

## Performance Considerations

- Logos are loaded asynchronously to avoid blocking the UI
- Failed logo loads are handled gracefully with fallback display
- Caching reduces repeated API calls
- Multiple sources ensure better coverage

## Fallback Display

When no logo is available, a colored circle with the first letter of the symbol is displayed:

- Blue background with white text
- Matches the size of the requested logo
- Maintains consistent layout

## Browser Compatibility

- Requires localStorage support for caching
- Gracefully degrades if localStorage is not available
- Works with all modern browsers

## Future Enhancements

Potential improvements for the future:

1. **Server-side caching** - Cache logos on the backend
2. **Higher resolution logos** - Support for retina displays
3. **Custom logo uploads** - Allow users to upload custom logos
4. **Logo preferences** - Let users choose preferred logo sources
5. **Batch loading** - Load multiple logos simultaneously 