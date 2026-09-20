'use client';

import React, { useState } from 'react';
import { Save } from 'lucide-react';
import { Button, Card, CardContent, Input, Label, Skeleton } from '@/components/ui';
import { useProfile, useUpdateProfile } from '@/lib/queries';
import { useAuth } from '@/lib/auth-context';
import { toast } from 'sonner';
import Link from 'next/link';

export default function ProfilePage() {
  const { isAuthenticated } = useAuth();
  const { data: profile, isLoading } = useProfile();
  const updateProfile = useUpdateProfile();

  const [form, setForm] = useState({
    display_name: '',
    first_name: '',
    last_name: '',
    phone: '',
    email: '',
  });
  const [initialized, setInitialized] = useState(false);

  // Populate form once profile loads
  if (profile && !initialized) {
    setForm({
      display_name: profile.display_name ?? '',
      first_name: profile.first_name ?? '',
      last_name: profile.last_name ?? '',
      phone: profile.phone ?? '',
      email: profile.email ?? '',
    });
    setInitialized(true);
  }

  if (!isAuthenticated) {
    return (
      <div className="mx-auto max-w-md px-4 py-12 text-center">
        <p className="text-sm text-muted-foreground mb-4">Sign in to edit your profile.</p>
        <Link href="/login?redirect=/account/profile"><Button>Sign In</Button></Link>
      </div>
    );
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await updateProfile.mutateAsync({
        display_name: form.display_name || null,
        first_name: form.first_name || null,
        last_name: form.last_name || null,
        phone: form.phone || null,
        email: form.email || null,
      });
      toast.success('Profile updated');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to update profile');
    }
  };

  return (
    <div className="mx-auto max-w-xl px-4 py-6 sm:px-6 lg:px-8">
      <h1 className="mb-6 text-xl font-bold text-foreground">Edit Profile</h1>

      {isLoading ? (
        <Card><CardContent className="p-6 space-y-4">
          {Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-10 w-full" />)}
        </CardContent></Card>
      ) : (
        <Card>
          <CardContent className="p-6">
            <form onSubmit={handleSave} className="space-y-4">
              <div>
                <Label htmlFor="display_name">Display Name</Label>
                <Input
                  id="display_name"
                  value={form.display_name}
                  onChange={(e) => setForm((f) => ({ ...f, display_name: e.target.value }))}
                  placeholder="How should we call you?"
                  className="mt-1"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label htmlFor="first_name">First Name</Label>
                  <Input id="first_name" value={form.first_name} onChange={(e) => setForm((f) => ({ ...f, first_name: e.target.value }))} className="mt-1" />
                </div>
                <div>
                  <Label htmlFor="last_name">Last Name</Label>
                  <Input id="last_name" value={form.last_name} onChange={(e) => setForm((f) => ({ ...f, last_name: e.target.value }))} className="mt-1" />
                </div>
              </div>
              <div>
                <Label htmlFor="email">Email</Label>
                <Input id="email" type="email" value={form.email} onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))} className="mt-1" />
              </div>
              <div>
                <Label htmlFor="phone">Phone</Label>
                <Input id="phone" type="tel" value={form.phone} onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))} placeholder="+91 XXXXX XXXXX" className="mt-1" />
              </div>

              <Button type="submit" isLoading={updateProfile.isPending} className="w-full">
                <Save className="mr-2 h-4 w-4" aria-hidden />
                Save Changes
              </Button>
            </form>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
