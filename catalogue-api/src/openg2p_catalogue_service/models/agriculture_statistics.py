import uuid
from decimal import Decimal

from openg2p_fastapi_common.models import BaseORMModel
from sqlalchemy import BigInteger, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


class LivestockPopulationStatistic(BaseORMModel):
    __tablename__ = "livestock_population_statistics"
    __table_args__ = (
        UniqueConstraint(
            "release_id",
            "species_code",
            "census_year",
            name="uq_livestock_stat_release_species_year",
        ),
    )

    statistic_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    release_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("catalogue_releases.release_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    species_code: Mapped[str] = mapped_column(String, nullable=False, index=True)
    census_year: Mapped[int] = mapped_column(Integer, nullable=False)
    population_total: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_record_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str | None] = mapped_column(String, nullable=True)


class SeedDemandSummaryStatistic(BaseORMModel):
    __tablename__ = "seed_demand_summary_statistics"
    __table_args__ = (UniqueConstraint("release_id", "budget_year", name="uq_seed_summary_release_year"),)

    statistic_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    release_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("catalogue_releases.release_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    budget_year: Mapped[int] = mapped_column(Integer, nullable=False)
    total_entries: Mapped[int] = mapped_column(Integer, nullable=False)
    total_quantity_demanded: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    average_quantity_per_entry: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    total_estimated_land_ha: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    average_estimated_land_ha: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)


class SeedDemandTrendStatistic(BaseORMModel):
    __tablename__ = "seed_demand_trend_statistics"
    __table_args__ = (
        UniqueConstraint(
            "release_id",
            "budget_year",
            "seed_class",
            name="uq_seed_trend_release_year_class",
        ),
    )

    statistic_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    release_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("catalogue_releases.release_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    budget_year: Mapped[int] = mapped_column(Integer, nullable=False)
    seed_class: Mapped[str] = mapped_column(String, nullable=False)
    quantity_demanded: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)


class SeedDemandByCropStatistic(BaseORMModel):
    __tablename__ = "seed_demand_by_crop_statistics"
    __table_args__ = (
        UniqueConstraint(
            "release_id",
            "crop_code",
            "budget_year",
            "seed_class",
            name="uq_seed_crop_stat_release_crop_year_class",
        ),
    )

    statistic_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    release_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("catalogue_releases.release_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    crop_code: Mapped[str] = mapped_column(String, nullable=False, index=True)
    crop_name: Mapped[str] = mapped_column(String, nullable=False)
    budget_year: Mapped[int] = mapped_column(Integer, nullable=False)
    seed_class: Mapped[str] = mapped_column(String, nullable=False)
    quantity_demanded: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
