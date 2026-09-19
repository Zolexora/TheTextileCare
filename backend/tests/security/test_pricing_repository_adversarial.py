"""Adversarial security tests for PricingRepository multi-tenant isolation.

Milestone 1 Challenger 2: Adversarially attacks multi-tenant boundaries in
backend/app/repositories/pricing.py:
- Cross-tenant reads (get_book, list_books, get_rule, list_rules_for_book)
- Cross-tenant mutations (update_book, delete_book, update_rule, delete_rule)
- Cross-tenant rule injections (create_rule, foreign book target)
- Tamper-proofing of immutable fields (id, tenant_id, scope, seller_id, branch_id)
- Calculation engine rule leakage (get_active_rules_for_calculation)
- Repository create_book spoofing / injection vulnerabilities
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from app.db import SessionLocal
from app.models.catalog import Category, Service, ServiceItem
from app.models.pricing import (
    ComponentType,
    PriceBook,
    PriceBookScope,
    PriceBookStatus,
    PriceRule,
    PriceRuleType,
    RateType,
)
from app.models.seller import Branch, Seller
from app.repositories.pricing import PricingRepository
from app.schemas.pricing import PriceBookUpdate, PriceRuleUpdate
from tests.conftest import create_test_tenant


def create_tenant_hierarchy(name_prefix: str) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """Helper creating a complete tenant hierarchy: tenant, seller, branch."""
    tenant = create_test_tenant(f"{name_prefix} Tenant")
    with SessionLocal() as db:
        seller = Seller(
            tenant_id=tenant.id,
            business_name=f"{name_prefix} Seller",
            slug=f"seller-{uuid.uuid4().hex[:8]}",
            status="ACTIVE",
        )
        db.add(seller)
        db.commit()
        db.refresh(seller)

        branch = Branch(
            tenant_id=tenant.id,
            seller_id=seller.id,
            name=f"{name_prefix} Branch",
            code=f"BR-{uuid.uuid4().hex[:4].upper()}",
            status="ACTIVE",
        )
        db.add(branch)
        db.commit()
        db.refresh(branch)

        return tenant.id, seller.id, branch.id


# ============================================================================
# 1. CROSS-TENANT READ ATTACKS
# ============================================================================

def test_cross_tenant_get_book_rejected():
    """Tenant B must NOT be able to read Tenant A's price book."""
    tenant_a_id, seller_a_id, _ = create_tenant_hierarchy("ReadA")
    tenant_b_id, seller_b_id, _ = create_tenant_hierarchy("ReadB")

    with SessionLocal() as db:
        repo = PricingRepository(db)

        book_a = repo.create_book(
            tenant_a_id,
            PriceBook(name="Secret Book A", scope=PriceBookScope.SELLER, seller_id=seller_a_id),
        )
        db.commit()

        # Attack: Tenant B queries Tenant A's book
        stolen_book = repo.get_book(tenant_b_id, book_a.id, include_platform_defaults=False)
        assert stolen_book is None, "Tenant B leaked Tenant A's price book via get_book!"


def test_cross_tenant_get_book_with_platform_defaults_rejected():
    """Tenant B must NOT read Tenant A's book even if include_platform_defaults=True."""
    tenant_a_id, seller_a_id, _ = create_tenant_hierarchy("ReadPlatA")
    tenant_b_id, _, _ = create_tenant_hierarchy("ReadPlatB")

    with SessionLocal() as db:
        repo = PricingRepository(db)

        book_a = repo.create_book(
            tenant_a_id,
            PriceBook(name="Tenant A Book", scope=PriceBookScope.SELLER, seller_id=seller_a_id),
        )
        db.commit()

        # Attack: Tenant B queries with include_platform_defaults=True
        stolen_book = repo.get_book(tenant_b_id, book_a.id, include_platform_defaults=True)
        assert stolen_book is None, "Tenant B bypassed tenant isolation with include_platform_defaults=True!"


