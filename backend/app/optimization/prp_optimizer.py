"""
SafeZone Maximal Covering Location Problem (MCLP) Optimizer.

Implements integer linear programming optimization using Google OR-Tools to select
an optimal subset of Priority Response Points (PRPs) that maximize unique covered
weighted crime risk within available patrol resource limits.
"""

from dataclasses import dataclass, field
import time
from typing import Any, Dict, List, Optional, Sequence, Union
from ortools.linear_solver import pywraplp

from app.optimization.candidate_generator import CandidatePRP
from app.optimization.coverage import (
    CandidateLocation,
    CoverageMatrix,
    DemandPoint,
    build_coverage_matrix,
)


@dataclass
class SelectedPRPItem:
    """Details of a selected PRP location from the optimization solver."""
    candidate_id: str
    latitude: float
    longitude: float
    name: str
    coverage_radius_km: float
    covered_demand_count: int
    covered_demand_weight: float
    strategy: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PRPOptimizationResult:
    """Comprehensive output of the OR-Tools PRP coverage optimization run."""
    selected_prps: List[SelectedPRPItem]
    total_demand_risk: float
    covered_demand_risk: float
    coverage_percentage: float
    uncovered_demand_points: List[DemandPoint]
    selected_count: int
    solver_status: str
    run_time_seconds: float
    run_parameters: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)


