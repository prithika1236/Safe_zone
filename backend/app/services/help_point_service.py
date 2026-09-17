import csv
import io
import math
from typing import Any, List, Optional, Tuple
from geoalchemy2.elements import WKTElement
from geoalchemy2.shape import to_shape
from shapely import wkb, wkt
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import SafeHelpPointType
from app.models.help_point import SafeHelpPoint
from app.schemas.help_point import (
    HelpPointCSVImportSummary,
    HelpPointCSVRowError,
    SafeHelpPointCreateRequest,
    SafeHelpPointResponse,
    SafeHelpPointUpdateRequest,
)


def extract_coordinates(location: Any) -> Tuple[float, float]:
    """Extract (latitude, longitude) from PostGIS spatial geometry, WKB, WKT, or Shapely."""
    if location is None:
        return 0.0, 0.0

    try:
        shape = to_shape(location)
        return float(shape.y), float(shape.x)
    except Exception:
        pass

    if isinstance(location, (bytes, bytearray, memoryview)):
        try:
            shape = wkb.loads(bytes(location))
            return float(shape.y), float(shape.x)
        except Exception:
            pass

    loc_str = str(location)
    if "POINT" in loc_str.upper():
        try:
            clean = loc_str
            if "SRID=" in clean.upper():
                clean = clean.split(";", 1)[-1]
            shape = wkt.loads(clean.strip())
            return float(shape.y), float(shape.x)
        except Exception:
            clean_str = loc_str.upper().replace("POINT", "").replace("(", "").replace(")", "").replace("SRID=4326;", "").strip()
            parts = clean_str.split()
            if len(parts) >= 2:
                try:
                    return float(parts[1]), float(parts[0])
                except ValueError:
                    pass

    if hasattr(location, "y") and hasattr(location, "x"):
        return float(location.y), float(location.x)

    return 0.0, 0.0


