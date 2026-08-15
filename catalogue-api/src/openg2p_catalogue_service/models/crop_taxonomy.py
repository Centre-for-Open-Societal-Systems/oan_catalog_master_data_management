"""Release-scoped canonical crop-variety detail models."""

from decimal import Decimal

from openg2p_fastapi_common.models import BaseORMModel
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column


class CropVarietySourceRecord(BaseORMModel):
    __tablename__ = "crop_variety_source_records"
    __table_args__ = (
        UniqueConstraint(
            "release_id",
            "source_record_code",
            name="uq_crop_variety_source_release_code",
        ),
        UniqueConstraint(
            "release_id",
            "source_row_number",
            name="uq_crop_variety_source_release_row",
        ),
        CheckConstraint(
            "source_row_number IS NULL OR source_row_number > 0",
            name="ck_crop_variety_source_row",
        ),
        CheckConstraint(
            "release_year IS NULL OR release_year BETWEEN 1800 AND 2200",
            name="ck_crop_variety_source_release_year",
        ),
        CheckConstraint(
            "altitude_min_m IS NULL OR altitude_max_m IS NULL OR altitude_max_m >= altitude_min_m",
            name="ck_crop_variety_source_altitude_range",
        ),
        CheckConstraint(
            "rainfall_min_mm IS NULL OR rainfall_max_mm IS NULL OR rainfall_max_mm >= rainfall_min_mm",
            name="ck_crop_variety_source_rainfall_range",
        ),
        CheckConstraint(
            "days_to_maturity_min IS NULL OR days_to_maturity_max IS NULL "
            "OR days_to_maturity_max >= days_to_maturity_min",
            name="ck_crop_variety_source_maturity_range",
        ),
        CheckConstraint(
            "yield_research_min_qt_ha IS NULL OR yield_research_max_qt_ha IS NULL "
            "OR yield_research_max_qt_ha >= yield_research_min_qt_ha",
            name="ck_crop_variety_source_research_yield_range",
        ),
        CheckConstraint(
            "yield_farmer_min_qt_ha IS NULL OR yield_farmer_max_qt_ha IS NULL "
            "OR yield_farmer_max_qt_ha >= yield_farmer_min_qt_ha",
            name="ck_crop_variety_source_farmer_yield_range",
        ),
        Index(
            "ix_crop_variety_source_release_variety",
            "release_id",
            "variety_value_id",
        ),
        Index("ix_crop_variety_source_release_year", "release_id", "release_year"),
    )

    variety_source_record_id: Mapped[str] = mapped_column(String, primary_key=True)
    release_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("catalogue_releases.release_id", ondelete="CASCADE"),
        nullable=False,
    )
    variety_value_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("catalogue_values.catalogue_value_id", ondelete="CASCADE"),
        nullable=False,
    )
    source_record_code: Mapped[str] = mapped_column(String, nullable=False)
    source_row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    centre: Mapped[str] = mapped_column(Text, nullable=False)
    release_year_raw: Mapped[str] = mapped_column(String, nullable=False)
    release_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    altitude_min_m: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    altitude_max_m: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    rainfall_min_mm: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    rainfall_max_mm: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    days_to_maturity_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    days_to_maturity_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    yield_research_min_qt_ha: Mapped[Decimal | None] = mapped_column(Numeric(16, 4), nullable=True)
    yield_research_max_qt_ha: Mapped[Decimal | None] = mapped_column(Numeric(16, 4), nullable=True)
    yield_farmer_min_qt_ha: Mapped[Decimal | None] = mapped_column(Numeric(16, 4), nullable=True)
    yield_farmer_max_qt_ha: Mapped[Decimal | None] = mapped_column(Numeric(16, 4), nullable=True)
    seed_rate_kg_ha: Mapped[Decimal | None] = mapped_column(Numeric(16, 4), nullable=True)
    adaptation_area: Mapped[str | None] = mapped_column(Text, nullable=True)
    planting_date_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    crop_pest_reaction: Mapped[str | None] = mapped_column(Text, nullable=True)


class CropCharacteristicDefinition(BaseORMModel):
    __tablename__ = "crop_characteristic_definitions"
    __table_args__ = (
        UniqueConstraint(
            "release_id",
            "characteristic_code",
            name="uq_crop_characteristic_release_code",
        ),
        CheckConstraint(
            "value_type IN ('TEXT', 'INTEGER', 'DECIMAL', 'BOOLEAN', 'RANGE')",
            name="ck_crop_characteristic_value_type",
        ),
        Index(
            "ix_crop_characteristic_release_category",
            "release_id",
            "applicable_category_value_id",
        ),
    )

    characteristic_definition_id: Mapped[str] = mapped_column(String, primary_key=True)
    release_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("catalogue_releases.release_id", ondelete="CASCADE"),
        nullable=False,
    )
    characteristic_code: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    value_type: Mapped[str] = mapped_column(String, nullable=False)
    default_unit_code: Mapped[str | None] = mapped_column(String, nullable=True)
    applicable_category_value_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("catalogue_values.catalogue_value_id", ondelete="CASCADE"),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class CropVarietyCharacteristic(BaseORMModel):
    __tablename__ = "crop_variety_characteristics"
    __table_args__ = (
        CheckConstraint(
            "value_min IS NULL OR value_max IS NULL OR value_max >= value_min",
            name="ck_crop_variety_characteristic_value_range",
        ),
        Index(
            "ix_crop_variety_characteristic_definition",
            "characteristic_definition_id",
        ),
    )

    variety_source_record_id: Mapped[str] = mapped_column(
        String,
        ForeignKey(
            "crop_variety_source_records.variety_source_record_id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )
    characteristic_definition_id: Mapped[str] = mapped_column(
        String,
        ForeignKey(
            "crop_characteristic_definitions.characteristic_definition_id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )
    raw_value: Mapped[str] = mapped_column(Text, nullable=False)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_numeric: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    value_boolean: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    value_min: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    value_max: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    unit_code: Mapped[str | None] = mapped_column(String, nullable=True)
