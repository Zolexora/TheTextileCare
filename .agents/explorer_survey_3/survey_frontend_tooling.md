# Survey Report: Frontend, Shared Types, & Monorepo Tooling
**Milestone**: TTC Phase 5 — Pricing Engine Foundation  
**Author**: Frontend Tooling Explorer (`teamwork_preview_explorer`)  
**Date**: 2026-09-19  
**Status**: Investigation Complete  

---

## 1. Executive Summary

This survey provides a comprehensive architectural and technical investigation of the frontend applications, shared TypeScript libraries, monorepo tooling, verification pipelines, and documentation structure in `/workspaces/TheTextileCare`. It specifically prepares the foundation for **TTC Phase 5: Pricing Engine Foundation**, ensuring that:
1. Shared TypeScript contracts (`@ttc/types`) accurately mirror Phase 5 domain entities and calculation APIs.
2. `apps/seller-web` gains a minimal, clean pricing management and calculation visualization foundation **without duplicating backend calculation logic**.
3. Monorepo verification scripts (`pnpm lint`, `pnpm typecheck`, `pnpm build`) pass reliably and cleanly.
4. All documentation and repository hygiene requirements are clearly mapped for subsequent implementation and verification phases.

---

## 2. Monorepo Architecture & Workspace Layout

### 2.1 Workspace Configuration
The repository is managed as a pnpm workspace with Turborepo:
- **Package Manager**: `pnpm@9.12.3` (locked via `pnpm-lock.yaml`)
- **Orchestration**: `turbo@2.0.5` (`turbo.json`)
- **TypeScript**: `typescript@5.5.4` (`tsconfig.base.json`)
- **Workspace Glob (`pnpm-workspace.yaml`)**:
  ```yaml
  packages:
    - 'apps/*'
    - 'packages/*'
  ```

### 2.2 Package Inventory
The monorepo contains 13 total workspace packages across `apps/` and `packages/`:

| Directory | Package Name | Type / Framework | Purpose |
|---|---|---|---|
| `apps/seller-web` | `@ttc/seller-web` | Next.js 14 (App Router) | Seller SaaS web portal |
| `apps/admin-web` | `@ttc/admin-web` | Next.js 14 (App Router) | Platform administration portal |
| `apps/marketplace-web` | `@ttc/marketplace-web` | Next.js 14 (App Router) | Customer marketplace portal |
| `apps/seller-mobile` | `@ttc/seller-mobile` | React Native / Expo 51 | Seller mobile app |
| `apps/marketplace-mobile` | `@ttc/marketplace-mobile` | React Native / Expo 51 | Customer marketplace mobile app |
| `apps/driver-mobile` | `@ttc/driver-mobile` | React Native / Expo 51 | Logistics driver mobile app |
| `packages/types` | `@ttc/types` | TypeScript source | Shared domain types and API contracts |
| `packages/api-client` | `@ttc/api-client` | TypeScript source | Shared HTTP client wrapper (`fetch`) |
| `packages/ui` | `@ttc/ui` | React 18 / Tailwind | Shared design system components |
| `packages/branding` | `@ttc/branding` | TypeScript source | Tenant white-label branding models |
| `packages/config` | `@ttc/config` | TypeScript source | Shared environment and app configuration |
| `packages/auth` | `@ttc/auth` | TypeScript source | Auth state and token handlers |
| `packages/tenant` | `@ttc/tenant` | TypeScript source | Multi-tenant context utilities |

---

## 3. Shared Types Package (`packages/types`)

### 3.1 Existing Type Package Structure
- **Package Manifest (`packages/types/package.json`)**:
  ```json
  {
    "name": "@ttc/types",
    "version": "0.1.0",
    "private": true,
    "main": "./src/index.ts",
    "types": "./src/index.ts",
    "scripts": {
      "typecheck": "tsc -p tsconfig.json --noEmit"
    }
  }
  ```
