import pytest
from sqlalchemy import inspect
from app.database.session import Base
from app.models import (
    User,
    PoliceOfficer,
    EmergencyContact,
    CrimeIncident,
    OptimizationRun,
    PRPLocation,
    RiskScore,
    PatrolUnit,
    PatrolAssignment,
    LocationUpdate,
    SOSRequest,
    SafeHelpPoint,
    UserRole,
    PatrolStatus,
    PRPStatus,
    OptimizationRunStatus,
    AssignmentStatus,
    SOSStatus,
    SafeHelpPointType,
)


def test_models_registered_in_metadata():
    expected_tables = {
        "users",
        "police_officers",
        "emergency_contacts",
        "crime_incidents",
        "optimization_runs",
        "prp_locations",
        "risk_scores",
        "patrol_units",
        "patrol_assignments",
        "location_updates",
        "sos_requests",
        "safe_help_points",
    }
    actual_tables = set(Base.metadata.tables.keys())
    assert expected_tables.issubset(actual_tables), f"Missing tables: {expected_tables - actual_tables}"


def test_model_relationships():
    # User <-> PoliceOfficer
    user_mapper = inspect(User)
    assert "police_officer" in user_mapper.relationships
    assert "emergency_contacts" in user_mapper.relationships
    assert "sos_requests" in user_mapper.relationships
    assert "optimization_runs" in user_mapper.relationships

    officer_mapper = inspect(PoliceOfficer)
    assert "user" in officer_mapper.relationships
    assert "patrol_units" in officer_mapper.relationships

    patrol_mapper = inspect(PatrolUnit)
    assert "officer" in patrol_mapper.relationships
    assert "assignments" in patrol_mapper.relationships
    assert "assigned_sos_requests" in patrol_mapper.relationships
    assert "location_updates" in patrol_mapper.relationships

    opt_mapper = inspect(OptimizationRun)
    assert "created_by" in opt_mapper.relationships
    assert "prp_locations" in opt_mapper.relationships
    assert "assignments" in opt_mapper.relationships

    prp_mapper = inspect(PRPLocation)
    assert "optimization_run" in prp_mapper.relationships
    assert "assignments" in prp_mapper.relationships

    sos_mapper = inspect(SOSRequest)
    assert "citizen" in sos_mapper.relationships
    assert "assigned_patrol_unit" in sos_mapper.relationships


def test_spatial_columns_exist():
    crime_table = Base.metadata.tables["crime_incidents"]
    assert "location" in crime_table.c

    prp_table = Base.metadata.tables["prp_locations"]
    assert "location" in prp_table.c

    sos_table = Base.metadata.tables["sos_requests"]
    assert "location" in sos_table.c

    patrol_table = Base.metadata.tables["patrol_units"]
    assert "current_location" in patrol_table.c

    help_table = Base.metadata.tables["safe_help_points"]
    assert "location" in help_table.c

    risk_table = Base.metadata.tables["risk_scores"]
    assert "location" in risk_table.c


def test_enums_integrity():
    assert UserRole.ADMIN.value == "ADMIN"
    assert UserRole.POLICE.value == "POLICE"
    assert UserRole.CITIZEN.value == "CITIZEN"

    assert SOSStatus.PENDING.value == "PENDING"
    assert SOSStatus.ASSIGNED.value == "ASSIGNED"
    assert SOSStatus.ACCEPTED.value == "ACCEPTED"
    assert SOSStatus.EN_ROUTE.value == "EN_ROUTE"
    assert SOSStatus.ARRIVED.value == "ARRIVED"
    assert SOSStatus.RESOLVED.value == "RESOLVED"
    assert SOSStatus.CANCELLED.value == "CANCELLED"
