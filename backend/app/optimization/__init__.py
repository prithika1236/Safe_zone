"""Optimization, risk scoring, coverage modeling, PRP solver, and assignment algorithms for SafeZone."""

from app.optimization.assignment import (
    AssignmentMatch,
    PatrolResource,
    PRPResource,
    assign_patrols_to_prps,
)
from app.optimization.candidate_generator import (
    CandidateGenerationConfig,
    CandidatePRP,
    CandidateStrategy,
    PredefinedLocation,
    generate_prp_candidates,
)
from app.optimization.coverage import (
    CandidateLocation,
    CoverageMatrix,
    DemandPoint,
    build_coverage_matrix,
)
from app.optimization.prp_optimizer import (
    PRPOptimizationResult,
    SelectedPRPItem,
    optimize_prp_coverage,
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
    # Coverage Modeling
    "DemandPoint",
    "CandidateLocation",
    "CoverageMatrix",
    "build_coverage_matrix",
    # OR-Tools PRP Optimizer
    "SelectedPRPItem",
    "PRPOptimizationResult",
    "optimize_prp_coverage",
    # Patrol Assignment
    "PatrolResource",
    "PRPResource",
    "AssignmentMatch",
    "assign_patrols_to_prps",
]