- **Export Mechanism**: Direct source export (`main` and `types` point to `./src/index.ts`). There is no build/transpilation step for `@ttc/types`; consuming applications transpile or consume the TypeScript files directly via workspace resolution.
- **Current Files in `packages/types/src/`**:
  - `index.ts`: Central re-exporter (`export * from './common'; export * from './api'; export * from './tenant'; export * from './catalog';`).
  - `common.ts`: Common utility types (`Environment`, `ApiError`, `PaginatedResponse<T>`, `HealthStatus`).
  - `api.ts`: API envelope definitions (`ApiResponse<T>`, `ApiErrorResponse`, `ErrorEnvelope`).
  - `tenant.ts`: Tenant, Membership, Audit, and RBAC types (`PlatformRole`, `TenantRole`, `RoleName`, `PermissionName`, `Tenant`, `Membership`, `AuditEvent`).
  - `catalog.ts`: Phase 4 Catalog entities (`Catalog`, `Category`, `Service`, `ServiceItem`, `ServiceAddon`).

### 3.2 Required Phase 5 Pricing Types (`packages/types/src/pricing.ts`)
Phase 5 introduces deterministic pricing, price books, and price rules referencing Phase 4 catalog entities. To support full frontend-backend contract symmetry, a new file `packages/types/src/pricing.ts` should be created and exported from `packages/types/src/index.ts`.

#### Enums & Literal Unions
```typescript
export type PriceBookScope = 'PLATFORM' | 'SELLER' | 'BRANCH';
export type PriceBookStatus = 'DRAFT' | 'ACTIVE' | 'ARCHIVED';
export type PriceRuleType = 'FIXED' | 'PER_ITEM' | 'PER_UNIT' | 'PER_WEIGHT';
export type ComponentType = 'BASE' | 'SURCHARGE' | 'DISCOUNT' | 'TAX';
export type PriceRuleStatus = 'ACTIVE' | 'INACTIVE';
```

#### Core Entities
```typescript
export interface PriceBook {
  id: string;
  tenant_id: string;
  seller_id?: string | null;
  branch_id?: string | null;
  name: string;
  description?: string | null;
  currency: string;
  scope: PriceBookScope;
  status: PriceBookStatus;
  effective_from?: string | null;
  effective_to?: string | null;
  is_default: boolean;
  priority: number;
  created_at: string;
  updated_at: string;
}

export interface PriceRule {
  id: string;
  tenant_id: string;
  price_book_id: string;
  service_id?: string | null;
  service_item_id?: string | null;
  service_addon_id?: string | null;
  rule_type: PriceRuleType;
  component_type: ComponentType;
  base_amount: string; // Decimal representation (string to avoid JS float inaccuracies)
  unit_rate?: string | null;
  min_quantity?: number | null;
  max_quantity?: number | null;
  percentage_rate?: string | null; // e.g., "0.08" for 8% tax
  priority: number;
  status: PriceRuleStatus;
  created_at: string;
  updated_at: string;
}
```

#### Mutation Inputs (CRUD)
```typescript
export interface CreatePriceBookInput {
  seller_id?: string | null;
  branch_id?: string | null;
  name: string;
  description?: string | null;
  currency: string;
  scope?: PriceBookScope;
  effective_from?: string | null;
  effective_to?: string | null;
  is_default?: boolean;
  priority?: number;
}

export interface UpdatePriceBookInput {
  name?: string;
  description?: string | null;
  currency?: string;
  status?: PriceBookStatus;
  effective_from?: string | null;
  effective_to?: string | null;
  is_default?: boolean;
  priority?: number;
}

export interface CreatePriceRuleInput {
  price_book_id: string;
  service_id?: string | null;
  service_item_id?: string | null;
  service_addon_id?: string | null;
  rule_type: PriceRuleType;
  component_type?: ComponentType;
  base_amount: string;
  unit_rate?: string | null;
  min_quantity?: number | null;
  max_quantity?: number | null;
  percentage_rate?: string | null;
  priority?: number;
}

export interface UpdatePriceRuleInput {
  rule_type?: PriceRuleType;
  component_type?: ComponentType;
  base_amount?: string;
  unit_rate?: string | null;
  min_quantity?: number | null;
  max_quantity?: number | null;
  percentage_rate?: string | null;
  priority?: number;
  status?: PriceRuleStatus;
}
```

