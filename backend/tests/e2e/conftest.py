from __future__ import annotations

import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import pytest
from fastapi.testclient import TestClient

import app.models  # Ensures all models (tenants, users, sellers, catalogs, pricing) are registered
from app.db import Base, SessionLocal, engine
from app.main import app
from app.models.catalog import Catalog, Category, Service, ServiceItem, ServiceAddon
from app.models.membership import Membership
from app.models.seller import Seller, Branch
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.memberships import MembershipRepository
from app.repositories.tenants import TenantRepository
from app.repositories.users import UserRepository
from app.services.roles import RoleService


def _deduplicate_table_indexes():
    for table in Base.metadata.tables.values():
        seen_names = set()
        unique_indexes = set()
        for idx in list(table.indexes):
            if idx.name not in seen_names:
                seen_names.add(idx.name)
                unique_indexes.add(idx)
        table.indexes.clear()
        table.indexes.update(unique_indexes)


@pytest.fixture(autouse=True)
def reset_database():
    """Reset database tables and seed defaults before each test."""
    _deduplicate_table_indexes()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        RoleService(db).seed_defaults()
    yield


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def make_auth_headers(user: User, tenant: Tenant | None = None) -> dict[str, str]:
    headers = {"X-User-Id": str(user.id)}
    if tenant:
        headers["X-Tenant-Id"] = str(tenant.id)
    return headers


def create_test_user(email: str, name: str | None = None, auth_user_id: str | None = None) -> User:
    with SessionLocal() as db:
        repo = UserRepository(db)
        return repo.create_or_get(
            email=email,
            auth_user_id=auth_user_id or f"auth-{email}",
            name=name or email.split("@")[0],
        )


def create_test_tenant(name: str, slug: str | None = None) -> Tenant:
    with SessionLocal() as db:
        repo = TenantRepository(db)
        actual_slug = slug or name.lower().replace(" ", "-") + f"-{uuid.uuid4().hex[:6]}"
        return repo.create(name=name, slug=actual_slug)


def create_test_membership(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    role_name: str,
    status: str = "ACTIVE",
) -> Membership:
    with SessionLocal() as db:
        repo = MembershipRepository(db)
        return repo.create(
            tenant_id=tenant_id,
            user_id=user_id,
            role_name=role_name,
            status=status,
        )


def create_test_seller(tenant_id: uuid.UUID, business_name: str = "Premier Care Dry Cleaners") -> Seller:
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


def create_test_branch(
    tenant_id: uuid.UUID,
    seller_id: uuid.UUID,
    name: str = "Downtown Express",
    code: str | None = None,
) -> Branch:
    with SessionLocal() as db:
        branch = Branch(
            tenant_id=tenant_id,
            seller_id=seller_id,
            name=name,
            code=code or f"BR-{uuid.uuid4().hex[:6]}".upper(),
            status="ACTIVE",
        )
        db.add(branch)
        db.commit()
        db.refresh(branch)
        return branch


