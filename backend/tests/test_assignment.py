from datetime import datetime, timedelta, timezone
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.enums import AssignmentStatus, OptimizationRunStatus, PatrolStatus, PRPStatus, UserRole
from app.models.optimization import OptimizationRun, PRPLocation
from app.models.patrol import PatrolAssignment, PatrolUnit
from app.models.user import PoliceOfficer, User
from app.optimization.assignment import (
    PatrolResource,
    PRPResource,
    assign_patrols_to_prps,
)
from app.schemas.assignment import AutoAssignmentRequest, ManualAssignmentRequest
from app.services.assignment_service import AssignmentService
from app.services.crime_service import create_point_geometry


def test_distance_preference_matching():
    """Matching engine pairs patrol units to PRPs minimizing total system travel distance."""
    # Unit 1 at (12.970, 77.590), Unit 2 at (12.980, 77.640)
    units = [
        PatrolResource(id=1, call_sign="EAGLE-01", latitude=12.970, longitude=77.590),
        PatrolResource(id=2, call_sign="EAGLE-02", latitude=12.980, longitude=77.640),
    ]
    # PRP 1 close to Unit 1 (12.971, 77.591), PRP 2 close to Unit 2 (12.981, 77.641)
    prps = [
        PRPResource(id=101, name="PRP-Central", latitude=12.971, longitude=77.591, optimization_run_id=1, priority_score=10.0),
        PRPResource(id=102, name="PRP-East", latitude=12.981, longitude=77.641, optimization_run_id=1, priority_score=8.0),
    ]

    matches = assign_patrols_to_prps(units, prps)

    assert len(matches) == 2
    match_map = {m.patrol_unit_id: m.prp_location_id for m in matches}
    assert match_map[1] == 101  # Unit 1 matched to nearby PRP 1
    assert match_map[2] == 102  # Unit 2 matched to nearby PRP 2


@pytest.mark.asyncio
async def test_unavailable_patrol_not_assigned(db_session: AsyncSession):
    """Patrol units marked BUSY or OFF_DUTY must not be assigned during auto-dispatch."""
    # 1. Setup Optimization Run and Approved PRP
    opt_run = OptimizationRun(
        shift="MORNING",
        available_patrol_count=2,
        coverage_radius_km=3.0,
        status=OptimizationRunStatus.APPROVED,
    )
    db_session.add(opt_run)
    await db_session.flush()

    prp = PRPLocation(
        optimization_run_id=opt_run.id,
        name="PRP-01",
        location=create_point_geometry(12.9716, 77.5946),
        coverage_radius_km=3.0,
        priority_score=15.0,
        status=PRPStatus.APPROVED,
    )
    db_session.add(prp)

    # 2. Setup Patrol Units: 1 OFF_DUTY, 1 BUSY, 1 AVAILABLE
    unit_off = PatrolUnit(
        call_sign="UNIT-OFF",
        status=PatrolStatus.OFF_DUTY,
        current_location=create_point_geometry(12.9710, 77.5940),
        is_active=True,
    )
    unit_busy = PatrolUnit(
        call_sign="UNIT-BUSY",
        status=PatrolStatus.BUSY,
        current_location=create_point_geometry(12.9712, 77.5942),
        is_active=True,
    )
    unit_avail = PatrolUnit(
        call_sign="UNIT-AVAIL",
        status=PatrolStatus.AVAILABLE,
        current_location=create_point_geometry(12.9715, 77.5945),
        is_active=True,
    )
    db_session.add_all([unit_off, unit_busy, unit_avail])
    await db_session.commit()

    # 3. Trigger auto assignment
    req = AutoAssignmentRequest(optimization_run_id=opt_run.id, shift="MORNING")
    res = await AssignmentService.auto_assign_patrols(db=db_session, payload=req)

    assert res.matched_count == 1
    assert res.assignments[0].call_sign == "UNIT-AVAIL"
    assert res.assignments[0].patrol_unit_id == unit_avail.id


