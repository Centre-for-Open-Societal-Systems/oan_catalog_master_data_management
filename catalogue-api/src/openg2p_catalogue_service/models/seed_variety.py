"""Ethio-Seed source records and release-scoped seed-variety details."""

from datetime import date

from openg2p_fastapi_common.models import BaseORMModel
from sqlalchemy import (
    CheckConstraint,
    Computed,
    Date,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

MATCH_STATE_CONSTRAINT = """
    (match_status = 'MATCHED'
     AND {matched_column} IS NOT NULL
     AND match_method IN (
         'EXACT_SOURCE_ID', 'EXACT_NAME_AND_CROP',
         'REVIEWED_ALIAS', 'REVIEWED_MANUAL'
     ))
    OR
    (match_status = 'UNRESOLVED'
     AND {matched_column} IS NULL
     AND match_method = 'UNRESOLVED')
    OR
    (match_status = 'CONFLICT'
     AND {matched_column} IS NULL
     AND match_method = 'CONFLICT')
"""


class StagedSeedVarietySourceRecord(BaseORMModel):
    __tablename__ = "g2p_seed_variety_source_record"
    __table_args__ = (
        CheckConstraint("source_variety_id > 0", name="ck_g2p_seed_variety_source_id"),
        CheckConstraint(
            "release_year IS NULL OR release_year BETWEEN 1800 AND 2200",
            name="ck_g2p_seed_variety_release_year",
        ),
        CheckConstraint(
            "release_year IS NULL OR release_date IS NULL OR EXTRACT(YEAR FROM release_date) = release_year",
            name="ck_g2p_seed_variety_release_date_year",
        ),
        CheckConstraint(
            "source_classification IS NULL OR source_classification IN ('Domestic', 'Imported')",
            name="ck_g2p_seed_variety_source_classification",
        ),
        CheckConstraint(
            MATCH_STATE_CONSTRAINT.format(matched_column="matched_variety_code"),
            name="ck_g2p_seed_variety_match_state",
        ),
        Index("ix_g2p_seed_variety_match", "match_status", "matched_variety_code"),
    )

    source_variety_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seed_crop_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("g2p_seed_catalog.id"),
        nullable=False,
        index=True,
    )
    crop_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("g2p_crop.id"),
        Computed("seed_crop_id"),
        nullable=False,
        index=True,
    )
    crop_name_raw: Mapped[str] = mapped_column(Text, nullable=False)
    common_name_raw: Mapped[str] = mapped_column(Text, nullable=False)
    category_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    release_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True, index=True)
    release_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    release_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    maintainer: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_classification: Mapped[str | None] = mapped_column(String, nullable=True)
    details_url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    matched_variety_code: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("g2p_crop_variety.variety_code"),
        nullable=True,
    )
    match_method: Mapped[str] = mapped_column(String, nullable=False, default="UNRESOLVED")
    match_status: Mapped[str] = mapped_column(String, nullable=False, default="UNRESOLVED")
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class SeedVarietySourceRecord(BaseORMModel):
    __tablename__ = "seed_variety_source_records"
    __table_args__ = (
        UniqueConstraint(
            "release_id",
            "source_variety_id",
            name="uq_seed_variety_source_release_id",
        ),
        UniqueConstraint(
            "release_id",
            "details_url",
            name="uq_seed_variety_source_release_url",
        ),
        CheckConstraint("source_variety_id > 0", name="ck_seed_variety_source_id"),
        CheckConstraint(
            "release_year IS NULL OR release_year BETWEEN 1800 AND 2200",
            name="ck_seed_variety_source_release_year",
        ),
        CheckConstraint(
            "release_year IS NULL OR release_date IS NULL OR EXTRACT(YEAR FROM release_date) = release_year",
            name="ck_seed_variety_source_release_date_year",
        ),
        CheckConstraint(
            "source_classification IS NULL OR source_classification IN ('Domestic', 'Imported')",
            name="ck_seed_variety_source_classification",
        ),
        CheckConstraint(
            MATCH_STATE_CONSTRAINT.format(matched_column="matched_crop_variety_value_id"),
            name="ck_seed_variety_source_match_state",
        ),
        Index("ix_seed_variety_source_release_crop", "release_id", "seed_crop_value_id"),
        Index("ix_seed_variety_source_release_consolidated_crop", "release_id", "crop_value_id"),
        Index(
            "ix_seed_variety_source_release_consolidated_variety",
            "release_id",
            "consolidated_crop_variety_value_id",
        ),
        Index(
            "ix_seed_variety_source_release_value",
            "release_id",
            "seed_variety_value_id",
        ),
        Index(
            "ix_seed_variety_source_release_match",
            "release_id",
            "match_status",
            "matched_crop_variety_value_id",
        ),
        Index("ix_seed_variety_source_release_year", "release_id", "release_year"),
    )

    seed_variety_source_record_id: Mapped[str] = mapped_column(String, primary_key=True)
    release_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("catalogue_releases.release_id", ondelete="CASCADE"),
        nullable=False,
    )
    seed_variety_value_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("catalogue_values.catalogue_value_id", ondelete="CASCADE"),
        nullable=False,
    )
    seed_crop_value_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("catalogue_values.catalogue_value_id", ondelete="CASCADE"),
        nullable=False,
    )
    crop_value_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("catalogue_values.catalogue_value_id", ondelete="CASCADE"),
        nullable=True,
    )
    consolidated_crop_variety_value_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("catalogue_values.catalogue_value_id", ondelete="CASCADE"),
        nullable=True,
    )
    matched_crop_variety_value_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("catalogue_values.catalogue_value_id", ondelete="CASCADE"),
        nullable=True,
    )
    source_variety_id: Mapped[int] = mapped_column(Integer, nullable=False)
    crop_name_raw: Mapped[str] = mapped_column(Text, nullable=False)
    common_name_raw: Mapped[str] = mapped_column(Text, nullable=False)
    category_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    release_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    release_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    release_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    maintainer: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_classification: Mapped[str | None] = mapped_column(String, nullable=True)
    details_url: Mapped[str] = mapped_column(Text, nullable=False)
    match_method: Mapped[str] = mapped_column(String, nullable=False)
    match_status: Mapped[str] = mapped_column(String, nullable=False)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
