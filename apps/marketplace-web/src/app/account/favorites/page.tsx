'use client';

import { Heart } from 'lucide-react';
import { EmptyState } from '@/components/ui';
import Link from 'next/link';
import { Button } from '@/components/ui';

export default function FavoritesPage() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-10 sm:px-6 lg:px-8">
      <h1 className="mb-6 text-xl font-bold text-foreground">Saved &amp; Favourites</h1>
      <EmptyState
        icon={<Heart className="h-10 w-10 text-muted-foreground" />}
        title="No saved sellers or services"
        description="Tap the heart icon on any seller or service to save it here."
        action={<Link href="/sellers"><Button variant="outline">Browse Sellers</Button></Link>}
      />
    </div>
  );
}
