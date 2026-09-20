# TTC Phase 5: Pricing Engine Foundation — Specification Survey Report

**Document Author**: `teamwork_preview_spec_miner` (Specification Miner)  
**Date**: 2026-09-19  
**Target Milestone**: Phase 5 — Pricing Engine Foundation  
**Target Working Directory**: `/workspaces/TheTextileCare`  
**Authoritative Request Reference**: `/workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md` (Header `## 2026-09-19T04:33:52Z`)  

---

## 1. Executive Summary & Domain Scope

The **Pricing Engine Foundation** provides the core domain answering **"How much does it cost?"** cleanly and strictly isolated from the Catalog domain (**"What is being offered?"**) and future Ordering/Checkout domains (**"Who is buying it?"**).

### 1.1 In-Scope Capabilities
- **Price Books (`price_books`)**: Container for tenant-isolated pricing rules scoped by seller, branch, or platform default, with effective dating and status lifecycles (`DRAFT`, `ACTIVE`, `INACTIVE`).
- **Price Rules (`price_rules`)**: Granular calculation rules referencing Phase 4 catalog services, items, and add-ons without altering catalog tables or duplicating catalog metadata.
- **Rule Rate Types**: `FIXED`, `PER_ITEM`, `PER_UNIT`, `PER_WEIGHT`.
- **Normalized Breakdown Structure**: Strict 4-tier financial breakdown consisting of `Base Price`, `Surcharges`, `Discounts`, and `Taxes`, computed using exact arbitrary-precision `Decimal` mathematics.
- **Deterministic Calculation Engine**: Pure calculation service resolving precedence (`Platform Default → Seller → Branch → Rule`), validating date effectiveness, and asserting mathematical consistency (`subtotal + surcharges - discounts + tax = grand total`) without persisting any customer order or cart.
- **Multi-Tenant Security & RBAC**: Tenant context isolation, defense against cross-tenant ID injection, least-privilege permissioning (`pricing.read`, `pricing.manage`), and audit event emission via `AuditService`.
- **APIs & Monorepo Integration**: RESTful endpoints under `/api/v1/pricing/`, shared TypeScript contracts in `@ttc/types` (`packages/types/src/pricing.ts`), and administrative UI baseline in `apps/seller-web`.

### 1.2 Explicit Out-of-Scope Boundaries
- **No Catalog Table Modifications**: No price, currency, or fee columns on `catalogs`, `services`, `service_items`, or `service_addons`.
- **No Order or Checkout Persistence**: No `orders`, `order_items`, `cart`, `invoices`, or transaction persistence tables.
- **No Payment Processing**: No Stripe, payment intents, or gateway integrations.
- **No Distributed Infrastructure**: No Kafka, RabbitMQ, microservice splits, or external pricing microservices; preserve the modular monolith.
- **No EAV (Entity-Attribute-Value) Tables**: Structured relational modeling for all price books and price rules.

---

## 2. Requirements Traceability Matrix (R1 - R5)

| Req ID | Requirement Area | Core Mandate | Authoritative Constraint / Standard | Verification Condition |
|---|---|---|---|---|
| **R1** | Architectural Integrity | FastAPI, SQLAlchemy 2, Alembic, PostgreSQL psycopg3, modular monolith | Maintain existing architecture; new migration chained to `ddf173e6fc96` without touching Phase 1-4 revisions | `alembic upgrade head` succeeds; no migration conflicts |
| **R2** | Core Pricing Model & Components | Normalized `price_books` and `price_rules` entities referencing Phase 4 catalog items/addons | Rule types: `FIXED`, `PER_ITEM`, `PER_UNIT`, `PER_WEIGHT`. Normalized breakdown: Base Price, Surcharge, Discount, Tax. `Decimal` arithmetic exclusively | Pydantic & SQLAlchemy schemas validate `Decimal` types; 0 floating-point operations |
| **R3** | Deterministic Calculation Service | Pure calculation engine with hierarchical precedence, date validity, and breakdown invariant | Precedence: `Platform Default → Seller → Branch → Rule`. Date range: `effective_from <= date <= effective_to`. Identity: `subtotal + surcharges - discounts + tax == grand_total` | `grand_total` matches identity under all rounding conditions; draft rules never leak |
| **R4** | Security & Permissions | Authenticated `TenantContext` isolation, ID injection defense, RBAC, and AuditService | Granular permissions `pricing.read` and `pricing.manage`. Tenant B accessing Tenant A returns `404 Not Found`. `VIEWER` cannot mutate (403) | Security tests for cross-tenant tampering, injection, and privilege escalation pass |
| **R5** | Integration & APIs | RESTful `/api/v1/pricing/` endpoints, TypeScript `@ttc/types`, and seller-web view foundation | Expose books, rules, and calculation endpoints. Export TypeScript interfaces in `packages/types`. Integrate seller-web without duplicating logic | `pnpm lint`, `pnpm typecheck`, and `pnpm build` pass across all 13 monorepo packages |

