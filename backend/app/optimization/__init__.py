"""Optimization, risk scoring, and PRP candidate generation algorithms for SafeZone."""

from app.optimization.candidate_generator import (
    CandidateGenerationConfig,
    CandidatePRP,
    CandidateStrategy,
    PredefinedLocation,
    generate_prp_candidates,
)
from app.optimization.risk_scoring import (
    DEFAULT_SEVERITY_MAPPING,
    SHIFT_CENTER_HOURS,
    IncidentRiskItem,
    RiskScoreBreakdown,
    RiskScoringConfig,
    calculate_circular_hour_distance,
    calculate_risk,
    compute_recency_factor,
    compute_time_factor,
    get_shift_target_hour,
)

__all__ = [
    # Risk Engine
    "DEFAULT_SEVERITY_MAPPING",
    "SHIFT_CENTER_HOURS",
    "IncidentRiskItem",
    "RiskScoreBreakdown",
    "RiskScoringConfig",
    "calculate_circular_hour_distance",
    "calculate_risk",
    "compute_recency_factor",
    "compute_time_factor",
    "get_shift_target_hour",
    # PRP Candidate Generation
    "CandidateStrategy",
    "PredefinedLocation",
    "CandidateGenerationConfig",
    "CandidatePRP",
    "generate_prp_candidates",
]
