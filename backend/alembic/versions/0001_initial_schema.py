"""Initial database schema with PostGIS support

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-09-18 01:14:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2


# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure PostGIS extension exists
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    # 1. Users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=32), nullable=False),
        sa.Column('phone_number', sa.String(length=32), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_role', 'users', ['role'], unique=False)

    # 2. Police Officers
    op.create_table(
        'police_officers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('badge_number', sa.String(length=64), nullable=False),
        sa.Column('rank', sa.String(length=64), nullable=True),
        sa.Column('department', sa.String(length=128), nullable=True),
        sa.Column('is_on_duty', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_police_officers_user_id', 'police_officers', ['user_id'], unique=True)
    op.create_index('ix_police_officers_badge_number', 'police_officers', ['badge_number'], unique=True)

    # 3. Patrol Units
    op.create_table(
        'patrol_units',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('call_sign', sa.String(length=64), nullable=False),
        sa.Column('officer_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='OFF_DUTY'),
        sa.Column('current_location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326, spatial_index=True), nullable=True),
        sa.Column('last_location_update', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['officer_id'], ['police_officers.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_patrol_units_call_sign', 'patrol_units', ['call_sign'], unique=True)
    op.create_index('ix_patrol_units_officer_id', 'patrol_units', ['officer_id'], unique=False)
    op.create_index('ix_patrol_units_status', 'patrol_units', ['status'], unique=False)

    # 4. Crime Incidents
    op.create_table(
        'crime_incidents',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('incident_number', sa.String(length=64), nullable=False),
        sa.Column('category', sa.String(length=128), nullable=False),
        sa.Column('severity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('incident_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326, spatial_index=True), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_crime_incidents_incident_number', 'crime_incidents', ['incident_number'], unique=True)
    op.create_index('ix_crime_incidents_category', 'crime_incidents', ['category'], unique=False)
    op.create_index('ix_crime_incidents_incident_time', 'crime_incidents', ['incident_time'], unique=False)

    # 5. Optimization Runs
    op.create_table(
        'optimization_runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_time', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('shift', sa.String(length=64), nullable=False),
        sa.Column('available_patrol_count', sa.Integer(), nullable=False),
        sa.Column('coverage_radius_km', sa.Float(), nullable=False, server_default='3.0'),
        sa.Column('parameters', sa.JSON(), nullable=True),
        sa.Column('metrics', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='PENDING'),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_optimization_runs_run_time', 'optimization_runs', ['run_time'], unique=False)
    op.create_index('ix_optimization_runs_status', 'optimization_runs', ['status'], unique=False)
    op.create_index('ix_optimization_runs_created_by_id', 'optimization_runs', ['created_by_id'], unique=False)

    # 6. PRP Locations
    op.create_table(
        'prp_locations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('optimization_run_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326, spatial_index=True), nullable=False),
        sa.Column('coverage_radius_km', sa.Float(), nullable=False, server_default='3.0'),
        sa.Column('priority_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='RECOMMENDED'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['optimization_run_id'], ['optimization_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_prp_locations_optimization_run_id', 'prp_locations', ['optimization_run_id'], unique=False)
    op.create_index('ix_prp_locations_status', 'prp_locations', ['status'], unique=False)

    # 7. Patrol Assignments
    op.create_table(
        'patrol_assignments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('patrol_unit_id', sa.Integer(), nullable=False),
        sa.Column('prp_location_id', sa.Integer(), nullable=False),
        sa.Column('optimization_run_id', sa.Integer(), nullable=False),
        sa.Column('shift', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='ASSIGNED'),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('arrived_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['patrol_unit_id'], ['patrol_units.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['prp_location_id'], ['prp_locations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['optimization_run_id'], ['optimization_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_patrol_assignments_patrol_unit_id', 'patrol_assignments', ['patrol_unit_id'], unique=False)
    op.create_index('ix_patrol_assignments_prp_location_id', 'patrol_assignments', ['prp_location_id'], unique=False)
    op.create_index('ix_patrol_assignments_optimization_run_id', 'patrol_assignments', ['optimization_run_id'], unique=False)
    op.create_index('ix_patrol_assignments_status', 'patrol_assignments', ['status'], unique=False)

    # 8. SOS Requests
    op.create_table(
        'sos_requests',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('citizen_id', sa.Integer(), nullable=False),
        sa.Column('location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326, spatial_index=True), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='PENDING'),
        sa.Column('assigned_patrol_unit_id', sa.Integer(), nullable=True),
        sa.Column('trigger_time', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('accepted_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('en_route_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('arrived_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['citizen_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_patrol_unit_id'], ['patrol_units.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sos_requests_citizen_id', 'sos_requests', ['citizen_id'], unique=False)
    op.create_index('ix_sos_requests_status', 'sos_requests', ['status'], unique=False)
    op.create_index('ix_sos_requests_assigned_patrol_unit_id', 'sos_requests', ['assigned_patrol_unit_id'], unique=False)
    op.create_index('ix_sos_requests_trigger_time', 'sos_requests', ['trigger_time'], unique=False)

    # 9. Location Updates
    op.create_table(
        'location_updates',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('patrol_unit_id', sa.Integer(), nullable=False),
        sa.Column('location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326, spatial_index=True), nullable=False),
        sa.Column('speed', sa.Float(), nullable=True),
        sa.Column('heading', sa.Float(), nullable=True),
        sa.Column('battery_level', sa.Float(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['patrol_unit_id'], ['patrol_units.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_location_updates_patrol_unit_id', 'location_updates', ['patrol_unit_id'], unique=False)
    op.create_index('ix_location_updates_recorded_at', 'location_updates', ['recorded_at'], unique=False)

    # 10. Emergency Contacts
    op.create_table(
        'emergency_contacts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('phone_number', sa.String(length=32), nullable=False),
        sa.Column('relationship_type', sa.String(length=64), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_emergency_contacts_user_id', 'emergency_contacts', ['user_id'], unique=False)

    # 11. Risk Scores
    op.create_table(
        'risk_scores',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326, spatial_index=True), nullable=False),
        sa.Column('grid_identifier', sa.String(length=64), nullable=True),
        sa.Column('frequency_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('severity_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('recency_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('time_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('total_risk_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('calculated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_risk_scores_grid_identifier', 'risk_scores', ['grid_identifier'], unique=False)
    op.create_index('ix_risk_scores_total_risk_score', 'risk_scores', ['total_risk_score'], unique=False)
    op.create_index('ix_risk_scores_calculated_at', 'risk_scores', ['calculated_at'], unique=False)

    # 12. Safe Help Points
    op.create_table(
        'safe_help_points',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=32), nullable=False, server_default='HELP_DESK'),
        sa.Column('location', geoalchemy2.types.Geography(geometry_type='POINT', srid=4326, spatial_index=True), nullable=False),
        sa.Column('address', sa.String(length=512), nullable=True),
        sa.Column('contact_number', sa.String(length=32), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_safe_help_points_name', 'safe_help_points', ['name'], unique=False)
    op.create_index('ix_safe_help_points_category', 'safe_help_points', ['category'], unique=False)
    op.create_index('ix_safe_help_points_is_verified', 'safe_help_points', ['is_verified'], unique=False)
    op.create_index('ix_safe_help_points_is_active', 'safe_help_points', ['is_active'], unique=False)


def downgrade() -> None:
    op.drop_table('safe_help_points')
    op.drop_table('risk_scores')
    op.drop_table('emergency_contacts')
    op.drop_table('location_updates')
    op.drop_table('sos_requests')
    op.drop_table('patrol_assignments')
    op.drop_table('prp_locations')
    op.drop_table('optimization_runs')
    op.drop_table('crime_incidents')
    op.drop_table('patrol_units')
    op.drop_table('police_officers')
    op.drop_table('users')
