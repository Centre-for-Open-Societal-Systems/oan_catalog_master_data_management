from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field


class Release(BaseModel):
    country_code: str
    version: str
    schema_version: str
    checksum: str
    source: str | None = None
    status: str
    activated_at: datetime | None = None


class CatalogueValueRelation(BaseModel):
    type: str
    target_catalogue_code: str
    target_code: str
    target_display_name: str


class CatalogueValue(BaseModel):
    code: str
    parent_code: str | None = None
    display_name: str
    display_name_amh: str | None = None
    display_name_i18n: Mapping[str, Any] | None = None
    semantic_roles: list[str] = Field(default_factory=list)
    sort_order: int | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    status: str
    metadata: Mapping[str, Any] = Field(default_factory=dict)
    relations: list[CatalogueValueRelation] = Field(default_factory=list)


class Catalogue(BaseModel):
    code: str
    domain: str | None = None
    display_name: str
    display_name_i18n: Mapping[str, Any] | None = None
    is_hierarchical: bool = False
    status: str
    values: list[CatalogueValue] = Field(default_factory=list)


class GeographyLevel(BaseModel):
    code: str
    display_name: str
    display_name_i18n: Mapping[str, Any] | None = None
    level_order: int
    parent_level_code: str | None = None


class GeographyUnit(BaseModel):
    code: str
    level_code: str
    parent_code: str | None = None
    display_name: str
    display_name_i18n: Mapping[str, Any] | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    status: str
    aliases: list[str] = Field(default_factory=list)
    metadata: Mapping[str, Any] = Field(default_factory=dict)


class Geography(BaseModel):
    levels: list[GeographyLevel] = Field(default_factory=list)
    units: list[GeographyUnit] = Field(default_factory=list)


class LivestockPopulation(BaseModel):
    species_code: str
    census_year: int
    population_total: int
    source_record_count: int | None = None
    source: str | None = None


class SeedDemandSummary(BaseModel):
    budget_year: int
    total_entries: int
    total_quantity_demanded: Decimal
    average_quantity_per_entry: Decimal
    total_estimated_land_ha: Decimal
    average_estimated_land_ha: Decimal


class SeedDemandTrend(BaseModel):
    budget_year: int
    seed_class: str
    quantity_demanded: Decimal


class SeedDemandByCrop(BaseModel):
    crop_code: str
    crop_name: str
    budget_year: int
    seed_class: str
    quantity_demanded: Decimal


class AgricultureStatistics(BaseModel):
    livestock_population: list[LivestockPopulation] = Field(default_factory=list)
    seed_demand_summary: list[SeedDemandSummary] = Field(default_factory=list)
    seed_demand_trends: list[SeedDemandTrend] = Field(default_factory=list)
    seed_demand_by_crop: list[SeedDemandByCrop] = Field(default_factory=list)


class MasterDataSnapshot(BaseModel):
    release: Release
    catalogues: list[Catalogue]
    geography: Geography
    agriculture_statistics: AgricultureStatistics


class CropTaxonomyReference(BaseModel):
    code: str
    display_name: str
    display_name_i18n: Mapping[str, Any] | None = None


class CropVarietyCharacteristic(BaseModel):
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


class CropVarietySourceRecord(BaseModel):
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
    characteristics: list[CropVarietyCharacteristic] = Field(default_factory=list)


class CropVarietyDetail(BaseModel):
    code: str
    display_name: str
    display_name_i18n: Mapping[str, Any] | None = None
    status: str
    crop_type: CropTaxonomyReference
    category: CropTaxonomyReference
    source_records: list[CropVarietySourceRecord] = Field(default_factory=list)


class CropVarietyDetailResponse(BaseModel):
    release: Release
    variety: CropVarietyDetail


class SeedVariety(BaseModel):
    code: str
    display_name: str
    status: str
    source_variety_id: int
    seed_crop: CropTaxonomyReference
    matched_crop_variety: CropTaxonomyReference | None = None
    crop_type: CropTaxonomyReference | None = None
    category: CropTaxonomyReference | None = None
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
    release: Release
    varieties: list[SeedVariety]
    total: int
    page: int
    page_size: int


class SeedVarietyDetailResponse(BaseModel):
    release: Release
    variety: SeedVariety


class LivestockReference(BaseModel):
    code: str
    display_name: str


class LivestockSpecies(LivestockReference):
    status: str
    description: str | None = None
    icon_url: str | None = None
    dataset_id: int | None = None
    scientific_name: str | None = None
    subfamily: str | None = None
    species_type_code: int | None = None
    chart_color: str | None = None
    ear_tag_range: str | None = None
    in_lis_population: bool
    in_etlits_registry: bool