#### Deterministic Calculation Contracts
```typescript
export interface PricingCalculationItemRequest {
  service_id: string;
  service_item_id?: string | null;
  quantity: number;
  unit_type?: string;
  addon_ids?: string[];
}

export interface PricingCalculationRequest {
  seller_id: string;
  branch_id?: string | null;
  items: PricingCalculationItemRequest[];
  coupon_code?: string | null;
  effective_date?: string | null; // ISO format string
}

export interface PricingBreakdownComponent {
  type: ComponentType;
  name: string;
  amount: string;
  rate?: string | null;
}

export interface PricingLineItemResult {
  service_id: string;
  service_item_id?: string | null;
  quantity: number;
  unit_type: string;
  base_price: string;
  surcharge_amount: string;
  discount_amount: string;
  tax_amount: string;
  subtotal: string;
  total: string;
  applied_rule_ids: string[];
  components: PricingBreakdownComponent[];
}

export interface PricingCalculationSummary {
  subtotal: string;
  surcharge_total: string;
  discount_total: string;
  tax_total: string;
  grand_total: string;
  currency: string;
  resolved_price_book_id: string;
  resolved_price_book_name: string;
}

export interface PricingCalculationResult {
  calculation_id: string;
  tenant_id: string;
  seller_id: string;
  branch_id?: string | null;
  calculated_at: string;
  summary: PricingCalculationSummary;
  items: PricingLineItemResult[];
}
```

### 3.3 Permissions Update (`packages/types/src/tenant.ts`)
Add Phase 5 pricing permissions to `PermissionName`:
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
  // Phase 5 Pricing Permissions
  | 'pricing.read'
  | 'pricing.manage';
