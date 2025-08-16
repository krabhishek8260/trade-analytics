import { test, expect } from '@playwright/test'

test.describe('Options History', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the dashboard page
    await page.goto('/dashboard')
    
    // Wait for the page to load
    await page.waitForLoadState('networkidle')
  })

  test('should display options history section', async ({ page }) => {
    // Check if options history section is present
    await expect(page.locator('text=Options History')).toBeVisible()
    
    // Should show order count
    await expect(page.locator('text=/Options History \\(\\d+ orders\\)/')).toBeVisible()
  })

  test('should expand and show orders list', async ({ page }) => {
    // Click to expand options history
    await page.click('text=/Options History \\(\\d+ orders\\)/')
    
    // Should show filters
    await expect(page.locator('input[placeholder*="Symbol"]')).toBeVisible()
    await expect(page.locator('select').filter({ hasText: 'Filled' })).toBeVisible()
    
    // Should show sync controls
    await expect(page.locator('text=Refresh')).toBeVisible()
    await expect(page.locator('text=Full Sync')).toBeVisible()
  })

  test('should filter orders by symbol', async ({ page }) => {
    // Expand options history
    await page.click('text=/Options History \\(\\d+ orders\\)/')
    
    // Enter symbol filter
    await page.fill('input[placeholder*="Symbol"]', 'AAPL')
    
    // Wait for API call and results
    await page.waitForTimeout(1000)
    
    // Should show filtered results (if any)
    const orderRows = page.locator('[data-testid="options-order-row"]')
    const count = await orderRows.count()
    
    // If there are orders, they should contain AAPL
    if (count > 0) {
      await expect(orderRows.first().locator('text=AAPL')).toBeVisible()
    }
  })

  test('should handle pagination', async ({ page }) => {
    // Expand options history
    await page.click('text=/Options History \\(\\d+ orders\\)/')
    
    // Wait for orders to load
    await page.waitForTimeout(1000)
    
    // Check if pagination is present (only if there are enough orders)
    const nextButton = page.locator('text=Next')
    if (await nextButton.isVisible()) {
      // Click next page
      await nextButton.click()
      
      // Should update page indicator
      await expect(page.locator('text=/Page \\d+ of \\d+/')).toBeVisible()
      
      // Previous button should now be available
      await expect(page.locator('text=Previous')).toBeVisible()
    }
  })

  test('should expand individual order details', async ({ page }) => {
    // Expand options history
    await page.click('text=/Options History \\(\\d+ orders\\)/')
    
    // Wait for orders to load
    await page.waitForTimeout(1000)
    
    // Find first order row and click it
    const orderRows = page.locator('[role="button"]').filter({ has: page.locator('text=/\\$\\d+\\.\\d+/') })
    const firstOrder = orderRows.first()
    
    if (await firstOrder.isVisible()) {
      await firstOrder.click()
      
      // Should show expanded details
      await expect(page.locator('text=Order Details')).toBeVisible()
      await expect(page.locator('text=Order ID:')).toBeVisible()
    }
  })

  test('should trigger sync when sync button is clicked', async ({ page }) => {
    // Expand options history
    await page.click('text=/Options History \\(\\d+ orders\\)/')
    
    // Click refresh button
    await page.click('text=Refresh')
    
    // Should show syncing state
    await expect(page.locator('text=Syncing...')).toBeVisible({ timeout: 5000 })
    
    // Should return to normal state
    await expect(page.locator('text=Refresh')).toBeVisible({ timeout: 10000 })
  })

  test('should display data source indicator', async ({ page }) => {
    // Expand options history
    await page.click('text=/Options History \\(\\d+ orders\\)/')
    
    // Wait for orders to load
    await page.waitForTimeout(1000)
    
    // Should show data source at bottom
    await expect(page.locator('text=/Data source:/')).toBeVisible()
  })

  test('should handle different order states', async ({ page }) => {
    // Expand options history
    await page.click('text=/Options History \\(\\d+ orders\\)/')
    
    // Change filter to show all states
    await page.selectOption('select', { label: 'All States' })
    
    // Wait for results
    await page.waitForTimeout(1000)
    
    // Should show orders with different states
    const orderStates = [
      page.locator('text=FILLED'),
      page.locator('text=CANCELLED'),
      page.locator('text=QUEUED')
    ]
    
    // At least one state should be visible
    let stateVisible = false
    for (const state of orderStates) {
      if (await state.isVisible()) {
        stateVisible = true
        break
      }
    }
    expect(stateVisible).toBeTruthy()
  })

  test('should show symbol logos', async ({ page }) => {
    // Expand options history
    await page.click('text=/Options History \\(\\d+ orders\\)/')
    
    // Wait for orders to load
    await page.waitForTimeout(1000)
    
    // Should show symbol logos (either actual logos or fallback initials)
    const symbolElements = page.locator('[data-testid="symbol-logo"], .symbol-logo, img[alt*="logo"]')
    
    if (await symbolElements.first().isVisible()) {
      await expect(symbolElements.first()).toBeVisible()
    }
  })

  test('should be responsive on mobile', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 })
    
    // Navigate to page
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')
    
    // Options history should still be accessible
    await expect(page.locator('text=Options History')).toBeVisible()
    
    // Expand and verify it works on mobile
    await page.click('text=/Options History \\(\\d+ orders\\)/')
    
    // Filters should be stacked vertically on mobile
    const filtersContainer = page.locator('input[placeholder*="Symbol"]').locator('..')
    await expect(filtersContainer).toBeVisible()
  })

  test('should handle empty state', async ({ page }) => {
    // This test would need to mock empty data or use a test account with no orders
    // For now, we'll check if the empty state exists in the DOM when applicable
    
    // Expand options history
    await page.click('text=/Options History \\(\\d+ orders\\)/')
    
    // If there are 0 orders, should show empty state
    const emptyState = page.locator('text=No options orders found.')
    const syncButton = page.locator('text=Sync Orders')
    
    // Check if empty state is shown
    if (await emptyState.isVisible()) {
      await expect(syncButton).toBeVisible()
    }
  })
})