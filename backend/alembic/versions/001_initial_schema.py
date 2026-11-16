"""Initial PostgreSQL schema for CCTV parking management

Revision ID: 001_initial_schema
Revises: None
Create Date: 2026-11-16 22:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. parking_slots
    op.create_table(
        'parking_slots',
        sa.Column('slot_id', sa.String(length=50), nullable=False),
        sa.Column('zone', sa.String(length=50), nullable=False),
        sa.Column('allowed_category', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='AVAILABLE'),
        sa.Column('polygon_coords', sa.JSON(), nullable=True),
        sa.Column('current_track_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('slot_id')
    )
    op.create_index(op.f('ix_parking_slots_slot_id'), 'parking_slots', ['slot_id'], unique=False)
    op.create_index(op.f('ix_parking_slots_zone'), 'parking_slots', ['zone'], unique=False)
    op.create_index(op.f('ix_parking_slots_status'), 'parking_slots', ['status'], unique=False)

    # 2. vehicle_sessions
    op.create_table(
        'vehicle_sessions',
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('track_id', sa.Integer(), nullable=False),
        sa.Column('plate_number', sa.String(length=32), nullable=True),
        sa.Column('vehicle_category', sa.String(length=50), nullable=False),
        sa.Column('assigned_slot_id', sa.String(length=50), nullable=True),
        sa.Column('actual_slot_id', sa.String(length=50), nullable=True),
        sa.Column('camera_id', sa.String(length=50), nullable=True),
        sa.Column('entry_time', sa.DateTime(), nullable=False),
        sa.Column('exit_time', sa.DateTime(), nullable=True),
        sa.Column('duration_minutes', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='ACTIVE'),
        sa.Column('overstay_alerted', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['actual_slot_id'], ['parking_slots.slot_id'], ),
        sa.ForeignKeyConstraint(['assigned_slot_id'], ['parking_slots.slot_id'], ),
        sa.PrimaryKeyConstraint('session_id')
    )
    op.create_index(op.f('ix_vehicle_sessions_track_id'), 'vehicle_sessions', ['track_id'], unique=False)
    op.create_index(op.f('ix_vehicle_sessions_plate_number'), 'vehicle_sessions', ['plate_number'], unique=False)
    op.create_index(op.f('ix_vehicle_sessions_status'), 'vehicle_sessions', ['status'], unique=False)

    # 3. watchlist
    op.create_table(
        'watchlist',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('plate_number', sa.String(length=32), nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=False),
        sa.Column('added_by', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_watchlist_plate_number'), 'watchlist', ['plate_number'], unique=True)
    op.create_index(op.f('ix_watchlist_is_active'), 'watchlist', ['is_active'], unique=False)

    # 4. alerts
    op.create_table(
        'alerts',
        sa.Column('alert_id', sa.String(length=64), nullable=False),
        sa.Column('alert_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('plate_number', sa.String(length=32), nullable=True),
        sa.Column('slot_id', sa.String(length=50), nullable=True),
        sa.Column('camera_id', sa.String(length=50), nullable=True),
        sa.Column('snapshot_url', sa.String(length=512), nullable=True),
        sa.Column('message', sa.String(length=512), nullable=True),
        sa.Column('is_acknowledged', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('alert_id')
    )
    op.create_index(op.f('ix_alerts_alert_type'), 'alerts', ['alert_type'], unique=False)
    op.create_index(op.f('ix_alerts_plate_number'), 'alerts', ['plate_number'], unique=False)
    op.create_index(op.f('ix_alerts_is_acknowledged'), 'alerts', ['is_acknowledged'], unique=False)

def downgrade() -> None:
    op.drop_table('alerts')
    op.drop_table('watchlist')
    op.drop_table('vehicle_sessions')
    op.drop_table('parking_slots')
