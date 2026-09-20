/**
 * TTC Marketplace-specific components.
 *
 * SellerCard, ServiceCard, PriceDisplay, RatingDisplay, OfferBadge,
 * AvailabilityBadge, OrderStatusBadge, OrderTimeline, StarRating.
 *
 * All components consume backend-typed data only — no hard-coded business rules.
 */

'use client';

import React from 'react';
import { Star, Clock, CheckCircle2, Circle, Loader2, MapPin } from 'lucide-react';
import { cn, formatCurrency, truncate } from '@/lib/utils';
import { Badge, Card, CardContent, Avatar, AvatarImage, AvatarFallback, Skeleton } from './ui';
import type { OrderStatus } from '@ttc/types';

// ---------------------------------------------------------------------------
// StarRating
// ---------------------------------------------------------------------------

interface StarRatingProps {
  rating: number;
  max?: number;
  size?: 'sm' | 'md' | 'lg';
  showValue?: boolean;
  count?: number;
  className?: string;
}

export function StarRating({ rating, max = 5, size = 'sm', showValue, count, className }: StarRatingProps) {
  const sizeClass = { sm: 'h-3 w-3', md: 'h-4 w-4', lg: 'h-5 w-5' }[size];
  return (
    <span className={cn('inline-flex items-center gap-0.5', className)}>
      {Array.from({ length: max }, (_, i) => (
        <Star
          key={i}
          className={cn(sizeClass, i < Math.round(rating) ? 'fill-amber-400 text-amber-400' : 'text-muted-foreground')}
          aria-hidden
        />
      ))}
      {showValue && (
        <span className="ml-1 text-xs text-muted-foreground">
          {rating.toFixed(1)}
          {count != null && ` (${count})`}
        </span>
      )}
    </span>
  );
}

// ---------------------------------------------------------------------------
// RatingDisplay — numeric + stars + count
// ---------------------------------------------------------------------------

