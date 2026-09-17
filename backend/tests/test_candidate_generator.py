from datetime import datetime, timedelta, timezone
import pytest

from app.models.crime import CrimeIncident
from app.optimization.candidate_generator import (
    CandidateGenerationConfig,
    CandidatePRP,
    CandidateStrategy,
    PredefinedLocation,
    generate_prp_candidates,
)
from app.optimization.risk_scoring import RiskScoringConfig
from app.services.crime_service import create_point_geometry


@pytest.fixture
def sample_incidents():
    ref_time = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)
    return [
        # Cluster 1: Downtown Bangalore (~12.9716, 77.5946)
        CrimeIncident(
            id=101,
            incident_number="CR-CAND-01",
            category="Robbery",
            severity=4,
            incident_time=ref_time - timedelta(days=1),
            location=create_point_geometry(12.9716, 77.5946),
            is_active=True,
        ),
        CrimeIncident(
            id=102,
            incident_number="CR-CAND-02",
            category="Theft",
            severity=3,
            incident_time=ref_time - timedelta(days=2),
            location=create_point_geometry(12.9720, 77.5950),
            is_active=True,
        ),
        CrimeIncident(
            id=103,
            incident_number="CR-CAND-03",
            category="Assault",
            severity=4,
            incident_time=ref_time - timedelta(hours=5),
            location=create_point_geometry(12.9710, 77.5940),
            is_active=True,
        ),
        # Cluster 2: Indiranagar (~12.9783, 77.6408) - approx 5km away
        CrimeIncident(
            id=201,
            incident_number="CR-CAND-04",
            category="Armed Robbery",
            severity=5,
            incident_time=ref_time - timedelta(days=3),
            location=create_point_geometry(12.9783, 77.6408),
            is_active=True,
        ),
        CrimeIncident(
            id=202,
            incident_number="CR-CAND-05",
            category="Burglary",
            severity=3,
            incident_time=ref_time - timedelta(days=4),
            location=create_point_geometry(12.9790, 77.6415),
            is_active=True,
        ),
    ]


def test_deterministic_output(sample_incidents):
    """Running candidate generator repeatedly with same inputs produces identical candidates."""
    ref_time = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)
    config = CandidateGenerationConfig(cluster_radius_km=1.0, min_candidate_separation_km=0.5)

    run_1 = generate_prp_candidates(sample_incidents, reference_time=ref_time, target_shift="EVENING", config=config)
    run_2 = generate_prp_candidates(sample_incidents, reference_time=ref_time, target_shift="EVENING", config=config)

    assert len(run_1) == len(run_2)
    assert len(run_1) >= 2

    for c1, c2 in zip(run_1, run_2):
        assert c1.candidate_id == c2.candidate_id
        assert c1.latitude == c2.latitude
        assert c1.longitude == c2.longitude
        assert c1.risk_score == c2.risk_score
        assert c1.source_incident_ids == c2.source_incident_ids


def test_duplicate_suppression(sample_incidents):
    """Incidents clustered tightly are merged into a representative centroid rather than multiple redundant PRPs."""
    ref_time = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)

    # 3 incidents in Downtown Bangalore are within 100 meters of each other
    # With cluster_radius_km=1.0 and separation=0.5km, they should produce exactly 1 candidate for Cluster 1
    config = CandidateGenerationConfig(cluster_radius_km=1.0, min_candidate_separation_km=0.5)
    candidates = generate_prp_candidates(sample_incidents, reference_time=ref_time, config=config)

    # We expect 2 candidates: 1 for Downtown cluster, 1 for Indiranagar cluster
    assert len(candidates) == 2

    # Verify Cluster 1 candidate merged all 3 downtown incidents
    downtown_cand = next(c for c in candidates if 12.9700 <= c.latitude <= 12.9730)
    assert set(downtown_cand.source_incident_ids) == {101, 102, 103}


def test_empty_data_handled_safely():
    """Empty incident list returns empty candidate list without exceptions."""
    result = generate_prp_candidates([])
    assert result == []


