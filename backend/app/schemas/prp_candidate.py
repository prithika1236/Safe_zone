"""Pydantic schemas for PRP candidate generation requests and responses."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.risk import RiskScoreBreakdownResponse, RiskWeightConfigSchema


class PredefinedLocationSchema(BaseModel):
    """Schema for predefined candidate locations (e.g. police stations)."""
    name: str = Field(..., description="Facility or location label.")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    category: Optional[str] = Field("OPERATIONAL_FACILITY", description="Location type classification.")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CandidateGenerationConfigSchema(BaseModel):
    """Configuration for PRP candidate generation."""
    strategy: str = Field("CLUSTER_CENTROID", description="Generation strategy: CLUSTER_CENTROID, PREDEFINED_OPERATIONAL, HYBRID.")
    cluster_radius_km: float = Field(1.0, gt=0.0, description="Clustering distance threshold in km.")
    min_candidate_separation_km: float = Field(0.3, ge=0.0, description="Minimum separation between distinct candidates in km.")
    min_incidents_per_cluster: int = Field(1, ge=1, description="Minimum incidents to form a cluster candidate.")
    max_candidates: int = Field(25, ge=1, description="Max candidate PRPs returned.")
    coverage_radius_km: float = Field(2.0, gt=0.0, description="Coverage radius for evaluating local risk.")
    risk_config: Optional[RiskWeightConfigSchema] = None


class CandidatePRPResponse(BaseModel):
    """Schema for a generated PRP candidate."""
    model_config = ConfigDict(from_attributes=True)

    candidate_id: str
    latitude: float
    longitude: float
    strategy: str
    incident_count: int
    source_incident_ids: List[int]
    risk_score: float
    risk_breakdown: RiskScoreBreakdownResponse
    reasoning: str
    coverage_radius_km: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CandidateGenerationRequest(BaseModel):
    """Request payload for generating PRP candidates."""
    shift: Optional[str] = Field(None, description="Target shift: MORNING, AFTERNOON, NIGHT.")
    reference_time: Optional[datetime] = Field(None, description="Anchor datetime for recency decay.")
    predefined_locations: Optional[List[PredefinedLocationSchema]] = None
    config: Optional[CandidateGenerationConfigSchema] = None