def test_cross_tenant_list_books_isolation():
    """Tenant B listing books must never return Tenant A's books."""
    tenant_a_id, seller_a_id, _ = create_tenant_hierarchy("ListA")
    tenant_b_id, seller_b_id, _ = create_tenant_hierarchy("ListB")

    with SessionLocal() as db:
        repo = PricingRepository(db)

        book_a = repo.create_book(
            tenant_a_id,
            PriceBook(name="Book Alpha", scope=PriceBookScope.SELLER, seller_id=seller_a_id),
        )
        book_b = repo.create_book(
            tenant_b_id,
            PriceBook(name="Book Beta", scope=PriceBookScope.SELLER, seller_id=seller_b_id),
        )
        db.commit()

        # Attack: Tenant B lists books
        books_for_b = repo.list_books(tenant_b_id, include_platform_defaults=False)
        book_ids_b = [b.id for b in books_for_b]

        assert book_b.id in book_ids_b
        assert book_a.id not in book_ids_b, "Tenant B saw Tenant A's book in list_books!"


def test_cross_tenant_list_books_foreign_seller_filter():
    """Tenant B cannot discover Tenant A's books by passing seller_id=seller_a."""
    tenant_a_id, seller_a_id, _ = create_tenant_hierarchy("FilterA")
    tenant_b_id, _, _ = create_tenant_hierarchy("FilterB")

    with SessionLocal() as db:
        repo = PricingRepository(db)

        book_a = repo.create_book(
            tenant_a_id,
            PriceBook(name="Seller A Book", scope=PriceBookScope.SELLER, seller_id=seller_a_id),
        )
        db.commit()

        # Attack: Tenant B queries list_books with seller_id belonging to Tenant A
        result = repo.list_books(tenant_b_id, seller_id=seller_a_id, include_platform_defaults=False)
        assert len(result) == 0, "Tenant B retrieved Tenant A's book by querying foreign seller_id!"


def test_cross_tenant_get_rule_rejected():
    """Tenant B must NOT be able to read Tenant A's price rule."""
    tenant_a_id, seller_a_id, _ = create_tenant_hierarchy("RuleReadA")
    tenant_b_id, _, _ = create_tenant_hierarchy("RuleReadB")

    with SessionLocal() as db:
        repo = PricingRepository(db)

        book_a = repo.create_book(
            tenant_a_id,
            PriceBook(name="Book A", scope=PriceBookScope.SELLER, seller_id=seller_a_id),
        )
        rule_a = repo.create_rule(
            tenant_a_id,
            book_a.id,
            PriceRule(
                rule_type=PriceRuleType.PER_ITEM,
                component_type=ComponentType.BASE_PRICE,
                rate=Decimal("33.00"),
            ),
        )
        db.commit()

        # Attack: Tenant B attempts to read rule_a
        stolen_rule = repo.get_rule(tenant_b_id, rule_a.id, include_platform_defaults=False)
        assert stolen_rule is None, "Tenant B read Tenant A's rule via get_rule!"

        # Attack: Tenant B attempts to read rule_a with include_platform_defaults=True
        stolen_rule_plat = repo.get_rule(tenant_b_id, rule_a.id, include_platform_defaults=True)
        assert stolen_rule_plat is None, "Tenant B read Tenant A's rule via include_platform_defaults!"


def test_cross_tenant_list_rules_for_book_rejected():
    """Tenant B must NOT list rules belonging to Tenant A's book."""
    tenant_a_id, seller_a_id, _ = create_tenant_hierarchy("ListRuleA")
    tenant_b_id, _, _ = create_tenant_hierarchy("ListRuleB")

    with SessionLocal() as db:
        repo = PricingRepository(db)

        book_a = repo.create_book(
            tenant_a_id,
            PriceBook(name="Book A", scope=PriceBookScope.SELLER, seller_id=seller_a_id),
        )
        repo.create_rule(
            tenant_a_id,
            book_a.id,
            PriceRule(
                rule_type=PriceRuleType.PER_ITEM,
                component_type=ComponentType.BASE_PRICE,
                rate=Decimal("15.00"),
            ),
        )
        db.commit()

        # Attack: Tenant B calls list_rules_for_book on book_a
        rules = repo.list_rules_for_book(tenant_b_id, book_a.id)
        assert len(rules) == 0, "Tenant B listed rules from Tenant A's book!"


