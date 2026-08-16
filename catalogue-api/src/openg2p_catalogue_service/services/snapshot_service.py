from openg2p_fastapi_common.service import BaseService

from ..schemas import (
    AgricultureStatisticsSnapshotData,
    GeographySnapshotData,
    MasterDataSnapshotResponse,
)
from .catalogue_service import CatalogueService
from .geography_service import GeographyService
from .statistics_service import StatisticsService


class SnapshotService(BaseService):
    async def get_snapshot(
        self,
        country_code: str | None = None,
        release_version: str | None = None,
    ) -> MasterDataSnapshotResponse:
        catalogue_service = CatalogueService.get_component()
        geography_service = GeographyService.get_component()
        statistics_service = StatisticsService.get_component()

        release = await catalogue_service.get_current_release(country_code, release_version)
        pinned_version = release.version

        catalogues = await catalogue_service.get_snapshot(country_code, pinned_version)
        levels = await geography_service.get_levels(country_code, pinned_version)
        units = await geography_service.get_units(
            country_code=country_code,
            release_version=pinned_version,
            page_size=100_000,
        )
        livestock = await statistics_service.get_livestock_population(
            country_code=country_code,
            release_version=pinned_version,
            page_size=100_000,
        )
        seed_summary = await statistics_service.get_seed_demand_summary(
            country_code=country_code,
            release_version=pinned_version,
            page_size=100_000,
        )
        seed_trends = await statistics_service.get_seed_demand_trends(
            country_code=country_code,
            release_version=pinned_version,
            page_size=100_000,
        )
        seed_by_crop = await statistics_service.get_seed_demand_by_crop(
            country_code=country_code,
            release_version=pinned_version,
            page_size=100_000,
        )

        return MasterDataSnapshotResponse(
            release=release,
            catalogues=catalogues.catalogues,
            geography=GeographySnapshotData(levels=levels.levels, units=units.units),
            agriculture_statistics=AgricultureStatisticsSnapshotData(
                livestock_population=livestock.statistics,
                seed_demand_summary=seed_summary.statistics,
                seed_demand_trends=seed_trends.statistics,
                seed_demand_by_crop=seed_by_crop.statistics,
            ),
        )
