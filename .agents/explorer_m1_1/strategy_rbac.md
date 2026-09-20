# RBAC & Test Harness Implementation Strategy for TTC Phase 5

**Author**: Milestone 1 Explorer 1 (`explorer_m1_1`)  
**Date**: 2026-09-19  
**Status**: Ready for Implementation  
**Target Milestone**: Milestone 1 (Backend Pricing Core & Schema Foundation)

---

## 1. Executive Summary

This report establishes the precise, production-grade strategy for resolving RBAC permission configuration defects and hardening the database test harness in the TTC backend.

During Phase 4 (Catalog expansion), duplicate permission entries were introduced into three roles in `DEFAULT_ROLE_PERMISSIONS`. Furthermore, Phase 5 introduces the Pricing Engine Foundation, requiring two new granular permissions: `pricing.read` and `pricing.manage`. To ensure proper role seeding, database constraint satisfaction, and isolation during testing, four coordinated modifications must be performed:

1. **Deduplicate catalog permissions** in `DEFAULT_ROLE_PERMISSIONS` in `backend/app/core/permissions/constants.py` across `TENANT_ADMIN`, `SELLER_OWNER`, and `SELLER_ADMIN`.
2. **Define `PRICING_READ` and `PRICING_MANAGE`** in `PermissionName` and map them across `DEFAULT_ROLE_PERMISSIONS` following the principle of least privilege.
3. **Register descriptions** for both pricing permissions in `PERMISSION_DESCRIPTIONS` in `backend/app/services/roles.py`, ensuring `RoleService.seed_defaults()` creates and maps them correctly.
4. **Ensure `import app.models`** is executed in `backend/tests/conftest.py` before `Base.metadata.create_all()` so all tables are registered when running unit/integration tests in isolation.

---

## 2. Topic 1: Catalog Permission Deduplication in `constants.py`

### 2.1 Problem Observation & Root Cause
In `backend/app/core/permissions/constants.py`, the 11 catalog permissions are repeated twice in three distinct role definitions:
- `RoleName.TENANT_ADMIN.value`: Lines 184–195 and lines 200–211.
- `RoleName.SELLER_OWNER.value`: Lines 237–248 and lines 253–264.
- `RoleName.SELLER_ADMIN.value`: Lines 280–291 and lines 296–307.

The 11 duplicated permissions in each block are:
1. `PermissionName.CATALOG_READ.value`
2. `PermissionName.CATALOG_MANAGE.value`
3. `PermissionName.CATALOG_PUBLISH.value`
4. `PermissionName.CATALOG_CATEGORIES_READ.value`
5. `PermissionName.CATALOG_CATEGORIES_MANAGE.value`
6. `PermissionName.CATALOG_SERVICES_READ.value`
7. `PermissionName.CATALOG_SERVICES_MANAGE.value`
8. `PermissionName.CATALOG_ADDONS_READ.value`
9. `PermissionName.CATALOG_ADDONS_MANAGE.value`
10. `PermissionName.CATALOG_ITEMS_READ.value`
11. `PermissionName.CATALOG_ITEMS_MANAGE.value`

### 2.2 Impact
- **Database Unique Constraint Violation**: In `RoleService.seed_defaults()`, while `RoleRepository.assign_permission_to_role` performs a duplicate check, iterating over duplicate entries generates redundant select queries per role per test run and introduces risks of `uq_role_permission` UniqueViolation during concurrent or batch seeding operations.
- **Maintenance Hazard**: Dual lists cause configuration drift where future permission edits may only update one block.

### 2.3 Proposed Solution
Delete the trailing duplicated 11 catalog permission lines from each of the three roles.

#### Before (Lines 184–211 in `TENANT_ADMIN`):
```python
        PermissionName.CATALOG_READ.value,
        PermissionName.CATALOG_MANAGE.value,
        PermissionName.CATALOG_PUBLISH.value,
        PermissionName.CATALOG_CATEGORIES_READ.value,
        PermissionName.CATALOG_CATEGORIES_MANAGE.value,
        PermissionName.CATALOG_SERVICES_READ.value,
        PermissionName.CATALOG_SERVICES_MANAGE.value,
        PermissionName.CATALOG_ADDONS_READ.value,
        PermissionName.CATALOG_ADDONS_MANAGE.value,
        PermissionName.CATALOG_ITEMS_READ.value,
        PermissionName.CATALOG_ITEMS_MANAGE.value,

        PermissionName.CONFIGURATION_READ.value,
        PermissionName.CONFIGURATION_MANAGE.value,
        PermissionName.CONFIGURATION_PUBLISH.value,

        PermissionName.CATALOG_READ.value,
        PermissionName.CATALOG_MANAGE.value,
        PermissionName.CATALOG_PUBLISH.value,
        PermissionName.CATALOG_CATEGORIES_READ.value,
        PermissionName.CATALOG_CATEGORIES_MANAGE.value,
        PermissionName.CATALOG_SERVICES_READ.value,
        PermissionName.CATALOG_SERVICES_MANAGE.value,
        PermissionName.CATALOG_ADDONS_READ.value,
        PermissionName.CATALOG_ADDONS_MANAGE.value,
        PermissionName.CATALOG_ITEMS_READ.value,
        PermissionName.CATALOG_ITEMS_MANAGE.value,
```

