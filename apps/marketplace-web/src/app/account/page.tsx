'use client';

import React from 'react';
import Link from 'next/link';
import { User, MapPin, Package, Heart, Tag, Bell, HelpCircle, Settings, ChevronRight } from 'lucide-react';
import { Card, CardContent, Skeleton } from '@/components/ui';
import { useProfile } from '@/lib/queries';
import { useAuth } from '@/lib/auth-context';
import { getInitials } from '@/lib/utils';
import { Avatar, AvatarFallback } from '@/components/ui';

const ACCOUNT_MENU = [
  { href: '/account/profile',     label: 'Profile',       icon: User,       desc: 'Edit personal information' },
  { href: '/account/addresses',   label: 'Addresses',     icon: MapPin,     desc: 'Manage delivery addresses' },
  { href: '/orders',              label: 'Orders',        icon: Package,    desc: 'View order history' },
  { href: '/account/favorites',   label: 'Saved',         icon: Heart,      desc: 'Favourites & collections' },
  { href: '/account/offers',      label: 'Offers',        icon: Tag,        desc: 'Coupons & promotions' },
  { href: '/account/notifications', label: 'Notifications', icon: Bell,    desc: 'Manage preferences' },
  { href: '/account/support',     label: 'Help & Support', icon: HelpCircle, desc: 'FAQs and contact us' },
  { href: '/account/settings',    label: 'Settings',      icon: Settings,   desc: 'Theme, language, preferences' },
];

export default function AccountPage() {
  const { isAuthenticated, user, signOut } = useAuth();
  const { data: profile, isLoading } = useProfile();

  const displayName = profile?.display_name ?? user?.name ?? user?.email ?? 'Account';
  const initials = getInitials(displayName);

  if (!isAuthenticated) {
    return (
      <div className="mx-auto max-w-md px-4 py-12 sm:px-6 lg:px-8 text-center">
        <User className="mx-auto mb-4 h-12 w-12 text-muted-foreground" aria-hidden />
        <h1 className="text-xl font-bold text-foreground mb-2">My Account</h1>
        <p className="text-sm text-muted-foreground mb-6">Sign in to access your account.</p>
        <Link href="/login">
          <div className="inline-flex h-10 items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90">
            Sign In
          </div>
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-6 sm:px-6 lg:px-8">
      {/* Profile header */}
      <div className="mb-6 flex items-center gap-4">
        <Avatar className="h-16 w-16">
          <AvatarFallback className="text-xl font-bold bg-primary text-primary-foreground">
            {initials}
          </AvatarFallback>
        </Avatar>
        <div>
          {isLoading ? (
            <>
              <Skeleton className="h-5 w-32 mb-1" />
              <Skeleton className="h-4 w-48" />
            </>
          ) : (
            <>
              <h1 className="text-lg font-bold text-foreground">{displayName}</h1>
              <p className="text-sm text-muted-foreground">{user?.email}</p>
            </>
          )}
        </div>
      </div>

      {/* Menu */}
      <nav aria-label="Account menu">
        <ul className="space-y-2">
          {ACCOUNT_MENU.map(({ href, label, icon: Icon, desc }) => (
            <li key={href}>
              <Link href={href}>
                <Card className="cursor-pointer transition-colors hover:bg-muted/50">
                  <CardContent className="flex items-center gap-3 p-4">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted">
                      <Icon className="h-4 w-4 text-foreground" aria-hidden />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-foreground">{label}</p>
                      <p className="text-xs text-muted-foreground">{desc}</p>
                    </div>
                    <ChevronRight className="h-4 w-4 text-muted-foreground flex-shrink-0" aria-hidden />
                  </CardContent>
                </Card>
              </Link>
            </li>
          ))}
        </ul>
      </nav>

      {/* Sign out */}
      <button
        onClick={() => signOut()}
        className="mt-6 w-full rounded-xl border border-destructive/30 py-3 text-sm font-medium text-destructive transition-colors hover:bg-destructive/5"
        aria-label="Sign out of your account"
      >
        Sign Out
      </button>
    </div>
  );
}