# ============================================================================
# 2. CROSS-TENANT MUTATION & DELETION ATTACKS
# ============================================================================

def test_cross_tenant_update_book_rejected():
    """Tenant B must NOT update Tenant A's price book."""
    tenant_a_id, seller_a_id, _ = create_tenant_hierarchy("UpdBookA")
    tenant_b_id, _, _ = create_tenant_hierarchy("UpdBookB")

    with SessionLocal() as db:
        repo = PricingRepository(db)

        book_a = repo.create_book(
            tenant_a_id,
            PriceBook(name="Original Name", scope=PriceBookScope.SELLER, seller_id=seller_a_id),
        )
        db.commit()

        # Attack: Tenant B calls update_book
        result = repo.update_book(tenant_b_id, book_a.id, PriceBookUpdate(name="Tampered Name"))
        assert result is None, "Tenant B successfully mutated Tenant A's price book!"

        # Verify book A in DB was not modified
        refreshed = repo.get_book(tenant_a_id, book_a.id)
        assert refreshed.name == "Original Name"


def test_cross_tenant_delete_book_rejected():
    """Tenant B must NOT delete Tenant A's price book."""
    tenant_a_id, seller_a_id, _ = create_tenant_hierarchy("DelBookA")
    tenant_b_id, _, _ = create_tenant_hierarchy("DelBookB")

    with SessionLocal() as db:
        repo = PricingRepository(db)

        book_a = repo.create_book(
            tenant_a_id,
            PriceBook(name="Protected Book", scope=PriceBookScope.SELLER, seller_id=seller_a_id),
        )
        db.commit()

        # Attack: Tenant B calls delete_book
        deleted = repo.delete_book(tenant_b_id, book_a.id)
        assert deleted is False, "Tenant B was allowed to delete Tenant A's price book!"

        # Verify book A still exists
        surviving = repo.get_book(tenant_a_id, book_a.id)
        assert surviving is not None


def test_book_immutable_fields_tamper_proofing():
    """Tenant A cannot re-assign book id, tenant_id, scope, seller_id, or branch_id."""
    tenant_a_id, seller_a_id, branch_a_id = create_tenant_hierarchy("ImmutBookA")
    tenant_b_id, seller_b_id, branch_b_id = create_tenant_hierarchy("ImmutBookB")

    with SessionLocal() as db:
        repo = PricingRepository(db)

        book_a = repo.create_book(
            tenant_a_id,
            PriceBook(
                name="Immut Book",
                scope=PriceBookScope.SELLER,
                seller_id=seller_a_id,
            ),
        )
        db.commit()
        original_id = book_a.id

        # Attack: Attempt to update immutable fields via raw dict
        tamper_data = {
            "id": uuid.uuid4(),
            "tenant_id": tenant_b_id,
            "scope": PriceBookScope.PLATFORM_DEFAULT,
            "seller_id": seller_b_id,
            "branch_id": branch_b_id,
            "name": "Legit Name Change",
        }
        updated = repo.update_book(tenant_a_id, book_a.id, tamper_data)
        assert updated is not None
        assert updated.id == original_id, "Book id was tampered!"
        assert updated.tenant_id == tenant_a_id, "Book tenant_id was tampered!"
        assert updated.scope == PriceBookScope.SELLER, "Book scope was tampered!"
        assert updated.seller_id == seller_a_id, "Book seller_id was tampered!"
        assert updated.branch_id is None, "Book branch_id was tampered!"
        assert updated.name == "Legit Name Change"


