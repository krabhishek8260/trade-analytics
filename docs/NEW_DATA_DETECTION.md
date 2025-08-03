# New Data Detection System

## Overview

The Trade Analytics application now includes a smart data detection system that monitors for new data availability without automatically refreshing the page. This provides a better user experience by allowing users to control when they want to see updated information.

## How It Works

### Background Data Checking

Instead of auto-refreshing the entire page, the system:

1. **Periodically checks for new data** in the background (every 30 seconds by default)
2. **Compares data hashes** to detect changes without loading the full UI
3. **Shows visual indicators** when new data is available
4. **Allows manual refresh** when the user is ready to see updates

### Data Change Detection

The system uses a simple hashing mechanism to detect changes:

```typescript
// Example data hash generation
const generateDataHash = (data: DashboardData): string => {
  const dataString = JSON.stringify({
    portfolio: data.portfolio?.total_value,
    stocks: data.stocks?.total_positions,
    options: data.options?.total_positions,
    portfolioReturn: data.portfolio?.total_return,
    stocksReturn: data.stocks?.total_return,
    optionsReturn: data.options?.total_return
  })
  return btoa(dataString).slice(0, 16) // Simple hash for comparison
}
```

## Features

### Visual Indicators

- **Green notification banner**: Appears when new data is detected
- **Animated refresh button**: Shows a pulsing green dot when new data is available
- **Status indicators**: Show when the system is actively checking for new data

### User Controls

- **Enable/Disable**: Toggle new data checking on/off
- **Check intervals**: Configure how often to check (15s, 30s, 1m, 2m, 5m)
- **Manual refresh**: Click to load new data when ready

## Implementation Details

### Dashboard Page

**File**: `frontend/src/app/dashboard/page.tsx`

**Key Components**:
- `hasNewData`: Boolean state indicating new data availability
- `newDataCheckEnabled`: Toggle for enabling/disabling checks
- `checkInterval`: Configurable interval for data checking
- `lastDataHash`: Hash of current data for comparison
- `checkForNewData()`: Function that fetches and compares data
- `handleRefresh()`: Manual refresh function

**Data Monitored**:
- Portfolio total value and returns
- Stock positions count and returns
- Options positions count and returns

### Analysis Tab

**File**: `frontend/src/components/analysis/AnalysisTab.tsx`

**Key Components**:
- `generateAnalysisDataHash()`: Creates hash from analysis data
- `checkForNewAnalysisData()`: Checks for new analysis data
- `handleManualRefresh()`: Refreshes analysis data

**Data Monitored**:
- Historical options orders
- Ticker performance data
- Current positions
- Filtered positions

### P&L Analytics Page

**File**: `frontend/src/app/dashboard/pnl/page.tsx`

**Key Components**:
- `generatePnLDataHash()`: Creates hash from P&L data
- `checkForNewPnLData()`: Checks for new P&L data
- `handleManualRefresh()`: Refreshes P&L data

**Data Monitored**:
- P&L summary totals
- Yearly P&L data
- Symbol-specific P&L data

## User Interface

### Notification Banner

```tsx
{hasNewData && (
  <div className="bg-green-500/10 border border-green-500/20 rounded-md p-3 mb-6 animate-in slide-in-from-top-2">
    <p className="text-green-600 text-sm flex items-center justify-between">
      <span className="flex items-center">
        <span className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></span>
        New data available
      </span>
      <button
        onClick={handleRefresh}
        className="text-xs bg-green-500 text-white px-2 py-1 rounded hover:bg-green-600 transition-colors"
      >
        Refresh Now
      </button>
    </p>
  </div>
)}
```

### Refresh Button with Indicator

```tsx
<button
  onClick={handleRefresh}
  disabled={dataLoading}
  className="px-3 py-1 text-sm bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/80 disabled:opacity-50 relative"
>
  {dataLoading ? 'Refreshing...' : 'Refresh'}
  {hasNewData && (
    <span className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full animate-pulse"></span>
  )}
</button>
```

### Control Panel

```tsx
<div className="flex items-center space-x-2">
  <label className="flex items-center text-xs text-muted-foreground">
    <input
      type="checkbox"
      checked={newDataCheckEnabled}
      onChange={(e) => setNewDataCheckEnabled(e.target.checked)}
      className="mr-1"
    />
    Check for new data
  </label>
  <select
    value={checkInterval / 1000}
    onChange={(e) => setCheckInterval(Number(e.target.value) * 1000)}
    className="text-xs bg-secondary text-secondary-foreground rounded px-2 py-1"
    disabled={!newDataCheckEnabled}
  >
    <option value={15}>15s</option>
    <option value={30}>30s</option>
    <option value={60}>1m</option>
    <option value={120}>2m</option>
    <option value={300}>5m</option>
  </select>
</div>
```

## Configuration

### Default Settings

- **Check interval**: 30 seconds
- **Enabled by default**: Yes
- **Auto-refresh disabled**: Yes (to prevent page reloads)

### User Preferences

Users can customize:
- Enable/disable new data checking
- Set check interval (15s to 5m)
- Choose when to refresh manually

## Benefits

### User Experience

1. **No Disruption**: Page doesn't auto-refresh, maintaining user's current view
2. **User Control**: Users decide when to see new data
3. **Visual Feedback**: Clear indicators when new data is available
4. **Performance**: Efficient background checking without UI updates

### Technical Benefits

1. **Reduced Server Load**: Only checks for changes, doesn't load full UI
2. **Better Performance**: No unnecessary page refreshes
3. **Scalable**: Configurable intervals based on user needs
4. **Reliable**: Simple hash-based change detection

## Troubleshooting

### Common Issues

1. **New data not detected**
   - Check if new data checking is enabled
   - Verify the check interval is appropriate
   - Ensure the data hash generation includes relevant fields

2. **Too frequent notifications**
   - Increase the check interval
   - Review the data hash generation to avoid false positives

3. **Performance issues**
   - Disable new data checking if not needed
   - Increase check interval to reduce API calls

### Debug Information

In development mode, the system logs:
- When data checking occurs
- When new data is detected
- Hash comparisons for debugging

## Future Enhancements

### Potential Improvements

1. **Smart Intervals**: Adjust check frequency based on user activity
2. **Push Notifications**: Browser notifications for new data
3. **Data Prioritization**: Different indicators for different types of data
4. **Offline Support**: Queue data checks when offline
5. **Custom Alerts**: User-defined conditions for data notifications

### API Optimizations

1. **Delta Endpoints**: Backend endpoints that return only changed data
2. **WebSocket Support**: Real-time data updates
3. **Caching**: Intelligent caching of data hashes
4. **Batch Checking**: Combine multiple data checks into single requests

## Migration from Auto-Refresh

### Before (Auto-Refresh)
- Page automatically refreshed every 30 seconds
- User's view and scroll position were lost
- No indication of when new data arrived
- Higher server load from full page refreshes

### After (New Data Detection)
- Background checking without page refresh
- User maintains current view and position
- Clear visual indicators for new data
- Reduced server load with efficient change detection
- User control over when to refresh

This system provides a much better user experience while maintaining data freshness and reducing unnecessary server requests. 