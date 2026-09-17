"""
SafeZone Risk Service.

Integrates spatial incident retrieval with the explainable mathematical risk engine,
supports geographic risk assessment, and manages RiskScore entity persistence.
"""

from datetime import datetime, timezone
import logging
from typing import List, Optional, Sequence, Union
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crime import CrimeIncident
from app.models.optimization import RiskScore
from app.optimization.risk_scoring import (
    IncidentRiskItem,
    RiskScoreBreakdown,
    RiskScoringConfig,
    calculate_risk,
)
from app.schemas.risk import RiskScoreRecordRead
from app.services.crime_service import create_point_geometry, extract_coordinates
from app.services.location_service import LocationService

logger = logging.getLogger("safezone.risk")


class RiskService:
    """Business service orchestrating explainable risk calculation and persistence."""

    @classmethod
    def calculate_risk_for_incidents(
        cls,
        incidents: Sequence[Union[CrimeIncident, IncidentRiskItem]],
        reference_time: Optional[datetime] = None,
        target_shift: Optional[str] = None,
        config: Optional[RiskScoringConfig] = None,
    ) -> RiskScoreBreakdown:
        """Directly calculate risk metrics for a sequence of incidents."""
        return calculate_risk(
            incidents=incidents,
            reference_time=reference_time,
            target_shift=target_shift,
            config=config,
        )

    @classmethod
    async def calculate_location_risk(
        cls,
        db: AsyncSession,
        latitude: float,
        longitude: float,
        radius_km: float = 3.0,
        reference_time: Optional[datetime] = None,
        target_shift: Optional[str] = None,
        config: Optional[RiskScoringConfig] = None,
    ) -> RiskScoreBreakdown:
        """
        Query active crime incidents within a radius and compute explainable risk breakdown.
        """
        nearby_items = await LocationService.get_nearby_incidents(
            db=db,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            is_active=True,
        )
        incidents = [item[0] for item in nearby_items]

        breakdown = calculate_risk(
            incidents=incidents,
            reference_time=reference_time,
            target_shift=target_shift,
            config=config,
        )

        breakdown.details["target_latitude"] = latitude
        breakdown.details["target_longitude"] = longitude
        breakdown.details["search_radius_km"] = radius_km
        return breakdown

    @classmethod
    async def record_risk_score(
        cls,
        db: AsyncSession,
        latitude: float,
        longitude: float,
        breakdown: RiskScoreBreakdown,
        grid_identifier: Optional[str] = None,
    ) -> RiskScore:
        """Persist a computed risk evaluation to the risk_scores database table."""
        record = RiskScore(
            location=create_point_geometry(latitude, longitude),
            grid_identifier=grid_identifier,
            frequency_score=breakdown.frequency_score,
            severity_score=breakdown.severity_score,
            recency_score=breakdown.recency_score,
            time_score=breakdown.time_score,
            total_risk_score=breakdown.total_risk_score,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    @classmethod
    async def get_historical_risk_scores(
        cls,
        db: AsyncSession,
        grid_identifier: Optional[str] = None,
        limit: int = 50,
    ) -> List[RiskScoreRecordRead]:
        """Retrieve previously saved risk score evaluations."""
        query = select(RiskScore).order_by(RiskScore.calculated_at.desc()).limit(limit)
        if grid_identifier:
            query = query.where(RiskScore.grid_identifier == grid_identifier)

        res = await db.execute(query)
        records = res.scalars().all()

        results: List[RiskScoreRecordRead] = []
        for r in records:
            lat, lng = extract_coordinates(r.location)
            results.append(
                RiskScoreRecordRead(
                    id=r.id,
                    latitude=lat,
                    longitude=lng,
                    grid_identifier=r.grid_identifier,
                    frequency_score=r.frequency_score,
                    severity_score=r.severity_score,
                    recency_score=r.recency_score,
                    time_score=r.time_score,
                    total_risk_score=r.total_risk_score,
                    calculated_at=r.calculated_at,
                )
            )
        return results
