"""add_order_images_and_idempotency

Revision ID: d4e5f6a1b2c5
Revises: c3d4e5f6a1b2
Create Date: 2026-11-24 13:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a1b2c5'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Alter orders.source_offer_id to nullable
    op.alter_column('orders', 'source_offer_id',
               existing_type=sa.UUID(),
               nullable=True)

    # 2. Add idempotency_key to orders
    op.add_column('orders', sa.Column('idempotency_key', sa.String(length=128), nullable=True))
    op.create_index('idx_orders_idempotency_key', 'orders', ['idempotency_key'], unique=True)

    # 3. Create order_images table
    op.create_table(
        'order_images',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('order_id', sa.UUID(), nullable=False),
        sa.Column('uploaded_by_user_id', sa.UUID(), nullable=False),
        sa.Column('image_uri', sa.String(length=512), nullable=False),
        sa.Column('mime_type', sa.String(length=64), server_default='image/jpeg', nullable=False),
        sa.Column('file_size_bytes', sa.Numeric(precision=12, scale=0), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by_user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_order_images_order_id', 'order_images', ['order_id'], unique=False)
    op.create_index('idx_order_images_uploaded_by', 'order_images', ['uploaded_by_user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_order_images_uploaded_by', table_name='order_images')
    op.drop_index('idx_order_images_order_id', table_name='order_images')
    op.drop_table('order_images')
    op.drop_index('idx_orders_idempotency_key', table_name='orders')
    op.drop_column('orders', 'idempotency_key')
    op.alter_column('orders', 'source_offer_id',
               existing_type=sa.UUID(),
               nullable=False)
