# New Data Detection - Quick Reference

## Implementation Checklist

### 1. Add State Variables

```typescript
// New data detection state
const [hasNewData, setHasNewData] = useState(false)
const [newDataCheckEnabled, setNewDataCheckEnabled] = useState(true)
const [checkInterval, setCheckInterval] = useState(30000) // 30 seconds default
const [lastDataHash, setLastDataHash] = useState<string>('')
```

### 2. Create Data Hash Function

```typescript
const generateDataHash = (data: YourDataType): string => {
  const dataString = JSON.stringify({
    // Include key metrics that would change when new data arrives
    keyMetric1: data.metric1,
    keyMetric2: data.metric2,
    count: data.items?.length || 0,
    totalValue: data.total || 0
  })
  return btoa(dataString).slice(0, 16) // Simple hash for comparison
}
```

### 3. Add Check Function

```typescript
const checkForNewData = async () => {
  if (!newDataCheckEnabled || loading) return

  try {
    // Fetch minimal data for comparison
    const newData = await fetchData()
    const newDataHash = generateDataHash(newData)
    
    if (lastDataHash && newDataHash !== lastDataHash) {
      console.log('New data detected!')
      setHasNewData(true)
    }
  } catch (error) {
    console.error('Failed to check for new data:', error)
  }
}
```

### 4. Add useEffect for Background Checking

```typescript
useEffect(() => {
  if (!newDataCheckEnabled || loading) return

  const interval = setInterval(() => {
    console.log('Checking for new data...')
    checkForNewData()
  }, checkInterval)

  return () => clearInterval(interval)
}, [newDataCheckEnabled, checkInterval, loading, lastDataHash])
```

### 5. Update Data Loading Function

```typescript
const loadData = async () => {
  try {
    setLoading(true)
    const data = await fetchData()
    setData(data)
    
    // Update data hash for change detection
    const dataHash = generateDataHash(data)
    setLastDataHash(dataHash)
  } catch (error) {
    console.error('Error loading data:', error)
  } finally {
    setLoading(false)
  }
}
```

### 6. Add Manual Refresh Function

```typescript
const handleManualRefresh = () => {
  setHasNewData(false) // Clear new data indicator
  loadData()
}
```

### 7. Add UI Components

#### Notification Banner
```tsx
{hasNewData && (
  <div className="bg-green-500/10 border border-green-500/20 rounded-md p-3 mb-6 animate-in slide-in-from-top-2">
    <p className="text-green-600 text-sm flex items-center justify-between">
      <span className="flex items-center">
        <span className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></span>
        New data available
      </span>
      <button
        onClick={handleManualRefresh}
        className="text-xs bg-green-500 text-white px-2 py-1 rounded hover:bg-green-600 transition-colors"
      >
        Refresh Now
      </button>
    </p>
  </div>
)}
```

#### Refresh Button with Indicator
```tsx
<button
  onClick={handleManualRefresh}
  disabled={loading}
  className="px-3 py-1 text-sm bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/80 disabled:opacity-50 relative"
>
  {loading ? 'Refreshing...' : 'Refresh'}
  {hasNewData && (
    <span className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full animate-pulse"></span>
  )}
</button>
```

#### Control Panel
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

## Common Patterns

### For Lists/Arrays
```typescript
const generateDataHash = (data: Item[]) => {
  const dataString = JSON.stringify({
    count: data.length,
    totalValue: data.reduce((sum, item) => sum + (item.value || 0), 0),
    lastUpdated: data[0]?.updated_at || null
  })
  return btoa(dataString).slice(0, 16)
}
```

### For Summary Data
```typescript
const generateDataHash = (data: SummaryData) => {
  const dataString = JSON.stringify({
    totalValue: data.total_value,
    totalCount: data.total_count,
    lastUpdated: data.last_updated
  })
  return btoa(dataString).slice(0, 16)
}
```

### For Complex Objects
```typescript
const generateDataHash = (data: ComplexData) => {
  const dataString = JSON.stringify({
    // Pick key fields that indicate changes
    primary: data.primary_metric,
    secondary: data.secondary_metric,
    count: data.items?.length || 0,
    // Hash of important nested data
    nested: btoa(JSON.stringify(data.important_nested_data)).slice(0, 8)
  })
  return btoa(dataString).slice(0, 16)
}
```

## Testing

### Test Data Change Detection
```typescript
// Mock data
const originalData = { value: 100, count: 5 }
const updatedData = { value: 150, count: 6 }

const originalHash = generateDataHash(originalData)
const updatedHash = generateDataHash(updatedData)

console.log('Hashes different:', originalHash !== updatedHash) // Should be true
```

### Test Background Checking
```typescript
// Mock the check function
const mockCheckForNewData = jest.fn()
const mockSetHasNewData = jest.fn()

// Simulate new data detection
mockCheckForNewData.mockImplementation(() => {
  mockSetHasNewData(true)
})

// Verify it was called
expect(mockSetHasNewData).toHaveBeenCalledWith(true)
```

## Troubleshooting

### Data Not Detected
- Check if `newDataCheckEnabled` is true
- Verify `checkInterval` is appropriate
- Ensure hash function includes relevant fields
- Check console for errors in `checkForNewData`

### Too Many Notifications
- Increase `checkInterval`
- Review hash function for false positives
- Add debouncing if needed

### Performance Issues
- Disable checking when not needed
- Increase check interval
- Optimize hash function to include fewer fields

## Best Practices

1. **Include Key Metrics**: Hash should include fields that indicate meaningful changes
2. **Avoid Sensitive Data**: Don't include personal or sensitive information in hashes
3. **Handle Errors Gracefully**: Always catch errors in check functions
4. **Clear Indicators**: Always clear `hasNewData` when manually refreshing
5. **Logging**: Add console logs for debugging in development
6. **User Control**: Always allow users to disable checking
7. **Performance**: Keep hash functions simple and fast 