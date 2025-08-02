#!/bin/bash

echo "🧹 Cleaning up Next.js development environment..."

# Kill any running Next.js processes
echo "📴 Stopping any running Next.js processes..."
pkill -f "next dev" 2>/dev/null || true

# Clean up cache directories
echo "🗑️  Removing cache directories..."
rm -rf .next
rm -rf node_modules/.cache
rm -rf .turbo

# Reinstall dependencies if needed
echo "📦 Reinstalling dependencies..."
npm install

# Start fresh development server
echo "🚀 Starting fresh development server..."
npm run dev 