@pytest.mark.asyncio
async def test_one_patrol_not_assigned_twice_simultaneously(db_session: AsyncSession):
    """A patrol unit with an active uncompleted assignment cannot be assigned a second PRP."""
    opt_run = OptimizationRun(
        shift="MORNING",
        available_patrol_count=2,
        coverage_radius_km=3.0,
        status=OptimizationRunStatus.APPROVED,
    )
    db_session.add(opt_run)
    await db_session.flush()

    prp1 = PRPLocation(
        optimization_run_id=opt_run.id,
        name="PRP-01",
        location=create_point_geometry(12.9716, 77.5946),
        priority_score=10.0,
        status=PRPStatus.APPROVED,
    )
    prp2 = PRPLocation(
        optimization_run_id=opt_run.id,
        name="PRP-02",
        location=create_point_geometry(12.9780, 77.6400),
        priority_score=12.0,
        status=PRPStatus.APPROVED,
    )
    unit = PatrolUnit(
        call_sign="UNIT-SINGLE",
        status=PatrolStatus.AVAILABLE,
        current_location=create_point_geometry(12.9716, 77.5946),
        is_active=True,
    )
    db_session.add_all([prp1, prp2, unit])
    await db_session.commit()

    # Manually assign Unit to PRP 1
    man_req = ManualAssignmentRequest(patrol_unit_id=unit.id, prp_location_id=prp1.id, shift="MORNING")
    ass1 = await AssignmentService.manual_assign_patrol(db=db_session, payload=man_req)
    assert ass1.status == AssignmentStatus.ASSIGNED

    # Attempt second concurrent assignment for the same unit -> should fail with ValueError
    man_req2 = ManualAssignmentRequest(patrol_unit_id=unit.id, prp_location_id=prp2.id, shift="MORNING")
    with pytest.raises(ValueError, match="already has an active assignment"):
        await AssignmentService.manual_assign_patrol(db=db_session, payload=man_req2)


@pytest.mark.asyncio
async def test_full_status_transitions_and_synchronization(db_session: AsyncSession):
    """Test lifecycle: ASSIGNED -> ACKNOWLEDGED -> ARRIVED -> COMPLETED, releasing unit to AVAILABLE."""
    # 1. Create Police Officer user
    police_user = User(
        email="officer.smith@safezone.org",
        hashed_password=hash_password("PolicePass123!"),
        full_name="Officer John Smith",
        role=UserRole.POLICE,
        is_active=True,
    )
    db_session.add(police_user)
    await db_session.flush()

    officer = PoliceOfficer(
        user_id=police_user.id,
        badge_number="PO-9999",
        rank="Sergeant",
        department="Central Police Station",
    )
    db_session.add(officer)
    await db_session.flush()

    unit = PatrolUnit(
        call_sign="PATROL-99",
        officer_id=officer.id,
        status=PatrolStatus.AVAILABLE,
        current_location=create_point_geometry(12.9716, 77.5946),
        is_active=True,
    )
    opt_run = OptimizationRun(
        shift="MORNING",
        available_patrol_count=1,
        coverage_radius_km=3.0,
        status=OptimizationRunStatus.APPROVED,
    )
    db_session.add_all([unit, opt_run])
    await db_session.flush()

    prp = PRPLocation(
        optimization_run_id=opt_run.id,
        name="PRP-TEST",
        location=create_point_geometry(12.9720, 77.5950),
        status=PRPStatus.APPROVED,
    )
    db_session.add(prp)
    await db_session.commit()

    # Step 1: Assign (ASSIGNED -> Unit BUSY)
    assignment = await AssignmentService.manual_assign_patrol(
        db=db_session,
        payload=ManualAssignmentRequest(patrol_unit_id=unit.id, prp_location_id=prp.id, shift="MORNING"),
    )
    assert assignment.status == AssignmentStatus.ASSIGNED
    await db_session.refresh(unit)
    assert unit.status == PatrolStatus.BUSY

    # Police officer fetches current active assignment
    current = await AssignmentService.get_police_current_assignment(db=db_session, user_id=police_user.id)
    assert current is not None
    assert current.id == assignment.id

    # Step 2: Officer acknowledges (ACKNOWLEDGED -> Unit EN_ROUTE)
    ack = await AssignmentService.update_assignment_status_by_police(
        db=db_session,
        assignment_id=assignment.id,
        user_id=police_user.id,
        new_status=AssignmentStatus.ACKNOWLEDGED,
    )
    assert ack.status == AssignmentStatus.ACKNOWLEDGED
    assert ack.acknowledged_at is not None
    await db_session.refresh(unit)
    assert unit.status == PatrolStatus.EN_ROUTE

    # Step 3: Officer arrives on scene (ARRIVED -> Unit ON_SCENE)
    arr = await AssignmentService.update_assignment_status_by_police(
        db=db_session,
        assignment_id=assignment.id,
        user_id=police_user.id,
        new_status=AssignmentStatus.ARRIVED,
    )
    assert arr.status == AssignmentStatus.ARRIVED
    assert arr.arrived_at is not None
    await db_session.refresh(unit)
    assert unit.status == PatrolStatus.ON_SCENE

    # Step 4: Officer completes deployment (COMPLETED -> Unit released to AVAILABLE)
    comp = await AssignmentService.update_assignment_status_by_police(
        db=db_session,
        assignment_id=assignment.id,
        user_id=police_user.id,
        new_status=AssignmentStatus.COMPLETED,
    )
    assert comp.status == AssignmentStatus.COMPLETED
    assert comp.completed_at is not None
    await db_session.refresh(unit)
    assert unit.status == PatrolStatus.AVAILABLE

    # Officer has no active uncompleted assignment now
    no_active = await AssignmentService.get_police_current_assignment(db=db_session, user_id=police_user.id)
    assert no_active is None


