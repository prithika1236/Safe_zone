"""
SafeZone Patrol to PRP Optimal Assignment Engine.

Provides deterministic, transparent minimum-distance bipartite matching
between available police patrol units and approved Priority Response Points (PRPs).
Uses Linear Sum Assignment optimization without machine learning.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence
from ortools.linear_solver import pywraplp

from app.services.location_service import haversine_distance_km, validate_coordinates


@dataclass
class PatrolResource:
    """Operational representation of an active patrol unit available for deployment."""
    id: int
    call_sign: str
    latitude: float
    longitude: float
    officer_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not validate_coordinates(self.latitude, self.longitude):
            raise ValueError(f"Invalid patrol coordinates for {self.call_sign}: ({self.latitude}, {self.longitude})")


@dataclass
class PRPResource:
    """Operational representation of an approved Priority Response Point."""
    id: int
    name: str
    latitude: float
    longitude: float
    optimization_run_id: int
    priority_score: float = 0.0
    shift: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not validate_coordinates(self.latitude, self.longitude):
            raise ValueError(f"Invalid PRP coordinates for {self.name}: ({self.latitude}, {self.longitude})")


@dataclass
class AssignmentMatch:
    """Result of matching a patrol unit to a specific PRP location."""
    patrol_unit_id: int
    call_sign: str
    prp_location_id: int
    prp_name: str
    optimization_run_id: int
    distance_km: float
    estimated_duration_minutes: float
    priority_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


def assign_patrols_to_prps(
    patrol_units: Sequence[PatrolResource],
    prp_locations: Sequence[PRPResource],
    max_dispatch_distance_km: float = 30.0,
    average_speed_kmh: float = 35.0,
) -> List[AssignmentMatch]:
    """
    Solve minimum-distance bipartite matching (Linear Sum Assignment) to match
    available patrol units to approved PRPs.

    Objective:
        Minimize sum_{i in Units, j in PRPs} (Distance_{i,j} * x_{i,j})

    Constraints:
        1. sum_{j in PRPs} x_{i,j} <= 1 for each patrol unit i (each unit gets at most 1 PRP).
        2. sum_{i in Units} x_{i,j} <= 1 for each PRP j (each PRP gets at most 1 unit).
        3. Total matched pairs = min(len(patrol_units), len(prp_locations)).

    Args:
        patrol_units: Available patrol units with known current positions.
        prp_locations: Target approved PRPs requiring patrol deployment.
        max_dispatch_distance_km: Max allowable distance threshold.
        average_speed_kmh: Heuristic vehicle travel speed for ETA calculation.

    Returns:
        List of optimal AssignmentMatch items sorted by priority score and distance.
    """
    num_units = len(patrol_units)
    num_prps = len(prp_locations)

    if num_units == 0 or num_prps == 0:
        return []

    # Calculate distance cost matrix
    cost_matrix: List[List[float]] = []
    for u in patrol_units:
        row: List[float] = []
        for p in prp_locations:
            d = haversine_distance_km(u.latitude, u.longitude, p.latitude, p.longitude)
            row.append(d)
        cost_matrix.append(row)

    # Instantiate MIP Solver
    solver = pywraplp.Solver.CreateSolver("CBC")
    if not solver:
        solver = pywraplp.Solver.CreateSolver("SCIP")
    if not solver:
        raise RuntimeError("No suitable OR-Tools MIP solver available (CBC/SCIP).")

    # Decision variables x[i][j] = 1 if unit i is assigned to PRP j, 0 otherwise
    x = {}
    for i in range(num_units):
        for j in range(num_prps):
            x[i, j] = solver.BoolVar(f"x_{i}_{j}")

    # Objective: Minimize total dispatch distance (with penalty for exceeding max threshold)
    objective = solver.Objective()
    for i in range(num_units):
        for j in range(num_prps):
            dist = cost_matrix[i][j]
            weight = dist if dist <= max_dispatch_distance_km else (dist + 1000.0)
            objective.SetCoefficient(x[i, j], float(weight))
    objective.SetMinimization()

    # Constraint 1: Each patrol unit assigned to at most 1 PRP
    for i in range(num_units):
        unit_constraint = solver.Constraint(0, 1.0, f"unit_{i}")
        for j in range(num_prps):
            unit_constraint.SetCoefficient(x[i, j], 1.0)

    # Constraint 2: Each PRP assigned to at most 1 patrol unit
    for j in range(num_prps):
        prp_constraint = solver.Constraint(0, 1.0, f"prp_{j}")
        for i in range(num_units):
            prp_constraint.SetCoefficient(x[i, j], 1.0)

    # Constraint 3: Match exactly min(num_units, num_prps)
    target_matches = min(num_units, num_prps)
    total_constraint = solver.Constraint(target_matches, target_matches, "total_matches")
    for i in range(num_units):
        for j in range(num_prps):
            total_constraint.SetCoefficient(x[i, j], 1.0)

    # Solve
    status = solver.Solve()

    matches: List[AssignmentMatch] = []
    if status in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
        for i in range(num_units):
            for j in range(num_prps):
                if x[i, j].solution_value() > 0.5:
                    u = patrol_units[i]
                    p = prp_locations[j]
                    dist = cost_matrix[i][j]
                    duration_mins = round((dist / average_speed_kmh) * 60.0, 1)

                    matches.append(
                        AssignmentMatch(
                            patrol_unit_id=u.id,
                            call_sign=u.call_sign,
                            prp_location_id=p.id,
                            prp_name=p.name,
                            optimization_run_id=p.optimization_run_id,
                            distance_km=dist,
                            estimated_duration_minutes=duration_mins,
                            priority_score=p.priority_score,
                            metadata={
                                "officer_name": u.officer_name,
                                "prp_shift": p.shift,
                            },
                        )
                    )

    # Sort matches deterministically by priority score desc, then distance asc
    matches.sort(key=lambda m: (-m.priority_score, m.distance_km))
    return matches
