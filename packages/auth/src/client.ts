import type { AuthProvider, AuthSession, AuthUser } from './types';

export class PlaceholderAuthProvider implements AuthProvider {
  async getSession(): Promise<AuthSession | null> {
    return null;
  }

  async getCurrentUser(): Promise<AuthUser | null> {
    return null;
  }

  async signIn(): Promise<AuthSession | null> {
    return null;
  }

  async signOut(): Promise<void> {
    return;
  }

  async refreshSession(): Promise<AuthSession | null> {
    return null;
  }
}
