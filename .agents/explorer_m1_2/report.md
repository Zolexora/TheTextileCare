# Strategy Report: Phase 7 SQLAlchemy 2.0 Domain Models & Pydantic v2 Schemas

**Author:** `explorer_m1_2`  
**Milestone:** Milestone 1 — Database Migration, Domain Models & RBAC Foundation  
**Date:** 2026-09-19  
**Domains Covered:** Commercial, Pickup, Payment, Billing, Settlement  
**Target Codebase:** `/workspaces/TheTextileCare/backend`  

---

## 1. Executive Summary & Architecture Overview

Phase 7 of TheTextileCare (TTC) establishes the commercial billing, post-pickup payment timing, settlement payout, and seller overdue restriction foundation. 

This report provides the authoritative architectural and code design for:
1. **SQLAlchemy 2.0 Domain Models**:
   - New `OrderPickup` model and `PickupStatus` enum in `backend/app/models/pickup.py`.
   - Refined `SellerCommercialConfiguration` and commercial enums in `backend/app/models/commercial.py` (adding missing `tenant_id`, penalty rates, and threshold configurations).
   - Refined `Payment` and `Refund` models and enums in `backend/app/models/payment.py` (adding missing `seller_id`, `settled`, `settlement_id`, `paid_at`, `due_date`, and `commission_deduction`).
   - Refined `SellerBillingInvoice` and `SellerSettlement` models and enums in `backend/app/models/billing.py` (fixing `SettlementStatus.SCHEDULED`, adding `UniqueConstraint(seller_id, invoice_month)`).
   - Confirmation and relationship mapping for `Order.reselected_from_order_id` in `backend/app/models/order.py`.
   - Complete export registration in `backend/app/models/__init__.py`.
2. **Pydantic v2 Domain Schemas**:
   - `backend/app/schemas/commercial.py` (Commercial models, mutual exclusivity validators, overdue status DTOs).
   - `backend/app/schemas/pickup.py` (Pickup inspection details, submit, approve, reject, complete DTOs).
   - `backend/app/schemas/payment.py` (Payment initiation, payment execution, fee/tax breakdown, refund DTOs).
   - `backend/app/schemas/billing.py` (Monthly invoice generation, payment, list, late penalty calculation DTOs).
   - `backend/app/schemas/settlement.py` (Monday payout batch generation, processing, preview DTOs).
   - `backend/app/schemas/order.py` additions (`OrderReselectRequest` for marketplace seller re-selection).

---

## 2. Core Architectural Invariants

### 2.1 Separation of Operational vs Financial Concerns (R5)
- **`OrderStatus` (`orders`)** is strictly operational: `DRAFT`, `PENDING`, `CONFIRMED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`. It contains **zero** payment states.
- **`PickupStatus` (`order_pickups`)** tracks physical laundry collection and verification: `SCHEDULED`, `DETAILS_SUBMITTED`, `APPROVED`, `REJECTED`, `COMPLETED`.
- **`PaymentStatus` (`payments`)** tracks monetary transaction states: `PENDING`, `SUCCEEDED`, `FAILED`, `OUTSTANDING`, `REFUNDED`, `PARTIALLY_REFUNDED`.
- **`InvoiceStatus` (`seller_billing_invoices`)** tracks monthly platform bills: `PENDING`, `PAID`, `OVERDUE`, `CANCELLED`.
- **`SettlementStatus` (`seller_settlements`)** tracks weekly seller disbursements: `SCHEDULED`, `PROCESSING`, `SETTLED`, `FAILED`.

### 2.2 Payment Timing Invariant (R1)
- Order creation creates orders in `PENDING` without charging the customer or interacting with any payment gateway.
- Payment is requested **only after customer approval** of actual pickup inspection details (`PickupStatus.APPROVED`).

### 2.3 Financial Ledger Separation Invariant (R1, R5)
- Third-party gateway processor costs (`gateway_fee`, `gateway_tax`) are tracked in dedicated columns, isolated from TTC platform revenues (`ttc_commission`, `ttc_commission_tax`).
- Monetary calculations use Python `Decimal` and PostgreSQL `Numeric(12, 2)` (or `Numeric(6, 4)` for penalty rates) with `ROUND_HALF_UP`. Floating-point numbers are strictly forbidden.

### 2.4 Multi-Tenant Data Isolation (R5)
- Every domain model contains a mandatory, indexed foreign key `tenant_id` referencing `tenants.id` with `ondelete="CASCADE"` or `"RESTRICT"`.
- Every query, schema validation, and repository operation must be strictly scoped to `TenantContext.tenant_id`.

