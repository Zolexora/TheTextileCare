# Backend Architecture Survey & Phase 5 Pricing Engine Foundation Blueprint

**Date**: 2026-09-19  
**Explorer**: Teamwork Backend Architecture Explorer (`explorer_survey_2`)  
**Target Repository**: `/workspaces/TheTextileCare`  
**Milestone**: TTC Phase 5: Pricing Engine Foundation  

---

## 1. Executive Summary

This report provides a comprehensive architectural survey of the existing backend codebase for The Textile Care (TTC) and specifies the exact blueprints for implementing **Phase 5: Pricing Engine Foundation**.

The TTC backend is implemented as a clean, highly structured **Modular Monolith** using **FastAPI**, **SQLAlchemy 2.0 (DeclarativeBase)**, **PostgreSQL (via psycopg)**, and **Alembic**. It features strict multi-tenant isolation, declarative Role-Based Access Control (RBAC), comprehensive request lifecycle auditing, and strict domain boundaries.

In Phase 4, the **Catalog Domain** (`catalogs`, `catalog_categories`, `services`, `service_items`, `service_addons`, `service_branch_availability`) was established. A core architectural principle of TTC is the strict decoupling of **"What is being offered?"** (Catalog) from **"How much does it cost?"** (Pricing). The catalog models contain **zero** pricing fields.

Phase 5 introduces the **Pricing Engine Foundation** as a deterministic, tenant-isolated pricing service that:
1. Defines `price_books` and `price_rules` entities referencing Phase 4 catalog entities without duplicating data.
2. Supports rule types: `FIXED`, `PER_ITEM`, `PER_UNIT`, `PER_WEIGHT`.
3. Resolves deterministic precedence (**Platform Default → Seller → Branch → Rule**) with priority and effective date filtering (`effective_from` / `effective_to`).
4. Produces normalized component breakdowns (`base_price`/`subtotal`, `surcharges`, `discounts`, `tax`, `grand_total`) using exact Python `Decimal` arithmetic.
5. Emits lifecycle audit events via `AuditService`.
6. Enforces tenant isolation, prevents ID injection, blocks privilege escalation for `VIEWER` roles, and persists no customer orders or cart sessions.

---

## 2. Backend Project Layout & Core Architecture

### 2.1 File Structure & Modular Organization

The backend source is located at `/workspaces/TheTextileCare/backend/app/`:

```
backend/
├── alembic.ini                   # Alembic configuration (script_location = migrations)
├── pyproject.toml                # Dependencies (FastAPI, SQLAlchemy, Pydantic, Alembic, pytest)
├── migrations/                   # Alembic migration scripts
│   ├── env.py                    # Imports app.models, sets target_metadata = Base.metadata
│   └── versions/                 # Sequential version migrations (Phase 1 through 4)
├── tests/                        # Pytest test suite
│   ├── conftest.py               # Database reset fixture, seeding, mock headers
│   ├── api/                      # Router & endpoint tests (catalog, audit, tenants, etc.)
│   ├── integration/              # Database schema & constraint tests
│   ├── security/                 # Tenant isolation, RBAC, privilege escalation, owner protection
│   └── unit/                     # Config, error handling, RBAC seed tests
└── app/
    ├── main.py                   # FastAPI entrypoint, middleware, exception handlers
    ├── config.py                 # Pydantic BaseSettings (Settings), DB URL, auth secrets
    ├── db.py                     # SQLAlchemy 2 DeclarativeBase, SessionLocal, get_db generator
    ├── dependencies.py           # FastAPI dependencies (auth, tenant context, permissions, roles)
    ├── lifecycle.py              # Application lifespan events
    ├── logging.py                # Structured logging configuration
    ├── api/
    │   ├── router.py             # Top-level API router mounting v1 domain routers
    │   └── v1/                   # REST endpoints (health, auth, tenants, memberships, roles,
    │                             # audit, sellers, configuration, catalog)
    ├── core/
    │   ├── exceptions/base.py    # Custom ApiError exception
    │   ├── middleware/security.py# SecurityHeadersMiddleware
    │   ├── permissions/constants.py # RoleName, PermissionName enums, DEFAULT_ROLE_PERMISSIONS
    │   ├── security/auth.py      # JWT validation, test/dev token extraction, user provisioning
    │   └── tenant/
    │       ├── context.py        # TenantContext dataclass
    │       └── resolver.py       # TenantResolver (header, membership, platform-admin check)
    ├── models/                   # SQLAlchemy 2 ORM models (DeclarativeBase)
    ├── schemas/                  # Pydantic V2 schemas (Base, Create, Update, Response)
    ├── repositories/             # Data access layer (CRUD, tenant-scoped queries)
    └── services/                 # Business logic, validation, audit event emission
```