def test_cross_tenant_update_rule_rejected():
    """Tenant B must NOT update Tenant A's price rule."""
    tenant_a_id, seller_a_id, _ = create_tenant_hierarchy("UpdRuleA")
    tenant_b_id, _, _ = create_tenant_hierarchy("UpdRuleB")

    with SessionLocal() as db:
        repo = PricingRepository(db)

        book_a = repo.create_book(
            tenant_a_id,
            PriceBook(name="Book A", scope=PriceBookScope.SELLER, seller_id=seller_a_id),
        )
        rule_a = repo.create_rule(
            tenant_a_id,
            book_a.id,
            PriceRule(
                rule_type=PriceRuleType.PER_ITEM,
                component_type=ComponentType.BASE_PRICE,
                rate=Decimal("100.00"),
            ),
        )
        db.commit()

        # Attack: Tenant B updates rule_a to rate 0.01
        res = repo.update_rule(tenant_b_id, rule_a.id, PriceRuleUpdate(rate=Decimal("0.01")))
        assert res is None, "Tenant B mutated Tenant A's rule!"

        # Verify rule_a rate unchanged
        refreshed = repo.get_rule(tenant_a_id, rule_a.id)
        assert refreshed.rate == Decimal("100.00")


def test_cross_tenant_delete_rule_rejected():
    """Tenant B must NOT delete Tenant A's price rule."""
    tenant_a_id, seller_a_id, _ = create_tenant_hierarchy("DelRuleA")
    tenant_b_id, _, _ = create_tenant_hierarchy("DelRuleB")

    with SessionLocal() as db:
        repo = PricingRepository(db)

        book_a = repo.create_book(
            tenant_a_id,
            PriceBook(name="Book A", scope=PriceBookScope.SELLER, seller_id=seller_a_id),
        )
        rule_a = repo.create_rule(
            tenant_a_id,
            book_a.id,
            PriceRule(
                rule_type=PriceRuleType.PER_ITEM,
                component_type=ComponentType.BASE_PRICE,
                rate=Decimal("50.00"),
            ),
        )
        db.commit()

        # Attack: Tenant B deletes rule_a
        deleted = repo.delete_rule(tenant_b_id, rule_a.id)
        assert deleted is False, "Tenant B deleted Tenant A's rule!"

        # Verify rule_a still exists
        surviving = repo.get_rule(tenant_a_id, rule_a.id)
        assert surviving is not None


def test_rule_immutable_fields_tamper_proofing():
    """Tenant A cannot re-assign rule id, tenant_id, or price_book_id."""
    tenant_a_id, seller_a_id, _ = create_tenant_hierarchy("ImmutRuleA")
    tenant_b_id, seller_b_id, _ = create_tenant_hierarchy("ImmutRuleB")

    with SessionLocal() as db:
        repo = PricingRepository(db)

        book_a = repo.create_book(
            tenant_a_id,
            PriceBook(name="Book A", scope=PriceBookScope.SELLER, seller_id=seller_a_id),
        )
        book_b = repo.create_book(
            tenant_b_id,
            PriceBook(name="Book B", scope=PriceBookScope.SELLER, seller_id=seller_b_id),
        )
        rule_a = repo.create_rule(
            tenant_a_id,
            book_a.id,
            PriceRule(
                rule_type=PriceRuleType.PER_ITEM,
                component_type=ComponentType.BASE_PRICE,
                rate=Decimal("25.00"),
            ),
        )
        db.commit()
        original_rule_id = rule_a.id

        # Attack: Attempt to mutate immutable fields
        tamper_data = {
            "id": uuid.uuid4(),
            "tenant_id": tenant_b_id,
            "price_book_id": book_b.id,
            "rate": Decimal("30.00"),
        }
        updated = repo.update_rule(tenant_a_id, rule_a.id, tamper_data)
        assert updated is not None
        assert updated.id == original_rule_id, "Rule id was tampered!"
        assert updated.tenant_id == tenant_a_id, "Rule tenant_id was tampered!"
        assert updated.price_book_id == book_a.id, "Rule price_book_id was hijacked to another book!"
        assert updated.rate == Decimal("30.00")


# ============================================================================
# 3. CROSS-TENANT RULE INJECTION ATTACKS
# ============================================================================

