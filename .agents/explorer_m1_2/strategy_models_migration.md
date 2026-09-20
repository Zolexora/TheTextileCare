# Strategy & Implementation Blueprint: Models, Enums & Alembic Migration (TTC Phase 5)

**Document**: Strategy and Implementation Blueprint for Phase 5 Pricing Engine Foundation  
**Author**: Milestone 1 Explorer 2 (`explorer_m1_2`)  
**Target Repository**: `/workspaces/TheTextileCare`  
**Date**: 2026-09-19  

---

## 1. Executive Summary

This blueprint defines the authoritative data models, enums, relationship mappings, model exports, and Alembic database migration strategy for **Phase 5: Pricing Engine Foundation** in The Textile Care (TTC) backend.

### Architectural Core Principles
1. **Strict Catalog Decoupling**: The Catalog domain (`backend/app/models/catalog.py`) defines *"What is being offered?"* and contains **zero** pricing columns. The Pricing domain (`backend/app/models/pricing.py`) defines *"How much does it cost?"*, referencing catalog services, items, and add-ons strictly via foreign keys (`CASCADE` ondelete).
2. **Deterministic Precedence Support**: The models cleanly express the 4-tier precedence hierarchy:
   $$\text{Platform Default} \longrightarrow \text{Seller Book} \longrightarrow \text{Branch Override Book} \longrightarrow \text{Rule Specificity}$$
3. **Multi-Tenant Isolation**: Every entity maintains an indexed `tenant_id` foreign key with `ondelete='CASCADE'`. `tenant_id` is nullable on `PriceBook` and `PriceRule` specifically to allow platform-wide default books (`scope = 'PLATFORM_DEFAULT'`).
4. **Arbitrary-Precision Monetary Decimals**: Rates are stored as `Numeric(10, 2)` (mapping to Python `Decimal`), eliminating floating-point drift and rounding errors.
5. **SQLAlchemy 2.0 & Python (str, Enum) Integration**: Enums inherit from `(str, Enum)` for seamless Pydantic serialization and JSON compatibility. Mapped columns use `mapped_column` and `Mapped[...]` type annotations.

---

## 2. Enums Architecture & Specifications

All enums inherit from `str, enum.Enum` to ensure JSON serialization compatibility, string comparison equality, and seamless integration with Pydantic v2 schemas and FastAPI request parameters.

### 2.1 Enum Definitions (`backend/app/models/pricing.py`)

```python
import enum

class PriceBookScope(str, enum.Enum):
    """Defines the hierarchy level of a price book."""
    PLATFORM_DEFAULT = "PLATFORM_DEFAULT"
    SELLER = "SELLER"
    BRANCH = "BRANCH"


class PriceBookStatus(str, enum.Enum):
    """Lifecycle state of a price book."""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class PriceRuleType(str, enum.Enum):
    """Calculation method for price computation."""
    FIXED = "FIXED"           # Flat charge independent of quantity/weight
    PER_ITEM = "PER_ITEM"     # Multiplied by piece count (integer)
    PER_UNIT = "PER_UNIT"     # Multiplied by measurable units (sq ft, meters)
    PER_WEIGHT = "PER_WEIGHT" # Multiplied by weight (kg, lbs)


class ComponentType(str, enum.Enum):
    """4-Tier financial breakdown category."""
    BASE_PRICE = "BASE_PRICE"
    SURCHARGE = "SURCHARGE"
    DISCOUNT = "DISCOUNT"
    TAX = "TAX"
```

### 2.2 Storage & Column Mapping Strategy: `native_enum=False`

**Recommendation: Use `SQLEnum(..., native_enum=False, length=50)`**

