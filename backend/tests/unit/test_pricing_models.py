"""Unit tests for Phase 5: Pricing Engine Foundation.

Tests Models, Enums, Pydantic Schemas, and PricingRepository with
strict multi-tenant isolation and mathematical precision validation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.db import SessionLocal
from app.models.pricing import (
    ComponentType,
    PriceBook,
    PriceBookScope,
    PriceBookStatus,
    PriceRule,
    PriceRuleType,
    RateType,
)
from app.repositories.pricing import PricingRepository
from app.schemas.pricing import (
    PriceBookCreate,
    PriceBookUpdate,
    PriceRuleCreate,
    PriceRuleUpdate,
    PricingCalculationItemRequest,
    PricingCalculationItemResult,
    PricingCalculationRequest,
    PricingCalculationResult,
    validate_currency_code,
)
from app.models.seller import Seller
from tests.conftest import create_test_tenant


def create_test_seller(tenant_id: uuid.UUID, business_name: str = "Test Seller") -> Seller:
    with SessionLocal() as db:
        seller = Seller(
            tenant_id=tenant_id,
            business_name=business_name,
            slug=f"seller-{uuid.uuid4().hex[:8]}",
            status="ACTIVE",
        )
        db.add(seller)
        db.commit()
        db.refresh(seller)
        return seller


# ============================================================================
# 1. ENUMS AND MODELS TESTS
# ============================================================================

def test_pricing_enums_values():
    """Verify all pricing enums define expected canonical string values."""
    assert PriceBookScope.PLATFORM_DEFAULT.value == "PLATFORM_DEFAULT"
    assert PriceBookScope.SELLER.value == "SELLER"
    assert PriceBookScope.BRANCH.value == "BRANCH"

    assert PriceBookStatus.DRAFT.value == "DRAFT"
    assert PriceBookStatus.ACTIVE.value == "ACTIVE"
    assert PriceBookStatus.INACTIVE.value == "INACTIVE"
    assert PriceBookStatus.ARCHIVED.value == "ARCHIVED"

    assert PriceRuleType.FIXED.value == "FIXED"
    assert PriceRuleType.PER_ITEM.value == "PER_ITEM"
    assert PriceRuleType.PER_UNIT.value == "PER_UNIT"
    assert PriceRuleType.PER_WEIGHT.value == "PER_WEIGHT"

    assert ComponentType.BASE_PRICE.value == "BASE_PRICE"
    assert ComponentType.SURCHARGE.value == "SURCHARGE"
    assert ComponentType.DISCOUNT.value == "DISCOUNT"
    assert ComponentType.TAX.value == "TAX"

    assert RateType.FLAT.value == "FLAT"
    assert RateType.PERCENTAGE.value == "PERCENTAGE"


def test_price_book_model_creation_and_defaults():
    """Verify PriceBook ORM model defaults and persistence."""
    tenant = create_test_tenant("Test Pricing Tenant")
    with SessionLocal() as db:
        book = PriceBook(
            tenant_id=tenant.id,
            name="Default Test Book",
            description="Test book description",
        )
        db.add(book)
        db.commit()
        db.refresh(book)

        assert book.id is not None
        assert book.tenant_id == tenant.id
        assert book.name == "Default Test Book"
        assert book.currency == "USD"
        assert book.scope == PriceBookScope.SELLER
        assert book.status == PriceBookStatus.DRAFT
        assert book.is_default is False
        assert book.is_active is True
        assert book.priority == 0
        assert book.created_at is not None
        assert book.updated_at is not None


def test_price_rule_model_creation_and_cascade_delete():
    """Verify PriceRule ORM model and cascade delete from PriceBook."""
    tenant = create_test_tenant("Cascade Tenant")
    with SessionLocal() as db:
        book = PriceBook(
            tenant_id=tenant.id,
            name="Parent Book",
        )
        db.add(book)
        db.commit()
        db.refresh(book)

        rule = PriceRule(
            tenant_id=tenant.id,
            price_book_id=book.id,
            rule_type=PriceRuleType.PER_ITEM,
            component_type=ComponentType.BASE_PRICE,
            rate_type=RateType.FLAT,
            rate=Decimal("15.50"),
            priority=5,
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)

        assert rule.id is not None
        assert rule.price_book_id == book.id
        assert rule.rate == Decimal("15.50")
        assert rule.status == "ACTIVE"
        assert rule.is_active is True
        assert rule.priority == 5
        assert rule.price_book.id == book.id

        # Test cascade delete
        db.delete(book)
        db.commit()

        # Rule should be cascade deleted
        found_rule = db.query(PriceRule).filter(PriceRule.id == rule.id).first()
        assert found_rule is None


# ============================================================================
# 2. PYDANTIC SCHEMAS VALIDATION TESTS
# ============================================================================

def test_currency_code_validator():
    """Verify currency code validator accepts ISO 4217 uppercase and rejects invalid."""
    assert validate_currency_code("USD") == "USD"
    assert validate_currency_code("eur") == "EUR"
    assert validate_currency_code(" GBP ") == "GBP"

    with pytest.raises(ValueError):
        validate_currency_code("US")
    with pytest.raises(ValueError):
        validate_currency_code("USDD")
    with pytest.raises(ValueError):
        validate_currency_code("123")


def test_price_book_create_scope_inference_and_validation():
    """Verify scope inference and foreign key validation on PriceBookCreate."""
    seller_uuid = uuid.uuid4()
    branch_uuid = uuid.uuid4()

    # Inferred SELLER
    dto_seller = PriceBookCreate(name="Seller Book", seller_id=seller_uuid)
    assert dto_seller.scope == PriceBookScope.SELLER

    # Inferred BRANCH
    dto_branch = PriceBookCreate(name="Branch Book", seller_id=seller_uuid, branch_id=branch_uuid)
    assert dto_branch.scope == PriceBookScope.BRANCH

    # Inferred PLATFORM_DEFAULT
    dto_platform = PriceBookCreate(name="Platform Default Book")
    assert dto_platform.scope == PriceBookScope.PLATFORM_DEFAULT

    # Invalid: PLATFORM_DEFAULT with seller_id
    with pytest.raises(ValidationError):
        PriceBookCreate(
            name="Invalid Platform",
            scope=PriceBookScope.PLATFORM_DEFAULT,
            seller_id=seller_uuid,
        )

    # Invalid: SELLER without seller_id
    with pytest.raises(ValidationError):
        PriceBookCreate(name="Invalid Seller", scope=PriceBookScope.SELLER)

    # Invalid: BRANCH without branch_id
    with pytest.raises(ValidationError):
        PriceBookCreate(
            name="Invalid Branch",
            scope=PriceBookScope.BRANCH,
            seller_id=seller_uuid,
        )


def test_price_rule_rate_and_dates_validation():
    """Verify rate non-negativity and chronological date ordering on PriceRuleCreate."""
    # Negative rate rejected
    with pytest.raises(ValidationError):
        PriceRuleCreate(
            rule_type=PriceRuleType.FIXED,
            rate=Decimal("-1.00"),
        )

    # Valid non-negative rates
    dto_zero = PriceRuleCreate(rule_type=PriceRuleType.FIXED, rate=Decimal("0.00"))
    assert dto_zero.rate == Decimal("0.00")

    dto_pos = PriceRuleCreate(rule_type=PriceRuleType.PER_ITEM, rate=Decimal("25.99"))
    assert dto_pos.rate == Decimal("25.99")

    # Chronological date validation
    now = datetime.now(timezone.utc)
    future = now + timedelta(days=30)
    past = now - timedelta(days=30)

    # Valid range
    dto_valid_dates = PriceRuleCreate(
        rule_type=PriceRuleType.FIXED,
        rate=Decimal("10.00"),
        effective_from=now,
        effective_to=future,
    )
    assert dto_valid_dates.effective_to >= dto_valid_dates.effective_from

    # Invalid range (effective_to < effective_from)
    with pytest.raises(ValidationError):
        PriceRuleCreate(
            rule_type=PriceRuleType.FIXED,
            rate=Decimal("10.00"),
            effective_from=future,
            effective_to=past,
        )


def test_pricing_calculation_grand_total_invariant():
    """Verify PricingCalculationResult enforces subtotal + surcharges - discounts + tax == grand_total."""
    item_res = PricingCalculationItemResult(
        service_id=uuid.uuid4(),
        unit_price=Decimal("10.00"),
        quantity=Decimal("2"),
        base_price=Decimal("20.00"),
        surcharges=Decimal("2.00"),
        discounts=Decimal("1.00"),
        tax=Decimal("1.50"),
        subtotal=Decimal("20.00"),
        total=Decimal("22.50"),
    )

    # Valid invariant: 20.00 + 2.00 - 1.00 + 1.50 = 22.50
    valid_res = PricingCalculationResult(
        currency="USD",
        subtotal=Decimal("20.00"),
        total_surcharges=Decimal("2.00"),
        total_discounts=Decimal("1.00"),
        total_tax=Decimal("1.50"),
        grand_total=Decimal("22.50"),
        items=[item_res],
    )
    assert valid_res.grand_total == Decimal("22.50")

    # Invalid invariant: grand_total wrong
    with pytest.raises(ValidationError):
        PricingCalculationResult(
            currency="USD",
            subtotal=Decimal("20.00"),
            total_surcharges=Decimal("2.00"),
            total_discounts=Decimal("1.00"),
            total_tax=Decimal("1.50"),
            grand_total=Decimal("25.00"),  # Incorrect!
            items=[item_res],
        )


def test_pricing_calculation_request_schema():
    """Verify PricingCalculationRequest validates currency and synchronizes calculation_date."""
    seller_id = uuid.uuid4()
    service_id = uuid.uuid4()

    item_req = PricingCalculationItemRequest(
        service_id=service_id,
        quantity=Decimal("3"),
    )
    assert item_req.quantity == Decimal("3")

    now = datetime.now(timezone.utc)
    calc_req = PricingCalculationRequest(
        seller_id=seller_id,
        calculation_date=now,
        items=[item_req],
    )
    assert calc_req.currency == "USD"
    assert calc_req.calculation_time == now

    # Quantity <= 0 rejected
    with pytest.raises(ValidationError):
        PricingCalculationItemRequest(
            service_id=service_id,
            quantity=Decimal("0"),
        )


# ============================================================================
# 3. REPOSITORY MULTI-TENANT ISOLATION TESTS
# ============================================================================

def test_pricing_repository_tenant_isolation_books():
    """Verify Tenant A cannot access, mutate, or delete Tenant B's price books."""
    tenant_a = create_test_tenant("Tenant Alpha")
    tenant_b = create_test_tenant("Tenant Beta")
    seller_a = create_test_seller(tenant_a.id, "Seller A")
    seller_b = create_test_seller(tenant_b.id, "Seller B")

    with SessionLocal() as db:
        repo = PricingRepository(db)

        # Create book for Tenant A
        book_a = repo.create_book(
            tenant_a.id,
            PriceBook(
                name="Tenant A Book",
                scope=PriceBookScope.SELLER,
                seller_id=seller_a.id,
            ),
        )
        db.commit()

        # Create book for Tenant B
        book_b = repo.create_book(
            tenant_b.id,
            PriceBook(
                name="Tenant B Book",
                scope=PriceBookScope.SELLER,
                seller_id=seller_b.id,
            ),
        )
        db.commit()

        # Tenant A lookup Tenant A -> Success
        assert repo.get_book(tenant_a.id, book_a.id) is not None

        # Tenant A lookup Tenant B -> Denied (None)
        assert repo.get_book(tenant_a.id, book_b.id) is None

        # Tenant A list books -> Contains only Tenant A's book
        books_for_a = repo.list_books(tenant_a.id, include_platform_defaults=False)
        assert len(books_for_a) == 1
        assert books_for_a[0].id == book_a.id

        # Tenant A update Tenant B -> Denied (None)
        upd = repo.update_book(tenant_a.id, book_b.id, PriceBookUpdate(name="Hacked"))
        assert upd is None
        # Verify book B name was not changed
        assert repo.get_book(tenant_b.id, book_b.id).name == "Tenant B Book"

        # Tenant A delete Tenant B -> Denied (False)
        assert repo.delete_book(tenant_a.id, book_b.id) is False
        assert repo.get_book(tenant_b.id, book_b.id) is not None

        # Tenant A delete Tenant A -> Success (True)
        assert repo.delete_book(tenant_a.id, book_a.id) is True
        assert repo.get_book(tenant_a.id, book_a.id) is None


