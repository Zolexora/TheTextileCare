# Pricing Engine Foundation: Schemas & Repository Strategy

**Document**: Strategy & Implementation Blueprint for Schemas & PricingRepository  
**Author**: Milestone 1 Explorer 3 (`explorer_m1_3`)  
**Target Milestone**: TTC Phase 5: Pricing Engine Foundation — Milestone 1  
**Target Files**:
- `backend/app/schemas/pricing.py`
- `backend/app/repositories/pricing.py`

---

## 1. Executive Summary & Scope

Phase 5 of The Textile Care (TTC) introduces the **Pricing Engine Foundation** — a deterministic, tenant-isolated, high-precision domain responsible for answering **"How much does it cost?"**, strictly segregated from the catalog domain ("What is being offered?").

This report delivers the authoritative architecture and production-ready implementation blueprints for:
1. **Pydantic Schemas (`backend/app/schemas/pricing.py`)**:
   - Export of all pricing enumerations (`PriceBookScope`, `PriceBookStatus`, `PriceRuleType`, `ComponentType`, `RateType`).
   - Request and response Data Transfer Objects (DTOs) for price books and price rules.
   - Request and response DTOs for the deterministic pricing calculation engine with normalized 4-tier breakdown.
   - Robust Pydantic V2 validations: ISO 4217 currency validation, non-negative monetary rate enforcement, chronological effective date validation (`effective_to >= effective_from`), and scope-to-entity consistency checks.
2. **Pricing Repository (`backend/app/repositories/pricing.py`)**:
   - Fully typed SQLAlchemy 2.0 repository extending `BaseRepository`.
   - Strict multi-tenant isolation enforcing `tenant_id == ctx.tenant.id` on every query, preventing cross-tenant leakage and ID injection.
   - Controlled platform default read policies (`tenant_id IS NULL`).
   - High-performance query `get_active_rules_for_calculation` tailored for the deterministic precedence resolution engine with eager relationship loading (`joinedload`) to prevent N+1 query overhead.

---

## 2. Architecture & Interface Alignment

### 2.1 Interface Contracts
Following `PROJECT.md` Section 53–67, the pricing domain communicates via clean interface contracts across milestones:

```
[REST API Layer - M3]
        │
        ▼ (DTOs: PriceBookCreate, PriceRuleCreate, PricingCalculationRequest)
[Service Layer - M2]
  ├── PricingService (CRUD, ID Injection Checks, AuditService)
  └── PricingCalculatorService (Deterministic Decimal Precedence Math)
        │
        ▼ (Repository Calls: get_book, list_books, get_active_rules_for_calculation)
[Data Access Layer - M1]
  └── PricingRepository (app/repositories/pricing.py)
        │
        ▼ (SQLAlchemy 2.0 select/where statements)
[Database Models - M1]
  ├── PriceBook (app/models/pricing.py)
  └── PriceRule (app/models/pricing.py)
```

### 2.2 Monetary & Precision Principles
In strict compliance with R2 and R3 in `ORIGINAL_REQUEST.md`:
- **Zero Floating-Point Drift**: All monetary values, rates, discounts, surcharges, taxes, and totals use Python's `Decimal` type. Floating-point arithmetic (`float`) is strictly prohibited.
- **Strict Invariant**:
  $$\text{grand\_total} = \text{subtotal} + \text{total\_surcharges} - \text{total\_discounts} + \text{total\_tax}$$
- Rounding: Standard currency rounding uses `Decimal('0.01')` with `ROUND_HALF_UP`.

---

## 3. Pydantic Schemas Blueprint (`backend/app/schemas/pricing.py`)

### 3.1 Enumerations
Pricing enums are implemented as string-based enums (`str, Enum`), ensuring native JSON serialization and Pydantic validation:
- `PriceBookScope`:
  - `PLATFORM_DEFAULT`: Platform-wide fallback price book (`tenant_id` is null or platform system tenant).
  - `SELLER`: Seller-specific price book covering all branches of that seller.
  - `BRANCH`: Branch-specific override price book for a specific branch.
