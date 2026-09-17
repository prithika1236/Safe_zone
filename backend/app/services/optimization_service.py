"""
SafeZone Optimization Service.

Coordinates historical crime data retrieval, candidate PRP generation,
OR-Tools MCLP solver execution, and database persistence/approval workflows.
"""

from datetime import datetime, timezone
import logging
import math
from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.crime import CrimeIncident
from app.models.enums import OptimizationRunStatus, PRPStatus
from app.models.optimization import OptimizationRun, PRPLocation
from app.optimization.candidate_generator import (
    CandidateGenerationConfig,
    CandidateStrategy,
    PredefinedLocation,
    generate_prp_candidates,
)
from app.optimization.coverage import DemandPoint
from app.optimization.prp_optimizer import (
    PRPOptimizationResult,
    SelectedPRPItem,
    optimize_prp_coverage,
)
from app.optimization.risk_scoring import (
    RiskScoringConfig,
    compute_recency_factor,
    compute_time_factor,
    get_shift_target_hour,
)
from app.schemas.optimization import (
    OptimizationResultResponse,
    OptimizationRunRequest,
    PRPLocationResponse,
    SelectedPRPResponse,
    UncoveredDemandPointResponse,
)
from app.services.crime_service import create_point_geometry, extract_coordinates
from app.services.location_service import validate_coordinates

logger = logging.getLogger("safezone.optimization")


