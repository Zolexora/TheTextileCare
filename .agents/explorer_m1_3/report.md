# Phase 7 Strategy Report: RBAC Permissions, Test Fixtures & Multi-Tenant Repositories

**Agent**: `explorer_m1_3`  
**Milestone**: Phase 7 Milestone 1 — Database Migration, Domain Models & RBAC Foundation  
**Target Working Directory**: `/workspaces/TheTextileCare/.agents/explorer_m1_3`  
**Date**: 2026-09-19  

---

## 1. Executive Summary

This strategy report provides the complete architectural blueprint and drop-in code designs for:
1. **Fine-Grained RBAC Permissions & Role Descriptions**:
   - 8 new Phase 7 permissions covering Commercial Configuration, Payments, Billing, and Settlement.
   - Extension of `RoleName` with `CUSTOMER`.
   - Comprehensive `DEFAULT_ROLE_PERMISSIONS` matrix across all 11 platform, tenant, seller, and customer roles adhering strictly to the principle of least privilege.
   - Comprehensive descriptions in `ROLE_DESCRIPTIONS` and `PERMISSION_DESCRIPTIONS` for automated seeding via `RoleService.seed_defaults()`.
2. **Test Fixtures & Database Reset Architecture (`conftest.py`)**:
   - Verification of `import app.models` in `backend/tests/conftest.py` ensuring all Phase 7 models (`OrderPickup`, `SellerCommercialConfiguration`, `Payment`, `Refund`, `SellerBillingInvoice`, `SellerSettlement`) are registered with `Base.metadata`.
   - Reusable test fixtures and world builders for Phase 7 domain entities to streamline unit, API, and E2E testing.
3. **Five Multi-Tenant Domain Repositories**:
   - `CommercialRepository` (`backend/app/repositories/commercial.py`)
   - `PickupRepository` (`backend/app/repositories/pickup.py`)
   - `PaymentRepository` (`backend/app/repositories/payment.py`)
   - `BillingRepository` (`backend/app/repositories/billing.py`)
   - `SettlementRepository` (`backend/app/repositories/settlement.py`)
   - Built on SQLAlchemy 2.0 type-safe constructs (`select`, `options`, `scalars`, `selectinload`), extending `BaseRepository`, with strict `tenant_id` query scoping, pagination tuples `(items, total_count)`, and transaction isolation (`flush()` instead of direct `commit()`).

---

## 2. RBAC Permissions, Roles & Mappings

### 2.1 Permission Definitions (`backend/app/core/permissions/constants.py`)

Eight new permissions are defined in `PermissionName` to govern Phase 7 operational and financial lifecycle transitions:

```python
class PermissionName(str, Enum):
    # ... existing permissions (TENANT_*, MEMBERSHIP_*, ROLE_*, USER_*, AUDIT_*,
    #                           SELLER_*, CATALOG_*, CONFIGURATION_*, PRICING_*, ORDER_*) ...

    # Phase 7 Commercial, Billing, Payment & Settlement Permissions
    COMMERCIAL_READ = 'commercial.read'
    COMMERCIAL_MANAGE = 'commercial.manage'
    PAYMENT_READ = 'payment.read'
    PAYMENT_PROCESS = 'payment.process'
    BILLING_READ = 'billing.read'
    BILLING_MANAGE = 'billing.manage'
    SETTLEMENT_READ = 'settlement.read'
    SETTLEMENT_PROCESS = 'settlement.process'
```

### 2.2 Role Enumeration & Groupings

The platform accommodates marketplace retail customers alongside tenant and platform members. To support customer-scoped endpoints cleanly and enable role-permission checks:

```python
class RoleName(str, Enum):
    PLATFORM_ADMIN = 'PLATFORM_ADMIN'
    PLATFORM_SUPPORT = 'PLATFORM_SUPPORT'
    TENANT_OWNER = 'TENANT_OWNER'
    TENANT_ADMIN = 'TENANT_ADMIN'
    TENANT_MEMBER = 'TENANT_MEMBER'
    TENANT_VIEWER = 'TENANT_VIEWER'

    # Phase 2 Seller Roles
    SELLER_OWNER = 'SELLER_OWNER'
    SELLER_ADMIN = 'SELLER_ADMIN'
    STAFF = 'STAFF'
    VIEWER = 'VIEWER'

    # Phase 7 Customer Role
    CUSTOMER = 'CUSTOMER'
```

### 2.3 Role-to-Permissions Matrix (`DEFAULT_ROLE_PERMISSIONS`)

The matrix strictly enforces least privilege:
- **`PLATFORM_ADMIN`**: Unrestricted super-administrator across all platform commercial configs, payment processing, invoice generation, and Monday settlement execution.
- **`PLATFORM_SUPPORT`**: Read-only diagnostic visibility across commercial terms, payments, billing, and settlements. No financial mutations or payout triggers.
- **`TENANT_OWNER` & `TENANT_ADMIN`**: Full control over their seller organization's commercial settings, pickup workflows, payment receipts, and billing statements. **Cannot trigger settlement disbursements** (`SETTLEMENT_PROCESS` is restricted to platform operators).
- **`SELLER_OWNER` & `SELLER_ADMIN`**: Manage seller operational configs, view payments, inspect monthly billing invoices, view settlement disbursement schedules.
- **`STAFF`**: Operational handling only: can view commercial configuration and orders, submit pickup details, and view payment status.
- **`VIEWER` & `TENANT_VIEWER`**: Pure read-only access to commercial configuration, billing invoices, and payments.
- **`CUSTOMER`**: Can view their own orders and payments (`ORDER_READ`, `PAYMENT_READ`), cancel cancellable orders (`ORDER_CANCEL`), and execute payment upon pickup detail approval (`PAYMENT_PROCESS`). Absolutely **zero access** to seller commercial terms, billing invoices, or platform settlements.