def test_invalid_coordinates_filtered_safely():
    """Incidents with invalid latitude/longitude are skipped without corrupting valid candidate generation."""
    ref_time = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)
    dirty_incidents = [
        # Valid incident
        CrimeIncident(
            id=1,
            incident_number="VALID-01",
            category="Theft",
            severity=3,
            incident_time=ref_time,
            location=create_point_geometry(12.9716, 77.5946),
            is_active=True,
        ),
        # Invalid coordinates (lat > 90)
        {"id": 2, "latitude": 999.0, "longitude": 77.5946, "severity": 5, "incident_time": ref_time},
        # Invalid coordinates (lng < -180)
        {"id": 3, "latitude": 12.9716, "longitude": -500.0, "severity": 4, "incident_time": ref_time},
        # None location
        {"id": 4, "latitude": None, "longitude": None, "severity": 2, "incident_time": ref_time},
    ]

    candidates = generate_prp_candidates(dirty_incidents, reference_time=ref_time)
    assert len(candidates) == 1
    assert candidates[0].source_incident_ids == [1]


def test_risk_association_and_traceability(sample_incidents):
    """Every generated candidate is associated with local risk metrics and traceable metadata."""
    ref_time = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)
    candidates = generate_prp_candidates(
        sample_incidents,
        reference_time=ref_time,
        target_shift="NIGHT",
        config=CandidateGenerationConfig(coverage_radius_km=2.0),
    )

    for cand in candidates:
        assert isinstance(cand, CandidatePRP)
        assert cand.candidate_id.startswith("PRP-CAND-")
        assert cand.risk_score > 0.0
        assert cand.risk_breakdown is not None
        assert 0.0 <= cand.risk_breakdown.total_risk_score <= 100.0
        assert cand.incident_count > 0
        assert len(cand.source_incident_ids) > 0
        assert "Candidate generated via" in cand.reasoning
        assert f"{cand.coverage_radius_km}km" in cand.reasoning


def test_predefined_operational_locations(sample_incidents):
    """Predefined operational locations (police stations/outposts) are integrated when requested."""
    ref_time = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)

    predefined = [
        PredefinedLocation(
            name="Cubbon Park Police Station",
            latitude=12.9750,
            longitude=77.5900,
            category="POLICE_STATION",
        )
    ]

    config = CandidateGenerationConfig(
        strategy=CandidateStrategy.HYBRID,
        cluster_radius_km=1.0,
        min_candidate_separation_km=0.1,
    )

    candidates = generate_prp_candidates(
        incidents=sample_incidents,
        predefined_locations=predefined,
        reference_time=ref_time,
        config=config,
    )

    strategies = [c.strategy for c in candidates]
    assert CandidateStrategy.PREDEFINED_OPERATIONAL.value in strategies
    assert CandidateStrategy.CLUSTER_CENTROID.value in strategies

    op_cand = next(c for c in candidates if c.strategy == CandidateStrategy.PREDEFINED_OPERATIONAL.value)
    assert op_cand.metadata.get("name") == "Cubbon Park Police Station"
    # Even predefined location gets evaluated for nearby crime risk
    assert op_cand.risk_score > 0.0


def test_candidate_config_validation():
    """Invalid generation configurations raise ValueError."""
    with pytest.raises(ValueError, match="cluster_radius_km"):
        CandidateGenerationConfig(cluster_radius_km=0.0)

    with pytest.raises(ValueError, match="min_candidate_separation_km"):
        CandidateGenerationConfig(min_candidate_separation_km=-1.0)

    with pytest.raises(ValueError, match="min_incidents_per_cluster"):
        CandidateGenerationConfig(min_incidents_per_cluster=0)

    with pytest.raises(ValueError, match="max_candidates"):
        CandidateGenerationConfig(max_candidates=0)

    with pytest.raises(ValueError, match="coverage_radius_km"):
        CandidateGenerationConfig(coverage_radius_km=-2.0)
