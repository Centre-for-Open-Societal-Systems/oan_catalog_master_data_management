from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from .catalogue import ReleaseData


class GeographyLevelData(BaseModel):
    code: str
    display_name: str
    display_name_i18n: dict[str, Any] | None = None
    level_order: int
    parent_level_code: str | None = None


class GeographyUnitData(BaseModel):
    code: str
    level_code: str
    parent_code: str | None = None
    display_name: str
    display_name_amh: str | None = None
    display_name_i18n: dict[str, Any] | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    status: str
    aliases: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GeographyLevelsResponse(BaseModel):
    release: ReleaseData
    levels: list[GeographyLevelData]


class GeographyUnitsResponse(BaseModel):
    release: ReleaseData
    units: list[GeographyUnitData]
    total: int
    page: int
    page_size: int


class GeographyUnitResponse(BaseModel):
    release: ReleaseData
    unit: GeographyUnitData


class GeographySnapshotData(BaseModel):
    levels: list[GeographyLevelData] = Field(default_factory=list)
    units: list[GeographyUnitData] = Field(default_factory=list)