#### Complete Mapping Specification:

| Role | Commercial Permissions | Payment Permissions | Billing Permissions | Settlement Permissions | Other Relevant |
|---|---|---|---|---|---|
| `PLATFORM_ADMIN` | `COMMERCIAL_READ`<br>`COMMERCIAL_MANAGE` | `PAYMENT_READ`<br>`PAYMENT_PROCESS` | `BILLING_READ`<br>`BILLING_MANAGE` | `SETTLEMENT_READ`<br>`SETTLEMENT_PROCESS` | All Phase 1–7 permissions |
| `PLATFORM_SUPPORT` | `COMMERCIAL_READ` | `PAYMENT_READ` | `BILLING_READ` | `SETTLEMENT_READ` | All Read permissions |
| `TENANT_OWNER` | `COMMERCIAL_READ`<br>`COMMERCIAL_MANAGE` | `PAYMENT_READ`<br>`PAYMENT_PROCESS` | `BILLING_READ` | `SETTLEMENT_READ` | Full Tenant Ops |
| `TENANT_ADMIN` | `COMMERCIAL_READ`<br>`COMMERCIAL_MANAGE` | `PAYMENT_READ`<br>`PAYMENT_PROCESS` | `BILLING_READ` | `SETTLEMENT_READ` | Full Tenant Ops |
| `TENANT_MEMBER` | None | None | None | None | Membership/User only |
| `TENANT_VIEWER` | `COMMERCIAL_READ` | `PAYMENT_READ` | `BILLING_READ` | None | Read-only |
| `SELLER_OWNER` | `COMMERCIAL_READ`<br>`COMMERCIAL_MANAGE` | `PAYMENT_READ`<br>`PAYMENT_PROCESS` | `BILLING_READ` | `SETTLEMENT_READ` | Full Seller Ops |
| `SELLER_ADMIN` | `COMMERCIAL_READ`<br>`COMMERCIAL_MANAGE` | `PAYMENT_READ`<br>`PAYMENT_PROCESS` | `BILLING_READ` | `SETTLEMENT_READ` | Seller Staff/Branch Ops |
| `STAFF` | `COMMERCIAL_READ` | `PAYMENT_READ` | None | None | Order Process Ops |
| `VIEWER` | `COMMERCIAL_READ` | `PAYMENT_READ` | `BILLING_READ` | None | Read-only |
| `CUSTOMER` | None | `PAYMENT_READ`<br>`PAYMENT_PROCESS` | None | None | `ORDER_READ`<br>`ORDER_CANCEL` |

### 2.4 Role & Permission Descriptions (`backend/app/services/roles.py`)

To ensure `RoleService(db).seed_defaults()` populates the database cleanly during testing and production initialization, the dictionaries in `backend/app/services/roles.py` must be updated:

```python
ROLE_DESCRIPTIONS: dict[str, str] = {
    RoleName.PLATFORM_ADMIN.value: 'Platform super administrator with unrestricted access',
    RoleName.PLATFORM_SUPPORT.value: 'Platform support personnel with operational visibility',
    RoleName.TENANT_OWNER.value: 'Tenant owner with complete organizational control',
    RoleName.TENANT_ADMIN.value: 'Tenant administrator managing members and settings',
    RoleName.TENANT_MEMBER.value: 'Standard tenant member with operational permissions',
    RoleName.TENANT_VIEWER.value: 'Read-only tenant viewer',
    RoleName.SELLER_OWNER.value: 'Seller owner with complete control',
    RoleName.SELLER_ADMIN.value: 'Seller administrator managing branches and staff',
    RoleName.STAFF.value: 'Seller staff with operational permissions',
    RoleName.VIEWER.value: 'Read-only seller viewer',
    RoleName.CUSTOMER.value: 'Marketplace retail customer with order and payment access',
}

PERMISSION_DESCRIPTIONS: dict[str, str] = {
    # Existing Phase 1-6 descriptions ...
    
    # Phase 7 Commercial, Billing, Payment & Settlement Descriptions
    PermissionName.COMMERCIAL_READ.value: 'View seller commercial configuration and restriction levels',
    PermissionName.COMMERCIAL_MANAGE.value: 'Configure seller commercial models, commission rates, and payment switches',
    PermissionName.PAYMENT_READ.value: 'View order payment records, fee breakdowns, and refund details',
    PermissionName.PAYMENT_PROCESS.value: 'Execute payments, process gateway callbacks, and issue refunds',
    PermissionName.BILLING_READ.value: 'View monthly seller billing invoices and overdue penalties',
    PermissionName.BILLING_MANAGE.value: 'Generate monthly invoices, calculate penalties, and manage invoice status',
    PermissionName.SETTLEMENT_READ.value: 'View cooling hold balances and weekly settlement disbursement status',
    PermissionName.SETTLEMENT_PROCESS.value: 'Trigger and execute weekly Monday settlement payouts',
}
```

---

## 3. Test Fixture Registration & Database Reset Architecture

### 3.1 Model Registration Verification in `conftest.py`

In `backend/tests/conftest.py`, the auto-use fixture is:
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

Because `conftest.py` starts with:
```python
import app.models  # noqa: F401
```
`Base.metadata.create_all(bind=engine)` collects all tables declared by subclasses of `Base` that have been imported by the Python process.

