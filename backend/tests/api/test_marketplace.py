from __future__ import annotations

from fastapi.testclient import TestClient
from decimal import Decimal

from app.main import app
from app.db import SessionLocal
from tests.e2e.conftest import setup_tenant_and_actor
from tests.conftest import create_test_user, make_auth_headers

client = TestClient(app)

def test_marketplace_seller_discovery():
    # Set up a tenant and a seller
    setup_data = setup_tenant_and_actor("Test Marketplace Tenant", "admin@marketplace.com")
    seller = setup_data["seller"]
    
    # By default, seller is DRAFT. Ensure it doesn't show up.
    resp = client.get("/api/v1/marketplace/sellers")
    assert resp.status_code == 200
    assert len(resp.json()) == 0
    
    # Set to PUBLISHED
    with SessionLocal() as db:
        from app.models.seller import Seller
        db_seller = db.query(Seller).filter(Seller.id == seller.id).first()
        db_seller.marketplace_status = 'PUBLISHED'
        db.commit()
        
    resp = client.get("/api/v1/marketplace/sellers")
    assert resp.status_code == 200
    sellers = resp.json()
    assert len(sellers) == 1
    assert sellers[0]["id"] == str(seller.id)

def test_marketplace_pricing_preview():
    # Setup full phase 4+5 infra
    setup_data = setup_tenant_and_actor("Preview Tenant", "admin@preview.com")
    tenant = setup_data["tenant"]
    seller = setup_data["seller"]
    branch = setup_data["downtown_branch"]
    catalog = setup_data["catalog"]
    services = setup_data["services"]
    items = setup_data["items"]
    
    # Publish seller
    with SessionLocal() as db:
        from app.models.seller import Seller
        db_seller = db.query(Seller).filter(Seller.id == seller.id).first()
        db_seller.marketplace_status = 'PUBLISHED'
        db.commit()

    # Create a pricing rule so pricing exists
    with SessionLocal() as db:
        from app.models.pricing import PriceBook, PriceRule, PriceBookScope, PriceBookStatus, PriceRuleType, ComponentType, RateType
        book = PriceBook(
            tenant_id=tenant.id,
            seller_id=seller.id,
            name="Default Public Pricing",
            scope=PriceBookScope.SELLER,
            status=PriceBookStatus.ACTIVE,
            priority=10
        )
        db.add(book)
        db.flush()
        
        rule = PriceRule(
            tenant_id=tenant.id,
            price_book_id=book.id,
            service_id=services["dry_cleaning"].id,
            service_item_id=items["suit"].id,
            rule_type=PriceRuleType.PER_ITEM,
            component_type=ComponentType.BASE_PRICE,
            rate_type=RateType.FLAT,
            rate=Decimal("150.00"),
            status="ACTIVE"
        )
        db.add(rule)
        db.commit()
    
    # Now customer tries to preview price
    resp = client.post(
        "/api/v1/marketplace/pricing/preview",
        json={
            "seller_id": str(seller.id),
            "branch_id": str(branch.id),
            "items": [
                {
                    "service_id": str(services["dry_cleaning"].id),
                    "service_item_id": str(items["suit"].id),
                    "quantity": "2"
                }
            ]
        }
    )
    
    assert resp.status_code == 200
    data = resp.json()
    assert data["subtotal"] == "300.00"
    assert data["grand_total"] == "300.00"
    assert len(data["items"]) == 1
    assert data["items"][0]["quantity"] == "2"

def test_marketplace_pricing_preview_invalid_entity():
    setup_data = setup_tenant_and_actor("Invalid Preview Tenant", "admin@invalidpreview.com")
    seller = setup_data["seller"]
    branch = setup_data["downtown_branch"]
    services = setup_data["services"]
    items = setup_data["items"]
    
    # Do NOT publish seller
    
    resp = client.post(
        "/api/v1/marketplace/pricing/preview",
        json={
            "seller_id": str(seller.id),
            "branch_id": str(branch.id),
            "items": [
                {
                    "service_id": str(services["dry_cleaning"].id),
                    "service_item_id": str(items["suit"].id),
                    "quantity": "2"
                }
            ]
        }
    )
    # Should be 404 because seller is unpublished
    assert resp.status_code == 404
