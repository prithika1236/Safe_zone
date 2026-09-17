import pytest
import pytest_asyncio
from geoalchemy2.functions import ST_GeomFromText
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.enums import PatrolStatus, SOSStatus, UserRole
from app.models.patrol import PatrolUnit
from app.models.user import PoliceOfficer, User
from app.services.crime_service import create_point_geometry


@pytest_asyncio.fixture
async def citizen_auth(db_session: AsyncSession):
    user = User(
        email="citizen_emergency@example.com",
        hashed_password=hash_password("citizen_pass123"),
        full_name="Emergency Citizen",
        phone_number="+91 9111122222",
        role=UserRole.CITIZEN,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token(
        subject=user.id,
        role=user.role.value,
        email=user.email,
    )
    return {"Authorization": f"Bearer {token}", "user": user}


@pytest_asyncio.fixture
async def police_fleet_auth(db_session: AsyncSession):
    user = User(
        email="officer_dispatch@police.gov",
        hashed_password=hash_password("police_pass123"),
        full_name="Officer Dispatcher",
        phone_number="+91 9888877777",
        role=UserRole.POLICE,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    officer = PoliceOfficer(
        user_id=user.id,
        badge_number="DSP-7701",
        rank="SERGEANT",
        is_on_duty=True,
    )
    db_session.add(officer)
    await db_session.flush()

    patrol = PatrolUnit(
        call_sign="PATROL-ALPHA",
        officer_id=officer.id,
        status=PatrolStatus.AVAILABLE,
        is_active=True,
        current_location=create_point_geometry(12.9720, 77.5950),
    )
    db_session.add(patrol)
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(patrol)

    token = create_access_token(
        subject=user.id,
        role=user.role.value,
        email=user.email,
    )
    return {"Authorization": f"Bearer {token}", "user": user, "patrol": patrol}


@pytest_asyncio.fixture
async def admin_auth_headers(db_session: AsyncSession):
    user = User(
        email="admin_dispatch@safezone.gov",
        hashed_password=hash_password("admin_pass123"),
        full_name="Admin Dispatch Monitor",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token(
        subject=user.id,
        role=user.role.value,
        email=user.email,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_citizen_trigger_sos_with_available_patrol(
    client: AsyncClient,
    citizen_auth,
    police_fleet_auth,
    db_session: AsyncSession,
):
    headers = {"Authorization": citizen_auth["Authorization"]}
    payload = {
        "latitude": 12.9716,
        "longitude": 77.5946,
        "notes": "Emergency immediate help required",
    }

    res = await client.post("/api/v1/sos/trigger", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()

    assert data["status"] == "ASSIGNED"
    assert data["patrol_assigned"] is True
    assert data["patrol_call_sign"] == "PATROL-ALPHA"
    assert data["distance_meters"] is not None

    # Verify patrol status transitioned to BUSY in DB
    patrol = police_fleet_auth["patrol"]
    await db_session.refresh(patrol)
    assert patrol.status == PatrolStatus.BUSY


@pytest.mark.asyncio
async def test_citizen_trigger_sos_without_available_patrol(
    client: AsyncClient,
    citizen_auth,
    db_session: AsyncSession,
):
    # Ensure no available patrols exist
    headers = {"Authorization": citizen_auth["Authorization"]}
    payload = {
        "latitude": 12.9716,
        "longitude": 77.5946,
    }

    res = await client.post("/api/v1/sos/trigger", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()

    assert data["status"] == "PENDING"
    assert data["patrol_assigned"] is False
    assert data["patrol_call_sign"] == None


@pytest.mark.asyncio
async def test_invalid_coordinates_rejected(
    client: AsyncClient,
    citizen_auth,
):
    headers = {"Authorization": citizen_auth["Authorization"]}
    payload = {
        "latitude": 120.0,  # Invalid latitude > 90
        "longitude": 77.5946,
    }
    res = await client.post("/api/v1/sos/trigger", json=payload, headers=headers)
    assert res.status_code in [400, 422]


@pytest.mark.asyncio
async def test_full_police_sos_state_machine(
    client: AsyncClient,
    citizen_auth,
    police_fleet_auth,
    db_session: AsyncSession,
):
    cit_headers = {"Authorization": citizen_auth["Authorization"]}
    pol_headers = {"Authorization": police_fleet_auth["Authorization"]}

    # 1. Citizen triggers SOS -> ASSIGNED
    trigger_res = await client.post(
        "/api/v1/sos/trigger",
        json={"latitude": 12.9716, "longitude": 77.5946},
        headers=cit_headers,
    )
    assert trigger_res.status_code == 201
    sos_id = trigger_res.json()["id"]

    # 2. Police gets active SOS
    pol_active = await client.get("/api/v1/police/sos/active", headers=pol_headers)
    assert pol_active.status_code == 200
    assert pol_active.json()["id"] == sos_id
    assert pol_active.json()["status"] == "ASSIGNED"

    # 3. Police accepts SOS -> ACCEPTED
    accept_res = await client.post(
        f"/api/v1/police/sos/{sos_id}/accept", headers=pol_headers
    )
    assert accept_res.status_code == 200
    assert accept_res.json()["status"] == "ACCEPTED"
    assert accept_res.json()["accepted_time"] is not None

    # 4. Police sets EN_ROUTE -> EN_ROUTE
    en_route_res = await client.post(
        f"/api/v1/police/sos/{sos_id}/en-route", headers=pol_headers
    )
    assert en_route_res.status_code == 200
    assert en_route_res.json()["status"] == "EN_ROUTE"

    # 5. Police sets ARRIVED -> ARRIVED
    arrived_res = await client.post(
        f"/api/v1/police/sos/{sos_id}/arrived", headers=pol_headers
    )
    assert arrived_res.status_code == 200
    assert arrived_res.json()["status"] == "ARRIVED"

    # 6. Police resolves incident -> RESOLVED
    resolve_res = await client.post(
        f"/api/v1/police/sos/{sos_id}/resolve",
        json={"resolution_notes": "Citizen escorted to safety, suspect fled."},
        headers=pol_headers,
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "RESOLVED"

    # 7. Patrol unit is released back to AVAILABLE in DB
    patrol = police_fleet_auth["patrol"]
    await db_session.refresh(patrol)
    assert patrol.status == PatrolStatus.AVAILABLE


@pytest.mark.asyncio
async def test_duplicate_accept_and_invalid_transitions(
    client: AsyncClient,
    citizen_auth,
    police_fleet_auth,
):
    cit_headers = {"Authorization": citizen_auth["Authorization"]}
    pol_headers = {"Authorization": police_fleet_auth["Authorization"]}

    # Citizen triggers SOS
    res = await client.post(
        "/api/v1/sos/trigger",
        json={"latitude": 12.9716, "longitude": 77.5946},
        headers=cit_headers,
    )
    sos_id = res.json()["id"]

    # Accept once -> OK
    acc = await client.post(f"/api/v1/police/sos/{sos_id}/accept", headers=pol_headers)
    assert acc.status_code == 200

    # Accept twice -> 400 BAD REQUEST
    acc2 = await client.post(f"/api/v1/police/sos/{sos_id}/accept", headers=pol_headers)
    assert acc2.status_code == 400

    # Attempt to resolve directly before arriving -> 400 BAD REQUEST
    res_direct = await client.post(f"/api/v1/police/sos/{sos_id}/resolve", headers=pol_headers)
    assert res_direct.status_code == 400


@pytest.mark.asyncio
async def test_citizen_cancellation_releases_patrol(
    client: AsyncClient,
    citizen_auth,
    police_fleet_auth,
    db_session: AsyncSession,
):
    cit_headers = {"Authorization": citizen_auth["Authorization"]}

    # Trigger SOS
    res = await client.post(
        "/api/v1/sos/trigger",
        json={"latitude": 12.9716, "longitude": 77.5946},
        headers=cit_headers,
    )
    sos_id = res.json()["id"]

    # Patrol unit is currently BUSY
    patrol = police_fleet_auth["patrol"]
    await db_session.refresh(patrol)
    assert patrol.status == PatrolStatus.BUSY

    # Citizen cancels SOS
    cancel_res = await client.post(f"/api/v1/sos/{sos_id}/cancel", headers=cit_headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"

    # Patrol unit is released back to AVAILABLE
    await db_session.refresh(patrol)
    assert patrol.status == PatrolStatus.AVAILABLE


@pytest.mark.asyncio
async def test_admin_list_sos_alerts(
    client: AsyncClient,
    admin_auth_headers,
    citizen_auth,
):
    # Citizen triggers SOS
    cit_headers = {"Authorization": citizen_auth["Authorization"]}
    await client.post(
        "/api/v1/sos/trigger",
        json={"latitude": 12.9716, "longitude": 77.5946},
        headers=cit_headers,
    )

    # Admin queries SOS alerts
    res = await client.get("/api/v1/admin/sos", headers=admin_auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1