#### Verification Finding:
In `backend/app/models/__init__.py`:
- `OrderPickup` and `PickupStatus` (from `app.models.pickup`) are **not yet imported**!
- When `backend/app/models/pickup.py` is implemented by Implementer M1, it must be explicitly imported and exported in `backend/app/models/__init__.py`:
  ```python
  from app.models.pickup import OrderPickup, PickupStatus
  from app.models.commercial import (
      PaymentGatewayType,
      SellerCommercialModel,
      SellerRestrictionLevel,
      SellerCommercialConfiguration,
  )
  from app.models.payment import Payment, PaymentStatus, Refund
  from app.models.billing import (
      InvoiceStatus,
      SellerBillingInvoice,
      SettlementStatus,
      SellerSettlement,
  )
  ```
  Once `app/models/__init__.py` imports `pickup.py`, `commercial.py`, `payment.py`, and `billing.py`, `Base.metadata.create_all` automatically creates:
  1. `order_pickups`
  2. `seller_commercial_configs`
  3. `payments`
  4. `refunds`
  5. `seller_billing_invoices`
  6. `seller_settlements`
  7. `orders` (with `reselected_from_order_id`)

### 3.2 Phase 7 Reusable Test Fixtures for `conftest.py`

To eliminate test boilerplate across `test_commercial.py`, `test_pickup.py`, `test_payment.py`, `test_billing.py`, and `test_settlement.py`, add the following standardized helper fixtures to `backend/tests/conftest.py`:

```python
# ---------------------------------------------------------------------------
# Phase 7 Test Fixture Helpers
# ---------------------------------------------------------------------------

def create_test_commercial_config(
    seller_id: uuid.UUID,
    tenant_id: uuid.UUID,
    commercial_model: str = "COMMISSION",
    commission_rate_percent: Decimal = Decimal("10.00"),
    subscription_fee: Decimal = Decimal("0.00"),
    marketplace_gateway: str = "TTC_GATEWAY",
    payment_required_before_pickup: bool = True,
    outstanding_receivable_allowed: bool = False,
    payment_deadline_days: int = 1,
    restriction_level: str = "NONE",
    overdue_grace_days: int = 7,
    daily_penalty_rate: Decimal = Decimal("0.001"),
) -> SellerCommercialConfiguration:
    with SessionLocal() as db:
        config = SellerCommercialConfiguration(
            seller_id=seller_id,
            tenant_id=tenant_id,
            commercial_model=commercial_model,
            commission_rate_percent=commission_rate_percent,
            subscription_fee=subscription_fee,
            marketplace_gateway=marketplace_gateway,
            payment_required_before_pickup=payment_required_before_pickup,
            outstanding_receivable_allowed=outstanding_receivable_allowed,
            payment_deadline_days=payment_deadline_days,
            restriction_level=restriction_level,
            overdue_grace_days=overdue_grace_days,
            daily_penalty_rate=daily_penalty_rate,
        )
        db.add(config)
        db.commit()
        return db.get(SellerCommercialConfiguration, config.id)


def create_test_pickup(
    order_id: uuid.UUID,
    tenant_id: uuid.UUID,
    seller_id: uuid.UUID,
    status: str = "SCHEDULED",
    actual_details: dict | None = None,
) -> OrderPickup:
    with SessionLocal() as db:
        pickup = OrderPickup(
            order_id=order_id,
            tenant_id=tenant_id,
            seller_id=seller_id,
            status=status,
            actual_details=actual_details or {"items": [{"name": "Shirt", "count": 2}]},
        )
        db.add(pickup)
        db.commit()
        return db.get(OrderPickup, pickup.id)


def create_test_payment(
    order_id: uuid.UUID,
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID,
    seller_id: uuid.UUID,
    amount: Decimal,
    gateway_type: str = "TTC_GATEWAY",
    status: str = "PENDING",
    currency: str = "INR",
    gateway_fee: Decimal = Decimal("0.00"),
    gateway_tax: Decimal = Decimal("0.00"),
    ttc_commission: Decimal = Decimal("0.00"),
    ttc_commission_tax: Decimal = Decimal("0.00"),
) -> Payment:
    with SessionLocal() as db:
        payment = Payment(
            order_id=order_id,
            tenant_id=tenant_id,
            customer_id=customer_id,
            seller_id=seller_id,
            gateway_type=gateway_type,
            status=status,
            currency=currency,
            amount=amount,
            gateway_fee=gateway_fee,
            gateway_tax=gateway_tax,
            ttc_commission=ttc_commission,
            ttc_commission_tax=ttc_commission_tax,
            refunded_amount=Decimal("0.00"),
            retained_amount=amount,
        )
        db.add(payment)
        db.commit()
        return db.get(Payment, payment.id)


def create_test_billing_invoice(
    seller_id: uuid.UUID,
    tenant_id: uuid.UUID,
    invoice_month: date,
    due_date: date,
    status: str = "PENDING",
    currency: str = "INR",
    subtotal: Decimal = Decimal("100.00"),
    tax_total: Decimal = Decimal("18.00"),
    penalty_total: Decimal = Decimal("0.00"),
    total_amount: Decimal = Decimal("118.00"),
) -> SellerBillingInvoice:
    with SessionLocal() as db:
        invoice = SellerBillingInvoice(
            seller_id=seller_id,
            tenant_id=tenant_id,
            invoice_month=invoice_month,
            due_date=due_date,
            status=status,
            currency=currency,
            subtotal=subtotal,
            tax_total=tax_total,
            penalty_total=penalty_total,
            total_amount=total_amount,
        )
        db.add(invoice)
        db.commit()
        return db.get(SellerBillingInvoice, invoice.id)


def create_test_settlement(
    seller_id: uuid.UUID,
    tenant_id: uuid.UUID,
    amount: Decimal,
    scheduled_for: date,
    gateway_type: str = "TTC_GATEWAY",
    status: str = "SCHEDULED",
    currency: str = "INR",
) -> SellerSettlement:
    with SessionLocal() as db:
        settlement = SellerSettlement(
            seller_id=seller_id,
            tenant_id=tenant_id,
            amount=amount,
            scheduled_for=scheduled_for,
            gateway_type=gateway_type,
            status=status,
            currency=currency,
        )
        db.add(settlement)
        db.commit()
        return db.get(SellerSettlement, settlement.id)
```

