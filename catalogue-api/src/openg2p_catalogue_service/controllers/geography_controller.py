from fastapi import Header, HTTPException, Query, Response
from iam_core.user_auth.decorators import require_permissions
from openg2p_fastapi_common.controller import BaseController

from ..helpers import apply_release_cache_headers, normalized_pagination
from ..schemas import GeographyLevelsResponse, GeographyUnitResponse, GeographyUnitsResponse
from ..security import GEOGRAPHY_READ_PERMISSION
from ..services import GeographyService, ResourceNotFoundError


class GeographyController(BaseController):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.router.tags += ["Geography"]
        self.router.prefix = "/v1/geography"
        self.router.responses[304] = {"description": "Release has not changed"}
        self.geography_service = GeographyService.get_component()

        self.router.add_api_route(
            "/levels", self.get_levels, response_model=GeographyLevelsResponse, methods=["GET"]
        )
        self.router.add_api_route(
            "/units", self.get_units, response_model=GeographyUnitsResponse, methods=["GET"]
        )
        self.router.add_api_route(
            "/units/{unit_code}",
            self.get_unit,
            response_model=GeographyUnitResponse,
            methods=["GET"],
        )

    @require_permissions(GEOGRAPHY_READ_PERMISSION)
    async def get_levels(
        self,
        response: Response,
        country_code: str | None = None,
        release_version: str | None = None,
        if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    ):
        try:
            result = await self.geography_service.get_levels(country_code, release_version)
            return (
                apply_release_cache_headers(
                    response, result.release.checksum, result.release.version, if_none_match
                )
                or result
            )
        except ResourceNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @require_permissions(GEOGRAPHY_READ_PERMISSION)
    async def get_units(
        self,
        response: Response,
        country_code: str | None = None,
        release_version: str | None = None,
        level_code: str | None = None,
        parent_code: str | None = None,
        status: str | None = None,
        search: str | None = Query(default=None, min_length=1, max_length=200),
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=100, ge=1, le=1000),
        if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    ):
        page, page_size = normalized_pagination(page, page_size)
        try:
            result = await self.geography_service.get_units(
                country_code=country_code,
                release_version=release_version,
                level_code=level_code,
                parent_code=parent_code,
                status=status,
                search=search,
                page=page,
                page_size=page_size,
            )
            return (
                apply_release_cache_headers(
                    response, result.release.checksum, result.release.version, if_none_match
                )
                or result
            )
        except ResourceNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @require_permissions(GEOGRAPHY_READ_PERMISSION)
    async def get_unit(
        self,
        unit_code: str,
        response: Response,
        country_code: str | None = None,
        release_version: str | None = None,
        level_code: str | None = None,
        if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    ):
        try:
            release, unit = await self.geography_service.get_unit(
                unit_code, country_code, release_version, level_code
            )
            cached = apply_release_cache_headers(response, release.checksum, release.version, if_none_match)
            return cached or GeographyUnitResponse(release=release, unit=unit)
        except ResourceNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
