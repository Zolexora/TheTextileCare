/**
 * Marketplace navigation — top header + mobile bottom nav.
 * Mobile-first, sticky on scroll.
 */

'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Home, Search, ShoppingCart, User, Heart, MapPin, Menu, X
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from './ui';
import { useAuth } from '@/lib/auth-context';
import { useCartStore, useLocationStore } from '@/lib/stores';
import { Logo } from '@ttc/ui';

// ---------------------------------------------------------------------------
// Top Header
// ---------------------------------------------------------------------------

export function MarketplaceHeader() {
  const { isAuthenticated } = useAuth();
  const totalItems = useCartStore((s) => s.getTotalItemCount());
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const pathname = usePathname();

  const navLinks = [
    { href: '/', label: 'Home' },
    { href: '/search', label: 'Explore' },
    { href: '/sellers', label: 'Sellers' },
  ];

  return (
    <header className="sticky top-0 z-40 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Logo */}
        <Link href="/" aria-label="The Textile Care — Home" className="flex shrink-0 items-center">
          <Logo theme="light" size="sm" className="dark:hidden" />
          <Logo theme="dark" size="sm" className="hidden dark:block" />
        </Link>

        {/* Location pill — desktop */}
        <LocationPill className="hidden sm:flex" />

        {/* Desktop nav */}
        <nav className="hidden items-center gap-6 md:flex" aria-label="Main navigation">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                'text-sm font-medium transition-colors hover:text-primary',
                pathname === link.href ? 'text-primary' : 'text-muted-foreground'
              )}
            >
              {link.label}
            </Link>
          ))}
        </nav>

        {/* Actions */}
        <div className="flex items-center gap-2">
          {/* Search — icon on mobile */}
          <Link href="/search" aria-label="Search" className="md:hidden">
            <Button variant="ghost" size="icon">
              <Search className="h-5 w-5" />
            </Button>
          </Link>

          {/* Cart */}
          <Link href="/cart" aria-label={`Cart, ${totalItems} items`} className="relative">
            <Button variant="ghost" size="icon">
              <ShoppingCart className="h-5 w-5" />
              {totalItems > 0 && (
                <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-accent text-[10px] font-bold text-accent-foreground">
                  {totalItems > 99 ? '99+' : totalItems}
                </span>
              )}
            </Button>
          </Link>

          {/* Auth */}
          {isAuthenticated ? (
            <Link href="/account" aria-label="Account">
              <Button variant="ghost" size="icon">
                <User className="h-5 w-5" />
              </Button>
            </Link>
          ) : (
            <Link href="/login" className="hidden sm:block">
              <Button variant="outline" size="sm">Sign In</Button>
            </Link>
          )}

          {/* Mobile menu toggle */}
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={() => setMobileMenuOpen((v) => !v)}
            aria-label={mobileMenuOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={mobileMenuOpen}
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
        </div>
      </div>

      {/* Mobile menu */}
      {mobileMenuOpen && (
        <nav
          className="border-t border-border bg-background px-4 py-4 md:hidden"
          aria-label="Mobile navigation"
        >
          <LocationPill className="mb-3 w-full" />
          <ul className="space-y-1">
            {navLinks.map((link) => (
              <li key={link.href}>
                <Link
                  href={link.href}
                  onClick={() => setMobileMenuOpen(false)}
                  className={cn(
                    'block rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-muted',
                    pathname === link.href ? 'bg-muted text-primary' : 'text-foreground'
                  )}
                >
                  {link.label}
                </Link>
              </li>
            ))}
            {!isAuthenticated && (
              <li>
                <Link
                  href="/login"
                  onClick={() => setMobileMenuOpen(false)}
                  className="block rounded-md px-3 py-2 text-sm font-medium text-foreground hover:bg-muted"
                >
                  Sign In / Register
                </Link>
              </li>
            )}
          </ul>
        </nav>
      )}
    </header>
  );
}

// ---------------------------------------------------------------------------
// Location pill — shows current location context
// ---------------------------------------------------------------------------

function LocationPill({ className }: { className?: string }) {
  const { pincode, city, isSet } = useLocationStore();
  const label = isSet ? (city ?? pincode ?? 'Location set') : 'Set location';

  return (
    <Link
      href="/location"
      className={cn(
        'flex items-center gap-1.5 rounded-full border border-border bg-muted/50 px-3 py-1.5 text-xs transition-colors hover:bg-muted',
        className
      )}
      aria-label={isSet ? `Current location: ${label}` : 'Set your location'}
    >
      <MapPin className="h-3.5 w-3.5 text-accent" aria-hidden />
      <span className="max-w-[120px] truncate font-medium">{label}</span>
    </Link>
  );
}

// ---------------------------------------------------------------------------
// Bottom Navigation (mobile)
// ---------------------------------------------------------------------------

const BOTTOM_NAV = [
  { href: '/',        label: 'Home',    Icon: Home },
  { href: '/search',  label: 'Search',  Icon: Search },
  { href: '/cart',    label: 'Cart',    Icon: ShoppingCart, showBadge: true },
  { href: '/account/favorites', label: 'Saved',   Icon: Heart },
  { href: '/account', label: 'Account', Icon: User },
];

export function BottomNav() {
  const pathname = usePathname();
  const totalItems = useCartStore((s) => s.getTotalItemCount());

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-40 border-t border-border bg-background pb-safe md:hidden"
      aria-label="Bottom navigation"
    >
      <ul className="flex h-16 items-center">
        {BOTTOM_NAV.map(({ href, label, Icon, showBadge }) => {
          const isActive = pathname === href || (href !== '/' && pathname.startsWith(href));
          return (
            <li key={href} className="flex-1">
              <Link
                href={href}
                className={cn(
                  'flex flex-col items-center justify-center gap-0.5 py-2 text-[10px] font-medium transition-colors',
                  isActive ? 'text-primary' : 'text-muted-foreground'
                )}
                aria-current={isActive ? 'page' : undefined}
              >
                <span className="relative">
                  <Icon className="h-5 w-5" aria-hidden />
                  {showBadge && totalItems > 0 && (
                    <span className="absolute -right-2 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-accent text-[9px] font-bold text-accent-foreground">
                      {totalItems > 9 ? '9+' : totalItems}
                    </span>
                  )}
                </span>
                {label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

// ---------------------------------------------------------------------------
// Breadcrumb
// ---------------------------------------------------------------------------

interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface BreadcrumbProps {
  items: BreadcrumbItem[];
  className?: string;
}

export function Breadcrumb({ items, className }: BreadcrumbProps) {
  return (
    <nav aria-label="Breadcrumb" className={className}>
      <ol className="flex flex-wrap items-center gap-1 text-sm text-muted-foreground">
        {items.map((item, idx) => (
          <React.Fragment key={idx}>
            {idx > 0 && <span aria-hidden>/</span>}
            <li>
              {item.href && idx < items.length - 1 ? (
                <Link href={item.href} className="hover:text-foreground hover:underline transition-colors">
                  {item.label}
                </Link>
              ) : (
                <span className="text-foreground font-medium" aria-current={idx === items.length - 1 ? 'page' : undefined}>
                  {item.label}
                </span>
              )}
            </li>
          </React.Fragment>
        ))}
      </ol>
    </nav>
  );
}
