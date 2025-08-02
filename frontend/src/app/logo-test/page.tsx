'use client';

import { useState, useEffect } from 'react';
import { SymbolLogo } from '@/components/ui/SymbolLogo';

export default function LogoTestPage() {
  const [testSymbol, setTestSymbol] = useState('AAPL');
  const [isLoading, setIsLoading] = useState(false);

  const testSymbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA'];

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-4xl mx-auto space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold mb-4">Logo Test Page</h1>
          <p className="text-muted-foreground mb-6">Testing the logo functionality</p>
        </div>

        <div className="bg-muted/50 rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Test Individual Symbol</h2>
          <div className="flex gap-4 items-center">
            <input
              type="text"
              value={testSymbol}
              onChange={(e) => setTestSymbol(e.target.value)}
              placeholder="Enter symbol (e.g., AAPL)"
              className="px-3 py-2 border rounded flex-1"
            />
            <button
              onClick={() => setIsLoading(true)}
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              Test Logo
            </button>
          </div>
          
          <div className="mt-4 p-4 bg-background rounded border">
            <h3 className="font-medium mb-2">Result:</h3>
            <SymbolLogo 
              symbol={testSymbol} 
              size="lg" 
              showText={true}
            />
          </div>
        </div>

        <div className="bg-muted/50 rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Test Multiple Symbols</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {testSymbols.map((symbol) => (
              <div key={symbol} className="p-4 bg-background rounded border">
                <SymbolLogo 
                  symbol={symbol} 
                  size="md" 
                  showText={true}
                />
              </div>
            ))}
          </div>
        </div>

        <div className="bg-muted/50 rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Different Sizes</h2>
          <div className="flex items-center gap-6">
            <div className="text-center">
              <SymbolLogo symbol="AAPL" size="sm" showText={false} />
              <div className="text-xs text-muted-foreground mt-1">Small</div>
            </div>
            <div className="text-center">
              <SymbolLogo symbol="MSFT" size="md" showText={false} />
              <div className="text-xs text-muted-foreground mt-1">Medium</div>
            </div>
            <div className="text-center">
              <SymbolLogo symbol="GOOGL" size="lg" showText={false} />
              <div className="text-xs text-muted-foreground mt-1">Large</div>
            </div>
          </div>
        </div>

        <div className="bg-muted/50 rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">With and Without Text</h2>
          <div className="flex items-center gap-6">
            <div className="text-center">
              <SymbolLogo symbol="META" size="md" showText={true} />
              <div className="text-xs text-muted-foreground mt-1">With Text</div>
            </div>
            <div className="text-center">
              <SymbolLogo symbol="NVDA" size="md" showText={false} />
              <div className="text-xs text-muted-foreground mt-1">Without Text</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 