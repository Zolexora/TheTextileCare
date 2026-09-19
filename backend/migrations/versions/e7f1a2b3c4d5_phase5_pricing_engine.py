"""phase5_pricing_engine

Revision ID: e7f1a2b3c4d5
Revises: ddf173e6fc96
Create Date: 2026-09-19 05:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7f1a2b3c4d5'
down_revision: Union[str, None] = 'ddf173e6fc96'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create price_books table
    op.create_table(
        'price_books',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column('scope', sa.String(length=50), server_default='SELLER', nullable=False),
        sa.Column('status', sa.String(length=50), server_default='DRAFT', nullable=False),
        sa.Column('seller_id', sa.Uuid(), nullable=True),
        sa.Column('branch_id', sa.Uuid(), nullable=True),
        sa.Column('currency', sa.String(length=3), server_default='USD', nullable=False),
        sa.Column('priority', sa.Integer(), server_default='0', nullable=False),
        sa.Column('is_default', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['branch_id'], ['seller_branches.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['seller_id'], ['sellers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_price_books_tenant_id'), 'price_books', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_price_books_seller_id'), 'price_books', ['seller_id'], unique=False)
    op.create_index(op.f('ix_price_books_branch_id'), 'price_books', ['branch_id'], unique=False)
    op.create_index('idx_price_books_tenant_scope', 'price_books', ['tenant_id', 'scope'], unique=False)
    op.create_index('idx_price_books_tenant_seller', 'price_books', ['tenant_id', 'seller_id'], unique=False)
    op.create_index('idx_price_books_tenant_branch', 'price_books', ['tenant_id', 'branch_id'], unique=False)
    op.create_index('idx_price_books_tenant_status', 'price_books', ['tenant_id', 'status'], unique=False)
    op.create_index('idx_price_books_seller_id', 'price_books', ['seller_id'], unique=False)
    op.create_index('idx_price_books_branch_id', 'price_books', ['branch_id'], unique=False)

    # 2. Create price_rules table
    op.create_table(
        'price_rules',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=True),
        sa.Column('price_book_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column('service_id', sa.Uuid(), nullable=True),
        sa.Column('service_item_id', sa.Uuid(), nullable=True),
        sa.Column('service_addon_id', sa.Uuid(), nullable=True),
        sa.Column('rule_type', sa.String(length=50), nullable=False),
        sa.Column('component_type', sa.String(length=50), server_default='BASE_PRICE', nullable=False),
        sa.Column('rate_type', sa.String(length=50), server_default='FLAT', nullable=False),
        sa.Column('rate', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='ACTIVE', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('priority', sa.Integer(), server_default='0', nullable=False),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['price_book_id'], ['price_books.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['service_addon_id'], ['service_addons.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['service_id'], ['services.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['service_item_id'], ['service_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_price_rules_tenant_id'), 'price_rules', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_price_rules_price_book_id'), 'price_rules', ['price_book_id'], unique=False)
    op.create_index(op.f('ix_price_rules_service_id'), 'price_rules', ['service_id'], unique=False)
    op.create_index(op.f('ix_price_rules_service_item_id'), 'price_rules', ['service_item_id'], unique=False)
    op.create_index(op.f('ix_price_rules_service_addon_id'), 'price_rules', ['service_addon_id'], unique=False)
    op.create_index('idx_price_rules_book_service', 'price_rules', ['price_book_id', 'service_id'], unique=False)
    op.create_index('idx_price_rules_book_item', 'price_rules', ['price_book_id', 'service_item_id'], unique=False)
    op.create_index('idx_price_rules_book_addon', 'price_rules', ['price_book_id', 'service_addon_id'], unique=False)
    op.create_index('idx_price_rules_book_active', 'price_rules', ['price_book_id', 'is_active'], unique=False)
    op.create_index('idx_price_rules_tenant_id', 'price_rules', ['tenant_id'], unique=False)
    op.create_index('idx_price_rules_tenant_book', 'price_rules', ['tenant_id', 'price_book_id'], unique=False)
    op.create_index(
        'idx_price_rules_service_lookup',
        'price_rules',
        ['service_id', 'service_item_id', 'service_addon_id'],
        unique=False,
    )


def downgrade() -> None:
    # Drop child table first (price_rules)
    op.drop_index('idx_price_rules_service_lookup', table_name='price_rules')
    op.drop_index('idx_price_rules_tenant_book', table_name='price_rules')
    op.drop_index('idx_price_rules_tenant_id', table_name='price_rules')
    op.drop_index('idx_price_rules_book_active', table_name='price_rules')
    op.drop_index('idx_price_rules_book_addon', table_name='price_rules')
    op.drop_index('idx_price_rules_book_item', table_name='price_rules')
    op.drop_index('idx_price_rules_book_service', table_name='price_rules')
    op.drop_index(op.f('ix_price_rules_service_addon_id'), table_name='price_rules')
    op.drop_index(op.f('ix_price_rules_service_item_id'), table_name='price_rules')
    op.drop_index(op.f('ix_price_rules_service_id'), table_name='price_rules')
    op.drop_index(op.f('ix_price_rules_price_book_id'), table_name='price_rules')
    op.drop_index(op.f('ix_price_rules_tenant_id'), table_name='price_rules')
    op.drop_table('price_rules')

    # Drop parent table second (price_books)
    op.drop_index('idx_price_books_branch_id', table_name='price_books')
    op.drop_index('idx_price_books_seller_id', table_name='price_books')
    op.drop_index('idx_price_books_tenant_status', table_name='price_books')
    op.drop_index('idx_price_books_tenant_branch', table_name='price_books')
    op.drop_index('idx_price_books_tenant_seller', table_name='price_books')
    op.drop_index('idx_price_books_tenant_scope', table_name='price_books')
    op.drop_index(op.f('ix_price_books_branch_id'), table_name='price_books')
    op.drop_index(op.f('ix_price_books_seller_id'), table_name='price_books')
    op.drop_index(op.f('ix_price_books_tenant_id'), table_name='price_books')
    op.drop_table('price_books')
