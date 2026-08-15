"""Compatibility staging models for the legacy SQL source files.

These tables deliberately preserve the SQL files' current column and constraint
names. They are an ingestion boundary, not the registry-facing data contract.
Validated publication will copy their data into release-specific canonical
catalogue, geography, and statistics tables.
"""

from datetime import datetime
from decimal import Decimal

from openg2p_fastapi_common.models import BaseORMModel
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column


class StagedCrop(BaseORMModel):
    __tablename__ = "g2p_crop"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    known_for: Mapped[str | None] = mapped_column(Text, nullable=True)
    num_field_inspection_needed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    isolation_distance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    preferred_ecological_zone_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scientific_name: Mapped[str | None] = mapped_column(String, nullable=True)
    centre: Mapped[str | None] = mapped_column(String, nullable=True)
    varieties_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    display_name_amh: Mapped[str | None] = mapped_column(String, nullable=True)
    taxonomy_type_code: Mapped[str | None] = mapped_column(String, nullable=True)
    taxonomy_source_id: Mapped[str | None] = mapped_column(String, nullable=True)
    taxonomy_category_code: Mapped[str | None] = mapped_column(String, nullable=True)
    taxonomy_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    record_source: Mapped[str] = mapped_column(String, nullable=False)
    varieties_count_source: Mapped[str] = mapped_column(String, nullable=False)
    taxonomy_match_method: Mapped[str] = mapped_column(String, nullable=False)
    taxonomy_match_status: Mapped[str] = mapped_column(String, nullable=False)
    category_source: Mapped[str] = mapped_column(String, nullable=False)


class StagedCropCategory(BaseORMModel):
    __tablename__ = "g2p_crop_category"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class StagedEcologicalZone(BaseORMModel):
    __tablename__ = "g2p_ecological_zone"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class StagedLivestockType(BaseORMModel):
    __tablename__ = "g2p_livestock_type"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    species_code: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon_url: Mapped[str | None] = mapped_column(String, nullable=True)
    dataset_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scientific_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    subfamily: Mapped[str | None] = mapped_column(Text, nullable=True)
    species_type_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chart_color: Mapped[str | None] = mapped_column(String, nullable=True)
    ear_tag_range: Mapped[str | None] = mapped_column(Text, nullable=True)
    in_lis_population: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    in_etlits_registry: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class StagedLivestockPopulation(BaseORMModel):
    __tablename__ = "g2p_livestock_population"
    __table_args__ = (
        UniqueConstraint(
            "species_code",
            "census_year",
            name="uq_g2p_livestock_population_species_year",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # The inherited SQL calls this species_code but stores g2p_livestock_type.id.
    species_code: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("g2p_livestock_type.id"),
        nullable=False,
        index=True,
    )
    census_year: Mapped[int] = mapped_column(Integer, nullable=False)
    population_total: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_record_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    create_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    write_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class StagedLivestockBreed(BaseORMModel):
    __tablename__ = "g2p_livestock_breed"
    __table_args__ = (
        UniqueConstraint(
            "species_id",
            "name",
            name="uq_g2p_livestock_breed_species_name",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    breed_code: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    abbreviation: Mapped[str | None] = mapped_column(String, nullable=True)
    species_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("g2p_livestock_type.id"),
        nullable=False,
        index=True,
    )
    breed_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    in_national_standard: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    in_etlits_registry: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)


class StagedLivestockGender(BaseORMModel):
    __tablename__ = "g2p_livestock_gender"

    code: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    in_etlits_registry: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class StagedLivestockLocationType(BaseORMModel):
    __tablename__ = "g2p_livestock_location_type"

    code: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    ethiopian_zone_name: Mapped[str | None] = mapped_column(String, nullable=True)
    altitude_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ecological_zone_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("g2p_ecological_zone.id"),
        nullable=True,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class StagedLivestockBodyCondition(BaseORMModel):
    __tablename__ = "g2p_livestock_body_condition"

    code: Mapped[str] = mapped_column(String, primary_key=True)
    bcs_score: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    condition_label: Mapped[str] = mapped_column(String, nullable=False)
    fatness_label: Mapped[str] = mapped_column(String, nullable=False)
    etlits_label: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class StagedLivestockProductionType(BaseORMModel):
    __tablename__ = "g2p_livestock_production_type"

    code: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    standard_purpose: Mapped[str | None] = mapped_column(String, nullable=True)
    in_national_standard: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    in_etlits_registry: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class StagedLivestockProductionTypeSpecies(BaseORMModel):
    __tablename__ = "g2p_livestock_production_type_species"

    production_type_code: Mapped[str] = mapped_column(
        String,
        ForeignKey("g2p_livestock_production_type.code", ondelete="CASCADE"),
        primary_key=True,
    )
    species_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("g2p_livestock_type.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )


class StagedLivestockRecordStatus(BaseORMModel):
    __tablename__ = "g2p_livestock_record_status"

    code: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    is_live_master_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class StagedLivestockRegistryEntry(BaseORMModel):
    __tablename__ = "g2p_livestock_registry_entry"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    species_code: Mapped[str] = mapped_column(
        String,
        ForeignKey("g2p_livestock_type.species_code"),
        nullable=False,
        index=True,
    )
    breed_name: Mapped[str] = mapped_column(String, nullable=False)
    breed_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("g2p_livestock_breed.id"),
        nullable=True,
        index=True,
    )
    gender_code: Mapped[str] = mapped_column(String, ForeignKey("g2p_livestock_gender.code"), nullable=False)
    location_type_code: Mapped[str] = mapped_column(
        String, ForeignKey("g2p_livestock_location_type.code"), nullable=False
    )
    body_condition_code: Mapped[str] = mapped_column(
        String, ForeignKey("g2p_livestock_body_condition.code"), nullable=False
    )
    production_type_code: Mapped[str] = mapped_column(
        String, ForeignKey("g2p_livestock_production_type.code"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String, ForeignKey("g2p_livestock_record_status.code"), nullable=False, index=True
    )
    created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StagedRegion(BaseORMModel):
    __tablename__ = "g2p_region"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    display_name_amh: Mapped[str | None] = mapped_column(String, nullable=True)
    admin0_name: Mapped[str | None] = mapped_column(String, nullable=True)
    admin0_pcod: Mapped[str | None] = mapped_column(String, nullable=True)
    admin1_pcod: Mapped[str | None] = mapped_column(String, nullable=True)
    admin1_refn: Mapped[str | None] = mapped_column(String, nullable=True)


class StagedZone(BaseORMModel):
    __tablename__ = "g2p_zone"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    display_name_amh: Mapped[str | None] = mapped_column(String, nullable=True)
    admin2_pcod: Mapped[str | None] = mapped_column(String, nullable=True)
    admin2_refn: Mapped[str | None] = mapped_column(String, nullable=True)
    admin2_altn: Mapped[str | None] = mapped_column(String, nullable=True)
    admin2_al_1: Mapped[str | None] = mapped_column(String, nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column("lat", Numeric(15, 11), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column("long", Numeric(15, 11), nullable=True)
    shape_length: Mapped[Decimal | None] = mapped_column(Numeric(20, 12), nullable=True)
    shape_area: Mapped[Decimal | None] = mapped_column(Numeric(20, 15), nullable=True)
    region: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("g2p_region.id"),
        nullable=False,
        index=True,
    )


class StagedWoreda(BaseORMModel):
    __tablename__ = "g2p_woreda"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    display_name_amh: Mapped[str | None] = mapped_column(String, nullable=True)
    admin3_pcod: Mapped[str | None] = mapped_column(String, nullable=True)
    admin3_refn: Mapped[str | None] = mapped_column(String, nullable=True)
    admin3_altn: Mapped[str | None] = mapped_column(String, nullable=True)
    admin3_al_1: Mapped[str | None] = mapped_column(String, nullable=True)
    shape_length: Mapped[Decimal | None] = mapped_column(Numeric(20, 12), nullable=True)
    shape_area: Mapped[Decimal | None] = mapped_column(Numeric(20, 15), nullable=True)
    zone: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("g2p_zone.id"),
        nullable=True,
        index=True,
    )


class StagedKebele(BaseORMModel):
    __tablename__ = "g2p_kebele"

    code: Mapped[str] = mapped_column(String, primary_key=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    display_name_amh: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_code: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    source_region_code: Mapped[str | None] = mapped_column(String, nullable=True)
    source_zone_code: Mapped[str | None] = mapped_column(String, nullable=True)
    source_woreda_code: Mapped[str | None] = mapped_column(String, nullable=True)
    matched_woreda_code: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("g2p_woreda.code"),
        nullable=True,
        index=True,
    )
    match_method: Mapped[str] = mapped_column(String, nullable=False)
    match_status: Mapped[str] = mapped_column(String, nullable=False)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class StagedSeedCatalogue(BaseORMModel):
    __tablename__ = "g2p_seed_catalog"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)


class StagedSeedDemandSummary(BaseORMModel):
    __tablename__ = "g2p_seed_demand_summary"
    __table_args__ = (
        UniqueConstraint(
            "budget_year",
            name="uq_g2p_seed_demand_summary_year",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    budget_year: Mapped[int] = mapped_column(Integer, nullable=False)
    total_entries: Mapped[int] = mapped_column(Integer, nullable=False)
    total_quantity_demanded: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    average_quantity_per_entry: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    total_estimated_land_ha: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    average_estimated_land_ha: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)


class StagedSeedDemandTrend(BaseORMModel):
    __tablename__ = "g2p_seed_demand_trend"
    __table_args__ = (
        UniqueConstraint(
            "budget_year",
            "seed_class",
            name="uq_g2p_seed_demand_trend_year_class",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    budget_year: Mapped[int] = mapped_column(Integer, nullable=False)
    seed_class: Mapped[str] = mapped_column(String, nullable=False)
    quantity_demanded: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)


class StagedSeedDemandByCrop(BaseORMModel):
    __tablename__ = "g2p_seed_demand_trend_by_crop"
    __table_args__ = (
        UniqueConstraint(
            "crop_id",
            "budget_year",
            "seed_class",
            name="uq_g2p_seed_demand_crop_year_class",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    crop_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    crop_name: Mapped[str] = mapped_column(String, nullable=False)
    budget_year: Mapped[int] = mapped_column(Integer, nullable=False)
    seed_class: Mapped[str] = mapped_column(String, nullable=False)
    quantity_demanded: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