class OptimizationService:
    """Service orchestrating PRP coverage optimization and state transitions."""

    @classmethod
    async def _fetch_and_prepare_inputs(
        cls,
        db: AsyncSession,
        payload: OptimizationRunRequest,
        reference_time: datetime,
    ) -> Tuple[List[CrimeIncident], List[DemandPoint], List[PredefinedLocation], RiskScoringConfig]:
        """Fetch active crimes and construct demand points and configuration."""
        # 1. Fetch active crime incidents
        res = await db.execute(
            select(CrimeIncident).where(CrimeIncident.is_active == True)
        )
        crimes = list(res.scalars().all())

        # 2. Risk scoring configuration
        risk_cfg = RiskScoringConfig()
        if payload.weights_config:
            risk_cfg = RiskScoringConfig(
                weight_frequency=payload.weights_config.weight_frequency,
                weight_severity=payload.weights_config.weight_severity,
                weight_recency=payload.weights_config.weight_recency,
                weight_time=payload.weights_config.weight_time,
                decay_lambda=payload.weights_config.decay_lambda,
                max_frequency_benchmark=payload.weights_config.max_frequency_benchmark,
                severity_scale_max=payload.weights_config.severity_scale_max,
            )

        # 3. Build demand points
        target_hour = get_shift_target_hour(payload.shift)
        demand_points: List[DemandPoint] = []

        for c in crimes:
            lat, lng = extract_coordinates(c.location)
            if not validate_coordinates(lat, lng):
                continue

            rec_factor = compute_recency_factor(c.incident_time, reference_time, risk_cfg.decay_lambda)
            t_factor = compute_time_factor(c.incident_time, target_hour)
            # Weighted demand risk
            dem_weight = max(0.1, round(float(c.severity) * rec_factor * t_factor, 4))

            demand_points.append(
                DemandPoint(
                    id=c.id,
                    latitude=lat,
                    longitude=lng,
                    weight=dem_weight,
                    category=c.category,
                    metadata={"severity": c.severity, "incident_time": c.incident_time.isoformat()},
                )
            )

        # 4. Predefined locations
        predefined: List[PredefinedLocation] = []
        if payload.predefined_locations:
            for pl in payload.predefined_locations:
                if validate_coordinates(pl.latitude, pl.longitude):
                    predefined.append(
                        PredefinedLocation(
                            name=pl.name,
                            latitude=pl.latitude,
                            longitude=pl.longitude,
                            category=pl.category,
                            metadata=pl.metadata,
                        )
                    )

        return crimes, demand_points, predefined, risk_cfg

    @classmethod
    async def preview_optimization(
        cls,
        db: AsyncSession,
        payload: OptimizationRunRequest,
    ) -> OptimizationResultResponse:
        """Execute OR-Tools coverage optimization in preview mode without persisting to database."""
        ref_time = datetime.now(timezone.utc)
        crimes, demand_points, predefined, risk_cfg = await cls._fetch_and_prepare_inputs(db, payload, ref_time)

        # Generate candidate locations
        cand_config = CandidateGenerationConfig(
            strategy=CandidateStrategy.HYBRID if predefined else CandidateStrategy.CLUSTER_CENTROID,
            cluster_radius_km=payload.cluster_radius_km,
            min_candidate_separation_km=payload.min_candidate_separation_km,
            max_candidates=payload.max_candidates,
            coverage_radius_km=payload.coverage_radius_km,
            risk_config=risk_cfg,
        )

        candidates = generate_prp_candidates(
            incidents=crimes,
            predefined_locations=predefined,
            reference_time=ref_time,
            target_shift=payload.shift,
            config=cand_config,
        )

        # Solve MCLP
        result = optimize_prp_coverage(
            candidates=candidates,
            demand_points=demand_points,
            available_patrol_count=payload.available_patrol_count,
            coverage_radius_km=payload.coverage_radius_km,
            shift=payload.shift,
        )

        return cls._format_result_response(result, payload, run_id=None, created_at=ref_time)

    @classmethod
    async def run_optimization(
        cls,
        db: AsyncSession,
        payload: OptimizationRunRequest,
        user_id: Optional[int] = None,
    ) -> OptimizationResultResponse:
        """
        Execute OR-Tools coverage optimization, persist OptimizationRun and PRPLocations
        in proposed (RECOMMENDED) state, and return full result.
        """
        ref_time = datetime.now(timezone.utc)
        crimes, demand_points, predefined, risk_cfg = await cls._fetch_and_prepare_inputs(db, payload, ref_time)

        # Generate candidates
        cand_config = CandidateGenerationConfig(
            strategy=CandidateStrategy.HYBRID if predefined else CandidateStrategy.CLUSTER_CENTROID,
            cluster_radius_km=payload.cluster_radius_km,
            min_candidate_separation_km=payload.min_candidate_separation_km,
            max_candidates=payload.max_candidates,
            coverage_radius_km=payload.coverage_radius_km,
            risk_config=risk_cfg,
        )

        candidates = generate_prp_candidates(
            incidents=crimes,
            predefined_locations=predefined,
            reference_time=ref_time,
            target_shift=payload.shift,
            config=cand_config,
        )

        # Solve MCLP
        result = optimize_prp_coverage(
            candidates=candidates,
            demand_points=demand_points,
            available_patrol_count=payload.available_patrol_count,
            coverage_radius_km=payload.coverage_radius_km,
            shift=payload.shift,
        )

        # Persist OptimizationRun
        run_record = OptimizationRun(
            shift=payload.shift,
            available_patrol_count=payload.available_patrol_count,
            coverage_radius_km=payload.coverage_radius_km,
            parameters=result.run_parameters,
            metrics={
                **result.metrics,
                "total_demand_risk": result.total_demand_risk,
                "covered_demand_risk": result.covered_demand_risk,
                "coverage_percentage": result.coverage_percentage,
                "solver_status": result.solver_status,
            },
            status=OptimizationRunStatus.PENDING,
            created_by_id=user_id,
        )
        db.add(run_record)
        await db.flush()  # Obtain run_record.id

        # Persist generated PRPLocation records in initial RECOMMENDED status
        prp_entities: List[PRPLocation] = []
        for p in result.selected_prps:
            prp = PRPLocation(
                optimization_run_id=run_record.id,
                name=p.name,
                location=create_point_geometry(p.latitude, p.longitude),
                coverage_radius_km=payload.coverage_radius_km,
                priority_score=p.covered_demand_weight,
                status=PRPStatus.RECOMMENDED,
            )
            db.add(prp)
            prp_entities.append(prp)

        await db.commit()
        await db.refresh(run_record)

        # Attach persisted database IDs to selected PRPs in response
        for entity, prp_dto in zip(prp_entities, result.selected_prps):
            prp_dto.metadata["prp_db_id"] = entity.id

        return cls._format_result_response(
            result=result,
            payload=payload,
            run_id=run_record.id,
            created_at=run_record.created_at,
            prp_entities=prp_entities,
        )

    @classmethod
    async def get_optimization_run(
        cls,
        db: AsyncSession,
        run_id: int,
    ) -> Optional[OptimizationResultResponse]:
        """Fetch details of a previous optimization run including PRPs."""
        query = (
            select(OptimizationRun)
            .where(OptimizationRun.id == run_id)
            .options(selectinload(OptimizationRun.prp_locations))
        )
        res = await db.execute(query)
        run = res.scalar_one_or_none()
        if not run:
            return None

        metrics = run.metrics or {}
        selected_prps = []
        for prp in run.prp_locations:
            lat, lng = extract_coordinates(prp.location)
            selected_prps.append(
                SelectedPRPResponse(
                    id=prp.id,
                    name=prp.name,
                    latitude=lat,
                    longitude=lng,
                    coverage_radius_km=prp.coverage_radius_km,
                    priority_score=prp.priority_score,
                    status=prp.status.value,
                    covered_demand_count=0,
                    covered_demand_weight=prp.priority_score,
                    strategy="MCLP_OPTIMIZED",
                )
            )

        return OptimizationResultResponse(
            run_id=run.id,
            shift=run.shift,
            available_patrol_count=run.available_patrol_count,
            coverage_radius_km=run.coverage_radius_km,
            selected_count=len(selected_prps),
            total_demand_risk=float(metrics.get("total_demand_risk", 0.0)),
            covered_demand_risk=float(metrics.get("covered_demand_risk", 0.0)),
            coverage_percentage=float(metrics.get("coverage_percentage", 0.0)),
            solver_status=str(metrics.get("solver_status", run.status.value)),
            selected_prps=selected_prps,
            uncovered_demand_points=[],
            metrics=metrics,
            run_time_seconds=float(metrics.get("run_time_seconds", 0.0)),
            created_at=run.created_at,
        )

    @classmethod
    async def approve_optimization_run(
        cls,
        db: AsyncSession,
        run_id: int,
    ) -> Optional[OptimizationResultResponse]:
        """Approve an optimization run and activate its associated PRP locations."""
        query = (
            select(OptimizationRun)
            .where(OptimizationRun.id == run_id)
            .options(selectinload(OptimizationRun.prp_locations))
        )
        res = await db.execute(query)
        run = res.scalar_one_or_none()
        if not run:
            return None

        run.status = OptimizationRunStatus.APPROVED
        for prp in run.prp_locations:
            prp.status = PRPStatus.APPROVED

        await db.commit()
        await db.refresh(run)
        return await cls.get_optimization_run(db, run_id)

    @classmethod
    async def list_optimization_runs(
        cls,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[OptimizationResultResponse], int, int]:
        """List historical optimization runs with pagination."""
        count_res = await db.execute(select(func.count(OptimizationRun.id)))
        total = count_res.scalar() or 0

        query = (
            select(OptimizationRun)
            .options(selectinload(OptimizationRun.prp_locations))
            .order_by(OptimizationRun.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        res = await db.execute(query)
        runs = res.scalars().all()

        items: List[OptimizationResultResponse] = []
        for r in runs:
            item = await cls.get_optimization_run(db, r.id)
            if item:
                items.append(item)

        pages = math.ceil(total / page_size) if page_size > 0 else 1
        return items, total, pages

    @classmethod
    async def list_prp_locations(
        cls,
        db: AsyncSession,
        status: Optional[PRPStatus] = None,
        run_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[PRPLocationResponse], int, int]:
        """List PRP locations with optional status and run filtering."""
        query = select(PRPLocation)
        count_query = select(func.count(PRPLocation.id))

        if status is not None:
            query = query.where(PRPLocation.status == status)
            count_query = count_query.where(PRPLocation.status == status)
        if run_id is not None:
            query = query.where(PRPLocation.optimization_run_id == run_id)
            count_query = count_query.where(PRPLocation.optimization_run_id == run_id)

        total_res = await db.execute(count_query)
        total = total_res.scalar() or 0

        query = query.order_by(PRPLocation.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        res = await db.execute(query)
        prps = res.scalars().all()

        items: List[PRPLocationResponse] = []
        for p in prps:
            lat, lng = extract_coordinates(p.location)
            items.append(
                PRPLocationResponse(
                    id=p.id,
                    optimization_run_id=p.optimization_run_id,
                    name=p.name,
                    latitude=lat,
                    longitude=lng,
                    coverage_radius_km=p.coverage_radius_km,
                    priority_score=p.priority_score,
                    status=p.status,
                    created_at=p.created_at,
                    updated_at=p.updated_at,
                )
            )

        pages = math.ceil(total / page_size) if page_size > 0 else 1
        return items, total, pages

    @classmethod
    def _format_result_response(
        cls,
        result: PRPOptimizationResult,
        payload: OptimizationRunRequest,
        run_id: Optional[int],
        created_at: datetime,
        prp_entities: Optional[List[PRPLocation]] = None,
    ) -> OptimizationResultResponse:
        """Format domain PRPOptimizationResult into API response schema."""
        prp_responses = []
        for idx, p in enumerate(result.selected_prps):
            db_id = prp_entities[idx].id if (prp_entities and idx < len(prp_entities)) else None
            prp_responses.append(
                SelectedPRPResponse(
                    id=db_id,
                    name=p.name,
                    latitude=p.latitude,
                    longitude=p.longitude,
                    coverage_radius_km=p.coverage_radius_km,
                    priority_score=p.covered_demand_weight,
                    status=PRPStatus.RECOMMENDED.value if run_id else "PREVIEW",
                    covered_demand_count=p.covered_demand_count,
                    covered_demand_weight=p.covered_demand_weight,
                    strategy=p.strategy,
                    metadata=p.metadata,
                )
            )

        uncovered_responses = [
            UncoveredDemandPointResponse(
                id=d.id,
                latitude=d.latitude,
                longitude=d.longitude,
                weight=d.weight,
                category=d.category,
            )
            for d in result.uncovered_demand_points[:10]  # Return top 10 uncovered points
        ]

        return OptimizationResultResponse(
            run_id=run_id,
            shift=payload.shift,
            available_patrol_count=payload.available_patrol_count,
            coverage_radius_km=payload.coverage_radius_km,
            selected_count=result.selected_count,
            total_demand_risk=result.total_demand_risk,
            covered_demand_risk=result.covered_demand_risk,
            coverage_percentage=result.coverage_percentage,
            solver_status=result.solver_status,
            selected_prps=prp_responses,
            uncovered_demand_points=uncovered_responses,
            metrics=result.metrics,
            run_time_seconds=result.run_time_seconds,
            created_at=created_at,
        )
