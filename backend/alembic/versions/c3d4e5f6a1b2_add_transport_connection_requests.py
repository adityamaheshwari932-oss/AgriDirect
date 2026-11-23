"""add_transport_connection_requests

Revision ID: c3d4e5f6a1b2
Revises: b2c3d4e5f6a1
Create Date: 2026-11-23 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a1b2'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'transport_connection_requests',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('requester_id', sa.UUID(), nullable=False),
        sa.Column('transporter_id', sa.UUID(), nullable=False),
        sa.Column('order_id', sa.UUID(), nullable=True),
        sa.Column('offer_id', sa.UUID(), nullable=True),
        sa.Column('pickup_state', sa.String(length=64), nullable=True),
        sa.Column('pickup_district', sa.String(length=64), nullable=True),
        sa.Column('pickup_address', sa.Text(), nullable=True),
        sa.Column('delivery_state', sa.String(length=64), nullable=True),
        sa.Column('delivery_district', sa.String(length=64), nullable=True),
        sa.Column('delivery_address', sa.Text(), nullable=True),
        sa.Column('cargo_description', sa.String(length=255), nullable=True),
        sa.Column('weight_kg', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('required_delivery_date', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), server_default='pending', nullable=False),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('response_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'declined', 'cancelled')",
            name='chk_transport_request_status'
        ),
        sa.ForeignKeyConstraint(['requester_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['transporter_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['offer_id'], ['offers.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        'idx_transport_req_transporter_status',
        'transport_connection_requests',
        ['transporter_id', 'status'],
        unique=False
    )
    op.create_index(
        'idx_transport_req_requester_status',
        'transport_connection_requests',
        ['requester_id', 'status'],
        unique=False
    )
    op.create_index(
        'idx_transport_req_order',
        'transport_connection_requests',
        ['order_id'],
        unique=False
    )
    op.create_index(
        'idx_transport_req_offer',
        'transport_connection_requests',
        ['offer_id'],
        unique=False
    )


def downgrade() -> None:
    op.drop_index('idx_transport_req_offer', table_name='transport_connection_requests')
    op.drop_index('idx_transport_req_order', table_name='transport_connection_requests')
    op.drop_index('idx_transport_req_requester_status', table_name='transport_connection_requests')
    op.drop_index('idx_transport_req_transporter_status', table_name='transport_connection_requests')
    op.drop_table('transport_connection_requests')