### 2.2 Application Entrypoint & Middleware (`backend/app/main.py`)

- **FastAPI instantiation**: `app = FastAPI(title='The Textile Care API', version='0.1.0', lifespan=lifespan)`.
- **Middleware stack**:
  1. `CORSMiddleware`: Dynamic origin parsing from `settings.cors_allowed_origins`.
  2. `SecurityHeadersMiddleware`: Adds security headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Content-Security-Policy`).
  3. `add_request_id` (`@app.middleware('http')`): Extracts or generates `X-Request-Id` (UUID4) and appends it to response headers.
- **Exception handlers**:
  - `ApiError`: Maps custom application errors to standardized JSON responses with error code, message, and `request_id`.
  - `Exception`: Catches unhandled exceptions, returning a generic 500 `INTERNAL_ERROR` preventing internal stack leakage.
- **Router inclusion**: `app.include_router(api_router)` from `app.api.router`.

### 2.3 Router Mounting (`backend/app/api/router.py`)

All v1 endpoints are mounted under `/api/v1`:
```python
router.include_router(health_router, prefix='/api/v1')
router.include_router(auth_router, prefix='/api/v1')
router.include_router(tenants_router, prefix='/api/v1')
router.include_router(memberships_router, prefix='/api/v1')
router.include_router(roles_router, prefix='/api/v1')
router.include_router(audit_router, prefix='/api/v1')
router.include_router(sellers_router, prefix='/api/v1')
router.include_router(configuration_router, prefix='/api/v1')
router.include_router(catalog_router, prefix='/api/v1/catalog')
```
For Phase 5, `pricing_router` must be mounted as:
```python
from app.api.v1.pricing import router as pricing_router
router.include_router(pricing_router, prefix='/api/v1/pricing')
```

### 2.4 Database Session Management (`backend/app/db.py`)

- **Engine creation**: `engine = create_engine(settings.database_url, pool_pre_ping=True)`.
- **Session factory**: `SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)`.
- **Model Base**: `class Base(DeclarativeBase): pass` (SQLAlchemy 2.0 style).
- **Dependency**:
  ```python
  def get_db() -> Generator[Session, None, None]:
      db = SessionLocal()
      try:
          yield db
      finally:
          db.close()
  ```

---

## 3. Tenant Isolation & Security Architecture

Multi-tenancy is the foundational security boundary in TTC. Isolation is strictly enforced across three distinct layers:

### 3.1 Layer 1: Request-Time Tenant Resolution (`TenantResolver` & `TenantContext`)

Located at `backend/app/core/tenant/`:
- `TenantContext` (`core/tenant/context.py`):
  Dataclass holding:
  - `user`: `User` model
  - `tenant`: `Tenant` model
  - `membership`: `Membership | None`
  - `role`: `Role | None`
  - `permissions`: `set[str]`
  - `is_platform_admin`: `bool`
  - `is_platform_support`: `bool`
- `TenantResolver` (`core/tenant/resolver.py`):
  Resolves the current tenant context using:
  1. `X-Tenant-Id` header (or explicit tenant parameter).
  2. Validates tenant exists and `tenant.status == 'ACTIVE'`.
  3. Checks membership: `MembershipRepository.get_by_tenant_and_user(target_tenant_id, user.id)`.
  4. If user lacks active membership:
     - Allows platform admins / platform support into platform mode.
     - Otherwise raises `ApiError(status_code=403, code='ACCESS_DENIED', message='You do not have access to this tenant.')`.
  5. If no header is passed, falls back to the user's primary active membership.

### 3.2 Layer 2: Dependency Injection (`backend/app/dependencies.py`)

Endpoints declare security requirements declaratively:
- `require_authenticated_user`: Authenticates user from JWT Bearer token (or `X-User-Id` in dev/test).
- `require_tenant_context`: Injects `TenantContext` for the caller.
- `require_permission(permission_name: str)`: Enforces `context.has_permission(...)`. Platform admins bypass; all other users must have the explicit permission granted via their role. If missing, raises `ApiError(status_code=403, code='PERMISSION_DENIED')`.
- `require_role(*role_names: str)`: Restricts operation to specific role names.

### 3.3 Layer 3: Database & Repository Scoping

Every database query in repositories includes an explicit `where(Model.tenant_id == tenant_id)` filter.
Example from `CatalogRepository` (`app/repositories/catalog.py`):
```python
stmt = select(Catalog).where(
    Catalog.id == catalog_id,
    Catalog.tenant_id == tenant_id
)
```
- **Result**: Even if an attacker supplies a valid ID of an entity belonging to another tenant, the query returns `None`, resulting in a `404 Not Found`.

### 3.4 Cross-Tenant Reference & ID Injection Protection

When a tenant creates or modifies a record that references another entity (e.g. `seller_id`, `branch_id`, `service_id`):
1. The service layer verifies that the referenced entity exists **and** belongs to `ctx.tenant.id`.
2. Example from `CatalogService.create_catalog` (`app/services/catalog.py:45`):
   ```python
   seller = self.db.query(Seller).filter(
       Seller.id == data.seller_id,
       Seller.tenant_id == tenant_id
   ).first()
   if not seller:
       raise HTTPException(status_code=404, detail="Seller not found")
   ```
3. Attempting to attach pricing rules to catalog entities or branches owned by another tenant fails immediately with 404.

---

## 4. Authentication & RBAC System

### 4.1 Token Extraction & User Resolution (`backend/app/core/security/auth.py`)

- **JWT Decoding**: Validates JWT Bearer tokens against `settings.auth_secret` using `HS256`.
- **Dev/Test Bypasses**: In `development` and `test` environments (`settings.app_env in {'development', 'test'}`), accepts `X-User-Id`, `X-Auth-User-Id`, or test tokens without signatures.
- **Auto-Provisioning**: Auto-provisions user records in dev/test if authenticated identity has no DB record.
- **Account Status**: Rejects inactive/suspended accounts (`user.status != 'ACTIVE'`) with 403 `USER_SUSPENDED`.

### 4.2 Roles & Permissions Matrix (`backend/app/core/permissions/constants.py`)

#### Existing Roles (`RoleName`):
- Platform: `PLATFORM_ADMIN`, `PLATFORM_SUPPORT`
- Tenant Standard: `TENANT_OWNER`, `TENANT_ADMIN`, `TENANT_MEMBER`, `TENANT_VIEWER`
- Tenant Seller: `SELLER_OWNER`, `SELLER_ADMIN`, `STAFF`, `VIEWER`

#### Existing Permissions (`PermissionName`):
- Tenancy & Memberships: `tenant.read`, `tenant.manage`, `membership.read`, `membership.manage`
- Roles & Users: `role.read`, `role.manage`, `user.read`, `user.manage`
- Audit: `audit.read`
- Seller Platform: `seller.read`, `seller.manage`, `seller.branches.read`, `seller.branches.manage`, `seller.staff.read`, `seller.staff.manage`, `seller.settings.read`, `seller.settings.manage`
- Catalog (Phase 4): `catalog.read`, `catalog.manage`, `catalog.publish`, `catalog.categories.read`, `catalog.categories.manage`, `catalog.services.read`, `catalog.services.manage`, `catalog.addons.read`, `catalog.addons.manage`, `catalog.items.read`, `catalog.items.manage`
- Configuration (Phase 3): `configuration.read`, `configuration.manage`, `configuration.publish`, `configuration.definitions.read`, `configuration.definitions.manage`

#### Phase 5 Permissions Required:
- `PermissionName.PRICING_READ = 'pricing.read'`
- `PermissionName.PRICING_MANAGE = 'pricing.manage'`

#### Role Assignment Matrix for Phase 5:
Following the **principle of least privilege**:
- `PLATFORM_ADMIN`: `['pricing.read', 'pricing.manage']`
- `PLATFORM_SUPPORT`: `['pricing.read']`
- `TENANT_OWNER`, `SELLER_OWNER`: `['pricing.read', 'pricing.manage']`
- `TENANT_ADMIN`, `SELLER_ADMIN`: `['pricing.read', 'pricing.manage']`
- `TENANT_MEMBER`, `STAFF`: `['pricing.read']`
- `TENANT_VIEWER`, `VIEWER`: `['pricing.read']` (read-only, **cannot** mutate pricing)

### 4.3 Seeding & RBAC Validation (`RoleService.seed_defaults`)

- Defined in `backend/app/services/roles.py`.
- Maps permissions to descriptions via `PERMISSION_DESCRIPTIONS`.
- `seed_defaults()` iterates through `PERMISSION_DESCRIPTIONS` and `DEFAULT_ROLE_PERMISSIONS` to sync DB records.
- **Critical Requirement**: `backend/tests/unit/test_rbac_seed.py` line 28 asserts:
  ```python
  perms = {p.name: p for p in db.query(Permission).all()}
  assert set(perms.keys()) == {p.value for p in PermissionName}
  ```
  Therefore, every new entry in `PermissionName` **must** have an entry in `PERMISSION_DESCRIPTIONS` in `services/roles.py`, or the unit test suite will fail.

---

## 5. Phase 4 Catalog Domain Models Inspection

Catalog models are located in `backend/app/models/catalog.py`:

```
Catalog (1)
  ├── Category (0..*) [Hierarchical with parent_id]
  └── Service (0..*)
        ├── ServiceItem (0..*) [unit_type: ITEM, KG, PAIR, SET]
        ├── ServiceAddon (0..*)
        └── ServiceBranchAvailability (0..*)
