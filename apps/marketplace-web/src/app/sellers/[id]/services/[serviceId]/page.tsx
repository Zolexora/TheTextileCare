'use client';

import React, { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ShoppingCart, Plus, Minus } from 'lucide-react';
import {
  Button, Skeleton, EmptyState, Textarea, Label, RadioGroup, RadioGroupItem, Checkbox
} from '@/components/ui';
import { useService } from '@/lib/queries';
import { useCartStore } from '@/lib/stores';
import { Breadcrumb } from '@/components/navigation';
import Link from 'next/link';
import { toast } from 'sonner';
import type {} from '@ttc/types';

export default function ServiceDetailPage() {
  const { id: sellerId, serviceId } = useParams<{ id: string; serviceId: string }>();
  const router = useRouter();
  const addItem = useCartStore((s) => s.addItem);

  const { data: service, isLoading, error } = useService(serviceId);

  // Configuration state
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [quantity, setQuantity] = useState(1);
  const [weight, setWeight] = useState('');
  const [selectedAddonIds, setSelectedAddonIds] = useState<string[]>([]);
  const [instructions, setInstructions] = useState('');

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6 lg:px-8 space-y-4">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-48 w-full rounded-xl" />
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (error || !service) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:px-8">
        <EmptyState
          title="Service not found"
          description="This service may no longer be available."
          action={<Link href={`/sellers/${sellerId}`}><Button variant="outline">Back to seller</Button></Link>}
        />
      </div>
    );
  }

  const toggleAddon = (addonId: string) => {
    setSelectedAddonIds((prev) =>
      prev.includes(addonId) ? prev.filter((a) => a !== addonId) : [...prev, addonId]
    );
  };

  const handleAddToCart = () => {
    const selectedItem = service.items.find((i) => i.id === selectedItemId);
    const selectedAddons = service.addons.filter((a) => selectedAddonIds.includes(a.id));

    // Determine unit type from service configuration
    const unitType = service.is_per_weight ? 'kg' : service.is_per_item ? 'piece' : 'unit';

    const key = `${sellerId}-${service.id}-${selectedItemId ?? 'base'}-${selectedAddonIds.sort().join(',')}`;

    addItem({
      key,
      service_id: service.id,
      service_name: service.name,
      service_item_id: selectedItemId ?? undefined,
      service_item_name: selectedItem?.name,
      quantity,
      weight: service.is_per_weight ? weight : undefined,
      unit_type: unitType,
      unit_price: '0', // Backend will calculate — ponytail: price resolved by backend
      addons: selectedAddons.map((a) => ({
        id: a.id,
        name: a.name,
        quantity: 1,
        unit_price: '0',
      })),
      seller_id: sellerId,
      seller_name: 'Seller', // ponytail: seller name from context when seller query is available
      branch_id: '', // ponytail: branch resolved during checkout serviceability
      instructions,
    });

    toast.success(`${service.name} added to cart`);
    router.push('/cart');
  };

  return (
    <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6 lg:px-8">
      <Breadcrumb
        className="mb-4"
        items={[
          { label: 'Sellers', href: '/sellers' },
          { label: 'Seller', href: `/sellers/${sellerId}` },
          { label: service.name },
        ]}
      />

      {/* Service image */}
      {service.image_url && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={service.image_url}
          alt={service.name}
          className="mb-6 h-48 w-full rounded-xl object-cover"
        />
      )}

      <h1 className="text-2xl font-bold text-foreground">{service.name}</h1>
      {service.description && (
        <p className="mt-2 text-sm text-muted-foreground">{service.description}</p>
      )}

      <div className="mt-6 space-y-6">
        {/* Item selection (if applicable) */}
        {service.items.length > 0 && (
          <fieldset>
            <legend className="mb-3 text-sm font-semibold text-foreground">
              Select Item <span className="text-destructive" aria-hidden>*</span>
            </legend>
            <RadioGroup
              value={selectedItemId ?? ''}
              onValueChange={setSelectedItemId}
              aria-label="Select item"
            >
              {service.items.map((item) => (
                <div key={item.id} className="flex items-center gap-3 rounded-lg border border-border p-3 hover:bg-muted/50">
                  <RadioGroupItem value={item.id} id={`item-${item.id}`} />
                  <Label htmlFor={`item-${item.id}`} className="flex-1 cursor-pointer">
                    <span className="font-medium">{item.name}</span>
                    {item.description && (
                      <span className="block text-xs text-muted-foreground">{item.description}</span>
                    )}
                  </Label>
                </div>
              ))}
            </RadioGroup>
          </fieldset>
        )}

        {/* Quantity */}
        <div>
          <Label className="mb-3 block text-sm font-semibold">
            {service.is_per_weight ? 'Weight (kg)' : 'Quantity'}
          </Label>
          {service.is_per_weight ? (
            <input
              type="number"
              min="0.1"
              step="0.1"
              value={weight}
              onChange={(e) => setWeight(e.target.value)}
              placeholder="e.g. 2.5"
              className="flex h-10 w-32 rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-label="Weight in kg"
            />
          ) : (
            <div className="flex items-center gap-3">
              <button
                onClick={() => setQuantity((q) => Math.max(1, q - 1))}
                className="flex h-9 w-9 items-center justify-center rounded-md border border-border bg-background hover:bg-muted"
                aria-label="Decrease quantity"
                disabled={quantity <= 1}
              >
                <Minus className="h-4 w-4" aria-hidden />
              </button>
              <span className="w-8 text-center font-semibold" aria-live="polite">{quantity}</span>
              <button
                onClick={() => setQuantity((q) => q + 1)}
                className="flex h-9 w-9 items-center justify-center rounded-md border border-border bg-background hover:bg-muted"
                aria-label="Increase quantity"
              >
                <Plus className="h-4 w-4" aria-hidden />
              </button>
            </div>
          )}
        </div>

        {/* Add-ons */}
        {service.addons.length > 0 && (
          <fieldset>
            <legend className="mb-3 text-sm font-semibold text-foreground">Add-ons (optional)</legend>
            <div className="space-y-2">
              {service.addons.map((addon) => (
                <div key={addon.id} className="flex items-center gap-3 rounded-lg border border-border p-3">
                  <Checkbox
                    id={`addon-${addon.id}`}
                    checked={selectedAddonIds.includes(addon.id)}
                    onCheckedChange={() => toggleAddon(addon.id)}
                  />
                  <Label htmlFor={`addon-${addon.id}`} className="flex-1 cursor-pointer">
                    <span className="font-medium">{addon.name}</span>
                    {addon.description && (
                      <span className="block text-xs text-muted-foreground">{addon.description}</span>
                    )}
                  </Label>
                </div>
              ))}
            </div>
          </fieldset>
        )}

        {/* Special instructions */}
        <div>
          <Label htmlFor="instructions" className="mb-2 block text-sm font-semibold">
            Special Instructions (optional)
          </Label>
          <Textarea
            id="instructions"
            placeholder="Any special care instructions, stain locations, etc."
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            rows={3}
          />
        </div>

        {/* Add to cart */}
        <div className="sticky bottom-0 -mx-4 border-t border-border bg-background px-4 pb-safe pt-3 pb-3 sm:relative sm:border-0 sm:p-0">
          <Button
            onClick={handleAddToCart}
            className="w-full"
            size="lg"
            disabled={service.items.length > 0 && !selectedItemId}
          >
            <ShoppingCart className="mr-2 h-5 w-5" aria-hidden />
            Add to Cart
          </Button>
        </div>
      </div>
    </div>
  );
}
