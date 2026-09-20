'use client';

import React from 'react';
import { Moon, Sun, Globe, Monitor } from 'lucide-react';
import { useTheme } from 'next-themes';
import { Card, CardContent, Label, RadioGroup, RadioGroupItem } from '@/components/ui';
import { useUIPreferencesStore } from '@/lib/stores';

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const {} = useUIPreferencesStore();

  return (
    <div className="mx-auto max-w-xl px-4 py-6 sm:px-6 lg:px-8 space-y-6">
      <h1 className="text-xl font-bold text-foreground">Settings</h1>

      {/* Theme */}
      <Card>
        <CardContent className="p-5">
          <h2 className="mb-4 text-sm font-semibold text-foreground">Appearance</h2>
          <RadioGroup value={theme ?? 'system'} onValueChange={setTheme} aria-label="Theme">
            <div className="flex items-center gap-3 rounded-lg border border-border p-3">
              <RadioGroupItem value="light" id="light" />
              <Label htmlFor="light" className="flex items-center gap-2 cursor-pointer">
                <Sun className="h-4 w-4" aria-hidden /> Light
              </Label>
            </div>
            <div className="flex items-center gap-3 rounded-lg border border-border p-3">
              <RadioGroupItem value="dark" id="dark" />
              <Label htmlFor="dark" className="flex items-center gap-2 cursor-pointer">
                <Moon className="h-4 w-4" aria-hidden /> Dark
              </Label>
            </div>
            <div className="flex items-center gap-3 rounded-lg border border-border p-3">
              <RadioGroupItem value="system" id="system" />
              <Label htmlFor="system" className="flex items-center gap-2 cursor-pointer">
                <Monitor className="h-4 w-4" aria-hidden /> System
              </Label>
            </div>
          </RadioGroup>
        </CardContent>
      </Card>

      {/* Language — integration boundary for i18n */}
      <Card>
        <CardContent className="p-5">
          <h2 className="mb-4 text-sm font-semibold text-foreground">Language &amp; Region</h2>
          <div className="flex items-center gap-3 rounded-lg border border-border p-3">
            <Globe className="h-4 w-4 text-muted-foreground" aria-hidden />
            <div className="flex-1">
              <p className="text-sm font-medium">English (India)</p>
              <p className="text-xs text-muted-foreground">More languages coming soon</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
