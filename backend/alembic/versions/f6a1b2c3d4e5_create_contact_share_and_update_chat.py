"""create_contact_share_and_update_chat_for_module5

Revision ID: f6a1b2c3d4e5
Revises: e5f6a1b2c3d4
Create Date: 2026-10-31 14:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6a1b2c3d4e5'
down_revision: Union[str, Sequence[str], None] = 'e5f6a1b2c3d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema for Module 5 messaging, attachments, and contact sharing."""
    # 1. Update conversations table
    with op.batch_alter_table('conversations') as batch_op:
        batch_op.add_column(sa.Column('order_id', sa.UUID(), nullable=True))
        batch_op.add_column(sa.Column('status', sa.String(length=32), server_default='active', nullable=False))
        batch_op.create_foreign_key('fk_conversations_order_id', 'orders', ['order_id'], ['id'], ondelete='SET NULL')
        batch_op.create_index('idx_conversations_order_id', ['order_id'], unique=False)
        batch_op.create_check_constraint('chk_conversations_status', "status IN ('active', 'archived')")

    # 2. Update messages table
    with op.batch_alter_table('messages') as batch_op:
        batch_op.add_column(sa.Column('message_type', sa.String(length=32), server_default='text', nullable=False))
        batch_op.add_column(sa.Column('delivery_status', sa.String(length=32), server_default='sent', nullable=False))
        batch_op.add_column(sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('read_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('order_id', sa.UUID(), nullable=True))
        batch_op.create_foreign_key('fk_messages_order_id', 'orders', ['order_id'], ['id'], ondelete='SET NULL')
        batch_op.create_index('idx_messages_status', ['conversation_id', 'delivery_status'], unique=False)
        batch_op.create_index('idx_messages_order_id', ['order_id'], unique=False)
        batch_op.create_check_constraint('chk_messages_delivery_status', "delivery_status IN ('sent', 'delivered', 'read')")
        batch_op.create_check_constraint('chk_messages_type', "message_type IN ('text', 'system', 'contact_request')")

    # 3. Update message_attachments table
    with op.batch_alter_table('message_attachments') as batch_op:
        batch_op.add_column(sa.Column('attachment_type', sa.String(length=32), server_default='image', nullable=False))
        batch_op.create_check_constraint('chk_msg_attachments_type', "attachment_type IN ('image', 'document')")

    # 4. Create contact_share_requests table
    op.create_table(
        'contact_share_requests',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('conversation_id', sa.UUID(), nullable=False),
        sa.Column('requester_id', sa.UUID(), nullable=False),
        sa.Column('recipient_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='pending', nullable=False),
        sa.Column('requested_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.CheckConstraint('requester_id <> recipient_id', name='chk_contact_share_counterparts'),
        sa.CheckConstraint("status IN ('pending', 'approved', 'rejected', 'cancelled')", name='chk_contact_share_status'),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recipient_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['requester_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_contact_share_conv_status', 'contact_share_requests', ['conversation_id', 'status'], unique=False)
    op.create_index('idx_contact_share_recipient_status', 'contact_share_requests', ['recipient_id', 'status'], unique=False)
    op.create_index(
        'uq_contact_share_pending_conv',
        'contact_share_requests',
        ['conversation_id'],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    """Downgrade schema for Module 5."""
    # 4. Drop contact_share_requests table
    op.drop_index('uq_contact_share_pending_conv', table_name='contact_share_requests')
    op.drop_index('idx_contact_share_recipient_status', table_name='contact_share_requests')
    op.drop_index('idx_contact_share_conv_status', table_name='contact_share_requests')
    op.drop_table('contact_share_requests')

    # 3. Revert message_attachments
    with op.batch_alter_table('message_attachments') as batch_op:
        batch_op.drop_constraint('chk_msg_attachments_type', type_='check')
        batch_op.drop_column('attachment_type')

    # 2. Revert messages
    with op.batch_alter_table('messages') as batch_op:
        batch_op.drop_constraint('chk_messages_type', type_='check')
        batch_op.drop_constraint('chk_messages_delivery_status', type_='check')
        batch_op.drop_index('idx_messages_order_id')
        batch_op.drop_index('idx_messages_status')
        batch_op.drop_constraint('fk_messages_order_id', type_='foreignkey')
        batch_op.drop_column('order_id')
        batch_op.drop_column('read_at')
        batch_op.drop_column('delivered_at')
        batch_op.drop_column('delivery_status')
        batch_op.drop_column('message_type')

    # 1. Revert conversations
    with op.batch_alter_table('conversations') as batch_op:
        batch_op.drop_constraint('chk_conversations_status', type_='check')
        batch_op.drop_index('idx_conversations_order_id')
        batch_op.drop_constraint('fk_conversations_order_id', type_='foreignkey')
        batch_op.drop_column('status')
        batch_op.drop_column('order_id')
