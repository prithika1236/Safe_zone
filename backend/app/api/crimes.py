from datetime import datetime
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.database.session import get_db
from app.schemas.crime import (
    CSVImportSummaryResponse,
    CrimeIncidentCreateRequest,
    CrimeIncidentResponse,
    CrimeIncidentUpdateRequest,
    PaginatedCrimesResponse,
)
from app.services.crime_service import CrimeService

router = APIRouter(
    prefix="/crimes",
    tags=["Crime Incident Management"],
    dependencies=[Depends(require_admin)],
)


@router.post(
    "",
    response_model=CrimeIncidentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Crime Incident",
)
async def create_crime(
    payload: CrimeIncidentCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        crime = await CrimeService.create_crime(db, payload)
        return crime
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "",
    response_model=PaginatedCrimesResponse,
    status_code=status.HTTP_200_OK,
    summary="List Crime Incidents",
)
async def list_crimes(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
    start_date: Optional[datetime] = Query(None, description="Filter incidents from start date"),
    end_date: Optional[datetime] = Query(None, description="Filter incidents up to end date"),
    category: Optional[str] = Query(None, description="Filter by category substring"),
    min_severity: Optional[int] = Query(None, ge=1, le=5, description="Filter minimum severity (1-5)"),
    max_severity: Optional[int] = Query(None, ge=1, le=5, description="Filter maximum severity (1-5)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search term for incident number or description"),
):
    items, total, pages = await CrimeService.list_crimes(
        db,
        page=page,
        page_size=page_size,
        start_date=start_date,
        end_date=end_date,
        category=category,
        min_severity=min_severity,
        max_severity=max_severity,
        is_active=is_active,
        search=search,
    )
    return PaginatedCrimesResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get(
    "/{crime_id}",
    response_model=CrimeIncidentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Crime Incident Details",
)
async def get_crime(
    crime_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    crime = await CrimeService.get_crime(db, crime_id)
    if not crime:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crime incident with ID {crime_id} not found",
        )
    return crime


@router.patch(
    "/{crime_id}",
    response_model=CrimeIncidentResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Crime Incident",
)
async def update_crime(
    crime_id: int,
    payload: CrimeIncidentUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    crime = await CrimeService.update_crime(db, crime_id, payload)
    if not crime:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crime incident with ID {crime_id} not found",
        )
    return crime


@router.delete(
    "/{crime_id}",
    status_code=status.HTTP_200_OK,
    summary="Deactivate Crime Incident",
)
async def deactivate_crime(
    crime_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    success = await CrimeService.deactivate_crime(db, crime_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crime incident with ID {crime_id} not found",
        )
    return {"message": f"Crime incident {crime_id} successfully deactivated"}


@router.post(
    "/import-csv",
    response_model=CSVImportSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Import Crimes from CSV",
    description="Upload a CSV file containing crime incidents for bulk ingestion with tolerant row-level validation.",
)
async def import_crimes_csv(
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
        csv_text = content_bytes.decode("utf-8-sig")  # handle UTF-8 with or without BOM
        summary = await CrimeService.import_csv(db, csv_text)
        return summary
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to decode CSV file as UTF-8 text",
        )
