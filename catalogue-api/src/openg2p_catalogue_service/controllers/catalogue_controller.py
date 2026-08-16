from fastapi import Header, HTTPException, Query, Response
from iam_core.user_auth.decorators import require_permissions
from openg2p_fastapi_common.controller import BaseController

from ..helpers import apply_release_cache_headers, normalized_pagination
from ..schemas import (
    CatalogueListResponse,
    CatalogueOptionsResponse,
    CatalogueValuesResponse,
    MasterDataSnapshotResponse,
    ReleaseData,
    catalogue_options,
)
from ..security import CATALOGUE_READ_PERMISSION, SNAPSHOT_READ_PERMISSION
from ..services import CatalogueNotFoundError, CatalogueService, SnapshotService


class CatalogueController(BaseController):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.router.tags += ["Catalogue"]
        self.router.prefix = "/v1"
        self.router.responses[304] = {"description": "Release has not changed"}
        self.catalogue_service = CatalogueService.get_component()
        self.snapshot_service = SnapshotService.get_component()

        self.router.add_api_route(
            "/releases/current",
            self.get_current_release,
            response_model=ReleaseData,
            methods=["GET"],
        )
        self.router.add_api_route(
            "/catalogues",
            self.get_catalogues,
            response_model=CatalogueListResponse,
            methods=["GET"],
        )
        self.router.add_api_route(
            "/catalogues/{catalogue_code}/values",
            self.get_catalogue_values,
            response_model=CatalogueValuesResponse,
            methods=["GET"],
        )
        self.router.add_api_route(
            "/catalogue-values",
            self.get_catalogue_options,
            response_model=CatalogueOptionsResponse,
            methods=["GET"],
        )
        self.router.add_api_route(
            "/snapshots/current",
            self.get_current_snapshot,
            response_model=MasterDataSnapshotResponse,
            methods=["GET"],
        )

    @require_permissions(CATALOGUE_READ_PERMISSION)
    async def get_catalogue_options(
        self,
        response: Response,
        catalogue_code: str = Query(min_length=1, max_length=100),
        country_code: str | None = None,
        release_version: str | None = None,
        status: str | None = None,
        parent_code: str | None = None,
        relation_type: str | None = Query(default=None, min_length=1, max_length=100),
        related_catalogue_code: str | None = Query(default=None, min_length=1, max_length=100),
        related_value_code: str | None = Query(default=None, min_length=1, max_length=200),
        search: str | None = Query(default=None, min_length=1, max_length=200),
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=100, ge=1, le=1000),
        if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    ):
        page, page_size = normalized_pagination(page, page_size)
        try:
            result = await self.catalogue_service.get_values(
                catalogue_code=catalogue_code,
                country_code=country_code,
                release_version=release_version,
                status=status,
                parent_code=parent_code,
                relation_type=relation_type,
                related_catalogue_code=related_catalogue_code,
                related_value_code=related_value_code,
                search=search,
                page=page,
                page_size=page_size,
            )
            return (
                apply_release_cache_headers(
                    response,
                    result.release.checksum,
                    result.release.version,
                    if_none_match,
                )
                or catalogue_options(result)
            )
        except CatalogueNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=500, detail="Invalid catalogue option data") from error

    @require_permissions(CATALOGUE_READ_PERMISSION)
    async def get_current_release(
        self,
        response: Response,
        country_code: str | None = None,
        release_version: str | None = None,
        if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    ):
        try:
            result = await self.catalogue_service.get_current_release(country_code, release_version)
            return (
                apply_release_cache_headers(response, result.checksum, result.version, if_none_match)
                or result
            )
        except CatalogueNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @require_permissions(SNAPSHOT_READ_PERMISSION)
    async def get_current_snapshot(
        self,
        response: Response,
        country_code: str | None = None,
        release_version: str | None = None,
        if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    ):
        try:
            release = await self.catalogue_service.get_current_release(country_code, release_version)
            cached = apply_release_cache_headers(response, release.checksum, release.version, if_none_match)
            if cached is not None:
                return cached
            return await self.snapshot_service.get_snapshot(country_code, release.version)
        except CatalogueNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @require_permissions(CATALOGUE_READ_PERMISSION)
    async def get_catalogues(
        self,
        response: Response,
        country_code: str | None = None,
        domain: str | None = None,
        release_version: str | None = None,
        if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    ):
        try:
            result = await self.catalogue_service.get_catalogues(country_code, domain, release_version)
            return (
                apply_release_cache_headers(
                    response, result.release.checksum, result.release.version, if_none_match
                )
                or result
            )
        except CatalogueNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @require_permissions(CATALOGUE_READ_PERMISSION)
    async def get_catalogue_values(
        self,
        catalogue_code: str,
        response: Response,
        country_code: str | None = None,
        release_version: str | None = None,
        status: str | None = None,
        parent_code: str | None = None,
        relation_type: str | None = Query(default=None, min_length=1, max_length=100),
        related_catalogue_code: str | None = Query(default=None, min_length=1, max_length=100),
        related_value_code: str | None = Query(default=None, min_length=1, max_length=200),
        search: str | None = Query(default=None, min_length=1, max_length=200),
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=100, ge=1, le=1000),
        if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    ):
        page, page_size = normalized_pagination(page, page_size)
        try:
            result = await self.catalogue_service.get_values(
                catalogue_code=catalogue_code,
                country_code=country_code,
                release_version=release_version,
                status=status,
                parent_code=parent_code,
                relation_type=relation_type,
                related_catalogue_code=related_catalogue_code,
                related_value_code=related_value_code,
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
        except CatalogueNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
