/**
 * Marketplace homepage — page-builder-driven sections.
 * SSR for SEO. Location-aware content.
 */

import type { Metadata } from 'next';
import { HomepageClient } from './homepage-client';

export const metadata: Metadata = {
  title: 'Professional Laundry & Dry Cleaning Near You',
  description:
    'Book laundry, dry cleaning, and garment care from verified sellers. Easy pickup and delivery to your door.',
};

export default function HomePage() {
  return <HomepageClient />;
}
