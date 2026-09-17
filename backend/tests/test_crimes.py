import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.enums import UserRole
from app.models.user import User


async def get_admin_token(db_session: AsyncSession) -> str:
    admin = User(
        email="admin_crime_test@safezone.gov",
        hashed_password=hash_password("AdminPass123!"),
        full_name="Crime System Admin",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return create_access_token(admin.id, admin.role.value, admin.email)


@pytest.mark.asyncio
async def test_create_and_get_crime_incident(client: AsyncClient, db_session: AsyncSession):
    admin_token = await get_admin_token(db_session)

    payload = {
        "incident_number": "CR-TEST-001",
        "category": "Robbery",
        "severity": 4,
        "incident_time": "2026-08-15T14:30:00Z",
        "latitude": 12.971598,
        "longitude": 77.594562,
        "description": "Armed robbery at store",
        "is_active": True,
    }
    response = await client.post(
        "/api/v1/crimes",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["incident_number"] == "CR-TEST-001"
    assert data["category"] == "Robbery"
    assert data["severity"] == 4
    assert abs(data["latitude"] - 12.971598) < 0.0001
    assert abs(data["longitude"] - 77.594562) < 0.0001
    crime_id = data["id"]

    # View crime
    get_res = await client.get(
        f"/api/v1/crimes/{crime_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_res.status_code == 200
    assert get_res.json()["id"] == crime_id


@pytest.mark.asyncio
async def test_invalid_coordinates_rejected(client: AsyncClient, db_session: AsyncSession):
    admin_token = await get_admin_token(db_session)

    payload = {
        "incident_number": "CR-INVALID-COORD",
        "category": "Theft",
        "severity": 2,
        "incident_time": "2026-08-15T14:30:00Z",
        "latitude": 95.0,  # Invalid latitude (> 90)
        "longitude": 77.594562,
    }
    response = await client.post(
        "/api/v1/crimes",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_update_and_deactivate_crime(client: AsyncClient, db_session: AsyncSession):
    admin_token = await get_admin_token(db_session)

    create_res = await client.post(
        "/api/v1/crimes",
        json={
            "incident_number": "CR-UPDATE-001",
            "category": "Theft",
            "severity": 2,
            "incident_time": "2026-08-10T10:00:00Z",
            "latitude": 12.950000,
            "longitude": 77.600000,
            "description": "Initial description",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    crime_id = create_res.json()["id"]

    # Update
    update_res = await client.patch(
        f"/api/v1/crimes/{crime_id}",
        json={
            "category": "Grand Theft Auto",
            "severity": 3,
            "description": "Updated description",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["category"] == "Grand Theft Auto"
    assert update_res.json()["severity"] == 3

    # Deactivate
    deact_res = await client.delete(
        f"/api/v1/crimes/{crime_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert deact_res.status_code == 200

    # Verify inactive
    get_res = await client.get(
        f"/api/v1/crimes/{crime_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_res.json()["is_active"] is False


@pytest.mark.asyncio
async def test_crime_filtering_and_pagination(client: AsyncClient, db_session: AsyncSession):
    admin_token = await get_admin_token(db_session)

    # Insert 5 test incidents
    categories = ["Theft", "Assault", "Theft", "Robbery", "Vandalism"]
    severities = [1, 3, 2, 5, 1]
    times = [
        "2026-08-01T10:00:00Z",
        "2026-08-05T12:00:00Z",
        "2026-08-10T14:00:00Z",
        "2026-08-15T16:00:00Z",
        "2026-08-20T18:00:00Z",
    ]

    for i in range(5):
        await client.post(
            "/api/v1/crimes",
            json={
                "incident_number": f"CR-FILTER-{i+1}",
                "category": categories[i],
                "severity": severities[i],
                "incident_time": times[i],
                "latitude": 12.90 + (i * 0.01),
                "longitude": 77.60 + (i * 0.01),
                "description": f"Incident sample {i+1}",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )

    # 1. Filter by category
    cat_res = await client.get(
        "/api/v1/crimes?category=Theft",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert cat_res.status_code == 200
    assert cat_res.json()["total"] == 2

    # 2. Filter by severity range (min=3, max=5)
    sev_res = await client.get(
        "/api/v1/crimes?min_severity=3&max_severity=5",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert sev_res.status_code == 200
    assert sev_res.json()["total"] == 2

    # 3. Filter by date range
    date_res = await client.get(
        "/api/v1/crimes?start_date=2026-08-04T00:00:00Z&end_date=2026-08-12T00:00:00Z",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert date_res.status_code == 200
    assert date_res.json()["total"] == 2

    # 4. Pagination
    page_res = await client.get(
        "/api/v1/crimes?page=1&page_size=2",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert page_res.status_code == 200
    assert len(page_res.json()["items"]) == 2
    assert page_res.json()["pages"] >= 3


@pytest.mark.asyncio
async def test_csv_import_valid_rows(client: AsyncClient, db_session: AsyncSession):
    admin_token = await get_admin_token(db_session)

    csv_data = (
        "incident_number,category,severity,incident_time,latitude,longitude,description\n"
        "CSV-VAL-001,Burglary,3,2026-08-01T12:00:00Z,12.971598,77.594562,Valid row 1\n"
        "CSV-VAL-002,Homicide,5,2026-08-02T15:30:00Z,12.978350,77.640838,Valid row 2\n"
    )
    files = {"file": ("crimes.csv", csv_data.encode("utf-8"), "text/csv")}
    response = await client.post(
        "/api/v1/crimes/import-csv",
        files=files,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 2
    assert data["imported_count"] == 2
    assert data["failed_count"] == 0
    assert len(data["errors"]) == 0


@pytest.mark.asyncio
async def test_csv_import_mixed_with_invalid_rows(client: AsyncClient, db_session: AsyncSession):
    admin_token = await get_admin_token(db_session)

    # 1 valid row, 1 invalid coords, 1 invalid severity, 1 invalid timestamp, 1 duplicate in csv
    csv_data = (
        "incident_number,category,severity,incident_time,latitude,longitude,description\n"
        "CSV-MIX-001,Assault,4,2026-08-01T12:00:00Z,12.971598,77.594562,Valid row\n"
        "CSV-MIX-002,Theft,2,2026-08-02T15:30:00Z,999.0,77.640838,Invalid Lat\n"
        "CSV-MIX-003,Robbery,99,2026-08-03T18:00:00Z,12.935192,77.624480,Invalid Severity\n"
        "CSV-MIX-004,Vandalism,1,not-a-valid-date,12.927923,77.627107,Invalid Date\n"
        "CSV-MIX-001,Duplicate,2,2026-08-05T20:00:00Z,12.969800,77.749900,Duplicate number\n"
    )
    files = {"file": ("crimes_mixed.csv", csv_data.encode("utf-8"), "text/csv")}
    response = await client.post(
        "/api/v1/crimes/import-csv",
        files=files,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 5
    assert data["imported_count"] == 1  # Only valid row imported
    assert data["failed_count"] == 4
    assert len(data["errors"]) == 4

    # Verify that the valid row was actually persisted in database
    get_res = await client.get(
        "/api/v1/crimes?search=CSV-MIX-001",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert get_res.status_code == 200
    assert get_res.json()["total"] == 1