def test_pricing_repository_cross_tenant_rule_injection_prevented():
    """Verify Tenant A cannot add rules to Tenant B's book, and cannot see or mutate Tenant B's rules."""
    tenant_a = create_test_tenant("Tenant Rule Alpha")
    tenant_b = create_test_tenant("Tenant Rule Beta")
    seller_b = create_test_seller(tenant_b.id, "Seller Rule B")

    with SessionLocal() as db:
        repo = PricingRepository(db)

        book_b = repo.create_book(
            tenant_b.id,
            PriceBook(
                name="Tenant B Book",
                scope=PriceBookScope.SELLER,
                seller_id=seller_b.id,
            ),
        )
        db.commit()

        # Tenant A attempts to create rule on Tenant B's book -> Denied (None)
        injected_rule = repo.create_rule(
            tenant_a.id,
            book_b.id,
            PriceRule(
                rule_type=PriceRuleType.FIXED,
                component_type=ComponentType.BASE_PRICE,
                rate=Decimal("10.00"),
            ),
        )
        assert injected_rule is None

        # Tenant B creates rule on its own book -> Success
        valid_rule_b = repo.create_rule(
            tenant_b.id,
            book_b.id,
            PriceRule(
                rule_type=PriceRuleType.FIXED,
                component_type=ComponentType.BASE_PRICE,
                rate=Decimal("15.00"),
            ),
        )
        db.commit()
        assert valid_rule_b is not None

        # Tenant A attempts to read Tenant B's rule -> Denied (None)
        assert repo.get_rule(tenant_a.id, valid_rule_b.id) is None

        # Tenant A attempts to update Tenant B's rule -> Denied (None)
        assert repo.update_rule(tenant_a.id, valid_rule_b.id, PriceRuleUpdate(rate=Decimal("0.01"))) is None

        # Tenant A attempts to delete Tenant B's rule -> Denied (False)
        assert repo.delete_rule(tenant_a.id, valid_rule_b.id) is False


