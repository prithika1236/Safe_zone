"""Pydantic schemas for PRP coverage optimization runs, previews, and PRP location management."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import OptimizationRunStatus, PRPStatus
from app.schemas.prp_candidate import PredefinedLocationSchema
from app.schemas.risk import RiskWeightConfigSchema


class OptimizationRunRequest(BaseModel):
    """Parameters for running or previewing PRP coverage optimization."""
    shift: str = Field("MORNING", description="Operational shift context ('MORNING', 'AFTERNOON', 'NIGHT').")
    available_patrol_count: int = Field(3, ge=1, le=50, description="Available patrol unit limit (P).")
    coverage_radius_km: float = Field(3.0, gt=0.0, le=25.0, description="Operational patrol coverage radius in km.")
    cluster_radius_km: float = Field(1.0, gt=0.0, le=10.0, description="Candidate clustering radius threshold in km.")
    min_candidate_separation_km: float = Field(0.3, ge=0.0, le=5.0, description="Minimum separation between distinct candidate points.")
    max_candidates: int = Field(30, ge=1, le=100, description="Max pool size of candidates generated.")
    weights_config: Optional[RiskWeightConfigSchema] = None
    predefined_locations: Optional[List[PredefinedLocationSchema]] = None


class SelectedPRPResponse(BaseModel):
    """Schema for an individual selected PRP location."""
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    name: str
    latitude: float
    longitude: float
    coverage_radius_km: float
    priority_score: float
    status: str
    covered_demand_count: int = 0
    covered_demand_weight: float = 0.0
    strategy: Optional[str] = "MCLP_OPTIMIZED"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UncoveredDemandPointResponse(BaseModel):
    """Demand point not covered in the current optimization run."""
    id: int
    latitude: float
    longitude: float
    weight: float
    category: str = "Demand"


class OptimizationResultResponse(BaseModel):
    """Comprehensive response for an optimization run or preview."""
    model_config = ConfigDict(from_attributes=True)

    run_id: Optional[int] = None
    shift: str
    available_patrol_count: int
    coverage_radius_km: float
    selected_count: int
    total_demand_risk: float
    covered_demand_risk: float
    coverage_percentage: float
    solver_status: str
    selected_prps: List[SelectedPRPResponse]
    uncovered_demand_points: List[UncoveredDemandPointResponse]
    metrics: Dict[str, Any] = Field(default_factory=dict)
    run_time_seconds: float
    created_at: Optional[datetime] = None


class PRPLocationResponse(BaseModel):
    """Schema for a persisted PRPLocation entity."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    optimization_run_id: int
    name: str
    latitude: float
    longitude: float
    coverage_radius_km: float
    priority_score: float
    status: PRPStatus
    created_at: datetime
    updated_at: datetime


class PRPStatusUpdateRequest(BaseModel):
    """Request payload to update the operational status of a PRP."""
    status: PRPStatus = Field(..., description="Target PRP status: RECOMMENDED, APPROVED, ACTIVE, INACTIVE, REJECTED.")


class PaginatedOptimizationRunsResponse(BaseModel):
    """Paginated list of historical optimization runs."""
    items: List[OptimizationResultResponse]
    total: int
    page: int
    page_size: int
    pages: int


class PaginatedPRPLocationsResponse(BaseModel):
    """Paginated list of PRP locations."""
    items: List[PRPLocationResponse]
    total: int
    page: int
    page_size: int
    pages: int
