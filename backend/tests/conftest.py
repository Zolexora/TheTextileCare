from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

import pytest
import app.models  # noqa: F401
from app.db import Base, SessionLocal, engine
from app.models.billing import SellerBillingInvoice, SellerSettlement
from app.models.commercial import SellerCommercialConfiguration
from app.models.membership import Membership
from app.models.payment import Payment
from app.models.pickup import OrderPickup
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.memberships import MembershipRepository
from app.repositories.tenants import TenantRepository
from app.repositories.users import UserRepository
from app.services.roles import RoleService


@pytest.fixture(autouse=True)
def reset_database():
    """Reset database tables and seed defaults before each test."""
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.commit()
    engine.dispose()
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        RoleService(db).seed_defaults()
    yield


def create_test_user(email: str, name: str | None = None, auth_user_id: str | None = None) -> User:
    with SessionLocal() as db:
        repo = UserRepository(db)
        return repo.create_or_get(
            email=email,
            auth_user_id=auth_user_id or f'auth-{email}',
            name=name or email.split('@')[0],
        )


def create_test_tenant(name: str, slug: str | None = None) -> Tenant:
    with SessionLocal() as db:
        repo = TenantRepository(db)
        actual_slug = slug or name.lower().replace(' ', '-')
        return repo.create(name=name, slug=actual_slug)


def create_test_membership(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    role_name: str,
    status: str = 'ACTIVE',
) -> Membership:
    with SessionLocal() as db:
        repo = MembershipRepository(db)
        return repo.create(
            tenant_id=tenant_id,
            user_id=user_id,
            role_name=role_name,
            status=status,
        )


def make_auth_headers(user: User, tenant: Tenant | None = None) -> dict[str, str]:
    headers = {'X-User-Id': str(user.id)}
    if tenant:
        headers['X-Tenant-Id'] = str(tenant.id)
    return headers


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
    daily_penalty_rate: Decimal = Decimal("0.0010"),
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
        db.refresh(config)
        return config


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
        db.refresh(pickup)
        return pickup


def create_test_payment(
    order_id: uuid.UUID,
    tenant_id: uuid.UUID,
    customer_id: uuid.UUID,
    seller_id: uuid.UUID,
    amount: Decimal,
    gateway_type: str = "TTC_GATEWAY",
    status: str = "PENDING",
    currency: str = "USD",
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
        db.refresh(payment)
        return payment


def create_test_billing_invoice(
    seller_id: uuid.UUID,
    tenant_id: uuid.UUID,
    invoice_month: str = "2026-09",
    due_date: date | None = None,
    status: str = "PENDING",
    currency: str = "USD",
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
            due_date=due_date or date(2026, 9, 15),
            status=status,
            currency=currency,
            subtotal=subtotal,
            tax_total=tax_total,
            penalty_total=penalty_total,
            total_amount=total_amount,
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        return invoice


def create_test_settlement(
    seller_id: uuid.UUID,
    tenant_id: uuid.UUID,
    amount: Decimal,
    scheduled_for: date | None = None,
    gateway_type: str = "TTC_GATEWAY",
    status: str = "SCHEDULED",
    currency: str = "USD",
) -> SellerSettlement:
    with SessionLocal() as db:
        settlement = SellerSettlement(
            seller_id=seller_id,
            tenant_id=tenant_id,
            amount=amount,
            scheduled_for=scheduled_for or date(2026, 9, 21),
            gateway_type=gateway_type,
            status=status,
            currency=currency,
        )
        db.add(settlement)
        db.commit()
        db.refresh(settlement)
        return settlement
