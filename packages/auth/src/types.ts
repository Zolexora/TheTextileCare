export interface AuthUser {
  id: string;
  email?: string;
  name?: string;
}

export interface AuthSession {
  accessToken?: string;
  refreshToken?: string;
  expiresAt?: string;
  user?: AuthUser;
}

export interface AuthProvider {
  getSession(): Promise<AuthSession | null>;
  getCurrentUser(): Promise<AuthUser | null>;
  signIn(): Promise<AuthSession | null>;
  signOut(): Promise<void>;
  refreshSession(): Promise<AuthSession | null>;
}