#### After (TENANT_ADMIN):
```python
        PermissionName.CATALOG_READ.value,
        PermissionName.CATALOG_MANAGE.value,
        PermissionName.CATALOG_PUBLISH.value,
        PermissionName.CATALOG_CATEGORIES_READ.value,
        PermissionName.CATALOG_CATEGORIES_MANAGE.value,
        PermissionName.CATALOG_SERVICES_READ.value,
        PermissionName.CATALOG_SERVICES_MANAGE.value,
        PermissionName.CATALOG_ADDONS_READ.value,
        PermissionName.CATALOG_ADDONS_MANAGE.value,
        PermissionName.CATALOG_ITEMS_READ.value,
        PermissionName.CATALOG_ITEMS_MANAGE.value,

        PermissionName.CONFIGURATION_READ.value,
        PermissionName.CONFIGURATION_MANAGE.value,
        PermissionName.CONFIGURATION_PUBLISH.value,
```
Apply the exact same deletion to `SELLER_OWNER` (lines 253–264) and `SELLER_ADMIN` (lines 296–307).

---

## 3. Topic 2: Phase 5 Pricing Permissions in `constants.py`

### 3.1 Adding to `PermissionName` Enum
In `backend/app/core/permissions/constants.py`, add `PRICING_READ` and `PRICING_MANAGE` to `PermissionName`:

```python
    # Phase 5 Pricing Permissions
    PRICING_READ = 'pricing.read'
    PRICING_MANAGE = 'pricing.manage'
```

### 3.2 Role Matrix Assignment (`DEFAULT_ROLE_PERMISSIONS`)
Following the principle of least privilege, requirements in `ORIGINAL_REQUEST.md`, and test suite specifications in `tests/e2e/test_pricing_tier1_features.py` and `tests/e2e/test_pricing_tier2_boundaries.py`:

| Role Name | `pricing.read` | `pricing.manage` | Rationale |
|:---|:---:|:---:|:---|
| `RoleName.PLATFORM_ADMIN.value` | **YES** | **YES** | Platform super admin has full permissions |
| `RoleName.PLATFORM_SUPPORT.value`| **YES** | **NO**  | Read-only operational visibility across platform |
| `RoleName.TENANT_OWNER.value`   | **YES** | **YES** | Tenant owner with full tenant organization control |
| `RoleName.TENANT_ADMIN.value`   | **YES** | **YES** | Tenant admin managing books and rules |
| `RoleName.TENANT_MEMBER.value`  | **NO**  | **NO**  | Explicitly denied all pricing access (tested in `F-05.4`) |
| `RoleName.TENANT_VIEWER.value`  | **YES** | **NO**  | Read-only tenant viewer (cannot mutate books/rules) |
| `RoleName.SELLER_OWNER.value`   | **YES** | **YES** | Seller owner managing seller price books & rules |
| `RoleName.SELLER_ADMIN.value`   | **YES** | **YES** | Seller admin managing seller price books & rules |
| `RoleName.STAFF.value`          | **YES** | **NO**  | Seller staff can inspect & calculate; cannot mutate/delete (tested in `B-06.5`) |
| `RoleName.VIEWER.value`         | **YES** | **NO**  | Seller viewer can inspect & calculate; cannot mutate (tested in `F-05.2`, `F-05.3`, `B-06.1-4`) |

### 3.3 Exact Code Replacement for `DEFAULT_ROLE_PERMISSIONS`

#### 1. `PLATFORM_ADMIN`:
```python
    RoleName.PLATFORM_ADMIN.value: [
        ...
        PermissionName.CONFIGURATION_DEFINITIONS_MANAGE.value,
        PermissionName.PRICING_READ.value,
        PermissionName.PRICING_MANAGE.value,
    ],
```

#### 2. `PLATFORM_SUPPORT`:
```python
    RoleName.PLATFORM_SUPPORT.value: [
        ...
        PermissionName.CATALOG_ITEMS_READ.value,
        PermissionName.PRICING_READ.value,
    ],
```

