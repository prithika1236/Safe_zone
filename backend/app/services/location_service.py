from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import math
from typing import Any, List, Optional, Sequence, Tuple
import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models.crime import CrimeIncident
from app.models.enums import PatrolStatus, SafeHelpPointType
from app.models.help_point import SafeHelpPoint
from app.models.patrol import PatrolUnit
from app.models.user import PoliceOfficer
from app.services.crime_service import extract_coordinates

logger = logging.getLogger("safezone.location")
settings = get_settings()

EARTH_RADIUS_KM = 6371.0


@dataclass
class Coordinate:
    latitude: float
    longitude: float

    def __post_init__(self):
        if not (-90.0 <= self.latitude <= 90.0):
            raise ValueError(f"Invalid latitude: {self.latitude}. Must be between -90 and 90.")
        if not (-180.0 <= self.longitude <= 180.0):
            raise ValueError(f"Invalid longitude: {self.longitude}. Must be between -180 and 180.")


@dataclass
class BoundingBox:
    min_lat: float
    min_lng: float
    max_lat: float
    max_lng: float


@dataclass
class RouteResult:
    origin: Tuple[float, float]
    destination: Tuple[float, float]
    straight_line_distance_km: float
    road_distance_km: float
    duration_seconds: float
    duration_minutes: float
    is_fallback_estimate: bool
    route_geometry: Optional[dict] = None


def validate_coordinates(latitude: float, longitude: float) -> bool:
    """Verify that latitude and longitude fall within legal WGS84 geographic boundaries."""
    return (-90.0 <= latitude <= 90.0) and (-180.0 <= longitude <= 180.0)


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the straight-line great-circle distance between two geographic coordinates in kilometers."""
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(EARTH_RADIUS_KM * c, 3)


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the straight-line great-circle distance in meters."""
    return round(haversine_distance_km(lat1, lon1, lat2, lon2) * 1000.0, 1)


def compute_bounding_box(latitude: float, longitude: float, radius_km: float) -> BoundingBox:
    """Compute a geographic bounding box enclosing a circle of radius_km centered at (latitude, longitude)."""
    lat_delta = math.degrees(radius_km / EARTH_RADIUS_KM)
    # Avoid division by zero at poles
    cos_lat = math.cos(math.radians(latitude))
    lng_delta = math.degrees(radius_km / (EARTH_RADIUS_KM * cos_lat)) if abs(cos_lat) > 1e-6 else 180.0

    return BoundingBox(
        min_lat=max(-90.0, latitude - lat_delta),
        min_lng=max(-180.0, longitude - lng_delta),
        max_lat=min(90.0, latitude + lat_delta),
        max_lng=min(180.0, longitude + lng_delta),
    )


def is_point_in_bbox(latitude: float, longitude: float, bbox: BoundingBox) -> bool:
    """Check if a coordinate lies within a geographic bounding box."""
    return (
        bbox.min_lat <= latitude <= bbox.max_lat
        and bbox.min_lng <= longitude <= bbox.max_lng
    )


class RoutingService:
    """OSRM-compatible routing abstraction with automatic graceful fallback estimation."""

    DEFAULT_URBAN_SPEED_KMH = 35.0
    FALLBACK_DETOUR_FACTOR = 1.3  # Road distance vs straight-line distance ratio

    @classmethod
    async def get_route(
        cls,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        timeout_seconds: float = 3.0,
        custom_base_url: Optional[str] = None,
    ) -> RouteResult:
        """
        Compute road route distance and travel duration between origin and destination.
        Clearly distinguishes straight-line distance from road route metrics.
        Gracefully falls back to heuristic estimation if routing server is unreachable.
        """
        straight_distance = haversine_distance_km(origin_lat, origin_lng, dest_lat, dest_lng)
        base_url = (custom_base_url or settings.OSRM_ROUTING_URL).rstrip("/")

        # Format: /route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=simplified&geometries=geojson
        endpoint = f"{base_url}/route/v1/driving/{origin_lng},{origin_lat};{dest_lng},{dest_lat}?overview=simplified&geometries=geojson"

        try:
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                response = await client.get(endpoint)
                if response.status_code == 200:
                    data = response.json()
                    routes = data.get("routes", [])
                    if routes:
                        primary_route = routes[0]
                        road_distance_meters = float(primary_route.get("distance", 0.0))
                        duration_secs = float(primary_route.get("duration", 0.0))
                        geometry = primary_route.get("geometry")

                        road_distance_km = round(road_distance_meters / 1000.0, 3)
                        return RouteResult(
                            origin=(origin_lat, origin_lng),
                            destination=(dest_lat, dest_lng),
                            straight_line_distance_km=straight_distance,
                            road_distance_km=road_distance_km,
                            duration_seconds=round(duration_secs, 1),
                            duration_minutes=round(duration_secs / 60.0, 1),
                            is_fallback_estimate=False,
                            route_geometry=geometry,
                        )
        except Exception as exc:
            logger.warning(
                "Routing service request failed (%s). Falling back to heuristic estimation.",
                str(exc),
            )

        # Fallback estimation based on urban road factor and average speed
        estimated_road_distance = round(straight_distance * cls.FALLBACK_DETOUR_FACTOR, 3)
        hours = estimated_road_distance / cls.DEFAULT_URBAN_SPEED_KMH
        duration_secs = round(hours * 3600.0, 1)

        return RouteResult(
            origin=(origin_lat, origin_lng),
            destination=(dest_lat, dest_lng),
            straight_line_distance_km=straight_distance,
            road_distance_km=estimated_road_distance,
            duration_seconds=duration_secs,
            duration_minutes=round(duration_secs / 60.0, 1),
            is_fallback_estimate=True,
            route_geometry=None,
        )


