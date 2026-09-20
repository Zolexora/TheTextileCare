import asyncio
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.models.tenant import Tenant
from app.models.seller import Seller, Branch
from app.models.catalog import Catalog, Category, Service, ServiceItem
from uuid import uuid4

def seed_db():
    db = SessionLocal()
    try:
        # Check if already seeded
        tenant = db.query(Tenant).filter_by(slug="sparkle-tenant").first()
        if not tenant:
            tenant = Tenant(name="Sparkle Cleaners Tenant", slug="sparkle-tenant")
            db.add(tenant)
            db.commit()

        # 2. Seller
        seller = db.query(Seller).filter_by(slug="sparkle").first()
        if not seller:
            seller = Seller(
                tenant_id=tenant.id,
                business_name="Sparkle Cleaners",
                display_name="Sparkle Cleaners",
                slug="sparkle",
                status="PUBLISHED",
                marketplace_status="ACTIVE",
                email="support@sparkle.com",
                phone="555-0100"
            )
            db.add(seller)
            db.commit()

        # 3. Branch
        branch = db.query(Branch).filter_by(code="DT1").first()
        if not branch:
            branch = Branch(
                tenant_id=tenant.id,
                seller_id=seller.id,
                name="Downtown Hub",
                code="DT1",
                status="ACTIVE",
                is_marketplace_visible=True,
                address_line_1="123 Wash Street",
                city="Metropolis",
                state="NY",
                postal_code="10001",
                country="USA"
            )
            db.add(branch)
            db.commit()

        # 4. Catalog
        catalog = db.query(Catalog).filter_by(seller_id=seller.id).first()
        if not catalog:
            catalog = Catalog(
                tenant_id=tenant.id,
                seller_id=seller.id,
                name="Standard Pricing 2024",
                status="ACTIVE"
            )
            db.add(catalog)
            db.commit()

        # 5. Categories
        cat_wf = db.query(Category).filter_by(slug="wash-and-fold").first()
        if not cat_wf:
            cat_wf = Category(tenant_id=tenant.id, catalog_id=catalog.id, name="Wash & Fold", slug="wash-and-fold")
            cat_dc = Category(tenant_id=tenant.id, catalog_id=catalog.id, name="Dry Cleaning", slug="dry-cleaning")
            db.add_all([cat_wf, cat_dc])
            db.commit()

        # 6. Services & Items
        svc_laundry = db.query(Service).filter_by(slug="regular-laundry").first()
        if not svc_laundry:
            svc_laundry = Service(
                tenant_id=tenant.id,
                catalog_id=catalog.id,
                category_id=cat_wf.id,
                name="Regular Laundry",
                slug="regular-laundry",
                service_type="LAUNDRY",
                status="ACTIVE",
            )
            svc_shirts = Service(
                tenant_id=tenant.id,
                catalog_id=catalog.id,
                category_id=cat_dc.id,
                name="Dress Shirts",
                slug="dress-shirts",
                service_type="DRY_CLEAN",
                status="ACTIVE",
            )
            db.add_all([svc_laundry, svc_shirts])
            db.commit()

            item1 = ServiceItem(tenant_id=tenant.id, service_id=svc_laundry.id, name="Per KG", unit_type="KG", status="ACTIVE")
            item2 = ServiceItem(tenant_id=tenant.id, service_id=svc_shirts.id, name="Standard Shirt", unit_type="ITEM", status="ACTIVE")
            db.add_all([item1, item2])
            db.commit()

        print("Database seeded successfully!")
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
