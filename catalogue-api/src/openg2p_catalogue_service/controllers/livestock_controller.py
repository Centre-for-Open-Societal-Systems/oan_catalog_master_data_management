from typing import Literal

from fastapi import Header, HTTPException, Query, Response
from iam_core.user_auth.decorators import require_permissions
from openg2p_fastapi_common.controller import BaseController

from ..helpers import apply_release_cache_headers, normalized_pagination
from ..schemas import (
    LivestockBreedListResponse,
    LivestockReferenceDataResponse,
    LivestockRegistryEntryListResponse,
    LivestockRegistryValidationResponse,
    LivestockSpeciesListResponse,
)
from ..security import CATALOGUE_READ_PERMISSION
from ..services import LivestockReferenceNotFoundError, LivestockService


class LivestockController(BaseController):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.router.tags += ["Livestock Catalogue"]
        self.router.prefix = "/v1/livestock"
        self.router.responses[304] = {"description": "Release has not changed"}
        self.livestock_service = LivestockService.get_component()
        self.router.add_api_route(
            "/species",
            self.get_species,
            response_model=LivestockSpeciesListResponse,
            methods=["GET"],
            summary="List livestock species",
        )
        self.router.add_api_route(
            "/breeds",
            self.get_breeds,
            response_model=LivestockBreedListResponse,
            methods=["GET"],
            summary="List and filter livestock breeds",
        )
        self.router.add_api_route(
            "/reference-data",
            self.get_reference_data,
            response_model=LivestockReferenceDataResponse,
            methods=["GET"],
            summary="Get complete livestock reference data",
        )
        self.router.add_api_route(
            "/registry-entries",
            self.get_registry_entries,
            response_model=LivestockRegistryEntryListResponse,
            methods=["GET"],
            summary="List the release-scoped ET-LITS registry snapshot",
        )
        self.router.add_api_route(
            "/registry-validation",
            self.get_registry_validation,
            response_model=LivestockRegistryValidationResponse,
            methods=["GET"],
            summary="List ET-LITS registry validation results",
        )

    @staticmethod
    def _cached(response: Response, result, if_none_match: str | None):
        return (
            apply_release_cache_headers(
                response,
                result.release.checksum,
                result.release.version,
                if_none_match,
            )
            or result
        )

    @require_permissions(CATALOGUE_READ_PERMISSION)
    async def get_species(
        self,
        response: Response,
        country_code: str | None = None,
        release_version: str | None = None,
        search: str | None = Query(default=None, min_length=1, max_length=200),
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=100, ge=1, le=1000),
        if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    ):
        page, page_size = normalized_pagination(page, page_size)
        try:
            result = await self.livestock_service.get_species(
                country_code, release_version, search, page, page_size
            )
            return self._cached(response, result, if_none_match)
        except LivestockReferenceNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @require_permissions(CATALOGUE_READ_PERMISSION)
    async def get_breeds(
        self,
        response: Response,
        country_code: str | None = None,
        release_version: str | None = None,
        species_code: str | None = Query(default=None, min_length=1, max_length=100),
        breed_type: Literal["Indigenous", "Exotic", "Cross"] | None = None,
        in_national_standard: bool | None = None,
        in_etlits_registry: bool | None = None,
        search: str | None = Query(default=None, min_length=1, max_length=200),
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=100, ge=1, le=1000),
        if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    ):
        page, page_size = normalized_pagination(page, page_size)
        try:
            result = await self.livestock_service.get_breeds(
                country_code=country_code,
                release_version=release_version,
                species_code=species_code,
                breed_type=breed_type,
                in_national_standard=in_national_standard,
                in_etlits_registry=in_etlits_registry,
                search=search,
                page=page,
                page_size=page_size,
            )
            return self._cached(response, result, if_none_match)
        except LivestockReferenceNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @require_permissions(CATALOGUE_READ_PERMISSION)
    async def get_reference_data(
        self,
        response: Response,
        country_code: str | None = None,
        release_version: str | None = None,
        if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    ):
        try:
            result = await self.livestock_service.get_reference_data(country_code, release_version)
            return self._cached(response, result, if_none_match)
        except LivestockReferenceNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @require_permissions(CATALOGUE_READ_PERMISSION)
    async def get_registry_entries(
        self,
        response: Response,
        country_code: str | None = None,
        release_version: str | None = None,
        species_code: str | None = Query(default=None, min_length=1, max_length=100),
        status: str | None = Query(default=None, min_length=1, max_length=100),
        breed_id: int | None = Query(default=None, ge=1),
        search: str | None = Query(default=None, min_length=1, max_length=200),
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=100, ge=1, le=1000),
        if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    ):
        page, page_size = normalized_pagination(page, page_size)
        try:
            result = await self.livestock_service.get_registry_entries(
                country_code=country_code,
                release_version=release_version,
                species_code=species_code,
                status=status,
                breed_id=breed_id,
                search=search,
                page=page,
                page_size=page_size,
            )
            return self._cached(response, result, if_none_match)
        except LivestockReferenceNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @require_permissions(CATALOGUE_READ_PERMISSION)
    async def get_registry_validation(
        self,
        response: Response,
        country_code: str | None = None,
        release_version: str | None = None,
        species_code: str | None = Query(default=None, min_length=1, max_length=100),
        status: str | None = Query(default=None, min_length=1, max_length=100),
        has_issues: bool | None = None,
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=100, ge=1, le=1000),
        if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    ):
        page, page_size = normalized_pagination(page, page_size)
        try:
            result = await self.livestock_service.get_registry_validation(
                country_code=country_code,
                release_version=release_version,
                species_code=species_code,
                status=status,
                has_issues=has_issues,
                page=page,
                page_size=page_size,
            )
            return self._cached(response, result, if_none_match)
        except LivestockReferenceNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
