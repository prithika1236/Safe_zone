from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from geoalchemy2 import Geography
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Enum as SAEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.enums import AssignmentStatus, PatrolStatus

if TYPE_CHECKING:
    from app.models.user import PoliceOfficer
    from app.models.optimization import OptimizationRun, PRPLocation
    from app.models.sos import SOSRequest


class PatrolUnit(Base):
    __tablename__ = "patrol_units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    call_sign: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    officer_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("police_officers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[PatrolStatus] = mapped_column(
        SAEnum(PatrolStatus, name="patrol_status_enum", native_enum=False),
        default=PatrolStatus.OFF_DUTY,
        nullable=False,
        index=True,
    )
    current_location = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=True),
        nullable=True,
    )
    last_location_update: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
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
    officer: Mapped[Optional["PoliceOfficer"]] = relationship(
        "PoliceOfficer",
        back_populates="patrol_units",
    )
    assignments: Mapped[List["PatrolAssignment"]] = relationship(
        "PatrolAssignment",
        back_populates="patrol_unit",
        cascade="all, delete-orphan",
    )
    assigned_sos_requests: Mapped[List["SOSRequest"]] = relationship(
        "SOSRequest",
        back_populates="assigned_patrol_unit",
    )
    location_updates: Mapped[List["LocationUpdate"]] = relationship(
        "LocationUpdate",
        back_populates="patrol_unit",
        cascade="all, delete-orphan",
    )


class PatrolAssignment(Base):
    __tablename__ = "patrol_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patrol_unit_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("patrol_units.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    prp_location_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("prp_locations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    optimization_run_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("optimization_runs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    shift: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[AssignmentStatus] = mapped_column(
        SAEnum(AssignmentStatus, name="assignment_status_enum", native_enum=False),
        default=AssignmentStatus.ASSIGNED,
        nullable=False,
        index=True,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    arrived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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
    patrol_unit: Mapped["PatrolUnit"] = relationship(
        "PatrolUnit",
        back_populates="assignments",
    )
    prp_location: Mapped["PRPLocation"] = relationship(
        "PRPLocation",
        back_populates="assignments",
    )
    optimization_run: Mapped["OptimizationRun"] = relationship(
        "OptimizationRun",
        back_populates="assignments",
    )


class LocationUpdate(Base):
    __tablename__ = "location_updates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    patrol_unit_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("patrol_units.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    location = mapped_column(Geography(geometry_type="POINT", srid=4326, spatial_index=True), nullable=False)
    speed: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    heading: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    battery_level: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    patrol_unit: Mapped["PatrolUnit"] = relationship(
        "PatrolUnit",
        back_populates="location_updates",
    )
