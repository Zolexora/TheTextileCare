export interface TenantContext {
  id: string;
  slug: string;
  name: string;
  domain?: string;
}

export interface TenantResolver {
  resolveFromUser(user: unknown): Promise<TenantContext | null>;
  resolveFromDomain(domain: string): Promise<TenantContext | null>;
  resolveFromApplication(applicationId: string): Promise<TenantContext | null>;
}
