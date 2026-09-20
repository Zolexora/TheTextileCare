'use client';

import { Bell } from 'lucide-react';
import { EmptyState } from '@/components/ui';

export default function NotificationsPage() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-10 sm:px-6 lg:px-8">
      <h1 className="mb-6 text-xl font-bold text-foreground">Notifications</h1>
      <EmptyState
        icon={<Bell className="h-10 w-10 text-muted-foreground" />}
        title="No notifications"
        description="Order updates, offers, and account alerts will appear here."
      />
    </div>
  );
}
