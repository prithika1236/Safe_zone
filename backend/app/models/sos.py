from datetime import datetime
from typing import TYPE_CHECKING, Optional
from geoalchemy2 import Geography
from sqlalchemy import DateTime, ForeignKey, Integer, Text, Enum as SAEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base
from app.models.enums import SOSStatus

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.patrol import PatrolUnit


class SOSRequest(Base):
    __tablename__ = "sos_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    citizen_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    location = mapped_column(Geography(geometry_type="POINT", srid=4326, spatial_index=True), nullable=False)
    status: Mapped[SOSStatus] = mapped_column(
        SAEnum(SOSStatus, name="sos_status_enum", native_enum=False),
        default=SOSStatus.PENDING,
        nullable=False,
        index=True,
    )
    assigned_patrol_unit_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("patrol_units.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    trigger_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
        nullable=False,
    )
    accepted_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    en_route_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    arrived_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    resolved_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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
    citizen: Mapped["User"] = relationship(
        "User",
        back_populates="sos_requests",
        foreign_keys=[citizen_id],
    )
    assigned_patrol_unit: Mapped[Optional["PatrolUnit"]] = relationship(
        "PatrolUnit",
        back_populates="assigned_sos_requests",
        foreign_keys=[assigned_patrol_unit_id],
    )
