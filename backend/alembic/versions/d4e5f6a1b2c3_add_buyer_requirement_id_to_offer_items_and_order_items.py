"""add_buyer_requirement_id_and_fulfillment_approvals

Revision ID: d4e5f6a1b2c3
Revises: fcf5c991d506
Create Date: 2026-10-30 06:05:00.000000

Consolidates Backend Module 3 and ADR-003 schema requirements:
1. Adds buyer_requirement_id to offer_items with foreign key and index.
2. Adds buyer_requirement_id to order_items with foreign key and index.
3. Creates unique constraint uq_order_items_identity_requirement on
   order_items(id, order_id, buyer_requirement_id) required by composite FK.
4. Creates requirement_fulfillment_approvals table with:
   - Primary key, foreign keys, unique constraint on order_item_id
   - Composite foreign key fk_approvals_order_item_composite to order_items
   - Check constraints chk_approval_proposed_quantity, chk_approval_status,
     and chk_approval_complete_invariants
   - Performance indexes on requirement_id, status, order_id, reviewed_by_user_id
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a1b2c3'
down_revision: Union[str, Sequence[str], None] = 'fcf5c991d506'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply Module 3 and ADR-003 schema additions in strict topological order."""
    # -----------------------------------------------------------------------
    # 1. Update offer_items
    # -----------------------------------------------------------------------
    with op.batch_alter_table('offer_items') as batch_op:
        batch_op.add_column(
            sa.Column('buyer_requirement_id', sa.UUID(), nullable=True),
        )
        batch_op.create_foreign_key(
            'fk_offer_items_buyer_requirement_id',
            'buyer_requirements',
            ['buyer_requirement_id'],
            ['id'],
            ondelete='SET NULL',
        )
        batch_op.create_index(
            'idx_offer_items_requirement',
            ['buyer_requirement_id'],
            unique=False,
        )

    # -----------------------------------------------------------------------
    # 2. Update order_items
    # -----------------------------------------------------------------------
    with op.batch_alter_table('order_items') as batch_op:
        batch_op.add_column(
            sa.Column('buyer_requirement_id', sa.UUID(), nullable=True),
        )
        batch_op.create_foreign_key(
            'fk_order_items_buyer_requirement_id',
            'buyer_requirements',
            ['buyer_requirement_id'],
            ['id'],
            ondelete='SET NULL',
        )
        batch_op.create_index(
            'idx_order_items_requirement',
            ['buyer_requirement_id'],
            unique=False,
        )
        # Unique constraint required to back fk_approvals_order_item_composite
        batch_op.create_unique_constraint(
            'uq_order_items_identity_requirement',
            ['id', 'order_id', 'buyer_requirement_id'],
        )

    # -----------------------------------------------------------------------
    # 3. Create requirement_fulfillment_approvals table
    # -----------------------------------------------------------------------
    op.create_table(
        'requirement_fulfillment_approvals',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('requirement_id', sa.UUID(), nullable=False),
        sa.Column('order_id', sa.UUID(), nullable=False),
        sa.Column('order_item_id', sa.UUID(), nullable=False),
        sa.Column('proposed_quantity', sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column('approved_quantity', sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column('status', sa.String(length=32), server_default='pending', nullable=False),
        sa.Column('reviewed_by_user_id', sa.UUID(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.String(length=500), nullable=True),
        sa.Column('voided_by_user_id', sa.UUID(), nullable=True),
        sa.Column('voided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('void_reason', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),

        # Primary Key & Unique Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('order_item_id', name='uq_requirement_fulfillment_approvals_order_item_id'),

        # Foreign Key Constraints
        sa.ForeignKeyConstraint(['requirement_id'], ['buyer_requirements.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['order_item_id'], ['order_items.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['reviewed_by_user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['voided_by_user_id'], ['users.id'], ondelete='RESTRICT'),

        # Composite Foreign Key referencing order_items identity & requirement
        sa.ForeignKeyConstraint(
            ['order_item_id', 'order_id', 'requirement_id'],
            ['order_items.id', 'order_items.order_id', 'order_items.buyer_requirement_id'],
            name='fk_approvals_order_item_composite',
            ondelete='RESTRICT',
        ),

        # Check Constraints
        sa.CheckConstraint('proposed_quantity > 0', name='chk_approval_proposed_quantity'),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'not_applied', 'voided')",
            name='chk_approval_status',
        ),
        sa.CheckConstraint(
            """(
                status = 'pending'
                AND approved_quantity IS NULL
                AND reviewed_by_user_id IS NULL
                AND reviewed_at IS NULL
                AND rejection_reason IS NULL
                AND voided_by_user_id IS NULL
                AND voided_at IS NULL
                AND void_reason IS NULL
            ) OR (
                status = 'approved'
                AND approved_quantity IS NOT NULL
                AND approved_quantity > 0
                AND approved_quantity <= proposed_quantity
                AND reviewed_by_user_id IS NOT NULL
                AND reviewed_at IS NOT NULL
                AND rejection_reason IS NULL
                AND voided_by_user_id IS NULL
                AND voided_at IS NULL
                AND void_reason IS NULL
            ) OR (
                status = 'rejected'
                AND approved_quantity IS NULL
                AND reviewed_by_user_id IS NOT NULL
                AND reviewed_at IS NOT NULL
                AND voided_by_user_id IS NULL
                AND voided_at IS NULL
                AND void_reason IS NULL
            ) OR (
                status = 'not_applied'
                AND approved_quantity IS NULL
                AND reviewed_by_user_id IS NOT NULL
                AND reviewed_at IS NOT NULL
                AND rejection_reason IS NULL
                AND voided_by_user_id IS NULL
                AND voided_at IS NULL
                AND void_reason IS NULL
            ) OR (
                status = 'voided'
                AND approved_quantity IS NULL
                AND reviewed_by_user_id IS NULL
                AND reviewed_at IS NULL
                AND rejection_reason IS NULL
                AND voided_at IS NOT NULL
                AND void_reason IS NOT NULL
            )""",
            name='chk_approval_complete_invariants',
        ),
    )

    # Performance Indexes
    op.create_index(
        'idx_req_approvals_requirement_status',
        'requirement_fulfillment_approvals',
        ['requirement_id', 'status'],
        unique=False,
    )
    op.create_index(
        'idx_req_approvals_buyer_pending',
        'requirement_fulfillment_approvals',
        ['requirement_id'],
        unique=False,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        'idx_req_approvals_order',
        'requirement_fulfillment_approvals',
        ['order_id'],
        unique=False,
    )
    op.create_index(
        'idx_req_approvals_reviewed_by',
        'requirement_fulfillment_approvals',
        ['reviewed_by_user_id'],
        unique=False,
        postgresql_where=sa.text("reviewed_by_user_id IS NOT NULL"),
    )


def downgrade() -> None:
    """Revert Module 3 and ADR-003 schema additions in reverse dependency order."""
    # -----------------------------------------------------------------------
    # 1. Drop requirement_fulfillment_approvals indexes and table
    # -----------------------------------------------------------------------
    op.drop_index('idx_req_approvals_reviewed_by', table_name='requirement_fulfillment_approvals')
    op.drop_index('idx_req_approvals_order', table_name='requirement_fulfillment_approvals')
    op.drop_index('idx_req_approvals_buyer_pending', table_name='requirement_fulfillment_approvals')
    op.drop_index('idx_req_approvals_requirement_status', table_name='requirement_fulfillment_approvals')
    op.drop_table('requirement_fulfillment_approvals')

    # -----------------------------------------------------------------------
    # 2. Revert order_items modifications
    # -----------------------------------------------------------------------
    with op.batch_alter_table('order_items') as batch_op:
        batch_op.drop_constraint('uq_order_items_identity_requirement', type_='unique')
        batch_op.drop_index('idx_order_items_requirement')
        batch_op.drop_constraint('fk_order_items_buyer_requirement_id', type_='foreignkey')
        batch_op.drop_column('buyer_requirement_id')

    # -----------------------------------------------------------------------
    # 3. Revert offer_items modifications
    # -----------------------------------------------------------------------
    with op.batch_alter_table('offer_items') as batch_op:
        batch_op.drop_index('idx_offer_items_requirement')
        batch_op.drop_constraint('fk_offer_items_buyer_requirement_id', type_='foreignkey')
        batch_op.drop_column('buyer_requirement_id')
