from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import PatrolStatus


# --- Police Officer Schemas ---
class PoliceOfficerCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=32)
    badge_number: str = Field(..., min_length=1, max_length=64)
    rank: Optional[str] = Field(None, max_length=64)
    department: Optional[str] = Field(None, max_length=128)
    is_on_duty: bool = False


class PoliceOfficerUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=32)
    badge_number: Optional[str] = Field(None, min_length=1, max_length=64)
    rank: Optional[str] = Field(None, max_length=64)
    department: Optional[str] = Field(None, max_length=128)
    is_on_duty: Optional[bool] = None
    is_active: Optional[bool] = None


class PoliceOfficerResponse(BaseModel):
    id: int
    user_id: int
    email: EmailStr
    full_name: str
    phone_number: Optional[str] = None
    badge_number: str
    rank: Optional[str] = None
    department: Optional[str] = None
    is_on_duty: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedPoliceOfficersResponse(BaseModel):
    items: List[PoliceOfficerResponse]
    total: int
    page: int
    page_size: int
    pages: int


# --- Patrol Unit Schemas ---
class PatrolUnitCreateRequest(BaseModel):
    call_sign: str = Field(..., min_length=1, max_length=64)
    officer_id: Optional[int] = None
    status: PatrolStatus = PatrolStatus.OFF_DUTY


class PatrolUnitUpdateRequest(BaseModel):
    call_sign: Optional[str] = Field(None, min_length=1, max_length=64)
    officer_id: Optional[int] = None
    status: Optional[PatrolStatus] = None
    is_active: Optional[bool] = None


class PatrolUnitStatusUpdateRequest(BaseModel):
    status: PatrolStatus


class PatrolUnitResponse(BaseModel):
    id: int
    call_sign: str
    officer_id: Optional[int] = None
    officer_badge: Optional[str] = None
    officer_name: Optional[str] = None
    status: PatrolStatus
    is_active: bool
    last_location_update: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedPatrolUnitsResponse(BaseModel):
    items: List[PatrolUnitResponse]
    total: int
    page: int
    page_size: int
    pages: int


# --- Operational Status Summary Schema ---
class OperationalStatusSummary(BaseModel):
    total_officers: int
    on_duty_officers: int
    total_patrol_units: int
    available_patrol_units: int
    busy_patrol_units: int
    en_route_patrol_units: int
    off_duty_patrol_units: int
