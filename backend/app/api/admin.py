from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.database.session import get_db
from app.models.enums import PatrolStatus
from app.schemas.patrol import (
    OperationalStatusSummary,
    PaginatedPatrolUnitsResponse,
    PaginatedPoliceOfficersResponse,
    PatrolUnitCreateRequest,
    PatrolUnitResponse,
    PatrolUnitStatusUpdateRequest,
    PatrolUnitUpdateRequest,
    PoliceOfficerCreateRequest,
    PoliceOfficerResponse,
    PoliceOfficerUpdateRequest,
)
from app.services.patrol_service import PatrolService

router = APIRouter(
    prefix="/admin",
    tags=["Admin Operational Management"],
    dependencies=[Depends(require_admin)],
)


# --- Police Officer Endpoints ---

@router.post(
    "/officers",
    response_model=PoliceOfficerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Police Officer Account",
    description="Admin creates a police account and linked operational officer profile.",
)
async def create_police_officer(
    payload: PoliceOfficerCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        officer = await PatrolService.create_police_officer(db, payload)
        return officer
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "/officers",
    response_model=PaginatedPoliceOfficersResponse,
    status_code=status.HTTP_200_OK,
    summary="List Police Officers",
    description="List all police officers with pagination and status filters.",
)
async def list_police_officers(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    is_on_duty: Optional[bool] = Query(None, description="Filter by duty status"),
    is_active: Optional[bool] = Query(None, description="Filter by account active status"),
):
    items, total, pages = await PatrolService.list_police_officers(
        db, page=page, page_size=page_size, is_on_duty=is_on_duty, is_active=is_active
    )
    return PaginatedPoliceOfficersResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/officers/{officer_id}",
    response_model=PoliceOfficerResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Police Officer Details",
)
async def get_police_officer(
    officer_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    officer = await PatrolService.get_police_officer(db, officer_id)
    if not officer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Police officer with ID {officer_id} not found",
        )
    return officer


@router.patch(
    "/officers/{officer_id}",
    response_model=PoliceOfficerResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Police Officer Details",
)
async def update_police_officer(
    officer_id: int,
    payload: PoliceOfficerUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        officer = await PatrolService.update_police_officer(db, officer_id, payload)
        if not officer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Police officer with ID {officer_id} not found",
            )
        return officer
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# --- Patrol Unit Endpoints ---

@router.post(
    "/patrols",
    response_model=PatrolUnitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Patrol Unit",
    description="Create a new patrol unit and optionally assign an officer.",
)
async def create_patrol_unit(
    payload: PatrolUnitCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        unit = await PatrolService.create_patrol_unit(db, payload)
        return unit
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "/patrols",
    response_model=PaginatedPatrolUnitsResponse,
    status_code=status.HTTP_200_OK,
    summary="List Patrol Units",
    description="List all patrol units with pagination and status filters.",
)
async def list_patrol_units(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    patrol_status: Optional[PatrolStatus] = Query(None, alias="status", description="Filter by patrol status"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
):
    items, total, pages = await PatrolService.list_patrol_units(
        db, page=page, page_size=page_size, status=patrol_status, is_active=is_active
    )
    return PaginatedPatrolUnitsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/patrols/{unit_id}",
    response_model=PatrolUnitResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Patrol Unit Details",
)
async def get_patrol_unit(
    unit_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    unit = await PatrolService.get_patrol_unit(db, unit_id)
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patrol unit with ID {unit_id} not found",
        )
    return unit


@router.patch(
    "/patrols/{unit_id}",
    response_model=PatrolUnitResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Patrol Unit Details",
)
async def update_patrol_unit(
    unit_id: int,
    payload: PatrolUnitUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        unit = await PatrolService.update_patrol_unit(db, unit_id, payload)
        if not unit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patrol unit with ID {unit_id} not found",
            )
        return unit
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.patch(
    "/patrols/{unit_id}/status",
    response_model=PatrolUnitResponse,
    status_code=status.HTTP_200_OK,
    summary="Set Patrol Unit Availability / Status",
)
async def set_patrol_unit_status(
    unit_id: int,
    payload: PatrolUnitStatusUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    unit = await PatrolService.set_patrol_unit_status(db, unit_id, payload.status)
    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patrol unit with ID {unit_id} not found",
        )
    return unit


# --- Operational Status Summary ---

@router.get(
    "/operations/summary",
    response_model=OperationalStatusSummary,
    status_code=status.HTTP_200_OK,
    summary="Get Current Operational Status Summary",
)
async def get_operational_summary(
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await PatrolService.get_operational_summary(db)
