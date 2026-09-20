'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { CreditCard, Lock, ArrowLeft } from 'lucide-react';
import {
  Button, Card, CardContent, Separator, Alert, AlertTitle, AlertDescription,
  EmptyState, Skeleton
} from '@/components/ui';
import { AddressCard } from '@/components/marketplace';
import { useCartStore, useCheckoutStore } from '@/lib/stores';
import { useAddresses, useCreateOrder } from '@/lib/queries';
import { useAuth } from '@/lib/auth-context';
import Link from 'next/link';
import { toast } from 'sonner';

// ---------------------------------------------------------------------------
// Checkout page — Phase 8
// Revalidation before payment: ponytail: placeholder — call /checkout/validate
// ---------------------------------------------------------------------------

export default function CheckoutPage() {
  const router = useRouter();
  const { isAuthenticated } = useAuth();
  const { items, getSellerIds, getItemsBySeller } = useCartStore();
  const { addressId, setAddressId, resetCheckout } = useCheckoutStore();
  const { data: addresses, isLoading: addressesLoading } = useAddresses();
  const createOrder = useCreateOrder();

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [materialChange] = useState<string | null>(null);

  const sellerIds = getSellerIds();

  if (items.length === 0) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-12 sm:px-6 lg:px-8">
        <EmptyState
          title="Your cart is empty"
          description="Add items to your cart before checking out."
          action={<Link href="/sellers"><Button>Browse Sellers</Button></Link>}
        />
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="mx-auto max-w-md px-4 py-12 sm:px-6 lg:px-8 text-center">
        <Lock className="mx-auto mb-4 h-12 w-12 text-muted-foreground" aria-hidden />
        <h1 className="text-xl font-bold text-foreground mb-2">Sign in to checkout</h1>
        <p className="text-sm text-muted-foreground mb-6">
          You need to be signed in to place an order.
        </p>
        <Link href="/login?redirect=/checkout">
          <Button className="w-full">Sign In</Button>
        </Link>
      </div>
    );
  }

  const handlePlaceOrder = async () => {
    if (!addressId) {
      toast.error('Please select a delivery address');
      return;
    }

    setIsSubmitting(true);
    try {
      // ponytail: create one order per seller — multi-seller splitting done here
      // In production, backend should handle splitting via a /checkout endpoint
      for (const sellerId of sellerIds) {
        const sellerItems = getItemsBySeller(sellerId);
        const firstItem = sellerItems[0];
        if (!firstItem) continue;

        await createOrder.mutateAsync({
          seller_id: sellerId,
          branch_id: firstItem.branch_id || sellerId, // ponytail: branch selection in scheduling phase
          currency: 'INR',
          customer_address_id: addressId,
          items: sellerItems.map((item) => ({
            service_id: item.service_id,
            service_item_id: item.service_item_id,
            quantity: String(item.quantity),
            weight: item.weight,
            unit_type: item.unit_type,
            addons: item.addons.map((a) => ({
              service_addon_id: a.id,
              quantity: String(a.quantity),
            })),
          })),
          notes: sellerItems.map((i) => i.instructions).filter(Boolean).join('; '),
        });
      }

      useCartStore.getState().clearCart();
      resetCheckout();
      router.push('/orders?confirmed=1');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Order failed. Please try again.';
      toast.error(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <div className="mb-6 flex items-center gap-3">
        <Link href="/cart" className="text-muted-foreground hover:text-foreground" aria-label="Back to cart">
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <h1 className="text-2xl font-bold text-foreground">Checkout</h1>
      </div>

      {materialChange && (
        <Alert variant="warning" className="mb-4">
          <AlertTitle>Price change detected</AlertTitle>
          <AlertDescription>{materialChange}</AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          {/* Address section */}
          <Card>
            <CardContent className="p-5">
              <h2 className="mb-4 text-sm font-semibold text-foreground">Pickup &amp; Delivery Address</h2>
              {addressesLoading ? (
                <div className="space-y-3">
                  {Array.from({ length: 2 }, (_, i) => <Skeleton key={i} className="h-20 rounded-xl" />)}
                </div>
              ) : !addresses?.length ? (
                <div className="text-center py-4">
                  <p className="text-sm text-muted-foreground mb-3">No saved addresses.</p>
                  <Link href="/account/addresses/new">
                    <Button variant="outline" size="sm">Add Address</Button>
                  </Link>
                </div>
              ) : (
                <div className="space-y-3">
                  {addresses.map((addr) => (
                    <AddressCard
                      key={addr.id}
                      address={addr}
                      isSelected={addressId === addr.id}
                      onSelect={setAddressId}
                    />
                  ))}
                  <Link href="/account/addresses/new" className="block text-sm text-accent hover:underline mt-2">
                    + Add new address
                  </Link>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Order sections — one per seller */}
          {sellerIds.map((sellerId) => {
            const sellerItems = getItemsBySeller(sellerId);
            const sellerName = sellerItems[0]?.seller_name ?? 'Seller';
            return (
              <Card key={sellerId}>
                <CardContent className="p-5">
                  <h2 className="mb-3 text-sm font-semibold text-foreground">{sellerName}</h2>
                  <div className="space-y-2 text-sm">
                    {sellerItems.map((item) => (
                      <div key={item.key} className="flex justify-between">
                        <span className="text-foreground">
                          {item.service_item_name ?? item.service_name}
                          <span className="ml-1 text-muted-foreground">× {item.quantity}</span>
                        </span>
                        <span className="text-muted-foreground">—</span>
                      </div>
                    ))}
                  </div>

                  {/* Scheduling section — placeholder for Phase 7 */}
                  <div className="mt-4 rounded-lg border border-dashed border-border p-3 text-xs text-muted-foreground">
                    <p className="font-medium text-foreground mb-1">Pickup &amp; Delivery Scheduling</p>
                    <p>Slot selection will be available once the scheduling service is connected.</p>
                    <Link href={`/account/schedule?seller=${sellerId}`} className="text-accent hover:underline">
                      Schedule now →
                    </Link>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Summary sidebar */}
        <aside className="lg:sticky lg:top-20 h-fit space-y-4">
          <Card>
            <CardContent className="p-5 space-y-4">
              <h2 className="font-semibold text-foreground">Order Total</h2>

              <div className="text-sm space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Items</span>
                  <span>{items.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Subtotal</span>
                  <span className="text-muted-foreground">Calculating…</span>
                </div>
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>Taxes &amp; Fees</span>
                  <span>At checkout</span>
                </div>
              </div>

              <Separator />

              <p className="text-xs text-muted-foreground">
                Final pricing, taxes, and fees are calculated by the seller and confirmed before payment.
              </p>

              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Lock className="h-3.5 w-3.5" aria-hidden />
                Secure checkout
              </div>

              <Button
                className="w-full"
                size="lg"
                onClick={handlePlaceOrder}
                isLoading={isSubmitting}
                disabled={!addressId}
              >
                <CreditCard className="mr-2 h-5 w-5" aria-hidden />
                Place Order
              </Button>
            </CardContent>
          </Card>
        </aside>
      </div>
    </div>
  );
}
