"""
SafeZone Patrol Assignment Service.

Manages the lifecycle, auto-dispatch, manual override, status transitions,
and conflict prevention for PatrolUnit to PRPLocation assignments.
"""

from datetime import datetime, timezone
import logging
import math
from typing import List, Optional, Sequence, Tuple
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import AssignmentStatus, PatrolStatus, PRPStatus
from app.models.optimization import OptimizationRun, PRPLocation
from app.models.patrol import PatrolAssignment, PatrolUnit
from app.models.user import PoliceOfficer
from app.optimization.assignment import (
    AssignmentMatch,
    PatrolResource,
    PRPResource,
    assign_patrols_to_prps,
)
from app.schemas.assignment import (
    AssignmentMatchResponse,
    AutoAssignmentRequest,
    AutoAssignmentResponse,
    ManualAssignmentRequest,
)
from app.services.crime_service import extract_coordinates
from app.services.location_service import haversine_distance_km, validate_coordinates

logger = logging.getLogger("safezone.assignment")

ACTIVE_ASSIGNMENT_STATUSES = (
    AssignmentStatus.ASSIGNED,
    AssignmentStatus.ACKNOWLEDGED,
    AssignmentStatus.ARRIVED,
)


class AssignmentService:
    """Business service orchestrating patrol assignments and state synchronization."""

    @classmethod
    def _format_assignment_response(
        cls,
        assignment: PatrolAssignment,
        unit: Optional[PatrolUnit] = None,
        prp: Optional[PRPLocation] = None,
    ) -> AssignmentMatchResponse:
        """Format domain PatrolAssignment entity into schema response."""
        p_unit = unit or assignment.patrol_unit
        p_prp = prp or assignment.prp_location

        call_sign = p_unit.call_sign if p_unit else "UNKNOWN"
        prp_name = p_prp.name if p_prp else "UNKNOWN"
        priority_score = p_prp.priority_score if p_prp else 0.0

        dist_km = None
        dur_mins = None
        if p_unit and p_unit.current_location and p_prp and p_prp.location:
            u_lat, u_lng = extract_coordinates(p_unit.current_location)
            p_lat, p_lng = extract_coordinates(p_prp.location)
            if validate_coordinates(u_lat, u_lng) and validate_coordinates(p_lat, p_lng):
                dist_km = haversine_distance_km(u_lat, u_lng, p_lat, p_lng)
                dur_mins = round((dist_km / 35.0) * 60.0, 1)

        return AssignmentMatchResponse(
            id=assignment.id,
            patrol_unit_id=assignment.patrol_unit_id,
            call_sign=call_sign,
            prp_location_id=assignment.prp_location_id,
            prp_name=prp_name,
            optimization_run_id=assignment.optimization_run_id,
            shift=assignment.shift,
            status=assignment.status,
            distance_km=dist_km,
            estimated_duration_minutes=dur_mins,
            priority_score=priority_score,
            assigned_at=assignment.assigned_at,
            acknowledged_at=assignment.acknowledged_at,
            arrived_at=assignment.arrived_at,
            completed_at=assignment.completed_at,
            metadata={},
        )

    @classmethod
    async def auto_assign_patrols(
        cls,
        db: AsyncSession,
        payload: AutoAssignmentRequest,
    ) -> AutoAssignmentResponse:
        """
        Execute automatic minimum-distance matching between available patrol units
        and approved unassigned PRPs.
        """
        now = datetime.now(timezone.utc)

        # 1. Fetch available patrol units with valid current locations
        unit_query = (
            select(PatrolUnit)
            .where(
                PatrolUnit.is_active == True,
                PatrolUnit.status == PatrolStatus.AVAILABLE,
                PatrolUnit.current_location.is_not(None),
            )
            .options(selectinload(PatrolUnit.officer))
        )
        unit_res = await db.execute(unit_query)
        available_units = unit_res.scalars().all()

        # Filter out any unit that currently has an active uncompleted assignment
        active_unit_ids_res = await db.execute(
            select(PatrolAssignment.patrol_unit_id).where(
                PatrolAssignment.status.in_(ACTIVE_ASSIGNMENT_STATUSES)
            )
        )
        busy_unit_ids = set(active_unit_ids_res.scalars().all())
        eligible_units = [u for u in available_units if u.id not in busy_unit_ids]

        # 2. Fetch approved/active PRPs
        prp_query = select(PRPLocation).where(
            PRPLocation.status.in_([PRPStatus.APPROVED, PRPStatus.ACTIVE, PRPStatus.RECOMMENDED])
        )
        if payload.optimization_run_id is not None:
            prp_query = prp_query.where(PRPLocation.optimization_run_id == payload.optimization_run_id)

        prp_res = await db.execute(prp_query)
        all_prps = prp_res.scalars().all()

        # Filter out PRPs that already have an active assignment
        active_prp_ids_res = await db.execute(
            select(PatrolAssignment.prp_location_id).where(
                PatrolAssignment.status.in_(ACTIVE_ASSIGNMENT_STATUSES)
            )
        )
        busy_prp_ids = set(active_prp_ids_res.scalars().all())
        eligible_prps = [p for p in all_prps if p.id not in busy_prp_ids]

        # 3. Construct optimization resource items
        patrol_resources: List[PatrolResource] = []
        for u in eligible_units:
            lat, lng = extract_coordinates(u.current_location)
            if validate_coordinates(lat, lng):
                officer_name = u.officer.user.full_name if (u.officer and hasattr(u.officer, "user") and u.officer.user) else None
                patrol_resources.append(
                    PatrolResource(
                        id=u.id,
                        call_sign=u.call_sign,
                        latitude=lat,
                        longitude=lng,
                        officer_name=officer_name,
                    )
                )

        prp_resources: List[PRPResource] = []
        for p in eligible_prps:
            lat, lng = extract_coordinates(p.location)
            if validate_coordinates(lat, lng):
                prp_resources.append(
                    PRPResource(
                        id=p.id,
                        name=p.name,
                        latitude=lat,
                        longitude=lng,
                        optimization_run_id=p.optimization_run_id,
                        priority_score=p.priority_score,
                    )
                )

        # 4. Execute matching engine
        matches = assign_patrols_to_prps(
            patrol_units=patrol_resources,
            prp_locations=prp_resources,
            max_dispatch_distance_km=payload.max_dispatch_distance_km,
        )

        # 5. Persist assignments and update unit/PRP statuses
        unit_map = {u.id: u for u in eligible_units}
        prp_map = {p.id: p for p in eligible_prps}
        saved_assignments: List[AssignmentMatchResponse] = []

        shift_str = payload.shift or "MORNING"

        for m in matches:
            assignment = PatrolAssignment(
                patrol_unit_id=m.patrol_unit_id,
                prp_location_id=m.prp_location_id,
                optimization_run_id=m.optimization_run_id,
                shift=shift_str,
                status=AssignmentStatus.ASSIGNED,
                assigned_at=now,
            )
            db.add(assignment)

            # Update patrol unit status to BUSY
            if m.patrol_unit_id in unit_map:
                unit_map[m.patrol_unit_id].status = PatrolStatus.BUSY

            # Update PRP status to ACTIVE
            if m.prp_location_id in prp_map:
                prp_map[m.prp_location_id].status = PRPStatus.ACTIVE

            await db.flush()

            saved_assignments.append(
                cls._format_assignment_response(
                    assignment=assignment,
                    unit=unit_map.get(m.patrol_unit_id),
                    prp=prp_map.get(m.prp_location_id),
                )
            )

        if saved_assignments:
            await db.commit()

        return AutoAssignmentResponse(
            matched_count=len(saved_assignments),
            unassigned_prp_count=len(eligible_prps) - len(saved_assignments),
            unassigned_patrol_count=len(eligible_units) - len(saved_assignments),
            assignments=saved_assignments,
        )

    @classmethod
    async def manual_assign_patrol(
        cls,
        db: AsyncSession,
        payload: ManualAssignmentRequest,
    ) -> AssignmentMatchResponse:
        """Manually assign a specific patrol unit to an approved PRP."""
        # 1. Validate Patrol Unit
        unit_res = await db.execute(select(PatrolUnit).where(PatrolUnit.id == payload.patrol_unit_id))
        unit = unit_res.scalar_one_or_none()
        if not unit:
            raise ValueError(f"Patrol unit with ID {payload.patrol_unit_id} not found")
        if not unit.is_active:
            raise ValueError(f"Patrol unit {unit.call_sign} is inactive")

        # Check for active existing assignment
        active_unit_res = await db.execute(
            select(PatrolAssignment.id).where(
                PatrolAssignment.patrol_unit_id == unit.id,
                PatrolAssignment.status.in_(ACTIVE_ASSIGNMENT_STATUSES),
            )
        )
        if active_unit_res.scalar_one_or_none():
            raise ValueError(f"Patrol unit {unit.call_sign} already has an active assignment")

        # 2. Validate PRP Location
        prp_res = await db.execute(select(PRPLocation).where(PRPLocation.id == payload.prp_location_id))
        prp = prp_res.scalar_one_or_none()
        if not prp:
            raise ValueError(f"PRP location with ID {payload.prp_location_id} not found")

        # Check for active existing assignment on PRP
        active_prp_res = await db.execute(
            select(PatrolAssignment.id).where(
                PatrolAssignment.prp_location_id == prp.id,
                PatrolAssignment.status.in_(ACTIVE_ASSIGNMENT_STATUSES),
            )
        )
        if active_prp_res.scalar_one_or_none():
            raise ValueError(f"PRP location '{prp.name}' already has an active patrol assigned")

        now = datetime.now(timezone.utc)
        assignment = PatrolAssignment(
            patrol_unit_id=unit.id,
            prp_location_id=prp.id,
            optimization_run_id=prp.optimization_run_id,
            shift=payload.shift,
            status=AssignmentStatus.ASSIGNED,
            assigned_at=now,
        )
        db.add(assignment)

        unit.status = PatrolStatus.BUSY
        prp.status = PRPStatus.ACTIVE

        await db.commit()
        await db.refresh(assignment)

        return cls._format_assignment_response(assignment, unit=unit, prp=prp)

    @classmethod
    async def cancel_assignment(
        cls,
        db: AsyncSession,
        assignment_id: int,
    ) -> Optional[AssignmentMatchResponse]:
        """Cancel an assignment and release the assigned patrol unit back to AVAILABLE."""
        query = (
            select(PatrolAssignment)
            .where(PatrolAssignment.id == assignment_id)
            .options(
                selectinload(PatrolAssignment.patrol_unit),
                selectinload(PatrolAssignment.prp_location),
            )
        )
        res = await db.execute(query)
        assignment = res.scalar_one_or_none()
        if not assignment:
            return None

        assignment.status = AssignmentStatus.CANCELLED

        if assignment.patrol_unit:
            assignment.patrol_unit.status = PatrolStatus.AVAILABLE

        await db.commit()
        await db.refresh(assignment)
        return cls._format_assignment_response(assignment)

    @classmethod
    async def reassign_patrol(
        cls,
        db: AsyncSession,
        assignment_id: int,
        new_patrol_unit_id: int,
    ) -> Optional[AssignmentMatchResponse]:
        """Reassign an active assignment to a different patrol unit."""
        query = (
            select(PatrolAssignment)
            .where(PatrolAssignment.id == assignment_id)
            .options(
                selectinload(PatrolAssignment.patrol_unit),
                selectinload(PatrolAssignment.prp_location),
            )
        )
        res = await db.execute(query)
        assignment = res.scalar_one_or_none()
        if not assignment:
            return None

        # Validate new patrol unit
        new_unit_res = await db.execute(select(PatrolUnit).where(PatrolUnit.id == new_patrol_unit_id))
        new_unit = new_unit_res.scalar_one_or_none()
        if not new_unit or not new_unit.is_active:
            raise ValueError("Target new patrol unit not found or inactive")

        # Release old unit if exists
        if assignment.patrol_unit:
            assignment.patrol_unit.status = PatrolStatus.AVAILABLE

        # Assign new unit
        assignment.patrol_unit_id = new_unit.id
        assignment.status = AssignmentStatus.ASSIGNED
        assignment.assigned_at = datetime.now(timezone.utc)
        assignment.acknowledged_at = None
        assignment.arrived_at = None
        assignment.completed_at = None

        new_unit.status = PatrolStatus.BUSY

        await db.commit()
        await db.refresh(assignment)
        return cls._format_assignment_response(assignment, unit=new_unit)

    @classmethod
    async def get_police_current_assignment(
        cls,
        db: AsyncSession,
        user_id: int,
    ) -> Optional[AssignmentMatchResponse]:
        """Fetch the active uncompleted assignment for a logged-in police officer."""
        # Find officer by user_id
        officer_res = await db.execute(select(PoliceOfficer).where(PoliceOfficer.user_id == user_id))
        officer = officer_res.scalar_one_or_none()
        if not officer:
            return None

        # Find assigned patrol unit
        unit_res = await db.execute(
            select(PatrolUnit).where(PatrolUnit.officer_id == officer.id, PatrolUnit.is_active == True)
        )
        unit = unit_res.scalar_one_or_none()
        if not unit:
            return None

        # Find latest active assignment
        query = (
            select(PatrolAssignment)
            .where(
                PatrolAssignment.patrol_unit_id == unit.id,
                PatrolAssignment.status.in_(ACTIVE_ASSIGNMENT_STATUSES),
            )
            .options(
                selectinload(PatrolAssignment.patrol_unit),
                selectinload(PatrolAssignment.prp_location),
            )
            .order_by(PatrolAssignment.assigned_at.desc())
        )
        res = await db.execute(query)
        assignment = res.scalar_one_or_none()
        if not assignment:
            return None

        return cls._format_assignment_response(assignment)

    @classmethod
    async def update_assignment_status_by_police(
        cls,
        db: AsyncSession,
        assignment_id: int,
        user_id: int,
        new_status: AssignmentStatus,
    ) -> Optional[AssignmentMatchResponse]:
        """Handle police workflow status updates: ACKNOWLEDGED, ARRIVED, COMPLETED."""
        query = (
            select(PatrolAssignment)
            .where(PatrolAssignment.id == assignment_id)
            .options(
                selectinload(PatrolAssignment.patrol_unit),
                selectinload(PatrolAssignment.prp_location),
            )
        )
        res = await db.execute(query)
        assignment = res.scalar_one_or_none()
        if not assignment:
            return None

        now = datetime.now(timezone.utc)
        assignment.status = new_status

        if new_status == AssignmentStatus.ACKNOWLEDGED:
            assignment.acknowledged_at = now
            if assignment.patrol_unit:
                assignment.patrol_unit.status = PatrolStatus.EN_ROUTE
        elif new_status == AssignmentStatus.ARRIVED:
            assignment.arrived_at = now
            if assignment.patrol_unit:
                assignment.patrol_unit.status = PatrolStatus.ON_SCENE
        elif new_status == AssignmentStatus.COMPLETED:
            assignment.completed_at = now
            if assignment.patrol_unit:
                assignment.patrol_unit.status = PatrolStatus.AVAILABLE
            if assignment.prp_location:
                assignment.prp_location.status = PRPStatus.COMPLETED

        await db.commit()
        await db.refresh(assignment)
        return cls._format_assignment_response(assignment)

    @classmethod
    async def list_assignments(
        cls,
        db: AsyncSession,
        status: Optional[AssignmentStatus] = None,
        patrol_unit_id: Optional[int] = None,
        optimization_run_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[AssignmentMatchResponse], int, int]:
        """List assignments with optional status and resource filtering."""
        query = select(PatrolAssignment).options(
            selectinload(PatrolAssignment.patrol_unit),
            selectinload(PatrolAssignment.prp_location),
        )
        count_query = select(func.count(PatrolAssignment.id))

        if status is not None:
            query = query.where(PatrolAssignment.status == status)
            count_query = count_query.where(PatrolAssignment.status == status)
        if patrol_unit_id is not None:
            query = query.where(PatrolAssignment.patrol_unit_id == patrol_unit_id)
            count_query = count_query.where(PatrolAssignment.patrol_unit_id == patrol_unit_id)
        if optimization_run_id is not None:
            query = query.where(PatrolAssignment.optimization_run_id == optimization_run_id)
            count_query = count_query.where(PatrolAssignment.optimization_run_id == optimization_run_id)

        total_res = await db.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(PatrolAssignment.assigned_at.desc()).offset((page - 1) * page_size).limit(page_size)
        res = await db.execute(query)
        assignments = res.scalars().all()

        items = [cls._format_assignment_response(a) for a in assignments]
        pages = math.ceil(total / page_size) if page_size > 0 else 1
        return items, total, pages