---

## 3. Core Pricing Data Model & Schema Specifications

### 3.1 Entity: `PriceBook` (`price_books` table)
Represents a scoped pricing book containing a set of price rules.

```sql
CREATE TABLE price_books (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    seller_id UUID NULL REFERENCES sellers(id) ON DELETE CASCADE,
    branch_id UUID NULL REFERENCES seller_branches(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description VARCHAR(1000) NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    status VARCHAR(50) NOT NULL DEFAULT 'DRAFT', -- DRAFT, ACTIVE, INACTIVE
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    effective_from TIMESTAMPTZ NULL,
    effective_to TIMESTAMPTZ NULL,
    created_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    updated_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_price_books_tenant_id ON price_books(tenant_id);
CREATE INDEX ix_price_books_seller_id ON price_books(seller_id);
CREATE INDEX ix_price_books_branch_id ON price_books(branch_id);
CREATE INDEX ix_price_books_tenant_status ON price_books(tenant_id, status);
CREATE INDEX ix_price_books_effective ON price_books(effective_from, effective_to);
```

#### Field Specifications:
- `tenant_id`: Mandatory tenant boundary.
- `seller_id`: Nullable. If `NULL`, book can serve as tenant/platform default. If set, scopes book to that specific seller.
- `branch_id`: Nullable. If set, scopes book specifically to that branch (overriding seller-wide book). Must belong to `seller_id`.
- `currency`: ISO-4217 standard 3-character code (default: `'USD'`).
- `status`: Lifecycle state:
  - `DRAFT`: In editing; excluded from active calculation.
  - `ACTIVE`: Available for calculation engine.
  - `INACTIVE`: Retired/archived; excluded from active calculation.
- `is_default`: Flag indicating if this book is the default fallback for the tenant or seller.
- `effective_from` / `effective_to`: Optional timestamp boundaries for seasonal, scheduled, or promotional pricing.

### 3.2 Entity: `PriceRule` (`price_rules` table)
Represents an individual pricing calculation rule attached to a `PriceBook`.

```sql
CREATE TABLE price_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    price_book_id UUID NOT NULL REFERENCES price_books(id) ON DELETE CASCADE,
    service_id UUID NULL REFERENCES services(id) ON DELETE CASCADE,
    service_item_id UUID NULL REFERENCES service_items(id) ON DELETE CASCADE,
    service_addon_id UUID NULL REFERENCES service_addons(id) ON DELETE CASCADE,
    rule_type VARCHAR(50) NOT NULL, -- FIXED, PER_ITEM, PER_UNIT, PER_WEIGHT
    component_type VARCHAR(50) NOT NULL DEFAULT 'BASE_PRICE', -- BASE_PRICE, SURCHARGE, DISCOUNT, TAX
    rate NUMERIC(12, 4) NOT NULL,
    rate_type VARCHAR(20) NOT NULL DEFAULT 'FLAT', -- FLAT, PERCENTAGE
    min_quantity NUMERIC(10, 2) NULL,
    max_quantity NUMERIC(10, 2) NULL,
    min_price NUMERIC(12, 4) NULL,
    max_price NUMERIC(12, 4) NULL,
    priority INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, INACTIVE
    effective_from TIMESTAMPTZ NULL,
    effective_to TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_price_rules_tenant_id ON price_rules(tenant_id);
CREATE INDEX ix_price_rules_price_book_id ON price_rules(price_book_id);
CREATE INDEX ix_price_rules_service_id ON price_rules(service_id);
CREATE INDEX ix_price_rules_service_item_id ON price_rules(service_item_id);
CREATE INDEX ix_price_rules_service_addon_id ON price_rules(service_addon_id);
CREATE INDEX ix_price_rules_status ON price_rules(status);
```

#### Field Specifications:
- `rule_type`:
  - `FIXED`: Applies flat rate regardless of item quantity or measurable units.
  - `PER_ITEM`: Multiplied by integer piece count (e.g. per shirt, per jacket).
  - `PER_UNIT`: Multiplied by measurable unit quantities (e.g. per square meter of rug, per linear foot).
  - `PER_WEIGHT`: Multiplied by weight (e.g. per kilogram of wash-and-fold laundry).
