/**
 * Middleware — tenant/domain resolution + auth header forwarding.
 *
 * Runs on Edge for all requests. Resolves:
 *  1. Custom seller domain → seller context
 *  2. Seller subdomain → seller context
 *  3. Marketplace root domain → default context
 *
 * Injects resolved tenant headers for server components and API routes.
 *
 * ponytail: full runtime domain resolution wired here when tenant API is ready.
 *           Currently passes through with default context.
 */

import { NextRequest, NextResponse } from 'next/server';

export const config = {
  matcher: [
    /*
     * Match all request paths except static files, API routes from Next itself,
     * and Next internal paths.
     */
    '/((?!_next/static|_next/image|favicon|icon|apple-touch|android-chrome|robots|sitemap|site.webmanifest).*)',
  ],
};

function resolveTenantFromHost(host: string): {
  tenantId: string | null;
  sellerSlug: string | null;
  domain: string;
} {
  // Production tenant resolution — extends here when TenantResolver API is available
  // ponytail: replace with real tenant API call when @ttc/tenant resolver is wired

  const marketplace = process.env.NEXT_PUBLIC_MARKETPLACE_DOMAIN ?? 'thetextilecare.com';

  // Seller subdomain: {slug}.thetextilecare.com
  const subdomainMatch = host.match(/^([a-z0-9-]+)\.(thetextilecare\.com|localhost)$/i);
  if (subdomainMatch && subdomainMatch[1] !== 'www' && subdomainMatch[1] !== 'marketplace') {
    return {
      tenantId: null,
      sellerSlug: subdomainMatch[1] ?? null,
      domain: host,
    };
  }

  // Custom seller domain — look up from env or future API
  // For now: fall through to default

  return { tenantId: null, sellerSlug: null, domain: host };
}

export default function middleware(request: NextRequest) {
  const host = request.headers.get('host') ?? 'localhost:3001';
  const { tenantId, sellerSlug } = resolveTenantFromHost(host);

  const response = NextResponse.next();

  // Forward resolved tenant context as headers for server components
  if (tenantId) response.headers.set('x-ttc-tenant-id', tenantId);
  if (sellerSlug) response.headers.set('x-ttc-seller-slug', sellerSlug);

  // Security headers
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('X-Frame-Options', 'SAMEORIGIN');
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  response.headers.set(
    'Permissions-Policy',
    'camera=(), microphone=(), geolocation=(self)'
  );

  return response;
}