#### 3. `TENANT_OWNER`:
```python
    RoleName.TENANT_OWNER.value: [
        ...
        PermissionName.CONFIGURATION_PUBLISH.value,
        PermissionName.PRICING_READ.value,
        PermissionName.PRICING_MANAGE.value,
    ],
```

#### 4. `TENANT_ADMIN` (Deduplicated + Pricing):
```python
    RoleName.TENANT_ADMIN.value: [
        PermissionName.TENANT_READ.value,
        PermissionName.TENANT_MANAGE.value,
        PermissionName.MEMBERSHIP_READ.value,
        PermissionName.MEMBERSHIP_MANAGE.value,
        PermissionName.ROLE_READ.value,
        PermissionName.USER_READ.value,
        PermissionName.AUDIT_READ.value,
        PermissionName.SELLER_READ.value,
        PermissionName.SELLER_MANAGE.value,
        PermissionName.SELLER_BRANCHES_READ.value,
        PermissionName.SELLER_BRANCHES_MANAGE.value,
        PermissionName.SELLER_STAFF_READ.value,
        PermissionName.SELLER_STAFF_MANAGE.value,
        PermissionName.SELLER_SETTINGS_READ.value,
        PermissionName.SELLER_SETTINGS_MANAGE.value,

        PermissionName.CATALOG_READ.value,
        PermissionName.CATALOG_MANAGE.value,
        PermissionName.CATALOG_PUBLISH.value,
        PermissionName.CATALOG_CATEGORIES_READ.value,
        PermissionName.CATALOG_CATEGORIES_MANAGE.value,
        PermissionName.CATALOG_SERVICES_READ.value,
        PermissionName.CATALOG_SERVICES_MANAGE.value,
        PermissionName.CATALOG_ADDONS_READ.value,
        PermissionName.CATALOG_ADDONS_MANAGE.value,
        PermissionName.CATALOG_ITEMS_READ.value,
        PermissionName.CATALOG_ITEMS_MANAGE.value,

        PermissionName.CONFIGURATION_READ.value,
        PermissionName.CONFIGURATION_MANAGE.value,
        PermissionName.CONFIGURATION_PUBLISH.value,

        PermissionName.PRICING_READ.value,
        PermissionName.PRICING_MANAGE.value,
    ],
```

#### 5. `TENANT_MEMBER` (Unchanged):
```python
    RoleName.TENANT_MEMBER.value: [
        PermissionName.TENANT_READ.value,
        PermissionName.MEMBERSHIP_READ.value,
        PermissionName.USER_READ.value,
    ],
```

#### 6. `TENANT_VIEWER`:
```python
    RoleName.TENANT_VIEWER.value: [
        PermissionName.TENANT_READ.value,
        PermissionName.PRICING_READ.value,
    ],
```

#### 7. `SELLER_OWNER` (Deduplicated + Pricing):
```python
    RoleName.SELLER_OWNER.value: [
        PermissionName.TENANT_READ.value,
        PermissionName.TENANT_MANAGE.value,
        PermissionName.MEMBERSHIP_READ.value,
        PermissionName.MEMBERSHIP_MANAGE.value,
        PermissionName.ROLE_READ.value,
        PermissionName.USER_READ.value,
        PermissionName.AUDIT_READ.value,
        PermissionName.SELLER_READ.value,
        PermissionName.SELLER_MANAGE.value,
        PermissionName.SELLER_BRANCHES_READ.value,
        PermissionName.SELLER_BRANCHES_MANAGE.value,
        PermissionName.SELLER_STAFF_READ.value,
        PermissionName.SELLER_STAFF_MANAGE.value,
        PermissionName.SELLER_SETTINGS_READ.value,
        PermissionName.SELLER_SETTINGS_MANAGE.value,

        PermissionName.CATALOG_READ.value,
        PermissionName.CATALOG_MANAGE.value,
        PermissionName.CATALOG_PUBLISH.value,
        PermissionName.CATALOG_CATEGORIES_READ.value,
        PermissionName.CATALOG_CATEGORIES_MANAGE.value,
        PermissionName.CATALOG_SERVICES_READ.value,
        PermissionName.CATALOG_SERVICES_MANAGE.value,
        PermissionName.CATALOG_ADDONS_READ.value,
        PermissionName.CATALOG_ADDONS_MANAGE.value,
        PermissionName.CATALOG_ITEMS_READ.value,
        PermissionName.CATALOG_ITEMS_MANAGE.value,

        PermissionName.CONFIGURATION_READ.value,
        PermissionName.CONFIGURATION_MANAGE.value,
        PermissionName.CONFIGURATION_PUBLISH.value,

        PermissionName.PRICING_READ.value,
        PermissionName.PRICING_MANAGE.value,
    ],
```

