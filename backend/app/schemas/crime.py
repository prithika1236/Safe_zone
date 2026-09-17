from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CrimeIncidentCreateRequest(BaseModel):
    incident_number: str = Field(..., min_length=1, max_length=64)
    category: str = Field(..., min_length=1, max_length=128)
    severity: int = Field(1, ge=1, le=5, description="Crime severity from 1 (Low) to 5 (Critical)")
    incident_time: datetime
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    description: Optional[str] = None
    is_active: bool = True


class CrimeIncidentUpdateRequest(BaseModel):
    category: Optional[str] = Field(None, min_length=1, max_length=128)
    severity: Optional[int] = Field(None, ge=1, le=5)
    incident_time: Optional[datetime] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class CrimeIncidentResponse(BaseModel):
    id: int
    incident_number: str
    category: str
    severity: int
    incident_time: datetime
    latitude: float
    longitude: float
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedCrimesResponse(BaseModel):
    items: List[CrimeIncidentResponse]
    total: int
    page: int
    page_size: int
    pages: int


class CSVRowError(BaseModel):
    row_number: int
    incident_number: Optional[str] = None
    error: str


class CSVImportSummaryResponse(BaseModel):
    total_rows: int
    imported_count: int
    failed_count: int
    errors: List[CSVRowError]