| Feature | `native_enum=False` (Recommended) | `native_enum=True` |
|---|---|---|
| **Database Type** | `VARCHAR(50)` (with or without check constraint) | PostgreSQL `CREATE TYPE ... AS ENUM` |
| **Consistency with TTC Codebase** | 100% consistent with `users.status`, `catalogs.status`, `service_items.unit_type` | Introduces new PG type management |
| **Test Fixture Stability** | Seamless: `Base.metadata.create_all()` and `drop_all()` in `tests/conftest.py` work without lingering PG enum type leaks | Lingering types can conflict across repeated teardown/setup cycles |
| **Alembic Migration Simplicity** | Direct table column creation, standard rollback | Requires explicit type creation and `drop()` on downgrade |
| **Type Safety in Python** | 100% type-checked in Python ORM and Pydantic | 100% type-checked in Python ORM and Pydantic |

---

## 3. Data Model Blueprints (`backend/app/models/pricing.py`)

### 3.1 Entity: `PriceBook` (`price_books` table)

#### Table Schema Summary:
- **`id`**: UUID primary key, default `uuid.uuid4`.
- **`tenant_id`**: UUID nullable (nullable for `PLATFORM_DEFAULT`), foreign key `tenants.id` ondelete `CASCADE`, indexed.
- **`name`**: `String(255)`, non-null.
- **`description`**: `String(1000)`, nullable.
- **`scope`**: `PriceBookScope`, non-null, default `PriceBookScope.SELLER`.
- **`status`**: `PriceBookStatus`, non-null, default `PriceBookStatus.ACTIVE`.
- **`seller_id`**: UUID nullable (populated when scope is `SELLER` or `BRANCH`), foreign key `sellers.id` ondelete `CASCADE`, indexed.
- **`branch_id`**: UUID nullable (populated when scope is `BRANCH`), foreign key `seller_branches.id` ondelete `CASCADE`, indexed.
- **`currency`**: `String(3)`, non-null, default `'USD'`.
- **`priority`**: `Integer`, non-null, default `0`.
- **`is_active`**: `Boolean`, non-null, default `True`.
- **`created_at`**: `DateTime(timezone=True)`, non-null, server default `func.now()`.
- **`updated_at`**: `DateTime(timezone=True)`, non-null, server default `func.now()`, onupdate `func.now()`.

#### Relationships:
- `tenant`: `Mapped[Tenant | None] = relationship('Tenant')`
- `seller`: `Mapped[Seller | None] = relationship('Seller')`
- `branch`: `Mapped[Branch | None] = relationship('Branch')`
- `rules`: `Mapped[list[PriceRule]] = relationship('PriceRule', back_populates='price_book', cascade='all, delete-orphan')`

### 3.2 Entity: `PriceRule` (`price_rules` table)

#### Table Schema Summary:
- **`id`**: UUID primary key, default `uuid.uuid4`.
- **`tenant_id`**: UUID nullable, foreign key `tenants.id` ondelete `CASCADE`, indexed.
- **`price_book_id`**: UUID non-null, foreign key `price_books.id` ondelete `CASCADE`, indexed.
- **`name`**: `String(255)`, nullable (optional label for the rule, e.g. "Express Rush Charge").
- **`description`**: `String(1000)`, nullable.
- **`service_id`**: UUID nullable (service-level pricing), foreign key `services.id` ondelete `CASCADE`, indexed.
- **`service_item_id`**: UUID nullable (item-level specific pricing), foreign key `service_items.id` ondelete `CASCADE`, indexed.
- **`service_addon_id`**: UUID nullable (add-on specific pricing), foreign key `service_addons.id` ondelete `CASCADE`, indexed.
- **`rule_type`**: `PriceRuleType`, non-null.
- **`component_type`**: `ComponentType`, non-null, default `ComponentType.BASE_PRICE`.
- **`rate`**: `Numeric(10, 2)`, non-null (represents exact Decimal rate/amount).
- **`effective_from`**: `DateTime(timezone=True)`, nullable.
- **`effective_to`**: `DateTime(timezone=True)`, nullable.
- **`is_active`**: `Boolean`, non-null, default `True`.
- **`priority`**: `Integer`, non-null, default `0`.
- **`created_at`**: `DateTime(timezone=True)`, non-null, server default `func.now()`.
- **`updated_at`**: `DateTime(timezone=True)`, non-null, server default `func.now()`, onupdate `func.now()`.

