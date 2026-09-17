from datetime import datetime
from typing import Optional
from geoalchemy2 import Geography
from sqlalchemy import Boolean, DateTime, Integer, String, Enum as SAEnum, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base
from app.models.enums import SafeHelpPointType


class SafeHelpPoint(Base):
    __tablename__ = "safe_help_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[SafeHelpPointType] = mapped_column(
        SAEnum(SafeHelpPointType, name="safe_help_point_type_enum", native_enum=False),
        default=SafeHelpPointType.HELP_DESK,
        nullable=False,
        index=True,
    )
    location = mapped_column(Geography(geometry_type="POINT", srid=4326, spatial_index=True), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    contact_number: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
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