---

## 3. SQLAlchemy 2.0 Model Specifications

### 3.1 `backend/app/models/pickup.py` (NEW FILE)

```python
"""Phase 7 — Order Pickup Domain Model.

Tracks physical garment collection, driver inspection snapshots,
and customer verification before payment is requested.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.seller import Seller
    from app.models.tenant import Tenant


class PickupStatus(str, enum.Enum):
    """Lifecycle states of the physical garment pickup process."""

    SCHEDULED = "SCHEDULED"
    DETAILS_SUBMITTED = "DETAILS_SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"


class OrderPickup(Base):
    """Authoritative physical pickup and inspection record for an Order.
    
    Customer approval of submitted details triggers payment collection.
    """

    __tablename__ = "order_pickups"
    __table_args__ = (
        UniqueConstraint("order_id", name="uq_order_pickups_order_id"),
        Index("ix_order_pickups_order_id", "order_id"),
        Index("ix_order_pickups_tenant_id", "tenant_id"),
        Index("ix_order_pickups_seller_id_status", "seller_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False, index=True
    )

    status: Mapped[str] = mapped_column(
        String(50), default=PickupStatus.SCHEDULED.value, nullable=False, index=True
    )

    # Inspection details (actual item counts, verified weights, fabric conditions, extra charges)
    actual_details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    driver_notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    customer_notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Key operational timestamps
    actual_pickup_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    details_submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    order: Mapped[Order] = relationship("Order", back_populates="pickup")
    tenant: Mapped[Tenant] = relationship("Tenant")
    seller: Mapped[Seller] = relationship("Seller")
```

---

### 3.2 `backend/app/models/commercial.py` (REFINED)

**Enhancements Made:**
1. Added missing `tenant_id` foreign key for strict tenant isolation.
2. Added `payment_gateway_type` and retained explicit `marketplace_gateway` / `white_label_gateway` routing.
3. Added configurable overdue enforcement thresholds (`overdue_warning_days`, `overdue_restriction_days`, `overdue_suspension_days`, `overdue_grace_days`, `daily_penalty_rate`).
4. Added monthly billing parameters (`billing_cycle_day`, `invoice_due_days`).

```python
"""Phase 7 — Commercial Configuration and Seller Restriction Models."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.seller import Seller
    from app.models.tenant import Tenant


class PaymentGatewayType(str, enum.Enum):
    TTC_GATEWAY = "TTC_GATEWAY"
    SELLER_GATEWAY = "SELLER_GATEWAY"


class SellerCommercialModel(str, enum.Enum):
    COMMISSION = "COMMISSION"
    SUBSCRIPTION = "SUBSCRIPTION"


class SellerRestrictionLevel(str, enum.Enum):
    NONE = "NONE"
    WARNING = "WARNING"
    MARKETPLACE_RESTRICTED = "MARKETPLACE_RESTRICTED"
    WHITE_LABEL_RESTRICTED = "WHITE_LABEL_RESTRICTED"
    FULL_SUSPENSION = "FULL_SUSPENSION"


class SellerCommercialConfiguration(Base):
    """Authoritative commercial terms and operational restriction parameters for a seller."""

    __tablename__ = "seller_commercial_configs"
    __table_args__ = (
        Index("ix_seller_commercial_configs_tenant_id", "tenant_id"),
        Index("ix_seller_commercial_configs_seller_id", "seller_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sellers.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )

    # Gateway routing
    payment_gateway_type: Mapped[str] = mapped_column(
        String(50), default=PaymentGatewayType.TTC_GATEWAY.value, nullable=False
    )
    marketplace_gateway: Mapped[str] = mapped_column(
        String(50), default=PaymentGatewayType.TTC_GATEWAY.value, nullable=False
    )
    white_label_gateway: Mapped[str] = mapped_column(
        String(50), default=PaymentGatewayType.SELLER_GATEWAY.value, nullable=False
    )

    # Mutually exclusive commercial models (R2)
    commercial_model: Mapped[str] = mapped_column(
        String(50), default=SellerCommercialModel.COMMISSION.value, nullable=False
    )
    commission_rate_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("10.00"), nullable=False
    )
    subscription_fee: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), nullable=False
    )

    # Payment timing & failure modes (R1)
    payment_required_before_pickup: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    outstanding_receivable_allowed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    payment_deadline_days: Mapped[int] = mapped_column(default=1, nullable=False)

    # Monthly billing cycle configuration (R2)
    billing_cycle_day: Mapped[int] = mapped_column(default=1, nullable=False)
    invoice_due_days: Mapped[int] = mapped_column(default=15, nullable=False)
    overdue_grace_days: Mapped[int] = mapped_column(default=0, nullable=False)
    daily_penalty_rate: Mapped[Decimal] = mapped_column(
        Numeric(6, 4), default=Decimal("0.0010"), nullable=False
    )

    # Overdue enforcement thresholds & active restriction level (R4)
    overdue_warning_days: Mapped[int] = mapped_column(default=1, nullable=False)
    overdue_restriction_days: Mapped[int] = mapped_column(default=7, nullable=False)
    overdue_suspension_days: Mapped[int] = mapped_column(default=30, nullable=False)
    restriction_level: Mapped[str] = mapped_column(
        String(50), default=SellerRestrictionLevel.NONE.value, nullable=False, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    seller: Mapped[Seller] = relationship("Seller")
    tenant: Mapped[Tenant] = relationship("Tenant")
```

