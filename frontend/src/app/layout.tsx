import type { Metadata, Viewport } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { QueryProvider } from '@/lib/providers/query-provider'
import { SupabaseProvider } from '@/lib/providers/supabase-provider'
import { ThemeProvider } from '@/lib/providers/theme-provider'
import { Toaster } from 'react-hot-toast'
import { ChunkErrorBoundary } from '@/components/ChunkErrorBoundary'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Trading Analytics v2',
  description: 'Modern trading analytics platform with real-time portfolio tracking and options analysis',
  keywords: ['trading', 'analytics', 'options', 'portfolio', 'robinhood'],
  authors: [{ name: 'Trading Analytics Team' }],
}

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: '#000000',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.className} antialiased`}>
        <ThemeProvider
          attribute="class"
          defaultTheme="dark"
          enableSystem
          disableTransitionOnChange
        >
          <SupabaseProvider>
            <QueryProvider>
              <ChunkErrorBoundary>
                <div className="min-h-screen bg-background">
                  {children}
                  <Toaster
                    position="top-right"
                    toastOptions={{
                      duration: 4000,
                      className: 'text-sm',
                      style: {
                        background: 'hsl(var(--card))',
                        color: 'hsl(var(--card-foreground))',
                        border: '1px solid hsl(var(--border))',
                      },
                    }}
                  />
                </div>
              </ChunkErrorBoundary>
            </QueryProvider>
          </SupabaseProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}