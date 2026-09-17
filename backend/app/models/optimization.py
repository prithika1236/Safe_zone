from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from geoalchemy2 import Geography
from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Enum as SAEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.enums import OptimizationRunStatus, PRPStatus

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.patrol import PatrolAssignment


class OptimizationRun(Base):
    __tablename__ = "optimization_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
        nullable=False,
    )
    shift: Mapped[str] = mapped_column(String(64), nullable=False)
    available_patrol_count: Mapped[int] = mapped_column(Integer, nullable=False)
    coverage_radius_km: Mapped[float] = mapped_column(Float, default=3.0, nullable=False)
    parameters: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    metrics: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    status: Mapped[OptimizationRunStatus] = mapped_column(
        SAEnum(OptimizationRunStatus, name="opt_run_status_enum", native_enum=False),
        default=OptimizationRunStatus.PENDING,
        nullable=False,
        index=True,
    )
    created_by_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    created_by: Mapped[Optional["User"]] = relationship("User", back_populates="optimization_runs")
    prp_locations: Mapped[List["PRPLocation"]] = relationship(
        "PRPLocation",
        back_populates="optimization_run",
        cascade="all, delete-orphan",
    )
    assignments: Mapped[List["PatrolAssignment"]] = relationship(
        "PatrolAssignment",
        back_populates="optimization_run",
    )


class PRPLocation(Base):
    __tablename__ = "prp_locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    optimization_run_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("optimization_runs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    location = mapped_column(Geography(geometry_type="POINT", srid=4326, spatial_index=True), nullable=False)
    coverage_radius_km: Mapped[float] = mapped_column(Float, default=3.0, nullable=False)
    priority_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[PRPStatus] = mapped_column(
        SAEnum(PRPStatus, name="prp_status_enum", native_enum=False),
        default=PRPStatus.RECOMMENDED,
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    optimization_run: Mapped["OptimizationRun"] = relationship(
        "OptimizationRun",
        back_populates="prp_locations",
    )
    assignments: Mapped[List["PatrolAssignment"]] = relationship(
        "PatrolAssignment",
        back_populates="prp_location",
    )


class RiskScore(Base):
    __tablename__ = "risk_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    location = mapped_column(Geography(geometry_type="POINT", srid=4326, spatial_index=True), nullable=False)
    grid_identifier: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    frequency_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    severity_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    recency_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    time_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_risk_score: Mapped[float] = mapped_column(Float, default=0.0, index=True, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
        nullable=False,
    )
