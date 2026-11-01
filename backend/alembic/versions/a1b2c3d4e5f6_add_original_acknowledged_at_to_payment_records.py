"""add_original_acknowledged_at_to_payment_records

Revision ID: a1b2c3d4e5f6
Revises: f6a1b2c3d4e5
Create Date: 2026-11-01 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f6a1b2c3d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add original_acknowledged_at column to payment_records to preserve acknowledgement audit trail."""
    with op.batch_alter_table('payment_records') as batch_op:
        batch_op.add_column(sa.Column('original_acknowledged_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Revert original_acknowledged_at column from payment_records."""
    with op.batch_alter_table('payment_records') as batch_op:
        batch_op.drop_column('original_acknowledged_at')