class LocationService:
    """Shared location and spatial search service across SafeZone domain entities."""

    @classmethod
    async def get_nearby_incidents(
        cls,
        db: AsyncSession,
        latitude: float,
        longitude: float,
        radius_km: float = 3.0,
        category: Optional[str] = None,
        min_severity: Optional[int] = None,
        max_severity: Optional[int] = None,
        is_active: bool = True,
    ) -> List[Tuple[CrimeIncident, float]]:
        """Find active crime incidents within radius_km, returning (incident, distance_km) sorted by distance."""
        bbox = compute_bounding_box(latitude, longitude, radius_km)
        query = select(CrimeIncident).where(CrimeIncident.is_active == is_active)

        if category:
            query = query.where(CrimeIncident.category.ilike(f"%{category.strip()}%"))
        if min_severity is not None:
            query = query.where(CrimeIncident.severity >= min_severity)
        if max_severity is not None:
            query = query.where(CrimeIncident.severity <= max_severity)

        res = await db.execute(query)
        incidents = res.scalars().all()

        results: List[Tuple[CrimeIncident, float]] = []
        for inc in incidents:
            inc_lat, inc_lng = extract_coordinates(inc.location)
            if is_point_in_bbox(inc_lat, inc_lng, bbox):
                dist = haversine_distance_km(latitude, longitude, inc_lat, inc_lng)
                if dist <= radius_km:
                    results.append((inc, dist))

        results.sort(key=lambda x: x[1])
        return results

    @classmethod
    async def get_nearby_patrols(
        cls,
        db: AsyncSession,
        latitude: float,
        longitude: float,
        radius_km: float = 10.0,
        status: Optional[PatrolStatus] = None,
        is_active: bool = True,
    ) -> List[Tuple[PatrolUnit, float]]:
        """Find active patrol units with recorded coordinates within radius_km."""
        bbox = compute_bounding_box(latitude, longitude, radius_km)
        query = (
            select(PatrolUnit)
            .where(
                PatrolUnit.is_active == is_active,
                PatrolUnit.current_location.is_not(None),
            )
            .options(selectinload(PatrolUnit.officer).selectinload(PoliceOfficer.user))
        )
        if status is not None:
            query = query.where(PatrolUnit.status == status)

        res = await db.execute(query)
        units = res.scalars().all()

        results: List[Tuple[PatrolUnit, float]] = []
        for unit in units:
            unit_lat, unit_lng = extract_coordinates(unit.current_location)
            if is_point_in_bbox(unit_lat, unit_lng, bbox):
                dist = haversine_distance_km(latitude, longitude, unit_lat, unit_lng)
                if dist <= radius_km:
                    results.append((unit, dist))

        results.sort(key=lambda x: x[1])
        return results

    @classmethod
    async def get_nearest_suitable_patrol_candidates(
        cls,
        db: AsyncSession,
        latitude: float,
        longitude: float,
        max_candidates: int = 5,
        max_radius_km: float = 20.0,
        allowed_statuses: Sequence[PatrolStatus] = (PatrolStatus.AVAILABLE,),
    ) -> List[Tuple[PatrolUnit, float]]:
        """
        Identify closest available patrol units suitable for emergency response or operational assignment.
        Returns units sorted strictly by straight-line distance.
        """
        query = (
            select(PatrolUnit)
            .where(
                PatrolUnit.is_active == True,
                PatrolUnit.current_location.is_not(None),
                PatrolUnit.status.in_(allowed_statuses),
            )
            .options(selectinload(PatrolUnit.officer).selectinload(PoliceOfficer.user))
        )
        res = await db.execute(query)
        units = res.scalars().all()

        candidates: List[Tuple[PatrolUnit, float]] = []
        for unit in units:
            unit_lat, unit_lng = extract_coordinates(unit.current_location)
            dist = haversine_distance_km(latitude, longitude, unit_lat, unit_lng)
            if dist <= max_radius_km:
                candidates.append((unit, dist))

        candidates.sort(key=lambda x: x[1])
        return candidates[:max_candidates]

    @classmethod
    async def get_nearby_safe_help_points(
        cls,
        db: AsyncSession,
        latitude: float,
        longitude: float,
        radius_km: float = 5.0,
        category: Optional[SafeHelpPointType] = None,
        is_verified: bool = True,
        is_active: bool = True,
    ) -> List[Tuple[SafeHelpPoint, float]]:
        """Find verified and active Safe Help Points within radius_km."""
        bbox = compute_bounding_box(latitude, longitude, radius_km)
        query = select(SafeHelpPoint).where(
            SafeHelpPoint.is_verified == is_verified,
            SafeHelpPoint.is_active == is_active,
        )
        if category is not None:
            query = query.where(SafeHelpPoint.category == category)

        res = await db.execute(query)
        hps = res.scalars().all()

        results: List[Tuple[SafeHelpPoint, float]] = []
        for hp in hps:
            hp_lat, hp_lng = extract_coordinates(hp.location)
            if is_point_in_bbox(hp_lat, hp_lng, bbox):
                dist = haversine_distance_km(latitude, longitude, hp_lat, hp_lng)
                if dist <= radius_km:
                    results.append((hp, dist))

        results.sort(key=lambda x: x[1])
        return results