#### 8. `SELLER_ADMIN` (Deduplicated + Pricing):
```python
    RoleName.SELLER_ADMIN.value: [
        PermissionName.TENANT_READ.value,
        PermissionName.MEMBERSHIP_READ.value,
        PermissionName.MEMBERSHIP_MANAGE.value,
        PermissionName.USER_READ.value,
        PermissionName.AUDIT_READ.value,
        PermissionName.SELLER_READ.value,
        PermissionName.SELLER_MANAGE.value,
        PermissionName.SELLER_BRANCHES_READ.value,
        PermissionName.SELLER_BRANCHES_MANAGE.value,
        PermissionName.SELLER_STAFF_READ.value,
        PermissionName.SELLER_STAFF_MANAGE.value,
        PermissionName.SELLER_SETTINGS_READ.value,
        PermissionName.SELLER_SETTINGS_MANAGE.value,

        PermissionName.CATALOG_READ.value,
        PermissionName.CATALOG_MANAGE.value,
        PermissionName.CATALOG_PUBLISH.value,
        PermissionName.CATALOG_CATEGORIES_READ.value,
        PermissionName.CATALOG_CATEGORIES_MANAGE.value,
        PermissionName.CATALOG_SERVICES_READ.value,
        PermissionName.CATALOG_SERVICES_MANAGE.value,
        PermissionName.CATALOG_ADDONS_READ.value,
        PermissionName.CATALOG_ADDONS_MANAGE.value,
        PermissionName.CATALOG_ITEMS_READ.value,
        PermissionName.CATALOG_ITEMS_MANAGE.value,

        PermissionName.CONFIGURATION_READ.value,
        PermissionName.CONFIGURATION_MANAGE.value,
        PermissionName.CONFIGURATION_PUBLISH.value,

        PermissionName.PRICING_READ.value,
        PermissionName.PRICING_MANAGE.value,
    ],
```

#### 9. `STAFF`:
```python
    RoleName.STAFF.value: [
        PermissionName.TENANT_READ.value,
        PermissionName.MEMBERSHIP_READ.value,
        PermissionName.USER_READ.value,
        PermissionName.SELLER_READ.value,
        PermissionName.SELLER_BRANCHES_READ.value,
        PermissionName.SELLER_STAFF_READ.value,
        PermissionName.SELLER_SETTINGS_READ.value,
        PermissionName.CONFIGURATION_READ.value,
        PermissionName.CATALOG_READ.value,
        PermissionName.CATALOG_CATEGORIES_READ.value,
        PermissionName.CATALOG_SERVICES_READ.value,
        PermissionName.CATALOG_ADDONS_READ.value,
        PermissionName.CATALOG_ITEMS_READ.value,
        PermissionName.PRICING_READ.value,
    ],
```

#### 10. `VIEWER`:
```python
    RoleName.VIEWER.value: [
        PermissionName.TENANT_READ.value,
        PermissionName.SELLER_READ.value,
        PermissionName.SELLER_BRANCHES_READ.value,
        PermissionName.CONFIGURATION_READ.value,
        PermissionName.CATALOG_READ.value,
        PermissionName.CATALOG_CATEGORIES_READ.value,
        PermissionName.CATALOG_SERVICES_READ.value,
        PermissionName.CATALOG_ADDONS_READ.value,
        PermissionName.CATALOG_ITEMS_READ.value,
        PermissionName.PRICING_READ.value,
    ],
```

---

## 4. Topic 3: Permission Descriptions in `backend/app/services/roles.py`

### 4.1 Problem Observation & Root Cause
In `backend/app/services/roles.py`:
`RoleService.seed_defaults()` iterates through `PERMISSION_DESCRIPTIONS.items()` to create initial permissions:
```python
        permissions_by_name: dict[str, Permission] = {}
        for perm_name, desc in PERMISSION_DESCRIPTIONS.items():
            perm = self.role_repo.get_permission_by_name(perm_name)
            if not perm:
                perm = self.role_repo.create_permission(name=perm_name, description=desc)
            permissions_by_name[perm_name] = perm
```
In `backend/tests/unit/test_rbac_seed.py` lines 27–28:
```python
        perms = {p.name: p for p in db.query(Permission).all()}
        assert set(perms.keys()) == {p.value for p in PermissionName}
```
If `PRICING_READ` and `PRICING_MANAGE` are defined in `PermissionName` but omitted from `PERMISSION_DESCRIPTIONS`:
1. `seed_defaults()` will NOT insert them into the `permissions` table.
2. `assert set(perms.keys()) == {p.value for p in PermissionName}` will fail.
3. In `DEFAULT_ROLE_PERMISSIONS`, `permissions_by_name.get(perm_name)` will return `None`, so pricing permissions will NOT be mapped to roles, causing `assigned_perms == set(expected_perms)` to fail.

