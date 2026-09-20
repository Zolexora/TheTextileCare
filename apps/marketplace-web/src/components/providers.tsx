/**
 * Root providers — wraps the entire app with:
 *  - TanStack Query client
 *  - ThemeProvider
 *  - AuthProvider (placeholder until real auth is wired)
 *  - Toast notification provider
 */

'use client';

import React, { useState, useCallback } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from 'next-themes';
import { Toaster } from 'sonner';
import { AuthContext, type AuthContextValue } from '@/lib/auth-context';
import type { AuthUser, AuthSession } from '@ttc/auth';

function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60_000,
        retry: (failureCount, error: unknown) => {
          // Don't retry on 4xx client errors
          const status = (error as { status?: number })?.status;
          if (status && status >= 400 && status < 500) return false;
          return failureCount < 2;
        },
        refetchOnWindowFocus: false,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

// Singleton on server, fresh on client (HMR-safe)
let browserQueryClient: QueryClient | undefined;

function getQueryClient(): QueryClient {
  if (typeof window === 'undefined') return makeQueryClient();
  if (!browserQueryClient) browserQueryClient = makeQueryClient();
  return browserQueryClient;
}

// ---------------------------------------------------------------------------
// Placeholder auth provider — replace with real OAuth/JWT implementation
// ponytail: placeholder auth, wire real provider when auth backend is ready
// ---------------------------------------------------------------------------

function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [session, setSession] = useState<AuthSession | null>(null);
  const [isLoading] = useState(false);

  const signIn = useCallback(async (email: string, _password?: string) => {
    void _password;
    // ponytail: placeholder — replace with actual auth API call
    const fakeUser: AuthUser = { id: 'guest', email, name: email.split('@')[0] };
    const fakeSession: AuthSession = { accessToken: 'placeholder', user: fakeUser };
    setUser(fakeUser);
    setSession(fakeSession);
  }, []);

  const signOut = useCallback(async () => {
    setUser(null);
    setSession(null);
  }, []);

  const signUp = useCallback(async (email: string, _password?: string, name?: string) => {
    void _password;
    const fakeUser: AuthUser = { id: 'guest', email, name: name ?? email.split('@')[0] };
    const fakeSession: AuthSession = { accessToken: 'placeholder', user: fakeUser };
    setUser(fakeUser);
    setSession(fakeSession);
  }, []);

  const value: AuthContextValue = {
    user,
    session,
    isLoading,
    isAuthenticated: !!user,
    token: session?.accessToken ?? null,
    signIn,
    signOut,
    signUp,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// ---------------------------------------------------------------------------
// Root providers
// ---------------------------------------------------------------------------

export function Providers({ children }: { children: React.ReactNode }) {
  const queryClient = getQueryClient();

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider
        attribute="class"
        defaultTheme="system"
        enableSystem
        disableTransitionOnChange
      >
        <AuthProvider>
          {children}
          <Toaster position="top-right" richColors closeButton />
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