```

---

## 4. `apps/seller-web` Frontend Architecture & UI Foundation

### 4.1 Current Architecture
- **Framework**: Next.js 14.2.15 (App Router with `react@18.3.1`)
- **Styling**: Tailwind CSS 3.4.10 with `@ttc/ui` components (`Button`, `Card`, `Dialog`, `Input`, `Logo`, `Typography`)
- **Current State**:
  - `src/app/layout.tsx`: Basic HTML layout shell with favicon metadata.
  - `src/app/page.tsx`: Single landing page displaying branding, a tenant card, and mock features.
  - Currently, `apps/seller-web` does **not** have active API client wiring or backend connections.
- **Dependencies (`apps/seller-web/package.json`)**:
  ```json
  "dependencies": {
    "@ttc/branding": "workspace:^",
    "@ttc/config": "workspace:*",
    "@ttc/ui": "workspace:*",
    "next": "14.2.15",
    "react": "18.3.1",
    "react-dom": "18.3.1"
  }
  ```

### 4.2 Integration Steps for `apps/seller-web`
To wire up the Phase 5 pricing foundation:
1. **Workspace Dependencies**:
   Add `@ttc/types` and `@ttc/api-client` to `apps/seller-web/package.json`:
   ```json
   "dependencies": {
     "@ttc/api-client": "workspace:*",
     "@ttc/branding": "workspace:^",
     "@ttc/config": "workspace:*",
     "@ttc/types": "workspace:*",
     "@ttc/ui": "workspace:*",
     "next": "14.2.15",
     "react": "18.3.1",
     "react-dom": "18.3.1"
   }
   ```
2. **API Client Factory (`apps/seller-web/src/lib/api.ts`)**:
   Leverage the existing `@ttc/api-client` package:
   ```typescript
   import { ApiClient } from '@ttc/api-client';

   export const apiClient = new ApiClient({
     baseUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
   });
   ```

### 4.3 Minimal Pricing Management Foundation Design (Zero Calculation Duplication)
Requirement R5 explicitly mandates:
> *"Build a minimal pricing management foundation in apps/seller-web without duplicating calculation logic."*

#### Architectural Principle
The frontend acts as an administrative viewer and an execution client. **All pricing calculation formulas, precedence resolution, tax math, discounts, and Decimal rounding belong solely to the backend FastAPI Pricing Engine.** The frontend simply formats inputs into `PricingCalculationRequest`, sends them to `POST /api/v1/pricing/calculate`, and renders the returned `PricingCalculationResult`.

#### UI Component Layout
Implement the pricing foundation either as a dedicated route `src/app/pricing/page.tsx` or integrated into the main seller portal dashboard:
1. **Top Navigation Bar / Tab Switcher**:
   - Navigation links: "Dashboard", "Catalog", "Pricing".
2. **Price Books Management Section**:
   - Table displaying configured price books:
     - Name, Scope (`PLATFORM`, `SELLER`, `BRANCH`), Status (`ACTIVE`, `DRAFT`), Currency, Effective Dates, Default Flag, Priority.
     - Action button: "Create Price Book" (opens modal using `@ttc/ui` `Dialog`, `Input`, `Button`).
3. **Price Rules Inspector Section**:
   - Displays rules assigned to the active Price Book:
     - Target (Service / Item / Addon), Rule Type (`FIXED`, `PER_ITEM`, `PER_UNIT`, `PER_WEIGHT`), Component (`BASE`, `SURCHARGE`, `DISCOUNT`, `TAX`), Base Amount, Unit Rate, Percentage Rate, Priority.
4. **Deterministic Pricing Calculator Sandbox Widget**:
   - An interactive testing panel for the seller:
     - Form: Service selector, Service Item code, Quantity (supports unit/weight), Addon toggles, Branch override selector.
     - Button: `Calculate Price` (triggers `apiClient.request<ApiResponse<PricingCalculationResult>>('/api/v1/pricing/calculate', { method: 'POST', body: ... })`).
     - Breakdown Card: Renders exact results returned by backend:
       - Base Subtotal: `$XX.XX`
       - Surcharges: `$XX.XX`
       - Discounts: `-$XX.XX`
       - Taxes: `$XX.XX`
       - **Grand Total**: `$XX.XX`
       - Resolved Rule & Price Book ID badge.

---

## 5. Monorepo Verification & Tooling Diagnostics

### 5.1 Verification Script Matrix

| Command | Tool | Packages Targeted | Current Status | Execution Time |
|---|---|---|---|---|
| `pnpm typecheck` | `turbo run typecheck` | 10 TypeScript packages | **PASS** (0 errors) | ~7.2s |
| `pnpm lint` | `turbo run lint` | 3 web apps (`next lint`) | **PASS** (0 warnings, 0 errors) | ~11.8s |
| `pnpm build` | `turbo run build` | 3 web apps (`next build`) | **PASS** (code 0) | ~0.7s (cached) / ~4s (fresh) |
| `pnpm test` | `turbo run test` | Skipped (no `test` script in packages) | PASS (0 tasks) | <0.1s |

### 5.2 Critical Backend Discovery & Diagnostics
During the investigation of test verification pipelines, running `pytest` in `backend` surfaced an existing issue introduced during Phase 4 permissions registration.

- **Observed Error**:
  ```
  sqlalchemy.exc.IntegrityError: (psycopg.errors.UniqueViolation) duplicate key value violates unique constraint "uq_role_permission"
  DETAIL: Key (role_id, permission_id)=(..., ...) already exists.
  ```
- **Root Cause**:
  In `backend/app/core/permissions/constants.py`, the `DEFAULT_ROLE_PERMISSIONS` dictionary contains duplicate blocks of `PermissionName.CATALOG_*` entries for multiple roles:
  1. `RoleName.TENANT_ADMIN.value`: Lines 184–195 and lines 200–211 contain identical catalog permission entries.
  2. `RoleName.SELLER_OWNER.value`: Lines 237–248 and lines 253–264 contain identical catalog permission entries.
  3. `RoleName.SELLER_ADMIN.value`: Lines 280–291 and lines 296–307 contain identical catalog permission entries.
- **Impact**:
  When `RoleService.seed_defaults()` executes inside `tests/conftest.py`'s `reset_database()` fixture, it iterates through `DEFAULT_ROLE_PERMISSIONS` and attempts to assign duplicated permissions within the same transaction. This triggers PostgreSQL's `uq_role_permission` unique constraint violation and aborts the test session.
- **Recommended Remediation**:
  The backend implementer or chore task must deduplicate the list entries in `DEFAULT_ROLE_PERMISSIONS` in `backend/app/core/permissions/constants.py`. Once deduplicated, `seed_defaults()` succeeds and pytest runs cleanly.

---

## 6. Documentation Structure (`docs/`)

### 6.1 Existing Documentation Layout
The `docs/` folder contains comprehensive architectural records:
```
docs/
├── README.md
├── app-factory/
│   └── architecture.md
├── architecture/
│   ├── backend.md, data-flow.md, frontend.md, identity-tenancy.md, mobile.md, monorepo.md, overview.md
├── customization/
│   └── architecture.md
├── database/
│   ├── architecture.md, phase-1-schema.md
├── decisions/
│   └── ADR-001 through ADR-009
├── deployment/
│   └── overview.md
├── project-status/
│   ├── ORIGINAL_REQUEST.md, Phase2_Implementation_Report.md, phase_4_verification_report.md
├── security/
│   ├── principles.md, rbac-tenant-isolation.md
└── white-label/
    └── architecture.md