---

### 3.3 `backend/app/models/payment.py` (REFINED)

**Enhancements Made:**
1. Added missing `seller_id` foreign key for direct seller isolation and queries.
2. Added `settled: bool` and `settlement_id: UUID | None` (referencing `seller_settlements.id`).
3. Added `paid_at: datetime | None` (essential for the 15-day settlement cooling hold calculation).
4. Added `due_date: datetime | None` (essential for outstanding receivables deadline tracking).
5. Added `tenant_id` and `commission_deduction` to `Refund` model.

```python
"""Phase 7 — Payment and Refund Models.

Enforces financial ledger fee/tax separation and tracks settlement status.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.billing import SellerSettlement
    from app.models.customer import Customer
    from app.models.order import Order
    from app.models.seller import Seller
    from app.models.tenant import Tenant


class PaymentStatus(str, enum.Enum):
    """Authoritative lifecycle states of a customer order payment."""

    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    OUTSTANDING = "OUTSTANDING"
    REFUNDED = "REFUNDED"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"


class Payment(Base):
    """Authoritative financial record of a customer payment for an order."""

    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payments_order_id", "order_id"),
        Index("ix_payments_tenant_id", "tenant_id"),
        Index("ix_payments_seller_id_created_at", "seller_id", "created_at"),
        Index("ix_payments_customer_id", "customer_id"),
        Index(
            "ix_payments_settlement_cooling",
            "gateway_type",
            "status",
            "settled",
            "paid_at",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )

    gateway_type: Mapped[str] = mapped_column(String(50), nullable=False)  # TTC_GATEWAY, SELLER_GATEWAY
    status: Mapped[str] = mapped_column(
        String(50), default=PaymentStatus.PENDING.value, nullable=False, index=True
    )

    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Gateway costs (belong to 3rd-party payment gateway, recorded separately)
    gateway_fee: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    gateway_tax: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )

    # TTC platform revenue (belong to TTC, recorded separately)
    ttc_commission: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    ttc_commission_tax: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )

    # Retained balance & refunds
    refunded_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    retained_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Settlement tracking (R3)
    settled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    settlement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("seller_settlements.id", ondelete="SET NULL"), nullable=True, index=True
    )

    gateway_transaction_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    order: Mapped[Order] = relationship("Order", back_populates="payment")
    refunds: Mapped[list[Refund]] = relationship(
        "Refund", back_populates="payment", cascade="all, delete-orphan"
    )
    settlement: Mapped[SellerSettlement | None] = relationship(
        "SellerSettlement", back_populates="payments"
    )
    seller: Mapped[Seller] = relationship("Seller")
    customer: Mapped[Customer] = relationship("Customer")
    tenant: Mapped[Tenant] = relationship("Tenant")


class Refund(Base):
    """Record of a customer refund against an existing payment."""

    __tablename__ = "refunds"
    __table_args__ = (
        Index("ix_refunds_payment_id", "payment_id"),
        Index("ix_refunds_tenant_id", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    payment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("payments.id", ondelete="CASCADE"), nullable=False, index=True
    )

    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)

    # Commission adjustment
    commission_deduction: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    gateway_fee_reversed: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    gateway_tax_reversed: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )

    gateway_refund_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    payment: Mapped[Payment] = relationship("Payment", back_populates="refunds")
    tenant: Mapped[Tenant] = relationship("Tenant")
```

---

### 3.4 `backend/app/models/billing.py` (REFINED)

