import uuid
from datetime import date
from decimal import Decimal

from openg2p_fastapi_common.models import BaseORMModel
from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class GeographyLevel(BaseORMModel):
    """A release-specific administrative level such as region or woreda."""

    __tablename__ = "geography_levels"
    __table_args__ = (
        UniqueConstraint("release_id", "code", name="uq_geography_level_release_code"),
        UniqueConstraint("release_id", "level_order", name="uq_geography_level_release_order"),
        CheckConstraint("level_order >= 0", name="ck_geography_level_order"),
    )

    geography_level_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    release_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("catalogue_releases.release_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    display_name_i18n: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    level_order: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_level_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("geography_levels.geography_level_id"),
        nullable=True,
        index=True,
    )


class GeographyUnit(BaseORMModel):
    """A versioned administrative unit exposed to registry consumers."""

    __tablename__ = "geography_units"
    __table_args__ = (
        UniqueConstraint("geography_level_id", "code", name="uq_geography_unit_level_code"),
        CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from",
            name="ck_geography_unit_dates",
        ),
    )

    geography_unit_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    geography_level_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("geography_levels.geography_level_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    display_name_amh: Mapped[str | None] = mapped_column(String, nullable=True)
    display_name_i18n: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    parent_unit_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("geography_units.geography_unit_id"),
        nullable=True,
        index=True,
    )
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(12, 8), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(12, 8), nullable=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="ACTIVE", index=True)
    aliases: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    unit_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
