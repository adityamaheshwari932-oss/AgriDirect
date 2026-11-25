"""add_bilateral_transport_assignment

Revision ID: e5f6a1b2c3d4
Revises: d4e5f6a1b2c5
Create Date: 2026-11-25 01:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e5f6a1b2c3d4'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a1b2c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Expand cargo_description column capacity
    op.alter_column(
        'transport_connection_requests',
        'cargo_description',
        existing_type=sa.String(255),
        type_=sa.String(500),
        existing_nullable=True,
    )

    # 2. Add bilateral approval and acceptance columns
    op.add_column(
        'transport_connection_requests',
        sa.Column('transporter_accepted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'transport_connection_requests',
        sa.Column('counterparty_approved_by_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_transport_req_counterparty_approved_by',
        'transport_connection_requests',
        'users',
        ['counterparty_approved_by_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.add_column(
        'transport_connection_requests',
        sa.Column('counterparty_approved_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'transport_connection_requests',
        sa.Column('counterparty_rejected_by_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_transport_req_counterparty_rejected_by',
        'transport_connection_requests',
        'users',
        ['counterparty_rejected_by_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.add_column(
        'transport_connection_requests',
        sa.Column('counterparty_rejected_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'transport_connection_requests',
        sa.Column('counterparty_rejection_reason', sa.Text(), nullable=True),
    )

    # 3. Update status check constraint for bilateral assignment lifecycle
    op.drop_constraint('chk_transport_request_status', 'transport_connection_requests', type_='check')
    op.create_check_constraint(
        'chk_transport_request_status',
        'transport_connection_requests',
        "status IN ('pending', 'transporter_accepted', 'counterparty_approved', 'counterparty_rejected', 'declined', 'cancelled', 'accepted', 'approved')",
    )


def downgrade() -> None:
    # 1. Restore original status check constraint
    op.drop_constraint('chk_transport_request_status', 'transport_connection_requests', type_='check')
    op.create_check_constraint(
        'chk_transport_request_status',
        'transport_connection_requests',
        "status IN ('pending', 'accepted', 'declined', 'cancelled')",
    )

    # 2. Drop bilateral approval columns and foreign keys
    op.drop_constraint('fk_transport_req_counterparty_rejected_by', 'transport_connection_requests', type_='foreignkey')
    op.drop_constraint('fk_transport_req_counterparty_approved_by', 'transport_connection_requests', type_='foreignkey')
    op.drop_column('transport_connection_requests', 'counterparty_rejection_reason')
    op.drop_column('transport_connection_requests', 'counterparty_rejected_at')
    op.drop_column('transport_connection_requests', 'counterparty_rejected_by_id')
    op.drop_column('transport_connection_requests', 'counterparty_approved_at')
    op.drop_column('transport_connection_requests', 'counterparty_approved_by_id')
    op.drop_column('transport_connection_requests', 'transporter_accepted_at')

    # 3. Revert cargo_description capacity
    op.alter_column(
        'transport_connection_requests',
        'cargo_description',
        existing_type=sa.String(500),
        type_=sa.String(255),
        existing_nullable=True,
    )
