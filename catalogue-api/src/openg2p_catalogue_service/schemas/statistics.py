from decimal import Decimal

from pydantic import BaseModel, Field

from .catalogue import ReleaseData


class LivestockPopulationData(BaseModel):
    species_code: str
    census_year: int
    population_total: int
    source_record_count: int | None = None
    source: str | None = None


class SeedDemandSummaryData(BaseModel):
    budget_year: int
    total_entries: int
    total_quantity_demanded: Decimal
    average_quantity_per_entry: Decimal
    total_estimated_land_ha: Decimal
    average_estimated_land_ha: Decimal


class SeedDemandTrendData(BaseModel):
    budget_year: int
    seed_class: str
    quantity_demanded: Decimal


class SeedDemandByCropData(BaseModel):
    crop_code: str
    crop_name: str
    budget_year: int
    seed_class: str
    quantity_demanded: Decimal


class LivestockPopulationResponse(BaseModel):
    release: ReleaseData
    statistics: list[LivestockPopulationData]
    total: int
    page: int
    page_size: int


class SeedDemandSummaryResponse(BaseModel):
    release: ReleaseData
    statistics: list[SeedDemandSummaryData]
    total: int
    page: int
    page_size: int


class SeedDemandTrendResponse(BaseModel):
    release: ReleaseData
    statistics: list[SeedDemandTrendData]
    total: int
    page: int
    page_size: int


class SeedDemandByCropResponse(BaseModel):
    release: ReleaseData
    statistics: list[SeedDemandByCropData]
    total: int
    page: int
    page_size: int


class AgricultureStatisticsSnapshotData(BaseModel):
    livestock_population: list[LivestockPopulationData] = Field(default_factory=list)
    seed_demand_summary: list[SeedDemandSummaryData] = Field(default_factory=list)
    seed_demand_trends: list[SeedDemandTrendData] = Field(default_factory=list)
    seed_demand_by_crop: list[SeedDemandByCropData] = Field(default_factory=list)