**Enhancements Made:**
1. Changed `SettlementStatus.PENDING` to `SettlementStatus.SCHEDULED` to strictly align with `PROJECT.md` contract.
2. Added `UniqueConstraint("seller_id", "invoice_month", name="uq_seller_billing_invoices_seller_month")`.
3. Standardized `invoice_month` as `String(7)` ("YYYY-MM") per `PROJECT.md` line 99.
4. Added `payments` relationship on `SellerSettlement` back-populating `Payment.settlement`.

```python
"""Phase 7 — Billing Invoices and Settlement Models."""
from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.payment import Payment
    from app.models.seller import Seller
    from app.models.tenant import Tenant


class InvoiceStatus(str, enum.Enum):
    """Lifecycle states of a monthly seller billing invoice."""

    PENDING = "PENDING"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


class SellerBillingInvoice(Base):
    """Monthly TTC billing invoice for a seller (commission + subscription + late penalties)."""

    __tablename__ = "seller_billing_invoices"
    __table_args__ = (
        UniqueConstraint("seller_id", "invoice_month", name="uq_seller_billing_invoices_seller_month"),
        Index("ix_seller_billing_invoices_tenant_id", "tenant_id"),
        Index("ix_seller_billing_invoices_seller_id", "seller_id"),
        Index("ix_seller_billing_invoices_status_due_date", "status", "due_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False, index=True
    )

    invoice_month: Mapped[str] = mapped_column(String(7), nullable=False)  # e.g. "2026-09"
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default=InvoiceStatus.PENDING.value, nullable=False, index=True
    )

    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    tax_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    penalty_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )

    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    seller: Mapped[Seller] = relationship("Seller")
    tenant: Mapped[Tenant] = relationship("Tenant")


class SettlementStatus(str, enum.Enum):
    """Lifecycle states of a Monday seller settlement payout."""

    SCHEDULED = "SCHEDULED"
    PROCESSING = "PROCESSING"
    SETTLED = "SETTLED"
    FAILED = "FAILED"


class SellerSettlement(Base):
    """Weekly Monday payout disbursement to seller for TTC_GATEWAY funds after 15-day cooling hold."""

    __tablename__ = "seller_settlements"
    __table_args__ = (
        Index("ix_seller_settlements_seller_id_scheduled", "seller_id", "scheduled_for"),
        Index("ix_seller_settlements_tenant_id", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False, index=True
    )

    gateway_type: Mapped[str] = mapped_column(
        String(50), default="TTC_GATEWAY", nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(50), default=SettlementStatus.SCHEDULED.value, nullable=False, index=True
    )

    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    scheduled_for: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reference_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    payments: Mapped[list[Payment]] = relationship(
        "Payment", back_populates="settlement"
    )
    seller: Mapped[Seller] = relationship("Seller")
    tenant: Mapped[Tenant] = relationship("Tenant")
```

---

### 3.5 `backend/app/models/order.py` (INTEGRATION REFINEMENT)

In `backend/app/models/order.py`:
1. `reselected_from_order_id` is already present:
   ```python
   reselected_from_order_id: Mapped[uuid.UUID | None] = mapped_column(
       ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True
   )
   ```
2. Add relationships to `Order`:
   ```python
   # Reselection self-referential relationship
   reselected_from_order: Mapped[Order | None] = relationship(
       "Order", remote_side="Order.id", foreign_keys=[reselected_from_order_id]
   )

   # One-to-one relationship to OrderPickup
   pickup: Mapped[OrderPickup | None] = relationship(
       "OrderPickup", back_populates="order", uselist=False, cascade="all, delete-orphan"
   )

   # One-to-one relationship to Payment
   payment: Mapped[Payment | None] = relationship(
       "Payment", back_populates="order", uselist=False, cascade="all, delete-orphan"
   )
   ```

---

### 3.6 `backend/app/models/__init__.py` (EXPORT REGISTRATION)

To guarantee that `Base.metadata.create_all()` in test fixtures creates all Phase 7 tables, export all models and enums in `backend/app/models/__init__.py`:

```python
from app.models.pickup import OrderPickup, PickupStatus
from app.models.commercial import (
    PaymentGatewayType,
    SellerCommercialModel,
    SellerRestrictionLevel,
    SellerCommercialConfiguration,
)
from app.models.payment import PaymentStatus, Payment, Refund
from app.models.billing import (
    InvoiceStatus,
    SellerBillingInvoice,
    SettlementStatus,
    SellerSettlement,
)

__all__.extend([
    "OrderPickup",
    "PickupStatus",
    "PaymentGatewayType",
    "SellerCommercialModel",
    "SellerRestrictionLevel",
    "SellerCommercialConfiguration",
    "PaymentStatus",
    "Payment",
    "Refund",
    "InvoiceStatus",
    "SellerBillingInvoice",
    "SettlementStatus",
    "SellerSettlement",
])
```

