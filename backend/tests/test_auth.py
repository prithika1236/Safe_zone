import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.models.enums import UserRole
from app.models.user import User


@pytest.mark.asyncio
async def test_password_hashing():
    raw = "superSecretPassword123!"
    hashed = hash_password(raw)
    assert hashed != raw
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    assert verify_password(raw, hashed) is True
    assert verify_password("wrongPassword", hashed) is False


@pytest.mark.asyncio
async def test_citizen_registration_success(client: AsyncClient):
    payload = {
        "email": "citizen@example.com",
        "password": "StrongPassword123!",
        "full_name": "John Citizen",
        "phone_number": "+1234567890",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "citizen@example.com"
    assert data["full_name"] == "John Citizen"
    assert data["role"] == "CITIZEN"
    assert "hashed_password" not in data
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_duplicate_email_registration_rejected(client: AsyncClient):
    payload = {
        "email": "duplicate@example.com",
        "password": "Password12345!",
        "full_name": "First User",
    }
    res1 = await client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = await client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"]


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    # Register first
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "loginuser@example.com",
            "password": "SecurePassword123!",
            "full_name": "Login User",
        },
    )

    login_payload = {
        "email": "loginuser@example.com",
        "password": "SecurePassword123!",
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "loginuser@example.com"
    assert data["user"]["role"] == "CITIZEN"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "wrongpwd@example.com",
            "password": "CorrectPassword123!",
            "full_name": "Wrong Pwd User",
        },
    )

    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "wrongpwd@example.com",
            "password": "WrongPassword999!",
        },
    )
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_current_user_profile(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "me@example.com",
            "password": "MyPassword123!",
            "full_name": "Profile Tester",
        },
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "me@example.com", "password": "MyPassword123!"},
    )
    token = login_res.json()["access_token"]

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"
    assert data["full_name"] == "Profile Tester"


@pytest.mark.asyncio
async def test_invalid_token_rejected(client: AsyncClient):
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.jwt.token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_inactive_account_rejected(client: AsyncClient, db_session: AsyncSession):
    # Insert inactive user
    inactive_user = User(
        email="inactive@example.com",
        hashed_password=hash_password("Password123!"),
        full_name="Inactive User",
        role=UserRole.CITIZEN,
        is_active=False,
    )
    db_session.add(inactive_user)
    await db_session.commit()
    await db_session.refresh(inactive_user)

    # Attempt login
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "inactive@example.com", "password": "Password123!"},
    )
    assert login_res.status_code == 403
    assert "Inactive user account" in login_res.json()["detail"]

    # Attempt token access
    token = create_access_token(inactive_user.id, inactive_user.role.value, inactive_user.email)
    me_res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 403


@pytest.mark.asyncio
async def test_rbac_dependencies(client: AsyncClient, db_session: AsyncSession):
    # Create an Admin user, Police user, and Citizen user
    admin_user = User(
        email="admin@safezone.gov",
        hashed_password=hash_password("AdminPass123!"),
        full_name="Chief Admin",
        role=UserRole.ADMIN,
        is_active=True,
    )
    police_user = User(
        email="officer@safezone.gov",
        hashed_password=hash_password("PolicePass123!"),
        full_name="Officer Smith",
        role=UserRole.POLICE,
        is_active=True,
    )
    citizen_user = User(
        email="citizen_rbac@safezone.gov",
        hashed_password=hash_password("CitizenPass123!"),
        full_name="Jane Citizen",
        role=UserRole.CITIZEN,
        is_active=True,
    )
    db_session.add_all([admin_user, police_user, citizen_user])
    await db_session.commit()
    await db_session.refresh(admin_user)
    await db_session.refresh(police_user)
    await db_session.refresh(citizen_user)

    admin_token = create_access_token(admin_user.id, admin_user.role.value, admin_user.email)
    police_token = create_access_token(police_user.id, police_user.role.value, police_user.email)
    citizen_token = create_access_token(citizen_user.id, citizen_user.role.value, citizen_user.email)

    from fastapi import Depends
    from app.api.deps import require_admin, require_admin_or_police, require_police
    from app.main import app

    # Add test endpoints dynamically to test RBAC filters
    @app.get("/test/admin-only")
    async def admin_only_endpoint(u: User = Depends(require_admin)):
        return {"authorized": True, "user": u.email}

    @app.get("/test/police-only")
    async def police_only_endpoint(u: User = Depends(require_police)):
        return {"authorized": True, "user": u.email}

    @app.get("/test/admin-or-police")
    async def admin_or_police_endpoint(u: User = Depends(require_admin_or_police)):
        return {"authorized": True, "user": u.email}

    # 1. Admin accessing admin-only: OK
    res = await client.get("/test/admin-only", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    assert res.json()["authorized"] is True

    # 2. Citizen accessing admin-only: 403 Forbidden
    res = await client.get("/test/admin-only", headers={"Authorization": f"Bearer {citizen_token}"})
    assert res.status_code == 403

    # 3. Police accessing admin-only: 403 Forbidden
    res = await client.get("/test/admin-only", headers={"Authorization": f"Bearer {police_token}"})
    assert res.status_code == 403

    # 4. Police accessing police-only: OK
    res = await client.get("/test/police-only", headers={"Authorization": f"Bearer {police_token}"})
    assert res.status_code == 200

    # 5. Citizen accessing police-only: 403 Forbidden
    res = await client.get("/test/police-only", headers={"Authorization": f"Bearer {citizen_token}"})
    assert res.status_code == 403

    # 6. Admin and Police accessing admin-or-police: OK
    res = await client.get("/test/admin-or-police", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    res = await client.get("/test/admin-or-police", headers={"Authorization": f"Bearer {police_token}"})
    assert res.status_code == 200

    # 7. Citizen accessing admin-or-police: 403 Forbidden
    res = await client.get("/test/admin-or-police", headers={"Authorization": f"Bearer {citizen_token}"})
    assert res.status_code == 403
