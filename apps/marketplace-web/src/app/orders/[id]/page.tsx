'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Package, Clock, MapPin, FileText } from 'lucide-react';
import { Button, Card, CardContent, Skeleton, EmptyState, Separator } from '@/components/ui';
import { OrderStatusBadge, OrderTimeline, type TimelineEvent } from '@/components/marketplace';
import { useOrder } from '@/lib/queries';
import { formatCurrency, formatDate } from '@/lib/utils';
import type { OrderStatus } from '@ttc/types';

// Map order status to timeline events
function buildTimeline(status: OrderStatus, history: Array<{ to_status: string; created_at: string }>): TimelineEvent[] {
  const STEPS: Array<{ status: string; label: string }> = [
    { status: 'PENDING',    label: 'Order Placed' },
    { status: 'CONFIRMED',  label: 'Confirmed' },
    { status: 'IN_PROGRESS', label: 'In Progress' },
    { status: 'COMPLETED',  label: 'Delivered' },
  ];

  const completedStatuses = new Set(history.map((h) => h.to_status));
  completedStatuses.add(status);

  const ORDER = ['PENDING', 'CONFIRMED', 'IN_PROGRESS', 'COMPLETED'];
  const currentIdx = ORDER.indexOf(status);

  return STEPS.map((step, idx) => {
    const historyEntry = history.find((h) => h.to_status === step.status);
    return {
      label: step.label,
      timestamp: historyEntry?.created_at ?? null,
      isCompleted: idx < currentIdx || status === step.status,
      isCurrent: step.status === status,
    };
  });
}

export default function OrderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: order, isLoading, error } = useOrder(id);

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6 lg:px-8 space-y-4">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-32 w-full rounded-xl" />
        <Skeleton className="h-48 w-full rounded-xl" />
      </div>
    );
  }

  if (error || !order) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:px-8">
        <EmptyState
          title="Order not found"
          action={<Link href="/orders"><Button variant="outline">Back to orders</Button></Link>}
        />
      </div>
    );
  }

  const timeline = buildTimeline(order.status, order.status_history);

  return (
    <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6 lg:px-8 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link href="/orders" aria-label="Back to orders">
          <ArrowLeft className="h-5 w-5 text-muted-foreground hover:text-foreground" />
        </Link>
        <div className="flex-1 min-w-0">
          <h1 className="text-xl font-bold text-foreground">Order #{order.order_number}</h1>
          <p className="text-xs text-muted-foreground">{formatDate(order.placed_at)}</p>
        </div>
        <OrderStatusBadge status={order.status} />
      </div>

      {/* Timeline */}
      <Card>
        <CardContent className="p-5">
          <h2 className="mb-4 text-sm font-semibold text-foreground flex items-center gap-2">
            <Clock className="h-4 w-4 text-muted-foreground" aria-hidden />
            Order Timeline
          </h2>
          <OrderTimeline events={timeline} />
        </CardContent>
      </Card>

      {/* Items */}
      <Card>
        <CardContent className="p-5">
          <h2 className="mb-4 text-sm font-semibold text-foreground flex items-center gap-2">
            <Package className="h-4 w-4 text-muted-foreground" aria-hidden />
            Items
          </h2>
          <div className="divide-y divide-border">
            {order.items.map((item) => (
              <div key={item.id} className="flex justify-between py-3 text-sm">
                <div>
                  <p className="font-medium text-foreground">{item.service_name_snapshot}</p>
                  {item.service_item_name_snapshot && (
                    <p className="text-xs text-muted-foreground">{item.service_item_name_snapshot}</p>
                  )}
                  <p className="text-xs text-muted-foreground">
                    {item.quantity} {item.unit_type} × {formatCurrency(item.unit_price, order.currency)}
                  </p>
                  {item.addons.map((a) => (
                    <p key={a.id} className="text-xs text-muted-foreground">+ {a.addon_name_snapshot}</p>
                  ))}
                </div>
                <div className="text-right">
                  <p className="font-semibold text-foreground">{formatCurrency(item.total_amount, order.currency)}</p>
                </div>
              </div>
            ))}
          </div>

          <Separator className="my-4" />

          <div className="space-y-1 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Subtotal</span>
              <span>{formatCurrency(order.subtotal, order.currency)}</span>
            </div>
            {parseFloat(order.discount_total) > 0 && (
              <div className="flex justify-between text-green-600">
                <span>Discount</span>
                <span>− {formatCurrency(order.discount_total, order.currency)}</span>
              </div>
            )}
            {parseFloat(order.tax_total) > 0 && (
              <div className="flex justify-between text-muted-foreground">
                <span>Tax</span>
                <span>{formatCurrency(order.tax_total, order.currency)}</span>
              </div>
            )}
            <Separator />
            <div className="flex justify-between font-bold">
              <span>Total</span>
              <span>{formatCurrency(order.grand_total, order.currency)}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Address */}
      {order.customer_address_snapshot && (
        <Card>
          <CardContent className="p-5">
            <h2 className="mb-3 text-sm font-semibold text-foreground flex items-center gap-2">
              <MapPin className="h-4 w-4 text-muted-foreground" aria-hidden />
              Pickup &amp; Delivery Address
            </h2>
            <div className="text-sm text-muted-foreground">
              {order.customer_address_snapshot.recipient_name && (
                <p className="font-medium text-foreground">{order.customer_address_snapshot.recipient_name}</p>
              )}
              <p>{order.customer_address_snapshot.address_line_1}</p>
              {order.customer_address_snapshot.address_line_2 && (
                <p>{order.customer_address_snapshot.address_line_2}</p>
              )}
              <p>
                {[
                  order.customer_address_snapshot.locality,
                  order.customer_address_snapshot.city,
                  order.customer_address_snapshot.state,
                  order.customer_address_snapshot.postal_code,
                ].filter(Boolean).join(', ')}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Actions */}
      <div className="flex flex-wrap gap-3">
        <Button variant="outline" size="sm" onClick={() => window.print()}>
          <FileText className="mr-1.5 h-4 w-4" aria-hidden />
          Download Invoice
        </Button>
        {order.status === 'COMPLETED' && (
          <Link href={`/orders/${id}/review`}>
            <Button variant="outline" size="sm">Write a Review</Button>
          </Link>
        )}
        {['PENDING', 'CONFIRMED'].includes(order.status) && (
          <Link href={`/orders/${id}/cancel`}>
            <Button variant="outline" size="sm" className="text-destructive border-destructive/30">
              Cancel Order
            </Button>
          </Link>
        )}
        <Link href="/sellers">
          <Button variant="outline" size="sm">Reorder</Button>
        </Link>
      </div>
    </div>
  );
}