---

## 4. Pydantic v2 Schema Specifications

### 4.1 `backend/app/schemas/commercial.py`

```python
"""Phase 7 — Commercial Configuration Pydantic v2 Schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.commercial import (
    PaymentGatewayType,
    SellerCommercialModel,
    SellerRestrictionLevel,
)

__all__ = [
    "PaymentGatewayType",
    "SellerCommercialModel",
    "SellerRestrictionLevel",
    "CommercialConfigBase",
    "CommercialConfigCreate",
    "CommercialConfigUpdate",
    "CommercialConfigResponse",
    "SellerRestrictionEvaluationResponse",
]


class CommercialConfigBase(BaseModel):
    commercial_model: SellerCommercialModel = SellerCommercialModel.COMMISSION
    commission_rate_percent: Decimal = Field(
        default=Decimal("10.00"), ge=Decimal("0.00"), le=Decimal("100.00")
    )
    subscription_fee: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))

    payment_gateway_type: PaymentGatewayType = PaymentGatewayType.TTC_GATEWAY
    marketplace_gateway: PaymentGatewayType = PaymentGatewayType.TTC_GATEWAY
    white_label_gateway: PaymentGatewayType = PaymentGatewayType.SELLER_GATEWAY

    payment_required_before_pickup: bool = True
    outstanding_receivable_allowed: bool = False
    payment_deadline_days: int = Field(default=1, ge=0)

    billing_cycle_day: int = Field(default=1, ge=1, le=28)
    invoice_due_days: int = Field(default=15, ge=1)
    overdue_grace_days: int = Field(default=0, ge=0)
    daily_penalty_rate: Decimal = Field(
        default=Decimal("0.0010"), ge=Decimal("0.0000"), le=Decimal("1.0000")
    )

    overdue_warning_days: int = Field(default=1, ge=0)
    overdue_restriction_days: int = Field(default=7, ge=0)
    overdue_suspension_days: int = Field(default=30, ge=0)

    @model_validator(mode="after")
    def validate_mutual_exclusivity(self) -> CommercialConfigBase:
        """Enforces mutual exclusivity between Commission and Subscription models (R2)."""
        if self.commercial_model == SellerCommercialModel.COMMISSION:
            if self.commission_rate_percent <= Decimal("0.00"):
                raise ValueError("Commission model requires commission_rate_percent > 0.00.")
            if self.subscription_fee != Decimal("0.00"):
                raise ValueError("Commission model requires subscription_fee to be exactly 0.00.")
        elif self.commercial_model == SellerCommercialModel.SUBSCRIPTION:
            if self.subscription_fee <= Decimal("0.00"):
                raise ValueError("Subscription model requires subscription_fee > 0.00.")
            if self.commission_rate_percent != Decimal("0.00"):
                raise ValueError("Subscription model requires commission_rate_percent to be exactly 0.00.")
        return self


class CommercialConfigCreate(CommercialConfigBase):
    seller_id: uuid.UUID


class CommercialConfigUpdate(BaseModel):
    commercial_model: SellerCommercialModel | None = None
    commission_rate_percent: Decimal | None = Field(default=None, ge=Decimal("0.00"), le=Decimal("100.00"))
    subscription_fee: Decimal | None = Field(default=None, ge=Decimal("0.00"))

    payment_gateway_type: PaymentGatewayType | None = None
    marketplace_gateway: PaymentGatewayType | None = None
    white_label_gateway: PaymentGatewayType | None = None

    payment_required_before_pickup: bool | None = None
    outstanding_receivable_allowed: bool | None = None
    payment_deadline_days: int | None = Field(default=None, ge=0)

    billing_cycle_day: int | None = Field(default=None, ge=1, le=28)
    invoice_due_days: int | None = Field(default=None, ge=1)
    overdue_grace_days: int | None = Field(default=None, ge=0)
    daily_penalty_rate: Decimal | None = Field(default=None, ge=Decimal("0.0000"), le=Decimal("1.0000"))

    overdue_warning_days: int | None = Field(default=None, ge=0)
    overdue_restriction_days: int | None = Field(default=None, ge=0)
    overdue_suspension_days: int | None = Field(default=None, ge=0)
    restriction_level: SellerRestrictionLevel | None = None

    @model_validator(mode="after")
    def validate_partial_mutual_exclusivity(self) -> CommercialConfigUpdate:
        if self.commercial_model is not None:
            if self.commercial_model == SellerCommercialModel.COMMISSION:
                if self.subscription_fee is not None and self.subscription_fee > Decimal("0.00"):
                    raise ValueError("Cannot set non-zero subscription_fee with COMMISSION model.")
            elif self.commercial_model == SellerCommercialModel.SUBSCRIPTION:
                if self.commission_rate_percent is not None and self.commission_rate_percent > Decimal("0.00"):
                    raise ValueError("Cannot set non-zero commission_rate_percent with SUBSCRIPTION model.")
        return self


class CommercialConfigResponse(CommercialConfigBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    seller_id: uuid.UUID
    restriction_level: SellerRestrictionLevel
    created_at: datetime
    updated_at: datetime


class SellerRestrictionEvaluationResponse(BaseModel):
    seller_id: uuid.UUID
    previous_restriction_level: SellerRestrictionLevel
    new_restriction_level: SellerRestrictionLevel
    max_days_overdue: int
    overdue_invoices_count: int
    pending_orders_cancelled_count: int
    evaluated_at: datetime
```

---

### 4.2 `backend/app/schemas/pickup.py`

```python
"""Phase 7 — Order Pickup Pydantic v2 Schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.pickup import PickupStatus

__all__ = [
    "PickupStatus",
    "PickupActualItemDetail",
    "PickupDetailsSubmitRequest",
    "PickupDetailsApproveRequest",
    "PickupDetailsRejectRequest",
    "PickupResponse",
    "PickupListResponse",
]


class PickupActualItemDetail(BaseModel):
    service_id: uuid.UUID
    service_item_id: uuid.UUID | None = None
    item_name: str
    verified_quantity: Decimal = Field(..., gt=Decimal("0"))
    measured_weight_kg: Decimal | None = Field(default=None, ge=Decimal("0"))
    fabric_notes: str | None = None
    detected_stains_or_damages: list[str] = Field(default_factory=list)


class PickupDetailsSubmitRequest(BaseModel):
    actual_details: dict[str, Any] = Field(
        ...,
        description="Authoritative inspection details including verified items, counts, and weights."
    )
    driver_notes: str | None = Field(default=None, max_length=1000)


class PickupDetailsApproveRequest(BaseModel):
    customer_notes: str | None = Field(default=None, max_length=1000)


class PickupDetailsRejectRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=1000)


class PickupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    order_id: uuid.UUID
    seller_id: uuid.UUID
    status: PickupStatus

    actual_details: dict[str, Any] | None
    driver_notes: str | None
    customer_notes: str | None
    rejection_reason: str | None

    actual_pickup_at: datetime | None
    details_submitted_at: datetime | None
    approved_at: datetime | None
    completed_at: datetime | None

    created_at: datetime
    updated_at: datetime


class PickupListResponse(BaseModel):
    items: list[PickupResponse]
    total: int
    limit: int
    offset: int
```

---

### 4.3 `backend/app/schemas/payment.py`

