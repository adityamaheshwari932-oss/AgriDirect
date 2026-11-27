"""add_bilateral_transport_assignment

Revision ID: e6a1b2c3d4f5
Revises: d4e5f6a1b2c5
Create Date: 2026-11-25 01:20:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e6a1b2c3d4f5'
down_revision: str | Sequence[str] | None = 'd4e5f6a1b2c5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Use batch_alter_table so schema changes execute cleanly on both PostgreSQL and SQLite
    with op.batch_alter_table('transport_connection_requests') as batch_op:
        # 1. Expand cargo_description column capacity
        batch_op.alter_column(
            'cargo_description',
            existing_type=sa.String(255),
            type_=sa.String(500),
            existing_nullable=True,
        )

        # 2. Add bilateral approval and acceptance columns
        batch_op.add_column(
            sa.Column('transporter_accepted_at', sa.DateTime(timezone=True), nullable=True),
        )
        batch_op.add_column(
            sa.Column('counterparty_approved_by_id', sa.UUID(), nullable=True),
        )
        batch_op.create_foreign_key(
            'fk_transport_req_counterparty_approved_by',
            'users',
            ['counterparty_approved_by_id'],
            ['id'],
            ondelete='SET NULL',
        )
        batch_op.add_column(
            sa.Column('counterparty_approved_at', sa.DateTime(timezone=True), nullable=True),
        )
        batch_op.add_column(
            sa.Column('counterparty_rejected_by_id', sa.UUID(), nullable=True),
        )
        batch_op.create_foreign_key(
            'fk_transport_req_counterparty_rejected_by',
            'users',
            ['counterparty_rejected_by_id'],
            ['id'],
            ondelete='SET NULL',
        )
        batch_op.add_column(
            sa.Column('counterparty_rejected_at', sa.DateTime(timezone=True), nullable=True),
        )
        batch_op.add_column(
            sa.Column('counterparty_rejection_reason', sa.Text(), nullable=True),
        )

        # 3. Update status check constraint for bilateral assignment lifecycle
        batch_op.drop_constraint('chk_transport_request_status', type_='check')
        batch_op.create_check_constraint(
            'chk_transport_request_status',
            "status IN ('pending', 'transporter_accepted', 'counterparty_approved', 'counterparty_rejected', 'declined', 'cancelled', 'accepted', 'approved')",
        )


def downgrade() -> None:
    with op.batch_alter_table('transport_connection_requests') as batch_op:
        # 1. Restore original status check constraint
        batch_op.drop_constraint('chk_transport_request_status', type_='check')
        batch_op.create_check_constraint(
            'chk_transport_request_status',
            "status IN ('pending', 'accepted', 'declined', 'cancelled')",
        )

        # 2. Drop bilateral approval columns and foreign keys
        batch_op.drop_constraint('fk_transport_req_counterparty_rejected_by', type_='foreignkey')
        batch_op.drop_constraint('fk_transport_req_counterparty_approved_by', type_='foreignkey')
        batch_op.drop_column('counterparty_rejection_reason')
        batch_op.drop_column('counterparty_rejected_at')
        batch_op.drop_column('counterparty_rejected_by_id')
        batch_op.drop_column('counterparty_approved_at')
        batch_op.drop_column('counterparty_approved_by_id')
        batch_op.drop_column('transporter_accepted_at')

        # 3. Revert cargo_description capacity
        batch_op.alter_column(
            'cargo_description',
            existing_type=sa.String(500),
            type_=sa.String(255),
            existing_nullable=True,
        )