```

### Table Schema Summary

| Table | Columns | Unique / Foreign Constraints |
|---|---|---|
| `catalogs` | `id`, `tenant_id`, `seller_id`, `name`, `description`, `status` (DRAFT, ACTIVE, INACTIVE), `created_by`, `updated_by`, `created_at`, `updated_at` | Unique(`tenant_id`, `seller_id`), FK `tenants`, FK `sellers`, FK `users` |
| `catalog_categories` | `id`, `tenant_id`, `catalog_id`, `parent_id`, `name`, `slug`, `description`, `image_url`, `sort_order`, `status`, `created_by`, `updated_by`, `created_at`, `updated_at` | Unique(`catalog_id`, `slug`), FK `catalogs`, FK `tenants`, Self-FK `parent_id` |
| `services` | `id`, `tenant_id`, `catalog_id`, `category_id`, `name`, `slug`, `description`, `short_description`, `service_type`, `status`, `sort_order`, `image_url`, `created_by`, `updated_by`, `created_at`, `updated_at` | Unique(`catalog_id`, `slug`), FK `catalogs`, FK `catalog_categories`, FK `tenants` |
| `service_items` | `id`, `tenant_id`, `service_id`, `name`, `code`, `description`, `unit_type`, `status`, `sort_order`, `created_at`, `updated_at` | Unique(`service_id`, `code`), FK `services`, FK `tenants` |
| `service_addons` | `id`, `tenant_id`, `service_id`, `name`, `code`, `description`, `status`, `sort_order`, `created_at`, `updated_at` | Unique(`service_id`, `code`), FK `services`, FK `tenants` |
| `service_branch_availability` | `id`, `tenant_id`, `service_id`, `branch_id`, `is_available`, `created_at`, `updated_at` | Unique(`service_id`, `branch_id`), FK `services`, FK `seller_branches`, FK `tenants` |

### Architectural Verification: Absence of Pricing in Catalog
Investigation confirms that **not a single price, amount, cost, currency, fee, or rate column** exists anywhere in `catalogs`, `catalog_categories`, `services`, `service_items`, `service_addons`, or `service_branch_availability`. The catalog strictly answers "What is being offered?", while Phase 5 Pricing Engine will answer "How much does it cost?".

---

## 6. AuditService Implementation

### 6.1 Model: `AuditEvent` (`backend/app/models/audit.py`)
- `id`: UUID primary key.
- `tenant_id`: UUID nullable (nullable for platform-level audit events).
- `actor_user_id`: UUID nullable (FK `users.id`, `ondelete='SET NULL'`).
- `event_type`: String(100), indexed (e.g., `CATALOG_CREATED`, `SELLER_UPDATED`).
- `entity_type`: String(100) nullable (e.g., `price_book`, `price_rule`).
- `entity_id`: String(100) nullable.
- `payload`: JSON dictionary storing contextual metadata.
- `created_at`: DateTime(timezone=True) server default `now()`.

### 6.2 Service: `AuditService` (`backend/app/services/audit.py`)
Provides:
```python
def log_event(
    self,
    event_type: str,
    payload: dict[str, Any] | None = None,
    tenant_id: uuid.UUID | None = None,
    actor_user_id: uuid.UUID | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
) -> AuditEvent
```

### 6.3 Standard Event Lifecycle Pattern for Phase 5 Pricing:
In `PricingService`:
- On create price book:
  `self.audit_service.log_event(event_type="PRICE_BOOK_CREATED", tenant_id=tenant_id, actor_user_id=user_id, entity_type="price_book", entity_id=str(book.id), payload={"name": book.name, "currency": book.currency})`
- On update price book:
  `self.audit_service.log_event(event_type="PRICE_BOOK_UPDATED", tenant_id=tenant_id, actor_user_id=user_id, entity_type="price_book", entity_id=str(book.id), payload=diff)`
- On status change (e.g., `ARCHIVED`, `ACTIVE`):
  `self.audit_service.log_event(event_type=f"PRICE_BOOK_{status}", ...)`
- On create/update/delete price rule:
  `self.audit_service.log_event(event_type="PRICE_RULE_CREATED", entity_type="price_rule", entity_id=str(rule.id), ...)`

---

## 7. Database & Alembic Migration Infrastructure

### 7.1 Migration Sequence & Current Head

Alembic configuration is in `backend/alembic.ini` and `backend/migrations/`.
Current migration history:

| Migration File | Revision ID | Revises (Down Revision) | Description |
|---|---|---|---|
| `0001_phase1_identity_and_tenancy.py` | `0001` | `None` | Tenants, Users, Roles, Permissions, Memberships, AuditEvents |
| `2010fc7ee67f_phase2_seller_platform.py` | `2010fc7ee67f` | `0001` | Sellers, Branches, StaffProfiles, SellerSettings, BusinessHours |
| `debba6592524_phase2_harden_seller_foundation.py` | `debba6592524` | `2010fc7ee67f` | Seller hardening and indexes |
| `275f700c133f_phase3_customization_engine.py` | `275f700c133f` | `debba6592524` | Applications, ApplicationModules, ConfigurationDefinitions, ConfigurationValues |
| `ddf173e6fc96_phase4_catalog_services.py` | `ddf173e6fc96` | `275f700c133f` | Catalogs, Categories, Services, ServiceItems, ServiceAddons, BranchAvailability |

Verification: Running `alembic heads` outputs:
`ddf173e6fc96 (head)`

### 7.2 Requirements for Phase 5 Migration
- **Do not rewrite or alter existing migrations.**
- Create a new migration file: `migrations/versions/<hash>_phase5_pricing_engine.py`.
- `down_revision = 'ddf173e6fc96'`.
- Define tables: `price_books` and `price_rules` (plus any necessary unique constraints and indexes).
- Upgrade and downgrade functions must be symmetric.

### 7.3 Model Registration in Alembic
In `backend/migrations/env.py`:
```python
import app.models  # noqa: F401
target_metadata = Base.metadata
```
When new models are declared in `app/models/pricing.py`, they must be imported and exposed in `app/models/__init__.py`. This ensures `Base.metadata` detects them automatically in Alembic and test runners.

---

## 8. Backend Test Suite & Fixture Architecture

### 8.1 Current Test Suite Status
Running `/workspaces/TheTextileCare/backend/.venv/bin/pytest` results in:
**`53 passed, 2 warnings in 92.26s`** (100% pass rate).

### 8.2 Test Organization
- `tests/api/`: REST API contracts and integration (e.g. `test_catalog.py`, `test_audit_api.py`, `test_memberships_api.py`).
- `tests/integration/`: DB constraints and schema tests (`test_database.py`).
- `tests/security/`: Tenant isolation, privilege escalation, role boundaries (`test_tenant_isolation.py`, `test_seller_isolation.py`, `test_owner_protection.py`).
- `tests/unit/`: RBAC seed integrity, configuration, error handling (`test_rbac_seed.py`, `test_config.py`).

### 8.3 Fixture Execution Lifecycle (`tests/conftest.py`)
- `reset_database` fixture:
  ```python
  @pytest.fixture(autouse=True)
  def reset_database():
      Base.metadata.drop_all(bind=engine)
      Base.metadata.create_all(bind=engine)
      with SessionLocal() as db:
          RoleService(db).seed_defaults()
      yield
  ```
- Fast in-memory / local PostgreSQL reset per test.
- Helper functions available:
  - `create_test_user(email, name, auth_user_id)`
  - `create_test_tenant(name, slug)`
  - `create_test_membership(tenant_id, user_id, role_name, status)`
  - `make_auth_headers(user, tenant)` -> returns `{'X-User-Id': str(user.id), 'X-Tenant-Id': str(tenant.id)}`

---

## 9. Phase 5 Pricing Engine Integration Blueprint

### 9.1 Data Model Architecture (`backend/app/models/pricing.py`)

#### Entity 1: `PriceBook`
Represents a collection of pricing rules for a given context and currency.

```python
class PriceBook(Base):
    __tablename__ = 'price_books'
    __table_args__ = (
        Index('ix_price_books_tenant_seller', 'tenant_id', 'seller_id'),
        Index('ix_price_books_tenant_status', 'tenant_id', 'status'),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True, index=True)
    seller_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('sellers.id', ondelete='CASCADE'), nullable=True, index=True)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('seller_branches.id', ondelete='CASCADE'), nullable=True, index=True)
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default='USD', nullable=False)
    
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default='DRAFT', nullable=False) # DRAFT, ACTIVE, INACTIVE, ARCHIVED
    
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    rules: Mapped[list[PriceRule]] = relationship('PriceRule', back_populates='price_book', cascade='all, delete-orphan')
    tenant: Mapped[Tenant | None] = relationship('Tenant')
    seller: Mapped[Seller | None] = relationship('Seller')
    branch: Mapped[Branch | None] = relationship('Branch')
