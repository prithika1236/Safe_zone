import pytest
from httpx import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crime import CrimeIncident
from app.models.enums import PatrolStatus, SafeHelpPointType
from app.models.help_point import SafeHelpPoint
from app.models.patrol import PatrolUnit
from app.services.crime_service import create_point_geometry
from app.services.location_service import (
    Coordinate,
    LocationService,
    RoutingService,
    compute_bounding_box,
    haversine_distance_km,
    haversine_distance_m,
    is_point_in_bbox,
    validate_coordinates,
)


def test_coordinate_validation():
    assert validate_coordinates(12.971598, 77.594562) is True
    assert validate_coordinates(-90.0, 180.0) is True
    assert validate_coordinates(90.0, -180.0) is True
    assert validate_coordinates(0.0, 0.0) is True

    # Out of bounds
    assert validate_coordinates(90.1, 77.0) is False
    assert validate_coordinates(-90.1, 77.0) is False
    assert validate_coordinates(12.0, 180.1) is False
    assert validate_coordinates(12.0, -180.1) is False

    coord = Coordinate(12.97, 77.59)
    assert coord.latitude == 12.97

    with pytest.raises(ValueError):
        Coordinate(95.0, 0.0)


def test_haversine_distance_calculations():
    # Distance between Bangalore Center (12.9716, 77.5946) and Indiranagar (12.9784, 77.6408)
    # Geodesic distance is approximately 5.06 km
    dist_km = haversine_distance_km(12.9716, 77.5946, 12.9784, 77.6408)
    assert 4.9 <= dist_km <= 5.2

    dist_m = haversine_distance_m(12.9716, 77.5946, 12.9784, 77.6408)
    assert 4900.0 <= dist_m <= 5200.0

    # Same point distance is 0.0
    assert haversine_distance_km(12.9716, 77.5946, 12.9716, 77.5946) == 0.0


def test_bounding_box_generation_and_containment():
    center_lat, center_lng = 12.9716, 77.5946
    radius_km = 5.0

    bbox = compute_bounding_box(center_lat, center_lng, radius_km)
    assert bbox.min_lat < center_lat < bbox.max_lat
    assert bbox.min_lng < center_lng < bbox.max_lng

    # Point within 1 km is inside bbox
    assert is_point_in_bbox(12.975, 77.598, bbox) is True

    # Point 50 km away is outside bbox
    assert is_point_in_bbox(13.400, 77.5946, bbox) is False


@pytest.mark.asyncio
async def test_nearby_incidents_search(db_session: AsyncSession):
    from datetime import datetime, timezone

    # Seed incidents
    inc1 = CrimeIncident(
        incident_number="LOC-INC-001",
        category="Robbery",
        severity=4,
        incident_time=datetime.now(timezone.utc),
        location=create_point_geometry(12.9750, 77.5960),  # ~0.4 km away
        is_active=True,
    )
    inc2 = CrimeIncident(
        incident_number="LOC-INC-002",
        category="Theft",
        severity=2,
        incident_time=datetime.now(timezone.utc),
        location=create_point_geometry(13.1000, 77.6000),  # ~14 km away
        is_active=True,
    )
    inc3 = CrimeIncident(
        incident_number="LOC-INC-003",
        category="Robbery",
        severity=5,
        incident_time=datetime.now(timezone.utc),
        location=create_point_geometry(12.9780, 77.6000),  # ~0.9 km away
        is_active=False,  # Inactive
    )
    db_session.add_all([inc1, inc2, inc3])
    await db_session.commit()

    # Search within 3.0 km
    results = await LocationService.get_nearby_incidents(
        db_session,
        latitude=12.9716,
        longitude=77.5946,
        radius_km=3.0,
        is_active=True,
    )
    assert len(results) == 1
    assert results[0][0].incident_number == "LOC-INC-001"
    assert results[0][1] < 1.0


@pytest.mark.asyncio
async def test_nearest_suitable_patrol_candidates(db_session: AsyncSession):
    # Seed patrol units
    unit_close = PatrolUnit(
        call_sign="UNIT-CLOSE",
        status=PatrolStatus.AVAILABLE,
        current_location=create_point_geometry(12.9750, 77.5960),  # ~0.4 km away
        is_active=True,
    )
    unit_mid = PatrolUnit(
        call_sign="UNIT-MID",
        status=PatrolStatus.AVAILABLE,
        current_location=create_point_geometry(12.9900, 77.6100),  # ~2.6 km away
        is_active=True,
    )
    unit_busy = PatrolUnit(
        call_sign="UNIT-BUSY",
        status=PatrolStatus.BUSY,
        current_location=create_point_geometry(12.9720, 77.5950),  # ~0.1 km away but BUSY
        is_active=True,
    )
    unit_far = PatrolUnit(
        call_sign="UNIT-FAR",
        status=PatrolStatus.AVAILABLE,
        current_location=create_point_geometry(13.2000, 77.7000),  # ~30 km away
        is_active=True,
    )
    db_session.add_all([unit_close, unit_mid, unit_busy, unit_far])
    await db_session.commit()

    # Query nearest suitable available units (max_radius 10km, max_candidates 2)
    candidates = await LocationService.get_nearest_suitable_patrol_candidates(
        db_session,
        latitude=12.9716,
        longitude=77.5946,
        max_candidates=2,
        max_radius_km=10.0,
        allowed_statuses=[PatrolStatus.AVAILABLE],
    )
    assert len(candidates) == 2
    # Sorted strictly by distance
    assert candidates[0][0].call_sign == "UNIT-CLOSE"
    assert candidates[1][0].call_sign == "UNIT-MID"
    assert candidates[0][1] < candidates[1][1]


@pytest.mark.asyncio
async def test_routing_service_fallback_on_unreachable_endpoint():
    # Calling with unreachable URL triggers fallback gracefully
    result = await RoutingService.get_route(
        origin_lat=12.9716,
        origin_lng=77.5946,
        dest_lat=12.9784,
        dest_lng=77.6408,
        custom_base_url="http://127.0.0.1:9999",  # non-existent port
        timeout_seconds=0.5,
    )
    assert result.is_fallback_estimate is True
    assert result.straight_line_distance_km > 0.0
    # Road distance is estimated higher than straight line distance
    assert result.road_distance_km > result.straight_line_distance_km
    assert result.duration_seconds > 0.0
    assert result.duration_minutes > 0.0


@pytest.mark.asyncio
async def test_routing_service_success_with_mock(monkeypatch):
    mock_response_data = {
        "routes": [
            {
                "distance": 5850.5,  # 5.85 km
                "duration": 720.0,   # 12 minutes
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[77.5946, 12.9716], [77.6408, 12.9784]],
                },
            }
        ]
    }

    async def mock_get(*args, **kwargs):
        return Response(200, json=mock_response_data)

    monkeypatch.setattr("httpx.AsyncClient.get", mock_get)

    result = await RoutingService.get_route(
        origin_lat=12.9716,
        origin_lng=77.5946,
        dest_lat=12.9784,
        dest_lng=77.6408,
    )

    assert result.is_fallback_estimate is False
    assert result.road_distance_km == 5.851
    assert result.duration_seconds == 720.0
    assert result.duration_minutes == 12.0
    assert result.straight_line_distance_km < result.road_distance_km
    assert result.route_geometry is not None
