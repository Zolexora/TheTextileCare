# Security: RBAC & Tenant Isolation Foundation (Phase 1)

## Core Security Principles

1. **Backend Authoritative**: The server strictly derives tenant identity, user identity, role, and permission sets from verified authentication tokens and database memberships. Client-supplied parameters (such as body IDs or arbitrary headers) are never trusted for authorization.
2. **Strict Tenant Isolation**: All tenant data queries must be filtered by the server-side resolved `tenant_id`. Cross-tenant queries are blocked with HTTP 403 or HTTP 404 to avoid leaking resource existence.
3. **Least Privilege**: Roles grant only the minimum permissions required for operation.
4. **Credential Confidentiality**: Passwords, access tokens, refresh tokens, API keys, and session secrets are never stored in business tables or logged into audit trails.

---

## 1. Role & Permission Model

### Platform vs. Tenant Roles

```text
Platform Roles:
  - PLATFORM_ADMIN: Full administrative authority across platform and all tenants.
  - PLATFORM_SUPPORT: Operational and support visibility; read-only platform authority.

Tenant Roles:
  - TENANT_OWNER: Complete administrative control of an individual tenant, membership, and configuration.
  - TENANT_ADMIN: Operational administrative control within a tenant.
  - TENANT_MEMBER: Standard business user access within a tenant.
  - TENANT_VIEWER: Read-only access within a tenant.
```

### Initial Permissions Matrix

| Permission String | Description | PLATFORM_ADMIN | PLATFORM_SUPPORT | TENANT_OWNER | TENANT_ADMIN | TENANT_MEMBER | TENANT_VIEWER |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `tenant.read` | View tenant details | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `tenant.manage` | Modify tenant settings | ✓ | - | ✓ | ✓ | - | - |
| `membership.read` | View member roster | ✓ | ✓ | ✓ | ✓ | ✓ | - |
| `membership.manage` | Add/update/remove members | ✓ | - | ✓ | ✓ | - | - |
| `role.read` | View roles & permissions | ✓ | ✓ | ✓ | ✓ | - | - |
| `role.manage` | Modify role mappings | ✓ | - | - | - | - | - |
| `user.read` | View user profiles | ✓ | ✓ | ✓ | ✓ | ✓ | - |
| `user.manage` | Manage platform users | ✓ | - | - | - | - | - |
| `audit.read` | View audit logs | ✓ | ✓ | ✓ | ✓ | - | - |

---

## 2. Privilege Escalation Defenses

- **Self-Role Modification Block**: A user cannot modify their own membership role (`SELF_ROLE_MODIFICATION_DENIED`).
- **Owner Role Protection**:
  - `TENANT_ADMIN` cannot assign `TENANT_OWNER` to any user (`PRIVILEGE_ESCALATION_DENIED`).
  - `TENANT_ADMIN` cannot modify or remove any `TENANT_OWNER` membership.
  - Only `PLATFORM_ADMIN` can escalate tenant ownership outside of initial tenant creation.
- **Platform Role Escalation Block**:
  - Tenant users cannot assign `PLATFORM_ADMIN` or `PLATFORM_SUPPORT` (`PLATFORM_ROLE_ESCALATION_DENIED`).
- **Sole Owner Invariant**:
  - A tenant must always have at least one active `TENANT_OWNER`. Removing, suspending, or demoting the last owner is blocked (`LAST_OWNER_PROTECTION`).

---

## 3. Tenant Isolation Enforcement

```text
Request (Header: X-Tenant-Id)
      │
      ▼
require_authenticated_user()  ──> extracts caller from Supabase JWT
      │
      ▼
TenantResolver.resolve()      ──> checks Membership(tenant_id, user_id, status='ACTIVE')
      │
      ├── Match found  ──> TenantContext(tenant, role, permissions)
      └── No match     ──> 403 Forbidden / 404 Not Found (cross-tenant denied)
```

- All queries executed through repositories require `tenant_id` from the resolved context.
- Cross-tenant resource IDs in path parameters are checked against `tenant_context.tenant.id`. Attempting to reference another tenant's resource yields 404.

---

## 4. Audit Trail Security

- Events captured: `TENANT_CREATED`, `TENANT_UPDATED`, `MEMBERSHIP_CREATED`, `MEMBERSHIP_UPDATED`, `MEMBERSHIP_ROLE_CHANGED`, `MEMBERSHIP_SUSPENDED`, `MEMBERSHIP_REMOVED`.
- Payloads are passed through `sanitize_payload()` to automatically redact keys matching:
  `password`, `token`, `secret`, `api_key`, `access_token`, `refresh_token`, `authorization`, `private_key`, `credential`.
- Tenant users can only read audit events where `audit_events.tenant_id == tenant_context.tenant_id`.
- Platform-level audit events (`tenant_id IS NULL`) are restricted exclusively to `PLATFORM_ADMIN` and `PLATFORM_SUPPORT`.

---

## 5. Scope Boundary

> [!NOTE]
> Phase 2 (Seller Platform, Seller Owner, Branches, Staff, Catalog, Pricing, Orders, Drivers, Billing) is strictly deferred.
