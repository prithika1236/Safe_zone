"""
SafeZone Explainable Risk Scoring Engine.

Provides deterministic, transparent, and mathematically grounded crime risk calculation
without machine learning or black-box models.

Formula Components:
1. Frequency Factor: Proportional volume of incidents up to a configurable benchmark.
2. Severity Factor: Mean severity of incidents normalized to the configured severity scale.
3. Recency Factor: Mean exponential decay: exp(-decay_lambda * age_in_days).
4. Time-of-Day Factor: Proximity of incident occurrence hours to target operational shift window.

Output includes normalized total risk score (0.0 to 100.0) and exact component contributions.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
from typing import Any, Dict, List, Optional, Sequence, Union

# Standard severity mapping for common crime categories (scale 1 to 5)
DEFAULT_SEVERITY_MAPPING: Dict[str, int] = {
    "Homicide": 5,
    "Armed Robbery": 5,
    "Kidnapping": 5,
    "Aggravated Assault": 4,
    "Robbery": 4,
    "Sexual Harassment": 4,
    "Burglary": 3,
    "Vehicle Theft": 3,
    "Theft": 2,
    "Vandalism": 2,
    "Disorderly Conduct": 1,
    "Trespassing": 1,
    "Other": 2,
}

# Standard operational shifts and their midpoint target hours (24h format)
SHIFT_CENTER_HOURS: Dict[str, float] = {
    "MORNING": 10.0,      # 06:00 - 14:00 (midpoint: 10:00)
    "AFTERNOON": 18.0,    # 14:00 - 22:00 (midpoint: 18:00)
    "EVENING": 18.0,      # Alias for AFTERNOON
    "NIGHT": 2.0,         # 22:00 - 06:00 (midpoint: 02:00)
}


@dataclass(frozen=True)
class RiskScoringConfig:
    """Configurable weights and tuning parameters for explainable risk calculation."""
    weight_frequency: float = 0.25
    weight_severity: float = 0.30
    weight_recency: float = 0.25
    weight_time: float = 0.20
    decay_lambda: float = 0.05
    max_frequency_benchmark: int = 50
    severity_scale_max: float = 5.0
    category_severity_mapping: Dict[str, int] = field(default_factory=lambda: dict(DEFAULT_SEVERITY_MAPPING))

    def __post_init__(self):
        if self.weight_frequency < 0 or self.weight_severity < 0 or self.weight_recency < 0 or self.weight_time < 0:
            raise ValueError("All risk scoring weights must be non-negative.")
        total_w = self.weight_frequency + self.weight_severity + self.weight_recency + self.weight_time
        if total_w <= 0.0:
            raise ValueError("Sum of risk scoring weights must be greater than zero.")
        if self.decay_lambda <= 0.0:
            raise ValueError("Recency decay lambda must be strictly positive (> 0.0).")
        if self.max_frequency_benchmark <= 0:
            raise ValueError("max_frequency_benchmark must be strictly positive (> 0).")
        if self.severity_scale_max <= 0.0:
            raise ValueError("severity_scale_max must be strictly positive (> 0.0).")


@dataclass
class IncidentRiskItem:
    """Standardized incident representation consumed by the risk scoring algorithm."""
    incident_time: datetime
    severity: int
    category: Optional[str] = None


@dataclass
class RiskScoreBreakdown:
    """Explainable risk result containing normalized component scores and weighted contributions."""
    total_risk_score: float
    frequency_score: float
    severity_score: float
    recency_score: float
    time_score: float
    frequency_contribution: float
    severity_contribution: float
    recency_contribution: float
    time_contribution: float
    incident_count: int
    details: Dict[str, Any] = field(default_factory=dict)


def get_shift_target_hour(shift: Union[str, int, float, None]) -> Optional[float]:
    """Resolve a shift name or hour into a target hour of day (0.0 - 23.99)."""
    if shift is None:
        return None
    if isinstance(shift, (int, float)):
        return float(shift % 24)
    if isinstance(shift, str):
        normalized = shift.strip().upper()
        if normalized in SHIFT_CENTER_HOURS:
            return SHIFT_CENTER_HOURS[normalized]
        if normalized in ("ALL", "ALL_DAY", "NONE", ""):
            return None
        try:
            val = float(normalized)
            return float(val % 24)
        except ValueError:
            return None
    return None


def calculate_circular_hour_distance(hour1: float, hour2: float) -> float:
    """Compute shortest distance in hours between two times on a 24-hour circular clock."""
    diff = abs((hour1 % 24.0) - (hour2 % 24.0))
    return min(diff, 24.0 - diff)


def compute_time_factor(incident_time: datetime, target_hour: Optional[float]) -> float:
    """
    Calculate time-of-day relevance factor in range [0.1, 1.0].
    When incident hour matches target operational hour, factor is 1.0.
    When 12 hours apart (diametrically opposite), factor is 0.1.
    If no target hour specified, defaults to neutral 1.0.
    """
    if target_hour is None:
        return 1.0
    hour_val = incident_time.hour + (incident_time.minute / 60.0) + (incident_time.second / 3600.0)
    circular_dist = calculate_circular_hour_distance(hour_val, target_hour)
    # Range of circular_dist is [0, 12]. Factor linearly scales from 1.0 down to 0.1.
    return max(0.1, 1.0 - (0.9 * (circular_dist / 12.0)))


def compute_recency_factor(incident_time: datetime, reference_time: datetime, decay_lambda: float) -> float:
    """
    Calculate exponential recency decay factor: exp(-lambda * age_in_days).
    Incidents at reference_time return 1.0. Older incidents decay asymptotically to 0.0.
    """
    # Ensure timezone compatibility
    if incident_time.tzinfo is None and reference_time.tzinfo is not None:
        ref = reference_time.astimezone(timezone.utc).replace(tzinfo=None)
        inc = incident_time
    elif incident_time.tzinfo is not None and reference_time.tzinfo is None:
        ref = reference_time
        inc = incident_time.astimezone(timezone.utc).replace(tzinfo=None)
    else:
        ref = reference_time
        inc = incident_time

    age_seconds = (ref - inc).total_seconds()
    age_days = max(0.0, age_seconds / 86400.0)
    return math.exp(-decay_lambda * age_days)


def calculate_risk(
    incidents: Sequence[Union[IncidentRiskItem, Any]],
    reference_time: Optional[datetime] = None,
    target_shift: Union[str, int, float, None] = None,
    config: Optional[RiskScoringConfig] = None,
) -> RiskScoreBreakdown:
    """
    Execute explainable, deterministic crime-risk calculation.

    Args:
        incidents: List of incident items (IncidentRiskItem, CrimeIncident model, or objects with incident_time and severity).
        reference_time: Point in time for recency evaluation (defaults to UTC now).
        target_shift: Operational shift name ('MORNING', 'AFTERNOON', 'NIGHT') or target hour (0-23).
        config: RiskScoringConfig specifying weights and parameters.

    Returns:
        RiskScoreBreakdown with component scores and normalized contributions.
    """
    cfg = config or RiskScoringConfig()
    ref_time = reference_time or datetime.now(timezone.utc)
    target_hour = get_shift_target_hour(target_shift)

    count = len(incidents)
    if count == 0:
        return RiskScoreBreakdown(
            total_risk_score=0.0,
            frequency_score=0.0,
            severity_score=0.0,
            recency_score=0.0,
            time_score=0.0,
            frequency_contribution=0.0,
            severity_contribution=0.0,
            recency_contribution=0.0,
            time_contribution=0.0,
            incident_count=0,
            details={
                "evaluated_shift": target_shift,
                "target_hour": target_hour,
                "reference_time": ref_time.isoformat(),
                "weights": {
                    "frequency": cfg.weight_frequency,
                    "severity": cfg.weight_severity,
                    "recency": cfg.weight_recency,
                    "time": cfg.weight_time,
                },
            },
        )

    # Standardize incident inputs
    recency_factors: List[float] = []
    severity_factors: List[float] = []
    time_factors: List[float] = []

    for inc in incidents:
        # Extract incident_time
        inc_time = getattr(inc, "incident_time", None)
        if inc_time is None:
            continue

        # Extract severity
        sev_val = getattr(inc, "severity", None)
        if sev_val is None:
            cat = getattr(inc, "category", "")
            sev_val = cfg.category_severity_mapping.get(cat, 2)

        # Compute factors
        rec_f = compute_recency_factor(inc_time, ref_time, cfg.decay_lambda)
        sev_f = min(1.0, max(0.0, float(sev_val) / cfg.severity_scale_max))
        time_f = compute_time_factor(inc_time, target_hour)

        recency_factors.append(rec_f)
        severity_factors.append(sev_f)
        time_factors.append(time_f)

    valid_count = len(recency_factors)
    if valid_count == 0:
        return calculate_risk([], ref_time, target_shift, cfg)

    # Component Scores (0.0 - 100.0)
    raw_freq = min(1.0, float(valid_count) / float(cfg.max_frequency_benchmark))
    frequency_score = round(raw_freq * 100.0, 4)
    severity_score = round((sum(severity_factors) / valid_count) * 100.0, 4)
    recency_score = round((sum(recency_factors) / valid_count) * 100.0, 4)
    time_score = round((sum(time_factors) / valid_count) * 100.0, 4)

    # Normalized weights
    total_w = cfg.weight_frequency + cfg.weight_severity + cfg.weight_recency + cfg.weight_time
    norm_w_freq = cfg.weight_frequency / total_w
    norm_w_sev = cfg.weight_severity / total_w
    norm_w_rec = cfg.weight_recency / total_w
    norm_w_time = cfg.weight_time / total_w

    # Component Contributions (sum to total_risk_score)
    freq_contrib = norm_w_freq * frequency_score
    sev_contrib = norm_w_sev * severity_score
    rec_contrib = norm_w_rec * recency_score
    time_contrib = norm_w_time * time_score

    total_risk = freq_contrib + sev_contrib + rec_contrib + time_contrib

    # Round results cleanly to 2 decimal places
    total_rounded = round(min(100.0, max(0.0, total_risk)), 2)
    freq_contrib_rounded = round(freq_contrib, 2)
    sev_contrib_rounded = round(sev_contrib, 2)
    rec_contrib_rounded = round(rec_contrib, 2)
    time_contrib_rounded = round(time_contrib, 2)

    return RiskScoreBreakdown(
        total_risk_score=total_rounded,
        frequency_score=round(frequency_score, 2),
        severity_score=round(severity_score, 2),
        recency_score=round(recency_score, 2),
        time_score=round(time_score, 2),
        frequency_contribution=freq_contrib_rounded,
        severity_contribution=sev_contrib_rounded,
        recency_contribution=rec_contrib_rounded,
        time_contribution=time_contrib_rounded,
        incident_count=valid_count,
        details={
            "evaluated_shift": target_shift,
            "target_hour": target_hour,
            "reference_time": ref_time.isoformat(),
            "decay_lambda": cfg.decay_lambda,
            "max_frequency_benchmark": cfg.max_frequency_benchmark,
            "weights": {
                "frequency": cfg.weight_frequency,
                "severity": cfg.weight_severity,
                "recency": cfg.weight_recency,
                "time": cfg.weight_time,
            },
        },
    )