---

## 4. Multi-Tenant Repositories Architecture

### 4.1 Core Architectural Principles
1. **Inherit `BaseRepository`**: All repositories take `db: Session` in `__init__`.
2. **SQLAlchemy 2.0 Declarative Statements**: Exclusively utilize `select(...)`, `update(...)`, `.where(...)`, `.options(...)`, `.scalars().all()`, `.scalar_one_or_none()`.
3. **Transaction Boundary Discipline**: Repositories invoke `self.db.flush()` on inserts and updates, never calling `self.db.commit()`. This allows the calling service layer or FastAPI request dependency to manage transactional atomicity across multiple repository operations.
4. **Strict Tenant & Seller Scoping**: Every query is filtered by `tenant_id` and/or `seller_id`. Queries from unauthorized tenants return `None` or empty lists, allowing the API layer to emit `404 Not Found` without leaking entity existence (defense against ID enumeration/injection).
5. **Standard Pagination**: List endpoints return `tuple[Sequence[Entity], int]` containing the page items and the total matching count.

---

### 4.2 `CommercialRepository` Specification (`backend/app/repositories/commercial.py`)

```python
"""Phase 7 — Commercial Repository.

Data access layer for seller commercial configurations and restriction statuses.
Ensures strict tenant and seller isolation.
"""
from __future__ import annotations

import uuid
from typing import Any, Sequence
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.commercial import SellerCommercialConfiguration, SellerRestrictionLevel
from app.repositories.base import BaseRepository


class CommercialRepository(BaseRepository):
    """Database access for SellerCommercialConfiguration entities."""

    def create(self, config: SellerCommercialConfiguration) -> SellerCommercialConfiguration:
        self.db.add(config)
        self.db.flush()
        return config

    def get_by_seller_id(
        self, tenant_id: uuid.UUID, seller_id: uuid.UUID
    ) -> SellerCommercialConfiguration | None:
        """Fetch commercial config scoped to both tenant_id and seller_id."""
        stmt = select(SellerCommercialConfiguration).where(
            SellerCommercialConfiguration.tenant_id == tenant_id,
            SellerCommercialConfiguration.seller_id == seller_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_seller_id_unscoped(
        self, seller_id: uuid.UUID
    ) -> SellerCommercialConfiguration | None:
        """Unscoped lookup for internal background services (e.g. restriction worker)."""
        stmt = select(SellerCommercialConfiguration).where(
            SellerCommercialConfiguration.seller_id == seller_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def update(
        self,
        tenant_id: uuid.UUID,
        seller_id: uuid.UUID,
        **kwargs: Any,
    ) -> SellerCommercialConfiguration | None:
        """Update commercial configuration fields scoped to tenant."""
        config = self.get_by_seller_id(tenant_id=tenant_id, seller_id=seller_id)
        if not config:
            return None

        for key, value in kwargs.items():
            if hasattr(config, key) and value is not None:
                setattr(config, key, value)

        self.db.flush()
        return config

    def update_restriction_level(
        self,
        seller_id: uuid.UUID,
        restriction_level: str,
    ) -> SellerCommercialConfiguration | None:
        """Update restriction level for a seller."""
        config = self.get_by_seller_id_unscoped(seller_id)
        if not config:
            return None

        config.restriction_level = restriction_level
        self.db.flush()
        return config

    def list_restricted_sellers(
        self, restriction_level: str | None = None
    ) -> Sequence[SellerCommercialConfiguration]:
        """List all sellers with operational restrictions."""
        stmt = select(SellerCommercialConfiguration).where(
            SellerCommercialConfiguration.restriction_level != SellerRestrictionLevel.NONE.value
        )
        if restriction_level:
            stmt = stmt.where(SellerCommercialConfiguration.restriction_level == restriction_level)
        return self.db.execute(stmt).scalars().all()

    def list_all(
        self, limit: int = 50, offset: int = 0
    ) -> tuple[Sequence[SellerCommercialConfiguration], int]:
        """Platform admin paginated listing of all commercial configurations."""
        count_q = select(func.count()).select_from(SellerCommercialConfiguration)
        total = self.db.execute(count_q).scalar() or 0

        stmt = (
            select(SellerCommercialConfiguration)
            .order_by(SellerCommercialConfiguration.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        items = self.db.execute(stmt).scalars().all()
        return items, total
```

---

### 4.3 `PickupRepository` Specification (`backend/app/repositories/pickup.py`)

