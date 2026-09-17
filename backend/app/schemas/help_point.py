from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SafeHelpPointType


class SafeHelpPointCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    category: SafeHelpPointType = SafeHelpPointType.HELP_DESK
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    address: Optional[str] = Field(None, max_length=512)
    contact_number: Optional[str] = Field(None, max_length=32)
    is_verified: bool = False
    is_active: bool = True


class SafeHelpPointUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[SafeHelpPointType] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    address: Optional[str] = None
    contact_number: Optional[str] = None
    is_verified: Optional[bool] = None
    is_active: Optional[bool] = None


class SafeHelpPointResponse(BaseModel):
    id: int
    name: str
    category: SafeHelpPointType
    latitude: float
    longitude: float
    address: Optional[str] = None
    contact_number: Optional[str] = None
    is_verified: bool
    is_active: bool
    distance_km: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedHelpPointsResponse(BaseModel):
    items: List[SafeHelpPointResponse]
    total: int
    page: int
    page_size: int
    pages: int


class HelpPointCSVRowError(BaseModel):
    row_number: int
    name: Optional[str] = None
    error: str


class HelpPointCSVImportSummary(BaseModel):
    total_rows: int
    imported_count: int
    failed_count: int
    errors: List[HelpPointCSVRowError]
