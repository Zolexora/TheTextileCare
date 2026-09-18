import type { TenantContext, TenantResolver } from './types';

export class PlaceholderTenantResolver implements TenantResolver {
  async resolveFromUser(): Promise<TenantContext | null> {
    return null;
  }

  async resolveFromDomain(): Promise<TenantContext | null> {
    return null;
  }

  async resolveFromApplication(): Promise<TenantContext | null> {
    return null;
  }
}
