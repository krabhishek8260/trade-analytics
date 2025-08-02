# Frontend Troubleshooting Guide

This guide covers common issues and their solutions for the Trading Analytics frontend.

## Quick Fixes

### 1. Next.js Chunk Loading Errors (404 errors)

**Symptoms:**
```
GET /_next/static/chunks/main-app.js 404
GET /_next/static/css/app/layout.css 404
```

**Solution:**
```bash
# Quick fix
npm run dev:clean

# Complete reset
./dev-reset.sh
```

### 2. Port Conflicts

**Symptoms:**
```
⚠ Port 3000 is in use, trying 3001 instead.
```

**Solution:**
```bash
# Kill processes on port 3000
lsof -ti:3000 | xargs kill -9

# Or use different port
npm run dev -- -p 3001
```

### 3. Build Cache Issues

**Symptoms:**
- Components not updating
- Stale data
- Compilation errors

**Solution:**
```bash
# Clear all caches
rm -rf .next node_modules/.cache
npm install
npm run dev
```

## Development Scripts

| Script | Description |
|--------|-------------|
| `npm run dev` | Start development server |
| `npm run dev:clean` | Clear cache and restart |
| `npm run dev:fresh` | Complete reset with dependency reinstall |
| `npm run dev:reset` | Reset with Turbo mode |
| `./dev-reset.sh` | Complete environment reset |

## Common Issues

### Module Resolution Errors

**Error:** `Module not found: Can't resolve 'module-name'`

**Solution:**
```bash
rm -rf node_modules package-lock.json
npm install
```

### TypeScript Errors

**Error:** TypeScript compilation errors

**Solution:**
```bash
# Clear TypeScript cache
rm -rf .next tsconfig.tsbuildinfo
npm run dev
```

### Hot Reload Not Working

**Symptoms:** Changes not reflecting in browser

**Solution:**
```bash
# Restart with clean cache
npm run dev:clean

# Or force browser refresh
# Press Ctrl+Shift+R (Cmd+Shift+R on Mac)
```

### Memory Issues

**Symptoms:** Slow performance, high memory usage

**Solution:**
```bash
# Clear all caches and restart
./dev-reset.sh

# Or increase Node.js memory limit
NODE_OPTIONS="--max-old-space-size=4096" npm run dev
```

## Environment Issues

### Environment Variables Not Loading

**Check:** `.env.local` file exists and has correct format

**Solution:**
```bash
# Restart development server
npm run dev:clean

# Verify environment variables
echo $NEXT_PUBLIC_API_URL
```

### API Connection Issues

**Symptoms:** Frontend can't connect to backend

**Solution:**
```bash
# Check backend is running
curl http://localhost:8000/health

# Verify API URL in .env.local
cat .env.local
```

## Performance Issues

### Slow Build Times

**Solution:**
```bash
# Use Turbo mode
npm run dev:reset

# Or increase memory
NODE_OPTIONS="--max-old-space-size=4096" npm run dev
```

### Large Bundle Size

**Solution:**
```bash
# Analyze bundle
npm run build
npx @next/bundle-analyzer
```

## Browser Issues

### CORS Errors

**Symptoms:** API requests failing with CORS errors

**Solution:**
- Check backend CORS configuration
- Verify API URL in environment variables
- Clear browser cache

### Cache Issues

**Symptoms:** Old data showing, components not updating

**Solution:**
```bash
# Hard refresh browser
# Ctrl+Shift+R (Cmd+Shift+R on Mac)

# Or clear browser cache completely
```

## Getting Help

1. **Check logs:** Look at terminal output for error messages
2. **Verify environment:** Ensure all environment variables are set
3. **Try reset:** Use `./dev-reset.sh` for complete reset
4. **Check dependencies:** Ensure all packages are installed
5. **Browser console:** Check browser developer tools for errors

## Emergency Reset

If nothing else works:

```bash
# Complete system reset
cd ..
rm -rf frontend/node_modules frontend/.next frontend/package-lock.json
cd frontend
npm install
npm run dev
```

## Prevention Tips

1. **Regular cleanup:** Use `npm run dev:clean` weekly
2. **Monitor ports:** Check for port conflicts before starting
3. **Update dependencies:** Keep packages up to date
4. **Use scripts:** Prefer the provided scripts over manual commands
5. **Backup config:** Keep copies of working configurations 