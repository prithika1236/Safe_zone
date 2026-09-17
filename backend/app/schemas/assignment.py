"""Pydantic schemas for patrol unit to PRP assignment management and status tracking."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AssignmentStatus


class AutoAssignmentRequest(BaseModel):
    """Parameters to trigger automatic distance-optimal assignment."""
    optimization_run_id: Optional[int] = Field(None, description="Target optimization run ID (defaults to latest approved run).")
    shift: Optional[str] = Field(None, description="Target shift filter (e.g. MORNING, EVENING, NIGHT).")
    max_dispatch_distance_km: float = Field(30.0, gt=0.0, le=100.0, description="Max dispatch radius.")


class ManualAssignmentRequest(BaseModel):
    """Parameters to manually assign a specific patrol unit to a PRP."""
    patrol_unit_id: int = Field(..., description="ID of the patrol unit.")
    prp_location_id: int = Field(..., description="ID of the approved PRP location.")
    shift: str = Field("MORNING", description="Operational shift identifier.")


class AssignmentReassignRequest(BaseModel):
    """Payload to reassign an existing assignment to a new patrol unit."""
    new_patrol_unit_id: int = Field(..., description="ID of the new patrol unit.")


class AssignmentMatchResponse(BaseModel):
    """Detailed response schema for a patrol assignment."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    patrol_unit_id: int
    call_sign: str
    prp_location_id: int
    prp_name: str
    optimization_run_id: int
    shift: str
    status: AssignmentStatus
    distance_km: Optional[float] = None
    estimated_duration_minutes: Optional[float] = None
    priority_score: Optional[float] = None
    assigned_at: datetime
    acknowledged_at: Optional[datetime] = None
    arrived_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AutoAssignmentResponse(BaseModel):
    """Result of an automatic assignment execution run."""
    matched_count: int
    unassigned_prp_count: int
    unassigned_patrol_count: int
    assignments: List[AssignmentMatchResponse]


class PaginatedAssignmentsResponse(BaseModel):
    """Paginated list of patrol assignments."""
    items: List[AssignmentMatchResponse]
    total: int
    page: int
    page_size: int
    pages: int
