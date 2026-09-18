export type PlatformRole = 'PLATFORM_ADMIN' | 'PLATFORM_SUPPORT';
export type TenantRole = 'TENANT_OWNER' | 'TENANT_ADMIN' | 'TENANT_MEMBER' | 'TENANT_VIEWER';
export type RoleName = PlatformRole | TenantRole;

export type PermissionName =
  | 'tenant.read'
  | 'tenant.manage'
  | 'membership.read'
  | 'membership.manage'
  | 'role.read'
  | 'role.manage'
  | 'user.read'
  | 'user.manage'
  | 'audit.read';

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  status: 'ACTIVE' | 'SUSPENDED' | 'INACTIVE';
  createdAt: string;
  updatedAt: string;
}

export interface Membership {
  id: string;
  tenantId: string;
  userId: string;
  roleId: string;
  role: RoleName | string;
  status: 'ACTIVE' | 'SUSPENDED' | 'INACTIVE';
  email?: string;
  name?: string;
  createdAt: string;
  updatedAt: string;
}

export interface AuditEvent {
  id: string;
  tenantId?: string | null;
  actorUserId?: string | null;
  eventType: string;
  entityType?: string | null;
  entityId?: string | null;
  payload: Record<string, unknown>;
  createdAt: string;
}
