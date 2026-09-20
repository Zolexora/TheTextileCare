'use client';

import React from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Package, CheckCircle2, ArrowRight } from 'lucide-react';
import { Button, Card, CardContent, Skeleton, EmptyState } from '@/components/ui';
import { OrderStatusBadge } from '@/components/marketplace';
import { useOrders } from '@/lib/queries';
import { useAuth } from '@/lib/auth-context';
import { formatCurrency, formatDate } from '@/lib/utils';
import type {} from '@ttc/types';

export default function OrdersPage() {
  const { isAuthenticated } = useAuth();
  const params = useSearchParams();
  const confirmed = params.get('confirmed') === '1';

  const { data: orderList, isLoading } = useOrders({ limit: 20 });

  if (!isAuthenticated) {
    return (
      <div className="mx-auto max-w-md px-4 py-12 sm:px-6 lg:px-8 text-center">
        <Package className="mx-auto mb-4 h-12 w-12 text-muted-foreground" aria-hidden />
        <h1 className="text-xl font-bold text-foreground mb-2">Your Orders</h1>
        <p className="text-sm text-muted-foreground mb-6">Sign in to view your order history.</p>
        <Link href="/login?redirect=/orders">
          <Button className="w-full">Sign In</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6 lg:px-8">
      {/* Confirmation banner */}
      {confirmed && (
        <div className="mb-6 flex items-center gap-3 rounded-xl bg-green-50 border border-green-200 px-4 py-3 dark:bg-green-950 dark:border-green-800">
          <CheckCircle2 className="h-5 w-5 text-green-600 flex-shrink-0" aria-hidden />
          <div>
            <p className="text-sm font-semibold text-green-800 dark:text-green-200">Order placed successfully!</p>
            <p className="text-xs text-green-600 dark:text-green-400">You&apos;ll receive updates as your order progresses.</p>
          </div>
        </div>
      )}

      <h1 className="mb-6 text-2xl font-bold text-foreground">My Orders</h1>

      {isLoading ? (
        <div className="space-y-4">
          {Array.from({ length: 3 }, (_, i) => (
            <Card key={i}><CardContent className="p-5 space-y-3">
              <Skeleton className="h-5 w-32" />
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-4 w-24" />
            </CardContent></Card>
          ))}
        </div>
      ) : !orderList?.items.length ? (
        <EmptyState
          icon={<Package className="h-12 w-12 text-muted-foreground" />}
          title="No orders yet"
          description="Your order history will appear here once you place your first order."
          action={<Link href="/sellers"><Button>Browse Sellers</Button></Link>}
        />
      ) : (
        <div className="space-y-4">
          {orderList.items.map((order) => (
            <Link key={order.id} href={`/orders/${order.id}`}>
              <Card className="cursor-pointer transition-shadow hover:shadow-md">
                <CardContent className="p-5">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="font-semibold text-foreground">Order #{order.order_number}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {formatDate(order.placed_at)}
                        {' · '}
                        {order.items_count} item(s)
                      </p>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <OrderStatusBadge status={order.status} />
                      <p className="text-sm font-semibold text-foreground">
                        {formatCurrency(order.grand_total, order.currency)}
                      </p>
                    </div>
                  </div>
                  <div className="mt-3 flex items-center justify-between text-xs text-accent">
                    <span>View details</span>
                    <ArrowRight className="h-3.5 w-3.5" aria-hidden />
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