```python
"""Phase 7 — Order Pickup Repository.

Data access layer for physical garment pickup lifecycles and detail approvals.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Sequence
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.order import Order
from app.models.pickup import OrderPickup, PickupStatus
from app.repositories.base import BaseRepository


class PickupRepository(BaseRepository):
    """Database access for OrderPickup entities."""

    def create(self, pickup: OrderPickup) -> OrderPickup:
        self.db.add(pickup)
        self.db.flush()
        return pickup

    def get_by_id(
        self, pickup_id: uuid.UUID, tenant_id: uuid.UUID | None = None
    ) -> OrderPickup | None:
        stmt = select(OrderPickup).where(OrderPickup.id == pickup_id)
        if tenant_id:
            stmt = stmt.where(OrderPickup.tenant_id == tenant_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_order_id(
        self, order_id: uuid.UUID, tenant_id: uuid.UUID | None = None
    ) -> OrderPickup | None:
        """Fetch pickup by order_id, optionally validating tenant ownership."""
        stmt = select(OrderPickup).where(OrderPickup.order_id == order_id)
        if tenant_id:
            stmt = stmt.where(OrderPickup.tenant_id == tenant_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_order_id_for_customer(
        self, order_id: uuid.UUID, customer_id: uuid.UUID
    ) -> OrderPickup | None:
        """Fetch pickup ensuring the associated order belongs to the customer."""
        stmt = (
            select(OrderPickup)
            .join(Order, Order.id == OrderPickup.order_id)
            .where(
                OrderPickup.order_id == order_id,
                Order.customer_id == customer_id,
            )
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def submit_actual_details(
        self,
        order_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actual_details: dict[str, Any],
        actual_pickup_at: datetime | None = None,
    ) -> OrderPickup | None:
        """Seller submits verified pickup details; transitions status to DETAILS_SUBMITTED."""
        pickup = self.get_by_order_id(order_id, tenant_id)
        if not pickup:
            return None

        pickup.actual_details = actual_details
        pickup.details_submitted_at = func.now()
        if actual_pickup_at:
            pickup.actual_pickup_at = actual_pickup_at
        pickup.status = PickupStatus.DETAILS_SUBMITTED.value
        self.db.flush()
        return pickup

    def approve_details(
        self, order_id: uuid.UUID, customer_id: uuid.UUID
    ) -> OrderPickup | None:
        """Customer approves pickup details; transitions status to APPROVED."""
        pickup = self.get_by_order_id_for_customer(order_id, customer_id)
        if not pickup:
            return None

        pickup.status = PickupStatus.APPROVED.value
        pickup.approved_at = func.now()
        self.db.flush()
        return pickup

    def reject_details(
        self, order_id: uuid.UUID, customer_id: uuid.UUID, reason: str
    ) -> OrderPickup | None:
        """Customer rejects pickup details; transitions status to REJECTED."""
        pickup = self.get_by_order_id_for_customer(order_id, customer_id)
        if not pickup:
            return None

        pickup.status = PickupStatus.REJECTED.value
        pickup.rejection_reason = reason
        self.db.flush()
        return pickup

    def complete_pickup(
        self, order_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> OrderPickup | None:
        """Seller completes pickup physical workflow; transitions status to COMPLETED."""
        pickup = self.get_by_order_id(order_id, tenant_id)
        if not pickup:
            return None

        pickup.status = PickupStatus.COMPLETED.value
        pickup.completed_at = func.now()
        self.db.flush()
        return pickup

    def list_by_seller(
        self,
        seller_id: uuid.UUID,
        tenant_id: uuid.UUID,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[Sequence[OrderPickup], int]:
        """Paginated pickup listing scoped to seller and tenant."""
        base = select(OrderPickup).where(
            OrderPickup.seller_id == seller_id,
            OrderPickup.tenant_id == tenant_id,
        )
        count_q = select(func.count()).select_from(OrderPickup).where(
            OrderPickup.seller_id == seller_id,
            OrderPickup.tenant_id == tenant_id,
        )

        if status:
            base = base.where(OrderPickup.status == status)
            count_q = count_q.where(OrderPickup.status == status)

        total = self.db.execute(count_q).scalar() or 0
        items = (
            self.db.execute(
                base.order_by(OrderPickup.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            .scalars()
            .all()
        )
        return items, total
```

---

### 4.4 `PaymentRepository` Specification (`backend/app/repositories/payment.py`)

