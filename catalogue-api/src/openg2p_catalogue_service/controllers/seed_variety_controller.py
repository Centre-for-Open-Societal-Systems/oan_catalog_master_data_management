from typing import Literal

from fastapi import Header, HTTPException, Query, Response
from iam_core.user_auth.decorators import require_permissions
from openg2p_fastapi_common.controller import BaseController

from ..helpers import apply_release_cache_headers, normalized_pagination
from ..schemas import SeedVarietyDetailResponse, SeedVarietyListResponse
from ..security import CATALOGUE_READ_PERMISSION
from ..services import SeedVarietyNotFoundError, SeedVarietyService


class SeedVarietyController(BaseController):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.router.tags += ["Seed Varieties"]
        self.router.prefix = "/v1"
        self.router.responses[304] = {"description": "Release has not changed"}
        self.seed_variety_service = SeedVarietyService.get_component()
        self.router.add_api_route(
            "/seed-varieties",
            self.get_seed_varieties,
            response_model=SeedVarietyListResponse,
            methods=["GET"],
        )
        self.router.add_api_route(
            "/seed-varieties/{seed_variety_code}",
            self.get_seed_variety,
            response_model=SeedVarietyDetailResponse,
            methods=["GET"],
        )

    @require_permissions(CATALOGUE_READ_PERMISSION)
    async def get_seed_varieties(
        self,
        response: Response,
        country_code: str | None = None,
        release_version: str | None = None,
        seed_crop_code: str | None = Query(default=None, min_length=1, max_length=200),
        crop_variety_code: str | None = Query(default=None, min_length=1, max_length=200),
        crop_type_code: str | None = Query(default=None, min_length=1, max_length=200),
        category_code: str | None = Query(default=None, min_length=1, max_length=200),
        match_status: Literal["MATCHED", "UNRESOLVED", "CONFLICT"] | None = None,
        release_year: int | None = Query(default=None, ge=1800, le=2200),
        search: str | None = Query(default=None, min_length=1, max_length=200),
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=100, ge=1, le=1000),
        if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    ):
        page, page_size = normalized_pagination(page, page_size)
        try:
            result = await self.seed_variety_service.get_seed_varieties(
                country_code=country_code,
                release_version=release_version,
                seed_crop_code=seed_crop_code,
                crop_variety_code=crop_variety_code,
                crop_type_code=crop_type_code,
                category_code=category_code,
                match_status=match_status,
                release_year=release_year,
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
                or result
            )
        except SeedVarietyNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @require_permissions(CATALOGUE_READ_PERMISSION)
    async def get_seed_variety(
        self,
        seed_variety_code: str,
        response: Response,
        country_code: str | None = None,
        release_version: str | None = None,
        if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    ):
        try:
            result = await self.seed_variety_service.get_seed_variety_detail(
                seed_variety_code,
                country_code,
                release_version,
            )
            return (
                apply_release_cache_headers(
                    response,
                    result.release.checksum,
                    result.release.version,
                    if_none_match,
                )
                or result
            )
        except SeedVarietyNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
