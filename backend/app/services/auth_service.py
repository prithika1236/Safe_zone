from typing import Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.auth import CitizenRegisterRequest, UserLoginRequest


class AuthService:
    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email.lower().strip())
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def register_citizen(
        cls,
        db: AsyncSession,
        payload: CitizenRegisterRequest,
    ) -> User:
        """Register a new citizen account. Public registration is strictly restricted to CITIZEN role."""
        normalized_email = payload.email.lower().strip()
        existing_user = await cls.get_user_by_email(db, normalized_email)
        if existing_user:
            raise ValueError("A user with this email already exists")

        user = User(
            email=normalized_email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name.strip(),
            role=UserRole.CITIZEN,  # Enforce CITIZEN role strictly
            phone_number=payload.phone_number.strip() if payload.phone_number else None,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @classmethod
    async def authenticate_user(
        cls,
        db: AsyncSession,
        payload: UserLoginRequest,
    ) -> Tuple[User, str]:
        """Authenticate user credentials, check active status, and issue JWT access token."""
        user = await cls.get_user_by_email(db, payload.email)
        if not user or not verify_password(payload.password, user.hashed_password):
            raise ValueError("Invalid email or password")

        if not user.is_active:
            raise PermissionError("Inactive user account")

        access_token = create_access_token(
            subject=user.id,
            role=user.role.value,
            email=user.email,
        )
        return user, access_token