def test_cross_tenant_create_rule_rejected():
    """Tenant B must NOT inject a rule into Tenant A's price book."""
    tenant_a_id, seller_a_id, _ = create_tenant_hierarchy("InjRuleA")
    tenant_b_id, _, _ = create_tenant_hierarchy("InjRuleB")

    with SessionLocal() as db:
        repo = PricingRepository(db)

        book_a = repo.create_book(
            tenant_a_id,
            PriceBook(name="Book A", scope=PriceBookScope.SELLER, seller_id=seller_a_id),
        )
        db.commit()

        # Attack: Tenant B attempts to create rule under book_a
        injected = repo.create_rule(
            tenant_b_id,
            book_a.id,
            PriceRule(
                rule_type=PriceRuleType.FIXED,
                component_type=ComponentType.BASE_PRICE,
                rate=Decimal("0.00"),
            ),
        )
        assert injected is None, "Tenant B successfully injected a rule into Tenant A's price book!"


def test_create_rule_into_platform_default_book_rejected():
    """Tenant B must NOT inject rules into a global PLATFORM_DEFAULT price book."""
    tenant_b_id, _, _ = create_tenant_hierarchy("InjPlatB")

    with SessionLocal() as db:
        repo = PricingRepository(db)

        # Global platform default book
        plat_book = PriceBook(
            scope=PriceBookScope.PLATFORM_DEFAULT,
            tenant_id=None,
            name="Global Defaults",
            status=PriceBookStatus.ACTIVE,
            is_active=True,
        )
        db.add(plat_book)
        db.commit()
        db.refresh(plat_book)

        # Attack: Tenant B tries to add a rule to the global platform default book
        injected = repo.create_rule(
            tenant_b_id,
            plat_book.id,
            PriceRule(
                rule_type=PriceRuleType.PER_ITEM,
                component_type=ComponentType.BASE_PRICE,
                rate=Decimal("1.00"),
            ),
        )
        assert injected is None, "Tenant B was allowed to inject a rule into global platform defaults!"


def test_create_rule_forces_caller_tenant_id():
    """create_rule must always set rule.tenant_id to caller tenant_id even if spoofed."""
    tenant_a_id, seller_a_id, _ = create_tenant_hierarchy("ForceTenA")
    tenant_b_id, _, _ = create_tenant_hierarchy("ForceTenB")

    with SessionLocal() as db:
        repo = PricingRepository(db)

        book_a = repo.create_book(
            tenant_a_id,
            PriceBook(name="Book A", scope=PriceBookScope.SELLER, seller_id=seller_a_id),
        )
        db.commit()

        # Caller is Tenant A, but rule has tenant_id = Tenant B
        rule = PriceRule(
            tenant_id=tenant_b_id,
            rule_type=PriceRuleType.PER_ITEM,
            component_type=ComponentType.BASE_PRICE,
            rate=Decimal("45.00"),
        )
        created_rule = repo.create_rule(tenant_a_id, book_a.id, rule)
        db.commit()

        assert created_rule is not None
        assert created_rule.tenant_id == tenant_a_id, "create_rule did not override spoofed tenant_id!"


# ============================================================================
# 4. CROSS-TENANT CALCULATION ENGINE LEAKAGE ATTACKS
# ============================================================================

