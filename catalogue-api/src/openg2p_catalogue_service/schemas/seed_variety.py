from datetime import date

from pydantic import BaseModel

from .catalogue import ReleaseData
from .crop_taxonomy import CropTaxonomyReferenceData


class SeedVarietyData(BaseModel):
    code: str
    display_name: str
    status: str
    source_variety_id: int
    seed_crop: CropTaxonomyReferenceData
    matched_crop_variety: CropTaxonomyReferenceData | None = None
    crop_type: CropTaxonomyReferenceData | None = None
    category: CropTaxonomyReferenceData | None = None
    crop_name_raw: str
    common_name_raw: str
    category_raw: str | None = None
    release_year: int | None = None
    release_date: date | None = None
    release_raw: str | None = None
    maintainer: str | None = None
    source_classification: str | None = None
    details_url: str
    match_method: str
    match_status: str
    review_note: str | None = None


class SeedVarietyListResponse(BaseModel):
    release: ReleaseData
    varieties: list[SeedVarietyData]
    total: int
    page: int
    page_size: int


class SeedVarietyDetailResponse(BaseModel):
    release: ReleaseData
    variety: SeedVarietyData
