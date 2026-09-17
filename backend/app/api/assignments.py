"""
API Router for Patrol Unit to PRP Assignments.

Provides ADMIN controls for automated dispatch and manual assignment overrides,
and POLICE endpoints for active assignment tracking and operational lifecycle progression.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin, require_police
from app.database.session import get_db
from app.models.enums import AssignmentStatus
from app.models.user import User
from app.schemas.assignment import (
    AssignmentMatchResponse,
    AssignmentReassignRequest,
    AutoAssignmentRequest,
    AutoAssignmentResponse,
    ManualAssignmentRequest,
    PaginatedAssignmentsResponse,
)
from app.services.assignment_service import AssignmentService

admin_router = APIRouter(prefix="/admin/assignments", tags=["Admin Patrol Assignments"])
police_router = APIRouter(prefix="/police/assignments", tags=["Police Patrol Assignments"])


# ==============================================================================
# ADMIN ASSIGNMENT ENDPOINTS
# ==============================================================================


@admin_router.post(
    "/auto",
    response_model=AutoAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger automatic distance-optimal patrol to PRP dispatch",
)
async def auto_assign_patrols(
    payload: AutoAssignmentRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Execute optimal bipartite matching between available patrol units and approved PRPs."""
    return await AssignmentService.auto_assign_patrols(db=db, payload=payload)


@admin_router.post(
    "/manual",
    response_model=AssignmentMatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Manually assign a specific patrol unit to a PRP",
)
async def manual_assign_patrol(
    payload: ManualAssignmentRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Manually create an assignment with strict conflict and availability validation."""
    try:
        return await AssignmentService.manual_assign_patrol(db=db, payload=payload)
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@admin_router.get(
    "",
    response_model=PaginatedAssignmentsResponse,
    summary="List patrol assignments with filtering and pagination",
)
async def list_assignments(
    status_filter: Optional[AssignmentStatus] = Query(None, alias="status"),
    patrol_unit_id: Optional[int] = Query(None),
    optimization_run_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Retrieve historical and active patrol assignments."""
    items, total, pages = await AssignmentService.list_assignments(
        db=db,
        status=status_filter,
        patrol_unit_id=patrol_unit_id,
        optimization_run_id=optimization_run_id,
        page=page,
        page_size=page_size,
    )
    return PaginatedAssignmentsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@admin_router.post(
    "/{assignment_id}/cancel",
    response_model=AssignmentMatchResponse,
    summary="Cancel an assignment and free the patrol unit",
)
async def cancel_assignment(
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Cancel an assignment and release its patrol unit back to AVAILABLE status."""
    res = await AssignmentService.cancel_assignment(db=db, assignment_id=assignment_id)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignment with ID {assignment_id} not found",
        )
    return res


@admin_router.post(
    "/{assignment_id}/reassign",
    response_model=AssignmentMatchResponse,
    summary="Reassign an active assignment to a different patrol unit",
)
async def reassign_patrol(
    assignment_id: int,
    payload: AssignmentReassignRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Reassign an active assignment to a new patrol unit."""
    try:
        res = await AssignmentService.reassign_patrol(
            db=db,
            assignment_id=assignment_id,
            new_patrol_unit_id=payload.new_patrol_unit_id,
        )
        if not res:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assignment with ID {assignment_id} not found",
            )
        return res
    except ValueError as err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


# ==============================================================================
# POLICE ASSIGNMENT ENDPOINTS
# ==============================================================================


@police_router.get(
    "/current",
    response_model=Optional[AssignmentMatchResponse],
    summary="Fetch the current active assignment for the authenticated officer",
)
async def get_current_police_assignment(
    db: AsyncSession = Depends(get_db),
    police_user: User = Depends(require_police),
):
    """Retrieve active deployment assignment for the logged-in police officer."""
    return await AssignmentService.get_police_current_assignment(db=db, user_id=police_user.id)


@police_router.post(
    "/{assignment_id}/acknowledge",
    response_model=AssignmentMatchResponse,
    summary="Acknowledge receipt of an assignment (sets unit to EN_ROUTE)",
)
async def acknowledge_assignment(
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    police_user: User = Depends(require_police),
):
    """Officer acknowledges assignment and initiates travel (EN_ROUTE)."""
    res = await AssignmentService.update_assignment_status_by_police(
        db=db,
        assignment_id=assignment_id,
        user_id=police_user.id,
        new_status=AssignmentStatus.ACKNOWLEDGED,
    )
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    return res


@police_router.post(
    "/{assignment_id}/arrived",
    response_model=AssignmentMatchResponse,
    summary="Mark unit arrived on-scene at the designated PRP (sets unit to ON_SCENE)",
)
async def mark_arrived_at_prp(
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    police_user: User = Depends(require_police),
):
    """Officer marks arrival on scene at the assigned PRP (ON_SCENE)."""
    res = await AssignmentService.update_assignment_status_by_police(
        db=db,
        assignment_id=assignment_id,
        user_id=police_user.id,
        new_status=AssignmentStatus.ARRIVED,
    )
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    return res


@police_router.post(
    "/{assignment_id}/complete",
    response_model=AssignmentMatchResponse,
    summary="Complete assignment and release patrol unit back to AVAILABLE",
)
async def complete_assignment(
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    police_user: User = Depends(require_police),
):
    """Officer completes shift/deployment at PRP, releasing unit back to AVAILABLE."""
    res = await AssignmentService.update_assignment_status_by_police(
        db=db,
        assignment_id=assignment_id,
        user_id=police_user.id,
        new_status=AssignmentStatus.COMPLETED,
    )
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    return res
