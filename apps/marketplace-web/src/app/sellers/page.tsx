'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button, EmptyState } from '@/components/ui';
import { SellerCard, SellerCardSkeleton } from '@/components/marketplace';
import { SellerCompare } from './seller-compare';
import { useSellers } from '@/lib/queries';
import { useLocationStore } from '@/lib/stores';
import Link from 'next/link';

export default function SellersPage() {
  const router = useRouter();
  const { isSet, pincode, coords, city } = useLocationStore();
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [showCompare, setShowCompare] = useState(false);

  const { data: sellerData, isLoading } = useSellers({
    pincode: pincode ?? undefined,
    latitude: coords?.latitude,
    longitude: coords?.longitude,
    page_size: 20,
  });

  const sellers = sellerData?.sellers ?? [];

  const toggleCompare = (id: string) => {
    setCompareIds((prev) =>
      prev.includes(id)
        ? prev.filter((i) => i !== id)
        : prev.length < 3
        ? [...prev, id]
        : prev
    );
  };

  const comparedSellers = sellers.filter((s) => compareIds.includes(s.id));

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-foreground">
            {isSet ? `Sellers near ${city ?? pincode ?? 'you'}` : 'All Sellers'}
          </h1>
          {sellers.length > 0 && (
            <p className="text-sm text-muted-foreground">{sellers.length} sellers found</p>
          )}
        </div>
        {!isSet && (
          <Link href="/location">
            <Button variant="outline" size="sm">Set Location</Button>
          </Link>
        )}
      </div>

      {/* Compare bar */}
      {compareIds.length >= 2 && (
        <div className="mb-4 flex items-center justify-between rounded-xl bg-primary/5 border border-primary/20 px-4 py-3">
          <p className="text-sm font-medium text-foreground">
            {compareIds.length} sellers selected for comparison
          </p>
          <Button size="sm" onClick={() => setShowCompare(true)}>
            Compare Now
          </Button>
        </div>
      )}

      {/* Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }, (_, i) => <SellerCardSkeleton key={i} />)}
        </div>
      ) : sellers.length === 0 ? (
        <EmptyState
          title={isSet ? 'No sellers available in your area' : 'Set your location first'}
          description={
            isSet
              ? 'We are expanding to more areas soon. Try a nearby pincode.'
              : 'Your location helps us show sellers that can serve you.'
          }
          action={
            <Link href="/location">
              <Button>
                {isSet ? 'Change Location' : 'Set Location'}
              </Button>
            </Link>
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {sellers.map((s) => (
            <SellerCard
              key={s.id}
              seller={{
                id: s.id,
                business_name: s.business_name,
                display_name: s.display_name,
                logo_url: s.logo_url,
              }}
              onSelect={(id) => router.push(`/sellers/${id}`)}
              onCompare={toggleCompare}
              isCompared={compareIds.includes(s.id)}
            />
          ))}
        </div>
      )}

      {/* Comparison modal */}
      {showCompare && (
        <SellerCompare
          sellers={comparedSellers.map((s) => ({
            id: s.id,
            business_name: s.business_name,
            display_name: s.display_name,
            logo_url: s.logo_url,
          }))}
          onClose={() => setShowCompare(false)}
          onSelect={(id) => { setShowCompare(false); router.push(`/sellers/${id}`); }}
        />
      )}
    </div>
  );
}
