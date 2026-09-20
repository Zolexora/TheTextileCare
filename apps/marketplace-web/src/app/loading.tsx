import React from 'react';
import { Skeleton } from '@/components/ui';

// Global loading skeleton for the root layout
export default function Loading() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 space-y-6">
      <Skeleton className="h-48 w-full rounded-2xl" />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {Array.from({ length: 8 }, (_, i) => <Skeleton key={i} className="h-24 rounded-xl" />)}
      </div>
      <Skeleton className="h-8 w-48" />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 3 }, (_, i) => <Skeleton key={i} className="h-40 rounded-xl" />)}
      </div>
    </div>
  );
}