```

### 6.2 Required Phase 5 Documentation
For Phase 5, the following four documentation artifacts must be produced:
1. `docs/architecture/pricing-engine.md`:
   - Precedence resolution flow (`Platform Default → Seller → Branch → Rule`).
   - Calculation engine lifecycle and component breakdown (Base Price, Surcharges, Discounts, Taxes).
   - Strict architectural separation between Catalog ("What is offered") and Pricing ("How much it costs").
2. `docs/database/phase-5-pricing-schema.md`:
   - Schema diagrams and table definitions for `price_books` and `price_rules`.
   - Foreign key relationships to `tenants`, `sellers`, `seller_branches`, `services`, `service_items`, `service_addons`.
   - Indexing, uniqueness constraints, and `NUMERIC(12, 4)` / `Decimal` precision rationale.
3. `docs/security/pricing-security-isolation.md`:
   - Tenant isolation model (authenticated context enforcement, rejection of cross-tenant foreign keys).
   - ID injection protections and role-based permissions (`pricing.read`, `pricing.manage`).
   - Audit trail events emitted via `AuditService`.
4. `docs/project-status/phase_5_verification_report.md`:
   - Verification results across backend tests, frontend builds, database migrations (`alembic upgrade head`), and git tree cleanliness.

---

## 7. Git Status & Repository Hygiene

### 7.1 Current Status
- **Current Branch**: `main` (synced with `origin/main` at `1c91406`)
- **Working Tree State**:
  - `deleted: docs/project_stats/phase_4_verification_report.md`
  - `untracked: docs/project-status/phase_4_verification_report.md`
  - `untracked: ORIGINAL_REQUEST.md`
- **Analysis**:
  The directory `docs/project_stats` was renamed to `docs/project-status` in git working tree. When committing Phase 5, this rename should be staged cleanly along with Phase 5 additions.
- **Commit Requirement**:
  Phase 5 must be committed cleanly with zero untracked artifacts:
  `feat(phase-5): implement pricing engine foundation`

---

## 8. Action Plan & Hand-off Recommendations

For the implementers and orchestrator, follow this sequence:
1. **Types Implementation**:
   - Create `packages/types/src/pricing.ts` with all types outlined in Section 3.2.
   - Update `packages/types/src/index.ts` and `packages/types/src/tenant.ts`.
   - Run `pnpm --filter @ttc/types typecheck`.
2. **Backend Deduplication & Pricing Engine**:
   - Deduplicate catalog permissions in `backend/app/core/permissions/constants.py` (resolves `uq_role_permission` error).
   - Implement Phase 5 entities (`price_books`, `price_rules`), Alembic migration, deterministic calculation service, permissions, and REST endpoints under `/api/v1/pricing/`.
3. **Seller Web UI Foundation**:
   - Add `"@ttc/types": "workspace:*"` and `"@ttc/api-client": "workspace:*"` to `apps/seller-web/package.json`.
   - Create `apps/seller-web/src/lib/api.ts`.
   - Build `/pricing` route or pricing tab with Price Books overview, Price Rules table, and the Deterministic Calculation Sandbox widget that calls the backend.
4. **Monorepo Verification & Docs**:
   - Run `pnpm lint`, `pnpm typecheck`, `pnpm build`.
   - Run `pytest` in `backend`.
   - Generate the four Phase 5 documentation files in `docs/`.
   - Verify clean git status and commit as `feat(phase-5): implement pricing engine foundation`.