def test_pricing_repository_get_active_rules_for_calculation():
    """Verify get_active_rules_for_calculation filters status, dates, and isolates tenants."""
    tenant_a = create_test_tenant("Calculation Tenant A")
    tenant_b = create_test_tenant("Calculation Tenant B")
    seller_a = create_test_seller(tenant_a.id, "Calc Seller A")
    seller_b = create_test_seller(tenant_b.id, "Calc Seller B")

    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        repo = PricingRepository(db)

        # 1. Active Book for Tenant A
        active_book = repo.create_book(
            tenant_a.id,
            PriceBook(
                name="Active Seller Book",
                scope=PriceBookScope.SELLER,
                status=PriceBookStatus.ACTIVE,
                seller_id=seller_a.id,
                is_active=True,
            ),
        )
        # 2. DRAFT Book for Tenant A (should be excluded)
        draft_book = repo.create_book(
            tenant_a.id,
            PriceBook(
                name="Draft Book",
                scope=PriceBookScope.SELLER,
                status=PriceBookStatus.DRAFT,
                seller_id=seller_a.id,
                is_active=True,
            ),
        )
        # 3. Active Book for Tenant B (should be excluded by tenant filter)
        tenant_b_book = repo.create_book(
            tenant_b.id,
            PriceBook(
                name="Tenant B Book",
                scope=PriceBookScope.SELLER,
                status=PriceBookStatus.ACTIVE,
                seller_id=seller_b.id,
                is_active=True,
            ),
        )
        db.commit()

        # Rule in active book (valid)
        rule_active = repo.create_rule(
            tenant_a.id,
            active_book.id,
            PriceRule(
                rule_type=PriceRuleType.PER_ITEM,
                component_type=ComponentType.BASE_PRICE,
                rate=Decimal("12.00"),
                status="ACTIVE",
                is_active=True,
            ),
        )
        # Rule in active book with expired date (should be excluded)
        rule_expired = repo.create_rule(
            tenant_a.id,
            active_book.id,
            PriceRule(
                rule_type=PriceRuleType.PER_ITEM,
                component_type=ComponentType.BASE_PRICE,
                rate=Decimal("5.00"),
                effective_from=now - timedelta(days=20),
                effective_to=now - timedelta(days=5),
                status="ACTIVE",
                is_active=True,
            ),
        )
        # Rule in active book marked INACTIVE (should be excluded)
        rule_inactive = repo.create_rule(
            tenant_a.id,
            active_book.id,
            PriceRule(
                rule_type=PriceRuleType.PER_ITEM,
                component_type=ComponentType.BASE_PRICE,
                rate=Decimal("8.00"),
                status="INACTIVE",
                is_active=False,
            ),
        )
        # Rule in draft book (should be excluded)
        rule_in_draft = repo.create_rule(
            tenant_a.id,
            draft_book.id,
            PriceRule(
                rule_type=PriceRuleType.PER_ITEM,
                component_type=ComponentType.BASE_PRICE,
                rate=Decimal("20.00"),
                status="ACTIVE",
                is_active=True,
            ),
        )
        # Rule in Tenant B's book (should be excluded)
        rule_tenant_b = repo.create_rule(
            tenant_b.id,
            tenant_b_book.id,
            PriceRule(
                rule_type=PriceRuleType.PER_ITEM,
                component_type=ComponentType.BASE_PRICE,
                rate=Decimal("99.00"),
                status="ACTIVE",
                is_active=True,
            ),
        )
        db.commit()

        # Query calculation rules for Tenant A
        calc_rules = repo.get_active_rules_for_calculation(
            tenant_id=tenant_a.id,
            seller_id=seller_a.id,
            as_of=now,
        )

        matched_ids = [r.id for r in calc_rules]
        assert rule_active.id in matched_ids
        assert rule_expired.id not in matched_ids
        assert rule_inactive.id not in matched_ids
        assert rule_in_draft.id not in matched_ids
        assert rule_tenant_b.id not in matched_ids
