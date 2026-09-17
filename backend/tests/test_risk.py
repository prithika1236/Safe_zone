from datetime import datetime, timedelta, timezone
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crime import CrimeIncident
from app.optimization.risk_scoring import (
    DEFAULT_SEVERITY_MAPPING,
    IncidentRiskItem,
    RiskScoreBreakdown,
    RiskScoringConfig,
    calculate_circular_hour_distance,
    calculate_risk,
    compute_recency_factor,
    compute_time_factor,
    get_shift_target_hour,
)
from app.services.crime_service import create_point_geometry
from app.services.risk_service import RiskService


def test_recency_decay_recent_greater_than_old():
    """Recent crime incident must produce a higher recency score and total risk than an older identical crime."""
    ref_time = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)

    recent_incident = IncidentRiskItem(
        incident_time=ref_time - timedelta(hours=2),  # 2 hours old
        severity=4,
        category="Robbery",
    )
    old_incident = IncidentRiskItem(
        incident_time=ref_time - timedelta(days=60),  # 60 days old
        severity=4,
        category="Robbery",
    )

    result_recent = calculate_risk([recent_incident], reference_time=ref_time)
    result_old = calculate_risk([old_incident], reference_time=ref_time)

    assert result_recent.recency_score > result_old.recency_score
    assert result_recent.recency_contribution > result_old.recency_contribution
    assert result_recent.total_risk_score > result_old.total_risk_score
    assert result_recent.severity_score == result_old.severity_score


def test_configured_high_severity_greater_than_low_severity():
    """Incident with high severity must produce a higher severity score and total score than low severity."""
    ref_time = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)

    high_sev = IncidentRiskItem(
        incident_time=ref_time - timedelta(days=1),
        severity=5,
        category="Homicide",
    )
    low_sev = IncidentRiskItem(
        incident_time=ref_time - timedelta(days=1),
        severity=1,
        category="Disorderly Conduct",
    )

    result_high = calculate_risk([high_sev], reference_time=ref_time)
    result_low = calculate_risk([low_sev], reference_time=ref_time)

    assert result_high.severity_score == 100.0
    assert result_low.severity_score == 20.0  # 1 / 5 * 100
    assert result_high.severity_contribution > result_low.severity_contribution
    assert result_high.total_risk_score > result_low.total_risk_score
    assert result_high.recency_score == result_low.recency_score


def test_relevant_time_window_influences_score():
    """Incidents occurring during or near target shift hour receive a higher time score."""
    ref_time = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)

    # NIGHT shift center is 02:00
    night_incident = IncidentRiskItem(
        incident_time=datetime(2026, 9, 17, 2, 0, 0, tzinfo=timezone.utc),
        severity=3,
    )
    afternoon_incident = IncidentRiskItem(
        incident_time=datetime(2026, 9, 17, 14, 0, 0, tzinfo=timezone.utc),  # 12h away from 02:00
        severity=3,
    )

    result_night = calculate_risk([night_incident], reference_time=ref_time, target_shift="NIGHT")
    result_day = calculate_risk([afternoon_incident], reference_time=ref_time, target_shift="NIGHT")

    assert result_night.time_score > result_day.time_score
    assert result_night.time_contribution > result_day.time_contribution
    assert result_night.total_risk_score > result_day.total_risk_score
    assert result_night.time_score == 100.0
    assert result_day.time_score == 10.0  # minimum floor at 12 hours difference


def test_empty_input_handled_safely():
    """Empty incident list returns all 0.0 scores safely without division by zero."""
    result = calculate_risk([])

    assert result.total_risk_score == 0.0
    assert result.frequency_score == 0.0
    assert result.severity_score == 0.0
    assert result.recency_score == 0.0
    assert result.time_score == 0.0
    assert result.frequency_contribution == 0.0
    assert result.severity_contribution == 0.0
    assert result.recency_contribution == 0.0
    assert result.time_contribution == 0.0
    assert result.incident_count == 0


def test_normalization_validity_and_bounds():
    """All component scores and total risk must be strictly bounded in [0.0, 100.0]."""
    ref_time = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)
    incidents = [
        IncidentRiskItem(incident_time=ref_time - timedelta(days=i * 2), severity=(i % 5) + 1)
        for i in range(30)
    ]

    result = calculate_risk(incidents, reference_time=ref_time, target_shift="MORNING")

    assert 0.0 <= result.total_risk_score <= 100.0
    assert 0.0 <= result.frequency_score <= 100.0
    assert 0.0 <= result.severity_score <= 100.0
    assert 0.0 <= result.recency_score <= 100.0
    assert 0.0 <= result.time_score <= 100.0

    # Contribution sum consistency
    sum_contributions = (
        result.frequency_contribution
        + result.severity_contribution
        + result.recency_contribution
        + result.time_contribution
    )
    assert abs(sum_contributions - result.total_risk_score) <= 0.05


