import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.enums import UserRole
from app.models.user import User


async def setup_admin_and_citizen(db_session: AsyncSession):
    admin = User(
        email="admin_hp_test@safezone.gov",
        hashed_password=hash_password("AdminPass123!"),
        full_name="Admin HP Supervisor",
        role=UserRole.ADMIN,
        is_active=True,
    )
    citizen = User(
        email="citizen_hp_test@safezone.gov",
        hashed_password=hash_password("CitizenPass123!"),
        full_name="Citizen Tester",
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
async def test_admin_crud_and_permissions(client: AsyncClient, db_session: AsyncSession):
    admin_token, citizen_token = await setup_admin_and_citizen(db_session)

    payload = {
        "name": "Central General Hospital",
        "category": "HOSPITAL",
        "latitude": 12.971598,
        "longitude": 77.594562,
        "address": "123 Health Ave",
        "contact_number": "+1234567890",
        "is_verified": True,
        "is_active": True,
    }

    # 1. Non-admin forbidden from creating
    citizen_create = await client.post(
        "/api/v1/help-points",
        json=payload,
        headers={"Authorization": f"Bearer {citizen_token}"},
    )
    assert citizen_create.status_code == 403

    # 2. Admin successfully creates
    admin_create = await client.post(
        "/api/v1/help-points",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_create.status_code == 201
    hp_id = admin_create.json()["id"]

    # 3. Admin updates details
    update_res = await client.patch(
        f"/api/v1/help-points/{hp_id}",
        json={"name": "Central Metropolitan Hospital"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Central Metropolitan Hospital"

    # 4. Admin toggles verification
    verif_res = await client.patch(
        f"/api/v1/help-points/{hp_id}/verification",
        json={"is_verified": False},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert verif_res.status_code == 200
    assert verif_res.json()["is_verified"] is False


@pytest.mark.asyncio
async def test_citizen_filters_unverified_and_inactive_points(client: AsyncClient, db_session: AsyncSession):
    admin_token, citizen_token = await setup_admin_and_citizen(db_session)

    # Create 4 points:
    # 1: Verified + Active (Should be visible to Citizen)
    # 2: Unverified + Active (Should be hidden from Citizen)
    # 3: Verified + Inactive (Should be hidden from Citizen)
    # 4: Unverified + Inactive (Should be hidden from Citizen)
    points = [
        {"name": "Visible Facility", "category": "POLICE_STATION", "latitude": 12.971, "longitude": 77.594, "is_verified": True, "is_active": True},
        {"name": "Unverified Facility", "category": "SHELTER", "latitude": 12.972, "longitude": 77.595, "is_verified": False, "is_active": True},
        {"name": "Inactive Facility", "category": "HOSPITAL", "latitude": 12.973, "longitude": 77.596, "is_verified": True, "is_active": False},
        {"name": "Hidden Facility", "category": "HELP_DESK", "latitude": 12.974, "longitude": 77.597, "is_verified": False, "is_active": False},
    ]

    for p in points:
        await client.post(
            "/api/v1/help-points",
            json=p,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    # Citizen list public endpoint
    public_res = await client.get(
        "/api/v1/help-points/public",
        headers={"Authorization": f"Bearer {citizen_token}"},
    )
    assert public_res.status_code == 200
    public_data = public_res.json()
    assert public_data["total"] == 1
    assert public_data["items"][0]["name"] == "Visible Facility"

    # Admin list endpoint sees all 4
    admin_res = await client.get(
        "/api/v1/help-points",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_res.status_code == 200
    assert admin_res.json()["total"] == 4


@pytest.mark.asyncio
async def test_nearby_spatial_query(client: AsyncClient, db_session: AsyncSession):
    admin_token, citizen_token = await setup_admin_and_citizen(db_session)

    # Origin coordinate: (12.971598, 77.594562) - Center Bangalore
    # Point 1: ~1.1 km away (12.980000, 77.600000) - Verified + Active
    # Point 2: ~3.5 km away (13.000000, 77.610000) - Verified + Active
    # Point 3: ~15 km away (13.100000, 77.650000) - Verified + Active (Out of 5km radius)
    # Point 4: ~0.5 km away (12.975000, 77.595000) - Unverified (Should be excluded)

    test_hps = [
        {"name": "Nearby Hospital (1.1km)", "category": "HOSPITAL", "latitude": 12.980000, "longitude": 77.600000, "is_verified": True, "is_active": True},
        {"name": "Nearby Police (3.5km)", "category": "POLICE_STATION", "latitude": 13.000000, "longitude": 77.610000, "is_verified": True, "is_active": True},
        {"name": "Far Shelter (15km)", "category": "SHELTER", "latitude": 13.100000, "longitude": 77.650000, "is_verified": True, "is_active": True},
        {"name": "Nearby Unverified Desk", "category": "HELP_DESK", "latitude": 12.975000, "longitude": 77.595000, "is_verified": False, "is_active": True},
    ]

    for hp in test_hps:
        await client.post(
            "/api/v1/help-points",
            json=hp,
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    # Query with 5.0 km radius from center
    nearby_res = await client.get(
        "/api/v1/help-points/nearby?latitude=12.971598&longitude=77.594562&radius_km=5.0",
        headers={"Authorization": f"Bearer {citizen_token}"},
    )
    assert nearby_res.status_code == 200
    items = nearby_res.json()

    # Must contain exactly the 2 verified points within 5km, sorted closest first
    assert len(items) == 2
    assert items[0]["name"] == "Nearby Hospital (1.1km)"
    assert items[0]["distance_km"] < items[1]["distance_km"]
    assert items[1]["name"] == "Nearby Police (3.5km)"


@pytest.mark.asyncio
async def test_help_points_csv_import(client: AsyncClient, db_session: AsyncSession):
    admin_token, citizen_token = await setup_admin_and_citizen(db_session)

    csv_data = (
        "name,category,latitude,longitude,address,contact_number,is_verified,is_active\n"
        "City Health Clinic,HOSPITAL,12.971598,77.594562,Clinic Road,+111222333,true,true\n"
        "East Police Post,POLICE_STATION,12.978000,77.640000,East Gate,+444555666,true,true\n"
        "Invalid Cat Facility,NOT_A_CATEGORY,12.935000,77.620000,Some Road,+777888999,true,true\n"
        "Invalid Coords Shelter,SHELTER,999.0,77.585000,Bad Lat Road,+000111222,true,true\n"
    )

    files = {"file": ("help_points.csv", csv_data.encode("utf-8"), "text/csv")}

    # Non-admin forbidden
    unauth_res = await client.post(
        "/api/v1/help-points/import-csv",
        files=files,
        headers={"Authorization": f"Bearer {citizen_token}"},
    )
    assert unauth_res.status_code == 403

    # Admin imports
    files = {"file": ("help_points.csv", csv_data.encode("utf-8"), "text/csv")}
    admin_res = await client.post(
        "/api/v1/help-points/import-csv",
        files=files,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_res.status_code == 200
    summary = admin_res.json()
    assert summary["total_rows"] == 4
    assert summary["imported_count"] == 2
    assert summary["failed_count"] == 2
    assert len(summary["errors"]) == 2
