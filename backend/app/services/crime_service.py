import csv
from datetime import datetime, timezone
import io
import math
from typing import Any, List, Optional, Tuple
from dateutil import parser as date_parser
from geoalchemy2.elements import WKTElement
from geoalchemy2.shape import to_shape
from shapely import wkb, wkt
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crime import CrimeIncident
from app.schemas.crime import (
    CSVImportSummaryResponse,
    CSVRowError,
    CrimeIncidentCreateRequest,
    CrimeIncidentResponse,
    CrimeIncidentUpdateRequest,
)


def extract_coordinates(location: Any) -> Tuple[float, float]:
    """Extract (latitude, longitude) from PostGIS spatial geometry, WKB, WKT, or Shapely."""
    if location is None:
        return 0.0, 0.0

    # 1. Try GeoAlchemy2 to_shape
    try:
        shape = to_shape(location)
        return float(shape.y), float(shape.x)
    except Exception:
        pass

    # 2. Try WKB binary decoding
    if isinstance(location, (bytes, bytearray, memoryview)):
        try:
            shape = wkb.loads(bytes(location))
            return float(shape.y), float(shape.x)
        except Exception:
            pass

    # 3. Try WKT string decoding
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

    # 4. Check attributes directly
    if hasattr(location, "y") and hasattr(location, "x"):
        return float(location.y), float(location.x)

    return 0.0, 0.0


def create_point_geometry(latitude: float, longitude: float) -> WKTElement:
    """Create a PostGIS Point geometry with SRID 4326 (WGS84)."""
    return WKTElement(f"POINT({longitude} {latitude})", srid=4326)


