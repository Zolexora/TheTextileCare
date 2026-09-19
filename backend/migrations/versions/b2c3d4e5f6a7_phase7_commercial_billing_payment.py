"""phase7_commercial_billing_payment

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-19 18:00:00.000000

Phase 7 — Commercial Billing, Payment Timing, Settlement & Seller Restrictions Foundation.

Creates:
  - orders.reselected_from_order_id (column alteration with FK to orders.id ondelete SET NULL)
  - order_pickups
  - seller_commercial_configs
  - seller_billing_invoices
  - seller_settlements
  - payments
  - refunds
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # 1. Alter orders: add reselected_from_order_id
    # -----------------------------------------------------------------------
    op.add_column(
        'orders',
        sa.Column('reselected_from_order_id', sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        'fk_orders_reselected_from_order_id_orders',
        'orders',
        'orders',
        ['reselected_from_order_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index(
        'ix_orders_reselected_from_order_id',
        'orders',
        ['reselected_from_order_id'],
        unique=False,
    )

    # -----------------------------------------------------------------------
    # 2. Table: order_pickups
    # -----------------------------------------------------------------------
    op.create_table(
        'order_pickups',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('seller_id', sa.Uuid(), nullable=False),
        sa.Column('order_id', sa.Uuid(), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='SCHEDULED', nullable=False),
        sa.Column('actual_pickup_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('details_submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.String(length=1000), nullable=True),
        sa.Column('actual_details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(
            "status IN ('SCHEDULED', 'DETAILS_SUBMITTED', 'APPROVED', 'REJECTED', 'COMPLETED')",
            name='ck_order_pickups_status',
        ),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['seller_id'], ['sellers.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('order_id', name='uq_order_pickups_order_id'),
    )
    op.create_index('ix_order_pickups_order_id', 'order_pickups', ['order_id'], unique=True)
    op.create_index('ix_order_pickups_tenant_id', 'order_pickups', ['tenant_id'], unique=False)
    op.create_index('ix_order_pickups_seller_id', 'order_pickups', ['seller_id'], unique=False)
    op.create_index('ix_order_pickups_status', 'order_pickups', ['status'], unique=False)
    op.create_index('ix_order_pickups_seller_status', 'order_pickups', ['seller_id', 'status'], unique=False)

    # -----------------------------------------------------------------------
    # 3. Table: seller_commercial_configs
    # -----------------------------------------------------------------------
    op.create_table(
        'seller_commercial_configs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('seller_id', sa.Uuid(), nullable=False),
        sa.Column('commercial_model', sa.String(length=50), server_default='COMMISSION', nullable=False),
        sa.Column('commission_rate_percent', sa.Numeric(precision=5, scale=2), server_default='10.00', nullable=False),
        sa.Column('subscription_fee', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('marketplace_gateway', sa.String(length=50), server_default='TTC_GATEWAY', nullable=False),
        sa.Column('white_label_gateway', sa.String(length=50), server_default='SELLER_GATEWAY', nullable=False),
        sa.Column('payment_required_before_pickup', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('outstanding_receivable_allowed', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('payment_deadline_days', sa.Integer(), server_default='1', nullable=False),
        sa.Column('restriction_level', sa.String(length=50), server_default='NONE', nullable=False),
        sa.Column('overdue_grace_days', sa.Integer(), server_default='7', nullable=False),
        sa.Column('daily_penalty_rate', sa.Numeric(precision=6, scale=4), server_default='0.0010', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("commercial_model IN ('COMMISSION', 'SUBSCRIPTION')", name='ck_seller_commercial_model'),
        sa.CheckConstraint("marketplace_gateway IN ('TTC_GATEWAY', 'SELLER_GATEWAY')", name='ck_seller_marketplace_gateway'),
        sa.CheckConstraint("white_label_gateway IN ('TTC_GATEWAY', 'SELLER_GATEWAY')", name='ck_seller_whitelabel_gateway'),
        sa.CheckConstraint(
            "restriction_level IN ('NONE', 'WARNING', 'MARKETPLACE_RESTRICTED', 'WHITE_LABEL_RESTRICTED', 'FULL_SUSPENSION')",
            name='ck_seller_restriction_level',
        ),
        sa.CheckConstraint("commission_rate_percent >= 0 AND commission_rate_percent <= 100", name='ck_seller_commission_rate'),
        sa.CheckConstraint("subscription_fee >= 0", name='ck_seller_subscription_fee'),
        sa.CheckConstraint("daily_penalty_rate >= 0", name='ck_seller_penalty_rate'),
        sa.CheckConstraint("overdue_grace_days >= 0", name='ck_seller_grace_days'),
        sa.CheckConstraint("payment_deadline_days >= 0", name='ck_seller_deadline_days'),
        sa.ForeignKeyConstraint(['seller_id'], ['sellers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('seller_id', name='uq_seller_commercial_configs_seller_id'),
    )
    op.create_index('ix_seller_commercial_configs_seller_id', 'seller_commercial_configs', ['seller_id'], unique=True)
    op.create_index('ix_seller_commercial_configs_tenant_id', 'seller_commercial_configs', ['tenant_id'], unique=False)
    op.create_index('ix_seller_commercial_configs_restriction_level', 'seller_commercial_configs', ['restriction_level'], unique=False)

    # -----------------------------------------------------------------------
    # 4. Table: seller_billing_invoices
    # -----------------------------------------------------------------------
    op.create_table(
        'seller_billing_invoices',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('seller_id', sa.Uuid(), nullable=False),
        sa.Column('invoice_month', sa.String(length=7), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='PENDING', nullable=False),
        sa.Column('currency', sa.String(length=3), server_default='USD', nullable=False),
        sa.Column('subtotal', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('tax_total', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('penalty_total', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('total_amount', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("status IN ('PENDING', 'PAID', 'OVERDUE', 'CANCELLED')", name='ck_billing_invoices_status'),
        sa.CheckConstraint("subtotal >= 0", name='ck_billing_invoices_subtotal_nonneg'),
        sa.CheckConstraint("tax_total >= 0", name='ck_billing_invoices_tax_nonneg'),
        sa.CheckConstraint("penalty_total >= 0", name='ck_billing_invoices_penalty_nonneg'),
        sa.CheckConstraint("total_amount >= 0", name='ck_billing_invoices_total_nonneg'),
        sa.ForeignKeyConstraint(['seller_id'], ['sellers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('seller_id', 'invoice_month', name='uq_seller_billing_invoices_seller_month'),
    )
    op.create_index('ix_seller_billing_invoices_seller_id', 'seller_billing_invoices', ['seller_id'], unique=False)
    op.create_index('ix_seller_billing_invoices_tenant_id', 'seller_billing_invoices', ['tenant_id'], unique=False)
    op.create_index('ix_seller_billing_invoices_status', 'seller_billing_invoices', ['status'], unique=False)
    op.create_index('ix_seller_billing_invoices_due_date', 'seller_billing_invoices', ['due_date'], unique=False)
    op.create_index('ix_seller_billing_invoices_seller_status', 'seller_billing_invoices', ['seller_id', 'status'], unique=False)

    # -----------------------------------------------------------------------
    # 5. Table: seller_settlements
    # -----------------------------------------------------------------------
    op.create_table(
        'seller_settlements',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('seller_id', sa.Uuid(), nullable=False),
        sa.Column('gateway_type', sa.String(length=50), server_default='TTC_GATEWAY', nullable=False),
        sa.Column('status', sa.String(length=50), server_default='SCHEDULED', nullable=False),
        sa.Column('currency', sa.String(length=3), server_default='USD', nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('scheduled_for', sa.Date(), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reference_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("gateway_type IN ('TTC_GATEWAY', 'SELLER_GATEWAY')", name='ck_settlements_gateway_type'),
        sa.CheckConstraint("status IN ('SCHEDULED', 'PROCESSING', 'SETTLED', 'FAILED', 'PENDING')", name='ck_settlements_status'),
        sa.CheckConstraint("amount >= 0", name='ck_settlements_amount_nonneg'),
        sa.ForeignKeyConstraint(['seller_id'], ['sellers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('reference_id', name='uq_seller_settlements_reference_id'),
    )
    op.create_index('ix_seller_settlements_seller_id', 'seller_settlements', ['seller_id'], unique=False)
    op.create_index('ix_seller_settlements_tenant_id', 'seller_settlements', ['tenant_id'], unique=False)
    op.create_index('ix_seller_settlements_status', 'seller_settlements', ['status'], unique=False)
    op.create_index('ix_seller_settlements_scheduled_for', 'seller_settlements', ['scheduled_for'], unique=False)
    op.create_index('ix_seller_settlements_seller_scheduled', 'seller_settlements', ['seller_id', 'scheduled_for'], unique=False)
    op.create_index('ix_seller_settlements_status_scheduled', 'seller_settlements', ['status', 'scheduled_for'], unique=False)

    # -----------------------------------------------------------------------
    # 6. Table: payments
    # -----------------------------------------------------------------------
    op.create_table(
        'payments',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('order_id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('seller_id', sa.Uuid(), nullable=False),
        sa.Column('customer_id', sa.Uuid(), nullable=False),
        sa.Column('gateway_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='PENDING', nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('gateway_fee', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('gateway_tax', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('ttc_commission', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('ttc_commission_tax', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('refunded_amount', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('retained_amount', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('settled', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('settlement_id', sa.Uuid(), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('gateway_transaction_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("gateway_type IN ('TTC_GATEWAY', 'SELLER_GATEWAY')", name='ck_payments_gateway_type'),
        sa.CheckConstraint(
            "status IN ('PENDING', 'SUCCEEDED', 'FAILED', 'OUTSTANDING', 'REFUNDED', 'PARTIALLY_REFUNDED')",
            name='ck_payments_status',
        ),
        sa.CheckConstraint("amount >= 0", name='ck_payments_amount_nonneg'),
        sa.CheckConstraint("gateway_fee >= 0", name='ck_payments_gateway_fee_nonneg'),
        sa.CheckConstraint("gateway_tax >= 0", name='ck_payments_gateway_tax_nonneg'),
        sa.CheckConstraint("ttc_commission >= 0", name='ck_payments_ttc_commission_nonneg'),
        sa.CheckConstraint("ttc_commission_tax >= 0", name='ck_payments_ttc_commission_tax_nonneg'),
        sa.CheckConstraint("refunded_amount >= 0 AND refunded_amount <= amount", name='ck_payments_refunded_range'),
        sa.CheckConstraint("retained_amount >= 0 AND retained_amount <= amount", name='ck_payments_retained_range'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['seller_id'], ['sellers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['settlement_id'], ['seller_settlements.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('order_id', name='uq_payments_order_id'),
    )
    op.create_index('ix_payments_order_id', 'payments', ['order_id'], unique=True)
    op.create_index('ix_payments_tenant_id', 'payments', ['tenant_id'], unique=False)
    op.create_index('ix_payments_seller_id', 'payments', ['seller_id'], unique=False)
    op.create_index('ix_payments_customer_id', 'payments', ['customer_id'], unique=False)
    op.create_index('ix_payments_status', 'payments', ['status'], unique=False)
    op.create_index('ix_payments_settlement_id', 'payments', ['settlement_id'], unique=False)
    op.create_index('ix_payments_settled_paid_at', 'payments', ['settled', 'paid_at'], unique=False)
    op.create_index('ix_payments_seller_settled', 'payments', ['seller_id', 'settled'], unique=False)
    op.create_index('ix_payments_due_date', 'payments', ['due_date'], unique=False)

    # -----------------------------------------------------------------------
    # 7. Table: refunds
    # -----------------------------------------------------------------------
    op.create_table(
        'refunds',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('payment_id', sa.Uuid(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('reason', sa.String(length=500), nullable=True),
        sa.Column('commission_deduction', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('gateway_fee_reversed', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('gateway_tax_reversed', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('gateway_refund_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('amount > 0', name='ck_refunds_amount_positive'),
        sa.CheckConstraint('commission_deduction >= 0', name='ck_refunds_commission_deduction_nonneg'),
        sa.CheckConstraint('gateway_fee_reversed >= 0', name='ck_refunds_gateway_fee_reversed_nonneg'),
        sa.CheckConstraint('gateway_tax_reversed >= 0', name='ck_refunds_gateway_tax_reversed_nonneg'),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_refunds_payment_id', 'refunds', ['payment_id'], unique=False)
    op.create_index('ix_refunds_tenant_id', 'refunds', ['tenant_id'], unique=False)
    op.create_index('ix_refunds_created_at', 'refunds', ['created_at'], unique=False)


def downgrade() -> None:
    # 7. Drop refunds
    op.drop_index('ix_refunds_created_at', table_name='refunds')
    op.drop_index('ix_refunds_tenant_id', table_name='refunds')
    op.drop_index('ix_refunds_payment_id', table_name='refunds')
    op.drop_table('refunds')

    # 6. Drop payments
    op.drop_index('ix_payments_due_date', table_name='payments')
    op.drop_index('ix_payments_seller_settled', table_name='payments')
    op.drop_index('ix_payments_settled_paid_at', table_name='payments')
    op.drop_index('ix_payments_settlement_id', table_name='payments')
    op.drop_index('ix_payments_status', table_name='payments')
    op.drop_index('ix_payments_customer_id', table_name='payments')
    op.drop_index('ix_payments_seller_id', table_name='payments')
    op.drop_index('ix_payments_tenant_id', table_name='payments')
    op.drop_index('ix_payments_order_id', table_name='payments')
    op.drop_table('payments')

    # 5. Drop seller_settlements
    op.drop_index('ix_seller_settlements_status_scheduled', table_name='seller_settlements')
    op.drop_index('ix_seller_settlements_seller_scheduled', table_name='seller_settlements')
    op.drop_index('ix_seller_settlements_scheduled_for', table_name='seller_settlements')
    op.drop_index('ix_seller_settlements_status', table_name='seller_settlements')
    op.drop_index('ix_seller_settlements_tenant_id', table_name='seller_settlements')
    op.drop_index('ix_seller_settlements_seller_id', table_name='seller_settlements')
    op.drop_table('seller_settlements')

    # 4. Drop seller_billing_invoices
    op.drop_index('ix_seller_billing_invoices_seller_status', table_name='seller_billing_invoices')
    op.drop_index('ix_seller_billing_invoices_due_date', table_name='seller_billing_invoices')
    op.drop_index('ix_seller_billing_invoices_status', table_name='seller_billing_invoices')
    op.drop_index('ix_seller_billing_invoices_tenant_id', table_name='seller_billing_invoices')
    op.drop_index('ix_seller_billing_invoices_seller_id', table_name='seller_billing_invoices')
    op.drop_table('seller_billing_invoices')

    # 3. Drop seller_commercial_configs
    op.drop_index('ix_seller_commercial_configs_restriction_level', table_name='seller_commercial_configs')
    op.drop_index('ix_seller_commercial_configs_tenant_id', table_name='seller_commercial_configs')
    op.drop_index('ix_seller_commercial_configs_seller_id', table_name='seller_commercial_configs')
    op.drop_table('seller_commercial_configs')

    # 2. Drop order_pickups
    op.drop_index('ix_order_pickups_seller_status', table_name='order_pickups')
    op.drop_index('ix_order_pickups_status', table_name='order_pickups')
    op.drop_index('ix_order_pickups_seller_id', table_name='order_pickups')
    op.drop_index('ix_order_pickups_tenant_id', table_name='order_pickups')
    op.drop_index('ix_order_pickups_order_id', table_name='order_pickups')
    op.drop_table('order_pickups')

    # 1. Revert orders alteration
    op.drop_index('ix_orders_reselected_from_order_id', table_name='orders')
    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE orders DROP CONSTRAINT IF EXISTS fk_orders_reselected_from_order_id_orders"))
    conn.execute(sa.text("ALTER TABLE orders DROP CONSTRAINT IF EXISTS orders_reselected_from_order_id_fkey"))
    op.drop_column('orders', 'reselected_from_order_id')
