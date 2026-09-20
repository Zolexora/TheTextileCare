'use client';

import React from 'react';
import Link from 'next/link';
import { MapPin, Search, Star, ArrowRight, ShoppingBag, Clock, Shield } from 'lucide-react';
import { Button, Card, CardContent, Skeleton } from '@/components/ui';
import { SellerCard, SellerCardSkeleton } from '@/components/marketplace';
import { useLocationStore } from '@/lib/stores';
import { useSellers, useCategories } from '@/lib/queries';

// ---------------------------------------------------------------------------
// Hero section
// ---------------------------------------------------------------------------

function HeroSection() {
  const { isSet, city } = useLocationStore();

  return (
    <section
      className="relative bg-gradient-to-br from-primary to-brand-700 py-16 text-white sm:py-20"
      aria-labelledby="hero-heading"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-accent">
            THE TEXTILE CARE
          </p>
          <h1 id="hero-heading" className="text-3xl font-bold tracking-tight sm:text-5xl">
            Premium Laundry &amp; Garment Care
          </h1>
          <p className="mt-4 text-lg text-white/80">
            Professional cleaning, easy pickup &amp; delivery. Choose from verified sellers near you.
          </p>

          {/* Location / search entry */}
          <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-center">
            {isSet ? (
              <>
                <p className="flex items-center justify-center gap-1.5 text-sm text-white/80">
                  <MapPin className="h-4 w-4 text-accent" aria-hidden />
                  {city ?? 'Your location is set'}
                </p>
                <Link href="/sellers">
                  <Button variant="accent" size="lg" className="w-full sm:w-auto">
                    Find Sellers Near You
                    <ArrowRight className="ml-2 h-4 w-4" aria-hidden />
                  </Button>
                </Link>
              </>
            ) : (
              <Link href="/location">
                <Button
                  variant="accent"
                  size="lg"
                  className="w-full sm:w-auto"
                  aria-label="Set your location to find sellers"
                >
                  <MapPin className="mr-2 h-4 w-4" aria-hidden />
                  Set Your Location
                </Button>
              </Link>
            )}
            <Link href="/search">
              <Button
                variant="outline"
                size="lg"
                className="w-full border-white/30 text-white hover:bg-white/10 sm:w-auto"
              >
                <Search className="mr-2 h-4 w-4" aria-hidden />
                Search Services
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Trust signals
// ---------------------------------------------------------------------------

const TRUST_SIGNALS = [
  { icon: Shield, label: 'Verified Sellers', desc: 'Background-checked, quality-assured' },
  { icon: Clock,  label: 'On-Time Service',  desc: 'Punctual pickup and delivery' },
  { icon: Star,   label: 'Top Rated',        desc: 'Avg. 4.7★ across the platform' },
];

function TrustSection() {
  return (
    <section className="border-b border-border bg-muted/30 py-8" aria-label="Why choose us">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <ul className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {TRUST_SIGNALS.map(({ icon: Icon, label, desc }) => (
            <li key={label} className="flex items-center gap-3 rounded-xl bg-card p-4 shadow-sm">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent/10">
                <Icon className="h-5 w-5 text-accent" aria-hidden />
              </div>
              <div>
                <p className="text-sm font-semibold text-foreground">{label}</p>
                <p className="text-xs text-muted-foreground">{desc}</p>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Category grid — configuration-driven from backend
// ---------------------------------------------------------------------------

function CategorySection() {
  const { data: categories, isLoading } = useCategories();

  if (isLoading) {
    return (
      <section className="py-10" aria-label="Loading categories">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <Skeleton className="mb-4 h-7 w-40" />
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {Array.from({ length: 6 }, (_, i) => (
              <Skeleton key={i} className="h-24 rounded-xl" />
            ))}
          </div>
        </div>
      </section>
    );
  }

  if (!categories?.length) return null;

  return (
    <section className="py-10" aria-labelledby="categories-heading">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mb-6 flex items-center justify-between">
          <h2 id="categories-heading" className="text-xl font-bold text-foreground">
            Browse by Service
          </h2>
          <Link href="/services" className="flex items-center gap-1 text-sm font-medium text-accent hover:underline">
            View all <ArrowRight className="h-3.5 w-3.5" aria-hidden />
          </Link>
        </div>
        <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {categories.slice(0, 8).map((cat) => (
            <li key={cat.id}>
              <Link href={`/services?category=${cat.id}`} aria-label={cat.name}>
                <Card className="group cursor-pointer overflow-hidden transition-all hover:shadow-md hover:-translate-y-0.5">
                  {cat.image_url && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={cat.image_url} alt="" aria-hidden className="h-20 w-full object-cover" />
                  )}
                  <CardContent className="p-3 text-center">
                    <p className="text-sm font-medium text-foreground group-hover:text-primary transition-colors">
                      {cat.name}
                    </p>
                  </CardContent>
                </Card>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Featured sellers
// ---------------------------------------------------------------------------

function FeaturedSellersSection() {
  const { isSet, pincode, coords } = useLocationStore();
  const { data: sellerData, isLoading } = useSellers(
    isSet
      ? { pincode: pincode ?? undefined, latitude: coords?.latitude, longitude: coords?.longitude, page_size: 4 }
      : { page_size: 4 }
  );

  const sellers = sellerData?.sellers ?? [];

  return (
    <section className="bg-muted/20 py-10" aria-labelledby="sellers-heading">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mb-6 flex items-center justify-between">
          <h2 id="sellers-heading" className="text-xl font-bold text-foreground">
            {isSet ? 'Available Sellers Near You' : 'Top-Rated Sellers'}
          </h2>
          <Link href="/sellers" className="flex items-center gap-1 text-sm font-medium text-accent hover:underline">
            View all <ArrowRight className="h-3.5 w-3.5" aria-hidden />
          </Link>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {isLoading
            ? Array.from({ length: 3 }, (_, i) => <SellerCardSkeleton key={i} />)
            : sellers.length === 0
            ? (
              <div className="col-span-full rounded-xl border border-dashed border-border py-12 text-center">
                <ShoppingBag className="mx-auto mb-3 h-8 w-8 text-muted-foreground" aria-hidden />
                <p className="text-sm text-muted-foreground">
                  {isSet ? 'No sellers available in your area yet.' : 'Set your location to find sellers.'}
                </p>
                <Link href={isSet ? '/search' : '/location'} className="mt-3 inline-block">
                  <Button variant="outline" size="sm">
                    {isSet ? 'Search services' : 'Set location'}
                  </Button>
                </Link>
              </div>
            )
            : sellers.map((s) => (
              <SellerCard
                key={s.id}
                seller={{
                  id: s.id,
                  business_name: s.business_name,
                  display_name: s.display_name,
                  logo_url: s.logo_url,
                }}
                onSelect={(id) => { window.location.href = `/sellers/${id}`; }}
              />
            ))
          }
        </div>

        {!isSet && (
          <div className="mt-6 text-center">
            <Link href="/location">
              <Button variant="default">
                <MapPin className="mr-2 h-4 w-4" aria-hidden />
                Set Location for Local Results
              </Button>
            </Link>
          </div>
        )}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// How it works
// ---------------------------------------------------------------------------

const HOW_IT_WORKS = [
  { step: '01', title: 'Choose a Service',   desc: 'Browse laundry, dry cleaning, and more.' },
  { step: '02', title: 'Select a Seller',    desc: 'Compare ratings, pricing, and turnaround.' },
  { step: '03', title: 'Schedule Pickup',    desc: 'Pick a convenient time for collection.' },
  { step: '04', title: 'Receive Delivery',   desc: 'Fresh, clean clothes back at your door.' },
];

function HowItWorksSection() {
  return (
    <section className="py-12" aria-labelledby="how-it-works-heading">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <h2 id="how-it-works-heading" className="mb-8 text-center text-2xl font-bold text-foreground">
          How It Works
        </h2>
        <ol className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {HOW_IT_WORKS.map(({ step, title, desc }) => (
            <li key={step} className="flex flex-col items-center text-center">
              <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-primary text-lg font-bold text-primary-foreground">
                {step}
              </div>
              <h3 className="mb-1 font-semibold text-foreground">{title}</h3>
              <p className="text-sm text-muted-foreground">{desc}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Homepage composition
// ---------------------------------------------------------------------------

export function HomepageClient() {
  return (
    <>
      <HeroSection />
      <TrustSection />
      <CategorySection />
      <FeaturedSellersSection />
      <HowItWorksSection />
    </>
  );
}