```python
"""Phase 7 — Payment & Refund Pydantic v2 Schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.commercial import PaymentGatewayType
from app.models.payment import PaymentStatus

__all__ = [
    "PaymentStatus",
    "PaymentGatewayType",
    "PaymentInitiateRequest",
    "PaymentProcessRequest",
    "PaymentResponse",
    "PaymentLedgerBreakdownResponse",
    "RefundCreateRequest",
    "RefundResponse",
    "PaymentListResponse",
]


class PaymentInitiateRequest(BaseModel):
    idempotency_key: str | None = Field(default=None, max_length=255)


class PaymentProcessRequest(BaseModel):
    payment_method: str = Field(default="CARD", max_length=50)
    payment_token: str | None = None
    idempotency_key: str | None = Field(default=None, max_length=255)
    simulate_failure: bool = False  # Supports testing dual failure modes


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    order_id: uuid.UUID
    seller_id: uuid.UUID
    customer_id: uuid.UUID

    gateway_type: PaymentGatewayType
    status: PaymentStatus
    currency: str
    amount: Decimal

    # Financial ledger fee/tax separation (R1, R5)
    gateway_fee: Decimal
    gateway_tax: Decimal
    ttc_commission: Decimal
    ttc_commission_tax: Decimal

    refunded_amount: Decimal
    retained_amount: Decimal

    settled: bool
    settlement_id: uuid.UUID | None
    gateway_transaction_id: str | None

    paid_at: datetime | None
    due_date: datetime | None
    created_at: datetime
    updated_at: datetime


class PaymentLedgerBreakdownResponse(BaseModel):
    payment_id: uuid.UUID
    order_id: uuid.UUID
    currency: str
    gross_customer_payment: Decimal
    gateway_fee: Decimal
    gateway_tax: Decimal
    ttc_commission: Decimal
    ttc_commission_tax: Decimal
    net_seller_share: Decimal
    refunded_amount: Decimal
    retained_amount: Decimal


class RefundCreateRequest(BaseModel):
    amount: Decimal = Field(..., gt=Decimal("0.00"))
    reason: str = Field(..., min_length=1, max_length=1000)
    idempotency_key: str | None = Field(default=None, max_length=255)


class RefundResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    payment_id: uuid.UUID
    amount: Decimal
    reason: str
    commission_deduction: Decimal
    gateway_fee_reversed: Decimal
    gateway_tax_reversed: Decimal
    gateway_refund_id: str | None
    created_at: datetime


class PaymentListResponse(BaseModel):
    items: list[PaymentResponse]
    total: int
    limit: int
    offset: int
```

---

### 4.4 `backend/app/schemas/billing.py`

```python
"""Phase 7 — Billing Invoices Pydantic v2 Schemas."""
from __future__ import annotations

import re
import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.billing import InvoiceStatus

__all__ = [
    "InvoiceStatus",
    "BillingInvoiceGenerateRequest",
    "BillingInvoicePayRequest",
    "BillingInvoiceResponse",
    "BillingInvoiceListResponse",
    "LatePenaltyCalculationResponse",
]

INVOICE_MONTH_REGEX = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class BillingInvoiceGenerateRequest(BaseModel):
    year: int = Field(..., ge=2020, le=2050)
    month: int = Field(..., ge=1, le=12)


class BillingInvoicePayRequest(BaseModel):
    payment_reference: str | None = Field(default=None, max_length=255)


class BillingInvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    seller_id: uuid.UUID
    invoice_month: str
    due_date: date
    status: InvoiceStatus
    currency: str

    subtotal: Decimal
    tax_total: Decimal
    penalty_total: Decimal
    total_amount: Decimal

    paid_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @field_validator("invoice_month")
    @classmethod
    def validate_month_format(cls, v: str) -> str:
        if not INVOICE_MONTH_REGEX.match(v):
            raise ValueError(f"Invalid invoice_month: '{v}'. Must be 'YYYY-MM' format.")
        return v


class BillingInvoiceListResponse(BaseModel):
    items: list[BillingInvoiceResponse]
    total: int
    limit: int
    offset: int


class LatePenaltyCalculationResponse(BaseModel):
    invoice_id: uuid.UUID
    seller_id: uuid.UUID
    invoice_month: str
    due_date: date
    as_of_date: date
    days_overdue: int
    daily_penalty_rate: Decimal
    base_overdue_amount: Decimal
    calculated_penalty: Decimal
    total_amount: Decimal
    status: InvoiceStatus
```

---

### 4.5 `backend/app/schemas/settlement.py`

```python
"""Phase 7 — Settlement Payout Pydantic v2 Schemas."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.billing import SettlementStatus
from app.models.commercial import PaymentGatewayType

__all__ = [
    "SettlementStatus",
    "SettlementGenerateRequest",
    "SettlementProcessRequest",
    "SettlementResponse",
    "SettlementListResponse",
    "SettlementEligibleBatchPreviewResponse",
]


class SettlementGenerateRequest(BaseModel):
    target_date: date | None = Field(
        default=None,
        description="Target Monday date for batch settlement generation. Defaults to current date/next Monday."
    )


class SettlementProcessRequest(BaseModel):
    settlement_ids: list[uuid.UUID] = Field(..., min_length=1)


class SettlementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    seller_id: uuid.UUID
    gateway_type: PaymentGatewayType
    status: SettlementStatus
    currency: str
    amount: Decimal

    scheduled_for: date
    processed_at: datetime | None
    reference_id: str | None

    created_at: datetime
    updated_at: datetime


class SettlementListResponse(BaseModel):
    items: list[SettlementResponse]
    total: int
    limit: int
    offset: int


class SettlementEligibleBatchPreviewResponse(BaseModel):
    target_date: date
    cooling_cutoff_timestamp: datetime
    seller_id: uuid.UUID
    eligible_transactions_count: int
    total_net_settlement_amount: Decimal
```