- `PriceBookStatus`:
  - `DRAFT`: Inactive, under configuration, excluded from calculation.
  - `ACTIVE`: Active and eligible for calculation.
  - `ARCHIVED`: Soft-retired, excluded from calculation.
- `PriceRuleType`:
  - `FIXED`: Fixed flat fee regardless of quantity (e.g., $10 setup fee).
  - `PER_ITEM`: Multiplied by integer or decimal count of items (e.g., $5 per shirt).
  - `PER_UNIT`: Multiplied by specified unit quantity (e.g., $3 per pair/set).
  - `PER_WEIGHT`: Multiplied by measured weight in kilograms (e.g., $2.50 per kg).
- `ComponentType`:
  - `BASE_PRICE`: Core charge for the catalog service or item.
  - `SURCHARGE`: Additional fee (e.g., rush delivery, delicate fabric handling).
  - `DISCOUNT`: Reduction applied to subtotal or line item.
  - `TAX`: Mandatory statutory tax applied to taxable amount.
- `RateType`:
  - `FLAT`: Absolute monetary amount in currency (e.g., $5.00).
  - `PERCENTAGE`: Relative multiplier expressed as percentage (e.g., 10.0 for 10% or 0.10).

### 3.2 Field & Model Validations
The schemas enforce four levels of validation:
1. **Currency Format**:
   - Validated via regex `^[A-Z]{3}$` to ensure standard 3-letter ISO 4217 uppercase currency codes (e.g., `USD`, `EUR`, `GBP`, `CAD`).
2. **Monetary Rate Non-Negativity**:
   - `rate: Decimal = Field(..., ge=Decimal('0'))`.
   - Rates cannot be negative. Discounts are specified as positive rates, and the calculation engine subtracts them.
3. **Temporal Ordering**:
   - `@model_validator(mode='after')` ensures that if both `effective_from` and `effective_to` are present, `effective_to >= effective_from`. If violated, raises `ValueError`.
4. **Scope-to-Foreign-Key Consistency**:
   - If `scope == PriceBookScope.PLATFORM_DEFAULT`: `seller_id` and `branch_id` must be `None`.
   - If `scope == PriceBookScope.SELLER`: `seller_id` must be provided, and `branch_id` must be `None`.
   - If `scope == PriceBookScope.BRANCH`: both `seller_id` and `branch_id` must be provided.

### 3.3 Complete Code Blueprint: `backend/app/schemas/pricing.py`