- `component_type`:
  - `BASE_PRICE`: Direct charge for the service, item, or add-on.
  - `SURCHARGE`: Additional fee (rush fee, oversized charge, heavy garment surcharge).
  - `DISCOUNT`: Reduction (volume discount, promo discount).
  - `TAX`: Sales tax, VAT, or municipal surcharge.
- `rate`: Numeric value stored in `NUMERIC(12, 4)` for high-precision calculations.
- `rate_type`:
  - `FLAT`: Absolute currency value (e.g. `$15.00` or `$2.50/kg`).
  - `PERCENTAGE`: Percentage applied to base or subtotal (e.g. `8.25%` tax or `10%` discount).
- `priority`: Integer priority score. Higher values resolve earlier / override lower values when multiple matching rules exist.
- `min_quantity` / `max_quantity`: Optional tier thresholds (e.g., minimum 5 kg for wash-and-fold).
- `min_price` / `max_price`: Optional minimum charge (floor) or maximum cap (ceiling).

---

## 4. Deterministic Precedence & Calculation Engine Specification

### 4.1 Precedence Resolution Hierarchy
When calculating the price for a customer request, the engine evaluates candidates across four hierarchical levels:

$$\text{Platform Default} \longrightarrow \text{Seller Book} \longrightarrow \text{Branch Override Book} \longrightarrow \text{Rule Specificity}$$

```
Level 1: Platform / Tenant Default
  └── Active PriceBook with is_default=True AND seller_id IS NULL AND branch_id IS NULL

Level 2: Seller Default
  └── Active PriceBook where seller_id = target_seller_id AND branch_id IS NULL

Level 3: Branch Specific Override
  └── Active PriceBook where seller_id = target_seller_id AND branch_id = target_branch_id

Level 4: Rule Specificity within Matched Book
  └── Rule with specific service_item_id > Rule with specific service_id > Generic rule
  └── In case of equal catalog specificity: Highest priority wins
```

#### Resolution Algorithm:
1. Identify all active candidate `PriceBooks` belonging to the tenant:
   - If `branch_id` is supplied: check for an active `PriceBook` scoped to `branch_id`.
   - If no branch book matches or no rule found: check for an active `PriceBook` scoped to `seller_id` (with `branch_id IS NULL`).
   - If no seller book matches or rule not found: fallback to an active default `PriceBook` with `seller_id IS NULL` (Platform Default).
2. For each requested line item (and associated add-ons):
   - Locate the most specific rule matching the entity:
     - Priority 1: `service_item_id == item.id`
     - Priority 2: `service_id == item.service_id` (fallback when no specific item rule exists)
     - For add-ons: `service_addon_id == addon.id`
   - Filter rules by effective date:
     - `(rule.effective_from IS NULL OR rule.effective_from <= calculation_date)` AND
     - `(rule.effective_to IS NULL OR rule.effective_to >= calculation_date)`
   - Filter rules by status: `rule.status == 'ACTIVE'`.
   - If multiple candidates remain: select rule with maximum `priority`.

### 4.2 Rule Calculation Formulas (Strict Decimal Arithmetic)

All arithmetic operations MUST execute using Python's `Decimal` class (`from decimal import Decimal, ROUND_HALF_UP`). Zero floating-point arithmetic is permitted.

#### 1. Base Price Calculation
- **`FIXED`**:
  $$\text{Base} = \text{rate}$$
- **`PER_ITEM`**:
  $$\text{Base} = \text{rate} \times \text{Decimal}(quantity)$$
- **`PER_UNIT`**:
  $$\text{Base} = \text{rate} \times \text{Decimal}(units)$$
- **`PER_WEIGHT`**:
  $$\text{Base} = \text{rate} \times \text{Decimal}(weight)$$

*Boundary Check*: If `min_price` is specified and $\text{Base} < \text{min\_price}$, then $\text{Base} = \text{min\_price}$. If `max_price` is specified and $\text{Base} > \text{max\_price}$, then $\text{Base} = \text{max\_price}$.

#### 2. Surcharges
- Flat Surcharge: $\text{Amount} = \text{rate}$ (or $\text{rate} \times quantity$ if per-item).
- Percentage Surcharge: $\text{Amount} = \text{Item Base} \times \left(\frac{\text{rate}}{100}\right)$.

#### 3. Discounts
- Flat Discount: $\text{Amount} = \min(\text{rate}, \text{Current Subtotal})$.
- Percentage Discount: $\text{Amount} = \text{Current Subtotal} \times \left(\frac{\text{rate}}{100}\right)$.

#### 4. Taxes
- Applicable to taxable base: $\text{Taxable Subtotal} = \text{Subtotal} + \text{Total Surcharges} - \text{Total Discounts}$.
- Percentage Tax: $\text{Tax Amount} = \text{Taxable Subtotal} \times \left(\frac{\text{tax\_rate}}{100}\right)$.