interface RatingDisplayProps {
  rating?: number | null;
  reviewCount?: number | null;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function RatingDisplay({ rating, reviewCount, size = 'sm', className }: RatingDisplayProps) {
  if (rating == null) return <span className={cn('text-xs text-muted-foreground', className)}>No reviews yet</span>;
  return (
    <span className={cn('inline-flex items-center gap-1', className)}>
      <StarRating rating={rating} size={size} />
      <span className="text-xs font-medium">{rating.toFixed(1)}</span>
      {reviewCount != null && (
        <span className="text-xs text-muted-foreground">({reviewCount})</span>
      )}
    </span>
  );
}

// ---------------------------------------------------------------------------
// PriceDisplay — renders backend pricing units without hard-coding
// ---------------------------------------------------------------------------

interface PriceDisplayProps {
  amount: string | number;
  currency?: string;
  unit?: string | null;
  originalAmount?: string | number | null;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function PriceDisplay({
  amount,
  currency = 'INR',
  unit,
  originalAmount,
  size = 'md',
  className,
}: PriceDisplayProps) {
  const sizeClass = { sm: 'text-sm', md: 'text-base', lg: 'text-lg' }[size];
  const formatted = formatCurrency(amount, currency);
  return (
    <span className={cn('inline-flex items-baseline gap-1', className)}>
      <span className={cn('font-semibold text-foreground', sizeClass)}>{formatted}</span>
      {unit && <span className="text-xs text-muted-foreground">/ {unit}</span>}
      {originalAmount != null && (
        <span className="text-xs text-muted-foreground line-through">
          {formatCurrency(originalAmount, currency)}
        </span>
      )}
    </span>
  );
}

// ---------------------------------------------------------------------------
// AvailabilityBadge
// ---------------------------------------------------------------------------

interface AvailabilityBadgeProps {
  available: boolean;
  label?: string;
  className?: string;
}

export function AvailabilityBadge({ available, label, className }: AvailabilityBadgeProps) {
  return (
    <Badge
      variant={available ? 'success' : 'outline'}
      className={cn('text-xs', className)}
    >
      {label ?? (available ? 'Available' : 'Unavailable')}
    </Badge>
  );
}

// ---------------------------------------------------------------------------
// OfferBadge
// ---------------------------------------------------------------------------

interface OfferBadgeProps {
  label: string;
  className?: string;
}

export function OfferBadge({ label, className }: OfferBadgeProps) {
  return (
    <Badge variant="warning" className={cn('text-xs font-semibold', className)}>
      {label}
    </Badge>
  );
}

// ---------------------------------------------------------------------------
// SellerCard — used in discovery list and comparison
// ---------------------------------------------------------------------------

export interface SellerCardData {
  id: string;
  business_name: string;
  display_name?: string | null;
  logo_url?: string | null;
  rating?: number | null;
  review_count?: number | null;
  /** Starting-from price string e.g. "₹49/kg" */
  price_from?: string | null;
  turnaround_label?: string | null;
  pickup_available?: boolean;
  delivery_available?: boolean;
  is_verified?: boolean;
  offers?: string[];
}

interface SellerCardProps {
  seller: SellerCardData;
  onSelect?: (id: string) => void;
  onCompare?: (id: string) => void;
  isCompared?: boolean;
  className?: string;
}

export function SellerCard({ seller, onSelect, onCompare, isCompared, className }: SellerCardProps) {
  const name = seller.display_name ?? seller.business_name;
  return (
    <Card
      className={cn('group cursor-pointer transition-shadow hover:shadow-md', className)}
      role="article"
      aria-label={`Seller: ${name}`}
    >
      <CardContent className="p-4">
        <div className="flex items-start gap-3">
          {/* Logo */}
          <Avatar className="h-12 w-12 rounded-lg flex-shrink-0">
            <AvatarImage src={seller.logo_url ?? undefined} alt={name} />
            <AvatarFallback className="rounded-lg text-sm font-bold bg-primary/10 text-primary">
              {name.slice(0, 2).toUpperCase()}
            </AvatarFallback>
          </Avatar>

          {/* Info */}
          <div className="min-w-0 flex-1">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <h3 className="truncate text-sm font-semibold text-foreground">{name}</h3>
                {seller.is_verified && (
                  <span className="inline-flex items-center gap-0.5 text-xs text-accent">
                    <CheckCircle2 className="h-3 w-3" aria-hidden />
                    Verified
                  </span>
                )}
              </div>
              <RatingDisplay rating={seller.rating} reviewCount={seller.review_count} />
            </div>

            {/* Price + turnaround */}
            <div className="mt-1.5 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              {seller.price_from && (
                <span className="font-medium text-foreground">From {seller.price_from}</span>
              )}
              {seller.turnaround_label && (
                <span className="flex items-center gap-0.5">
                  <Clock className="h-3 w-3" aria-hidden />
                  {seller.turnaround_label}
                </span>
              )}
            </div>