---

### 4.6 `backend/app/schemas/order.py` (Reselection Extension)

Add `OrderReselectRequest` to `backend/app/schemas/order.py`:

```python
class OrderReselectRequest(BaseModel):
    """Customer request to re-select an alternative seller after restriction cancellation (R4)."""
    new_seller_id: uuid.UUID
    new_branch_id: uuid.UUID
```

---

## 5. Mathematical Ledger and Transition Rules

### 5.1 Payment Ledger Formula (R1)
For customer payment $P$:
$$\text{Gateway Fee } GF = \text{compute\_fee}(P)$$
$$\text{Gateway Tax } GT = GF \times \text{tax\_rate}$$
$$\text{TTC Commission } TC = \text{Retained Amount} \times \text{Commission Rate}$$
$$\text{TTC Commission Tax } TT = TC \times \text{tax\_rate}$$
$$\text{Net Seller Payable } NS = P - (GF + GT) - (TC + TT)$$

### 5.2 15-Day Cooling Hold Formula (R3)
A transaction is eligible for batch settlement payout on `target_date` if:
1. `payment.gateway_type == "TTC_GATEWAY"`
2. `payment.status == "SUCCEEDED"`
3. `payment.settled is False`
4. `payment.paid_at <= target_date - 15 days`
5. `target_date.weekday() == 0` (Monday)

Transactions with `gateway_type == "SELLER_GATEWAY"` bypass this entirely: TTC generates zero holds and zero settlements.

### 5.3 Daily Late Penalty Formula (R2)
For an overdue invoice as of `as_of_date`:
$$\text{Days Overdue } D = \max(0, (\text{as\_of\_date} - \text{due\_date}).\text{days} - \text{overdue\_grace\_days})$$
$$\text{Base Amount } B = \text{subtotal} + \text{tax\_total}$$
$$\text{Penalty Total } PT = B \times \text{daily\_penalty\_rate} \times D$$
$$\text{Total Amount } TA = B + PT$$
Computation is idempotent: re-evaluating on the same day yields identical results without compounding.

### 5.4 Overdue Seller Restrictions & Auto-Cancellation (R4)
When evaluating a seller's restriction status:
1. If $D \ge \text{overdue\_suspension\_days}$: status = `FULL_SUSPENSION`.
2. Else if $D \ge \text{overdue\_restriction\_days}$: status = `MARKETPLACE_RESTRICTED`.
3. Else if $D \ge \text{overdue\_warning\_days}$: status = `WARNING`.
4. Else: status = `NONE`.

When moving to `MARKETPLACE_RESTRICTED` or `FULL_SUSPENSION`:
- Query all orders where `seller_id == seller.id` and `status == OrderStatus.PENDING`.
- Transition each to `OrderStatus.CANCELLED` with `cancellation_reason = "SELLER_RESTRICTED"`.
- Operational orders in `CONFIRMED` and `IN_PROGRESS` remain strictly untouched.
- Since `PENDING` orders were never charged, zero refunds are required.

---

## 6. Implementation Verification Checklist for Milestone 1 Worker

1. [ ] **Create `backend/app/models/pickup.py`** with `OrderPickup` and `PickupStatus`.
2. [ ] **Update `backend/app/models/commercial.py`** to include `tenant_id`, overdue thresholds, and penalty rates.
3. [ ] **Update `backend/app/models/payment.py`** to include `seller_id`, `settled`, `settlement_id`, `paid_at`, `due_date`, and `commission_deduction`.
4. [ ] **Update `backend/app/models/billing.py`** to use `SettlementStatus.SCHEDULED` and add `uq_seller_billing_invoices_seller_month`.
5. [ ] **Update `backend/app/models/order.py`** to map relationships `pickup`, `payment`, and `reselected_from_order`.
6. [ ] **Export all models and enums** in `backend/app/models/__init__.py`.
7. [ ] **Create Pydantic v2 schemas** in:
   - `backend/app/schemas/commercial.py`
   - `backend/app/schemas/pickup.py`
   - `backend/app/schemas/payment.py`
   - `backend/app/schemas/billing.py`
   - `backend/app/schemas/settlement.py`
   - Add `OrderReselectRequest` to `backend/app/schemas/order.py`.
8. [ ] **Run test suite / `Base.metadata.create_all()`** to verify zero syntax errors and clean table creations.