```python
"""Phase 7 — Payment Repository.

Data access layer for payment transactions, refunds, fee/tax ledgers, and cooling holds.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Sequence
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.payment import Payment, PaymentStatus, Refund
from app.repositories.base import BaseRepository


class PaymentRepository(BaseRepository):
    """Database access for Payment and Refund entities."""

    # -------------------------------------------------------------------
    # Payments CRUD & Scoped Lookups
    # -------------------------------------------------------------------

    def create(self, payment: Payment) -> Payment:
        self.db.add(payment)
        self.db.flush()
        return payment

    def get_by_id(
        self, payment_id: uuid.UUID, tenant_id: uuid.UUID | None = None
    ) -> Payment | None:
        stmt = select(Payment).where(Payment.id == payment_id)
        if tenant_id:
            stmt = stmt.where(Payment.tenant_id == tenant_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_order_id(
        self, order_id: uuid.UUID, tenant_id: uuid.UUID | None = None
    ) -> Payment | None:
        stmt = select(Payment).where(Payment.order_id == order_id)
        if tenant_id:
            stmt = stmt.where(Payment.tenant_id == tenant_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_order_id_for_customer(
        self, order_id: uuid.UUID, customer_id: uuid.UUID
    ) -> Payment | None:
        stmt = select(Payment).where(
            Payment.order_id == order_id,
            Payment.customer_id == customer_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def update_status(
        self,
        payment_id: uuid.UUID,
        status: str,
        gateway_transaction_id: str | None = None,
        paid_at: datetime | None = None,
    ) -> Payment | None:
        payment = self.get_by_id(payment_id)
        if not payment:
            return None

        payment.status = status
        if gateway_transaction_id:
            payment.gateway_transaction_id = gateway_transaction_id
        if paid_at:
            payment.paid_at = paid_at
        elif status == PaymentStatus.SUCCEEDED.value and not payment.paid_at:
            payment.paid_at = func.now()

        self.db.flush()
        return payment

    # -------------------------------------------------------------------
    # Refund Operations & Retained Amount Adjustments
    # -------------------------------------------------------------------

    def create_refund(self, refund: Refund) -> Refund:
        self.db.add(refund)
        self.db.flush()
        return refund

    def list_refunds_for_payment(self, payment_id: uuid.UUID) -> Sequence[Refund]:
        stmt = select(Refund).where(Refund.payment_id == payment_id).order_by(Refund.created_at.asc())
        return self.db.execute(stmt).scalars().all()

    def update_retained_commission(
        self,
        payment_id: uuid.UUID,
        refunded_amount: Decimal,
        retained_amount: Decimal,
        ttc_commission: Decimal,
        ttc_commission_tax: Decimal,
        status: str,
    ) -> Payment | None:
        """Update payment financial balances following partial/full refund."""
        payment = self.get_by_id(payment_id)
        if not payment:
            return None

        payment.refunded_amount = refunded_amount
        payment.retained_amount = retained_amount
        payment.ttc_commission = ttc_commission
        payment.ttc_commission_tax = ttc_commission_tax
        payment.status = status
        self.db.flush()
        return payment

    # -------------------------------------------------------------------
    # Settlement Queries (TTC Gateway 15-Day Cooling Period)
    # -------------------------------------------------------------------

    def get_eligible_cooling_payments(
        self,
        seller_id: uuid.UUID,
        tenant_id: uuid.UUID,
        cooling_cutoff: datetime,
    ) -> Sequence[Payment]:
        """Fetch payments eligible for Monday weekly settlement.
        
        Criteria:
        - TTC_GATEWAY transaction
        - SUCCEEDED status
        - Not yet settled (settled == False)
        - Cleared 15-day cooling period (paid_at <= cooling_cutoff)
        - Strictly scoped to seller_id and tenant_id
        """
        stmt = (
            select(Payment)
            .where(
                Payment.seller_id == seller_id,
                Payment.tenant_id == tenant_id,
                Payment.gateway_type == "TTC_GATEWAY",
                Payment.status == PaymentStatus.SUCCEEDED.value,
                Payment.settled == False,
                Payment.paid_at <= cooling_cutoff,
            )
            .order_by(Payment.paid_at.asc())
        )
        return self.db.execute(stmt).scalars().all()

    def mark_settled(self, payment_ids: list[uuid.UUID], settlement_id: uuid.UUID) -> int:
        """Batch mark payments as settled and link to SellerSettlement record."""
        if not payment_ids:
            return 0

        stmt = (
            select(Payment)
            .where(Payment.id.in_(payment_ids))
        )
        payments = self.db.execute(stmt).scalars().all()
        for p in payments:
            p.settled = True
            p.settlement_id = settlement_id
        self.db.flush()
        return len(payments)

    # -------------------------------------------------------------------
    # Paginated Listing
    # -------------------------------------------------------------------

    def list_by_seller(
        self,
        seller_id: uuid.UUID,
        tenant_id: uuid.UUID,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[Sequence[Payment], int]:
        base = select(Payment).where(
            Payment.seller_id == seller_id,
            Payment.tenant_id == tenant_id,
        )
        count_q = select(func.count()).select_from(Payment).where(
            Payment.seller_id == seller_id,
            Payment.tenant_id == tenant_id,
        )
        if status:
            base = base.where(Payment.status == status)
            count_q = count_q.where(Payment.status == status)

        total = self.db.execute(count_q).scalar() or 0
        items = (
            self.db.execute(
                base.order_by(Payment.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            .scalars()
            .all()
        )
        return items, total

    def list_by_customer(
        self,
        customer_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[Sequence[Payment], int]:
        base = select(Payment).where(Payment.customer_id == customer_id)
        count_q = select(func.count()).select_from(Payment).where(Payment.customer_id == customer_id)

        total = self.db.execute(count_q).scalar() or 0
        items = (
            self.db.execute(
                base.order_by(Payment.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            .scalars()
            .all()
        )
        return items, total
```

---

### 4.5 `BillingRepository` Specification (`backend/app/repositories/billing.py`)