```python
"""Pydantic V2 schemas for TTC Phase 5 Pricing Engine Foundation.

Defines request/response DTOs for Price Books, Price Rules, and Deterministic
Pricing Calculations with strict validation and Decimal precision.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ============================================================================
# Enumerations
# ============================================================================

class PriceBookScope(str, Enum):
    """Scope of applicability for a PriceBook."""
    PLATFORM_DEFAULT = "PLATFORM_DEFAULT"
    SELLER = "SELLER"
    BRANCH = "BRANCH"


class PriceBookStatus(str, Enum):
    """Lifecycle status of a PriceBook."""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class PriceRuleType(str, Enum):
    """Calculation mechanism for evaluating price rules."""
    FIXED = "FIXED"
    PER_ITEM = "PER_ITEM"
    PER_UNIT = "PER_UNIT"
    PER_WEIGHT = "PER_WEIGHT"


class ComponentType(str, Enum):
    """Pricing component category in normalized breakdown."""
    BASE_PRICE = "BASE_PRICE"
    SURCHARGE = "SURCHARGE"
    DISCOUNT = "DISCOUNT"
    TAX = "TAX"


class RateType(str, Enum):
    """Specifies whether rate is an absolute amount or percentage."""
    FLAT = "FLAT"
    PERCENTAGE = "PERCENTAGE"


# ============================================================================
# Currency Helper / Validator
# ============================================================================

CURRENCY_REGEX = re.compile(r"^[A-Z]{3}$")


def validate_currency_code(v: str) -> str:
    normalized = v.strip().upper()
    if not CURRENCY_REGEX.match(normalized):
        raise ValueError(f"Invalid ISO 4217 currency code: '{v}'. Must be a 3-letter uppercase string.")
    return normalized


# ============================================================================
# PriceBook Schemas
# ============================================================================

class PriceBookBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Descriptive name of the price book")
    description: str | None = Field(None, max_length=1000, description="Optional detailed description")
    currency: str = Field(default="USD", min_length=3, max_length=3, description="ISO 4217 currency code")
    priority: int = Field(default=0, description="Priority tie-breaker for conflicting books")
    is_active: bool = Field(default=True, description="Whether this price book is active")

    @field_validator("currency")
    @classmethod
    def check_currency(cls, v: str) -> str:
        return validate_currency_code(v)


class PriceBookCreate(PriceBookBase):
    scope: PriceBookScope = Field(
        default=PriceBookScope.SELLER,
        description="Applicability scope (PLATFORM_DEFAULT, SELLER, BRANCH)"
    )
    seller_id: uuid.UUID | None = Field(None, description="Target seller if scope is SELLER or BRANCH")
    branch_id: uuid.UUID | None = Field(None, description="Target branch if scope is BRANCH")

    @model_validator(mode="after")
    def validate_scope_and_identifiers(self) -> PriceBookCreate:
        if self.scope == PriceBookScope.PLATFORM_DEFAULT:
            if self.seller_id is not None or self.branch_id is not None:
                raise ValueError("PLATFORM_DEFAULT price books must not have seller_id or branch_id.")
        elif self.scope == PriceBookScope.SELLER:
            if self.seller_id is None:
                raise ValueError("SELLER scope price books require a valid seller_id.")
            if self.branch_id is not None:
                raise ValueError("SELLER scope price books must not have a branch_id.")
        elif self.scope == PriceBookScope.BRANCH:
            if self.seller_id is None or self.branch_id is None:
                raise ValueError("BRANCH scope price books require both seller_id and branch_id.")
        return self


class PriceBookUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    currency: str | None = Field(None, min_length=3, max_length=3)
    priority: int | None = None
    is_active: bool | None = None

    @field_validator("currency")
    @classmethod
    def check_currency(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_currency_code(v)
        return v


class PriceBookResponse(PriceBookBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID | None
    scope: PriceBookScope
    seller_id: uuid.UUID | None
    branch_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    rules_count: int | None = None


class PriceBookListParams(BaseModel):
    scope: PriceBookScope | None = None
    seller_id: uuid.UUID | None = None
    branch_id: uuid.UUID | None = None
    is_active: bool | None = None
    include_platform_defaults: bool = Field(default=True, description="Whether to include PLATFORM_DEFAULT books")


# ============================================================================
# PriceRule Schemas
# ============================================================================

class PriceRuleBase(BaseModel):
    name: str | None = Field(None, max_length=255, description="Optional human-readable rule name")
    service_id: uuid.UUID | None = Field(None, description="Catalog service target")
    service_item_id: uuid.UUID | None = Field(None, description="Specific catalog service item target")
    service_addon_id: uuid.UUID | None = Field(None, description="Specific catalog addon target")
    rule_type: PriceRuleType = Field(default=PriceRuleType.FIXED, description="Rule calculation type")
    component_type: ComponentType = Field(default=ComponentType.BASE_PRICE, description="Component tier")
    rate_type: RateType = Field(default=RateType.FLAT, description="FLAT or PERCENTAGE")
    rate: Decimal = Field(..., ge=Decimal("0.00"), description="Monetary rate or percentage")
    priority: int = Field(default=0, description="Tie-breaking priority within same specificity level")
    is_active: bool = Field(default=True, description="Whether this rule is active")
    effective_from: datetime | None = Field(None, description="Start of temporal validity window")
    effective_to: datetime | None = Field(None, description="End of temporal validity window")

    @model_validator(mode="after")
    def validate_effective_date_range(self) -> PriceRuleBase:
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("effective_to must be greater than or equal to effective_from.")
        return self


class PriceRuleCreate(PriceRuleBase):
    pass


class PriceRuleUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    service_id: uuid.UUID | None = None
    service_item_id: uuid.UUID | None = None
    service_addon_id: uuid.UUID | None = None
    rule_type: PriceRuleType | None = None
    component_type: ComponentType | None = None
    rate_type: RateType | None = None
    rate: Decimal | None = Field(None, ge=Decimal("0.00"))
    priority: int | None = None
    is_active: bool | None = None
    effective_from: datetime | None = None
    effective_to: datetime | None = None

    @model_validator(mode="after")
    def validate_effective_date_range(self) -> PriceRuleUpdate:
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("effective_to must be greater than or equal to effective_from.")
        return self


class PriceRuleResponse(PriceRuleBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID | None
    price_book_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Deterministic Pricing Calculation Schemas
# ============================================================================

class PricingCalculationItemRequest(BaseModel):
    service_id: uuid.UUID = Field(..., description="Target catalog service ID")
    service_item_id: uuid.UUID | None = Field(None, description="Target catalog service item ID")
    quantity: Decimal = Field(default=Decimal("1"), gt=Decimal("0"), description="Item quantity (must be > 0)")
    weight: Decimal | None = Field(None, ge=Decimal("0"), description="Item weight in kg for PER_WEIGHT rules")
    unit_type: str = Field(default="ITEM", max_length=50, description="Unit type (ITEM, KG, PAIR, SET)")
    addon_ids: list[uuid.UUID] = Field(default_factory=list, description="Selected addon IDs for this item")


class PricingCalculationRequest(BaseModel):
    seller_id: uuid.UUID = Field(..., description="Target seller")
    branch_id: uuid.UUID | None = Field(None, description="Optional branch for branch-level overrides")
    currency: str = Field(default="USD", min_length=3, max_length=3, description="Calculation currency")
    calculation_time: datetime | None = Field(
        None, description="Reference datetime for effective dates (defaults to UTC now)"
    )
    items: list[PricingCalculationItemRequest] = Field(
        ..., min_length=1, description="List of items to calculate pricing for"
    )

    @field_validator("currency")
    @classmethod
    def check_currency(cls, v: str) -> str:
        return validate_currency_code(v)


class PricingCalculationComponentBreakdown(BaseModel):
    name: str = Field(..., description="Name of rule or component")
    component_type: ComponentType
    rate_type: RateType
    rate: Decimal = Field(..., description="Configured rate or percentage")
    amount: Decimal = Field(..., description="Evaluated monetary impact (positive Decimal)")


class PricingCalculationItemResult(BaseModel):
    service_id: uuid.UUID
    service_item_id: uuid.UUID | None = None
    unit_price: Decimal = Field(..., description="Base rate per unit/item before multipliers")
    quantity: Decimal
    weight: Decimal | None = None
    base_price: Decimal = Field(..., description="Total base price for line item (rate * qty/weight)")
    surcharges: Decimal = Field(default=Decimal("0.00"), description="Total surcharges applied")
    discounts: Decimal = Field(default=Decimal("0.00"), description="Total discounts applied")
    tax: Decimal = Field(default=Decimal("0.00"), description="Total tax applied")
    subtotal: Decimal = Field(..., description="Line subtotal (base_price)")
    total: Decimal = Field(..., description="Line total (base_price + surcharges - discounts + tax)")
    applied_rule_ids: list[uuid.UUID] = Field(default_factory=list, description="IDs of rules matched")
    breakdown: list[PricingCalculationComponentBreakdown] = Field(default_factory=list)


class PricingCalculationResult(BaseModel):
    currency: str
    subtotal: Decimal = Field(..., description="Sum of all item base prices")
    total_surcharges: Decimal = Field(..., description="Sum of all surcharges across items")
    total_discounts: Decimal = Field(..., description="Sum of all discounts across items")
    total_tax: Decimal = Field(..., description="Sum of all taxes across items")
    grand_total: Decimal = Field(..., description="Subtotal + surcharges - discounts + tax")
    items: list[PricingCalculationItemResult] = Field(..., description="Detailed per-item calculation results")

    @model_validator(mode="after")
    def validate_grand_total_invariant(self) -> PricingCalculationResult:
        expected = self.subtotal + self.total_surcharges - self.total_discounts + self.total_tax
        if self.grand_total != expected:
            raise ValueError(
                f"Grand total invariant violated: grand_total ({self.grand_total}) "
                f"!= subtotal ({self.subtotal}) + surcharges ({self.total_surcharges}) "
                f"- discounts ({self.total_discounts}) + tax ({self.total_tax}) [Expected: {expected}]"
            )
        return self
```

