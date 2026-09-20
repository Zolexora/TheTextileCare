'use client';

import React from 'react';
import { useParams, useRouter } from 'next/navigation';
import { ArrowRight } from 'lucide-react';
import { Button, Card, CardContent, Skeleton, EmptyState, Tabs, TabsList, TabsTrigger, TabsContent, Badge } from '@/components/ui';
import { RatingDisplay, ServiceCard, ServiceCardSkeleton } from '@/components/marketplace';
import { useSeller, useServices } from '@/lib/queries';
import { Breadcrumb } from '@/components/navigation';
import Link from 'next/link';

export default function SellerPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const { data: seller, isLoading: sellerLoading, error } = useSeller(id);
  const { data: services, isLoading: servicesLoading } = useServices({ seller_id: id });

  if (sellerLoading) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8 space-y-6">
        <Skeleton className="h-6 w-48" />
        <div className="flex gap-4">
          <Skeleton className="h-20 w-20 rounded-xl flex-shrink-0" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-7 w-48" />
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-4 w-64" />
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }, (_, i) => <ServiceCardSkeleton key={i} />)}
        </div>
      </div>
    );
  }

  if (error || !seller) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <EmptyState
          title="Seller not found"
          description="This seller may no longer be available."
          action={<Link href="/sellers"><Button variant="outline">Browse sellers</Button></Link>}
        />
      </div>
    );
  }

  const name = seller.display_name ?? seller.business_name;

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <Breadcrumb
        className="mb-4"
        items={[
          { label: 'Home', href: '/' },
          { label: 'Sellers', href: '/sellers' },
          { label: name },
        ]}
      />

      {/* Seller header */}
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start">
        {seller.logo_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={seller.logo_url}
            alt={`${name} logo`}
            className="h-20 w-20 rounded-xl object-cover border border-border flex-shrink-0"
          />
        ) : (
          <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-2xl font-bold text-primary">
            {name.slice(0, 2).toUpperCase()}
          </div>
        )}

        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <h1 className="text-2xl font-bold text-foreground">{name}</h1>
              <RatingDisplay rating={null} className="mt-1" />
            </div>
            <Button
              onClick={() => router.push(`/sellers/${id}/order`)}
              className="shrink-0"
            >
              Order Now
              <ArrowRight className="ml-2 h-4 w-4" aria-hidden />
            </Button>
          </div>

          {seller.description && (
            <p className="mt-2 text-sm text-muted-foreground">{seller.description}</p>
          )}

          <div className="mt-3 flex flex-wrap gap-3 text-xs text-muted-foreground">
            <Badge variant="success">Available</Badge>
            <Badge variant="secondary">Pickup</Badge>
            <Badge variant="secondary">Delivery</Badge>
          </div>
        </div>
      </div>

      {/* Tabs: Services / Reviews / Info */}
      <Tabs defaultValue="services">
        <TabsList className="mb-4">
          <TabsTrigger value="services">Services</TabsTrigger>
          <TabsTrigger value="reviews">Reviews</TabsTrigger>
          <TabsTrigger value="info">Info</TabsTrigger>
        </TabsList>

        <TabsContent value="services">
          {servicesLoading ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 4 }, (_, i) => <ServiceCardSkeleton key={i} />)}
            </div>
          ) : !services?.length ? (
            <EmptyState
              title="No services listed"
              description="This seller hasn't published services yet."
            />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {services.map((s) => (
                <ServiceCard
                  key={s.id}
                  service={{
                    id: s.id,
                    name: s.name,
                    description: s.description,
                    image_url: s.image_url,
                  }}
                  onSelect={(sid) => router.push(`/sellers/${id}/services/${sid}`)}
                />
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="reviews">
          <EmptyState
            title="Reviews coming soon"
            description="Customer reviews will appear here after orders are completed."
          />
        </TabsContent>

        <TabsContent value="info">
          <Card>
            <CardContent className="p-6 space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <h3 className="text-sm font-semibold text-foreground mb-2">Operating Hours</h3>
                  <p className="text-sm text-muted-foreground">Contact seller for hours</p>
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-foreground mb-2">Service Areas</h3>
                  <p className="text-sm text-muted-foreground">See serviceability at checkout</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
