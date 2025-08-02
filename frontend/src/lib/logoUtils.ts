// Logo fetching utility with static assets and fallback strategies

interface LogoCache {
  [symbol: string]: {
    url: string;
    timestamp: number;
  };
}

const LOGO_CACHE_KEY = 'stock_logos_cache';
const CACHE_DURATION = 24 * 60 * 60 * 1000; // 24 hours

// List of available static logos
const AVAILABLE_LOGOS = [
  // Original logos
  'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'NFLX', 'AMD', 'INTC', 'SPY', 'QQQ',
  
  // Major companies
  'BRK-B', 'UNH', 'JPM', 'V', 'PG', 'MA', 'JNJ', 'WMT', 'HD', 'BAC', 'KO', 'PFE', 'VZ', 'T', 'DIS',
  
  // Tech companies
  'CRM', 'ORCL', 'CSCO', 'ADBE', 'PYPL', 'UBER', 'LYFT', 'ZM', 'SHOP', 'SPOT', 'PINS', 'SNAP', 'TWTR', 'SQSP', 'DDOG',
  
  // ETFs
  'IWM', 'VTI', 'EEM', 'IEFA', 'VEA', 'AGG', 'BND', 'TLT', 'LQD',
  
  // Modern tech companies
  'PLTR', 'COIN', 'HOOD', 'ABNB', 'DASH', 'RBLX', 'AFRM', 'SQ',
  
  // Portfolio symbols - Stock positions
  'GOOG', 'NVDL', 'SOFI', 'TSLL', 'MU', 'RKLB', 'MSTY', 'BMNR',
  
  // Portfolio symbols - Options positions
  'CRWV', 'AMZU', 'ASTS', 'BITX', 'QUBT', 'NBIS', 'SMCI', 'GRAB'
];

// Get cached logos
const getCachedLogos = (): LogoCache => {
  if (typeof window === 'undefined') return {};
  
  try {
    const cached = localStorage.getItem(LOGO_CACHE_KEY);
    if (cached) {
      const parsed = JSON.parse(cached);
      // Clean expired entries
      const now = Date.now();
      const validEntries = Object.entries(parsed).filter(
        ([_, data]: [string, any]) => now - data.timestamp < CACHE_DURATION
      );
      return Object.fromEntries(validEntries);
    }
  } catch (error) {
    console.warn('Failed to load logo cache:', error);
  }
  return {};
};

// Save logo to cache
const saveLogoToCache = (symbol: string, url: string) => {
  if (typeof window === 'undefined') return;
  
  try {
    const cache = getCachedLogos();
    cache[symbol] = {
      url,
      timestamp: Date.now()
    };
    localStorage.setItem(LOGO_CACHE_KEY, JSON.stringify(cache));
  } catch (error) {
    console.warn('Failed to save logo to cache:', error);
  }
};

// Get static logo URL with cache busting
const getStaticLogoUrl = (symbol: string): string => {
  const cleanSymbol = symbol.toUpperCase().replace(/[^A-Z]/g, '');
  // Add cache busting parameter to prevent browser caching issues
  const timestamp = Date.now();
  return `/logos/${cleanSymbol}.png?v=${timestamp}`;
};

// Fetch logo URL for a symbol
export const fetchLogoUrl = async (symbol: string): Promise<string | null> => {
  if (!symbol) return null;
  
  console.log('fetchLogoUrl called with symbol:', symbol);
  
  const cleanSymbol = symbol.toUpperCase().replace(/[^A-Z]/g, '');
  
  // Check if we have a static logo for this symbol
  if (AVAILABLE_LOGOS.includes(cleanSymbol)) {
    const logoUrl = getStaticLogoUrl(cleanSymbol);
    console.log(`Static logo available for ${cleanSymbol}:`, logoUrl);
    
    // Always return fresh URL with cache busting, don't use cache for now
    return logoUrl;
  }
  
  console.log(`No static logo available for ${cleanSymbol}, using fallback`);
  // If no logo found, return null
  return null;
};

// Clear logo cache
export const clearLogoCache = () => {
  if (typeof window === 'undefined') return;
  
  try {
    localStorage.removeItem(LOGO_CACHE_KEY);
    console.log('Logo cache cleared');
  } catch (error) {
    console.warn('Failed to clear logo cache:', error);
  }
};

// Force refresh logo (clear cache and return fresh URL)
export const forceRefreshLogo = (symbol: string): string | null => {
  if (!symbol) return null;
  
  const cleanSymbol = symbol.toUpperCase().replace(/[^A-Z]/g, '');
  
  // Remove from cache if exists
  if (typeof window !== 'undefined') {
    try {
      const cache = getCachedLogos();
      delete cache[cleanSymbol];
      localStorage.setItem(LOGO_CACHE_KEY, JSON.stringify(cache));
    } catch (error) {
      console.warn('Failed to remove logo from cache:', error);
    }
  }
  
  // Check if we have a static logo for this symbol
  if (AVAILABLE_LOGOS.includes(cleanSymbol)) {
    const logoUrl = getStaticLogoUrl(cleanSymbol);
    console.log(`Force refreshed logo for ${cleanSymbol}:`, logoUrl);
    return logoUrl;
  }
  
  return null;
};

// Get cache stats
export const getLogoCacheStats = () => {
  const cache = getCachedLogos();
  return {
    totalEntries: Object.keys(cache).length,
    symbols: Object.keys(cache),
    availableLogos: AVAILABLE_LOGOS
  };
};

// Get list of available logos
export const getAvailableLogos = () => {
  return AVAILABLE_LOGOS;
}; 