### 4.3 Normalized Breakdown Structure & Invariant Equation

The calculation output returns a strictly normalized breakdown:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Subtotal        = Σ(Base Price of Items + Addons)        │
│ 2. Surcharges      = Σ(Applicable Surcharge Rules)          │
│ 3. Discounts       = Σ(Applicable Discount Rules)           │
│ 4. Taxable Amount  = Subtotal + Surcharges - Discounts      │
│ 5. Taxes           = Σ(Applicable Tax Rules)                │
│─────────────────────────────────────────────────────────────│
│ GRAND TOTAL        = Subtotal + Surcharges - Discounts + Tax │
└─────────────────────────────────────────────────────────────┘
```

**The Invariant Condition**:
$$\text{grand\_total} \equiv \text{subtotal} + \text{total\_surcharges} - \text{total\_discounts} + \text{total\_tax}$$
Any calculation result where this equality does not hold to the cent ($0.01$) must raise a `CalculationInvariantError`.

---

## 5. Security, RBAC & Multi-Tenant Isolation Specifications

### 5.1 Strict Tenant Isolation
- Every pricing repository method takes `tenant_id: UUID` as an explicit argument and includes `filter(Model.tenant_id == tenant_id)`.
- Rejection of cross-tenant entities:
  - If a user in Tenant A attempts to read or mutate a `price_book_id` belonging to Tenant B, the API returns `404 Not Found`.
  - If a user in Tenant A attempts to create a price book or rule referencing a `seller_id`, `branch_id`, `service_id`, `service_item_id`, or `service_addon_id` belonging to Tenant B, the service validates ownership and aborts with `404 Not Found` or `400 Bad Request`.
- Client ID Spoofing Defense: Tenant resolution relies exclusively on `TenantContext` resolved via signed session/token or header validated against active memberships.

### 5.2 Granular Permissions Matrix

| Role | `pricing.read` | `pricing.manage` | Description / Capabilities |
|---|:---:|:---:|---|
| **PLATFORM_ADMIN** | ✅ | ✅ | Unrestricted platform control across all tenants |
| **PLATFORM_SUPPORT** | ✅ | ❌ | Operational read visibility; cannot mutate pricing |
| **TENANT_OWNER** | ✅ | ✅ | Full organizational control over tenant pricing |
| **TENANT_ADMIN** | ✅ | ✅ | Manages tenant pricing books and rules |
| **TENANT_MEMBER** | ❌ | ❌ | Standard operational member; no pricing access |
| **TENANT_VIEWER** | ❌ | ❌ | Restricted viewer; no pricing access |
| **SELLER_OWNER** | ✅ | ✅ | Full control over seller price books and overrides |
| **SELLER_ADMIN** | ✅ | ✅ | Administers seller and branch pricing |
| **STAFF** | ✅ | ❌ | Operational staff; can quote prices, cannot alter rules |
| **VIEWER** | ✅ | ❌ | Read-only access; mutations strictly blocked (403) |

#### Seed Configuration Updates Required:
1. `app/core/permissions/constants.py`:
   - `PermissionName.PRICING_READ = 'pricing.read'`
   - `PermissionName.PRICING_MANAGE = 'pricing.manage'`
   - Update `DEFAULT_ROLE_PERMISSIONS` dictionary for all applicable roles.
2. `app/services/roles.py`:
   - Update `PERMISSION_DESCRIPTIONS` dictionary with human-readable descriptions for both permissions to ensure `RoleService.seed_defaults()` succeeds and unit test `test_rbac_seed.py` passes.

### 5.3 AuditService Lifecycle Events
All mutations must emit audit trails via `AuditService.log_event`:
- `PRICING_BOOK_CREATED`: `{ "book_id": str, "name": str, "seller_id": str | None }`
- `PRICING_BOOK_UPDATED`: `{ "book_id": str, "updated_fields": list }`
- `PRICING_BOOK_STATUS_CHANGED`: `{ "book_id": str, "old_status": str, "new_status": str }`
- `PRICING_RULE_CREATED`: `{ "rule_id": str, "book_id": str, "rule_type": str, "rate": str }`
- `PRICING_RULE_UPDATED`: `{ "rule_id": str, "updated_fields": list }`
- `PRICING_RULE_DELETED`: `{ "rule_id": str, "book_id": str }`

---

## 6. API Specification & Route Contracts

All endpoints are prefixed under `/api/v1/pricing`.

### 6.1 Price Book Management Endpoints

#### 1. Create Price Book
- **Endpoint**: `POST /api/v1/pricing/books`
- **Permission**: `pricing.manage`
- **Request Body**:
  ```json
  {
    "seller_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "branch_id": null,
    "name": "Standard Seller Catalog Pricing",
    "description": "Base pricing for standard items",
    "currency": "USD",
    "is_default": true,
    "effective_from": "2026-01-01T00:00:00Z",
    "effective_to": null
  }
  ```
- **Response**: `201 Created` with `PriceBookResponse`.

#### 2. List Price Books
- **Endpoint**: `GET /api/v1/pricing/books?seller_id={id}&branch_id={id}&status={status}`
- **Permission**: `pricing.read`
- **Response**: `200 OK` with `list[PriceBookResponse]`.

#### 3. Get Price Book by ID
- **Endpoint**: `GET /api/v1/pricing/books/{book_id}`
- **Permission**: `pricing.read`
- **Response**: `200 OK` with `PriceBookDetailResponse` (includes associated rules).

#### 4. Update Price Book
- **Endpoint**: `PATCH /api/v1/pricing/books/{book_id}`
- **Permission**: `pricing.manage`
- **Request Body**: `PriceBookUpdate`
- **Response**: `200 OK` with `PriceBookResponse`.

#### 5. Activate / Deactivate Price Book
- **Endpoint**: `POST /api/v1/pricing/books/{book_id}/activate`
- **Endpoint**: `POST /api/v1/pricing/books/{book_id}/deactivate`
- **Permission**: `pricing.manage`
- **Response**: `200 OK` with updated `PriceBookResponse`.

### 6.2 Price Rule Management Endpoints

#### 6. Create Price Rule
- **Endpoint**: `POST /api/v1/pricing/books/{book_id}/rules`
- **Permission**: `pricing.manage`
- **Request Body**:
  ```json
  {
    "service_id": "0d2c3be4-8a4b-4fd3-b3c1-1e967a544df1",
    "service_item_id": "c1f729b1-098e-4a6c-9a4f-56de20311234",
    "service_addon_id": null,
    "rule_type": "PER_ITEM",
    "component_type": "BASE_PRICE",
    "rate": "7.50",
    "rate_type": "FLAT",
    "priority": 10,
    "effective_from": null,
    "effective_to": null
  }
  ```
- **Response**: `201 Created` with `PriceRuleResponse`.

#### 7. Update / Delete Price Rule
- **Endpoint**: `PATCH /api/v1/pricing/books/{book_id}/rules/{rule_id}`
- **Endpoint**: `DELETE /api/v1/pricing/books/{book_id}/rules/{rule_id}`
- **Permission**: `pricing.manage`
- **Response**: `200 OK` (PATCH) / `204 No Content` (DELETE).

### 6.3 Deterministic Calculation Endpoint

#### 8. Perform Pricing Calculation (Dry-Run / Quote)
- **Endpoint**: `POST /api/v1/pricing/calculate`
- **Permission**: `pricing.read`
- **Request Body**:
  ```json
  {
    "seller_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "branch_id": "b1b0cb7c-87d2-43bb-a5a4-96fe7444cfa2",
    "calculation_date": "2026-09-19T10:00:00Z",
    "currency": "USD",
    "items": [
      {
        "service_id": "0d2c3be4-8a4b-4fd3-b3c1-1e967a544df1",
        "service_item_id": "c1f729b1-098e-4a6c-9a4f-56de20311234",
        "quantity": 3,
        "units": null,
        "addons": [
          {
            "service_addon_id": "a9e62311-209f-4f8a-9a99-44be21623812",
            "quantity": 3
          }
        ]
      },
      {
        "service_id": "5f8a9e10-1234-4a6c-b3fc-3c963f66afa7",
        "service_item_id": null,
        "quantity": 1,
        "units": 4.5,
        "addons": []
      }
    ]
  }
  ```
- **Response**: `200 OK` with `PricingCalculationResult`:
  ```json
  {
    "currency": "USD",
    "subtotal": "38.50",
    "total_surcharges": "5.00",
    "total_discounts": "2.00",
    "taxable_amount": "41.50",
    "total_tax": "3.42",
    "grand_total": "44.92",
    "line_items": [
      {
        "service_id": "0d2c3be4-8a4b-4fd3-b3c1-1e967a544df1",
        "service_item_id": "c1f729b1-098e-4a6c-9a4f-56de20311234",
        "quantity": "3",
        "unit_price": "7.50",
        "base_amount": "22.50",
        "addons_amount": "4.50",
        "subtotal": "27.00",
        "applied_rule_ids": ["..."]
      },
      {
        "service_id": "5f8a9e10-1234-4a6c-b3fc-3c963f66afa7",
        "service_item_id": null,
        "quantity": "1",
        "units": "4.50",
        "unit_price": "2.5556",
        "base_amount": "11.50",
        "addons_amount": "0.00",
        "subtotal": "11.50",
        "applied_rule_ids": ["..."]
      }
    ],
    "components": [
      { "component_type": "BASE_PRICE", "name": "Item & Service Base", "amount": "38.50" },
      { "component_type": "SURCHARGE", "name": "Rush Expedited Surcharge", "amount": "5.00" },
      { "component_type": "DISCOUNT", "name": "Loyalty Volume Discount", "amount": "2.00" },
      { "component_type": "TAX", "name": "Sales Tax (8.25%)", "amount": "3.42" }
    ]
  }
  ```

---

## 7. Frontend Ecosystem & Shared Types

### 7.1 Shared Types: `packages/types/src/pricing.ts`

```typescript
export type PriceRuleType = 'FIXED' | 'PER_ITEM' | 'PER_UNIT' | 'PER_WEIGHT';
export type PricingComponentType = 'BASE_PRICE' | 'SURCHARGE' | 'DISCOUNT' | 'TAX';
export type PriceRateType = 'FLAT' | 'PERCENTAGE';
export type PriceBookStatus = 'DRAFT' | 'ACTIVE' | 'INACTIVE';

