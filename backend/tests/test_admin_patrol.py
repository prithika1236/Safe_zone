import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.enums import PatrolStatus, UserRole
from app.models.user import User


async def setup_admin_and_citizen(db_session: AsyncSession):
    admin = User(
        email="admin_patrol_test@safezone.gov",
        hashed_password=hash_password("AdminPass123!"),
        full_name="Admin Supervisor",
        role=UserRole.ADMIN,
        is_active=True,
    )
    citizen = User(
        email="citizen_patrol_test@safezone.gov",
        hashed_password=hash_password("CitizenPass123!"),
        full_name="Regular Citizen",
        role=UserRole.CITIZEN,
        is_active=True,
    )
    db_session.add_all([admin, citizen])
    await db_session.commit()
    await db_session.refresh(admin)
    await db_session.refresh(citizen)

    admin_token = create_access_token(admin.id, admin.role.value, admin.email)
    citizen_token = create_access_token(citizen.id, citizen.role.value, citizen.email)
    return admin_token, citizen_token


@pytest.mark.asyncio
async def test_admin_create_police_officer_success(client: AsyncClient, db_session: AsyncSession):
    admin_token, _ = await setup_admin_and_citizen(db_session)

    payload = {
        "email": "officer101@safezone.gov",
        "password": "OfficerSecurePass123!",
        "full_name": "James Gordon",
        "phone_number": "+1987654321",
        "badge_number": "BADGE-101",
        "rank": "Sergeant",
        "department": "Metropolitan Central",
        "is_on_duty": True,
    }
    response = await client.post(
        "/api/v1/admin/officers",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["badge_number"] == "BADGE-101"
    assert data["full_name"] == "James Gordon"
    assert data["rank"] == "Sergeant"
    assert data["department"] == "Metropolitan Central"
    assert data["is_on_duty"] is True
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_non_admin_cannot_create_police_officer(client: AsyncClient, db_session: AsyncSession):
    _, citizen_token = await setup_admin_and_citizen(db_session)

    payload = {
        "email": "unauthorized_officer@safezone.gov",
        "password": "Password123!",
        "full_name": "Unauthorized Officer",
        "badge_number": "BADGE-999",
    }
    response = await client.post(
        "/api/v1/admin/officers",
        json=payload,
        headers={"Authorization": f"Bearer {citizen_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_duplicate_officer_badge_and_email_rejected(client: AsyncClient, db_session: AsyncSession):
    admin_token, _ = await setup_admin_and_citizen(db_session)

    payload1 = {
        "email": "officer_unique@safezone.gov",
        "password": "Password123!",
        "full_name": "Officer One",
        "badge_number": "BADGE-UNIQUE",
    }
    res1 = await client.post(
        "/api/v1/admin/officers",
        json=payload1,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res1.status_code == 201

    # Duplicate badge
    payload2 = {
        "email": "officer_other@safezone.gov",
        "password": "Password123!",
        "full_name": "Officer Two",
        "badge_number": "BADGE-UNIQUE",
    }
    res2 = await client.post(
        "/api/v1/admin/officers",
        json=payload2,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"]


@pytest.mark.asyncio
async def test_list_and_update_police_officers(client: AsyncClient, db_session: AsyncSession):
    admin_token, _ = await setup_admin_and_citizen(db_session)

    # Create two officers
    res_off1 = await client.post(
        "/api/v1/admin/officers",
        json={
            "email": "officer_list_1@safezone.gov",
            "password": "Password123!",
            "full_name": "Officer List 1",
            "badge_number": "BADGE-L1",
            "is_on_duty": True,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    officer1_id = res_off1.json()["id"]

    await client.post(
        "/api/v1/admin/officers",
        json={
            "email": "officer_list_2@safezone.gov",
            "password": "Password123!",
            "full_name": "Officer List 2",
            "badge_number": "BADGE-L2",
            "is_on_duty": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # List all
    list_res = await client.get(
        "/api/v1/admin/officers?page=1&page_size=10",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 2
    assert len(list_data["items"]) >= 2

    # Filter on-duty
    on_duty_res = await client.get(
        "/api/v1/admin/officers?is_on_duty=true",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert on_duty_res.status_code == 200
    for item in on_duty_res.json()["items"]:
        assert item["is_on_duty"] is True

    # Update officer 1
    update_res = await client.patch(
        f"/api/v1/admin/officers/{officer1_id}",
        json={
            "rank": "Lieutenant",
            "department": "Traffic & Emergency",
            "is_on_duty": False,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["rank"] == "Lieutenant"
    assert updated_data["department"] == "Traffic & Emergency"
    assert updated_data["is_on_duty"] is False


@pytest.mark.asyncio
async def test_patrol_unit_crud_and_status_management(client: AsyncClient, db_session: AsyncSession):
    admin_token, _ = await setup_admin_and_citizen(db_session)

    # 1. Create an officer
    off_res = await client.post(
        "/api/v1/admin/officers",
        json={
            "email": "patrol_officer@safezone.gov",
            "password": "Password123!",
            "full_name": "Patrol Officer",
            "badge_number": "BADGE-PATROL-1",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    officer_id = off_res.json()["id"]

    # 2. Create PatrolUnit
    create_patrol_res = await client.post(
        "/api/v1/admin/patrols",
        json={
            "call_sign": "DELTA-01",
            "officer_id": officer_id,
            "status": "AVAILABLE",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_patrol_res.status_code == 201
    unit_data = create_patrol_res.json()
    unit_id = unit_data["id"]
    assert unit_data["call_sign"] == "DELTA-01"
    assert unit_data["officer_badge"] == "BADGE-PATROL-1"
    assert unit_data["status"] == "AVAILABLE"

    # 3. Duplicate call_sign rejection
    dup_res = await client.post(
        "/api/v1/admin/patrols",
        json={"call_sign": "DELTA-01"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert dup_res.status_code == 400
    assert "already exists" in dup_res.json()["detail"]

    # 4. Update patrol status
    status_res = await client.patch(
        f"/api/v1/admin/patrols/{unit_id}/status",
        json={"status": "BUSY"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "BUSY"

    # 5. List patrol units
    list_res = await client.get(
        "/api/v1/admin/patrols?status=BUSY",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert list_res.status_code == 200
    assert len(list_res.json()["items"]) >= 1

    # 6. Operational summary
    summary_res = await client.get(
        "/api/v1/admin/operations/summary",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["total_officers"] >= 1
    assert summary["total_patrol_units"] >= 1
    assert summary["busy_patrol_units"] >= 1
