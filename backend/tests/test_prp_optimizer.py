from datetime import datetime, timedelta, timezone
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.crime import CrimeIncident
from app.models.enums import OptimizationRunStatus, PRPStatus, UserRole
from app.models.user import User
from app.optimization.candidate_generator import (
    CandidateGenerationConfig,
    CandidatePRP,
    generate_prp_candidates,
)
from app.optimization.coverage import CandidateLocation, DemandPoint, build_coverage_matrix
from app.optimization.prp_optimizer import (
    PRPOptimizationResult,
    optimize_prp_coverage,
)
from app.schemas.optimization import OptimizationRunRequest
from app.services.crime_service import create_point_geometry
from app.services.optimization_service import OptimizationService


@pytest.fixture
def optimization_scenario():
    """Create a controlled scenario with 4 demand points and 3 candidates."""
    # Candidates
    cands = [
        CandidateLocation(id="C1", latitude=12.9716, longitude=77.5946, name="Candidate-Central"),
        CandidateLocation(id="C2", latitude=12.9780, longitude=77.6400, name="Candidate-East"),
        CandidateLocation(id="C3", latitude=12.9300, longitude=77.5800, name="Candidate-South"),
    ]

    # Demand Points:
    # D1 (close to C1): weight 8.0
    # D2 (between C1 and C2, within 3km of both): weight 5.0
    # D3 (close to C2): weight 2.0
    # D4 (close to C3): weight 1.0
    demands = [
        DemandPoint(id=1, latitude=12.9720, longitude=77.5950, weight=8.0, category="Armed Robbery"),
        DemandPoint(id=2, latitude=12.9750, longitude=77.6150, weight=5.0, category="Robbery"),
        DemandPoint(id=3, latitude=12.9785, longitude=77.6405, weight=2.0, category="Theft"),
        DemandPoint(id=4, latitude=12.9310, longitude=77.5810, weight=1.0, category="Vandalism"),
    ]
    return cands, demands


def test_patrol_limit_constraint(optimization_scenario):
    """Solver must strictly respect available patrol capacity limit (P)."""
    cands, demands = optimization_scenario

    # Available patrols = 1
    res_1 = optimize_prp_coverage(cands, demands, available_patrol_count=1, coverage_radius_km=3.0)
    assert res_1.selected_count <= 1
    assert len(res_1.selected_prps) <= 1

    # Available patrols = 2
    res_2 = optimize_prp_coverage(cands, demands, available_patrol_count=2, coverage_radius_km=3.0)
    assert res_2.selected_count <= 2
    assert len(res_2.selected_prps) <= 2


def test_high_risk_preference(optimization_scenario):
    """When budget is constrained (P=1), solver chooses candidate covering highest weighted risk."""
    cands, demands = optimization_scenario

    # C1 covers D1 (weight 8.0) and D2 (weight 5.0) = 13.0
    # C2 covers D2 (weight 5.0) and D3 (weight 2.0) = 7.0
    # C3 covers D4 (weight 1.0) = 1.0
    res = optimize_prp_coverage(cands, demands, available_patrol_count=1, coverage_radius_km=3.0)

    assert res.selected_count == 1
    assert res.selected_prps[0].candidate_id == "C1"
    assert res.covered_demand_risk == 13.0


def test_overlap_non_double_counting(optimization_scenario):
    """Demand point covered by multiple selected PRPs is counted only ONCE in covered_demand_risk."""
    cands, demands = optimization_scenario

    # If both C1 and C2 are selected, both cover D2 (weight 5.0)
    # Total unique risk = D1(8.0) + D2(5.0) + D3(2.0) = 15.0
    res = optimize_prp_coverage(cands, demands, available_patrol_count=2, coverage_radius_km=3.0)

    assert res.selected_count == 2
    selected_ids = {p.candidate_id for p in res.selected_prps}
    assert "C1" in selected_ids
    assert "C2" in selected_ids

    # Covered demand risk must be strictly 15.0 (NOT 15.0 + 5.0 = 20.0)
    assert res.covered_demand_risk == 15.0
    assert res.total_demand_risk == 16.0  # D1(8) + D2(5) + D3(2) + D4(1)
    assert res.coverage_percentage == round((15.0 / 16.0) * 100.0, 2)


def test_configurable_coverage_radius(optimization_scenario):
    """Larger radius expands coverage scope compared to smaller radius."""
    cands, demands = optimization_scenario

    # Small radius (1km) - D2 is ~2.5km from C1 and C2 so it won't be covered
    res_small = optimize_prp_coverage(cands, demands, available_patrol_count=1, coverage_radius_km=1.0)
    # Large radius (5km) - C1 can reach D1, D2, and possibly further
    res_large = optimize_prp_coverage(cands, demands, available_patrol_count=1, coverage_radius_km=5.0)

    assert res_large.covered_demand_risk >= res_small.covered_demand_risk


def test_zero_patrols_and_empty_inputs():
    """Zero available patrols or empty candidates handled safely."""
    demands = [DemandPoint(id=1, latitude=12.97, longitude=77.59, weight=5.0)]
    cands = [CandidateLocation(id="C1", latitude=12.97, longitude=77.59)]

    # Zero patrols
    res_zero = optimize_prp_coverage(cands, demands, available_patrol_count=0)
    assert res_zero.selected_count == 0
    assert res_zero.covered_demand_risk == 0.0
    assert res_zero.coverage_percentage == 0.0

    # Empty candidates
    res_empty_cands = optimize_prp_coverage([], demands, available_patrol_count=2)
    assert res_empty_cands.selected_count == 0

    # Empty demands
    res_empty_demands = optimize_prp_coverage(cands, [], available_patrol_count=2)
    assert res_empty_demands.covered_demand_risk == 0.0
    assert res_empty_demands.coverage_percentage == 100.0


