"""
SafeZone PRP Candidate Generation Engine.

Generates deterministic, deduplicated, spatially valid, and traceable candidate
Priority Response Points (PRPs) from historical crime clusters, risk density centroids,
and predefined safe operational facilities.

Ensures candidate locations are safe, representative centroids rather than raw crime points,
providing a modular foundation for subsequent patrol allocation optimization.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from app.optimization.risk_scoring import (
    IncidentRiskItem,
    RiskScoreBreakdown,
    RiskScoringConfig,
    calculate_risk,
    compute_recency_factor,
)
from app.services.crime_service import extract_coordinates
from app.services.location_service import haversine_distance_km, validate_coordinates


class CandidateStrategy(str, Enum):
    """Strategies for generating candidate patrol response points."""
    CLUSTER_CENTROID = "CLUSTER_CENTROID"
    GRID_CENTROID = "GRID_CENTROID"
    PREDEFINED_OPERATIONAL = "PREDEFINED_OPERATIONAL"
    HYBRID = "HYBRID"


@dataclass
class PredefinedLocation:
    """Predefined safe operational location (e.g. police outpost, major civic junction)."""
    name: str
    latitude: float
    longitude: float
    category: Optional[str] = "OPERATIONAL_FACILITY"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not validate_coordinates(self.latitude, self.longitude):
            raise ValueError(f"Invalid coordinates for predefined location '{self.name}': ({self.latitude}, {self.longitude})")


@dataclass(frozen=True)
class CandidateGenerationConfig:
    """Configuration parameters for deterministic PRP candidate generation."""
    strategy: CandidateStrategy = CandidateStrategy.CLUSTER_CENTROID
    cluster_radius_km: float = 1.0
    min_candidate_separation_km: float = 0.3
    min_incidents_per_cluster: int = 1
    max_candidates: int = 25
    coverage_radius_km: float = 2.0
    grid_cell_size_km: float = 1.0
    risk_config: RiskScoringConfig = field(default_factory=RiskScoringConfig)

    def __post_init__(self):
        if self.cluster_radius_km <= 0.0:
            raise ValueError("cluster_radius_km must be strictly positive (> 0.0).")
        if self.min_candidate_separation_km < 0.0:
            raise ValueError("min_candidate_separation_km cannot be negative.")
        if self.min_incidents_per_cluster < 1:
            raise ValueError("min_incidents_per_cluster must be at least 1.")
        if self.max_candidates < 1:
            raise ValueError("max_candidates must be at least 1.")
        if self.coverage_radius_km <= 0.0:
            raise ValueError("coverage_radius_km must be strictly positive (> 0.0).")


@dataclass
class CandidatePRP:
    """A deterministic, traceable candidate Priority Response Point."""
    candidate_id: str
    latitude: float
    longitude: float
    strategy: str
    incident_count: int
    source_incident_ids: List[int]
    risk_score: float
    risk_breakdown: RiskScoreBreakdown
    reasoning: str
    coverage_radius_km: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class _IncidentRecord:
    id: int
    latitude: float
    longitude: float
    severity: int
    incident_time: datetime
    category: str
    weight: float


def _parse_incidents(
    incidents: Sequence[Any],
    reference_time: datetime,
    decay_lambda: float,
) -> List[_IncidentRecord]:
    """Extract and validate geographic coordinates and calculate weights for incidents."""
    parsed: List[_IncidentRecord] = []

    for idx, inc in enumerate(incidents):
        # Extract location
        loc = getattr(inc, "location", None)
        if loc is not None:
            lat, lng = extract_coordinates(loc)
        else:
            lat = getattr(inc, "latitude", None)
            lng = getattr(inc, "longitude", None)

        if lat is None or lng is None:
            continue

        try:
            lat_f = float(lat)
            lng_f = float(lng)
        except (ValueError, TypeError):
            continue

        if not validate_coordinates(lat_f, lng_f):
            continue

        inc_id = getattr(inc, "id", idx + 1)
        sev = getattr(inc, "severity", 2)
        inc_time = getattr(inc, "incident_time", reference_time)
        cat = getattr(inc, "category", "Crime")

        rec_factor = compute_recency_factor(inc_time, reference_time, decay_lambda)
        weight = max(0.1, float(sev) * rec_factor)

        parsed.append(
            _IncidentRecord(
                id=inc_id,
                latitude=lat_f,
                longitude=lng_f,
                severity=sev,
                incident_time=inc_time,
                category=cat,
                weight=weight,
            )
        )

    # Sort deterministically: recent incidents first, higher severity first, id tiebreaker
    parsed.sort(
        key=lambda r: (
            -r.incident_time.timestamp() if r.incident_time else 0,
            -r.severity,
            r.id,
        )
    )
    return parsed


def _generate_cluster_centroids(
    incidents: List[_IncidentRecord],
    cluster_radius_km: float,
    min_incidents: int,
) -> List[Tuple[float, float, List[int], float]]:
    """
    Cluster incidents using deterministic greedy distance grouping.
    Returns list of tuples: (centroid_lat, centroid_lng, source_incident_ids, total_weight).
    """
    clusters: List[Dict[str, Any]] = []

    for inc in incidents:
        matched_cluster = None
        min_dist = float("inf")

        for c in clusters:
            d = haversine_distance_km(inc.latitude, inc.longitude, c["lat"], c["lng"])
            if d <= cluster_radius_km and d < min_dist:
                min_dist = d
                matched_cluster = c

        if matched_cluster is not None:
            # Update weighted centroid
            old_w = matched_cluster["weight"]
            new_w = old_w + inc.weight
            matched_cluster["lat"] = (matched_cluster["lat"] * old_w + inc.latitude * inc.weight) / new_w
            matched_cluster["lng"] = (matched_cluster["lng"] * old_w + inc.longitude * inc.weight) / new_w
            matched_cluster["weight"] = new_w
            matched_cluster["incidents"].append(inc.id)
        else:
            clusters.append({
                "lat": inc.latitude,
                "lng": inc.longitude,
                "weight": inc.weight,
                "incidents": [inc.id],
            })

    results = []
    for c in clusters:
        if len(c["incidents"]) >= min_incidents:
            results.append((round(c["lat"], 6), round(c["lng"], 6), c["incidents"], c["weight"]))

    return results


def _deduplicate_candidate_points(
    candidates: List[Dict[str, Any]],
    min_separation_km: float,
) -> List[Dict[str, Any]]:
    """
    Suppresses candidate points that are closer than min_separation_km,
    preserving higher-weighted or operational candidates.
    """
    # Sort candidates by weight/importance descending
    candidates.sort(key=lambda c: (-c.get("weight", 0.0), len(c.get("source_incident_ids", []))))

    kept: List[Dict[str, Any]] = []
    for cand in candidates:
        is_duplicate = False
        for k in kept:
            d = haversine_distance_km(cand["latitude"], cand["longitude"], k["latitude"], k["longitude"])
            if d < min_separation_km:
                is_duplicate = True
                # Merge source incident IDs into surviving candidate
                k["source_incident_ids"] = sorted(list(set(k["source_incident_ids"] + cand["source_incident_ids"])))
                k["weight"] = k.get("weight", 0.0) + cand.get("weight", 0.0)
                break
        if not is_duplicate:
            kept.append(cand)

    return kept


def generate_prp_candidates(
    incidents: Sequence[Any],
    predefined_locations: Optional[Sequence[Union[PredefinedLocation, Tuple[float, float, str]]]] = None,
    reference_time: Optional[datetime] = None,
    target_shift: Optional[str] = None,
    config: Optional[CandidateGenerationConfig] = None,
) -> List[CandidatePRP]:
    """
    Generate deterministic, deduplicated, risk-associated PRP candidates.

    Args:
        incidents: Sequence of crime incident records (CrimeIncident models, IncidentRiskItem, or dicts).
        predefined_locations: Optional safe operational locations (police stations, outposts, etc.).
        reference_time: Datetime anchor for recency decay (defaults to UTC now).
        target_shift: Target operational shift ('MORNING', 'AFTERNOON', 'NIGHT').
        config: Candidate generation configuration.

    Returns:
        List of CandidatePRP objects sorted by local risk score descending.
    """
    cfg = config or CandidateGenerationConfig()
    ref_time = reference_time or datetime.now(timezone.utc)

    # 1. Parse and validate incident records
    parsed_incidents = _parse_incidents(
        incidents=incidents,
        reference_time=ref_time,
        decay_lambda=cfg.risk_config.decay_lambda,
    )

    candidate_raw_list: List[Dict[str, Any]] = []

    # 2. Generate cluster-based centroids if strategy permits
    if cfg.strategy in (CandidateStrategy.CLUSTER_CENTROID, CandidateStrategy.HYBRID) and parsed_incidents:
        centroids = _generate_cluster_centroids(
            incidents=parsed_incidents,
            cluster_radius_km=cfg.cluster_radius_km,
            min_incidents=cfg.min_incidents_per_cluster,
        )
        for idx, (c_lat, c_lng, inc_ids, c_weight) in enumerate(centroids, start=1):
            candidate_raw_list.append({
                "latitude": c_lat,
                "longitude": c_lng,
                "strategy": CandidateStrategy.CLUSTER_CENTROID.value,
                "source_incident_ids": inc_ids,
                "weight": c_weight,
                "metadata": {"cluster_size": len(inc_ids)},
            })

    # 3. Add predefined operational locations if provided
    if predefined_locations and cfg.strategy in (CandidateStrategy.PREDEFINED_OPERATIONAL, CandidateStrategy.HYBRID):
        for idx, loc in enumerate(predefined_locations, start=1):
            if isinstance(loc, PredefinedLocation):
                name, lat, lng = loc.name, loc.latitude, loc.longitude
                meta = loc.metadata
            elif isinstance(loc, (tuple, list)) and len(loc) >= 2:
                lat, lng = float(loc[0]), float(loc[1])
                name = str(loc[2]) if len(loc) > 2 else f"Predefined-{idx}"
                meta = {}
            else:
                continue

            if not validate_coordinates(lat, lng):
                continue

            candidate_raw_list.append({
                "latitude": round(lat, 6),
                "longitude": round(lng, 6),
                "strategy": CandidateStrategy.PREDEFINED_OPERATIONAL.value,
                "source_incident_ids": [],
                "weight": 100.0,  # High priority to retain predefined locations
                "metadata": {"name": name, **meta},
            })

    # If no candidates generated, return empty list safely
    if not candidate_raw_list:
        return []

    # 4. Deduplicate and suppress spatial overlaps
    deduped = _deduplicate_candidate_points(
        candidates=candidate_raw_list,
        min_separation_km=cfg.min_candidate_separation_km,
    )

    # 5. Evaluate local risk and assemble CandidatePRP objects
    final_candidates: List[CandidatePRP] = []

    for idx, item in enumerate(deduped, start=1):
        cand_lat = item["latitude"]
        cand_lng = item["longitude"]
        strat = item["strategy"]
        source_ids = item["source_incident_ids"]

        # Find all incidents within coverage_radius_km of candidate
        local_incidents: List[IncidentRiskItem] = []
        for inc in parsed_incidents:
            d = haversine_distance_km(cand_lat, cand_lng, inc.latitude, inc.longitude)
            if d <= cfg.coverage_radius_km:
                local_incidents.append(
                    IncidentRiskItem(
                        incident_time=inc.incident_time,
                        severity=inc.severity,
                        category=inc.category,
                    )
                )

        # Calculate explainable risk score
        risk_breakdown = calculate_risk(
            incidents=local_incidents,
            reference_time=ref_time,
            target_shift=target_shift,
            config=cfg.risk_config,
        )

        cand_id = f"PRP-CAND-{idx:03d}"
        reasoning = (
            f"Candidate generated via {strat}. Covers {len(local_incidents)} incidents within "
            f"{cfg.coverage_radius_km}km radius with local composite risk score {risk_breakdown.total_risk_score}."
        )

        candidate = CandidatePRP(
            candidate_id=cand_id,
            latitude=cand_lat,
            longitude=cand_lng,
            strategy=strat,
            incident_count=len(local_incidents),
            source_incident_ids=source_ids,
            risk_score=risk_breakdown.total_risk_score,
            risk_breakdown=risk_breakdown,
            reasoning=reasoning,
            coverage_radius_km=cfg.coverage_radius_km,
            metadata=item.get("metadata", {}),
        )
        final_candidates.append(candidate)

    # 6. Sort candidates deterministically by risk_score desc, then coordinates
    final_candidates.sort(
        key=lambda c: (-c.risk_score, -c.incident_count, c.latitude, c.longitude)
    )

    # Re-index candidate IDs cleanly after sorting
    for rank, cand in enumerate(final_candidates[:cfg.max_candidates], start=1):
        cand.candidate_id = f"PRP-CAND-{rank:03d}"

    return final_candidates[:cfg.max_candidates]
