import math
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import hash_password
from app.models.enums import PatrolStatus, UserRole
from app.models.patrol import PatrolUnit
from app.models.user import PoliceOfficer, User
from app.schemas.patrol import (
    OperationalStatusSummary,
    PatrolUnitCreateRequest,
    PatrolUnitResponse,
    PatrolUnitUpdateRequest,
    PoliceOfficerCreateRequest,
    PoliceOfficerResponse,
    PoliceOfficerUpdateRequest,
)


class PatrolService:
    # --- Police Officer Management ---

    @staticmethod
    def _format_officer_response(officer: PoliceOfficer) -> PoliceOfficerResponse:
        return PoliceOfficerResponse(
            id=officer.id,
            user_id=officer.user_id,
            email=officer.user.email,
            full_name=officer.user.full_name,
            phone_number=officer.user.phone_number,
            badge_number=officer.badge_number,
            rank=officer.rank,
            department=officer.department,
            is_on_duty=officer.is_on_duty,
            is_active=officer.user.is_active,
            created_at=officer.created_at,
            updated_at=officer.updated_at,
        )

    @classmethod
    async def create_police_officer(
        cls,
        db: AsyncSession,
        payload: PoliceOfficerCreateRequest,
    ) -> PoliceOfficerResponse:
        email = payload.email.lower().strip()
        badge = payload.badge_number.strip()

        # Check existing email
        stmt_user = select(User).where(User.email == email)
        res_user = await db.execute(stmt_user)
        if res_user.scalar_one_or_none():
            raise ValueError("A user with this email already exists")

        # Check existing badge
        stmt_badge = select(PoliceOfficer).where(PoliceOfficer.badge_number == badge)
        res_badge = await db.execute(stmt_badge)
        if res_badge.scalar_one_or_none():
            raise ValueError(f"An officer with badge number '{badge}' already exists")

        # Create User account with POLICE role
        user = User(
            email=email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name.strip(),
            role=UserRole.POLICE,
            phone_number=payload.phone_number.strip() if payload.phone_number else None,
            is_active=True,
        )
        db.add(user)
        await db.flush()

        # Create PoliceOfficer profile
        officer = PoliceOfficer(
            user_id=user.id,
            badge_number=badge,
            rank=payload.rank.strip() if payload.rank else None,
            department=payload.department.strip() if payload.department else None,
            is_on_duty=payload.is_on_duty,
        )
        db.add(officer)
        await db.commit()
        await db.refresh(officer)
        await db.refresh(user)

        officer.user = user
        return cls._format_officer_response(officer)

    @classmethod
    async def list_police_officers(
        cls,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        is_on_duty: Optional[bool] = None,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[PoliceOfficerResponse], int, int]:
        query = select(PoliceOfficer).join(PoliceOfficer.user).options(selectinload(PoliceOfficer.user))
        count_query = select(func.count(PoliceOfficer.id)).join(PoliceOfficer.user)

        if is_on_duty is not None:
            query = query.where(PoliceOfficer.is_on_duty == is_on_duty)
            count_query = count_query.where(PoliceOfficer.is_on_duty == is_on_duty)

        if is_active is not None:
            query = query.where(User.is_active == is_active)
            count_query = count_query.where(User.is_active == is_active)

        total_res = await db.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(PoliceOfficer.id.asc()).offset((page - 1) * page_size).limit(page_size)
        res = await db.execute(query)
        officers = res.scalars().all()

        items = [cls._format_officer_response(o) for o in officers]
        pages = math.ceil(total / page_size) if page_size > 0 else 1
        return items, total, pages

    @classmethod
    async def get_police_officer(
        cls,
        db: AsyncSession,
        officer_id: int,
    ) -> Optional[PoliceOfficerResponse]:
        query = (
            select(PoliceOfficer)
            .where(PoliceOfficer.id == officer_id)
            .options(selectinload(PoliceOfficer.user))
        )
        res = await db.execute(query)
        officer = res.scalar_one_or_none()
        if not officer:
            return None
        return cls._format_officer_response(officer)

    @classmethod
    async def update_police_officer(
        cls,
        db: AsyncSession,
        officer_id: int,
        payload: PoliceOfficerUpdateRequest,
    ) -> Optional[PoliceOfficerResponse]:
        query = (
            select(PoliceOfficer)
            .where(PoliceOfficer.id == officer_id)
            .options(selectinload(PoliceOfficer.user))
        )
        res = await db.execute(query)
        officer = res.scalar_one_or_none()
        if not officer:
            return None

        if payload.badge_number is not None and payload.badge_number.strip() != officer.badge_number:
            new_badge = payload.badge_number.strip()
            stmt_badge = select(PoliceOfficer).where(
                PoliceOfficer.badge_number == new_badge,
                PoliceOfficer.id != officer_id,
            )
            badge_res = await db.execute(stmt_badge)
            if badge_res.scalar_one_or_none():
                raise ValueError(f"An officer with badge number '{new_badge}' already exists")
            officer.badge_number = new_badge

        if payload.rank is not None:
            officer.rank = payload.rank.strip() if payload.rank else None
        if payload.department is not None:
            officer.department = payload.department.strip() if payload.department else None
        if payload.is_on_duty is not None:
            officer.is_on_duty = payload.is_on_duty

        # Linked User updates
        if payload.full_name is not None:
            officer.user.full_name = payload.full_name.strip()
        if payload.phone_number is not None:
            officer.user.phone_number = payload.phone_number.strip() if payload.phone_number else None
        if payload.is_active is not None:
            officer.user.is_active = payload.is_active

        await db.commit()
        await db.refresh(officer)
        await db.refresh(officer.user)
        return cls._format_officer_response(officer)

    # --- Patrol Unit Management ---

    @staticmethod
    def _format_patrol_response(unit: PatrolUnit) -> PatrolUnitResponse:
        return PatrolUnitResponse(
            id=unit.id,
            call_sign=unit.call_sign,
            officer_id=unit.officer_id,
            officer_badge=unit.officer.badge_number if unit.officer else None,
            officer_name=unit.officer.user.full_name if unit.officer and unit.officer.user else None,
            status=unit.status,
            is_active=unit.is_active,
            last_location_update=unit.last_location_update,
            created_at=unit.created_at,
            updated_at=unit.updated_at,
        )

    @classmethod
    async def create_patrol_unit(
        cls,
        db: AsyncSession,
        payload: PatrolUnitCreateRequest,
    ) -> PatrolUnitResponse:
        call_sign = payload.call_sign.strip()

        stmt_call = select(PatrolUnit).where(PatrolUnit.call_sign == call_sign)
        res_call = await db.execute(stmt_call)
        if res_call.scalar_one_or_none():
            raise ValueError(f"Patrol unit with call sign '{call_sign}' already exists")

        if payload.officer_id:
            officer_res = await db.execute(
                select(PoliceOfficer)
                .where(PoliceOfficer.id == payload.officer_id)
                .options(selectinload(PoliceOfficer.user))
            )
            if not officer_res.scalar_one_or_none():
                raise ValueError(f"Officer with ID {payload.officer_id} does not exist")

        unit = PatrolUnit(
            call_sign=call_sign,
            officer_id=payload.officer_id,
            status=payload.status,
            is_active=True,
        )
        db.add(unit)
        await db.commit()
        await db.refresh(unit)

        # Load relationships for formatting
        return await cls.get_patrol_unit(db, unit.id)  # type: ignore

    @classmethod
    async def list_patrol_units(
        cls,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        status: Optional[PatrolStatus] = None,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[PatrolUnitResponse], int, int]:
        query = (
            select(PatrolUnit)
            .outerjoin(PatrolUnit.officer)
            .options(
                selectinload(PatrolUnit.officer).selectinload(PoliceOfficer.user),
            )
        )
        count_query = select(func.count(PatrolUnit.id))

        if status is not None:
            query = query.where(PatrolUnit.status == status)
            count_query = count_query.where(PatrolUnit.status == status)

        if is_active is not None:
            query = query.where(PatrolUnit.is_active == is_active)
            count_query = count_query.where(PatrolUnit.is_active == is_active)

        total_res = await db.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(PatrolUnit.id.asc()).offset((page - 1) * page_size).limit(page_size)
        res = await db.execute(query)
        units = res.scalars().all()

        items = [cls._format_patrol_response(u) for u in units]
        pages = math.ceil(total / page_size) if page_size > 0 else 1
        return items, total, pages

    @classmethod
    async def get_patrol_unit(
        cls,
        db: AsyncSession,
        unit_id: int,
    ) -> Optional[PatrolUnitResponse]:
        query = (
            select(PatrolUnit)
            .where(PatrolUnit.id == unit_id)
            .options(
                selectinload(PatrolUnit.officer).selectinload(PoliceOfficer.user),
            )
        )
        res = await db.execute(query)
        unit = res.scalar_one_or_none()
        if not unit:
            return None
        return cls._format_patrol_response(unit)

    @classmethod
    async def update_patrol_unit(
        cls,
        db: AsyncSession,
        unit_id: int,
        payload: PatrolUnitUpdateRequest,
    ) -> Optional[PatrolUnitResponse]:
        query = (
            select(PatrolUnit)
            .where(PatrolUnit.id == unit_id)
            .options(
                selectinload(PatrolUnit.officer).selectinload(PoliceOfficer.user),
            )
        )
        res = await db.execute(query)
        unit = res.scalar_one_or_none()
        if not unit:
            return None

        if payload.call_sign is not None and payload.call_sign.strip() != unit.call_sign:
            new_call = payload.call_sign.strip()
            stmt_call = select(PatrolUnit).where(
                PatrolUnit.call_sign == new_call,
                PatrolUnit.id != unit_id,
            )
            call_res = await db.execute(stmt_call)
            if call_res.scalar_one_or_none():
                raise ValueError(f"Patrol unit with call sign '{new_call}' already exists")
            unit.call_sign = new_call

        if payload.officer_id is not None:
            if payload.officer_id > 0:
                off_res = await db.execute(
                    select(PoliceOfficer).where(PoliceOfficer.id == payload.officer_id)
                )
                if not off_res.scalar_one_or_none():
                    raise ValueError(f"Officer with ID {payload.officer_id} does not exist")
                unit.officer_id = payload.officer_id
            else:
                unit.officer_id = None

        if payload.status is not None:
            unit.status = payload.status

        if payload.is_active is not None:
            unit.is_active = payload.is_active

        await db.commit()
        await db.refresh(unit)
        return await cls.get_patrol_unit(db, unit.id)

    @classmethod
    async def set_patrol_unit_status(
        cls,
        db: AsyncSession,
        unit_id: int,
        status: PatrolStatus,
    ) -> Optional[PatrolUnitResponse]:
        query = (
            select(PatrolUnit)
            .where(PatrolUnit.id == unit_id)
            .options(
                selectinload(PatrolUnit.officer).selectinload(PoliceOfficer.user),
            )
        )
        res = await db.execute(query)
        unit = res.scalar_one_or_none()
        if not unit:
            return None

        unit.status = status
        await db.commit()
        await db.refresh(unit)
        return await cls.get_patrol_unit(db, unit.id)

    # --- Operational Status Summary ---

    @classmethod
    async def get_operational_summary(
        cls,
        db: AsyncSession,
    ) -> OperationalStatusSummary:
        # Officer counts
        total_officers = (await db.execute(select(func.count(PoliceOfficer.id)))).scalar() or 0
        on_duty_officers = (
            await db.execute(select(func.count(PoliceOfficer.id)).where(PoliceOfficer.is_on_duty == True))
        ).scalar() or 0

        # Patrol unit counts by status
        total_units = (await db.execute(select(func.count(PatrolUnit.id)))).scalar() or 0
        available_units = (
            await db.execute(
                select(func.count(PatrolUnit.id)).where(
                    PatrolUnit.status == PatrolStatus.AVAILABLE,
                    PatrolUnit.is_active == True,
                )
            )
        ).scalar() or 0
        busy_units = (
            await db.execute(
                select(func.count(PatrolUnit.id)).where(
                    PatrolUnit.status == PatrolStatus.BUSY,
                    PatrolUnit.is_active == True,
                )
            )
        ).scalar() or 0
        en_route_units = (
            await db.execute(
                select(func.count(PatrolUnit.id)).where(
                    PatrolUnit.status == PatrolStatus.EN_ROUTE,
                    PatrolUnit.is_active == True,
                )
            )
        ).scalar() or 0
        off_duty_units = (
            await db.execute(
                select(func.count(PatrolUnit.id)).where(
                    PatrolUnit.status == PatrolStatus.OFF_DUTY,
                    PatrolUnit.is_active == True,
                )
            )
        ).scalar() or 0

        return OperationalStatusSummary(
            total_officers=total_officers,
            on_duty_officers=on_duty_officers,
            total_patrol_units=total_units,
            available_patrol_units=available_units,
            busy_patrol_units=busy_units,
            en_route_patrol_units=en_route_units,
            off_duty_patrol_units=off_duty_units,
        )
