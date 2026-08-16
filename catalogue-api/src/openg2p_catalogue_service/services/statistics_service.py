from openg2p_fastapi_common.service import BaseService
from sqlalchemy import func, select

from ..engine import get_session_maker
from ..models import (
    LivestockPopulationStatistic,
    SeedDemandByCropStatistic,
    SeedDemandSummaryStatistic,
    SeedDemandTrendStatistic,
)
from ..schemas import (
    LivestockPopulationData,
    LivestockPopulationResponse,
    SeedDemandByCropData,
    SeedDemandByCropResponse,
    SeedDemandSummaryData,
    SeedDemandSummaryResponse,
    SeedDemandTrendData,
    SeedDemandTrendResponse,
)
from .release_service import release_data, resolve_release


class StatisticsService(BaseService):
    async def _page(self, session, statement, model, page: int, page_size: int):
        total = (await session.execute(select(func.count()).select_from(statement.subquery()))).scalar_one()
        rows = (
            (
                await session.execute(
                    statement.order_by(*model.__table__.primary_key.columns)
                    .limit(page_size)
                    .offset((page - 1) * page_size)
                )
            )
            .scalars()
            .all()
        )
        return rows, total

    async def get_livestock_population(
        self,
        country_code: str | None = None,
        release_version: str | None = None,
        species_code: str | None = None,
        census_year: int | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> LivestockPopulationResponse:
        async with get_session_maker()() as session:
            release = await resolve_release(session, country_code, release_version)
            stmt = select(LivestockPopulationStatistic).where(
                LivestockPopulationStatistic.release_id == release.release_id
            )
            if species_code is not None:
                stmt = stmt.where(LivestockPopulationStatistic.species_code == species_code)
            if census_year is not None:
                stmt = stmt.where(LivestockPopulationStatistic.census_year == census_year)
            rows, total = await self._page(
                session,
                stmt.order_by(
                    LivestockPopulationStatistic.species_code,
                    LivestockPopulationStatistic.census_year,
                ),
                LivestockPopulationStatistic,
                page,
                page_size,
            )
        return LivestockPopulationResponse(
            release=release_data(release),
            statistics=[
                LivestockPopulationData(
                    species_code=row.species_code,
                    census_year=row.census_year,
                    population_total=row.population_total,
                    source_record_count=row.source_record_count,
                    source=row.source,
                )
                for row in rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_seed_demand_summary(
        self,
        country_code: str | None = None,
        release_version: str | None = None,
        budget_year: int | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> SeedDemandSummaryResponse:
        async with get_session_maker()() as session:
            release = await resolve_release(session, country_code, release_version)
            stmt = select(SeedDemandSummaryStatistic).where(
                SeedDemandSummaryStatistic.release_id == release.release_id
            )
            if budget_year is not None:
                stmt = stmt.where(SeedDemandSummaryStatistic.budget_year == budget_year)
            rows, total = await self._page(
                session,
                stmt.order_by(SeedDemandSummaryStatistic.budget_year),
                SeedDemandSummaryStatistic,
                page,
                page_size,
            )
        return SeedDemandSummaryResponse(
            release=release_data(release),
            statistics=[
                SeedDemandSummaryData(
                    budget_year=row.budget_year,
                    total_entries=row.total_entries,
                    total_quantity_demanded=row.total_quantity_demanded,
                    average_quantity_per_entry=row.average_quantity_per_entry,
                    total_estimated_land_ha=row.total_estimated_land_ha,
                    average_estimated_land_ha=row.average_estimated_land_ha,
                )
                for row in rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_seed_demand_trends(
        self,
        country_code: str | None = None,
        release_version: str | None = None,
        budget_year: int | None = None,
        seed_class: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> SeedDemandTrendResponse:
        async with get_session_maker()() as session:
            release = await resolve_release(session, country_code, release_version)
            stmt = select(SeedDemandTrendStatistic).where(
                SeedDemandTrendStatistic.release_id == release.release_id
            )
            if budget_year is not None:
                stmt = stmt.where(SeedDemandTrendStatistic.budget_year == budget_year)
            if seed_class is not None:
                stmt = stmt.where(SeedDemandTrendStatistic.seed_class == seed_class)
            rows, total = await self._page(
                session,
                stmt.order_by(
                    SeedDemandTrendStatistic.budget_year,
                    SeedDemandTrendStatistic.seed_class,
                ),
                SeedDemandTrendStatistic,
                page,
                page_size,
            )
        return SeedDemandTrendResponse(
            release=release_data(release),
            statistics=[
                SeedDemandTrendData(
                    budget_year=row.budget_year,
                    seed_class=row.seed_class,
                    quantity_demanded=row.quantity_demanded,
                )
                for row in rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_seed_demand_by_crop(
        self,
        country_code: str | None = None,
        release_version: str | None = None,
        crop_code: str | None = None,
        budget_year: int | None = None,
        seed_class: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> SeedDemandByCropResponse:
        async with get_session_maker()() as session:
            release = await resolve_release(session, country_code, release_version)
            stmt = select(SeedDemandByCropStatistic).where(
                SeedDemandByCropStatistic.release_id == release.release_id
            )
            if crop_code is not None:
                stmt = stmt.where(SeedDemandByCropStatistic.crop_code == crop_code)
            if budget_year is not None:
                stmt = stmt.where(SeedDemandByCropStatistic.budget_year == budget_year)
            if seed_class is not None:
                stmt = stmt.where(SeedDemandByCropStatistic.seed_class == seed_class)
            rows, total = await self._page(
                session,
                stmt.order_by(
                    SeedDemandByCropStatistic.crop_code,
                    SeedDemandByCropStatistic.budget_year,
                    SeedDemandByCropStatistic.seed_class,
                ),
                SeedDemandByCropStatistic,
                page,
                page_size,
            )
        return SeedDemandByCropResponse(
            release=release_data(release),
            statistics=[
                SeedDemandByCropData(
                    crop_code=row.crop_code,
                    crop_name=row.crop_name,
                    budget_year=row.budget_year,
                    seed_class=row.seed_class,
                    quantity_demanded=row.quantity_demanded,
                )
                for row in rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )
