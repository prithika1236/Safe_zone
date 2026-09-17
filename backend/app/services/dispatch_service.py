import math
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from geoalchemy2.functions import ST_GeomFromText, ST_X, ST_Y
from geoalchemy2.shape import to_shape
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import PatrolStatus, SOSStatus
from app.models.patrol import PatrolUnit
from app.models.sos import SOSRequest
from app.models.user import PoliceOfficer, User
from app.schemas.sos import (
    CitizenSOSResponse,
    SOSTriggerRequest,
    SOSResponse,
)
from app.services.crime_service import create_point_geometry, extract_coordinates
from app.services.location_service import (
    RoutingService,
    haversine_distance_m,
    validate_coordinates,
)


class DispatchService:
    """
    Emergency SOS Dispatch Engine and State Machine.
    CRITICAL ARCHITECTURAL GUARANTEE: Never invokes PRP optimization.
    """

    @staticmethod
    def _extract_coords(geometry_obj) -> Tuple[float, float]:
        return extract_coordinates(geometry_obj)

    @classmethod
    async def _to_sos_response(
        cls, db: AsyncSession, sos: SOSRequest
    ) -> SOSResponse:
        lat, lon = cls._extract_coords(sos.location)
        patrol = sos.assigned_patrol_unit

        dist_m: Optional[float] = None
        eta_s: Optional[float] = None

        patrol_lat, patrol_lon = (
            cls._extract_coords(patrol.current_location)
            if patrol and patrol.current_location is not None
            else (None, None)
        )

        if patrol and patrol_lat is not None and patrol_lon is not None:
            route = await RoutingService.get_route(
                origin_lat=patrol_lat,
                origin_lng=patrol_lon,
                dest_lat=lat,
                dest_lng=lon,
            )
            dist_m = route.road_distance_km * 1000.0
            eta_s = route.duration_seconds

        citizen = sos.citizen

        return SOSResponse(
            id=sos.id,
            citizen_id=sos.citizen_id,
            status=sos.status,
            latitude=lat,
            longitude=lon,
            assigned_patrol_unit_id=sos.assigned_patrol_unit_id,
            patrol_call_sign=patrol.call_sign if patrol else None,
            patrol_unit_type=None,
            patrol_latitude=patrol_lat,
            patrol_longitude=patrol_lon,
            distance_meters=dist_m,
            estimated_duration_seconds=eta_s,
            trigger_time=sos.trigger_time,
            accepted_time=sos.accepted_time,
            en_route_time=sos.en_route_time,
            arrived_time=sos.arrived_time,
            resolved_time=sos.resolved_time,
            notes=sos.notes,
            citizen_name=citizen.full_name if citizen else None,
            citizen_phone=citizen.phone_number if citizen else None,
            created_at=sos.created_at,
            updated_at=sos.updated_at,
        )

    @classmethod
    async def _to_citizen_response(
        cls, db: AsyncSession, sos: SOSRequest
    ) -> CitizenSOSResponse:
        lat, lon = cls._extract_coords(sos.location)
        patrol = sos.assigned_patrol_unit

        dist_m: Optional[float] = None
        eta_s: Optional[float] = None

        patrol_lat, patrol_lon = (
            cls._extract_coords(patrol.current_location)
            if patrol and patrol.current_location is not None
            else (None, None)
        )

        if patrol and patrol_lat is not None and patrol_lon is not None:
            route = await RoutingService.get_route(
                origin_lat=patrol_lat,
                origin_lng=patrol_lon,
                dest_lat=lat,
                dest_lng=lon,
            )
            dist_m = route.road_distance_km * 1000.0
            eta_s = route.duration_seconds

        return CitizenSOSResponse(
            id=sos.id,
            status=sos.status,
            latitude=lat,
            longitude=lon,
            patrol_assigned=sos.assigned_patrol_unit_id is not None,
            patrol_call_sign=patrol.call_sign if patrol else None,
            distance_meters=dist_m,
            estimated_duration_seconds=eta_s,
            trigger_time=sos.trigger_time,
            accepted_time=sos.accepted_time,
            en_route_time=sos.en_route_time,
            arrived_time=sos.arrived_time,
            resolved_time=sos.resolved_time,
            created_at=sos.created_at,
        )

    @classmethod
    async def trigger_sos(
        cls,
        db: AsyncSession,
        citizen_id: int,
        payload: SOSTriggerRequest,
    ) -> CitizenSOSResponse:
        """
        Citizen triggers emergency panic button:
        1. Validate coordinates.
        2. Check for existing active SOS requests.
        3. Create SOSRequest.
        4. Spatial nearest-neighbor search for available, on-duty patrol using FOR UPDATE lock.
        5. Assign patrol unit if available.
        """
        if not validate_coordinates(payload.latitude, payload.longitude):
            raise ValueError(
                f"Invalid emergency coordinates: ({payload.latitude}, {payload.longitude})"
            )

        # Check if citizen has an existing active SOS
        active_statuses = [
            SOSStatus.PENDING,
            SOSStatus.ASSIGNED,
            SOSStatus.ACCEPTED,
            SOSStatus.EN_ROUTE,
            SOSStatus.ARRIVED,
        ]
        stmt = (
            select(SOSRequest)
            .where(
                SOSRequest.citizen_id == citizen_id,
                SOSRequest.status.in_(active_statuses),
            )
            .options(
                selectinload(SOSRequest.assigned_patrol_unit),
                selectinload(SOSRequest.citizen),
            )
        )
        res = await db.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing:
            # Update location on existing active request and return
            existing.location = create_point_geometry(payload.latitude, payload.longitude)
            if payload.notes:
                existing.notes = payload.notes
            await db.commit()
            await db.refresh(existing)
            return await cls._to_citizen_response(db, existing)

        # Create new SOSRequest
        sos_req = SOSRequest(
            citizen_id=citizen_id,
            location=create_point_geometry(payload.latitude, payload.longitude),
            status=SOSStatus.PENDING,
            notes=payload.notes,
            trigger_time=datetime.now(timezone.utc),
        )
        db.add(sos_req)
        await db.flush()

        # Find nearest suitable on-duty AVAILABLE patrol unit with row lock
        patrol_stmt = (
            select(PatrolUnit)
            .join(PoliceOfficer, PatrolUnit.officer_id == PoliceOfficer.id)
            .where(
                PatrolUnit.status == PatrolStatus.AVAILABLE,
                PatrolUnit.is_active == True,
                PoliceOfficer.is_on_duty == True,
                PatrolUnit.current_location.is_not(None),
            )
            .with_for_update()
        )
        patrol_res = await db.execute(patrol_stmt)
        available_units = patrol_res.scalars().all()

        if available_units:
            # Sort by haversine distance to citizen
            def dist_fn(unit: PatrolUnit) -> float:
                plat, plon = cls._extract_coords(unit.current_location)
                return haversine_distance_m(
                    payload.latitude,
                    payload.longitude,
                    plat,
                    plon,
                )

            best_unit = min(available_units, key=dist_fn)

            # Safely reserve patrol unit
            best_unit.status = PatrolStatus.BUSY
            sos_req.assigned_patrol_unit_id = best_unit.id
            sos_req.status = SOSStatus.ASSIGNED

        await db.commit()

        # Reload with relationships
        reload_stmt = (
            select(SOSRequest)
            .where(SOSRequest.id == sos_req.id)
            .options(
                selectinload(SOSRequest.assigned_patrol_unit),
                selectinload(SOSRequest.citizen),
            )
        )
        final_res = await db.execute(reload_stmt)
        final_sos = final_res.scalar_one()

        return await cls._to_citizen_response(db, final_sos)

    @classmethod
    async def get_active_citizen_sos(
        cls,
        db: AsyncSession,
        citizen_id: int,
    ) -> Optional[CitizenSOSResponse]:
        """Fetch current active SOS for citizen."""
        active_statuses = [
            SOSStatus.PENDING,
            SOSStatus.ASSIGNED,
            SOSStatus.ACCEPTED,
            SOSStatus.EN_ROUTE,
            SOSStatus.ARRIVED,
        ]
        stmt = (
            select(SOSRequest)
            .where(
                SOSRequest.citizen_id == citizen_id,
                SOSRequest.status.in_(active_statuses),
            )
            .options(
                selectinload(SOSRequest.assigned_patrol_unit),
                selectinload(SOSRequest.citizen),
            )
            .order_by(desc(SOSRequest.created_at))
        )
        res = await db.execute(stmt)
        sos = res.scalars().first()
        if not sos:
            return None
        return await cls._to_citizen_response(db, sos)

    @classmethod
    async def cancel_sos(
        cls,
        db: AsyncSession,
        citizen_id: int,
        sos_id: int,
    ) -> CitizenSOSResponse:
        """Citizen cancels emergency panic alert."""
        stmt = (
            select(SOSRequest)
            .where(
                SOSRequest.id == sos_id,
                SOSRequest.citizen_id == citizen_id,
            )
            .options(
                selectinload(SOSRequest.assigned_patrol_unit),
                selectinload(SOSRequest.citizen),
            )
            .with_for_update()
        )
        res = await db.execute(stmt)
        sos = res.scalar_one_or_none()

        if not sos:
            raise ValueError(f"SOS Request #{sos_id} not found")

        if sos.status in [SOSStatus.RESOLVED, SOSStatus.CANCELLED]:
            raise ValueError(f"SOS Request is already in terminal status: {sos.status}")

        # If patrol unit was assigned, release it back to AVAILABLE
        if sos.assigned_patrol_unit:
            sos.assigned_patrol_unit.status = PatrolStatus.AVAILABLE

        sos.status = SOSStatus.CANCELLED
        await db.commit()
        await db.refresh(sos)
        return await cls._to_citizen_response(db, sos)

    # --- POLICE DISPATCH WORKFLOW ---

    @classmethod
    async def police_get_active_sos(
        cls,
        db: AsyncSession,
        user_id: int,
    ) -> Optional[SOSResponse]:
        """Fetch incoming or active SOS request assigned to the officer's patrol unit."""
        # Find officer's patrol unit
        officer_stmt = select(PoliceOfficer).where(PoliceOfficer.user_id == user_id)
        off_res = await db.execute(officer_stmt)
        officer = off_res.scalar_one_or_none()
        if not officer:
            return None

        patrol_stmt = select(PatrolUnit).where(PatrolUnit.officer_id == officer.id)
        patrol_res = await db.execute(patrol_stmt)
        patrol = patrol_res.scalar_one_or_none()
        if not patrol:
            return None

        active_statuses = [
            SOSStatus.ASSIGNED,
            SOSStatus.ACCEPTED,
            SOSStatus.EN_ROUTE,
            SOSStatus.ARRIVED,
        ]
        sos_stmt = (
            select(SOSRequest)
            .where(
                SOSRequest.assigned_patrol_unit_id == patrol.id,
                SOSRequest.status.in_(active_statuses),
            )
            .options(
                selectinload(SOSRequest.assigned_patrol_unit),
                selectinload(SOSRequest.citizen),
            )
            .order_by(desc(SOSRequest.created_at))
        )
        sos_res = await db.execute(sos_stmt)
        sos = sos_res.scalars().first()
        if not sos:
            return None

        return await cls._to_sos_response(db, sos)

    @classmethod
    async def police_accept_sos(
        cls,
        db: AsyncSession,
        user_id: int,
        sos_id: int,
    ) -> SOSResponse:
        """Officer accepts emergency dispatch assignment (ASSIGNED -> ACCEPTED)."""
        stmt = (
            select(SOSRequest)
            .where(SOSRequest.id == sos_id)
            .options(
                selectinload(SOSRequest.assigned_patrol_unit),
                selectinload(SOSRequest.citizen),
            )
            .with_for_update()
        )
        res = await db.execute(stmt)
        sos = res.scalar_one_or_none()

        if not sos:
            raise ValueError(f"SOS Request #{sos_id} not found")

        if sos.status == SOSStatus.ACCEPTED:
            raise ValueError("SOS Request is already ACCEPTED")

        if sos.status != SOSStatus.ASSIGNED:
            raise ValueError(
                f"Cannot accept SOS Request in status: {sos.status}. Must be in ASSIGNED status."
            )

        sos.status = SOSStatus.ACCEPTED
        sos.accepted_time = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(sos)

        return await cls._to_sos_response(db, sos)

    @classmethod
    async def police_en_route_sos(
        cls,
        db: AsyncSession,
        user_id: int,
        sos_id: int,
    ) -> SOSResponse:
        """Officer departs and travels to citizen emergency (ACCEPTED -> EN_ROUTE)."""
        stmt = (
            select(SOSRequest)
            .where(SOSRequest.id == sos_id)
            .options(
                selectinload(SOSRequest.assigned_patrol_unit),
                selectinload(SOSRequest.citizen),
            )
            .with_for_update()
        )
        res = await db.execute(stmt)
        sos = res.scalar_one_or_none()

        if not sos:
            raise ValueError(f"SOS Request #{sos_id} not found")

        if sos.status != SOSStatus.ACCEPTED:
            raise ValueError(
                f"Cannot mark EN_ROUTE for SOS in status {sos.status}. Must be in ACCEPTED status."
            )

        sos.status = SOSStatus.EN_ROUTE
        sos.en_route_time = datetime.now(timezone.utc)
        if sos.assigned_patrol_unit:
            sos.assigned_patrol_unit.status = PatrolStatus.EN_ROUTE

        await db.commit()
        await db.refresh(sos)

        return await cls._to_sos_response(db, sos)

    @classmethod
    async def police_arrived_sos(
        cls,
        db: AsyncSession,
        user_id: int,
        sos_id: int,
    ) -> SOSResponse:
        """Officer arrives on-scene at citizen location (EN_ROUTE -> ARRIVED)."""
        stmt = (
            select(SOSRequest)
            .where(SOSRequest.id == sos_id)
            .options(
                selectinload(SOSRequest.assigned_patrol_unit),
                selectinload(SOSRequest.citizen),
            )
            .with_for_update()
        )
        res = await db.execute(stmt)
        sos = res.scalar_one_or_none()

        if not sos:
            raise ValueError(f"SOS Request #{sos_id} not found")

        if sos.status != SOSStatus.EN_ROUTE:
            raise ValueError(
                f"Cannot mark ARRIVED for SOS in status {sos.status}. Must be in EN_ROUTE status."
            )

        sos.status = SOSStatus.ARRIVED
        sos.arrived_time = datetime.now(timezone.utc)
        if sos.assigned_patrol_unit:
            sos.assigned_patrol_unit.status = PatrolStatus.ON_SCENE

        await db.commit()
        await db.refresh(sos)

        return await cls._to_sos_response(db, sos)

    @classmethod
    async def police_resolve_sos(
        cls,
        db: AsyncSession,
        user_id: int,
        sos_id: int,
        resolution_notes: Optional[str] = None,
    ) -> SOSResponse:
        """Officer resolves incident and releases patrol unit back to AVAILABLE (ARRIVED -> RESOLVED)."""
        stmt = (
            select(SOSRequest)
            .where(SOSRequest.id == sos_id)
            .options(
                selectinload(SOSRequest.assigned_patrol_unit),
                selectinload(SOSRequest.citizen),
            )
            .with_for_update()
        )
        res = await db.execute(stmt)
        sos = res.scalar_one_or_none()

        if not sos:
            raise ValueError(f"SOS Request #{sos_id} not found")

        if sos.status != SOSStatus.ARRIVED:
            raise ValueError(
                f"Cannot RESOLVE SOS in status {sos.status}. Officer must be ARRIVED on-scene first."
            )

        sos.status = SOSStatus.RESOLVED
        sos.resolved_time = datetime.now(timezone.utc)
        if resolution_notes:
            sos.notes = f"{sos.notes or ''}\nResolution: {resolution_notes}".strip()

        # Release patrol unit back to AVAILABLE
        if sos.assigned_patrol_unit:
            sos.assigned_patrol_unit.status = PatrolStatus.AVAILABLE

        await db.commit()
        await db.refresh(sos)

        return await cls._to_sos_response(db, sos)

    # --- ADMIN MONITORING ---

    @classmethod
    async def admin_list_sos(
        cls,
        db: AsyncSession,
        status_filter: Optional[SOSStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[SOSResponse], int, int]:
        """Admin queries all historical and active SOS requests."""
        count_stmt = select(func.count(SOSRequest.id))
        if status_filter:
            count_stmt = count_stmt.where(SOSRequest.status == status_filter)

        total_res = await db.execute(count_stmt)
        total = total_res.scalar() or 0

        pages = math.ceil(total / page_size) if total > 0 else 1

        query_stmt = (
            select(SOSRequest)
            .options(
                selectinload(SOSRequest.assigned_patrol_unit),
                selectinload(SOSRequest.citizen),
            )
            .order_by(desc(SOSRequest.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        if status_filter:
            query_stmt = query_stmt.where(SOSRequest.status == status_filter)

        res = await db.execute(query_stmt)
        sos_list = res.scalars().all()

        items = [await cls._to_sos_response(db, s) for s in sos_list]
        return (items, total, pages)