class LivestockSpeciesListResponse(BaseModel):
    release: Release
    species: list[LivestockSpecies]
    total: int
    page: int
    page_size: int


class LivestockBreed(LivestockReference):
    status: str
    species: LivestockReference
    source_id: int
    breed_code: str | None = None
    abbreviation: str | None = None
    breed_type: Literal["Indigenous", "Exotic", "Cross"]
    in_national_standard: bool
    in_etlits_registry: bool
    source: str


class LivestockBreedListResponse(BaseModel):
    release: Release
    breeds: list[LivestockBreed]
    total: int
    page: int
    page_size: int


class LivestockGender(LivestockReference):
    description: str | None = None
    in_etlits_registry: bool


class LivestockLocationType(LivestockReference):
    ethiopian_zone_name: str | None = None
    altitude_description: str | None = None
    description: str | None = None
    ecological_zone: LivestockReference


class LivestockBodyCondition(LivestockReference):
    bcs_score: int
    condition_label: str
    fatness_label: str
    etlits_label: str | None = None
    description: str | None = None


class LivestockProductionType(LivestockReference):
    standard_purpose: str | None = None
    in_national_standard: bool
    in_etlits_registry: bool
    description: str | None = None
    valid_species: list[LivestockReference] = Field(default_factory=list)


class LivestockRecordStatus(LivestockReference):
    sort_order: int
    is_live_master_data: bool
    description: str | None = None


class LivestockReferenceDataResponse(BaseModel):
    release: Release
    genders: list[LivestockGender]
    location_types: list[LivestockLocationType]
    body_conditions: list[LivestockBodyCondition]
    production_types: list[LivestockProductionType]
    record_statuses: list[LivestockRecordStatus]


class LivestockRegistryValidation(BaseModel):
    id: str
    status: str
    species_code: str
    breed_name: str
    breed_code: str | None = None
    breed_species_code: str | None = None
    production_type_code: str
    breed_unrecognised: bool
    breed_outside_national_standard: bool
    breed_species_mismatch: bool
    production_type_species_mismatch: bool


class LivestockRegistryEntry(BaseModel):
    id: str
    species_code: str
    breed_name: str
    breed_id: int | None = None
    breed_code: str | None = None
    breed_species_code: str | None = None
    gender_code: str
    location_type_code: str
    body_condition_code: str
    production_type_code: str
    status: str
    created_on: datetime
    updated_on: datetime
    validation: LivestockRegistryValidation


class LivestockRegistryEntryListResponse(BaseModel):
    release: Release
    entries: list[LivestockRegistryEntry]
    total: int
    page: int
    page_size: int


class LivestockRegistryValidationResponse(BaseModel):
    release: Release
    validations: list[LivestockRegistryValidation]
    total: int
    page: int
    page_size: int


@dataclass(frozen=True, slots=True)
class SnapshotFetch:
    changed: bool
    etag: str
    snapshot: MasterDataSnapshot | None


@dataclass(frozen=True, slots=True)
class CropVarietyDetailFetch:
    changed: bool
    etag: str
    detail: CropVarietyDetailResponse | None


@dataclass(frozen=True, slots=True)
class SeedVarietyListFetch:
    changed: bool
    etag: str
    listing: SeedVarietyListResponse | None


@dataclass(frozen=True, slots=True)
class SeedVarietyDetailFetch:
    changed: bool
    etag: str
    detail: SeedVarietyDetailResponse | None


@dataclass(frozen=True, slots=True)
class LivestockSpeciesListFetch:
    changed: bool
    etag: str
    listing: LivestockSpeciesListResponse | None


@dataclass(frozen=True, slots=True)
class LivestockBreedListFetch:
    changed: bool
    etag: str
    listing: LivestockBreedListResponse | None


@dataclass(frozen=True, slots=True)
class LivestockReferenceDataFetch:
    changed: bool
    etag: str
    reference_data: LivestockReferenceDataResponse | None


@dataclass(frozen=True, slots=True)
class LivestockRegistryEntryListFetch:
    changed: bool
    etag: str
    listing: LivestockRegistryEntryListResponse | None


@dataclass(frozen=True, slots=True)
class LivestockRegistryValidationFetch:
    changed: bool
    etag: str
    listing: LivestockRegistryValidationResponse | None


@dataclass(frozen=True, slots=True)
class SyncState:
    country_code: str
    release_version: str | None = None
    etag: str | None = None


@dataclass(frozen=True, slots=True)
class SyncResult:
    changed: bool
    state: SyncState