def test_deterministic_solver_behavior(optimization_scenario):
    """Repeated solver invocations produce identical selected PRPs and coverage metrics."""
    cands, demands = optimization_scenario

    run_1 = optimize_prp_coverage(cands, demands, available_patrol_count=2, coverage_radius_km=3.0)
    run_2 = optimize_prp_coverage(cands, demands, available_patrol_count=2, coverage_radius_km=3.0)

    assert run_1.selected_count == run_2.selected_count
    assert run_1.covered_demand_risk == run_2.covered_demand_risk
    assert [p.candidate_id for p in run_1.selected_prps] == [p.candidate_id for p in run_2.selected_prps]


@pytest.mark.asyncio
async def test_optimization_service_db_persistence_and_approval(db_session: AsyncSession):
    """Test full OptimizationService database run persistence and approval workflow."""
    now = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)

    # Seed crime data
    c1 = CrimeIncident(
        incident_number="OPT-CR-01",
        category="Robbery",
        severity=5,
        incident_time=now - timedelta(days=1),
        location=create_point_geometry(12.9716, 77.5946),
        is_active=True,
    )
    c2 = CrimeIncident(
        incident_number="OPT-CR-02",
        category="Assault",
        severity=4,
        incident_time=now - timedelta(days=2),
        location=create_point_geometry(12.9720, 77.5950),
        is_active=True,
    )
    db_session.add_all([c1, c2])
    await db_session.commit()

    # 1. Preview mode (no DB record created)
    req = OptimizationRunRequest(
        shift="MORNING",
        available_patrol_count=2,
        coverage_radius_km=3.0,
    )
    preview = await OptimizationService.preview_optimization(db=db_session, payload=req)
    assert preview.run_id is None
    assert preview.selected_count >= 1

    # 2. Execution mode (persists OptimizationRun and PRPLocations in RECOMMENDED status)
    result = await OptimizationService.run_optimization(db=db_session, payload=req)
    assert result.run_id is not None
    assert result.selected_count >= 1
    assert result.selected_prps[0].status == PRPStatus.RECOMMENDED.value

    # 3. Retrieve run details
    fetched_run = await OptimizationService.get_optimization_run(db=db_session, run_id=result.run_id)
    assert fetched_run is not None
    assert fetched_run.run_id == result.run_id

    # 4. Approve run (transitions status to APPROVED)
    approved_run = await OptimizationService.approve_optimization_run(db=db_session, run_id=result.run_id)
    assert approved_run is not None
    assert approved_run.selected_prps[0].status == PRPStatus.APPROVED.value

    # 5. List PRPs
    prps, total, _ = await OptimizationService.list_prp_locations(db=db_session, status=PRPStatus.APPROVED)
    assert total >= 1
    assert prps[0].status == PRPStatus.APPROVED


@pytest.mark.asyncio
async def test_admin_optimization_endpoints_and_rbac(client: AsyncClient, db_session: AsyncSession):
    """Test REST endpoints: ADMIN allowed, CITIZEN forbidden."""
    # Create Admin User
    admin = User(
        email="admin.opt@safezone.org",
        hashed_password=hash_password("AdminSecure123!"),
        full_name="Admin Optimizer",
        role=UserRole.ADMIN,
        is_active=True,
    )
    # Create Citizen User
    citizen = User(
        email="citizen.opt@safezone.org",
        hashed_password=hash_password("CitizenPass123!"),
        full_name="Citizen User",
        role=UserRole.CITIZEN,
        is_active=True,
    )
    db_session.add_all([admin, citizen])
    await db_session.commit()
    await db_session.refresh(admin)
    await db_session.refresh(citizen)

    admin_token = create_access_token(admin.id, admin.role.value, admin.email)
    citizen_token = create_access_token(citizen.id, citizen.role.value, citizen.email)

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    citizen_headers = {"Authorization": f"Bearer {citizen_token}"}

    payload = {
        "shift": "EVENING",
        "available_patrol_count": 3,
        "coverage_radius_km": 3.0,
    }

    # 1. Admin can preview
    res_prev = await client.post("/api/v1/admin/optimization/preview", json=payload, headers=admin_headers)
    assert res_prev.status_code == 200

    # 2. Admin can run optimization
    res_run = await client.post("/api/v1/admin/optimization/run", json=payload, headers=admin_headers)
    assert res_run.status_code == 201
    run_data = res_run.json()
    run_id = run_data["run_id"]
    assert run_id is not None

    # 3. Admin can approve run
    res_app = await client.post(f"/api/v1/admin/optimization/runs/{run_id}/approve", headers=admin_headers)
    assert res_app.status_code == 200

    # 4. Admin can list PRPs
    res_prps = await client.get("/api/v1/admin/optimization/prps", headers=admin_headers)
    assert res_prps.status_code == 200

    # 5. Citizen is strictly FORBIDDEN from accessing exact PRPs or running optimization
    res_cit_run = await client.post("/api/v1/admin/optimization/run", json=payload, headers=citizen_headers)
    assert res_cit_run.status_code == 403

    res_cit_prps = await client.get("/api/v1/admin/optimization/prps", headers=citizen_headers)
    assert res_cit_prps.status_code == 403
