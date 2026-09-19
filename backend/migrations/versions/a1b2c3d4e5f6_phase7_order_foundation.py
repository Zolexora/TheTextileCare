"""phase7_order_foundation

Revision ID: a1b2c3d4e5f6
Revises: 112e2205a754
Create Date: 2026-09-19 11:00:00.000000

Phase 7 — Order Foundation.

Creates:
  - order_number_seq  (PostgreSQL SEQUENCE for concurrency-safe order numbers)
  - orders
  - order_items
  - order_item_addons
  - order_status_history
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '112e2205a754'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------------------------------------------------------------
    # Sequence for concurrency-safe order number generation
    # ---------------------------------------------------------------
    op.execute("CREATE SEQUENCE IF NOT EXISTS order_number_seq START 1 INCREMENT 1")

    # ---------------------------------------------------------------
    # orders
    # ---------------------------------------------------------------
    op.create_table(
        'orders',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('seller_id', sa.Uuid(), nullable=False),
        sa.Column('branch_id', sa.Uuid(), nullable=False),
        sa.Column('customer_id', sa.Uuid(), nullable=False),
        sa.Column('order_number', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('subtotal', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('discount_total', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('surcharge_total', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('tax_total', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('grand_total', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('pricing_snapshot', sa.JSON(), nullable=False),
        sa.Column('catalog_snapshot', sa.JSON(), nullable=False),
        sa.Column('customer_snapshot', sa.JSON(), nullable=False),
        sa.Column('customer_address_snapshot', sa.JSON(), nullable=True),
        sa.Column('idempotency_key', sa.String(length=255), nullable=True),
        sa.Column('placed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancellation_reason', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('updated_by', sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(['branch_id'], ['seller_branches.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['seller_id'], ['sellers.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('order_number', name='uq_order_order_number'),
        sa.UniqueConstraint('customer_id', 'idempotency_key', name='uq_order_customer_idempotency'),
    )
    op.create_index('ix_orders_customer_id_created_at', 'orders', ['customer_id', 'created_at'])
    op.create_index('ix_orders_seller_id_created_at', 'orders', ['seller_id', 'created_at'])
    op.create_index('ix_orders_branch_id_created_at', 'orders', ['branch_id', 'created_at'])
    op.create_index('ix_orders_tenant_id_status', 'orders', ['tenant_id', 'status'])
    op.create_index('ix_orders_status_created_at', 'orders', ['status', 'created_at'])
    op.create_index('ix_orders_order_number', 'orders', ['order_number'])

    # ---------------------------------------------------------------
    # order_items
    # ---------------------------------------------------------------
    op.create_table(
        'order_items',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('order_id', sa.Uuid(), nullable=False),
        sa.Column('service_id', sa.Uuid(), nullable=True),
        sa.Column('service_item_id', sa.Uuid(), nullable=True),
        sa.Column('service_name_snapshot', sa.String(length=255), nullable=False),
        sa.Column('service_item_name_snapshot', sa.String(length=255), nullable=True),
        sa.Column('unit_type', sa.String(length=50), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('subtotal', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('discount_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('surcharge_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('tax_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('total_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('pricing_snapshot', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['service_id'], ['services.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['service_item_id'], ['service_items.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_order_items_order_id', 'order_items', ['order_id'])
    op.create_index('ix_order_items_service_id', 'order_items', ['service_id'])

    # ---------------------------------------------------------------
    # order_item_addons
    # ---------------------------------------------------------------
    op.create_table(
        'order_item_addons',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('order_item_id', sa.Uuid(), nullable=False),
        sa.Column('service_addon_id', sa.Uuid(), nullable=True),
        sa.Column('addon_name_snapshot', sa.String(length=255), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('subtotal', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('discount_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('surcharge_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('tax_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('total_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('pricing_snapshot', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['order_item_id'], ['order_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['service_addon_id'], ['service_addons.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_order_item_addons_order_item_id', 'order_item_addons', ['order_item_id'])

    # ---------------------------------------------------------------
    # order_status_history
    # ---------------------------------------------------------------
    op.create_table(
        'order_status_history',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('order_id', sa.Uuid(), nullable=False),
        sa.Column('from_status', sa.String(length=50), nullable=True),
        sa.Column('to_status', sa.String(length=50), nullable=False),
        sa.Column('reason', sa.String(length=1000), nullable=True),
        sa.Column('actor_user_id', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_order_status_history_order_id_created_at',
        'order_status_history',
        ['order_id', 'created_at'],
    )


def downgrade() -> None:
    op.drop_index('ix_order_status_history_order_id_created_at', table_name='order_status_history')
    op.drop_table('order_status_history')
    op.drop_index('ix_order_item_addons_order_item_id', table_name='order_item_addons')
    op.drop_table('order_item_addons')
    op.drop_index('ix_order_items_service_id', table_name='order_items')
    op.drop_index('ix_order_items_order_id', table_name='order_items')
    op.drop_table('order_items')
    op.drop_index('ix_orders_order_number', table_name='orders')
    op.drop_index('ix_orders_status_created_at', table_name='orders')
    op.drop_index('ix_orders_tenant_id_status', table_name='orders')
    op.drop_index('ix_orders_branch_id_created_at', table_name='orders')
    op.drop_index('ix_orders_seller_id_created_at', table_name='orders')
    op.drop_index('ix_orders_customer_id_created_at', table_name='orders')
    op.drop_table('orders')
    op.execute("DROP SEQUENCE IF EXISTS order_number_seq")
