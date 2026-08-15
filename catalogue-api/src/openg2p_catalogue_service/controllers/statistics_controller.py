from fastapi import Header, HTTPException, Query, Response
from iam_core.user_auth.decorators import require_permissions
from openg2p_fastapi_common.controller import BaseController

from ..helpers import apply_release_cache_headers, normalized_pagination
from ..schemas import (
    LivestockPopulationResponse,
    SeedDemandByCropResponse,
    SeedDemandSummaryResponse,
    SeedDemandTrendResponse,
)
from ..security import STATISTICS_READ_PERMISSION
from ..services import ResourceNotFoundError, StatisticsService


class StatisticsController(BaseController):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.router.tags += ["Agriculture statistics"]
        self.router.prefix = "/v1/statistics"
        self.router.responses[304] = {"description": "Release has not changed"}
        self.statistics_service = StatisticsService.get_component()

        self.router.add_api_route(
            "/livestock-population",
            self.get_livestock_population,
            response_model=LivestockPopulationResponse,
            methods=["GET"],
        )
        self.router.add_api_route(
            "/seed-demand/summary",
            self.get_seed_demand_summary,
            response_model=SeedDemandSummaryResponse,
            methods=["GET"],
        )
        self.router.add_api_route(
            "/seed-demand/trends",
            self.get_seed_demand_trends,
            response_model=SeedDemandTrendResponse,
            methods=["GET"],
        )
        self.router.add_api_route(
            "/seed-demand/by-crop",
            self.get_seed_demand_by_crop,
            response_model=SeedDemandByCropResponse,
            methods=["GET"],
        )

    @staticmethod
    def _cached(response: Response, result, if_none_match: str | None):
        return (
            apply_release_cache_headers(
                response, result.release.checksum, result.release.version, if_none_match
            )
            or result
        )

    @require_permissions(STATISTICS_READ_PERMISSION)
    async def get_livestock_population(
        self,
        response: Response,
        country_code: str | None = None,
        release_version: str | None = None,
        species_code: str | None = None,
        census_year: int | None = None,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=100, ge=1, le=1000),
        if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    ):
        page, page_size = normalized_pagination(page, page_size)
        try:
            result = await self.statistics_service.get_livestock_population(
                country_code,
                release_version,
                species_code,
                census_year,
                page,
                page_size,
            )
            return self._cached(response, result, if_none_match)
        except ResourceNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @require_permissions(STATISTICS_READ_PERMISSION)
    async def get_seed_demand_summary(
        self,
        response: Response,
        country_code: str | None = None,
        release_version: str | None = None,
        budget_year: int | None = None,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=100, ge=1, le=1000),
        if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    ):
        page, page_size = normalized_pagination(page, page_size)
        try:
            result = await self.statistics_service.get_seed_demand_summary(
                country_code,
                release_version,
                budget_year,
                page,
                page_size,
            )
            return self._cached(response, result, if_none_match)
        except ResourceNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @require_permissions(STATISTICS_READ_PERMISSION)
    async def get_seed_demand_trends(
        self,
        response: Response,
        country_code: str | None = None,
        release_version: str | None = None,
        budget_year: int | None = None,
        seed_class: str | None = None,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=100, ge=1, le=1000),
        if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    ):
        page, page_size = normalized_pagination(page, page_size)
        try:
            result = await self.statistics_service.get_seed_demand_trends(
                country_code,
                release_version,
                budget_year,
                seed_class,
                page,
                page_size,
            )
            return self._cached(response, result, if_none_match)
        except ResourceNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @require_permissions(STATISTICS_READ_PERMISSION)
    async def get_seed_demand_by_crop(
        self,
        response: Response,
        country_code: str | None = None,
        release_version: str | None = None,
        crop_code: str | None = None,
        budget_year: int | None = None,
        seed_class: str | None = None,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=100, ge=1, le=1000),
        if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    ):
        page, page_size = normalized_pagination(page, page_size)
        try:
            result = await self.statistics_service.get_seed_demand_by_crop(
                country_code,
                release_version,
                crop_code,
                budget_year,
                seed_class,
                page,
                page_size,
            )
            return self._cached(response, result, if_none_match)
        except ResourceNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