---

## 4. Pricing Repository Blueprint (`backend/app/repositories/pricing.py`)

### 4.1 Multi-Tenant Isolation Architecture
Multi-tenancy in TTC is non-negotiable. The `PricingRepository` strictly maintains tenant isolation through the following technical guarantees:
1. **Authenticated Context Filter**:
   Every mutation query (`get_book`, `update_book`, `delete_book`, `create_rule`, `update_rule`, `delete_rule`) mandates `tenant_id` as the primary scoping filter.
2. **Platform Defaults Segregation**:
   - `PLATFORM_DEFAULT` books have `tenant_id IS NULL`.
   - Normal tenant operations CANNOT modify or delete platform default records.
   - Reading platform defaults is parameterized via `include_platform_defaults: bool = True` (only applied during listings and calculations, never on update/delete).
3. **ID Injection Defeat**:
   If an attacker in Tenant A attempts to fetch, update, delete, or link rules to an entity belonging to Tenant B by passing Tenant B's UUID, the repository query:
   ```sql
   SELECT * FROM price_books WHERE id = :foreign_id AND tenant_id = :tenant_a_id
   ```
   evaluates to zero rows. The method returns `None` or `False`. The higher-level service maps this directly to `404 Not Found`.

### 4.2 Query Optimization for Deterministic Calculation
Method `get_active_rules_for_calculation` retrieves all candidate active rules for a given tenant, seller, and optional branch in a single SQL query:
- Joins `PriceRule` with `PriceBook`.
- Eagerly loads the parent `PriceBook` using `joinedload(PriceRule.price_book)` so that the calculation service can evaluate book-level scope and priority without generating N+1 queries.
- Filters:
  1. `PriceBook.is_active == True` and `PriceRule.is_active == True`.
  2. Tenant ownership: `PriceBook.tenant_id == tenant_id OR (PriceBook.tenant_id IS NULL AND PriceBook.scope == 'PLATFORM_DEFAULT')`.
  3. Scope matching:
     - Branch match: `(scope == 'BRANCH' AND seller_id == :seller AND branch_id == :branch)`
     - Seller match: `(scope == 'SELLER' AND seller_id == :seller)`
     - Platform match: `(scope == 'PLATFORM_DEFAULT')`
  4. Temporal validity: `effective_from IS NULL OR effective_from <= as_of` AND `effective_to IS NULL OR effective_to >= as_of`.