def test_bad_configuration_rejected():
    """Invalid scoring configurations must raise ValueError."""
    # Negative weight
    with pytest.raises(ValueError, match="non-negative"):
        RiskScoringConfig(weight_frequency=-0.1)

    # Sum of weights zero
    with pytest.raises(ValueError, match="greater than zero"):
        RiskScoringConfig(weight_frequency=0, weight_severity=0, weight_recency=0, weight_time=0)

    # Negative decay lambda
    with pytest.raises(ValueError, match="strictly positive"):
        RiskScoringConfig(decay_lambda=-0.01)

    # Zero benchmark
    with pytest.raises(ValueError, match="strictly positive"):
        RiskScoringConfig(max_frequency_benchmark=0)

    # Zero severity scale
    with pytest.raises(ValueError, match="strictly positive"):
        RiskScoringConfig(severity_scale_max=0.0)


def test_deterministic_repeatability():
    """Identical inputs and configuration must produce identical outputs."""
    ref_time = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)
    incidents = [
        IncidentRiskItem(incident_time=ref_time - timedelta(days=1), severity=4, category="Robbery"),
        IncidentRiskItem(incident_time=ref_time - timedelta(days=5), severity=2, category="Theft"),
        IncidentRiskItem(incident_time=ref_time - timedelta(hours=10), severity=5, category="Armed Robbery"),
    ]

    cfg = RiskScoringConfig(weight_frequency=0.3, weight_severity=0.3, weight_recency=0.2, weight_time=0.2)

    run_1 = calculate_risk(incidents, reference_time=ref_time, target_shift="EVENING", config=cfg)
    run_2 = calculate_risk(incidents, reference_time=ref_time, target_shift="EVENING", config=cfg)

    assert run_1.total_risk_score == run_2.total_risk_score
    assert run_1.frequency_score == run_2.frequency_score
    assert run_1.severity_score == run_2.severity_score
    assert run_1.recency_score == run_2.recency_score
    assert run_1.time_score == run_2.time_score
    assert run_1.frequency_contribution == run_2.frequency_contribution
    assert run_1.severity_contribution == run_2.severity_contribution
    assert run_1.recency_contribution == run_2.recency_contribution
    assert run_1.time_contribution == run_2.time_contribution


def test_circular_clock_distance():
    """Test 24-hour circular distance calculation."""
    assert calculate_circular_hour_distance(2.0, 2.0) == 0.0
    assert calculate_circular_hour_distance(2.0, 14.0) == 12.0
    assert calculate_circular_hour_distance(23.0, 1.0) == 2.0
    assert calculate_circular_hour_distance(1.0, 23.0) == 2.0


@pytest.mark.asyncio
async def test_risk_service_database_integration(db_session: AsyncSession):
    """Test RiskService spatial assessment, record persistence, and retrieval."""
    now = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)

    # Seed crime incidents
    crime1 = CrimeIncident(
        incident_number="CR-RISK-001",
        category="Robbery",
        severity=4,
        incident_time=now - timedelta(days=2),
        location=create_point_geometry(12.9716, 77.5946),
        is_active=True,
    )
    crime2 = CrimeIncident(
        incident_number="CR-RISK-002",
        category="Theft",
        severity=2,
        incident_time=now - timedelta(days=10),
        location=create_point_geometry(12.9720, 77.5950),
        is_active=True,
    )
    crime_far = CrimeIncident(
        incident_number="CR-RISK-FAR",
        category="Homicide",
        severity=5,
        incident_time=now - timedelta(hours=1),
        location=create_point_geometry(13.5000, 78.5000),  # ~100km away
        is_active=True,
    )
    db_session.add_all([crime1, crime2, crime_far])
    await db_session.commit()

    # Calculate location risk at (12.9716, 77.5946) within 3km
    breakdown = await RiskService.calculate_location_risk(
        db=db_session,
        latitude=12.9716,
        longitude=77.5946,
        radius_km=3.0,
        reference_time=now,
        target_shift="MORNING",
    )

    assert breakdown.incident_count == 2  # crime1 and crime2 inside 3km, crime_far excluded
    assert breakdown.total_risk_score > 0.0

    # Persist the score record
    saved_record = await RiskService.record_risk_score(
        db=db_session,
        latitude=12.9716,
        longitude=77.5946,
        breakdown=breakdown,
        grid_identifier="GRID_BLR_01",
    )

    assert saved_record.id is not None
    assert saved_record.grid_identifier == "GRID_BLR_01"

    # Retrieve historical records
    history = await RiskService.get_historical_risk_scores(db=db_session, grid_identifier="GRID_BLR_01")
    assert len(history) >= 1
    assert history[0].grid_identifier == "GRID_BLR_01"
    assert history[0].total_risk_score == breakdown.total_risk_score