#### Relationships:
- `price_book`: `Mapped[PriceBook] = relationship('PriceBook', back_populates='rules')`
- `tenant`: `Mapped[Tenant | None] = relationship('Tenant')`
- `service`: `Mapped[Service | None] = relationship('Service')`
- `service_item`: `Mapped[ServiceItem | None] = relationship('ServiceItem')`
- `service_addon`: `Mapped[ServiceAddon | None] = relationship('ServiceAddon')`

---

## 4. Complete Source Code Blueprint: `backend/app/models/pricing.py`

```python
"""Pricing engine data models and enums for TTC Phase 5."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.catalog import Service, ServiceAddon, ServiceItem
    from app.models.seller import Branch, Seller
    from app.models.tenant import Tenant


class PriceBookScope(str, enum.Enum):
    """Precedence scope for price books."""
    PLATFORM_DEFAULT = "PLATFORM_DEFAULT"
    SELLER = "SELLER"
    BRANCH = "BRANCH"


class PriceBookStatus(str, enum.Enum):
    """Lifecycle status for price books."""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class PriceRuleType(str, enum.Enum):
    """Unit calculation type for price rules."""
    FIXED = "FIXED"
    PER_ITEM = "PER_ITEM"
    PER_UNIT = "PER_UNIT"
    PER_WEIGHT = "PER_WEIGHT"


class ComponentType(str, enum.Enum):
    """Financial breakdown component category."""
    BASE_PRICE = "BASE_PRICE"
    SURCHARGE = "SURCHARGE"
    DISCOUNT = "DISCOUNT"
    TAX = "TAX"


class PriceBook(Base):
    """Container for scoped pricing rules in TTC Phase 5."""
    __tablename__ = "price_books"
    __table_args__ = (
        Index("idx_price_books_tenant_scope", "tenant_id", "scope"),
        Index("idx_price_books_tenant_seller", "tenant_id", "seller_id"),
        Index("idx_price_books_tenant_branch", "tenant_id", "branch_id"),
        Index("idx_price_books_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    scope: Mapped[PriceBookScope] = mapped_column(
        SQLEnum(PriceBookScope, name="price_book_scope", native_enum=False, length=50),
        default=PriceBookScope.SELLER,
        nullable=False,
    )
    status: Mapped[PriceBookStatus] = mapped_column(
        SQLEnum(PriceBookStatus, name="price_book_status", native_enum=False, length=50),
        default=PriceBookStatus.ACTIVE,
        nullable=False,
    )
    seller_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sellers.id", ondelete="CASCADE"), nullable=True, index=True
    )
    branch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("seller_branches.id", ondelete="CASCADE"), nullable=True, index=True
    )
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    tenant: Mapped[Tenant | None] = relationship("Tenant")
    seller: Mapped[Seller | None] = relationship("Seller")
    branch: Mapped[Branch | None] = relationship("Branch")
    rules: Mapped[list[PriceRule]] = relationship(
        "PriceRule", back_populates="price_book", cascade="all, delete-orphan"
    )


class PriceRule(Base):
    """Specific pricing calculation rule referencing catalog entities."""
    __tablename__ = "price_rules"
    __table_args__ = (
        Index("idx_price_rules_book_service", "price_book_id", "service_id"),
        Index("idx_price_rules_book_item", "price_book_id", "service_item_id"),
        Index("idx_price_rules_book_addon", "price_book_id", "service_addon_id"),
        Index("idx_price_rules_book_active", "price_book_id", "is_active"),
        Index("idx_price_rules_tenant_id", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    price_book_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("price_books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    service_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), nullable=True, index=True
    )
    service_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("service_items.id", ondelete="CASCADE"), nullable=True, index=True
    )
    service_addon_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("service_addons.id", ondelete="CASCADE"), nullable=True, index=True
    )

    rule_type: Mapped[PriceRuleType] = mapped_column(
        SQLEnum(PriceRuleType, name="price_rule_type", native_enum=False, length=50),
        nullable=False,
    )
    component_type: Mapped[ComponentType] = mapped_column(
        SQLEnum(ComponentType, name="component_type", native_enum=False, length=50),
        default=ComponentType.BASE_PRICE,
        nullable=False,
    )
    rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    effective_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    effective_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    price_book: Mapped[PriceBook] = relationship("PriceBook", back_populates="rules")
    tenant: Mapped[Tenant | None] = relationship("Tenant")
    service: Mapped[Service | None] = relationship("Service")
    service_item: Mapped[ServiceItem | None] = relationship("ServiceItem")
    service_addon: Mapped[ServiceAddon | None] = relationship("ServiceAddon")
```

