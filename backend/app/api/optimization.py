"""
Admin API Router for PRP Coverage Optimization and Management.

All endpoints are strictly protected and accessible only by ADMIN users.
Citizens are strictly forbidden from accessing exact strategic PRP locations.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.database.session import get_db
from app.models.enums import PRPStatus
from app.models.user import User
from app.schemas.optimization import (
    OptimizationResultResponse,
    OptimizationRunRequest,
    PaginatedOptimizationRunsResponse,
    PaginatedPRPLocationsResponse,
)
from app.services.optimization_service import OptimizationService

router = APIRouter(prefix="/admin/optimization", tags=["Admin PRP Optimization"])


@router.post(
    "/preview",
    response_model=OptimizationResultResponse,
    summary="Preview PRP optimization run without database persistence",
)
async def preview_optimization(
    payload: OptimizationRunRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Execute OR-Tools coverage optimization in preview mode (dry-run)."""
    return await OptimizationService.preview_optimization(db=db, payload=payload)


@router.post(
    "/run",
    response_model=OptimizationResultResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute and persist PRP optimization run",
)
async def execute_optimization_run(
    payload: OptimizationRunRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """
    Execute OR-Tools coverage optimization, persisting the OptimizationRun and
    generating PRPLocations in proposed (RECOMMENDED) status.
    """
    return await OptimizationService.run_optimization(
        db=db,
        payload=payload,
        user_id=admin_user.id,
    )


@router.get(
    "/runs",
    response_model=PaginatedOptimizationRunsResponse,
    summary="List historical optimization runs",
)
async def list_optimization_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Retrieve paginated historical optimization runs."""
    items, total, pages = await OptimizationService.list_optimization_runs(
        db=db,
        page=page,
        page_size=page_size,
    )
    return PaginatedOptimizationRunsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/runs/{run_id}",
    response_model=OptimizationResultResponse,
    summary="View optimization run details and PRPs",
)
async def get_optimization_run_details(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Retrieve details, metrics, and PRPs of a specific optimization run."""
    run = await OptimizationService.get_optimization_run(db=db, run_id=run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Optimization run with ID {run_id} not found",
        )
    return run


@router.post(
    "/runs/{run_id}/approve",
    response_model=OptimizationResultResponse,
    summary="Approve and activate an optimization run and its PRPs",
)
async def approve_optimization_run(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Approve an optimization run, transitioning its PRPs from RECOMMENDED to APPROVED."""
    updated = await OptimizationService.approve_optimization_run(db=db, run_id=run_id)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Optimization run with ID {run_id} not found",
        )
    return updated


@router.get(
    "/prps",
    response_model=PaginatedPRPLocationsResponse,
    summary="List active or filtered PRP locations",
)
async def list_prp_locations(
    status_filter: Optional[PRPStatus] = Query(None, alias="status"),
    run_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """Retrieve paginated PRP locations with optional status and run filters."""
    items, total, pages = await OptimizationService.list_prp_locations(
        db=db,
        status=status_filter,
        run_id=run_id,
        page=page,
        page_size=page_size,
    )
    return PaginatedPRPLocationsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )
