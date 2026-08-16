"""Relational staging models for the versioned crop-taxonomy source."""

from decimal import Decimal

from openg2p_fastapi_common.models import BaseORMModel
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class StagedCropTaxonomyCategory(BaseORMModel):
    __tablename__ = "g2p_crop_taxonomy_category"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_g2p_crop_taxonomy_category_status",
        ),
    )

    category_code: Mapped[str] = mapped_column(String, primary_key=True)
    source_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    display_name_i18n: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="ACTIVE")


class StagedCropTaxonomyType(BaseORMModel):
    __tablename__ = "g2p_crop_taxonomy_type"
    __table_args__ = (
        UniqueConstraint(
            "category_code",
            "display_name",
            name="uq_g2p_crop_taxonomy_type_category_name",
        ),
        CheckConstraint(
            "source_reported_variety_count IS NULL OR source_reported_variety_count >= 0",
            name="ck_g2p_crop_taxonomy_type_variety_count",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_g2p_crop_taxonomy_type_status",
        ),
    )

    type_code: Mapped[str] = mapped_column(String, primary_key=True)
    source_id: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    category_code: Mapped[str] = mapped_column(
        String,
        ForeignKey("g2p_crop_taxonomy_category.category_code"),
        nullable=False,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    display_name_i18n: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    scientific_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    centre: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_reported_variety_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="ACTIVE")


class StagedCropVariety(BaseORMModel):
    __tablename__ = "g2p_crop_variety"
    __table_args__ = (
        UniqueConstraint(
            "type_code",
            "display_name",
            name="uq_g2p_crop_variety_type_name",
        ),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE')",
            name="ck_g2p_crop_variety_status",
        ),
    )

    variety_code: Mapped[str] = mapped_column(String, primary_key=True)
    type_code: Mapped[str] = mapped_column(
        String,
        ForeignKey("g2p_crop_taxonomy_type.type_code"),
        nullable=False,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    display_name_i18n: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="ACTIVE")


class StagedCropVarietySourceRecord(BaseORMModel):
    __tablename__ = "g2p_crop_variety_source_record"
    __table_args__ = (
        CheckConstraint(
            "source_row_number IS NULL OR source_row_number > 0",
            name="ck_g2p_crop_variety_source_row",
        ),
        CheckConstraint(
            "release_year IS NULL OR release_year BETWEEN 1800 AND 2200",
            name="ck_g2p_crop_variety_release_year",
        ),
        CheckConstraint(
            "altitude_min_m IS NULL OR altitude_max_m IS NULL OR altitude_max_m >= altitude_min_m",
            name="ck_g2p_crop_variety_altitude_range",
        ),
        CheckConstraint(
            "rainfall_min_mm IS NULL OR rainfall_max_mm IS NULL OR rainfall_max_mm >= rainfall_min_mm",
            name="ck_g2p_crop_variety_rainfall_range",
        ),
        CheckConstraint(
            "days_to_maturity_min IS NULL OR days_to_maturity_max IS NULL "
            "OR days_to_maturity_max >= days_to_maturity_min",
            name="ck_g2p_crop_variety_maturity_range",
        ),
        CheckConstraint(
            "yield_research_min_qt_ha IS NULL OR yield_research_max_qt_ha IS NULL "
            "OR yield_research_max_qt_ha >= yield_research_min_qt_ha",
            name="ck_g2p_crop_variety_research_yield_range",
        ),
        CheckConstraint(
            "yield_farmer_min_qt_ha IS NULL OR yield_farmer_max_qt_ha IS NULL "
            "OR yield_farmer_max_qt_ha >= yield_farmer_min_qt_ha",
            name="ck_g2p_crop_variety_farmer_yield_range",
        ),
    )

    source_record_code: Mapped[str] = mapped_column(String, primary_key=True)
    variety_code: Mapped[str] = mapped_column(
        String,
        ForeignKey("g2p_crop_variety.variety_code"),
        nullable=False,
        index=True,
    )
    source_row_number: Mapped[int | None] = mapped_column(Integer, nullable=True, unique=True)
    centre: Mapped[str] = mapped_column(Text, nullable=False)
    release_year_raw: Mapped[str] = mapped_column(String, nullable=False)
    release_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True, index=True)
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


class StagedCropCharacteristicDefinition(BaseORMModel):
    __tablename__ = "g2p_crop_characteristic_definition"
    __table_args__ = (
        CheckConstraint(
            "value_type IN ('TEXT', 'INTEGER', 'DECIMAL', 'BOOLEAN', 'RANGE')",
            name="ck_g2p_crop_characteristic_value_type",
        ),
    )

    characteristic_code: Mapped[str] = mapped_column(String, primary_key=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    value_type: Mapped[str] = mapped_column(String, nullable=False)
    default_unit_code: Mapped[str | None] = mapped_column(String, nullable=True)
    applicable_category_code: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("g2p_crop_taxonomy_category.category_code"),
        nullable=True,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class StagedCropVarietyCharacteristic(BaseORMModel):
    __tablename__ = "g2p_crop_variety_characteristic"
    __table_args__ = (
        CheckConstraint(
            "value_min IS NULL OR value_max IS NULL OR value_max >= value_min",
            name="ck_g2p_crop_variety_characteristic_range",
        ),
    )

    source_record_code: Mapped[str] = mapped_column(
        String,
        ForeignKey("g2p_crop_variety_source_record.source_record_code", ondelete="CASCADE"),
        primary_key=True,
    )
    characteristic_code: Mapped[str] = mapped_column(
        String,
        ForeignKey("g2p_crop_characteristic_definition.characteristic_code"),
        primary_key=True,
        index=True,
    )
    raw_value: Mapped[str] = mapped_column(Text, nullable=False)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_numeric: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    value_boolean: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    value_min: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    value_max: Mapped[Decimal | None] = mapped_column(Numeric(24, 8), nullable=True)
    unit_code: Mapped[str | None] = mapped_column(String, nullable=True)