---

## 5. Model Exports Blueprint: `backend/app/models/__init__.py`

To ensure `Base.metadata` automatically discovers and registers the new models (used by Alembic and `reset_database` in pytest), append the following to `backend/app/models/__init__.py`:

```python
from app.models.pricing import (
    ComponentType,
    PriceBook,
    PriceBookScope,
    PriceBookStatus,
    PriceRule,
    PriceRuleType,
)

__all__.extend([
    'PriceBook',
    'PriceRule',
    'PriceBookScope',
    'PriceBookStatus',
    'PriceRuleType',
    'ComponentType',
])
```

---

## 6. Alembic Migration Blueprint: `backend/migrations/versions/<rev>_phase5_pricing_engine.py`

### 6.1 Metadata Specifications
- **File Name**: `c8b91e56d204_phase5_pricing_engine.py` (or any unique 12-char hex string)
- **Revision**: `'c8b91e56d204'`
- **Revises (`down_revision`)**: `'ddf173e6fc96'` (Verified current Alembic head)
- **Branch Labels**: `None`
- **Depends On**: `None`

### 6.2 Complete Migration Script Code

```python
"""phase5_pricing_engine

Revision ID: c8b91e56d204
Revises: ddf173e6fc96
Create Date: 2026-09-19 05:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8b91e56d204'
down_revision: Union[str, None] = 'ddf173e6fc96'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create price_books table
    op.create_table(
        'price_books',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column('scope', sa.String(length=50), server_default='SELLER', nullable=False),
        sa.Column('status', sa.String(length=50), server_default='ACTIVE', nullable=False),
        sa.Column('seller_id', sa.Uuid(), nullable=True),
        sa.Column('branch_id', sa.Uuid(), nullable=True),
        sa.Column('currency', sa.String(length=3), server_default='USD', nullable=False),
        sa.Column('priority', sa.Integer(), server_default='0', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['branch_id'], ['seller_branches.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['seller_id'], ['sellers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_price_books_tenant_id'), 'price_books', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_price_books_seller_id'), 'price_books', ['seller_id'], unique=False)
    op.create_index(op.f('ix_price_books_branch_id'), 'price_books', ['branch_id'], unique=False)
    op.create_index('idx_price_books_tenant_scope', 'price_books', ['tenant_id', 'scope'], unique=False)
    op.create_index('idx_price_books_tenant_seller', 'price_books', ['tenant_id', 'seller_id'], unique=False)
    op.create_index('idx_price_books_tenant_branch', 'price_books', ['tenant_id', 'branch_id'], unique=False)
    op.create_index('idx_price_books_tenant_status', 'price_books', ['tenant_id', 'status'], unique=False)

    # 2. Create price_rules table
    op.create_table(
        'price_rules',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=True),
        sa.Column('price_book_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column('service_id', sa.Uuid(), nullable=True),
        sa.Column('service_item_id', sa.Uuid(), nullable=True),
        sa.Column('service_addon_id', sa.Uuid(), nullable=True),
        sa.Column('rule_type', sa.String(length=50), nullable=False),
        sa.Column('component_type', sa.String(length=50), server_default='BASE_PRICE', nullable=False),
        sa.Column('rate', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('priority', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['price_book_id'], ['price_books.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['service_addon_id'], ['service_addons.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['service_id'], ['services.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['service_item_id'], ['service_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_price_rules_tenant_id'), 'price_rules', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_price_rules_price_book_id'), 'price_rules', ['price_book_id'], unique=False)
    op.create_index(op.f('ix_price_rules_service_id'), 'price_rules', ['service_id'], unique=False)
    op.create_index(op.f('ix_price_rules_service_item_id'), 'price_rules', ['service_item_id'], unique=False)
    op.create_index(op.f('ix_price_rules_service_addon_id'), 'price_rules', ['service_addon_id'], unique=False)
    op.create_index('idx_price_rules_book_service', 'price_rules', ['price_book_id', 'service_id'], unique=False)
    op.create_index('idx_price_rules_book_item', 'price_rules', ['price_book_id', 'service_item_id'], unique=False)
    op.create_index('idx_price_rules_book_addon', 'price_rules', ['price_book_id', 'service_addon_id'], unique=False)
    op.create_index('idx_price_rules_book_active', 'price_rules', ['price_book_id', 'is_active'], unique=False)
    op.create_index('idx_price_rules_tenant_id', 'price_rules', ['tenant_id'], unique=False)


def downgrade() -> None:
    # Drop child table first (price_rules)
    op.drop_index('idx_price_rules_tenant_id', table_name='price_rules')
    op.drop_index('idx_price_rules_book_active', table_name='price_rules')
    op.drop_index('idx_price_rules_book_addon', table_name='price_rules')
    op.drop_index('idx_price_rules_book_item', table_name='price_rules')
    op.drop_index('idx_price_rules_book_service', table_name='price_rules')
    op.drop_index(op.f('ix_price_rules_service_addon_id'), table_name='price_rules')
    op.drop_index(op.f('ix_price_rules_service_item_id'), table_name='price_rules')
    op.drop_index(op.f('ix_price_rules_service_id'), table_name='price_rules')
    op.drop_index(op.f('ix_price_rules_price_book_id'), table_name='price_rules')
    op.drop_index(op.f('ix_price_rules_tenant_id'), table_name='price_rules')
    op.drop_table('price_rules')

    # Drop parent table second (price_books)
    op.drop_index('idx_price_books_tenant_status', table_name='price_books')
    op.drop_index('idx_price_books_tenant_branch', table_name='price_books')
    op.drop_index('idx_price_books_tenant_seller', table_name='price_books')
    op.drop_index('idx_price_books_tenant_scope', table_name='price_books')
    op.drop_index(op.f('ix_price_books_branch_id'), table_name='price_books')
    op.drop_index(op.f('ix_price_books_seller_id'), table_name='price_books')
    op.drop_index(op.f('ix_price_books_tenant_id'), table_name='price_books')
    op.drop_table('price_books')
```

---

## 7. Operational & Environmental Caveats for Implementer

1. **Test Fixture Dependency (`tests/conftest.py`)**:
   - As identified during our investigation, `backend/tests/conftest.py` does not currently import `app.models`. When `Base.metadata.create_all()` is invoked during `reset_database`, it only creates tables for models imported in `conftest.py`.
   - Milestone 1 Feature 1 must ensure `import app.models` is added to `backend/tests/conftest.py`.
2. **Current Database Alembic Stamp**:
   - The current development PostgreSQL database has `alembic_version` set to `'275f700c133f'` while the catalog tables already exist.
   - Before executing `alembic upgrade head` in local development, developers should either:
     - Run `alembic stamp ddf173e6fc96` to align the version tracker with existing Phase 4 tables, or
     - Drop and recreate the local development database cleanly.
3. **Foreign Key Integrity**:
   - All foreign keys (`tenants.id`, `sellers.id`, `seller_branches.id`, `services.id`, `service_items.id`, `service_addons.id`) are configured with `ondelete='CASCADE'`. When a catalog item or seller is deleted, associated price rules and books cascade delete automatically.