def test_calculation_engine_strict_tenant_isolation():
    """Rules from Tenant A must NEVER leak into Tenant B's pricing calculation."""
    tenant_a_id, seller_a_id, _ = create_tenant_hierarchy("CalcIsoA")
    tenant_b_id, seller_b_id, _ = create_tenant_hierarchy("CalcIsoB")

    with SessionLocal() as db:
        repo = PricingRepository(db)

        book_a = repo.create_book(
            tenant_a_id,
            PriceBook(
                name="Book A",
                scope=PriceBookScope.SELLER,
                seller_id=seller_a_id,
                status=PriceBookStatus.ACTIVE,
                is_active=True,
            ),
        )
        rule_a = repo.create_rule(
            tenant_a_id,
            book_a.id,
            PriceRule(
                rule_type=PriceRuleType.PER_ITEM,
                component_type=ComponentType.BASE_PRICE,
                rate=Decimal("120.00"),
                status="ACTIVE",
                is_active=True,
            ),
        )

        book_b = repo.create_book(
            tenant_b_id,
            PriceBook(
                name="Book B",
                scope=PriceBookScope.SELLER,
                seller_id=seller_b_id,
                status=PriceBookStatus.ACTIVE,
                is_active=True,
            ),
        )
        rule_b = repo.create_rule(
            tenant_b_id,
            book_b.id,
            PriceRule(
                rule_type=PriceRuleType.PER_ITEM,
                component_type=ComponentType.BASE_PRICE,
                rate=Decimal("40.00"),
                status="ACTIVE",
                is_active=True,
            ),
        )
        db.commit()

        # Calculation query for Tenant B
        calc_rules_b = repo.get_active_rules_for_calculation(
            tenant_id=tenant_b_id,
            seller_id=seller_b_id,
        )
        rule_ids_b = [r.id for r in calc_rules_b]

        assert rule_b.id in rule_ids_b
        assert rule_a.id not in rule_ids_b, "Tenant A's rule leaked into Tenant B's calculation!"


def test_calculation_engine_foreign_seller_id_rejected():
    """Tenant B querying calculation with Tenant A's seller_id must receive 0 tenant rules."""
    tenant_a_id, seller_a_id, _ = create_tenant_hierarchy("ForeignSellerA")
    tenant_b_id, _, _ = create_tenant_hierarchy("ForeignSellerB")

    with SessionLocal() as db:
        repo = PricingRepository(db)

        book_a = repo.create_book(
            tenant_a_id,
            PriceBook(
                name="Book A",
                scope=PriceBookScope.SELLER,
                seller_id=seller_a_id,
                status=PriceBookStatus.ACTIVE,
                is_active=True,
            ),
        )
        rule_a = repo.create_rule(
            tenant_a_id,
            book_a.id,
            PriceRule(
                rule_type=PriceRuleType.PER_ITEM,
                component_type=ComponentType.BASE_PRICE,
                rate=Decimal("88.00"),
                status="ACTIVE",
                is_active=True,
            ),
        )
        db.commit()

        # Attack: Tenant B queries calculation passing seller_a_id
        calc_rules = repo.get_active_rules_for_calculation(
            tenant_id=tenant_b_id,
            seller_id=seller_a_id,
        )
        rule_ids = [r.id for r in calc_rules]
        assert rule_a.id not in rule_ids, "Tenant B leaked Tenant A's rules by querying with seller_a_id!"


def test_calculation_engine_platform_defaults_shared_safely():
    """Global platform defaults (tenant_id=None) are available to both, but cannot be modified."""
    tenant_a_id, seller_a_id, _ = create_tenant_hierarchy("SharePlatA")
    tenant_b_id, seller_b_id, _ = create_tenant_hierarchy("SharePlatB")

    with SessionLocal() as db:
        repo = PricingRepository(db)

        plat_book = PriceBook(
            scope=PriceBookScope.PLATFORM_DEFAULT,
            tenant_id=None,
            name="Global Platform Book",
            status=PriceBookStatus.ACTIVE,
            is_active=True,
            priority=-100,
        )
        db.add(plat_book)
        db.commit()
        db.refresh(plat_book)

        plat_rule = PriceRule(
            tenant_id=None,
            price_book_id=plat_book.id,
            rule_type=PriceRuleType.PER_ITEM,
            component_type=ComponentType.BASE_PRICE,
            rate=Decimal("10.00"),
            status="ACTIVE",
            is_active=True,
            priority=-100,
        )
        db.add(plat_rule)
        db.commit()
        db.refresh(plat_rule)

        # Both tenants receive the global platform default rule
        rules_a = repo.get_active_rules_for_calculation(tenant_id=tenant_a_id, seller_id=seller_a_id)
        rules_b = repo.get_active_rules_for_calculation(tenant_id=tenant_b_id, seller_id=seller_b_id)

        assert plat_rule.id in [r.id for r in rules_a]
        assert plat_rule.id in [r.id for r in rules_b]

        # But neither tenant can mutate the platform default rule
        assert repo.update_rule(tenant_a_id, plat_rule.id, PriceRuleUpdate(rate=Decimal("0.00"))) is None
        assert repo.update_rule(tenant_b_id, plat_rule.id, PriceRuleUpdate(rate=Decimal("0.00"))) is None
        assert repo.delete_rule(tenant_a_id, plat_rule.id) is False
        assert repo.delete_rule(tenant_b_id, plat_rule.id) is False