```python
"""Phase 7 — Billing Repository.

Data access layer for monthly seller billing invoices, overdue calculations, and late penalties.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Sequence
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.billing import InvoiceStatus, SellerBillingInvoice
from app.repositories.base import BaseRepository


class BillingRepository(BaseRepository):
    """Database access for SellerBillingInvoice entities."""

    def create(self, invoice: SellerBillingInvoice) -> SellerBillingInvoice:
        self.db.add(invoice)
        self.db.flush()
        return invoice

    def get_by_id(
        self, invoice_id: uuid.UUID, tenant_id: uuid.UUID | None = None
    ) -> SellerBillingInvoice | None:
        stmt = select(SellerBillingInvoice).where(SellerBillingInvoice.id == invoice_id)
        if tenant_id:
            stmt = stmt.where(SellerBillingInvoice.tenant_id == tenant_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_seller_and_month(
        self, seller_id: uuid.UUID, tenant_id: uuid.UUID, invoice_month: date
    ) -> SellerBillingInvoice | None:
        """Find invoice for a seller in a given month to guarantee idempotent invoice creation."""
        stmt = select(SellerBillingInvoice).where(
            SellerBillingInvoice.seller_id == seller_id,
            SellerBillingInvoice.tenant_id == tenant_id,
            SellerBillingInvoice.invoice_month == invoice_month,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_overdue_invoices(
        self, as_of_date: date, tenant_id: uuid.UUID | None = None
    ) -> Sequence[SellerBillingInvoice]:
        """Fetch all invoices whose due_date has passed and are still unpaid."""
        stmt = (
            select(SellerBillingInvoice)
            .where(
                SellerBillingInvoice.status.in_([InvoiceStatus.PENDING.value, InvoiceStatus.OVERDUE.value]),
                SellerBillingInvoice.due_date < as_of_date,
            )
        )
        if tenant_id:
            stmt = stmt.where(SellerBillingInvoice.tenant_id == tenant_id)
        return self.db.execute(stmt).scalars().all()

    def get_max_overdue_days_for_seller(
        self, seller_id: uuid.UUID, as_of_date: date
    ) -> int:
        """Calculate the longest number of days overdue across all unpaid invoices for a seller."""
        stmt = select(SellerBillingInvoice).where(
            SellerBillingInvoice.seller_id == seller_id,
            SellerBillingInvoice.status.in_([InvoiceStatus.PENDING.value, InvoiceStatus.OVERDUE.value]),
            SellerBillingInvoice.due_date < as_of_date,
        )
        invoices = self.db.execute(stmt).scalars().all()
        if not invoices:
            return 0
        max_days = max((as_of_date - inv.due_date).days for inv in invoices)
        return max(max_days, 0)

    def update_penalty(
        self,
        invoice_id: uuid.UUID,
        penalty_total: Decimal,
        total_amount: Decimal,
        status: str = InvoiceStatus.OVERDUE.value,
    ) -> SellerBillingInvoice | None:
        """Idempotently update accrued late-payment penalties on an overdue invoice."""
        invoice = self.get_by_id(invoice_id)
        if not invoice:
            return None

        invoice.penalty_total = penalty_total
        invoice.total_amount = total_amount
        invoice.status = status
        self.db.flush()
        return invoice

    def mark_as_paid(
        self, invoice_id: uuid.UUID, paid_at: datetime | None = None
    ) -> SellerBillingInvoice | None:
        invoice = self.get_by_id(invoice_id)
        if not invoice:
            return None

        invoice.status = InvoiceStatus.PAID.value
        invoice.paid_at = paid_at or func.now()
        self.db.flush()
        return invoice

    def list_by_seller(
        self,
        seller_id: uuid.UUID,
        tenant_id: uuid.UUID,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[Sequence[SellerBillingInvoice], int]:
        base = select(SellerBillingInvoice).where(
            SellerBillingInvoice.seller_id == seller_id,
            SellerBillingInvoice.tenant_id == tenant_id,
        )
        count_q = select(func.count()).select_from(SellerBillingInvoice).where(
            SellerBillingInvoice.seller_id == seller_id,
            SellerBillingInvoice.tenant_id == tenant_id,
        )
        if status:
            base = base.where(SellerBillingInvoice.status == status)
            count_q = count_q.where(SellerBillingInvoice.status == status)

        total = self.db.execute(count_q).scalar() or 0
        items = (
            self.db.execute(
                base.order_by(SellerBillingInvoice.invoice_month.desc())
                .limit(limit)
                .offset(offset)
            )
            .scalars()
            .all()
        )
        return items, total

    def list_all(
        self,
        status: str | None = None,
        invoice_month: date | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[SellerBillingInvoice], int]:
        base = select(SellerBillingInvoice)
        count_q = select(func.count()).select_from(SellerBillingInvoice)

        if status:
            base = base.where(SellerBillingInvoice.status == status)
            count_q = count_q.where(SellerBillingInvoice.status == status)
        if invoice_month:
            base = base.where(SellerBillingInvoice.invoice_month == invoice_month)
            count_q = count_q.where(SellerBillingInvoice.invoice_month == invoice_month)

        total = self.db.execute(count_q).scalar() or 0
        items = (
            self.db.execute(
                base.order_by(SellerBillingInvoice.invoice_month.desc(), SellerBillingInvoice.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            .scalars()
            .all()
        )
        return items, total
```

---

### 4.6 `SettlementRepository` Specification (`backend/app/repositories/settlement.py`)

```python
"""Phase 7 — Settlement Repository.

Data access layer for weekly Monday settlement disbursements, status transitions, and audit trails.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Sequence
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.billing import SellerSettlement, SettlementStatus
from app.repositories.base import BaseRepository


class SettlementRepository(BaseRepository):
    """Database access for SellerSettlement entities."""

    def create(self, settlement: SellerSettlement) -> SellerSettlement:
        self.db.add(settlement)
        self.db.flush()
        return settlement

    def get_by_id(
        self, settlement_id: uuid.UUID, tenant_id: uuid.UUID | None = None
    ) -> SellerSettlement | None:
        stmt = select(SellerSettlement).where(SellerSettlement.id == settlement_id)
        if tenant_id:
            stmt = stmt.where(SellerSettlement.tenant_id == tenant_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_scheduled_for_date(
        self,
        scheduled_for: date,
        status: str = SettlementStatus.PENDING.value,
    ) -> Sequence[SellerSettlement]:
        """Fetch all settlements scheduled for a target Monday."""
        stmt = select(SellerSettlement).where(
            SellerSettlement.scheduled_for == scheduled_for,
            SellerSettlement.status == status,
        )
        return self.db.execute(stmt).scalars().all()

    def update_status(
        self,
        settlement_id: uuid.UUID,
        status: str,
        reference_id: str | None = None,
        processed_at: datetime | None = None,
    ) -> SellerSettlement | None:
        settlement = self.get_by_id(settlement_id)
        if not settlement:
            return None

        settlement.status = status
        if reference_id:
            settlement.reference_id = reference_id
        if processed_at:
            settlement.processed_at = processed_at
        elif status == SettlementStatus.SETTLED.value and not settlement.processed_at:
            settlement.processed_at = func.now()

        self.db.flush()
        return settlement

    def list_by_seller(
        self,
        seller_id: uuid.UUID,
        tenant_id: uuid.UUID,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[Sequence[SellerSettlement], int]:
        base = select(SellerSettlement).where(
            SellerSettlement.seller_id == seller_id,
            SellerSettlement.tenant_id == tenant_id,
        )
        count_q = select(func.count()).select_from(SellerSettlement).where(
            SellerSettlement.seller_id == seller_id,
            SellerSettlement.tenant_id == tenant_id,
        )
        if status:
            base = base.where(SellerSettlement.status == status)
            count_q = count_q.where(SellerSettlement.status == status)

        total = self.db.execute(count_q).scalar() or 0
        items = (
            self.db.execute(
                base.order_by(SellerSettlement.scheduled_for.desc(), SellerSettlement.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            .scalars()
            .all()
        )
        return items, total

    def list_all(
        self,
        status: str | None = None,
        scheduled_for: date | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[SellerSettlement], int]:
        base = select(SellerSettlement)
        count_q = select(func.count()).select_from(SellerSettlement)

        if status:
            base = base.where(SellerSettlement.status == status)
            count_q = count_q.where(SellerSettlement.status == status)
        if scheduled_for:
            base = base.where(SellerSettlement.scheduled_for == scheduled_for)
            count_q = count_q.where(SellerSettlement.scheduled_for == scheduled_for)

        total = self.db.execute(count_q).scalar() or 0
        items = (
            self.db.execute(
                base.order_by(SellerSettlement.scheduled_for.desc(), SellerSettlement.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            .scalars()
            .all()
        )
        return items, total
```

