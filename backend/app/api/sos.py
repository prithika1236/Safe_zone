from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin, require_police
from app.database.session import get_db
from app.models.enums import SOSStatus
from app.models.user import User
from app.schemas.sos import (
    CitizenSOSResponse,
    PaginatedSOSResponse,
    SOSResolveRequest,
    SOSResponse,
    SOSTriggerRequest,
)
from app.services.dispatch_service import DispatchService

citizen_router = APIRouter(prefix="/sos", tags=["Citizen Emergency SOS"])
police_router = APIRouter(prefix="/police/sos", tags=["Police SOS Dispatch Response"])
admin_router = APIRouter(prefix="/admin/sos", tags=["Admin SOS Monitoring"])


# ==============================================================================
# CITIZEN ENDPOINTS
# ==============================================================================


@citizen_router.post(
    "/trigger",
    response_model=CitizenSOSResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger Emergency SOS Panic Button",
    description="Citizen activates emergency panic trigger. Captures coordinates, creates PENDING SOS, and attempts spatial dispatch.",
)
async def trigger_emergency_sos(
    payload: SOSTriggerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await DispatchService.trigger_sos(
            db=db,
            citizen_id=current_user.id,
            payload=payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@citizen_router.get(
    "/active",
    response_model=Optional[CitizenSOSResponse],
    summary="Get Active SOS Distress Status for Authenticated Citizen",
)
async def get_active_citizen_sos(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await DispatchService.get_active_citizen_sos(
        db=db,
        citizen_id=current_user.id,
    )


@citizen_router.post(
    "/{sos_id}/cancel",
    response_model=CitizenSOSResponse,
    summary="Cancel / Disarm Active Emergency SOS",
)
async def cancel_emergency_sos(
    sos_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await DispatchService.cancel_sos(
            db=db,
            citizen_id=current_user.id,
            sos_id=sos_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ==============================================================================
# POLICE ENDPOINTS
# ==============================================================================


@police_router.get(
    "/active",
    response_model=Optional[SOSResponse],
    summary="Get Active SOS Alert Assigned to Officer's Patrol Unit",
)
async def get_police_active_sos(
    db: AsyncSession = Depends(get_db),
    police_user: User = Depends(require_police),
):
    return await DispatchService.police_get_active_sos(
        db=db,
        user_id=police_user.id,
    )


@police_router.post(
    "/{sos_id}/accept",
    response_model=SOSResponse,
    summary="Officer Accepts Emergency SOS Dispatch",
)
async def police_accept_sos(
    sos_id: int,
    db: AsyncSession = Depends(get_db),
    police_user: User = Depends(require_police),
):
    try:
        return await DispatchService.police_accept_sos(
            db=db,
            user_id=police_user.id,
            sos_id=sos_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@police_router.post(
    "/{sos_id}/en-route",
    response_model=SOSResponse,
    summary="Officer Departs and is EN ROUTE to Citizen Location",
)
async def police_en_route_sos(
    sos_id: int,
    db: AsyncSession = Depends(get_db),
    police_user: User = Depends(require_police),
):
    try:
        return await DispatchService.police_en_route_sos(
            db=db,
            user_id=police_user.id,
            sos_id=sos_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@police_router.post(
    "/{sos_id}/arrived",
    response_model=SOSResponse,
    summary="Officer Marks Arrival On Scene at Emergency Location",
)
async def police_arrived_sos(
    sos_id: int,
    db: AsyncSession = Depends(get_db),
    police_user: User = Depends(require_police),
):
    try:
        return await DispatchService.police_arrived_sos(
            db=db,
            user_id=police_user.id,
            sos_id=sos_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@police_router.post(
    "/{sos_id}/resolve",
    response_model=SOSResponse,
    summary="Officer Resolves Incident and Releases Patrol Unit",
)
async def police_resolve_sos(
    sos_id: int,
    payload: SOSResolveRequest = SOSResolveRequest(),
    db: AsyncSession = Depends(get_db),
    police_user: User = Depends(require_police),
):
    try:
        return await DispatchService.police_resolve_sos(
            db=db,
            user_id=police_user.id,
            sos_id=sos_id,
            resolution_notes=payload.resolution_notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ==============================================================================
# ADMIN ENDPOINTS
# ==============================================================================


@admin_router.get(
    "",
    response_model=PaginatedSOSResponse,
    summary="List all SOS Emergency Alerts (Admin Monitoring)",
)
async def admin_list_sos_alerts(
    status_filter: Optional[SOSStatus] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    items, total, pages = await DispatchService.admin_list_sos(
        db=db,
        status_filter=status_filter,
        page=page,
        page_size=page_size,
    )
    return PaginatedSOSResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )
