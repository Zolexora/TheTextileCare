import React from 'react';
import Link from 'next/link';
import { Search } from 'lucide-react';
import { Button } from '@/components/ui';

export default function NotFound() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 text-center">
      <p className="text-7xl font-black text-muted-foreground/30">404</p>
      <h1 className="mt-4 text-2xl font-bold text-foreground">Page not found</h1>
      <p className="mt-2 text-sm text-muted-foreground max-w-sm">
        The page you&apos;re looking for doesn&apos;t exist or has been moved.
      </p>
      <div className="mt-6 flex flex-wrap justify-center gap-3">
        <Link href="/">
          <Button>Go Home</Button>
        </Link>
        <Link href="/search">
          <Button variant="outline">
            <Search className="mr-2 h-4 w-4" aria-hidden />
            Search
          </Button>
        </Link>
      </div>
    </div>
  );
}