```

#### Entity 2: `PriceRule`
Defines an individual pricing calculation rule referencing a catalog entity.

```python
class PriceRule(Base):
    __tablename__ = 'price_rules'
    __table_args__ = (
        Index('ix_price_rules_book_status', 'price_book_id', 'status'),
        Index('ix_price_rules_catalog_lookup', 'service_id', 'service_item_id', 'service_addon_id'),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=True, index=True)
    price_book_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('price_books.id', ondelete='CASCADE'), nullable=False, index=True)
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    
    # Rule Type: FIXED, PER_ITEM, PER_UNIT, PER_WEIGHT
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # Component Type: BASE_PRICE, SURCHARGE, DISCOUNT, TAX
    component_type: Mapped[str] = mapped_column(String(50), default='BASE_PRICE', nullable=False)
    
    # Rate Type: FLAT, PERCENTAGE
    rate_type: Mapped[str] = mapped_column(String(50), default='FLAT', nullable=False)
    
    # Monetary values using Numeric for exact Decimal handling
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True) # e.g. 5.5000
    rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)     # e.g. 0.0800 for 8%
    
    # Catalog References (loosely coupled via FK without copying catalog attributes)
    category_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('catalog_categories.id', ondelete='CASCADE'), nullable=True)
    service_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('services.id', ondelete='CASCADE'), nullable=True)
    service_item_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('service_items.id', ondelete='CASCADE'), nullable=True)
    service_addon_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('service_addons.id', ondelete='CASCADE'), nullable=True)
    
    # Resolution Controls
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default='ACTIVE', nullable=False) # DRAFT, ACTIVE, INACTIVE
    
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    price_book: Mapped[PriceBook] = relationship('PriceBook', back_populates='rules')
    service: Mapped[Service | None] = relationship('Service')
    service_item: Mapped[ServiceItem | None] = relationship('ServiceItem')
    service_addon: Mapped[ServiceAddon | None] = relationship('ServiceAddon')