def create_test_catalog_hierarchy(tenant_id: uuid.UUID, seller_id: uuid.UUID) -> dict[str, Any]:
    """Creates standard catalog entities: Category, Services, Service Items, and Addons."""
    with SessionLocal() as db:
        catalog = Catalog(
            tenant_id=tenant_id,
            seller_id=seller_id,
            name="Primary Service Catalog",
            status="ACTIVE",
        )
        db.add(catalog)
        db.flush()

        category = Category(
            tenant_id=tenant_id,
            catalog_id=catalog.id,
            name="Garment Care",
            slug=f"garment-care-{uuid.uuid4().hex[:6]}",
            status="ACTIVE",
        )
        db.add(category)
        db.flush()

        # Service 1: Dry Cleaning (Per Item)
        dry_cleaning = Service(
            tenant_id=tenant_id,
            catalog_id=catalog.id,
            category_id=category.id,
            name="Dry Cleaning",
            slug=f"dry-cleaning-{uuid.uuid4().hex[:6]}",
            service_type="SERVICE",
            status="ACTIVE",
        )
        db.add(dry_cleaning)
        db.flush()

        suit_item = ServiceItem(
            tenant_id=tenant_id,
            service_id=dry_cleaning.id,
            name="2-Piece Suit",
            code=f"SUIT-{uuid.uuid4().hex[:4]}".upper(),
            unit_type="ITEM",
            status="ACTIVE",
        )
        shirt_item = ServiceItem(
            tenant_id=tenant_id,
            service_id=dry_cleaning.id,
            name="Silk Shirt",
            code=f"SHIRT-{uuid.uuid4().hex[:4]}".upper(),
            unit_type="ITEM",
            status="ACTIVE",
        )
        db.add_all([suit_item, shirt_item])

        delicate_addon = ServiceAddon(
            tenant_id=tenant_id,
            service_id=dry_cleaning.id,
            name="Delicate Fabric Treatment",
            code=f"DELICATE-{uuid.uuid4().hex[:4]}".upper(),
            status="ACTIVE",
        )
        stain_addon = ServiceAddon(
            tenant_id=tenant_id,
            service_id=dry_cleaning.id,
            name="Spot Stain Removal",
            code=f"STAIN-{uuid.uuid4().hex[:4]}".upper(),
            status="ACTIVE",
        )
        db.add_all([delicate_addon, stain_addon])

        # Service 2: Wash & Fold (Per Weight)
        wash_fold = Service(
            tenant_id=tenant_id,
            catalog_id=catalog.id,
            category_id=category.id,
            name="Wash & Fold Laundry",
            slug=f"wash-fold-{uuid.uuid4().hex[:6]}",
            service_type="SERVICE",
            status="ACTIVE",
        )
        db.add(wash_fold)
        db.flush()

        laundry_bag_item = ServiceItem(
            tenant_id=tenant_id,
            service_id=wash_fold.id,
            name="Laundry by Weight",
            code=f"WEIGHT-{uuid.uuid4().hex[:4]}".upper(),
            unit_type="KG",
            status="ACTIVE",
        )
        db.add(laundry_bag_item)

        express_addon = ServiceAddon(
            tenant_id=tenant_id,
            service_id=wash_fold.id,
            name="Same-Day Express",
            code=f"EXPRESS-{uuid.uuid4().hex[:4]}".upper(),
            status="ACTIVE",
        )
        db.add(express_addon)

        # Service 3: Upholstery / Drapery (Per Unit / Linear Foot / M2)
        upholstery = Service(
            tenant_id=tenant_id,
            catalog_id=catalog.id,
            category_id=category.id,
            name="Household Drapery & Upholstery",
            slug=f"upholstery-{uuid.uuid4().hex[:6]}",
            service_type="SERVICE",
            status="ACTIVE",
        )
        db.add(upholstery)
        db.flush()

        curtain_item = ServiceItem(
            tenant_id=tenant_id,
            service_id=upholstery.id,
            name="Curtains per Sq Meter",
            code=f"CURTAIN-{uuid.uuid4().hex[:4]}".upper(),
            unit_type="M2",
            status="ACTIVE",
        )
        db.add(curtain_item)

        db.commit()

        return {
            "catalog": catalog,
            "category": category,
            "services": {
                "dry_cleaning": dry_cleaning,
                "wash_fold": wash_fold,
                "upholstery": upholstery,
            },
            "items": {
                "suit": suit_item,
                "shirt": shirt_item,
                "laundry_bag": laundry_bag_item,
                "curtain": curtain_item,
            },
            "addons": {
                "delicate": delicate_addon,
                "stain": stain_addon,
                "express": express_addon,
            },
        }


def setup_tenant_and_actor(
    tenant_name: str = "TTC Laundry Corp",
    user_email: str = "admin@ttclaundry.com",
    role: str = "TENANT_ADMIN",
) -> dict[str, Any]:
    """Helper to set up a tenant, admin user, seller, branches, and catalog hierarchy."""
    tenant = create_test_tenant(tenant_name)
    user = create_test_user(user_email)
    create_test_membership(tenant.id, user.id, role)
    headers = make_auth_headers(user, tenant)
    seller = create_test_seller(tenant.id)
    downtown_branch = create_test_branch(tenant.id, seller.id, name="Downtown Branch", code="DT-01")
    suburb_branch = create_test_branch(tenant.id, seller.id, name="Suburb Branch", code="SUB-02")
    catalog_data = create_test_catalog_hierarchy(tenant.id, seller.id)

    return {
        "tenant": tenant,
        "user": user,
        "headers": headers,
        "seller": seller,
        "downtown_branch": downtown_branch,
        "suburb_branch": suburb_branch,
        **catalog_data,
    }


def assert_calculation_invariant(result: dict[str, Any]) -> None:
    """Verifies the core financial breakdown invariant to exact 2-decimal precision:
    grand_total == subtotal + total_surcharges - total_discounts + total_tax
    """
    subtotal = Decimal(str(result["subtotal"]))
    surcharges = Decimal(str(result.get("total_surcharges", "0.00")))
    discounts = Decimal(str(result.get("total_discounts", "0.00")))
    tax = Decimal(str(result.get("total_tax", "0.00")))
    grand_total = Decimal(str(result["grand_total"]))
    taxable_amount = Decimal(str(result.get("taxable_amount", subtotal + surcharges - discounts)))

    expected_taxable = (subtotal + surcharges - discounts).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    assert taxable_amount == expected_taxable, (
        f"Taxable amount mismatch: observed {taxable_amount}, expected {expected_taxable}"
    )

    expected_grand_total = (subtotal + surcharges - discounts + tax).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    assert grand_total == expected_grand_total, (
        f"Calculation invariant violated: grand_total {grand_total} != "
        f"subtotal {subtotal} + surcharges {surcharges} - discounts {discounts} + tax {tax} = {expected_grand_total}"
    )