            {/* Pickup / Delivery */}
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {seller.pickup_available != null && (
                <AvailabilityBadge available={seller.pickup_available} label="Pickup" />
              )}
              {seller.delivery_available != null && (
                <AvailabilityBadge available={seller.delivery_available} label="Delivery" />
              )}
              {seller.offers?.slice(0, 1).map((o, i) => (
                <OfferBadge key={i} label={o} />
              ))}
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="mt-3 flex gap-2">
          {onSelect && (
            <button
              onClick={() => onSelect(seller.id)}
              className="flex-1 rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              View Seller
            </button>
          )}
          {onCompare && (
            <button
              onClick={() => onCompare(seller.id)}
              aria-pressed={isCompared}
              className={cn(
                'rounded-md border px-3 py-1.5 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                isCompared
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'border-input bg-background text-foreground hover:bg-muted'
              )}
            >
              {isCompared ? 'Remove' : 'Compare'}
            </button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// ServiceCard
// ---------------------------------------------------------------------------

export interface ServiceCardData {
  id: string;
  name: string;
  description?: string | null;
  image_url?: string | null;
  category_name?: string;
  price_from?: string | null;
  unit_label?: string | null;
  turnaround_label?: string | null;
}

interface ServiceCardProps {
  service: ServiceCardData;
  onSelect?: (id: string) => void;
  className?: string;
}

export function ServiceCard({ service, onSelect, className }: ServiceCardProps) {
  return (
    <Card
      className={cn('group cursor-pointer overflow-hidden transition-shadow hover:shadow-md', className)}
      role="article"
    >
      {service.image_url && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={service.image_url}
          alt={service.name}
          className="h-32 w-full object-cover"
        />
      )}
      <CardContent className="p-4">
        {service.category_name && (
          <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {service.category_name}
          </p>
        )}
        <h3 className="font-semibold text-foreground">{service.name}</h3>
        {service.description && (
          <p className="mt-1 text-sm text-muted-foreground">{truncate(service.description, 80)}</p>
        )}
        <div className="mt-2 flex items-center justify-between">
          <div className="flex flex-col">
            {service.price_from && (
              <span className="text-sm font-semibold text-foreground">
                {service.price_from}
                {service.unit_label && <span className="text-xs font-normal text-muted-foreground"> / {service.unit_label}</span>}
              </span>
            )}
            {service.turnaround_label && (
              <span className="flex items-center gap-0.5 text-xs text-muted-foreground">
                <Clock className="h-3 w-3" aria-hidden />
                {service.turnaround_label}
              </span>
            )}
          </div>
          {onSelect && (
            <button
              onClick={() => onSelect(service.id)}
              className="rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              Select
            </button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// OrderStatusBadge
// ---------------------------------------------------------------------------

const ORDER_STATUS_CONFIG: Record<OrderStatus, { label: string; variant: 'default' | 'secondary' | 'success' | 'warning' | 'destructive' | 'outline' }> = {
  DRAFT:       { label: 'Draft',       variant: 'secondary' },
  PENDING:     { label: 'Pending',     variant: 'warning' },
  CONFIRMED:   { label: 'Confirmed',   variant: 'default' },
  IN_PROGRESS: { label: 'In Progress', variant: 'accent' as 'default' },
  COMPLETED:   { label: 'Completed',   variant: 'success' },
  CANCELLED:   { label: 'Cancelled',   variant: 'destructive' },
};

interface OrderStatusBadgeProps {
  status: OrderStatus;
  className?: string;
}

export function OrderStatusBadge({ status, className }: OrderStatusBadgeProps) {
  const cfg = ORDER_STATUS_CONFIG[status] ?? { label: status, variant: 'outline' as const };
  return (
    <Badge variant={cfg.variant as Parameters<typeof Badge>[0]['variant']} className={className}>
      {cfg.label}
    </Badge>
  );
}

// ---------------------------------------------------------------------------
// OrderTimeline
// ---------------------------------------------------------------------------

export interface TimelineEvent {
  label: string;
  timestamp?: string | null;
  isCompleted: boolean;
  isCurrent?: boolean;
}

interface OrderTimelineProps {
  events: TimelineEvent[];
  className?: string;
}

export function OrderTimeline({ events, className }: OrderTimelineProps) {
  return (
    <ol className={cn('relative border-l border-border pl-6', className)} aria-label="Order timeline">
      {events.map((event, idx) => (
        <li key={idx} className="mb-6 last:mb-0">
          <span
            className={cn(
              'absolute -left-[9px] flex h-4 w-4 items-center justify-center rounded-full border-2',
              event.isCurrent
                ? 'border-accent bg-accent text-accent-foreground'
                : event.isCompleted
                ? 'border-primary bg-primary text-primary-foreground'
                : 'border-border bg-background'
            )}
            aria-hidden
          >
            {event.isCurrent ? (
              <Loader2 className="h-2.5 w-2.5 animate-spin" />
            ) : event.isCompleted ? (
              <CheckCircle2 className="h-2.5 w-2.5" />
            ) : (
              <Circle className="h-2.5 w-2.5 text-muted-foreground" />
            )}
          </span>
          <div className="ml-2">
            <p className={cn('text-sm font-medium', event.isCompleted || event.isCurrent ? 'text-foreground' : 'text-muted-foreground')}>
              {event.label}
            </p>
            {event.timestamp && (
              <p className="text-xs text-muted-foreground">
                {new Date(event.timestamp).toLocaleString('en-IN', {
                  day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
                })}
              </p>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
}

// ---------------------------------------------------------------------------
// CartItemRow
// ---------------------------------------------------------------------------

export interface CartItemRowProps {
  name: string;
  unit: string;
  quantity: number;
  unitPrice: string;
  total: string;
  currency?: string;
  addons?: Array<{ name: string; quantity: number; total: string }>;
  onRemove?: () => void;
  onEdit?: () => void;
}

export function CartItemRow({
  name, unit, quantity, unitPrice, total, currency = 'INR', addons, onRemove, onEdit,
}: CartItemRowProps) {
  return (
    <div className="flex items-start justify-between gap-2 py-3">
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-foreground">{name}</p>
        <p className="text-xs text-muted-foreground">
          {quantity} {unit} × {formatCurrency(unitPrice, currency)}
        </p>
        {addons?.map((a, i) => (
          <p key={i} className="text-xs text-muted-foreground">
            + {a.name} × {a.quantity}
          </p>
        ))}
      </div>
      <div className="flex flex-col items-end gap-1">
        <span className="text-sm font-semibold">{formatCurrency(total, currency)}</span>
        <div className="flex gap-1">
          {onEdit && (
            <button onClick={onEdit} className="text-xs text-accent hover:underline">Edit</button>
          )}
          {onRemove && (
            <button onClick={onRemove} className="text-xs text-destructive hover:underline">Remove</button>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// AddressCard
// ---------------------------------------------------------------------------

export interface AddressCardData {
  id: string;
  label?: string | null;
  recipient_name?: string | null;
  address_line_1: string;
  address_line_2?: string | null;
  locality?: string | null;
  city: string;
  state: string;
  postal_code: string;
  is_default: boolean;
}

interface AddressCardProps {
  address: AddressCardData;
  isSelected?: boolean;
  onSelect?: (id: string) => void;
  onEdit?: (id: string) => void;
  onDelete?: (id: string) => void;
  className?: string;
}

export function AddressCard({ address, isSelected, onSelect, onEdit, onDelete, className }: AddressCardProps) {
  return (
    <div
      className={cn(
        'rounded-xl border p-4 transition-colors',
        isSelected ? 'border-primary bg-primary/5' : 'border-border bg-card',
        onSelect && 'cursor-pointer hover:border-primary/50',
        className
      )}
      role={onSelect ? 'button' : undefined}
      tabIndex={onSelect ? 0 : undefined}
      onClick={() => onSelect?.(address.id)}
      onKeyDown={(e) => e.key === 'Enter' && onSelect?.(address.id)}
      aria-pressed={onSelect ? isSelected : undefined}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2">
          <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
          <div className="text-sm">
            <p className="font-medium text-foreground">
              {address.label ?? 'Address'}
              {address.is_default && (
                <Badge variant="secondary" className="ml-2 text-xs">Default</Badge>
              )}
            </p>
            {address.recipient_name && <p className="text-muted-foreground">{address.recipient_name}</p>}
            <p className="text-muted-foreground">{address.address_line_1}</p>
            {address.address_line_2 && <p className="text-muted-foreground">{address.address_line_2}</p>}
            <p className="text-muted-foreground">
              {[address.locality, address.city, address.state, address.postal_code].filter(Boolean).join(', ')}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          {onEdit && (
            <button
              onClick={(e) => { e.stopPropagation(); onEdit(address.id); }}
              className="text-xs text-accent hover:underline"
              aria-label={`Edit ${address.label ?? 'address'}`}
            >
              Edit
            </button>
          )}
          {onDelete && (
            <button
              onClick={(e) => { e.stopPropagation(); onDelete(address.id); }}
              className="text-xs text-destructive hover:underline"
              aria-label={`Delete ${address.label ?? 'address'}`}
            >
              Delete
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Skeletons for common loading states
// ---------------------------------------------------------------------------

export function SellerCardSkeleton() {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex gap-3">
          <Skeleton className="h-12 w-12 rounded-lg flex-shrink-0" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
            <Skeleton className="h-3 w-2/3" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function ServiceCardSkeleton() {
  return (
    <Card className="overflow-hidden">
      <Skeleton className="h-32 w-full rounded-none" />
      <CardContent className="p-4 space-y-2">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-1/2" />
      </CardContent>
    </Card>
  );
}
