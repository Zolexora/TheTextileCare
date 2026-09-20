import './globals.css';
import type { Metadata, Viewport } from 'next';
import { Providers } from '@/components/providers';
import { MarketplaceHeader, BottomNav } from '@/components/navigation';

export const metadata: Metadata = {
  title: {
    default: 'The Textile Care — Laundry & Dry Cleaning Marketplace',
    template: '%s | The Textile Care',
  },
  description:
    'Book professional laundry, dry cleaning, and garment care services from verified sellers near you. Easy pickup and delivery.',
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL ?? 'https://thetextilecare.com'
  ),
  openGraph: {
    type: 'website',
    locale: 'en_IN',
    siteName: 'The Textile Care',
  },
  twitter: { card: 'summary_large_image' },
  robots: { index: true, follow: true },
  icons: {
    icon: [
      { url: '/favicon.ico' },
      { url: '/icon.svg', type: 'image/svg+xml' },
      { url: '/favicon-32x32.png', sizes: '32x32', type: 'image/png' },
      { url: '/favicon-16x16.png', sizes: '16x16', type: 'image/png' },
    ],
    apple: [{ url: '/apple-touch-icon.png', sizes: '180x180' }],
  },
  manifest: '/site.webmanifest',
};

export const viewport: Viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#062B5F' },
    { media: '(prefers-color-scheme: dark)', color: '#0052CC' },
  ],
  width: 'device-width',
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-background antialiased">
        <Providers>
          <div className="flex min-h-screen flex-col">
            <MarketplaceHeader />
            {/* Main content — padded bottom for mobile bottom nav */}
            <main id="main-content" className="flex-1 pb-16 md:pb-0" tabIndex={-1}>
              {children}
            </main>
            <footer className="hidden border-t border-border bg-muted/30 md:block">
              <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
                <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
                  <p className="text-sm text-muted-foreground">
                    © {new Date().getFullYear()} The Textile Care. All rights reserved.
                  </p>
                  <nav className="flex gap-4 text-sm text-muted-foreground" aria-label="Footer">
                    <a href="/about" className="hover:text-foreground transition-colors">About</a>
                    <a href="/help" className="hover:text-foreground transition-colors">Help</a>
                    <a href="/privacy" className="hover:text-foreground transition-colors">Privacy</a>
                    <a href="/terms" className="hover:text-foreground transition-colors">Terms</a>
                  </nav>
                </div>
              </div>
            </footer>
            <BottomNav />
          </div>
        </Providers>
      </body>
    </html>
  );
}