@pytest.mark.asyncio
async def test_admin_and_police_endpoints_and_rbac(client: AsyncClient, db_session: AsyncSession):
    """Test REST API endpoints and RBAC enforcement for assignments."""
    # Admin User
    admin = User(
        email="admin.dispatch@safezone.org",
        hashed_password=hash_password("AdminSecure123!"),
        full_name="Dispatch Admin",
        role=UserRole.ADMIN,
        is_active=True,
    )
    # Police User
    police_user = User(
        email="police.officer@safezone.org",
        hashed_password=hash_password("PoliceSecure123!"),
        full_name="Officer Jane",
        role=UserRole.POLICE,
        is_active=True,
    )
    # Citizen User
    citizen = User(
        email="citizen.nospy@safezone.org",
        hashed_password=hash_password("CitizenPass123!"),
        full_name="Citizen User",
        role=UserRole.CITIZEN,
        is_active=True,
    )
    db_session.add_all([admin, police_user, citizen])
    await db_session.flush()

    officer = PoliceOfficer(
        user_id=police_user.id,
        badge_number="PO-1234",
        rank="Constable",
        department="North Station",
    )
    db_session.add(officer)
    await db_session.flush()

    unit = PatrolUnit(
        call_sign="DELTA-01",
        officer_id=officer.id,
        status=PatrolStatus.AVAILABLE,
        current_location=create_point_geometry(12.9716, 77.5946),
        is_active=True,
    )
    opt_run = OptimizationRun(
        shift="MORNING",
        available_patrol_count=1,
        coverage_radius_km=3.0,
        status=OptimizationRunStatus.APPROVED,
    )
    db_session.add_all([unit, opt_run])
    await db_session.flush()

    prp = PRPLocation(
        optimization_run_id=opt_run.id,
        name="PRP-NORTH",
        location=create_point_geometry(12.9720, 77.5950),
        status=PRPStatus.APPROVED,
    )
    db_session.add(prp)
    await db_session.commit()

    admin_token = create_access_token(admin.id, admin.role.value, admin.email)
    police_token = create_access_token(police_user.id, police_user.role.value, police_user.email)
    citizen_token = create_access_token(citizen.id, citizen.role.value, citizen.email)

    admin_h = {"Authorization": f"Bearer {admin_token}"}
    police_h = {"Authorization": f"Bearer {police_token}"}
    citizen_h = {"Authorization": f"Bearer {citizen_token}"}

    # 1. Admin triggers auto assignment
    res_auto = await client.post("/api/v1/admin/assignments/auto", json={"shift": "MORNING"}, headers=admin_h)
    assert res_auto.status_code == 201
    auto_data = res_auto.json()
    assert auto_data["matched_count"] == 1
    assignment_id = auto_data["assignments"][0]["id"]

    # 2. Admin lists assignments
    res_list = await client.get("/api/v1/admin/assignments", headers=admin_h)
    assert res_list.status_code == 200
    assert res_list.json()["total"] >= 1

    # 3. Police officer gets current assignment
    res_curr = await client.get("/api/v1/police/assignments/current", headers=police_h)
    assert res_curr.status_code == 200
    curr_data = res_curr.json()
    assert curr_data is not None
    assert curr_data["id"] == assignment_id

    # 4. Police officer acknowledges assignment
    res_ack = await client.post(f"/api/v1/police/assignments/{assignment_id}/acknowledge", headers=police_h)
    assert res_ack.status_code == 200
    assert res_ack.json()["status"] == AssignmentStatus.ACKNOWLEDGED.value

    # 5. Citizen is FORBIDDEN from accessing admin or police assignment routes
    res_cit_admin = await client.get("/api/v1/admin/assignments", headers=citizen_h)
    assert res_cit_admin.status_code == 403

    res_cit_police = await client.get("/api/v1/police/assignments/current", headers=citizen_h)
    assert res_cit_police.status_code == 403
