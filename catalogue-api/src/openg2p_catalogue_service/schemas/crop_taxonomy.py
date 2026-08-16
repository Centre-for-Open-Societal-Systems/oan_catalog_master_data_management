from decimal import Decimal

from pydantic import BaseModel, Field

from .catalogue import ReleaseData


class CropTaxonomyReferenceData(BaseModel):
    code: str
    display_name: str
    display_name_i18n: dict | None = None


class CropVarietyCharacteristicData(BaseModel):
    code: str
    display_name: str
    value_type: str
    raw_value: str
    value_text: str | None = None
    value_numeric: Decimal | None = None
    value_boolean: bool | None = None
    value_min: Decimal | None = None
    value_max: Decimal | None = None
    unit_code: str | None = None


class CropVarietySourceRecordData(BaseModel):
    source_record_code: str
    source_row_number: int | None = None
    centre: str
    release_year_raw: str
    release_year: int | None = None
    source_url: str | None = None
    altitude_min_m: Decimal | None = None
    altitude_max_m: Decimal | None = None
    rainfall_min_mm: Decimal | None = None
    rainfall_max_mm: Decimal | None = None
    days_to_maturity_min: int | None = None
    days_to_maturity_max: int | None = None
    yield_research_min_qt_ha: Decimal | None = None
    yield_research_max_qt_ha: Decimal | None = None
    yield_farmer_min_qt_ha: Decimal | None = None
    yield_farmer_max_qt_ha: Decimal | None = None
    seed_rate_kg_ha: Decimal | None = None
    adaptation_area: str | None = None
    planting_date_text: str | None = None
    crop_pest_reaction: str | None = None
    characteristics: list[CropVarietyCharacteristicData] = Field(default_factory=list)


class CropVarietyDetailData(BaseModel):
    code: str
    display_name: str
    display_name_i18n: dict | None = None
    status: str
    crop_type: CropTaxonomyReferenceData
    category: CropTaxonomyReferenceData
    source_records: list[CropVarietySourceRecordData] = Field(default_factory=list)


class CropVarietyDetailResponse(BaseModel):
    release: ReleaseData
    variety: CropVarietyDetailData