def optimize_prp_coverage(
    candidates: Sequence[Union[CandidateLocation, CandidatePRP, Dict[str, Any]]],
    demand_points: Sequence[DemandPoint],
    available_patrol_count: int,
    coverage_radius_km: float = 2.0,
    shift: Optional[str] = None,
    solver_timeout_seconds: float = 10.0,
) -> PRPOptimizationResult:
    """
    Solve Maximal Covering Location Problem (MCLP) using Google OR-Tools.

    Objective:
        Maximize unique covered weighted crime risk (sum_{i in I} w_i * y_i).
        Does NOT double count risk covered by multiple selected PRPs.

    Constraints:
        1. sum_{j in J} x_j <= available_patrol_count (patrol capacity constraint).
        2. y_i <= sum_{j in N_i} x_j for each demand point i (coverage indicator constraint).

    Args:
        candidates: Pool of candidate PRP locations.
        demand_points: Weighted crime demand points.
        available_patrol_count: Number of available patrol units (P).
        coverage_radius_km: Spatial coverage radius threshold in kilometers.
        shift: Operational shift context ('MORNING', 'AFTERNOON', 'NIGHT').
        solver_timeout_seconds: Max solver execution time limit.

    Returns:
        PRPOptimizationResult with selected PRPs, covered risk metrics, and solver status.
    """
    start_time = time.time()

    # Standardize candidates into CandidateLocation instances
    standardized_cands: List[CandidateLocation] = []
    cand_sources: List[Any] = []

    for idx, c in enumerate(candidates):
        cand_id = getattr(c, "candidate_id", None) or getattr(c, "id", None) or f"CAND-{idx + 1:03d}"
        lat = getattr(c, "latitude", None) or (c.get("latitude") if isinstance(c, dict) else None)
        lng = getattr(c, "longitude", None) or (c.get("longitude") if isinstance(c, dict) else None)
        name = getattr(c, "name", None) or getattr(c, "candidate_id", f"PRP-{idx + 1:03d}")
        meta = getattr(c, "metadata", {}) if hasattr(c, "metadata") else (c.get("metadata", {}) if isinstance(c, dict) else {})
        strat = getattr(c, "strategy", "OPTIMIZATION_CANDIDATE")

        if lat is not None and lng is not None:
            cl = CandidateLocation(
                id=str(cand_id),
                latitude=float(lat),
                longitude=float(lng),
                name=str(name),
                metadata={"strategy": strat, **meta},
            )
            standardized_cands.append(cl)
            cand_sources.append(c)

    num_candidates = len(standardized_cands)
    num_demand = len(demand_points)
    total_demand_risk = round(sum(d.weight for d in demand_points), 4)

    run_params = {
        "shift": shift,
        "available_patrol_count": available_patrol_count,
        "coverage_radius_km": coverage_radius_km,
        "num_candidates": num_candidates,
        "num_demand_points": num_demand,
        "solver_timeout_seconds": solver_timeout_seconds,
    }

    # Edge Case 1: Zero patrols available or zero candidates
    if available_patrol_count <= 0 or num_candidates == 0:
        elapsed = round(time.time() - start_time, 4)
        return PRPOptimizationResult(
            selected_prps=[],
            total_demand_risk=total_demand_risk,
            covered_demand_risk=0.0,
            coverage_percentage=0.0,
            uncovered_demand_points=list(demand_points),
            selected_count=0,
            solver_status="OPTIMAL" if available_patrol_count == 0 else "NO_CANDIDATES",
            run_time_seconds=elapsed,
            run_parameters=run_params,
            metrics={"objective_value": 0.0, "covered_demand_count": 0},
        )

    # Edge Case 2: Zero demand points
    if num_demand == 0:
        # Select up to P candidates deterministically
        k = min(available_patrol_count, num_candidates)
        selected_items = [
            SelectedPRPItem(
                candidate_id=standardized_cands[i].id,
                latitude=standardized_cands[i].latitude,
                longitude=standardized_cands[i].longitude,
                name=standardized_cands[i].name,
                coverage_radius_km=coverage_radius_km,
                covered_demand_count=0,
                covered_demand_weight=0.0,
                strategy=standardized_cands[i].metadata.get("strategy", "OPTIMIZATION_CANDIDATE"),
                metadata=standardized_cands[i].metadata,
            )
            for i in range(k)
        ]
        elapsed = round(time.time() - start_time, 4)
        return PRPOptimizationResult(
            selected_prps=selected_items,
            total_demand_risk=0.0,
            covered_demand_risk=0.0,
            coverage_percentage=100.0,
            uncovered_demand_points=[],
            selected_count=k,
            solver_status="OPTIMAL",
            run_time_seconds=elapsed,
            run_parameters=run_params,
            metrics={"objective_value": 0.0, "covered_demand_count": 0},
        )

    # Build spatial coverage matrix
    cov_matrix = build_coverage_matrix(
        candidates=standardized_cands,
        demand_points=demand_points,
        coverage_radius_km=coverage_radius_km,
    )

    # Instantiate OR-Tools MIP Solver
    solver = pywraplp.Solver.CreateSolver("CBC")
    if not solver:
        solver = pywraplp.Solver.CreateSolver("SCIP")
    if not solver:
        raise RuntimeError("No suitable OR-Tools MIP solver available (CBC/SCIP).")

    solver.SetTimeLimit(int(solver_timeout_seconds * 1000))

    # Decision variables:
    # x[j] = 1 if candidate j is selected as a PRP, 0 otherwise
    x = [solver.BoolVar(f"x_{j}") for j in range(num_candidates)]

    # y[i] = 1 if demand point i is covered by at least one selected PRP, 0 otherwise
    y = [solver.BoolVar(f"y_{i}") for i in range(num_demand)]

    # Objective: Maximize unique covered weighted demand risk
    objective = solver.Objective()
    for i in range(num_demand):
        objective.SetCoefficient(y[i], float(demand_points[i].weight))
    objective.SetMaximization()

    # Constraint 1: Patrol limit (sum_{j in J} x[j] <= P)
    patrol_limit_constraint = solver.Constraint(0, float(available_patrol_count), "patrol_limit")
    for j in range(num_candidates):
        patrol_limit_constraint.SetCoefficient(x[j], 1.0)

    # Constraint 2: Coverage indicator (y[i] <= sum_{j in N_i} x[j] for all i in I)
    for i in range(num_demand):
        covering_cands = cov_matrix.demand_to_candidates[i]
        if covering_cands:
            # y[i] - sum_{j in N_i} x[j] <= 0
            cov_constraint = solver.Constraint(-solver.infinity(), 0.0, f"cov_{i}")
            cov_constraint.SetCoefficient(y[i], 1.0)
            for j in covering_cands:
                cov_constraint.SetCoefficient(x[j], -1.0)
        else:
            # Unreachable demand point: force y[i] = 0
            unreachable_constraint = solver.Constraint(0.0, 0.0, f"unreachable_{i}")
            unreachable_constraint.SetCoefficient(y[i], 1.0)

    # Solve the optimization problem
    status = solver.Solve()

    status_str = "UNKNOWN"
    if status == pywraplp.Solver.OPTIMAL:
        status_str = "OPTIMAL"
    elif status == pywraplp.Solver.FEASIBLE:
        status_str = "FEASIBLE"
    elif status == pywraplp.Solver.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status == pywraplp.Solver.UNBOUNDED:
        status_str = "UNBOUNDED"

    # Extract selected candidates
    selected_indices = [j for j in range(num_candidates) if x[j].solution_value() > 0.5]
    covered_demand_indices = set(i for i in range(num_demand) if y[i].solution_value() > 0.5)

    # Format selected PRPs
    selected_prps: List[SelectedPRPItem] = []
    for rank, j in enumerate(selected_indices, start=1):
        cand = standardized_cands[j]
        covered_in_this_prp = [i for i in cov_matrix.candidate_to_demand[j] if i in covered_demand_indices]
        prp_covered_weight = round(sum(demand_points[i].weight for i in covered_in_this_prp), 4)

        selected_prps.append(
            SelectedPRPItem(
                candidate_id=cand.id,
                latitude=cand.latitude,
                longitude=cand.longitude,
                name=f"PRP-{rank:02d}",
                coverage_radius_km=coverage_radius_km,
                covered_demand_count=len(covered_in_this_prp),
                covered_demand_weight=prp_covered_weight,
                strategy=cand.metadata.get("strategy", "MCLP_OPTIMIZED"),
                metadata=cand.metadata,
            )
        )

    # Sort selected PRPs by covered demand weight descending
    selected_prps.sort(key=lambda p: -p.covered_demand_weight)
    for rank, p in enumerate(selected_prps, start=1):
        p.name = f"PRP-{rank:02d}"

    # Calculate metrics
    covered_demand_risk = round(sum(demand_points[i].weight for i in covered_demand_indices), 4)
    cov_pct = round((covered_demand_risk / total_demand_risk * 100.0), 2) if total_demand_risk > 0 else 100.0

    uncovered_points = [demand_points[i] for i in range(num_demand) if i not in covered_demand_indices]
    uncovered_points.sort(key=lambda d: -d.weight)

    elapsed_secs = round(time.time() - start_time, 4)

    metrics = {
        "objective_value": round(objective.Value(), 4),
        "covered_demand_count": len(covered_demand_indices),
        "total_demand_count": num_demand,
        "uncovered_demand_count": len(uncovered_points),
        "selected_prp_count": len(selected_prps),
        "iterations": solver.iterations(),
        "nodes": solver.nodes() if hasattr(solver, "nodes") else 0,
    }

    return PRPOptimizationResult(
        selected_prps=selected_prps,
        total_demand_risk=total_demand_risk,
        covered_demand_risk=covered_demand_risk,
        coverage_percentage=cov_pct,
        uncovered_demand_points=uncovered_points,
        selected_count=len(selected_prps),
        solver_status=status_str,
        run_time_seconds=elapsed_secs,
        run_parameters=run_params,
        metrics=metrics,
    )