```

### 9.2 Deterministic Calculation Engine (`app/services/pricing_calculator.py`)

#### A. Calculation Request & Result Contracts
The calculation service receives a calculation request:
- `tenant_id`: Authenticated tenant context.
- `seller_id`: Target seller.
- `branch_id`: Target branch (optional).
- `calculation_time`: Datetime for evaluating effective dates (defaults to `now(timezone.utc)`).
- `currency`: Default `USD`.
- `line_items`:
  - `service_id`: UUID
  - `service_item_id`: UUID | None
  - `quantity`: Decimal (default 1)
  - `weight`: Decimal | None (used when rule_type is `PER_WEIGHT`)
  - `unit_type`: str (e.g. `ITEM`, `KG`, `PAIR`, `SET`)
  - `addon_ids`: list[UUID]

#### B. Precedence Resolution Algorithm
For each line item (and addon), candidate active rules are gathered from candidate active price books:

1. **Precedence Hierarchy**:
   - **Scope Precedence**:
     - **Branch Level Book** (`seller_id == S`, `branch_id == B`): Precedence Weight = 300
     - **Seller Level Book** (`seller_id == S`, `branch_id == None`): Precedence Weight = 200
     - **Platform Default Book** (`tenant_id == None` or `is_default == True`, `seller_id == None`): Precedence Weight = 100
   - **Specificity Precedence** (within matching scope):
     - Item-specific rule (`service_item_id == line_item.service_item_id`): Specificity = 40
     - Addon-specific rule (`service_addon_id == line_item.addon_id`): Specificity = 40
     - Service-level rule (`service_id == line_item.service_id`, item is null): Specificity = 20
     - Category-level rule: Specificity = 10
     - General catch-all rule: Specificity = 0
   - **Rule Priority**:
     - `rule.priority` added as tie-breaker.
   - **Composite Score**: `(Precedence Weight) + (Specificity) + (Priority)`. Highest score wins for base price.

2. **Temporal & Lifecycle Filtering**:
   - Price book and rule `status` must both be `'ACTIVE'`.
   - `effective_from` must be `None` or `<= calculation_time`.
   - `effective_to` must be `None` or `>= calculation_time`.
   - Draft and inactive rules are completely ignored.

3. **Breakdown Computation with Exact Decimal**:
   - `Base Price`:
     - `FIXED`: `amount`
     - `PER_ITEM`: `amount * quantity`
     - `PER_UNIT`: `amount * quantity`
     - `PER_WEIGHT`: `amount * weight` (validates `weight > 0`)
   - `Surcharges`:
     - Applied to base price (either flat amount or `rate * base_price`).
   - `Discounts`:
     - Applied to base price + surcharges (either flat amount or `rate * (base_price + surcharges)`).
   - `Tax`:
     - Applied to taxable amount `(base_price + surcharges - discounts) * tax_rate`.
   - `Grand Total`:
     - Strictly enforced equality:
       `grand_total = (subtotal + total_surcharges - total_discounts + total_tax).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)`
   - All monetary components rounded to 2 decimal places with `ROUND_HALF_UP` without any floating-point conversions.

### 9.3 Security, Isolation, and Least-Privilege RBAC

1. **Deny Cross-Tenant Access**:
   - `tenant_id` is always derived from authenticated `ctx.tenant.id`.
   - Queries to `price_books` and `price_rules` require matching `tenant_id` (or `tenant_id is None` for platform read-only defaults).
   - Mutations by Tenant A against Tenant B price books return `404 Not Found`.
2. **Prevent ID Injection**:
   - When creating a price book or rule, any referenced `seller_id`, `branch_id`, `service_id`, `service_item_id`, or `service_addon_id` is queried against the database to confirm it exists and belongs to `ctx.tenant.id`. If not, a `404 Not Found` (or 400 Bad Request) is raised before saving.
3. **Role Enforcement**:
   - Mutations (`POST`, `PATCH`, `DELETE`) require `pricing.manage`.
   - Reads (`GET`, calculation) require `pricing.read`.
   - Users with role `VIEWER` or `TENANT_VIEWER` only possess `pricing.read`. Attempts to create or modify pricing return `403 Forbidden` (`PERMISSION_DENIED`).
4. **Audit Emission**:
   - Every mutation calls `AuditService.log_event(...)` with `tenant_id`, `actor_user_id`, `event_type`, and entity details.

### 9.4 API Endpoints Map (`backend/app/api/v1/pricing.py`)

| Method | Path | Permission Required | Description |
|---|---|---|---|
| `POST` | `/api/v1/pricing/books` | `pricing.manage` | Create a new PriceBook |
| `GET` | `/api/v1/pricing/books` | `pricing.read` | List PriceBooks for tenant (filter by seller_id, branch_id) |
| `GET` | `/api/v1/pricing/books/{book_id}` | `pricing.read` | Retrieve PriceBook details including rules |
| `PATCH` | `/api/v1/pricing/books/{book_id}` | `pricing.manage` | Update PriceBook metadata or status |
| `DELETE` | `/api/v1/pricing/books/{book_id}` | `pricing.manage` | Delete or archive PriceBook |
| `POST` | `/api/v1/pricing/books/{book_id}/rules` | `pricing.manage` | Add a PriceRule to a PriceBook |
| `GET` | `/api/v1/pricing/books/{book_id}/rules` | `pricing.read` | List PriceRules in a PriceBook |
| `GET` | `/api/v1/pricing/rules/{rule_id}` | `pricing.read` | Get specific PriceRule |
| `PATCH` | `/api/v1/pricing/rules/{rule_id}` | `pricing.manage` | Update a PriceRule |
| `DELETE` | `/api/v1/pricing/rules/{rule_id}` | `pricing.manage` | Delete a PriceRule |
| `POST` | `/api/v1/pricing/calculate` | `pricing.read` | Deterministic stateless price calculation |

### 9.5 Frontend & Shared Contracts Integration

1. **`packages/types/src/pricing.ts`**:
   Define shared TypeScript interfaces:
   ```typescript
   export type PriceRuleType = 'FIXED' | 'PER_ITEM' | 'PER_UNIT' | 'PER_WEIGHT';
   export type PricingComponentType = 'BASE_PRICE' | 'SURCHARGE' | 'DISCOUNT' | 'TAX';
   export type PricingRateType = 'FLAT' | 'PERCENTAGE';
   export type PriceBookStatus = 'DRAFT' | 'ACTIVE' | 'INACTIVE' | 'ARCHIVED';

   export interface PriceBook {
     id: string;
     tenant_id: string | null;
     seller_id: string | null;
     branch_id: string | null;
     name: string;
     description?: string | null;
     currency: string;
     is_default: boolean;
     status: PriceBookStatus;
     effective_from?: string | null;
     effective_to?: string | null;
     created_at: string;
     updated_at: string;
   }

   export interface PriceRule {
     id: string;
     price_book_id: string;
     name: string;
     rule_type: PriceRuleType;
     component_type: PricingComponentType;
     rate_type: PricingRateType;
     amount?: number | null;
     rate?: number | null;
     category_id?: string | null;
     service_id?: string | null;
     service_item_id?: string | null;
     service_addon_id?: string | null;
     priority: number;
     status: 'ACTIVE' | 'INACTIVE';
     effective_from?: string | null;
     effective_to?: string | null;
   }

   export interface PricingCalculationItemRequest {
     service_id: string;
     service_item_id?: string | null;
     quantity?: number;
     weight?: number | null;
     unit_type?: string;
     addon_ids?: string[];
   }

   export interface PricingCalculationRequest {
     seller_id: string;
     branch_id?: string | null;
     currency?: string;
     calculation_time?: string;
     items: PricingCalculationItemRequest[];
   }

   export interface PricingCalculationComponentBreakdown {
     name: string;
     component_type: PricingComponentType;
     rate_type: PricingRateType;
     amount: string; // Exact Decimal string representation
     rate?: string | null;
   }

   export interface PricingCalculationItemResult {
     service_id: string;
     service_item_id?: string | null;
     unit_price: string;
     quantity: string;
     weight?: string | null;
     base_price: string;
     surcharges: string;
     discounts: string;
     tax: string;
     subtotal: string;
     total: string;
     applied_rule_ids: string[];
     breakdown: PricingCalculationComponentBreakdown[];
   }

   export interface PricingCalculationResult {
     currency: string;
     subtotal: string;
     total_surcharges: string;
     total_discounts: string;
     total_tax: string;
     grand_total: string;
     items: PricingCalculationItemResult[];
   }
   ```
   Export from `packages/types/src/index.ts`.

2. **`apps/seller-web` Minimal Foundation**:
   - Provide a basic pricing view (`/pricing` route or pricing management section) that queries `/api/v1/pricing/books`.
   - Never duplicate calculation logic in the client; always call `/api/v1/pricing/calculate` for deterministic calculations.

---

## 10. File Modification & Creation Inventory

To implement Phase 5 without regression, the following backend files will be created or modified:

| Action | Path | Purpose |
|---|---|---|
| **Modify** | `backend/app/core/permissions/constants.py` | Add `PRICING_READ`, `PRICING_MANAGE` to `PermissionName` and update `DEFAULT_ROLE_PERMISSIONS` matrix |
| **Modify** | `backend/app/services/roles.py` | Add descriptions to `PERMISSION_DESCRIPTIONS` (satisfies `test_rbac_seed.py`) |
| **Create** | `backend/app/models/pricing.py` | Declare `PriceBook` and `PriceRule` models with Decimal columns and catalog FKs |
| **Modify** | `backend/app/models/__init__.py` | Export `PriceBook` and `PriceRule` to register with `Base.metadata` |
| **Create** | `backend/app/schemas/pricing.py` | Pydantic V2 schemas for PriceBook, PriceRule, and PricingCalculation |
| **Create** | `backend/app/repositories/pricing.py` | Repository with tenant-isolated queries for books and rules |
| **Create** | `backend/app/services/pricing.py` | CRUD business logic, validation, audit logging for books and rules |
| **Create** | `backend/app/services/pricing_calculator.py` | Deterministic precedence resolution and Decimal calculation algorithm |
| **Create** | `backend/app/api/v1/pricing.py` | FastAPI APIRouter endpoints for books, rules, and calculation |
| **Modify** | `backend/app/api/router.py` | Include `pricing_router` under prefix `/api/v1/pricing` |
| **Create** | `backend/migrations/versions/<hash>_phase5_pricing_engine.py` | Alembic migration with `down_revision = 'ddf173e6fc96'` |
| **Create** | `backend/tests/api/test_pricing.py` | API lifecycle, CRUD, calculation, and breakdown tests |
| **Create** | `backend/tests/security/test_pricing_isolation.py` | Cross-tenant isolation, ID injection, and VIEWER privilege escalation tests |
| **Create** | `backend/tests/unit/test_pricing_calculation.py` | Unit tests for deterministic precedence, Decimal precision, rounding, rule types |
| **Create** | `packages/types/src/pricing.ts` | Shared TypeScript interfaces for Pricing |
| **Modify** | `packages/types/src/index.ts` | Export pricing types |

---

## 11. Conclusion & Readiness Assessment

The existing codebase is in an exemplary state:
- Clean modular monolith architecture.
- Full multi-tenant isolation patterns consistently applied.
- All 53 existing backend tests pass.
- Alembic migration chain is clean, with head `ddf173e6fc96`.
- Catalog tables are completely free of pricing data, ready for clean foreign key references from `price_rules`.

The blueprint defined above adheres strictly to all requirements of TTC Phase 5:
- Preserves architectural integrity.
- Guarantees exact Decimal calculations and validated breakdowns (`Subtotal + surcharges - discounts + tax = grand total`).
- Prevents cross-tenant leaks and ID injection.
- Emits lifecycle audit events.
- Does not persist customer orders, cart, or payment sessions.
- Sets the foundation for clean implementation and testing.