export interface PriceBook {
  id: string;
  tenant_id: string;
  seller_id?: string | null;
  branch_id?: string | null;
  name: string;
  description?: string | null;
  currency: string;
  status: PriceBookStatus;
  is_default: boolean;
  effective_from?: string | null;
  effective_to?: string | null;
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
  component_type: PricingComponentType;
  rate: string; // Decimal representation
  rate_type: PriceRateType;
  min_quantity?: string | null;
  max_quantity?: string | null;
  min_price?: string | null;
  max_price?: string | null;
  priority: number;
  status: 'ACTIVE' | 'INACTIVE';
  effective_from?: string | null;
  effective_to?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PricingCalculationItemInput {
  service_id: string;
  service_item_id?: string | null;
  quantity: number;
  units?: number | null;
  unit_type?: string | null;
  addons?: Array<{
    service_addon_id: string;
    quantity: number;
  }>;
}

export interface PricingCalculationRequest {
  seller_id: string;
  branch_id?: string | null;
  calculation_date?: string | null;
  currency?: string;
  items: PricingCalculationItemInput[];
}

export interface PricingComponentBreakdown {
  component_type: PricingComponentType;
  name: string;
  amount: string;
  rate?: string;
  rate_type?: PriceRateType;
}

export interface PricingLineItemBreakdown {
  service_id: string;
  service_item_id?: string | null;
  quantity: string;
  units?: string | null;
  unit_price: string;
  base_amount: string;
  addons_amount: string;
  subtotal: string;
  applied_rule_ids: string[];
}

export interface PricingCalculationResult {
  currency: string;
  subtotal: string;
  total_surcharges: string;
  total_discounts: string;
  taxable_amount: string;
  total_tax: string;
  grand_total: string;
  line_items: PricingLineItemBreakdown[];
  components: PricingComponentBreakdown[];
}
```

### 7.2 Monorepo Index Export
In `packages/types/src/index.ts`:
```typescript
export * from './pricing';
```

### 7.3 `apps/seller-web` UI Foundation
In `apps/seller-web/src/app/page.tsx` (or dedicated pricing route `/pricing`):
- Add a dedicated pricing card/button linking to or viewing Price Books.
- Display current seller pricing books and statuses.
- Use `@ttc/types` (`PriceBook`, `PricingCalculationResult`) for all interfaces.
- Zero local price calculation duplication — all calculation performed via API call to `/api/v1/pricing/calculate`.

---

## 8. Specification Discovery & Edge Cases Tables

### 8.1 Features Discovered
| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|---|---|---|---|---|---|---|
| 1 | Architecture | Modular Monolith Layering | API → Schema → Service → Repository → DB pattern for pricing | Route calls, Pydantic DTOs | Model instances, JSON DTOs | 400 Bad Request, 404 Not Found, 422 Validation Error | Inspection of `backend/app/` Phase 1-4 |
| 2 | Migration | Alembic Version Chaining | Phase 5 migration must extend revision `ddf173e6fc96` | Alembic op commands | Database schema updates | Migration conflict if branched or missing down_revision | Inspection of `backend/migrations/versions/` |
| 3 | Data Model | Price Books (`price_books`) | Scope pricing rules to tenant, seller, or branch with date validity | Book attributes (name, currency, seller_id, branch_id) | Created/updated `PriceBook` | 404 if seller/branch not in tenant; 400 on duplicate | ORIGINAL_REQUEST R2 & DISPATCH.md |
| 4 | Data Model | Price Rules (`price_rules`) | Specific rate definitions linked to catalog entities | Rule attributes (rule_type, component_type, rate, priority) | Created/updated `PriceRule` | 404 if catalog entities not found; 400 if invalid rate | ORIGINAL_REQUEST R2 & DISPATCH.md |
| 5 | Data Model | Pure Decimal Arithmetic | All monetary computations using arbitrary precision `Decimal` | Decimal string or Numeric inputs | Mathematically exact Decimal outputs | Reject float conversion; raise error on NaN or negative price | ORIGINAL_REQUEST R2 & Acceptance Criteria |
| 6 | Engine | FIXED Rule Type | Flat fee independent of unit quantity or count | Item or addon request with rule_type `FIXED` | Constant base amount = rate | Minimum price floor / maximum cap applied | ORIGINAL_REQUEST R2 & R3 |
| 7 | Engine | PER_ITEM Rule Type | Multiplied by integer piece count | Integer quantity | Base amount = rate * quantity | 400 if quantity <= 0 | ORIGINAL_REQUEST R2 & R3 |
| 8 | Engine | PER_UNIT Rule Type | Multiplied by continuous measurable unit | Units (Decimal) | Base amount = rate * units | 400 if units <= 0 | ORIGINAL_REQUEST R2 & R3 |
| 9 | Engine | PER_WEIGHT Rule Type | Multiplied by weight in KG or scale unit | Weight (Decimal) | Base amount = rate * weight | 400 if weight <= 0 | ORIGINAL_REQUEST R2 & R3 |
| 10 | Engine | 4-Tier Component Breakdown | Base Price, Surcharge, Discount, and Tax structured output | Raw item requests | Normalized breakdown objects | 500 / Invariant error if grand total != subtotal + surcharges - discounts + tax | ORIGINAL_REQUEST R2, R3 & Acceptance Criteria |
| 11 | Engine | Precedence Engine | Platform Default -> Seller -> Branch -> Rule evaluation | Request with seller_id and branch_id | Matched winning rule per item | Fallback to next tier if higher tier has no rule | ORIGINAL_REQUEST R3 & DISPATCH.md |
| 12 | Engine | Effective Date Filter | Filters books/rules based on `effective_from` and `effective_to` | `calculation_date` timestamp | Only effective rules considered | Ignore expired or future rules | ORIGINAL_REQUEST R3 |
| 13 | Engine | Active/Draft State Filter | Excludes `DRAFT` and `INACTIVE` books and rules | Status string | Only `ACTIVE` entities used | Draft entities return empty/fallback | ORIGINAL_REQUEST R3 & Acceptance Criteria |
| 14 | Security | Tenant Boundary Isolation | Hardcoded `tenant_id` filtering on all DB queries | `TenantContext` | Tenant-scoped results only | Cross-tenant queries return 404 Not Found | ORIGINAL_REQUEST R4 & Security tests |
| 15 | Security | ID Injection Defense | Prevents referencing foreign tenant entities | Foreign IDs in payload | Validated internal IDs | 404 Not Found when foreign ID specified | ORIGINAL_REQUEST R4 & Phase 4 test patterns |
| 16 | Security | Granular RBAC Permissions | `pricing.read` and `pricing.manage` permissions | User Role & Context | Access allowed or denied | 403 Forbidden for missing permission | ORIGINAL_REQUEST R4 & `constants.py` |
| 17 | Security | Privilege Escalation Protection | `VIEWER` and `STAFF` blocked from mutations | Token with `VIEWER` role | HTTP 403 Forbidden | Explicitly tested; mutation rejected | Acceptance Criteria & `constants.py` |
| 18 | Security | AuditService Lifecycle Trails | Emits audit events on all mutations | Event type and payload | Recorded `AuditEvent` row | Audit failure logged without crashing operation | `app/services/audit.py` & Phase 4 pattern |
| 19 | API | `/api/v1/pricing/calculate` | Dry-run pricing calculation without order persistence | Calculation request JSON | Detailed quotation breakdown | 404 for invalid seller/branch; 400 for bad input | ORIGINAL_REQUEST R3 & R5 |
| 20 | Frontend | Shared TypeScript Contracts | `@ttc/types` exports for books, rules, calculation result | TypeScript types in `packages/types` | Reusable NPM types | Typecheck failure if types desynced | ORIGINAL_REQUEST R5 & Phase 4 pattern |
| 21 | Frontend | Seller-Web Foundation UI | Visual foundation in `apps/seller-web` | Page components | Rendered UI card/view | TypeScript / Next.js build clean | ORIGINAL_REQUEST R5 & `apps/seller-web` |

### 8.2 Edge Cases
| # | Feature | Input | Observed Behavior / Required Handling |
|---|---|---|---|
| 1 | Test Harness | Running `pytest` without `import app.models` in `tests/conftest.py` | `Base.metadata.create_all` does not register all tables, causing `UndefinedTable` errors in `reset_database`. Implementer must ensure `conftest.py` imports `app.models`. |
| 2 | Precedence Engine | Branch book exists with no rules for item X, but Seller book has a rule for item X | Engine should fall back from Branch book to Seller book for that item, ensuring complete quotation. |
| 3 | Precedence Engine | Both Service-level rule ($10) and Item-level rule ($12) exist for item X in same book | Item-level rule is more specific and overrides the generic Service-level rule ($12 applied). |
| 4 | Effective Dating | Book is effective, but specific rule has expired `effective_to` | The rule is skipped; engine falls back to next applicable rule in hierarchy or raises error if required. |
| 5 | Effective Dating | Calculation date is `None` in request | Defaults to current UTC timestamp (`datetime.now(timezone.utc)`). |
| 6 | Rounding & Precision | Intermediate calculation yields 3-decimal amount (e.g. $10.125) | Half-up round to 2 decimals ($10.13), asserting invariant `grand_total == subtotal + surcharges - discounts + tax`. |
| 7 | Zero Quantity / Weight | Item with `quantity = 0` or `units = 0` | Rejected with `422 Unprocessable Entity` or `400 Bad Request`. |
| 8 | Negative Rates | Rule created with negative rate (e.g. rate = -5.00) | Rejected by schema validation (`rate >= 0`); discounts must use positive rates with `component_type = 'DISCOUNT'`. |
| 9 | Discounts Exceeding Subtotal | Total discount ($50) exceeds taxable subtotal ($30) | Discount clamped to subtotal ($30); grand total never drops below $0.00 unless negative balance explicitly supported. |
| 10 | Cross-Tenant ID Injection | Tenant A passes Tenant B's `service_id` in calculation payload | Service validates `service.tenant_id == ctx.tenant_id`, rejecting with `404 Not Found`. |
| 11 | Catalog Isolation | Attempting to read catalog item pricing from catalog endpoints | Catalog endpoints contain no price data; pricing must be queried via `/api/v1/pricing/`. |
| 12 | Draft Book Isolation | Active request matches only a `DRAFT` price book | Draft book is ignored; engine falls back to default active book or returns unpriced error. |

---

## 9. Monorepo Verification & Test Strategy

### 9.1 Test Suite Plan (`backend/tests/api/test_pricing.py` & `backend/tests/security/test_pricing_security.py`)
1. **`test_pricing_lifecycle`**:
   - Create a Seller, Service, and ServiceItem.
   - Create a PriceBook in `DRAFT` status.
   - Add rules: `PER_ITEM` base price ($5.00), `PER_ITEM` addon ($1.50), percentage surcharge (10%), tax (8.25%).
   - Verify calculation ignores book in `DRAFT`.
   - Activate PriceBook.
   - Execute calculation: verify exact mathematically computed `Decimal` breakdown and invariant check.
2. **`test_precedence_hierarchy`**:
   - Create Platform Default book ($10), Seller book ($8), and Branch book ($7).
   - Assert item calculated with branch returns $7.
   - Assert item calculated without branch returns $8.
   - Assert item for another seller without custom book falls back to platform default ($10).
3. **`test_pricing_isolation_and_id_injection`**:
   - Assert Tenant B cannot view or edit Tenant A's price books (`404 Not Found`).
   - Assert Tenant A cannot attach Tenant B's `seller_id` or `service_id` to a price book (`404 Not Found`).
4. **`test_pricing_permission_enforcement`**:
   - Authenticate user with role `VIEWER`.
   - Verify `GET /api/v1/pricing/books` succeeds (`200 OK`).
   - Verify `POST /api/v1/pricing/books` fails (`403 Forbidden`).
   - Verify `POST /api/v1/pricing/calculate` succeeds (`200 OK`).

### 9.2 Build Verification Commands
```bash
# Backend test verification
.venv/bin/pytest backend/tests

# Monorepo TypeScript & Lint verification
pnpm lint
pnpm typecheck
pnpm build
```

---

## 10. Conclusion & Recommended Next Steps
All functional and non-functional specifications, schemas, precedence algorithms, invariant equations, security policies, and integration contracts for Phase 5 are fully defined and cross-referenced against the existing Phase 1-4 codebase. 

The implementation team can immediately begin Phase 5 execution in exact conformance with this specification report.