def create_point_geometry(latitude: float, longitude: float) -> WKTElement:
    """Create a PostGIS Point geometry with SRID 4326 (WGS84)."""
    return WKTElement(f"POINT({longitude} {latitude})", srid=4326)


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two spatial coordinates in kilometers."""
    radius_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(radius_km * c, 3)


class HelpPointService:
    @staticmethod
    def _format_help_point_response(
        hp: SafeHelpPoint,
        distance_km: Optional[float] = None,
    ) -> SafeHelpPointResponse:
        lat, lng = extract_coordinates(hp.location)
        return SafeHelpPointResponse(
            id=hp.id,
            name=hp.name,
            category=hp.category,
            latitude=lat,
            longitude=lng,
            address=hp.address,
            contact_number=hp.contact_number,
            is_verified=hp.is_verified,
            is_active=hp.is_active,
            distance_km=distance_km,
            created_at=hp.created_at,
            updated_at=hp.updated_at,
        )

    @classmethod
    async def create_help_point(
        cls,
        db: AsyncSession,
        payload: SafeHelpPointCreateRequest,
    ) -> SafeHelpPointResponse:
        hp = SafeHelpPoint(
            name=payload.name.strip(),
            category=payload.category,
            location=create_point_geometry(payload.latitude, payload.longitude),
            address=payload.address.strip() if payload.address else None,
            contact_number=payload.contact_number.strip() if payload.contact_number else None,
            is_verified=payload.is_verified,
            is_active=payload.is_active,
        )
        db.add(hp)
        await db.commit()
        await db.refresh(hp)
        return cls._format_help_point_response(hp)

    @classmethod
    async def get_help_point(
        cls,
        db: AsyncSession,
        hp_id: int,
    ) -> Optional[SafeHelpPointResponse]:
        res = await db.execute(select(SafeHelpPoint).where(SafeHelpPoint.id == hp_id))
        hp = res.scalar_one_or_none()
        if not hp:
            return None
        return cls._format_help_point_response(hp)

    @classmethod
    async def list_help_points(
        cls,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 50,
        category: Optional[SafeHelpPointType] = None,
        is_verified: Optional[bool] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[SafeHelpPointResponse], int, int]:
        query = select(SafeHelpPoint)
        count_query = select(func.count(SafeHelpPoint.id))

        if category is not None:
            query = query.where(SafeHelpPoint.category == category)
            count_query = count_query.where(SafeHelpPoint.category == category)

        if is_verified is not None:
            query = query.where(SafeHelpPoint.is_verified == is_verified)
            count_query = count_query.where(SafeHelpPoint.is_verified == is_verified)

        if is_active is not None:
            query = query.where(SafeHelpPoint.is_active == is_active)
            count_query = count_query.where(SafeHelpPoint.is_active == is_active)

        if search:
            search_term = f"%{search.strip()}%"
            filter_expr = or_(
                SafeHelpPoint.name.ilike(search_term),
                SafeHelpPoint.address.ilike(search_term),
            )
            query = query.where(filter_expr)
            count_query = count_query.where(filter_expr)

        total_res = await db.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(SafeHelpPoint.id.asc()).offset((page - 1) * page_size).limit(page_size)
        res = await db.execute(query)
        hps = res.scalars().all()

        items = [cls._format_help_point_response(hp) for hp in hps]
        pages = math.ceil(total / page_size) if page_size > 0 else 1
        return items, total, pages

    @classmethod
    async def update_help_point(
        cls,
        db: AsyncSession,
        hp_id: int,
        payload: SafeHelpPointUpdateRequest,
    ) -> Optional[SafeHelpPointResponse]:
        res = await db.execute(select(SafeHelpPoint).where(SafeHelpPoint.id == hp_id))
        hp = res.scalar_one_or_none()
        if not hp:
            return None

        if payload.name is not None:
            hp.name = payload.name.strip()
        if payload.category is not None:
            hp.category = payload.category
        if payload.latitude is not None and payload.longitude is not None:
            hp.location = create_point_geometry(payload.latitude, payload.longitude)
        if payload.address is not None:
            hp.address = payload.address.strip() if payload.address else None
        if payload.contact_number is not None:
            hp.contact_number = payload.contact_number.strip() if payload.contact_number else None
        if payload.is_verified is not None:
            hp.is_verified = payload.is_verified
        if payload.is_active is not None:
            hp.is_active = payload.is_active

        await db.commit()
        await db.refresh(hp)
        return cls._format_help_point_response(hp)

    @classmethod
    async def toggle_verification(
        cls,
        db: AsyncSession,
        hp_id: int,
        is_verified: bool,
    ) -> Optional[SafeHelpPointResponse]:
        res = await db.execute(select(SafeHelpPoint).where(SafeHelpPoint.id == hp_id))
        hp = res.scalar_one_or_none()
        if not hp:
            return None

        hp.is_verified = is_verified
        await db.commit()
        await db.refresh(hp)
        return cls._format_help_point_response(hp)

    @classmethod
    async def toggle_activation(
        cls,
        db: AsyncSession,
        hp_id: int,
        is_active: bool,
    ) -> Optional[SafeHelpPointResponse]:
        res = await db.execute(select(SafeHelpPoint).where(SafeHelpPoint.id == hp_id))
        hp = res.scalar_one_or_none()
        if not hp:
            return None

        hp.is_active = is_active
        await db.commit()
        await db.refresh(hp)
        return cls._format_help_point_response(hp)

    # --- Citizen Operations (Strictly Verified + Active) ---

    @classmethod
    async def list_public_help_points(
        cls,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 50,
        category: Optional[SafeHelpPointType] = None,
    ) -> Tuple[List[SafeHelpPointResponse], int, int]:
        """Retrieve only VERIFIED and ACTIVE Safe Help Points."""
        query = (
            select(SafeHelpPoint)
            .where(
                SafeHelpPoint.is_verified == True,
                SafeHelpPoint.is_active == True,
            )
        )
        count_query = (
            select(func.count(SafeHelpPoint.id))
            .where(
                SafeHelpPoint.is_verified == True,
                SafeHelpPoint.is_active == True,
            )
        )

        if category is not None:
            query = query.where(SafeHelpPoint.category == category)
            count_query = count_query.where(SafeHelpPoint.category == category)

        total_res = await db.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(SafeHelpPoint.name.asc()).offset((page - 1) * page_size).limit(page_size)
        res = await db.execute(query)
        hps = res.scalars().all()

        items = [cls._format_help_point_response(hp) for hp in hps]
        pages = math.ceil(total / page_size) if page_size > 0 else 1
        return items, total, pages

    @classmethod
    async def query_nearby_help_points(
        cls,
        db: AsyncSession,
        latitude: float,
        longitude: float,
        radius_km: float = 5.0,
        category: Optional[SafeHelpPointType] = None,
        limit: int = 50,
    ) -> List[SafeHelpPointResponse]:
        """Query nearby VERIFIED + ACTIVE Safe Help Points within radius_km with distance calculation."""
        query = (
            select(SafeHelpPoint)
            .where(
                SafeHelpPoint.is_verified == True,
                SafeHelpPoint.is_active == True,
            )
        )
        if category is not None:
            query = query.where(SafeHelpPoint.category == category)

        res = await db.execute(query)
        hps = res.scalars().all()

        results_with_distance = []
        for hp in hps:
            hp_lat, hp_lng = extract_coordinates(hp.location)
            dist = haversine_distance_km(latitude, longitude, hp_lat, hp_lng)
            if dist <= radius_km:
                results_with_distance.append((hp, dist))

        # Sort by distance ascending
        results_with_distance.sort(key=lambda x: x[1])
        trimmed = results_with_distance[:limit]

        return [cls._format_help_point_response(hp, dist) for hp, dist in trimmed]

    @classmethod
    async def import_csv(
        cls,
        db: AsyncSession,
        csv_text: str,
    ) -> HelpPointCSVImportSummary:
        """Import Safe Help Points from CSV with row validation and partial success tolerance."""
        reader = csv.DictReader(io.StringIO(csv_text))
        if not reader.fieldnames:
            raise ValueError("CSV file is empty or missing headers")

        header_map = {name.strip().lower().replace(" ", "_"): name for name in reader.fieldnames}
        required_fields = ["name", "category", "latitude", "longitude"]
        missing = [rf for rf in required_fields if rf not in header_map]
        if missing:
            raise ValueError(f"CSV missing required columns: {', '.join(missing)}")

        total_rows = 0
        imported_count = 0
        errors: List[HelpPointCSVRowError] = []

        valid_categories = {cat.value: cat for cat in SafeHelpPointType}

        for idx, row in enumerate(reader, start=2):
            total_rows += 1
            row_data = {k: row[v].strip() if row[v] else "" for k, v in header_map.items()}

            name = row_data.get("name", "")
            if not name:
                errors.append(HelpPointCSVRowError(row_number=idx, name=None, error="Name is required"))
                continue

            cat_raw = row_data.get("category", "").upper().replace(" ", "_")
            if cat_raw not in valid_categories:
                errors.append(
                    HelpPointCSVRowError(
                        row_number=idx,
                        name=name,
                        error=f"Invalid category '{row_data.get('category')}'. Valid: {', '.join(valid_categories.keys())}",
                    )
                )
                continue
            category = valid_categories[cat_raw]

            try:
                lat = float(row_data.get("latitude", ""))
                if lat < -90.0 or lat > 90.0:
                    raise ValueError()
            except ValueError:
                errors.append(HelpPointCSVRowError(row_number=idx, name=name, error="Latitude must be a float between -90 and 90"))
                continue

            try:
                lng = float(row_data.get("longitude", ""))
                if lng < -180.0 or lng > 180.0:
                    raise ValueError()
            except ValueError:
                errors.append(HelpPointCSVRowError(row_number=idx, name=name, error="Longitude must be a float between -180 and 180"))
                continue

            address = row_data.get("address", "") or None
            contact = row_data.get("contact_number", "") or None
            is_verified = row_data.get("is_verified", "false").lower() in ("true", "1", "yes")
            is_active = row_data.get("is_active", "true").lower() not in ("false", "0", "no")

            hp = SafeHelpPoint(
                name=name,
                category=category,
                location=create_point_geometry(lat, lng),
                address=address,
                contact_number=contact,
                is_verified=is_verified,
                is_active=is_active,
            )
            db.add(hp)
            imported_count += 1

        if imported_count > 0:
            await db.commit()

        return HelpPointCSVImportSummary(
            total_rows=total_rows,
            imported_count=imported_count,
            failed_count=len(errors),
            errors=errors,
        )