### 4.2 Proposed Solution
In `backend/app/services/roles.py`, add entries for both permissions in `PERMISSION_DESCRIPTIONS` (lines 62–63):

```python
    PermissionName.PRICING_READ.value: 'View price books, rules, and calculate prices',
    PermissionName.PRICING_MANAGE.value: 'Manage price books and pricing rules',
```

---

## 5. Topic 4: Test Harness Schema Creation in `backend/tests/conftest.py`

### 5.1 Problem Observation & Root Cause
In `backend/tests/conftest.py`:
```python
@pytest.fixture(autouse=True)
def reset_database():
    """Reset database tables and seed defaults before each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        RoleService(db).seed_defaults()
    yield
```
`Base.metadata.create_all(bind=engine)` uses the tables currently registered on `Base.metadata`.
In Python, SQLAlchemy ORM models register on `Base.metadata` only when their module is imported.
`conftest.py` imports only:
```python
from app.db import Base, SessionLocal, engine
from app.models.membership import Membership
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.memberships import MembershipRepository
from app.repositories.tenants import TenantRepository
from app.repositories.users import UserRepository
from app.services.roles import RoleService
```
When running unit or integration tests in isolation without importing `app.main` (or when running new Phase 5 pricing tests):
If `app.models` is not imported, tables for `Seller`, `Catalog`, `Configuration`, and `Pricing` may not be registered in `Base.metadata` when `reset_database` executes.
This causes table creation omissions, foreign key dependency failures, or `psycopg.errors.UndefinedTable: relation "xyz" does not exist`.

### 5.2 Precedent in Monorepo
1. `backend/migrations/env.py` line 5:
   `import app.models  # noqa: F401`
2. `backend/tests/e2e/conftest.py` line 10:
   `import app.models  # Ensures all models (tenants, users, sellers, catalogs, pricing) are registered`

### 5.3 Proposed Solution
Add `import app.models  # noqa: F401` to `backend/tests/conftest.py` right above `from app.db import Base, SessionLocal, engine`.

#### Diff in `backend/tests/conftest.py`:
```python
 from __future__ import annotations
 
 import uuid
 
 import pytest
+import app.models  # noqa: F401
 from app.db import Base, SessionLocal, engine
 from app.models.membership import Membership
 from app.models.tenant import Tenant
```

---

## 6. Frontend & Shared Types Alignment (Milestone 4 Preparation)

In `packages/types/src/tenant.ts`, `PermissionName` should be updated in Milestone 4 to export the new pricing permissions for full frontend end-to-end type safety:

```typescript
export type PermissionName =
  | 'tenant.read'
  | 'tenant.manage'
  | 'membership.read'
  | 'membership.manage'
  | 'role.read'
  | 'role.manage'
  | 'user.read'
  | 'user.manage'
  | 'audit.read'
  | 'pricing.read'
  | 'pricing.manage';
```

---

## 7. Step-by-Step Verification Method

Once implemented by Milestone 1 implementers:

1. **Verify Unit RBAC Seed Test**:
   ```bash
   cd /workspaces/TheTextileCare/backend
   pytest tests/unit/test_rbac_seed.py -v
   ```
   **Pass Condition**: All 5 tests pass, confirming `RoleName` and `PermissionName` counts match DB records, and all role assignments in `DEFAULT_ROLE_PERMISSIONS` match assigned permissions.

2. **Verify Security RBAC & Privilege Escalation Tests**:
   ```bash
   pytest tests/security/test_tenant_rbac.py -v
   pytest tests/security/test_privilege_escalation.py -v
   ```
   **Pass Condition**: All security tests pass with zero `UndefinedTable` errors.

3. **Verify Full Existing API Test Suite**:
   ```bash
   pytest tests/api/ -v
   ```
   **Pass Condition**: All 21 API tests pass.

4. **Verify Zero Duplicate Permissions in Python**:
   ```bash
   python3 -c "
   import sys
   sys.path.insert(0, '/workspaces/TheTextileCare/backend')
   from app.core.permissions.constants import DEFAULT_ROLE_PERMISSIONS
   for role, perms in DEFAULT_ROLE_PERMISSIONS.items():
       assert len(perms) == len(set(perms)), f'Duplicate found in {role}'
   print('Zero duplicate permissions verified across all roles.')
   "
   ```
