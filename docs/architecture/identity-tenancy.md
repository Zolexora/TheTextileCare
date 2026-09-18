# Architecture: Identity, Tenancy & Membership Foundation (Phase 1)

## Overview

The Textile Care (TTC) multi-tenant architecture establishes an authoritative hierarchy for user authentication, platform user records, tenant tenancy, tenant memberships, roles, and fine-grained permissions:

```text
Platform
   │
   ├── User (Platform User mapped to Supabase Auth UID)
   │
   ├── Organization / Tenant
   │
   └── Membership (Scattered many-to-many relationship)
          │
          └── Role (Platform vs. Tenant Scope)
                 │
                 └── Permissions (Explicit permission strings)
```

> [!IMPORTANT]
> **Deferred to Later Phases**:
> Seller platform, branches, staff hierarchies, catalog, pricing, marketplace, driver platform, white-label engines, and app factory are explicitly deferred to Phase 2 and beyond.

---

## 1. Identity Model

- **Authentication Provider**: Supabase Auth serves as the single authority for identity issuance, token signing, session lifecycle, and credential security.
- **No Password Duplication**: Passwords, refresh tokens, and authentication secrets are never stored in the application database tables.
- **Platform User Mapping**: The local `users` table records platform identity tied to the external `auth_user_id` (Supabase UID), storing `email`, `name`, and user `status` (`ACTIVE`, `SUSPENDED`, `INACTIVE`).
- **Auto-Provisioning**: Upon first authenticated API request verified by JWT token or trusted integration headers, platform user records are idempotently synchronized or provisioned.

---

## 2. Tenancy & Tenant Resolution

A tenant is an isolated boundary representing an organization, brand, or business entity on The Textile Care platform.

### Tenant Model
- `id`: UUID (Primary Key)
- `name`: Organization name (e.g., "Alpha Cleaners")
- `slug`: Unique slug identifier (e.g., "alpha-cleaners")
- `status`: Lifecycle state (`ACTIVE`, `SUSPENDED`, `INACTIVE`)
- `created_at`, `updated_at`: UTC timestamps

### Multi-Tenancy Resolution Flow
1. **Server-Side Authentication**: The incoming request extracts the caller's identity (`get_current_user`).
2. **Tenant Context Determination**:
   - The caller specifies a target tenant via the `X-Tenant-Id` header (or explicit URL parameter in scoped endpoints).
   - If omitted, the server checks the user's active tenant memberships and defaults to their primary active tenant.
3. **Strict Validation**:
   - The server verifies that the authenticated user possesses an active membership in the requested tenant.
   - Platform roles (`PLATFORM_ADMIN`, `PLATFORM_SUPPORT`) may access tenant contexts in administrative or support modes without arbitrary tenant membership creation.
   - Any request targeting an unassociated tenant is denied with HTTP 403 (or 404 to avoid leaking tenant existence).

---

## 3. Membership Model & Multi-Tenant Users

Users can belong to multiple tenants simultaneously, holding different roles across tenants:

```text
User A
 ├── Tenant 1 (Alpha)  ──> TENANT_OWNER
 └── Tenant 2 (Beta)   ──> TENANT_MEMBER
```

### Invariants & Protection
- **Composite Uniqueness**: Database constraint `uq_tenant_user_membership` on `(tenant_id, user_id)` guarantees that a user cannot have duplicate active memberships in the same tenant.
- **Tenant Owner Protection**: Every tenant must maintain at least one active `TENANT_OWNER`. Deletion, deactivation, or demotion of the final owner is rejected (`LAST_OWNER_PROTECTION`).
- **Self-Role Modification Protection**: A tenant user cannot modify their own membership role (`SELF_ROLE_MODIFICATION_DENIED`).
- **Platform Role Isolation**: Tenant administrators cannot assign platform roles (`PLATFORM_ADMIN`, `PLATFORM_SUPPORT`) under any circumstances.

---

## 4. API Endpoints for Tenancy & Identity

| Method | Path | Required Permission | Description |
|---|---|---|---|
| `GET` | `/api/v1/auth/me` | Authenticated | Retrieve current user profile and memberships |
| `GET` | `/api/v1/tenants` | Authenticated | List all accessible tenants for the caller |
| `POST` | `/api/v1/tenants` | Authenticated | Create a new tenant (creator becomes `TENANT_OWNER`) |
| `GET` | `/api/v1/tenants/current` | `tenant.read` | Get details of currently active tenant |
| `PATCH` | `/api/v1/tenants/current` | `tenant.manage` | Update details of currently active tenant |
| `GET` | `/api/v1/tenants/current/members` | `membership.read` | List roster of current tenant members |
| `POST` | `/api/v1/tenants/current/members` | `membership.manage` | Add a member to current tenant |
| `PATCH` | `/api/v1/tenants/current/members/{id}` | `membership.manage` | Update role or status of tenant member |
| `DELETE` | `/api/v1/tenants/current/members/{id}` | `membership.manage` | Remove member from current tenant |
| `GET` | `/api/v1/roles` | `role.read` | View available system roles and permissions |
| `GET` | `/api/v1/tenants/current/audit-logs` | `audit.read` | View audit trail for current tenant |
