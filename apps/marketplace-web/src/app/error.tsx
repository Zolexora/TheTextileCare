'use client';

import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui';

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function GlobalError({ error, reset }: ErrorPageProps) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 text-center">
      <AlertTriangle className="mb-4 h-12 w-12 text-destructive" aria-hidden />
      <h1 className="text-xl font-bold text-foreground">Something went wrong</h1>
      <p className="mt-2 text-sm text-muted-foreground max-w-md">
        {error.message || 'An unexpected error occurred. Please try again.'}
      </p>
      {error.digest && (
        <p className="mt-1 text-xs text-muted-foreground">Error ID: {error.digest}</p>
      )}
      <div className="mt-6 flex gap-3">
        <Button onClick={reset}>
          <RefreshCw className="mr-2 h-4 w-4" aria-hidden />
          Try Again
        </Button>
        <Button variant="outline" onClick={() => (window.location.href = '/')}>
          Go Home
        </Button>
      </div>
    </div>
  );
}