---

## 5. Security, Isolation & ID Injection Defense Matrix

| Component / Query | Security Vector | Mitigation Strategy | Failure Result |
|---|---|---|---|
| `CommercialRepository.get_by_seller_id` | Seller A queries Seller B's commercial agreement | Scoped by `tenant_id == tenant_id` AND `seller_id == seller_id` | Returns `None` -> API emits 404 |
| `CommercialRepository.update` | Seller A attempts to modify Seller B's commission rate | Update statement scoped to `tenant_id` | Returns `None` -> API emits 404 |
| `PickupRepository.get_by_order_id` | Seller A queries pickup details of Seller B's customer order | Scoped by `tenant_id == tenant_id` | Returns `None` -> API emits 404 |
| `PickupRepository.approve_details` | Customer A attempts to approve pickup for Customer B's order | Joins `Order` and checks `Order.customer_id == customer_id` | Returns `None` -> API emits 404 |
| `PaymentRepository.get_by_order_id` | Cross-tenant order payment lookup | Scoped by `tenant_id == tenant_id` | Returns `None` -> API emits 404 |
| `PaymentRepository.get_eligible_cooling_payments` | Payout batch includes cross-tenant funds | Scoped strictly to `tenant_id == tenant_id` AND `seller_id == seller_id` | Only owner's cleared funds are batched |
| `BillingRepository.get_by_seller_and_month` | Duplicate monthly billing invoice injection | Filter on `(seller_id, tenant_id, invoice_month)` + unique constraint | Returns existing invoice -> prevents double billing |
| `SettlementRepository.list_by_seller` | Seller attempts to view platform-wide payouts | Scoped strictly to `seller_id` AND `tenant_id` | Only authenticated seller payouts returned |

---

## 6. Implementation & Verification Checklist for Implementer M1

1. **Permissions & Roles**:
   - Update `backend/app/core/permissions/constants.py`:
     - Add `COMMERCIAL_READ`, `COMMERCIAL_MANAGE`, `PAYMENT_READ`, `PAYMENT_PROCESS`, `BILLING_READ`, `BILLING_MANAGE`, `SETTLEMENT_READ`, `SETTLEMENT_PROCESS` to `PermissionName`.
     - Add `CUSTOMER = 'CUSTOMER'` to `RoleName`.
     - Update `DEFAULT_ROLE_PERMISSIONS` dictionary for all roles as specified in Section 2.3.
   - Update `backend/app/services/roles.py`:
     - Add `ROLE_DESCRIPTIONS[RoleName.CUSTOMER.value]`.
     - Add descriptions for all 8 Phase 7 permissions to `PERMISSION_DESCRIPTIONS`.
2. **Model Imports in `__init__.py`**:
   - Ensure `backend/app/models/__init__.py` imports and exposes `OrderPickup` and `PickupStatus` from `app.models.pickup`.
3. **Test Fixtures in `conftest.py`**:
   - Verify `reset_database` drops and creates all tables.
   - Add the Phase 7 helper functions (`create_test_commercial_config`, `create_test_pickup`, `create_test_payment`, `create_test_billing_invoice`, `create_test_settlement`).
4. **Repositories**:
   - Create `backend/app/repositories/commercial.py` as specified in Section 4.2.
   - Create `backend/app/repositories/pickup.py` as specified in Section 4.3.
   - Create `backend/app/repositories/payment.py` as specified in Section 4.4.
   - Create `backend/app/repositories/billing.py` as specified in Section 4.5.
   - Create `backend/app/repositories/settlement.py` as specified in Section 4.6.
   - Export all repositories in `backend/app/repositories/__init__.py`.
5. **Static Verification**:
   ```bash
   python -m py_compile backend/app/core/permissions/constants.py
   python -m py_compile backend/app/services/roles.py
   python -m py_compile backend/app/repositories/commercial.py
   python -m py_compile backend/app/repositories/pickup.py
   python -m py_compile backend/app/repositories/payment.py
   python -m py_compile backend/app/repositories/billing.py
   python -m py_compile backend/app/repositories/settlement.py
   ```
