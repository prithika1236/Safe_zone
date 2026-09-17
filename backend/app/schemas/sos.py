from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import SOSStatus


class SOSTriggerRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Citizen emergency latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Citizen emergency longitude")
    notes: Optional[str] = Field(None, description="Optional distress details/notes")


class SOSResolveRequest(BaseModel):
    resolution_notes: Optional[str] = Field(None, description="Officer notes upon resolving the incident")


class SOSResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    citizen_id: int
    status: SOSStatus
    latitude: float
    longitude: float
    assigned_patrol_unit_id: Optional[int] = None
    patrol_call_sign: Optional[str] = None
    patrol_unit_type: Optional[str] = None
    patrol_latitude: Optional[float] = None
    patrol_longitude: Optional[float] = None
    distance_meters: Optional[float] = None
    estimated_duration_seconds: Optional[float] = None
    trigger_time: datetime
    accepted_time: Optional[datetime] = None
    en_route_time: Optional[datetime] = None
    arrived_time: Optional[datetime] = None
    resolved_time: Optional[datetime] = None
    notes: Optional[str] = None
    citizen_name: Optional[str] = None
    citizen_phone: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CitizenSOSResponse(BaseModel):
    """
    Citizen-facing SOS status.
    CRITICAL PRIVACY GUARANTEE: Never exposes exact PRP locations or police fleet internals.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: SOSStatus
    latitude: float
    longitude: float
    patrol_assigned: bool
    patrol_call_sign: Optional[str] = None
    distance_meters: Optional[float] = None
    estimated_duration_seconds: Optional[float] = None
    trigger_time: datetime
    accepted_time: Optional[datetime] = None
    en_route_time: Optional[datetime] = None
    arrived_time: Optional[datetime] = None
    resolved_time: Optional[datetime] = None
    created_at: datetime


class PaginatedSOSResponse(BaseModel):
    items: List[SOSResponse]
    total: int
    page: int
    page_size: int
    pages: int
