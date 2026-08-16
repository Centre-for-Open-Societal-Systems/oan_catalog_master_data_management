from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .catalogue import ReleaseData


class LivestockReferenceData(BaseModel):
    code: str
    display_name: str


class LivestockSpeciesData(LivestockReferenceData):
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
    release: ReleaseData
    species: list[LivestockSpeciesData]
    total: int
    page: int
    page_size: int


class LivestockBreedData(LivestockReferenceData):
    status: str
    species: LivestockReferenceData
    source_id: int
    breed_code: str | None = None
    abbreviation: str | None = None
    breed_type: Literal["Indigenous", "Exotic", "Cross"]
    in_national_standard: bool
    in_etlits_registry: bool
    source: str


class LivestockBreedListResponse(BaseModel):
    release: ReleaseData
    breeds: list[LivestockBreedData]
    total: int
    page: int
    page_size: int


class LivestockGenderData(LivestockReferenceData):
    description: str | None = None
    in_etlits_registry: bool


class LivestockLocationTypeData(LivestockReferenceData):
    ethiopian_zone_name: str | None = None
    altitude_description: str | None = None
    description: str | None = None
    ecological_zone: LivestockReferenceData


class LivestockBodyConditionData(LivestockReferenceData):
    bcs_score: int
    condition_label: str
    fatness_label: str
    etlits_label: str | None = None
    description: str | None = None


class LivestockProductionTypeData(LivestockReferenceData):
    standard_purpose: str | None = None
    in_national_standard: bool
    in_etlits_registry: bool
    description: str | None = None
    valid_species: list[LivestockReferenceData] = Field(default_factory=list)


class LivestockRecordStatusData(LivestockReferenceData):
    sort_order: int
    is_live_master_data: bool
    description: str | None = None


class LivestockReferenceDataResponse(BaseModel):
    release: ReleaseData
    genders: list[LivestockGenderData]
    location_types: list[LivestockLocationTypeData]
    body_conditions: list[LivestockBodyConditionData]
    production_types: list[LivestockProductionTypeData]
    record_statuses: list[LivestockRecordStatusData]


class LivestockRegistryValidationData(BaseModel):
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


class LivestockRegistryEntryData(BaseModel):
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
    validation: LivestockRegistryValidationData


class LivestockRegistryEntryListResponse(BaseModel):
    release: ReleaseData
    entries: list[LivestockRegistryEntryData]
    total: int
    page: int
    page_size: int


class LivestockRegistryValidationResponse(BaseModel):
    release: ReleaseData
    validations: list[LivestockRegistryValidationData]
    total: int
    page: int
    page_size: int
