"""
SafeZone Spatial Coverage Matrix Builder.

Computes bipartite adjacency relationships between candidate Priority Response Points (PRPs)
and geographic crime demand points within a specified operational coverage radius.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence
from app.services.location_service import haversine_distance_km, validate_coordinates


@dataclass
class DemandPoint:
    """Geographic point representing an incident or weighted crime demand."""
    id: int
    latitude: float
    longitude: float
    weight: float = 1.0
    category: str = "Demand"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not validate_coordinates(self.latitude, self.longitude):
            raise ValueError(f"Invalid demand coordinates: ({self.latitude}, {self.longitude})")
        if self.weight < 0.0:
            raise ValueError("Demand weight must be non-negative.")


@dataclass
class CandidateLocation:
    """Geographic point representing a candidate patrol placement location."""
    id: str
    latitude: float
    longitude: float
    name: str = "Candidate"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not validate_coordinates(self.latitude, self.longitude):
            raise ValueError(f"Invalid candidate coordinates: ({self.latitude}, {self.longitude})")


@dataclass
class CoverageMatrix:
    """Bipartite spatial coverage mapping between candidate PRPs and demand points."""
    candidates: List[CandidateLocation]
    demand_points: List[DemandPoint]
    coverage_radius_km: float
    # Mapping: candidate_index (j) -> list of demand_point_indices (i) covered by candidate j
    candidate_to_demand: Dict[int, List[int]] = field(default_factory=dict)
    # Mapping: demand_point_index (i) -> list of candidate_indices (j) that cover demand point i
    demand_to_candidates: Dict[int, List[int]] = field(default_factory=dict)
    # Total weight of demand points covered by each candidate individually
    candidate_coverage_weights: Dict[int, float] = field(default_factory=dict)
    # Total weight across all demand points
    total_demand_weight: float = 0.0


def build_coverage_matrix(
    candidates: Sequence[CandidateLocation],
    demand_points: Sequence[DemandPoint],
    coverage_radius_km: float = 2.0,
) -> CoverageMatrix:
    """
    Construct spatial coverage matrix between candidate locations and demand points.

    Args:
        candidates: List of candidate placement coordinates.
        demand_points: List of weighted demand/incident coordinates.
        coverage_radius_km: Spatial threshold in kilometers.

    Returns:
        CoverageMatrix with complete bidirectional indices and weight metrics.
    """
    if coverage_radius_km <= 0.0:
        raise ValueError("coverage_radius_km must be strictly positive (> 0.0).")

    cand_list = list(candidates)
    demand_list = list(demand_points)

    cand_to_dem: Dict[int, List[int]] = {j: [] for j in range(len(cand_list))}
    dem_to_cand: Dict[int, List[int]] = {i: [] for i in range(len(demand_list))}
    cand_weights: Dict[int, float] = {j: 0.0 for j in range(len(cand_list))}

    total_weight = 0.0
    for i, dem in enumerate(demand_list):
        total_weight += dem.weight

    for j, cand in enumerate(cand_list):
        for i, dem in enumerate(demand_list):
            dist = haversine_distance_km(cand.latitude, cand.longitude, dem.latitude, dem.longitude)
            if dist <= coverage_radius_km:
                cand_to_dem[j].append(i)
                dem_to_cand[i].append(j)
                cand_weights[j] += dem.weight

    return CoverageMatrix(
        candidates=cand_list,
        demand_points=demand_list,
        coverage_radius_km=coverage_radius_km,
        candidate_to_demand=cand_to_dem,
        demand_to_candidates=dem_to_cand,
        candidate_coverage_weights=cand_weights,
        total_demand_weight=round(total_weight, 4),
    )