# ============================================================================
# 5. ADVERSARIAL INJECTION & SPOOFING VULNERABILITY TESTS
# ============================================================================

def test_create_book_tenant_id_spoofing_via_platform_default_scope():
    """Adversarial stress-test: Verify that create_book never allows Tenant A to create

    a price book stamped with Tenant B's tenant_id by setting scope=PLATFORM_DEFAULT.
    """
    tenant_a_id, _, _ = create_tenant_hierarchy("SpoofA")
    tenant_b_id, seller_b_id, _ = create_tenant_hierarchy("SpoofB")

    with SessionLocal() as db:
        repo = PricingRepository(db)

        # Tenant A crafts a book with scope=PLATFORM_DEFAULT and target tenant_id=Tenant B
        malicious_book = PriceBook(
            name="Injected Trojan Book",
            scope=PriceBookScope.PLATFORM_DEFAULT,
            tenant_id=tenant_b_id,
            status=PriceBookStatus.ACTIVE,
            is_active=True,
        )

        # Tenant A calls create_book
        saved_book = repo.create_book(tenant_a_id, malicious_book)
        db.commit()

        # CHALLENGE:
        # If create_book properly enforces multi-tenant isolation, saved_book.tenant_id
        # MUST be tenant_a_id (caller's tenant), and Tenant B must NOT see it.
        # If saved_book.tenant_id == tenant_b_id, Tenant A succeeded in injecting a book into Tenant B!
        assert saved_book.tenant_id == tenant_a_id, (
            f"SECURITY VULNERABILITY: create_book allowed Tenant A ({tenant_a_id}) "
            f"to persist a price book with Tenant B's tenant_id ({saved_book.tenant_id})!"
        )


def test_create_book_cascaded_rules_tenant_id_mismatch():
    """Adversarial stress-test: Verify that cascaded rules attached to a new book

    cannot have their tenant_id spoofed to a victim tenant.
    """
    tenant_a_id, seller_a_id, _ = create_tenant_hierarchy("CascSpoofA")
    tenant_b_id, _, _ = create_tenant_hierarchy("CascSpoofB")

    with SessionLocal() as db:
        repo = PricingRepository(db)

        book_a = PriceBook(
            name="Book A with Trojan Rule",
            scope=PriceBookScope.SELLER,
            seller_id=seller_a_id,
            status=PriceBookStatus.ACTIVE,
            is_active=True,
        )
        trojan_rule = PriceRule(
            tenant_id=tenant_b_id,  # Target Tenant B
            rule_type=PriceRuleType.PER_ITEM,
            component_type=ComponentType.BASE_PRICE,
            rate=Decimal("66.60"),
            status="ACTIVE",
            is_active=True,
        )
        book_a.rules.append(trojan_rule)

        saved_book = repo.create_book(tenant_a_id, book_a)
        db.commit()
        db.refresh(trojan_rule)

        # CHALLENGE:
        # All cascaded rules in book_a MUST belong to tenant_a_id.
        # If trojan_rule.tenant_id == tenant_b_id, Tenant B can read and manipulate Tenant A's rule.
        assert trojan_rule.tenant_id == tenant_a_id, (
            f"SECURITY VULNERABILITY: create_book persisted a cascaded rule with "
            f"victim tenant_id ({trojan_rule.tenant_id}) under Tenant A's book!"
        )
