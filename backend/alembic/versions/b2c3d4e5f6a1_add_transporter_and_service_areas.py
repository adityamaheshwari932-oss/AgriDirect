"""add_transporter_and_service_areas

Revision ID: b2c3d4e5f6a1
Revises: a1b2c3d4e5f6
Create Date: 2026-11-18 03:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a1'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update chk_users_role to allow 'transporter'
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_constraint('chk_users_role', type_='check')
        batch_op.create_check_constraint(
            'chk_users_role',
            "role IN ('farmer', 'buyer', 'admin', 'transporter')"
        )

    # 2. Create transporter_profiles table
    op.create_table(
        'transporter_profiles',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('business_name', sa.String(length=128), nullable=False),
        sa.Column('contact_name', sa.String(length=128), nullable=False),
        sa.Column('phone_number', sa.String(length=32), nullable=False),
        sa.Column('transport_type', sa.String(length=64), nullable=False),
        sa.Column('vehicle_capacity_kg', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('vehicle_registration_number', sa.String(length=64), nullable=False),
        sa.Column('is_available', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('experience_years', sa.Integer(), server_default='0', nullable=False),
        sa.Column('operating_states', sa.String(length=255), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('vehicle_capacity_kg > 0', name='chk_transporter_capacity_positive'),
        sa.CheckConstraint('experience_years >= 0', name='chk_transporter_exp_non_negative'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(
        'idx_transporter_profiles_type_available',
        'transporter_profiles',
        ['transport_type', 'is_available'],
        unique=False
    )

    # 3. Create service_areas table
    op.create_table(
        'service_areas',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('transporter_profile_id', sa.UUID(), nullable=False),
        sa.Column('state', sa.String(length=64), nullable=False),
        sa.Column('district', sa.String(length=64), nullable=False),
        sa.Column('taluka_subdistrict', sa.String(length=64), nullable=True),
        sa.Column('village_town', sa.String(length=64), nullable=True),
        sa.Column('pincode', sa.String(length=16), nullable=True),
        sa.Column('coverage_type', sa.String(length=32), server_default='both', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("coverage_type IN ('pickup_only', 'delivery_only', 'both')", name='chk_service_area_coverage_type'),
        sa.ForeignKeyConstraint(['transporter_profile_id'], ['transporter_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('transporter_profile_id', 'state', 'district', 'coverage_type', name='uq_service_area_profile_location')
    )
    op.create_index('idx_service_areas_state_district', 'service_areas', ['state', 'district'], unique=False)
    op.create_index('idx_service_areas_transporter_id', 'service_areas', ['transporter_profile_id'], unique=False)

    # 4. Add transporter columns to orders table
    with op.batch_alter_table('orders') as batch_op:
        batch_op.add_column(sa.Column('transporter_id', sa.UUID(), nullable=True))
        batch_op.add_column(sa.Column('transport_status', sa.String(length=32), server_default='none', nullable=False))
        batch_op.create_foreign_key(
            'fk_orders_transporter_id_users',
            'users',
            ['transporter_id'],
            ['id'],
            ondelete='SET NULL'
        )


def downgrade() -> None:
    # 4. Remove transporter columns from orders table
    with op.batch_alter_table('orders') as batch_op:
        batch_op.drop_constraint('fk_orders_transporter_id_users', type_='foreignkey')
        batch_op.drop_column('transport_status')
        batch_op.drop_column('transporter_id')

    # 3. Drop service_areas
    op.drop_index('idx_service_areas_transporter_id', table_name='service_areas')
    op.drop_index('idx_service_areas_state_district', table_name='service_areas')
    op.drop_table('service_areas')

    # 2. Drop transporter_profiles
    op.drop_index('idx_transporter_profiles_type_available', table_name='transporter_profiles')
    op.drop_table('transporter_profiles')

    # 1. Revert chk_users_role
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_constraint('chk_users_role', type_='check')
        batch_op.create_check_constraint(
            'chk_users_role',
            "role IN ('farmer', 'buyer', 'admin')"
        )
