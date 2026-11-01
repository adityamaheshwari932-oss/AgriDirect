"""create_order_delivery_acknowledgements

Revision ID: e5f6a1b2c3d4
Revises: d4e5f6a1b2c3
Create Date: 2026-10-31 12:15:00.000000

Consolidates Backend Module 4 revised delivery acknowledgement policy:
1. Creates order_delivery_acknowledgements table with:
   - Primary key (UUID with gen_random_uuid() default)
   - Foreign key to orders.id (ON DELETE CASCADE)
   - Foreign key to users.id (ON DELETE RESTRICT)
   - Timestamp acknowledged_at with server_default=now()
   - Optional notes text column
   - Unique constraint uq_order_delivery_acknowledgements_order_user on (order_id, user_id)
   - Performance indexes on order_id and user_id
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a1b2c3d4'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a1b2c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create order_delivery_acknowledgements table and indexes."""
    op.create_table(
        'order_delivery_acknowledgements',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('order_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], name='fk_order_delivery_acknowledgements_order_id', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='fk_order_delivery_acknowledgements_user_id', ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('order_id', 'user_id', name='uq_order_delivery_acknowledgements_order_user'),
    )
    op.create_index(
        'idx_order_delivery_acknowledgements_order_id',
        'order_delivery_acknowledgements',
        ['order_id'],
        unique=False,
    )
    op.create_index(
        'idx_order_delivery_acknowledgements_user_id',
        'order_delivery_acknowledgements',
        ['user_id'],
        unique=False,
    )


def downgrade() -> None:
    """Drop order_delivery_acknowledgements table and indexes."""
    op.drop_index('idx_order_delivery_acknowledgements_user_id', table_name='order_delivery_acknowledgements')
    op.drop_index('idx_order_delivery_acknowledgements_order_id', table_name='order_delivery_acknowledgements')
    op.drop_table('order_delivery_acknowledgements')

