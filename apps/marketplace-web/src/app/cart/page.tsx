'use client';

import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ShoppingCart, Trash2, ArrowRight, MapPin, Tag } from 'lucide-react';
import { Button, Card, CardContent, Separator, EmptyState, Alert, AlertDescription } from '@/components/ui';
import { CartItemRow } from '@/components/marketplace';
import { useCartStore, useLocationStore } from '@/lib/stores';

export default function CartPage() {
  const router = useRouter();
  const { items, coupons, removeItem, clearCart, getSellerIds, getItemsBySeller } = useCartStore();
  const { isSet } = useLocationStore();

  const sellerIds = getSellerIds();
  const totalItems = items.reduce((sum, i) => sum + i.quantity, 0);

  if (items.length === 0) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-12 sm:px-6 lg:px-8">
        <EmptyState
          icon={<ShoppingCart className="h-12 w-12 text-muted-foreground" />}
          title="Your cart is empty"
          description="Add services from a seller to get started."
          action={
            <Link href="/sellers">
              <Button>Browse Sellers</Button>
            </Link>
          }
        />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-foreground">
          Cart <span className="text-muted-foreground text-base font-normal">({totalItems} items)</span>
        </h1>
        <Button variant="ghost" size="sm" onClick={clearCart} className="text-destructive hover:text-destructive">
          <Trash2 className="mr-1.5 h-4 w-4" aria-hidden />
          Clear all
        </Button>
      </div>

      {!isSet && (
        <Alert variant="warning" className="mb-4">
          <MapPin className="h-4 w-4" aria-hidden />
          <AlertDescription>
            <Link href="/location" className="font-medium underline">Set your location</Link> before checkout to confirm seller availability.
          </AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Cart items — grouped by seller */}
        <div className="lg:col-span-2 space-y-4">
          {sellerIds.map((sellerId) => {
            const sellerItems = getItemsBySeller(sellerId);
            const sellerName = sellerItems[0]?.seller_name ?? 'Seller';

            return (
              <Card key={sellerId}>
                <CardContent className="p-4">
                  <div className="mb-3 flex items-center justify-between">
                    <Link href={`/sellers/${sellerId}`} className="font-semibold text-foreground hover:text-primary transition-colors">
                      {sellerName}
                    </Link>
                    <span className="text-xs text-muted-foreground">{sellerItems.length} item(s)</span>
                  </div>

                  <div className="divide-y divide-border">
                    {sellerItems.map((item) => (
                      <CartItemRow
                        key={item.key}
                        name={item.service_item_name ?? item.service_name}
                        unit={item.unit_type}
                        quantity={item.quantity}
                        unitPrice={item.unit_price}
                        total={String(parseFloat(item.unit_price || '0') * item.quantity)}
                        addons={item.addons.map((a) => ({
                          name: a.name,
                          quantity: a.quantity,
                          total: String(parseFloat(a.unit_price || '0') * a.quantity),
                        }))}
                        onRemove={() => removeItem(item.key)}
                        onEdit={() => router.push(`/sellers/${sellerId}/services/${item.service_id}`)}
                      />
                    ))}
                  </div>

                  {/* Coupon */}
                  <div className="mt-3 flex items-center gap-2 text-sm">
                    <Tag className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
                    <span className="text-muted-foreground">
                      {coupons[sellerId] ? (
                        <span className="text-green-600 font-medium">Coupon: {coupons[sellerId]}</span>
                      ) : (
                        <Link href={`/offers?seller=${sellerId}`} className="hover:underline">Apply coupon</Link>
                      )}
                    </span>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Order summary — sticky on desktop */}
        <aside className="lg:sticky lg:top-20 h-fit">
          <Card>
            <CardContent className="p-5 space-y-4">
              <h2 className="font-semibold text-foreground">Order Summary</h2>

              <div className="space-y-2 text-sm">
                {sellerIds.map((sellerId) => {
                  const sellerItems = getItemsBySeller(sellerId);
                  const name = sellerItems[0]?.seller_name ?? 'Seller';
                  return (
                    <div key={sellerId} className="flex justify-between">
                      <span className="text-muted-foreground">{name}</span>
                      <span>{sellerItems.length} item(s)</span>
                    </div>
                  );
                })}
              </div>

              <Separator />

              <div className="flex justify-between text-sm font-medium">
                <span>Subtotal</span>
                <span className="text-muted-foreground">Calculated at checkout</span>
              </div>

              <p className="text-xs text-muted-foreground">
                Taxes, fees, and pickup/delivery charges are calculated at checkout based on your location and selected seller.
              </p>

              <Button
                className="w-full"
                size="lg"
                onClick={() => router.push('/checkout')}
              >
                Proceed to Checkout
                <ArrowRight className="ml-2 h-4 w-4" aria-hidden />
              </Button>

              <Link href="/sellers" className="block text-center text-sm text-accent hover:underline">
                Continue Shopping
              </Link>
            </CardContent>
          </Card>
        </aside>
      </div>
    </div>
  );
}
