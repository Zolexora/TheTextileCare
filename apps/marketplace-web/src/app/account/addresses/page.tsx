'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { Plus, MapPin } from 'lucide-react';
import { Button, Dialog, DialogContent, DialogHeader, DialogTitle, Input, Label, Skeleton, EmptyState } from '@/components/ui';
import { AddressCard } from '@/components/marketplace';
import { useAddresses, useCreateAddress, useUpdateAddress, useDeleteAddress } from '@/lib/queries';
import { useAuth } from '@/lib/auth-context';
import type { CustomerAddress, CustomerAddressCreate } from '@ttc/types';
import { toast } from 'sonner';

function AddressForm({
  initial,
  onSave,
  onCancel,
}: {
  initial?: Partial<CustomerAddressCreate>;
  onSave: (data: CustomerAddressCreate) => Promise<void>;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<CustomerAddressCreate>({
    address_line_1: initial?.address_line_1 ?? '',
    address_line_2: initial?.address_line_2 ?? '',
    locality: initial?.locality ?? '',
    city: initial?.city ?? '',
    state: initial?.state ?? '',
    postal_code: initial?.postal_code ?? '',
    country: initial?.country ?? 'IN',
    label: initial?.label ?? '',
    recipient_name: initial?.recipient_name ?? '',
    phone: initial?.phone ?? '',
    is_default: initial?.is_default ?? false,
  });
  const [saving, setSaving] = useState(false);

  const set = (k: keyof CustomerAddressCreate, v: string | boolean) =>
    setForm((f: CustomerAddressCreate) => ({ ...f, [k]: v }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await onSave(form);
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label htmlFor="label">Label (e.g. Home, Work)</Label>
          <Input id="label" value={form.label ?? ''} onChange={(e) => set('label', e.target.value)} placeholder="Home" className="mt-1" />
        </div>
        <div>
          <Label htmlFor="recipient">Recipient Name</Label>
          <Input id="recipient" value={form.recipient_name ?? ''} onChange={(e) => set('recipient_name', e.target.value)} placeholder="Name" className="mt-1" />
        </div>
      </div>
      <div>
        <Label htmlFor="pincode">Pincode <span className="text-destructive" aria-hidden>*</span></Label>
        <Input id="pincode" value={form.postal_code} onChange={(e) => set('postal_code', e.target.value)} placeholder="6-digit pincode" maxLength={6} required className="mt-1" />
      </div>
      <div>
        <Label htmlFor="locality">Locality / Area</Label>
        <Input id="locality" value={form.locality ?? ''} onChange={(e) => set('locality', e.target.value)} placeholder="Area / Post office" className="mt-1" />
      </div>
      <div>
        <Label htmlFor="address1">House / Flat / Building <span className="text-destructive" aria-hidden>*</span></Label>
        <Input id="address1" value={form.address_line_1} onChange={(e) => set('address_line_1', e.target.value)} placeholder="Flat no., building name" required className="mt-1" />
      </div>
      <div>
        <Label htmlFor="address2">Landmark (optional)</Label>
        <Input id="address2" value={form.address_line_2 ?? ''} onChange={(e) => set('address_line_2', e.target.value)} placeholder="Near landmark" className="mt-1" />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label htmlFor="city">City <span className="text-destructive" aria-hidden>*</span></Label>
          <Input id="city" value={form.city} onChange={(e) => set('city', e.target.value)} required className="mt-1" />
        </div>
        <div>
          <Label htmlFor="state">State <span className="text-destructive" aria-hidden>*</span></Label>
          <Input id="state" value={form.state} onChange={(e) => set('state', e.target.value)} required className="mt-1" />
        </div>
      </div>
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="default"
          checked={form.is_default ?? false}
          onChange={(e) => set('is_default', e.target.checked)}
          className="rounded"
        />
        <Label htmlFor="default">Set as default address</Label>
      </div>
      <div className="flex gap-2 justify-end pt-2">
        <Button type="button" variant="outline" onClick={onCancel}>Cancel</Button>
        <Button type="submit" isLoading={saving}>Save Address</Button>
      </div>
    </form>
  );
}

export default function AddressesPage() {
  const { isAuthenticated } = useAuth();
  const { data: addresses, isLoading } = useAddresses();
  const createAddress = useCreateAddress();
  const updateAddress = useUpdateAddress();
  const deleteAddress = useDeleteAddress();

  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<CustomerAddress | null>(null);

  if (!isAuthenticated) {
    return (
      <div className="mx-auto max-w-md px-4 py-12 text-center">
        <MapPin className="mx-auto mb-4 h-12 w-12 text-muted-foreground" aria-hidden />
        <p className="text-sm text-muted-foreground mb-4">Sign in to manage addresses.</p>
        <Link href="/login?redirect=/account/addresses"><Button>Sign In</Button></Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-6 sm:px-6 lg:px-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold text-foreground">Saved Addresses</h1>
        <Button size="sm" onClick={() => setAdding(true)}>
          <Plus className="mr-1.5 h-4 w-4" aria-hidden />
          Add New
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 2 }, (_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)}
        </div>
      ) : !addresses?.length ? (
        <EmptyState
          icon={<MapPin className="h-10 w-10 text-muted-foreground" />}
          title="No saved addresses"
          description="Add an address for faster checkout."
          action={<Button onClick={() => setAdding(true)}>Add Address</Button>}
        />
      ) : (
        <div className="space-y-3">
          {addresses.map((addr) => (
            <AddressCard
              key={addr.id}
              address={addr}
              onEdit={(id) => setEditing(addresses.find((a) => a.id === id) ?? null)}
              onDelete={async (id) => {
                await deleteAddress.mutateAsync(id);
                toast.success('Address deleted');
              }}
            />
          ))}
        </div>
      )}

      {/* Add dialog */}
      <Dialog open={adding} onOpenChange={setAdding}>
        <DialogContent>
          <DialogHeader><DialogTitle>Add New Address</DialogTitle></DialogHeader>
          <AddressForm
            onSave={async (data) => {
              await createAddress.mutateAsync(data);
              toast.success('Address added');
              setAdding(false);
            }}
            onCancel={() => setAdding(false)}
          />
        </DialogContent>
      </Dialog>

      {/* Edit dialog */}
      <Dialog open={!!editing} onOpenChange={(open) => !open && setEditing(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>Edit Address</DialogTitle></DialogHeader>
          {editing && (
            <AddressForm
              initial={editing}
              onSave={async (data) => {
                await updateAddress.mutateAsync({ id: editing.id, body: data });
                toast.success('Address updated');
                setEditing(null);
              }}
              onCancel={() => setEditing(null)}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
