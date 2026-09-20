'use client';

import { Tag } from 'lucide-react';
import { EmptyState, Button } from '@/components/ui';
import Link from 'next/link';

export default function OffersPage() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-10 sm:px-6 lg:px-8">
      <h1 className="mb-6 text-xl font-bold text-foreground">Offers &amp; Coupons</h1>
      <EmptyState
        icon={<Tag className="h-10 w-10 text-muted-foreground" />}
        title="No active offers"
        description="Offers and coupons available to you will appear here."
        action={<Link href="/sellers"><Button variant="outline">Explore Services</Button></Link>}
      />
    </div>
  );
}