- Order by: `PriceBook.priority.desc()`, `PriceRule.priority.desc()`, `PriceRule.created_at.desc()`.

### 4.3 Complete Code Blueprint: `backend/app/repositories/pricing.py`

```python
"""PricingRepository for TTC Phase 5 Pricing Engine Foundation.

Encapsulates all database operations for PriceBook and PriceRule entities
using SQLAlchemy 2.0 select/execute statements with strict multi-tenant isolation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Sequence

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.pricing import PriceBook, PriceRule, PriceBookScope
from app.repositories.base import BaseRepository
from app.schemas.pricing import PriceBookUpdate, PriceRuleUpdate


class PricingRepository(BaseRepository):
    """Repository managing PriceBook and PriceRule persistence with tenant isolation."""

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    # ========================================================================
    # PriceBook Operations
    # ========================================================================

    def get_book(
        self,
        tenant_id: uuid.UUID,
        book_id: uuid.UUID,
        include_platform_defaults: bool = False,
    ) -> PriceBook | None:
        """Retrieve a price book by ID ensuring tenant isolation."""
        stmt = select(PriceBook).where(PriceBook.id == book_id)

        if include_platform_defaults:
            stmt = stmt.where(
                or_(
                    PriceBook.tenant_id == tenant_id,
                    and_(
                        PriceBook.tenant_id.is_(None),
                        PriceBook.scope == PriceBookScope.PLATFORM_DEFAULT,
                    ),
                )
            )
        else:
            stmt = stmt.where(PriceBook.tenant_id == tenant_id)

        return self.db.execute(stmt).scalar_one_or_none()

    def list_books(
        self,
        tenant_id: uuid.UUID,
        scope: PriceBookScope | None = None,
        seller_id: uuid.UUID | None = None,
        branch_id: uuid.UUID | None = None,
        is_active: bool | None = None,
        include_platform_defaults: bool = True,
    ) -> Sequence[PriceBook]:
        """List price books matching tenant and optional scope/entity filters."""
        stmt = select(PriceBook)

        if include_platform_defaults:
            tenant_condition = or_(
                PriceBook.tenant_id == tenant_id,
                and_(
                    PriceBook.tenant_id.is_(None),
                    PriceBook.scope == PriceBookScope.PLATFORM_DEFAULT,
                ),
            )
        else:
            tenant_condition = (PriceBook.tenant_id == tenant_id)

        stmt = stmt.where(tenant_condition)

        if scope is not None:
            stmt = stmt.where(PriceBook.scope == scope)

        if seller_id is not None:
            if include_platform_defaults:
                stmt = stmt.where(
                    or_(
                        PriceBook.seller_id == seller_id,
                        PriceBook.scope == PriceBookScope.PLATFORM_DEFAULT,
                    )
                )
            else:
                stmt = stmt.where(PriceBook.seller_id == seller_id)

        if branch_id is not None:
            stmt = stmt.where(PriceBook.branch_id == branch_id)

        if is_active is not None:
            stmt = stmt.where(PriceBook.is_active == is_active)

        stmt = stmt.order_by(PriceBook.priority.desc(), PriceBook.created_at.desc())
        return self.db.execute(stmt).scalars().all()

    def create_book(self, tenant_id: uuid.UUID, book: PriceBook) -> PriceBook:
        """Persist a new price book for the tenant."""
        book.tenant_id = tenant_id
        self.db.add(book)
        self.db.flush()
        return book

    def update_book(
        self,
        tenant_id: uuid.UUID,
        book_id: uuid.UUID,
        data: dict[str, Any] | PriceBookUpdate,
    ) -> PriceBook | None:
        """Update a tenant's price book metadata. Rejects cross-tenant mutation."""
        book = self.get_book(tenant_id, book_id, include_platform_defaults=False)
        if not book:
            return None

        update_dict = data.model_dump(exclude_unset=True) if isinstance(data, PriceBookUpdate) else data

        # Protected fields that cannot be altered via update
        immutable_fields = {"id", "tenant_id", "scope", "seller_id", "branch_id"}

        for field, value in update_dict.items():
            if field not in immutable_fields and hasattr(book, field):
                setattr(book, field, value)

        self.db.flush()
        return book

    def delete_book(self, tenant_id: uuid.UUID, book_id: uuid.UUID) -> bool:
        """Delete a tenant's price book and all its cascaded rules."""
        book = self.get_book(tenant_id, book_id, include_platform_defaults=False)
        if not book:
            return False

        self.db.delete(book)
        self.db.flush()
        return True

    # ========================================================================
    # PriceRule Operations
    # ========================================================================

    def get_rule(
        self,
        tenant_id: uuid.UUID,
        rule_id: uuid.UUID,
        include_platform_defaults: bool = False,
    ) -> PriceRule | None:
        """Retrieve a single price rule ensuring tenant isolation."""
        stmt = (
            select(PriceRule)
            .options(joinedload(PriceRule.price_book))
            .where(PriceRule.id == rule_id)
        )

        if include_platform_defaults:
            stmt = stmt.where(
                or_(
                    PriceRule.tenant_id == tenant_id,
                    PriceRule.tenant_id.is_(None),
                )
            )
        else:
            stmt = stmt.where(PriceRule.tenant_id == tenant_id)

        return self.db.execute(stmt).scalar_one_or_none()

    def list_rules_for_book(
        self,
        tenant_id: uuid.UUID,
        book_id: uuid.UUID,
        is_active: bool | None = None,
        include_platform_defaults: bool = True,
    ) -> Sequence[PriceRule]:
        """List all rules associated with a price book."""
        book = self.get_book(tenant_id, book_id, include_platform_defaults=include_platform_defaults)
        if not book:
            return []

        stmt = select(PriceRule).where(PriceRule.price_book_id == book_id)

        if is_active is not None:
            stmt = stmt.where(PriceRule.is_active == is_active)

        stmt = stmt.order_by(PriceRule.priority.desc(), PriceRule.created_at.asc())
        return self.db.execute(stmt).scalars().all()

    def create_rule(
        self,
        tenant_id: uuid.UUID,
        book_id: uuid.UUID,
        rule: PriceRule,
    ) -> PriceRule | None:
        """Create a price rule under a price book owned by the tenant."""
        book = self.get_book(tenant_id, book_id, include_platform_defaults=False)
        if not book:
            return None

        rule.tenant_id = tenant_id
        rule.price_book_id = book_id
        self.db.add(rule)
        self.db.flush()
        return rule

    def update_rule(
        self,
        tenant_id: uuid.UUID,
        rule_id: uuid.UUID,
        data: dict[str, Any] | PriceRuleUpdate,
    ) -> PriceRule | None:
        """Update a price rule belonging to the tenant."""
        rule = self.get_rule(tenant_id, rule_id, include_platform_defaults=False)
        if not rule:
            return None

        update_dict = data.model_dump(exclude_unset=True) if isinstance(data, PriceRuleUpdate) else data

        immutable_fields = {"id", "tenant_id", "price_book_id"}

        for field, value in update_dict.items():
            if field not in immutable_fields and hasattr(rule, field):
                setattr(rule, field, value)

        self.db.flush()
        return rule

    def delete_rule(self, tenant_id: uuid.UUID, rule_id: uuid.UUID) -> bool:
        """Delete a price rule belonging to the tenant."""
        rule = self.get_rule(tenant_id, rule_id, include_platform_defaults=False)
        if not rule:
            return False

        self.db.delete(rule)
        self.db.flush()
        return True

    # ========================================================================
    # Calculation Engine Rule Retrieval
    # ========================================================================

    def get_active_rules_for_calculation(
        self,
        tenant_id: uuid.UUID,
        seller_id: uuid.UUID,
        branch_id: uuid.UUID | None = None,
        as_of: datetime | None = None,
    ) -> Sequence[PriceRule]:
        """Fetch all eligible active rules across Branch, Seller, and Platform Default scopes.

        Used directly by PricingCalculatorService for deterministic precedence evaluation.
        Eagerly loads `price_book` to prevent N+1 queries during precedence scoring.
        """
        ref_time = as_of or datetime.now(timezone.utc)

        scope_conditions = [
            # 1. Seller scope book matching the seller
            and_(
                PriceBook.scope == PriceBookScope.SELLER,
                PriceBook.seller_id == seller_id,
            ),
            # 2. Platform default book
            (PriceBook.scope == PriceBookScope.PLATFORM_DEFAULT),
        ]

        # 3. Branch scope book if branch_id is provided
        if branch_id is not None:
            scope_conditions.append(
                and_(
                    PriceBook.scope == PriceBookScope.BRANCH,
                    PriceBook.seller_id == seller_id,
                    PriceBook.branch_id == branch_id,
                )
            )

        stmt = (
            select(PriceRule)
            .join(PriceBook, PriceRule.price_book_id == PriceBook.id)
            .options(joinedload(PriceRule.price_book))
            .where(
                PriceBook.is_active.is_(True),
                PriceRule.is_active.is_(True),
                # Tenant isolation: tenant's books OR platform defaults
                or_(
                    PriceBook.tenant_id == tenant_id,
                    and_(
                        PriceBook.tenant_id.is_(None),
                        PriceBook.scope == PriceBookScope.PLATFORM_DEFAULT,
                    ),
                ),
                or_(*scope_conditions),
                # Temporal filtering on PriceRule
                or_(PriceRule.effective_from.is_(None), PriceRule.effective_from <= ref_time),
                or_(PriceRule.effective_to.is_(None), PriceRule.effective_to >= ref_time),
            )
            .order_by(
                PriceBook.priority.desc(),
                PriceRule.priority.desc(),
                PriceRule.created_at.desc(),
            )
        )

        return self.db.execute(stmt).scalars().all()
```

