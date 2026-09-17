"""Pydantic schemas for risk assessment, scoring configuration, and breakdown details."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RiskWeightConfigSchema(BaseModel):
    """Configurable weights for risk scoring calculation."""
    weight_frequency: float = Field(0.25, ge=0.0, description="Weight for incident frequency volume.")
    weight_severity: float = Field(0.30, ge=0.0, description="Weight for mean incident severity.")
    weight_recency: float = Field(0.25, ge=0.0, description="Weight for recency exponential decay.")
    weight_time: float = Field(0.20, ge=0.0, description="Weight for time-of-day/shift proximity.")
    decay_lambda: float = Field(0.05, gt=0.0, description="Exponential decay lambda factor.")
    max_frequency_benchmark: int = Field(50, gt=0, description="Incident count threshold for 100% frequency score.")
    severity_scale_max: float = Field(5.0, gt=0.0, description="Maximum scale value for severity normalization.")


class LocationRiskRequest(BaseModel):
    """Request schema for spatial risk assessment around a coordinate."""
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Target geographic latitude.")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Target geographic longitude.")
    radius_km: float = Field(3.0, gt=0.0, le=50.0, description="Search radius in kilometers.")
    shift: Optional[str] = Field(None, description="Operational shift context ('MORNING', 'AFTERNOON', 'NIGHT').")
    reference_time: Optional[datetime] = Field(None, description="Reference point in time (defaults to now).")
    weights_config: Optional[RiskWeightConfigSchema] = Field(None, description="Custom weight configuration.")


class RiskScoreBreakdownResponse(BaseModel):
    """Detailed explainable breakdown of computed risk score."""
    total_risk_score: float = Field(..., ge=0.0, le=100.0, description="Composite normalized risk score (0-100).")
    frequency_score: float = Field(..., ge=0.0, le=100.0, description="Incident frequency score component.")
    severity_score: float = Field(..., ge=0.0, le=100.0, description="Incident severity score component.")
    recency_score: float = Field(..., ge=0.0, le=100.0, description="Incident recency score component.")
    time_score: float = Field(..., ge=0.0, le=100.0, description="Time-of-day proximity score component.")
    frequency_contribution: float = Field(..., description="Weighted contribution to total score.")
    severity_contribution: float = Field(..., description="Weighted contribution to total score.")
    recency_contribution: float = Field(..., description="Weighted contribution to total score.")
    time_contribution: float = Field(..., description="Weighted contribution to total score.")
    incident_count: int = Field(..., description="Number of valid incidents analyzed.")
    details: Dict[str, Any] = Field(default_factory=dict, description="Metadata and configuration details.")


class RiskScoreRecordRead(BaseModel):
    """Schema for persisted RiskScore entity."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    latitude: float
    longitude: float
    grid_identifier: Optional[str] = None
    frequency_score: float
    severity_score: float
    recency_score: float
    time_score: float
    total_risk_score: float
    calculated_at: datetime
