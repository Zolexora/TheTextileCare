/**
 * Authentication helpers for marketplace-web.
 * Thin wrappers over @ttc/auth that work with Next.js cookies/server components.
 *
 * Auth is intentionally not a prerequisite for browsing — guests can view
 * sellers, services, and prices without logging in.
 */

'use client';

import { createContext, useContext } from 'react';
import type { AuthUser, AuthSession } from '@ttc/auth';

export type { AuthUser, AuthSession };

export interface AuthContextValue {
  user: AuthUser | null;
  session: AuthSession | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  /** Access token for API calls, null for guests */
  token: string | null;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  signUp: (email: string, password: string, name?: string) => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue>({
  user: null,
  session: null,
  isLoading: false,
  isAuthenticated: false,
  token: null,
  signIn: async () => {},
  signOut: async () => {},
  signUp: async () => {},
});

export function useAuth(): AuthContextValue {
  return useContext(AuthContext);
}
