'use client';

import React from 'react';
import { Star, Clock } from 'lucide-react';
import { Button, Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui';
import { cn } from '@/lib/utils';

/**
 * Seller comparison panel.
 * Compares: Price, Rating, Turnaround, Pickup, Delivery.
 * Does NOT show distance.
 */

interface SellerData {
  id: string;
  business_name: string;
  display_name?: string | null;
  logo_url?: string | null;
  rating?: number | null;
  review_count?: number | null;
  price_from?: string | null;
  turnaround_label?: string | null;
  pickup_available?: boolean;
  delivery_available?: boolean;
}

interface SellerCompareProps {
  sellers: SellerData[];
  onClose: () => void;
  onSelect: (id: string) => void;
}

const COMPARE_ROWS: {
  label: string;
  key: keyof SellerData;
  render: (val: SellerData[keyof SellerData]) => React.ReactNode;
}[] = [
  {
    label: 'Rating',
    key: 'rating',
    render: (v) =>
      v != null ? (
        <span className="flex items-center gap-1 font-semibold">
          <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" aria-hidden />
          {Number(v).toFixed(1)}
        </span>
      ) : (
        <span className="text-muted-foreground">—</span>
      ),
  },
  {
    label: 'Starting Price',
    key: 'price_from',
    render: (v) =>
      v ? (
        <span className="font-semibold text-foreground">{String(v)}</span>
      ) : (
        <span className="text-muted-foreground">—</span>
      ),
  },
  {
    label: 'Turnaround',
    key: 'turnaround_label',
    render: (v) =>
      v ? (
        <span className="flex items-center gap-1">
          <Clock className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
          {String(v)}
        </span>
      ) : (
        <span className="text-muted-foreground">—</span>
      ),
  },
  {
    label: 'Pickup',
    key: 'pickup_available',
    render: (v) => (
      <span className={cn('font-medium', v ? 'text-green-600' : 'text-muted-foreground')}>
        {v ? 'Available' : 'Not available'}
      </span>
    ),
  },
  {
    label: 'Delivery',
    key: 'delivery_available',
    render: (v) => (
      <span className={cn('font-medium', v ? 'text-green-600' : 'text-muted-foreground')}>
        {v ? 'Available' : 'Not available'}
      </span>
    ),
  },
];

export function SellerCompare({ sellers, onClose, onSelect }: SellerCompareProps) {
  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-3xl overflow-x-auto">
        <DialogHeader>
          <DialogTitle>Compare Sellers</DialogTitle>
        </DialogHeader>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[400px] text-sm" role="table">
            <thead>
              <tr>
                <th className="w-32 text-left text-xs font-medium text-muted-foreground p-2" scope="col">
                  Feature
                </th>
                {sellers.map((s) => {
                  const name = s.display_name ?? s.business_name;
                  return (
                    <th key={s.id} className="text-center p-2" scope="col">
                      <div className="flex flex-col items-center gap-1">
                        <Avatar className="h-10 w-10 rounded-lg">
                          <AvatarImage src={s.logo_url ?? undefined} alt={name} />
                          <AvatarFallback className="rounded-lg text-xs font-bold bg-primary/10 text-primary">
                            {name.slice(0, 2).toUpperCase()}
                          </AvatarFallback>
                        </Avatar>
                        <span className="font-semibold text-foreground leading-tight">{name}</span>
                      </div>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {COMPARE_ROWS.map(({ label, key, render }) => (
                <tr key={label} className="border-t border-border">
                  <td className="p-2 text-xs font-medium text-muted-foreground">{label}</td>
                  {sellers.map((s) => (
                    <td key={s.id} className="p-2 text-center">
                      {render(s[key])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t border-border">
                <td className="p-2" />
                {sellers.map((s) => (
                  <td key={s.id} className="p-2 text-center">
                    <Button size="sm" onClick={() => onSelect(s.id)}>
                      Select
                    </Button>
                  </td>
                ))}
              </tr>
            </tfoot>
          </table>
        </div>
      </DialogContent>
    </Dialog>
  );
}
