from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.database.session import get_db
from app.models.enums import SafeHelpPointType
from app.models.user import User
from app.schemas.help_point import (
    HelpPointCSVImportSummary,
    PaginatedHelpPointsResponse,
    SafeHelpPointCreateRequest,
    SafeHelpPointResponse,
    SafeHelpPointUpdateRequest,
)
from app.services.help_point_service import HelpPointService

router = APIRouter(prefix="/help-points", tags=["Safe Help Points"])


class VerificationUpdateRequest(BaseModel):
    is_verified: bool


class ActivationUpdateRequest(BaseModel):
    is_active: bool


# --- Citizen / Public Endpoints (Strictly Verified + Active) ---

@router.get(
    "/public",
    response_model=PaginatedHelpPointsResponse,
    status_code=status.HTTP_200_OK,
    summary="List Verified Safe Help Points (Citizen)",
    description="Retrieve list of verified and active public safe help points.",
)
async def list_public_help_points(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    category: Optional[SafeHelpPointType] = Query(None, description="Filter by facility type"),
):
    items, total, pages = await HelpPointService.list_public_help_points(
        db, page=page, page_size=page_size, category=category
    )
    return PaginatedHelpPointsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/nearby",
    response_model=List[SafeHelpPointResponse],
    status_code=status.HTTP_200_OK,
    summary="Find Nearby Safe Help Points (Citizen)",
    description="Query verified and active Safe Help Points within a radial distance from coordinates.",
)
async def get_nearby_help_points(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Current latitude"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Current longitude"),
    radius_km: float = Query(5.0, gt=0.0, le=50.0, description="Search radius in km"),
    category: Optional[SafeHelpPointType] = Query(None, description="Optional facility category filter"),
    limit: int = Query(20, ge=1, le=100),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    return await HelpPointService.query_nearby_help_points(
        db,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        category=category,
        limit=limit,
    )


# --- Admin Management Endpoints ---

@router.post(
    "",
    response_model=SafeHelpPointResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Safe Help Point (Admin)",
    dependencies=[Depends(require_admin)],
)
async def create_help_point(
    payload: SafeHelpPointCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await HelpPointService.create_help_point(db, payload)


@router.get(
    "",
    response_model=PaginatedHelpPointsResponse,
    status_code=status.HTTP_200_OK,
    summary="List All Safe Help Points (Admin)",
    description="Admin listing supporting full status and verification filtering.",
    dependencies=[Depends(require_admin)],
)
async def list_all_help_points(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    category: Optional[SafeHelpPointType] = Query(None),
    is_verified: Optional[bool] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
):
    items, total, pages = await HelpPointService.list_help_points(
        db,
        page=page,
        page_size=page_size,
        category=category,
        is_verified=is_verified,
        is_active=is_active,
        search=search,
    )
    return PaginatedHelpPointsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/{hp_id}",
    response_model=SafeHelpPointResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Safe Help Point Details (Admin)",
    dependencies=[Depends(require_admin)],
)
async def get_help_point(
    hp_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    hp = await HelpPointService.get_help_point(db, hp_id)
    if not hp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Safe Help Point with ID {hp_id} not found",
        )
    return hp


@router.patch(
    "/{hp_id}",
    response_model=SafeHelpPointResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Safe Help Point (Admin)",
    dependencies=[Depends(require_admin)],
)
async def update_help_point(
    hp_id: int,
    payload: SafeHelpPointUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    hp = await HelpPointService.update_help_point(db, hp_id, payload)
    if not hp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Safe Help Point with ID {hp_id} not found",
        )
    return hp


@router.patch(
    "/{hp_id}/verification",
    response_model=SafeHelpPointResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify/Unverify Safe Help Point (Admin)",
    dependencies=[Depends(require_admin)],
)
async def toggle_verification(
    hp_id: int,
    payload: VerificationUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    hp = await HelpPointService.toggle_verification(db, hp_id, payload.is_verified)
    if not hp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Safe Help Point with ID {hp_id} not found",
        )
    return hp


@router.patch(
    "/{hp_id}/activation",
    response_model=SafeHelpPointResponse,
    status_code=status.HTTP_200_OK,
    summary="Activate/Deactivate Safe Help Point (Admin)",
    dependencies=[Depends(require_admin)],
)
async def toggle_activation(
    hp_id: int,
    payload: ActivationUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    hp = await HelpPointService.toggle_activation(db, hp_id, payload.is_active)
    if not hp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Safe Help Point with ID {hp_id} not found",
        )
    return hp


@router.post(
    "/import-csv",
    response_model=HelpPointCSVImportSummary,
    status_code=status.HTTP_200_OK,
    summary="Import Safe Help Points from CSV (Admin)",
    dependencies=[Depends(require_admin)],
)
async def import_help_points_csv(
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be a valid .csv file",
        )

    try:
        content_bytes = await file.read()
        csv_text = content_bytes.decode("utf-8-sig")
        return await HelpPointService.import_csv(db, csv_text)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to decode CSV file as UTF-8 text",
        )
