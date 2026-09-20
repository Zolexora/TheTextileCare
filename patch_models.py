import os
import re

# 1. Update catalog.py
with open('backend/app/models/catalog.py', 'r') as f:
    content = f.read()

models_code = """
class ServiceConfigurationVersion(Base):
    __tablename__ = 'service_configuration_versions'
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    service_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('services.id', ondelete='CASCADE'), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    configuration_snapshot: Mapped[dict] = mapped_column(sqlalchemy.JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class PricePolicyVersion(Base):
    __tablename__ = 'price_policy_versions'
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    service_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('services.id', ondelete='CASCADE'), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    recalculation_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    price_change_policy: Mapped[str] = mapped_column(String(50), nullable=False, default='STRICT')
    price_rejection_policy: Mapped[str] = mapped_column(String(50), nullable=False, default='CANCEL') 
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
"""
if 'PricePolicyVersion' not in content:
    content = content.replace("from app.db import Base", "from app.db import Base\nimport sqlalchemy")
    content += "\n" + models_code
    with open('backend/app/models/catalog.py', 'w') as f:
        f.write(content)

# 2. Update order.py
with open('backend/app/models/order.py', 'r') as f:
    content = f.read()

# Add to Order
if 'price_locked_at' not in content:
    order_patch = """
    price_locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)"""
    content = content.replace("cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)", "cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)\n" + order_patch)

# Add to OrderItem
if 'price_policy_version_id' not in content:
    item_patch = """
    service_configuration_version_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('service_configuration_versions.id', ondelete='SET NULL'), nullable=True)
    price_policy_version_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('price_policy_versions.id', ondelete='SET NULL'), nullable=True)
    applicable_rate: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    price_policy_snapshot: Mapped[dict] = mapped_column(sqlalchemy.JSON, nullable=True)"""
    
    content = content.replace("from app.db import Base", "from app.db import Base\nimport sqlalchemy")
    content = content.replace("unit_type: Mapped[str] = mapped_column(String(50), nullable=False, default=\"ITEM\")", "unit_type: Mapped[str] = mapped_column(String(50), nullable=False, default=\"ITEM\")\n" + item_patch)

    with open('backend/app/models/order.py', 'w') as f:
        f.write(content)