class CrimeService:
    @staticmethod
    def _format_crime_response(crime: CrimeIncident) -> CrimeIncidentResponse:
        lat, lng = extract_coordinates(crime.location)
        return CrimeIncidentResponse(
            id=crime.id,
            incident_number=crime.incident_number,
            category=crime.category,
            severity=crime.severity,
            incident_time=crime.incident_time,
            latitude=lat,
            longitude=lng,
            description=crime.description,
            is_active=crime.is_active,
            created_at=crime.created_at,
            updated_at=crime.updated_at,
        )

    @classmethod
    async def create_crime(
        cls,
        db: AsyncSession,
        payload: CrimeIncidentCreateRequest,
    ) -> CrimeIncidentResponse:
        incident_num = payload.incident_number.strip()
        existing = await db.execute(
            select(CrimeIncident).where(CrimeIncident.incident_number == incident_num)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Crime incident with number '{incident_num}' already exists")

        # Timezone-aware timestamp
        inc_time = payload.incident_time
        if inc_time.tzinfo is None:
            inc_time = inc_time.replace(tzinfo=timezone.utc)

        crime = CrimeIncident(
            incident_number=incident_num,
            category=payload.category.strip(),
            severity=payload.severity,
            incident_time=inc_time,
            location=create_point_geometry(payload.latitude, payload.longitude),
            description=payload.description.strip() if payload.description else None,
            is_active=payload.is_active,
        )
        db.add(crime)
        await db.commit()
        await db.refresh(crime)
        return cls._format_crime_response(crime)

    @classmethod
    async def get_crime(
        cls,
        db: AsyncSession,
        crime_id: int,
    ) -> Optional[CrimeIncidentResponse]:
        res = await db.execute(select(CrimeIncident).where(CrimeIncident.id == crime_id))
        crime = res.scalar_one_or_none()
        if not crime:
            return None
        return cls._format_crime_response(crime)

    @classmethod
    async def list_crimes(
        cls,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 50,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        category: Optional[str] = None,
        min_severity: Optional[int] = None,
        max_severity: Optional[int] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[CrimeIncidentResponse], int, int]:
        query = select(CrimeIncident)
        count_query = select(func.count(CrimeIncident.id))

        if start_date is not None:
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
            query = query.where(CrimeIncident.incident_time >= start_date)
            count_query = count_query.where(CrimeIncident.incident_time >= start_date)

        if end_date is not None:
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)
            query = query.where(CrimeIncident.incident_time <= end_date)
            count_query = count_query.where(CrimeIncident.incident_time <= end_date)

        if category:
            query = query.where(CrimeIncident.category.ilike(f"%{category.strip()}%"))
            count_query = count_query.where(CrimeIncident.category.ilike(f"%{category.strip()}%"))

        if min_severity is not None:
            query = query.where(CrimeIncident.severity >= min_severity)
            count_query = count_query.where(CrimeIncident.severity >= min_severity)

        if max_severity is not None:
            query = query.where(CrimeIncident.severity <= max_severity)
            count_query = count_query.where(CrimeIncident.severity <= max_severity)

        if is_active is not None:
            query = query.where(CrimeIncident.is_active == is_active)
            count_query = count_query.where(CrimeIncident.is_active == is_active)

        if search:
            search_term = f"%{search.strip()}%"
            filter_expr = or_(
                CrimeIncident.incident_number.ilike(search_term),
                CrimeIncident.category.ilike(search_term),
                CrimeIncident.description.ilike(search_term),
            )
            query = query.where(filter_expr)
            count_query = count_query.where(filter_expr)

        total_res = await db.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(CrimeIncident.incident_time.desc()).offset((page - 1) * page_size).limit(page_size)
        res = await db.execute(query)
        crimes = res.scalars().all()

        items = [cls._format_crime_response(c) for c in crimes]
        pages = math.ceil(total / page_size) if page_size > 0 else 1
        return items, total, pages

    @classmethod
    async def update_crime(
        cls,
        db: AsyncSession,
        crime_id: int,
        payload: CrimeIncidentUpdateRequest,
    ) -> Optional[CrimeIncidentResponse]:
        res = await db.execute(select(CrimeIncident).where(CrimeIncident.id == crime_id))
        crime = res.scalar_one_or_none()
        if not crime:
            return None

        if payload.category is not None:
            crime.category = payload.category.strip()
        if payload.severity is not None:
            crime.severity = payload.severity
        if payload.incident_time is not None:
            inc_time = payload.incident_time
            if inc_time.tzinfo is None:
                inc_time = inc_time.replace(tzinfo=timezone.utc)
            crime.incident_time = inc_time

        if payload.latitude is not None and payload.longitude is not None:
            crime.location = create_point_geometry(payload.latitude, payload.longitude)

        if payload.description is not None:
            crime.description = payload.description.strip() if payload.description else None
        if payload.is_active is not None:
            crime.is_active = payload.is_active

        await db.commit()
        await db.refresh(crime)
        return cls._format_crime_response(crime)

    @classmethod
    async def deactivate_crime(
        cls,
        db: AsyncSession,
        crime_id: int,
    ) -> bool:
        res = await db.execute(select(CrimeIncident).where(CrimeIncident.id == crime_id))
        crime = res.scalar_one_or_none()
        if not crime:
            return False

        crime.is_active = False
        await db.commit()
        return True

    @classmethod
    async def import_csv(
        cls,
        db: AsyncSession,
        csv_text: str,
    ) -> CSVImportSummaryResponse:
        """Import crimes from CSV with robust row-level validation and partial success tolerance."""
        reader = csv.DictReader(io.StringIO(csv_text))
        if not reader.fieldnames:
            raise ValueError("CSV file is empty or missing headers")

        # Normalize header keys
        header_map = {name.strip().lower().replace(" ", "_"): name for name in reader.fieldnames}
        required_fields = ["incident_number", "category", "severity", "incident_time", "latitude", "longitude"]
        missing = [rf for rf in required_fields if rf not in header_map]
        if missing:
            raise ValueError(f"CSV missing required columns: {', '.join(missing)}")

        total_rows = 0
        imported_count = 0
        errors: List[CSVRowError] = []
        seen_incident_numbers = set()

        for idx, row in enumerate(reader, start=2):  # line 2 is first data row
            total_rows += 1
            row_data = {k: row[v].strip() if row[v] else "" for k, v in header_map.items()}

            incident_num = row_data.get("incident_number", "")
            if not incident_num:
                errors.append(CSVRowError(row_number=idx, incident_number=None, error="Incident number is required"))
                continue

            if incident_num in seen_incident_numbers:
                errors.append(CSVRowError(row_number=idx, incident_number=incident_num, error=f"Duplicate incident number '{incident_num}' in CSV"))
                continue

            # Check database for existing incident number
            existing = await db.execute(select(CrimeIncident.id).where(CrimeIncident.incident_number == incident_num))
            if existing.scalar_one_or_none():
                errors.append(CSVRowError(row_number=idx, incident_number=incident_num, error=f"Incident number '{incident_num}' already exists in database"))
                continue

            category = row_data.get("category", "")
            if not category:
                errors.append(CSVRowError(row_number=idx, incident_number=incident_num, error="Category is required"))
                continue

            # Severity validation
            try:
                severity = int(row_data.get("severity", "1"))
                if severity < 1 or severity > 5:
                    raise ValueError()
            except ValueError:
                errors.append(CSVRowError(row_number=idx, incident_number=incident_num, error="Severity must be an integer between 1 and 5"))
                continue

            # Timestamp validation
            time_raw = row_data.get("incident_time", "")
            try:
                inc_time = date_parser.parse(time_raw)
                if inc_time.tzinfo is None:
                    inc_time = inc_time.replace(tzinfo=timezone.utc)
            except Exception:
                errors.append(CSVRowError(row_number=idx, incident_number=incident_num, error=f"Invalid timestamp format: '{time_raw}'"))
                continue

            # Coordinates validation
            try:
                lat = float(row_data.get("latitude", ""))
                if lat < -90.0 or lat > 90.0:
                    raise ValueError()
            except ValueError:
                errors.append(CSVRowError(row_number=idx, incident_number=incident_num, error="Latitude must be a float between -90 and 90"))
                continue

            try:
                lng = float(row_data.get("longitude", ""))
                if lng < -180.0 or lng > 180.0:
                    raise ValueError()
            except ValueError:
                errors.append(CSVRowError(row_number=idx, incident_number=incident_num, error="Longitude must be a float between -180 and 180"))
                continue

            description = row_data.get("description", None) or None
            is_active_val = row_data.get("is_active", "true").lower() not in ("false", "0", "no")

            crime = CrimeIncident(
                incident_number=incident_num,
                category=category,
                severity=severity,
                incident_time=inc_time,
                location=create_point_geometry(lat, lng),
                description=description,
                is_active=is_active_val,
            )
            db.add(crime)
            seen_incident_numbers.add(incident_num)
            imported_count += 1

        if imported_count > 0:
            await db.commit()

        return CSVImportSummaryResponse(
            total_rows=total_rows,
            imported_count=imported_count,
            failed_count=len(errors),
            errors=errors,
        )
