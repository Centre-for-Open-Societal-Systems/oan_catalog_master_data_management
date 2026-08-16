from fastapi import Header, HTTPException, Response
from iam_core.user_auth.decorators import require_permissions
from openg2p_fastapi_common.controller import BaseController

from ..helpers import apply_release_cache_headers
from ..schemas import CropVarietyDetailResponse
from ..security import CATALOGUE_READ_PERMISSION
from ..services import CropTaxonomyService, CropVarietyNotFoundError


class CropTaxonomyController(BaseController):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.router.tags += ["Crop Taxonomy"]
        self.router.prefix = "/v1"
        self.router.responses[304] = {"description": "Release has not changed"}
        self.crop_taxonomy_service = CropTaxonomyService.get_component()
        self.router.add_api_route(
            "/crop-varieties/{variety_code}",
            self.get_crop_variety,
            response_model=CropVarietyDetailResponse,
            methods=["GET"],
        )

    @require_permissions(CATALOGUE_READ_PERMISSION)
    async def get_crop_variety(
        self,
        variety_code: str,
        response: Response,
        country_code: str | None = None,
        release_version: str | None = None,
        if_none_match: str | None = Header(default=None, alias="If-None-Match"),
    ):
        try:
            result = await self.crop_taxonomy_service.get_variety_detail(
                variety_code,
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
        except CropVarietyNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
