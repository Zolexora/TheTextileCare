'use client';

import React, { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Search, X, Clock, TrendingUp } from 'lucide-react';
import { Input, Button, EmptyState } from '@/components/ui';
import { SellerCard, ServiceCard, SellerCardSkeleton } from '@/components/marketplace';
import { useSellers, useServices } from '@/lib/queries';
import { useLocationStore } from '@/lib/stores';
import { cn } from '@/lib/utils';

const RECENT_SEARCHES_KEY = 'ttc-recent-searches';

function getRecentSearches(): string[] {
  if (typeof window === 'undefined') return [];
  try {
    return JSON.parse(localStorage.getItem(RECENT_SEARCHES_KEY) ?? '[]') as string[];
  } catch { return []; }
}

function saveRecentSearch(q: string) {
  const prev = getRecentSearches().filter((s) => s !== q);
  localStorage.setItem(RECENT_SEARCHES_KEY, JSON.stringify([q, ...prev].slice(0, 10)));
}

// Tab type
type SearchTab = 'all' | 'sellers' | 'services';

export default function SearchPage() {
  const router = useRouter();
  const params = useSearchParams();
  const initialQ = params.get('q') ?? '';

  const [query, setQuery] = useState(initialQ);
  const [committed, setCommitted] = useState(initialQ);
  const [tab, setTab] = useState<SearchTab>('all');
  const [recentSearches, setRecentSearches] = useState<string[]>([]);

  const { pincode, coords } = useLocationStore();

  useEffect(() => {
    setRecentSearches(getRecentSearches());
  }, []);

  const handleSearch = (q: string) => {
    if (!q.trim()) return;
    saveRecentSearch(q.trim());
    setCommitted(q.trim());
    setRecentSearches(getRecentSearches());
    router.replace(`/search?q=${encodeURIComponent(q.trim())}`, { scroll: false });
  };

  // Sellers query
  const { data: sellerData, isLoading: sellersLoading } = useSellers(
    committed
      ? {
          pincode: pincode ?? undefined,
          latitude: coords?.latitude,
          longitude: coords?.longitude,
        }
      : {}
  );

  // Services query — filter client-side by name when no backend search param
  const { data: services, isLoading: servicesLoading } = useServices({});

  const filteredSellers = (sellerData?.sellers ?? []).filter(
    (s) =>
      !committed ||
      s.business_name.toLowerCase().includes(committed.toLowerCase()) ||
      (s.display_name ?? '').toLowerCase().includes(committed.toLowerCase())
  );

  const filteredServices = (services ?? []).filter(
    (s) =>
      !committed ||
      s.name.toLowerCase().includes(committed.toLowerCase()) ||
      (s.description ?? '').toLowerCase().includes(committed.toLowerCase())
  );

  const isLoading = sellersLoading || servicesLoading;
  const hasResults = filteredSellers.length > 0 || filteredServices.length > 0;

  const TABS: { key: SearchTab; label: string; count: number }[] = [
    { key: 'all',      label: 'All',      count: filteredSellers.length + filteredServices.length },
    { key: 'sellers',  label: 'Sellers',  count: filteredSellers.length },
    { key: 'services', label: 'Services', count: filteredServices.length },
  ];

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      {/* Search input */}
      <div className="relative mb-6">
        <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground" aria-hidden />
        <Input
          type="search"
          placeholder="Search laundry, dry cleaning, sellers…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch(query)}
          className="pl-10 pr-10 py-3 text-base"
          aria-label="Search"
          autoFocus
        />
        {query && (
          <button
            onClick={() => { setQuery(''); setCommitted(''); }}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            aria-label="Clear search"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Recent / popular — shown before any search */}
      {!committed && (
        <div className="space-y-6">
          {recentSearches.length > 0 && (
            <div>
              <div className="mb-3 flex items-center gap-2">
                <Clock className="h-4 w-4 text-muted-foreground" aria-hidden />
                <h2 className="text-sm font-semibold text-foreground">Recent Searches</h2>
              </div>
              <ul className="flex flex-wrap gap-2">
                {recentSearches.map((s) => (
                  <li key={s}>
                    <button
                      onClick={() => { setQuery(s); handleSearch(s); }}
                      className="rounded-full border border-border px-3 py-1.5 text-sm text-foreground hover:bg-muted transition-colors"
                    >
                      {s}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <div>
            <div className="mb-3 flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-muted-foreground" aria-hidden />
              <h2 className="text-sm font-semibold text-foreground">Popular Services</h2>
            </div>
            <ul className="flex flex-wrap gap-2">
              {['Wash & Fold', 'Dry Cleaning', 'Steam Iron', 'Curtains', 'Woollens'].map((s) => (
                <li key={s}>
                  <button
                    onClick={() => { setQuery(s); handleSearch(s); }}
                    className="rounded-full bg-muted px-3 py-1.5 text-sm text-foreground hover:bg-muted/70 transition-colors"
                  >
                    {s}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Results */}
      {committed && (
        <>
          {/* Tabs */}
          <div className="mb-4 flex gap-1 overflow-x-auto border-b border-border" role="tablist">
            {TABS.map(({ key, label, count }) => (
              <button
                key={key}
                role="tab"
                aria-selected={tab === key}
                onClick={() => setTab(key)}
                className={cn(
                  'flex items-center gap-1.5 whitespace-nowrap border-b-2 px-4 py-2 text-sm font-medium transition-colors',
                  tab === key
                    ? 'border-primary text-primary'
                    : 'border-transparent text-muted-foreground hover:text-foreground'
                )}
              >
                {label}
                {!isLoading && (
                  <span className="rounded-full bg-muted px-1.5 py-0.5 text-xs">{count}</span>
                )}
              </button>
            ))}
          </div>

          {isLoading ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 6 }, (_, i) => <SellerCardSkeleton key={i} />)}
            </div>
          ) : !hasResults ? (
            <EmptyState
              title={`No results for "${committed}"`}
              description="Try different keywords or browse all services."
              action={
                <Button variant="outline" onClick={() => { setQuery(''); setCommitted(''); }}>
                  Clear search
                </Button>
              }
            />
          ) : (
            <div className="space-y-8">
              {(tab === 'all' || tab === 'sellers') && filteredSellers.length > 0 && (
                <section aria-labelledby="sellers-results">
                  <h2 id="sellers-results" className="mb-3 text-base font-semibold text-foreground">
                    Sellers ({filteredSellers.length})
                  </h2>
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {filteredSellers.map((s) => (
                      <SellerCard
                        key={s.id}
                        seller={{ id: s.id, business_name: s.business_name, display_name: s.display_name, logo_url: s.logo_url }}
                        onSelect={(id) => router.push(`/sellers/${id}`)}
                      />
                    ))}
                  </div>
                </section>
              )}

              {(tab === 'all' || tab === 'services') && filteredServices.length > 0 && (
                <section aria-labelledby="services-results">
                  <h2 id="services-results" className="mb-3 text-base font-semibold text-foreground">
                    Services ({filteredServices.length})
                  </h2>
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                    {filteredServices.map((s) => (
                      <ServiceCard
                        key={s.id}
                        service={{ id: s.id, name: s.name, description: s.description, image_url: s.image_url }}
                        onSelect={(id) => router.push(`/services/${id}`)}
                      />
                    ))}
                  </div>
                </section>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