---

## 5. Security, Isolation & Adversarial Hardening Verification

To guarantee that the implementation satisfies all security criteria from `ORIGINAL_REQUEST.md`, test cases must explicitly verify:

| Vulnerability / Test Vector | Attack Description | Repository / Schema Defense | Expected Status / Result |
|---|---|---|---|
| **Cross-Tenant Mutation** | Tenant A attempts `update_book` or `delete_book` targeting Tenant B's `book_id` | `get_book(tenant_a_id, book_b_id)` returns `None` due to `PriceBook.tenant_id == tenant_a_id` | Returns `None` / `False` -> Service maps to `404 Not Found` |
| **Cross-Tenant Rule Addition** | Tenant A sends `create_rule` targeting Tenant B's `book_id` | `create_rule` checks `get_book(tenant_a_id, book_id)`, finds `None`, aborts insert | Returns `None` -> Service maps to `404 Not Found` |
| **Cross-Tenant Read Leak** | Tenant A calls `get_book` or `get_rule` with Tenant B's entity UUID | Where clause restricts to `tenant_id == tenant_a_id` | Returns `None` -> 404 (does not leak entity existence) |
| **Negative Rate Injection** | User submits `rate = -50.00` in `PriceRuleCreate` | Pydantic validator `Field(..., ge=Decimal('0.00'))` fails | 422 Unprocessable Entity |
| **Invalid Date Window** | User submits `effective_from = 2026-10-01`, `effective_to = 2026-09-01` | Pydantic `@model_validator` asserts `effective_to >= effective_from` | 422 Unprocessable Entity (`ValueError`) |
| **Scope Inconsistency** | User creates `PLATFORM_DEFAULT` book with `branch_id = UUID(...)` | Schema `@model_validator` asserts platform defaults have no seller/branch | 422 Unprocessable Entity (`ValueError`) |
| **Platform Default Tampering**| Standard tenant attempts to delete/update platform default book | `get_book(include_platform_defaults=False)` rejects books where `tenant_id IS NULL` | Returns `None` / `False` -> 404 Not Found |

---

## 6. Implementation Checklist & Migration Handoff

For Implementer R1 and subsequent milestones:
1. **Schema File**: Write `backend/app/schemas/pricing.py` matching Section 3.3.
2. **Repository File**: Write `backend/app/repositories/pricing.py` matching Section 4.3.
3. **Schemas `__init__.py`**: Export all schemas and enums in `backend/app/schemas/__init__.py`.
4. **Repositories `__init__.py`**: Export `PricingRepository` in `backend/app/repositories/__init__.py`.
5. **Unit Verification**:
   - Verify with Pydantic model validation tests (`pytest backend/tests/unit/test_pricing_schemas.py`).
   - Verify repository multi-tenant queries with test fixtures (`pytest backend/tests/integration/test_pricing_repo.py`).
