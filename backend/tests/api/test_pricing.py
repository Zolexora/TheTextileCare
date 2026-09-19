"""Comprehensive Phase 5 Pricing Engine Tests.

Covers:
  - Price book CRUD lifecycle
  - Price rule CRUD lifecycle
  - Deterministic calculation: FIXED, PER_ITEM, PER_UNIT, PER_WEIGHT
  - Surcharges (flat + percentage)
  - Discounts (flat + percentage, capped at subtotal)
  - Tax (percentage)
  - Combined (subtotal + surcharge - discount + tax = grand_total)
  - Effective date window filtering
  - Branch-level override precedence
  - Draft/inactive rules not leaking into calculation
  - Decimal precision and rounding
  - Tenant isolation / ID injection
  - RBAC enforcement
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db import SessionLocal
from app.models.seller import Seller, Branch
from app.models.catalog import Catalog, Service, ServiceItem
from app.models.pricing import (
    PriceBook,
    PriceBookScope,
    PriceBookStatus,
    PriceRule,
    PriceRuleType,
    ComponentType,
    RateType,
)
from tests.conftest import (
    create_test_membership,
    create_test_tenant,
    create_test_user,
    make_auth_headers,
)

client = TestClient(app)


# =============================================================================
# Helpers
# =============================================================================

def _db_seller(tenant_id: uuid.UUID) -> Seller:
    with SessionLocal() as db:
        s = Seller(
            tenant_id=tenant_id,
            business_name="Test Seller",
            slug=f"seller-{uuid.uuid4().hex[:8]}",
        )
        db.add(s)
        db.commit()
        db.refresh(s)
        return s


def _db_branch(tenant_id: uuid.UUID, seller_id: uuid.UUID) -> Branch:
    with SessionLocal() as db:
        b = Branch(
            tenant_id=tenant_id,
            seller_id=seller_id,
            name="Main Branch",
            code=f"BR-{uuid.uuid4().hex[:6]}",
        )
        db.add(b)
        db.commit()
        db.refresh(b)
        return b


def _db_catalog_service(tenant_id: uuid.UUID, seller_id: uuid.UUID) -> tuple[Catalog, Service]:
    with SessionLocal() as db:
        cat = Catalog(
            tenant_id=tenant_id,
            seller_id=seller_id,
            name="Test Catalog",
        )
        db.add(cat)
        db.flush()
        svc = Service(
            tenant_id=tenant_id,
            catalog_id=cat.id,
            name="Shirt Wash",
            slug=f"shirt-wash-{uuid.uuid4().hex[:6]}",
        )
        db.add(svc)
        db.commit()
        db.refresh(cat)
        db.refresh(svc)
        return cat, svc


def _db_price_book(
    tenant_id: uuid.UUID,
    seller_id: uuid.UUID,
    branch_id: uuid.UUID | None = None,
    scope: PriceBookScope = PriceBookScope.SELLER,
    priority: int = 0,
) -> PriceBook:
    with SessionLocal() as db:
        book = PriceBook(
            tenant_id=tenant_id,
            seller_id=seller_id,
            branch_id=branch_id,
            name="Test Book",
            currency="USD",
            scope=scope,
            status=PriceBookStatus.ACTIVE,
            is_active=True,
            priority=priority,
        )
        db.add(book)
        db.commit()
        db.refresh(book)
        return book


def _db_price_rule(
    tenant_id: uuid.UUID,
    book_id: uuid.UUID,
    service_id: uuid.UUID,
    rule_type: PriceRuleType = PriceRuleType.PER_ITEM,
    rate: Decimal = Decimal("100.00"),
    component_type: ComponentType = ComponentType.BASE_PRICE,
    rate_type: RateType = RateType.FLAT,
    status: str = "ACTIVE",
    is_active: bool = True,
    effective_from: datetime | None = None,
    effective_to: datetime | None = None,
    service_item_id: uuid.UUID | None = None,
) -> PriceRule:
    with SessionLocal() as db:
        rule = PriceRule(
            tenant_id=tenant_id,
            price_book_id=book_id,
            service_id=service_id,
            service_item_id=service_item_id,
            name="Test Rule",
            rule_type=rule_type,
            component_type=component_type,
            rate_type=rate_type,
            rate=rate,
            status=status,
            is_active=is_active,
            priority=0,
            effective_from=effective_from,
            effective_to=effective_to,
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)
        return rule


def _seller_admin(tenant_id: uuid.UUID):
    user = create_test_user(f"padmin-{uuid.uuid4().hex[:6]}@test.com")
    create_test_membership(tenant_id, user.id, "SELLER_ADMIN")
    return user


def _viewer(tenant_id: uuid.UUID):
    user = create_test_user(f"viewer-{uuid.uuid4().hex[:6]}@test.com")
    create_test_membership(tenant_id, user.id, "VIEWER")
    return user


# =============================================================================
# Price Book CRUD
# =============================================================================

class TestPriceBookCRUD:
    def test_create_and_get_price_book(self):
        tenant = create_test_tenant("PB Corp")
        user = _seller_admin(tenant.id)
        seller = _db_seller(tenant.id)
        headers = make_auth_headers(user, tenant)

        res = client.post("/api/v1/pricing/price-books", headers=headers, json={
            "name": "Standard Pricing",
            "currency": "USD",
            "seller_id": str(seller.id),
            "scope": "SELLER",
        })
        assert res.status_code == 201, res.text
        book = res.json()
        assert book["name"] == "Standard Pricing"
        assert book["status"] == "DRAFT"
        assert book["currency"] == "USD"

        res2 = client.get(f"/api/v1/pricing/price-books/{book['id']}", headers=headers)
        assert res2.status_code == 200
        assert res2.json()["id"] == book["id"]

    def test_list_price_books(self):
        tenant = create_test_tenant("ListPB Corp")
        user = _seller_admin(tenant.id)
        seller = _db_seller(tenant.id)
        headers = make_auth_headers(user, tenant)

        for i in range(3):
            client.post("/api/v1/pricing/price-books", headers=headers, json={
                "name": f"Book {i}",
                "currency": "USD",
                "seller_id": str(seller.id),
            })

        res = client.get("/api/v1/pricing/price-books", headers=headers)
        assert res.status_code == 200
        assert len(res.json()) >= 3

    def test_update_price_book(self):
        tenant = create_test_tenant("UpdatePB Corp")
        user = _seller_admin(tenant.id)
        seller = _db_seller(tenant.id)
        headers = make_auth_headers(user, tenant)

        book = _db_price_book(tenant.id, seller.id)
        res = client.patch(f"/api/v1/pricing/price-books/{book.id}", headers=headers, json={
            "name": "Updated Name",
        })
        assert res.status_code == 200
        assert res.json()["name"] == "Updated Name"

    def test_activate_deactivate_lifecycle(self):
        tenant = create_test_tenant("LifecyclePB Corp")
        user = _seller_admin(tenant.id)
        seller = _db_seller(tenant.id)
        headers = make_auth_headers(user, tenant)

        book = _db_price_book(tenant.id, seller.id)
        res = client.post(f"/api/v1/pricing/price-books/{book.id}/activate", headers=headers)
        assert res.status_code == 200
        assert res.json()["status"] == "ACTIVE"

        res = client.post(f"/api/v1/pricing/price-books/{book.id}/deactivate", headers=headers)
        assert res.status_code == 200
        assert res.json()["status"] == "INACTIVE"


# =============================================================================
# Price Rule CRUD
# =============================================================================

class TestPriceRuleCRUD:
    def test_create_and_get_rule(self):
        tenant = create_test_tenant("Rules Corp")
        user = _seller_admin(tenant.id)
        seller = _db_seller(tenant.id)
        _, svc = _db_catalog_service(tenant.id, seller.id)
        book = _db_price_book(tenant.id, seller.id)
        headers = make_auth_headers(user, tenant)

        res = client.post(f"/api/v1/pricing/price-books/{book.id}/rules", headers=headers, json={
            "name": "Shirt Base",
            "service_id": str(svc.id),
            "rule_type": "PER_ITEM",
            "component_type": "BASE_PRICE",
            "rate_type": "FLAT",
            "rate": "150.00",
        })
        assert res.status_code == 201, res.text
        rule = res.json()
        assert rule["rule_type"] == "PER_ITEM"
        assert rule["rate"] == "150.00"

        res2 = client.get(f"/api/v1/pricing/rules/{rule['id']}", headers=headers)
        assert res2.status_code == 200
        assert res2.json()["id"] == rule["id"]

    def test_activate_deactivate_rule(self):
        tenant = create_test_tenant("RuleLifecycle Corp")
        user = _seller_admin(tenant.id)
        seller = _db_seller(tenant.id)
        _, svc = _db_catalog_service(tenant.id, seller.id)
        book = _db_price_book(tenant.id, seller.id)
        rule = _db_price_rule(tenant.id, book.id, svc.id)
        headers = make_auth_headers(user, tenant)

        res = client.post(f"/api/v1/pricing/rules/{rule.id}/deactivate", headers=headers)
        assert res.status_code == 200
        assert res.json()["status"] == "INACTIVE"

        res = client.post(f"/api/v1/pricing/rules/{rule.id}/activate", headers=headers)
        assert res.status_code == 200
        assert res.json()["status"] == "ACTIVE"


# =============================================================================
# Calculation Tests
# =============================================================================

class TestPricingCalculation:
    def _setup(self, tenant_name: str):
        tenant = create_test_tenant(tenant_name)
        user = _seller_admin(tenant.id)
        seller = _db_seller(tenant.id)
        _, svc = _db_catalog_service(tenant.id, seller.id)
        book = _db_price_book(tenant.id, seller.id)
        headers = make_auth_headers(user, tenant)
        return tenant, user, seller, svc, book, headers

    def test_fixed_pricing(self):
        tenant, user, seller, svc, book, headers = self._setup("Fixed Tenant")
        _db_price_rule(tenant.id, book.id, svc.id, rule_type=PriceRuleType.FIXED, rate=Decimal("500.00"))

        res = client.post("/api/v1/pricing/calculate", headers=headers, json={
            "seller_id": str(seller.id),
            "currency": "USD",
            "items": [{"service_id": str(svc.id), "quantity": "1"}],
        })
        assert res.status_code == 200, res.text
        result = res.json()
        assert result["grand_total"] == "500.00"
        assert result["subtotal"] == "500.00"

    def test_per_item_pricing(self):
        tenant, user, seller, svc, book, headers = self._setup("PerItem Tenant")
        _db_price_rule(tenant.id, book.id, svc.id, rule_type=PriceRuleType.PER_ITEM, rate=Decimal("100.00"))

        res = client.post("/api/v1/pricing/calculate", headers=headers, json={
            "seller_id": str(seller.id),
            "currency": "USD",
            "items": [{"service_id": str(svc.id), "quantity": "2"}],
        })
        assert res.status_code == 200, res.text
        result = res.json()
        assert result["subtotal"] == "200.00"
        assert result["grand_total"] == "200.00"

    def test_per_weight_pricing(self):
        tenant, user, seller, svc, book, headers = self._setup("PerWeight Tenant")
        _db_price_rule(tenant.id, book.id, svc.id, rule_type=PriceRuleType.PER_WEIGHT, rate=Decimal("80.00"))

        res = client.post("/api/v1/pricing/calculate", headers=headers, json={
            "seller_id": str(seller.id),
            "currency": "USD",
            "items": [{"service_id": str(svc.id), "quantity": "1", "weight": "3.5"}],
        })
        assert res.status_code == 200, res.text
        result = res.json()
        assert result["subtotal"] == "280.00"

    def test_multiple_items(self):
        tenant = create_test_tenant("MultiItem Tenant")
        user = _seller_admin(tenant.id)
        seller = _db_seller(tenant.id)
        # Create both services under the same catalog to avoid unique constraint
        with SessionLocal() as db:
            from app.models.catalog import Catalog, Service
            cat = Catalog(tenant_id=tenant.id, seller_id=seller.id, name="Multi Catalog")
            db.add(cat)
            db.flush()
            svc1 = Service(tenant_id=tenant.id, catalog_id=cat.id, name="Service 1", slug=f"svc1-{uuid.uuid4().hex[:6]}")
            svc2 = Service(tenant_id=tenant.id, catalog_id=cat.id, name="Service 2", slug=f"svc2-{uuid.uuid4().hex[:6]}")
            db.add_all([svc1, svc2])
            db.commit()
            db.refresh(svc1); db.refresh(svc2)
        book = _db_price_book(tenant.id, seller.id)
        _db_price_rule(tenant.id, book.id, svc1.id, rate=Decimal("100.00"))
        _db_price_rule(tenant.id, book.id, svc2.id, rate=Decimal("300.00"))
        headers = make_auth_headers(user, tenant)

        res = client.post("/api/v1/pricing/calculate", headers=headers, json={
            "seller_id": str(seller.id),
            "currency": "USD",
            "items": [
                {"service_id": str(svc1.id), "quantity": "2"},
                {"service_id": str(svc2.id), "quantity": "1"},
            ],
        })
        assert res.status_code == 200, res.text
        result = res.json()
        assert result["subtotal"] == "500.00"

    def test_surcharge_percentage(self):
        tenant, user, seller, svc, book, headers = self._setup("Surcharge Tenant")
        _db_price_rule(tenant.id, book.id, svc.id, rate=Decimal("500.00"), rule_type=PriceRuleType.FIXED)
        _db_price_rule(
            tenant.id, book.id, svc.id,
            component_type=ComponentType.SURCHARGE,
            rate_type=RateType.PERCENTAGE,
            rate=Decimal("10"),
            rule_type=PriceRuleType.FIXED,
        )

        res = client.post("/api/v1/pricing/calculate", headers=headers, json={
            "seller_id": str(seller.id),
            "currency": "USD",
            "items": [{"service_id": str(svc.id), "quantity": "1"}],
        })
        assert res.status_code == 200, res.text
        result = res.json()
        assert result["subtotal"] == "500.00"
        assert result["total_surcharges"] == "50.00"
        assert result["grand_total"] == "550.00"

    def test_flat_surcharge(self):
        tenant, user, seller, svc, book, headers = self._setup("FlatSurcharge Tenant")
        _db_price_rule(tenant.id, book.id, svc.id, rate=Decimal("500.00"), rule_type=PriceRuleType.FIXED)
        _db_price_rule(
            tenant.id, book.id, svc.id,
            component_type=ComponentType.SURCHARGE,
            rate_type=RateType.FLAT,
            rate=Decimal("50.00"),
            rule_type=PriceRuleType.FIXED,
        )

        res = client.post("/api/v1/pricing/calculate", headers=headers, json={
            "seller_id": str(seller.id),
            "currency": "USD",
            "items": [{"service_id": str(svc.id), "quantity": "1"}],
        })
        assert res.status_code == 200, res.text
        result = res.json()
        assert result["total_surcharges"] == "50.00"
        assert result["grand_total"] == "550.00"

    def test_discount_percentage(self):
        tenant, user, seller, svc, book, headers = self._setup("Discount Tenant")
        _db_price_rule(tenant.id, book.id, svc.id, rate=Decimal("500.00"), rule_type=PriceRuleType.FIXED)
        _db_price_rule(
            tenant.id, book.id, svc.id,
            component_type=ComponentType.DISCOUNT,
            rate_type=RateType.PERCENTAGE,
            rate=Decimal("10"),
            rule_type=PriceRuleType.FIXED,
        )

        res = client.post("/api/v1/pricing/calculate", headers=headers, json={
            "seller_id": str(seller.id),
            "currency": "USD",
            "items": [{"service_id": str(svc.id), "quantity": "1"}],
        })
        assert res.status_code == 200, res.text
        result = res.json()
        assert result["total_discounts"] == "50.00"
        assert result["grand_total"] == "450.00"

    def test_tax_calculation(self):
        tenant, user, seller, svc, book, headers = self._setup("Tax Tenant")
        _db_price_rule(tenant.id, book.id, svc.id, rate=Decimal("500.00"), rule_type=PriceRuleType.FIXED)
        _db_price_rule(
            tenant.id, book.id, svc.id,
            component_type=ComponentType.TAX,
            rate_type=RateType.PERCENTAGE,
            rate=Decimal("18"),
            rule_type=PriceRuleType.FIXED,
        )

        res = client.post("/api/v1/pricing/calculate", headers=headers, json={
            "seller_id": str(seller.id),
            "currency": "USD",
            "items": [{"service_id": str(svc.id), "quantity": "1"}],
        })
        assert res.status_code == 200, res.text
        result = res.json()
        assert result["total_tax"] == "90.00"
        assert result["grand_total"] == "590.00"

    def test_combined_calculation(self):
        """subtotal + surcharge - discount + tax = grand_total"""
        tenant, user, seller, svc, book, headers = self._setup("Combined Tenant")
        _db_price_rule(tenant.id, book.id, svc.id, rate=Decimal("500.00"), rule_type=PriceRuleType.FIXED)
        _db_price_rule(tenant.id, book.id, svc.id, component_type=ComponentType.SURCHARGE, rate_type=RateType.FLAT, rate=Decimal("50.00"), rule_type=PriceRuleType.FIXED)
        _db_price_rule(tenant.id, book.id, svc.id, component_type=ComponentType.DISCOUNT, rate_type=RateType.FLAT, rate=Decimal("25.00"), rule_type=PriceRuleType.FIXED)
        _db_price_rule(tenant.id, book.id, svc.id, component_type=ComponentType.TAX, rate_type=RateType.PERCENTAGE, rate=Decimal("18"), rule_type=PriceRuleType.FIXED)

        res = client.post("/api/v1/pricing/calculate", headers=headers, json={
            "seller_id": str(seller.id),
            "currency": "USD",
            "items": [{"service_id": str(svc.id), "quantity": "1"}],
        })
        assert res.status_code == 200, res.text
        r = res.json()
        subtotal = Decimal(r["subtotal"])
        surcharge = Decimal(r["total_surcharges"])
        discount = Decimal(r["total_discounts"])
        tax = Decimal(r["total_tax"])
        grand = Decimal(r["grand_total"])

        # taxable base = 500 + 50 - 25 = 525; tax = 525 * 0.18 = 94.50
        assert subtotal == Decimal("500.00")
        assert surcharge == Decimal("50.00")
        assert discount == Decimal("25.00")
        assert tax == Decimal("94.50")
        assert grand == subtotal + surcharge - discount + tax

    def test_decimal_precision_rounding(self):
        """Ensure fractional multiplication rounds correctly."""
        tenant, user, seller, svc, book, headers = self._setup("Rounding Tenant")
        _db_price_rule(tenant.id, book.id, svc.id, rule_type=PriceRuleType.PER_ITEM, rate=Decimal("33.33"))

        res = client.post("/api/v1/pricing/calculate", headers=headers, json={
            "seller_id": str(seller.id),
            "currency": "USD",
            "items": [{"service_id": str(svc.id), "quantity": "3"}],
        })
        assert res.status_code == 200, res.text
        # 33.33 × 3 = 99.99
        assert res.json()["subtotal"] == "99.99"

    def test_inactive_rule_not_used(self):
        tenant, user, seller, svc, book, headers = self._setup("InactiveRule Tenant")
        _db_price_rule(tenant.id, book.id, svc.id, is_active=False, status="INACTIVE", rate=Decimal("100.00"))

        res = client.post("/api/v1/pricing/calculate", headers=headers, json={
            "seller_id": str(seller.id),
            "currency": "USD",
            "items": [{"service_id": str(svc.id), "quantity": "1"}],
        })
        # Should fail — no active rule
        assert res.status_code == 422

    def test_effective_date_before_window(self):
        tenant, user, seller, svc, book, headers = self._setup("EffDate Before Tenant")
        future = datetime.now(timezone.utc) + timedelta(days=10)
        _db_price_rule(tenant.id, book.id, svc.id, effective_from=future, rate=Decimal("100.00"))

        res = client.post("/api/v1/pricing/calculate", headers=headers, json={
            "seller_id": str(seller.id),
            "currency": "USD",
            "items": [{"service_id": str(svc.id), "quantity": "1"}],
        })
        assert res.status_code == 422  # Rule not active yet

    def test_effective_date_after_window(self):
        tenant, user, seller, svc, book, headers = self._setup("EffDate After Tenant")
        past = datetime.now(timezone.utc) - timedelta(days=10)
        expired = datetime.now(timezone.utc) - timedelta(days=1)
        _db_price_rule(tenant.id, book.id, svc.id, effective_from=past, effective_to=expired, rate=Decimal("100.00"))

        res = client.post("/api/v1/pricing/calculate", headers=headers, json={
            "seller_id": str(seller.id),
            "currency": "USD",
            "items": [{"service_id": str(svc.id), "quantity": "1"}],
        })
        assert res.status_code == 422  # Rule expired

    def test_branch_overrides_seller(self):
        """Branch-scope book (higher priority) should win over Seller-scope book."""
        tenant = create_test_tenant("BranchOverride Tenant")
        user = _seller_admin(tenant.id)
        seller = _db_seller(tenant.id)
        branch = _db_branch(tenant.id, seller.id)
        _, svc = _db_catalog_service(tenant.id, seller.id)
        headers = make_auth_headers(user, tenant)

        seller_book = _db_price_book(tenant.id, seller.id, scope=PriceBookScope.SELLER, priority=0)
        branch_book = _db_price_book(tenant.id, seller.id, branch_id=branch.id, scope=PriceBookScope.BRANCH, priority=10)

        _db_price_rule(tenant.id, seller_book.id, svc.id, rate=Decimal("100.00"))
        _db_price_rule(tenant.id, branch_book.id, svc.id, rate=Decimal("75.00"))

        res = client.post("/api/v1/pricing/calculate", headers=headers, json={
            "seller_id": str(seller.id),
            "branch_id": str(branch.id),
            "currency": "USD",
            "items": [{"service_id": str(svc.id), "quantity": "1"}],
        })
        assert res.status_code == 200, res.text
        # Branch rule (75.00) should win
        assert res.json()["grand_total"] == "75.00"

    def test_missing_pricing_returns_422(self):
        tenant, user, seller, svc, book, headers = self._setup("MissingPrice Tenant")
        # No rules created

        res = client.post("/api/v1/pricing/calculate", headers=headers, json={
            "seller_id": str(seller.id),
            "currency": "USD",
            "items": [{"service_id": str(svc.id), "quantity": "1"}],
        })
        assert res.status_code == 422

    def test_discount_capped_at_subtotal(self):
        """Discount cannot push total negative."""
        tenant, user, seller, svc, book, headers = self._setup("DiscountCap Tenant")
        _db_price_rule(tenant.id, book.id, svc.id, rate=Decimal("100.00"), rule_type=PriceRuleType.FIXED)
        _db_price_rule(tenant.id, book.id, svc.id, component_type=ComponentType.DISCOUNT, rate_type=RateType.FLAT, rate=Decimal("999.00"), rule_type=PriceRuleType.FIXED)

        res = client.post("/api/v1/pricing/calculate", headers=headers, json={
            "seller_id": str(seller.id),
            "currency": "USD",
            "items": [{"service_id": str(svc.id), "quantity": "1"}],
        })
        assert res.status_code == 200, res.text
        assert Decimal(res.json()["grand_total"]) >= Decimal("0")


# =============================================================================
# Tenant Isolation & ID Injection
# =============================================================================

class TestTenantIsolation:
    def test_tenant_b_cannot_read_tenant_a_book(self):
        tenant_a = create_test_tenant("IsoA")
        user_a = _seller_admin(tenant_a.id)
        seller_a = _db_seller(tenant_a.id)
        book_a = _db_price_book(tenant_a.id, seller_a.id)

        tenant_b = create_test_tenant("IsoB")
        user_b = _seller_admin(tenant_b.id)
        headers_b = make_auth_headers(user_b, tenant_b)

        res = client.get(f"/api/v1/pricing/price-books/{book_a.id}", headers=headers_b)
        assert res.status_code == 404

    def test_tenant_b_cannot_create_book_for_tenant_a_seller(self):
        tenant_a = create_test_tenant("IsoA2")
        seller_a = _db_seller(tenant_a.id)

        tenant_b = create_test_tenant("IsoB2")
        user_b = _seller_admin(tenant_b.id)
        headers_b = make_auth_headers(user_b, tenant_b)

        res = client.post("/api/v1/pricing/price-books", headers=headers_b, json={
            "name": "Hack Book",
            "seller_id": str(seller_a.id),
            "currency": "USD",
        })
        assert res.status_code == 404

    def test_tenant_b_cannot_calculate_with_tenant_a_seller(self):
        tenant_a = create_test_tenant("IsoCalcA")
        seller_a = _db_seller(tenant_a.id)

        tenant_b = create_test_tenant("IsoCalcB")
        user_b = _seller_admin(tenant_b.id)
        _, svc_b = _db_catalog_service(tenant_b.id, _db_seller(tenant_b.id).id)
        headers_b = make_auth_headers(user_b, tenant_b)

        res = client.post("/api/v1/pricing/calculate", headers=headers_b, json={
            "seller_id": str(seller_a.id),  # Tenant A's seller
            "currency": "USD",
            "items": [{"service_id": str(svc_b.id), "quantity": "1"}],
        })
        assert res.status_code == 404

    def test_cross_tenant_rule_injection(self):
        tenant_a = create_test_tenant("RuleInjA")
        user_a = _seller_admin(tenant_a.id)
        seller_a = _db_seller(tenant_a.id)
        _, svc_a = _db_catalog_service(tenant_a.id, seller_a.id)
        book_a = _db_price_book(tenant_a.id, seller_a.id)

        tenant_b = create_test_tenant("RuleInjB")
        user_b = _seller_admin(tenant_b.id)
        seller_b = _db_seller(tenant_b.id)
        book_b = _db_price_book(tenant_b.id, seller_b.id)
        headers_b = make_auth_headers(user_b, tenant_b)

        # Tenant B tries to create a rule inside Tenant A's book
        res = client.post(f"/api/v1/pricing/price-books/{book_a.id}/rules", headers=headers_b, json={
            "service_id": str(svc_a.id),
            "rule_type": "FIXED",
            "rate": "1.00",
        })
        assert res.status_code == 404


# =============================================================================
# RBAC Enforcement
# =============================================================================

class TestPricingRBAC:
    def test_viewer_can_read_price_books(self):
        tenant = create_test_tenant("RBAC Read")
        seller = _db_seller(tenant.id)
        book = _db_price_book(tenant.id, seller.id)
        user = _viewer(tenant.id)
        headers = make_auth_headers(user, tenant)

        res = client.get(f"/api/v1/pricing/price-books/{book.id}", headers=headers)
        assert res.status_code == 200

    def test_viewer_cannot_create_price_book(self):
        tenant = create_test_tenant("RBAC Deny")
        seller = _db_seller(tenant.id)
        user = _viewer(tenant.id)
        headers = make_auth_headers(user, tenant)

        res = client.post("/api/v1/pricing/price-books", headers=headers, json={
            "name": "Hack Book",
            "seller_id": str(seller.id),
            "currency": "USD",
        })
        assert res.status_code == 403

    def test_viewer_cannot_activate_price_book(self):
        tenant = create_test_tenant("RBAC Activate")
        seller = _db_seller(tenant.id)
        book = _db_price_book(tenant.id, seller.id)
        user = _viewer(tenant.id)
        headers = make_auth_headers(user, tenant)

        res = client.post(f"/api/v1/pricing/price-books/{book.id}/activate", headers=headers)
        assert res.status_code == 403

    def test_viewer_can_calculate(self):
        """VIEWER has pricing.read so they can use the calculate endpoint."""
        tenant = create_test_tenant("RBAC Calc")
        seller = _db_seller(tenant.id)
        _, svc = _db_catalog_service(tenant.id, seller.id)
        book = _db_price_book(tenant.id, seller.id)
        _db_price_rule(tenant.id, book.id, svc.id, rate=Decimal("100.00"))
        user = _viewer(tenant.id)
        headers = make_auth_headers(user, tenant)

        res = client.post("/api/v1/pricing/calculate", headers=headers, json={
            "seller_id": str(seller.id),
            "currency": "USD",
            "items": [{"service_id": str(svc.id), "quantity": "1"}],
        })
        assert res.status_code == 200
