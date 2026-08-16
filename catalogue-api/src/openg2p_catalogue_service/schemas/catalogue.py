from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class ReleaseData(BaseModel):
    country_code: str
    version: str
    schema_version: str
    checksum: str
    source: str | None = None
    status: str
    activated_at: datetime | None = None


class CatalogueData(BaseModel):
    code: str
    domain: str | None = None
    display_name: str
    display_name_i18n: dict[str, Any] | None = None
    is_hierarchical: bool = False
    status: str


class CatalogueValueRelationData(BaseModel):
    type: str
    target_catalogue_code: str
    target_code: str
    target_display_name: str


class CatalogueValueData(BaseModel):
    code: str
    parent_code: str | None = None
    display_name: str
    display_name_i18n: dict[str, Any] | None = None
    semantic_roles: list[str] = Field(default_factory=list)
    sort_order: int | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    status: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    relations: list[CatalogueValueRelationData] = Field(default_factory=list)


class CatalogueListResponse(BaseModel):
    release: ReleaseData
    catalogues: list[CatalogueData]


class CatalogueValuesResponse(BaseModel):
    release: ReleaseData
    catalogue: CatalogueData
    values: list[CatalogueValueData]
    total: int
    page: int
    page_size: int


class CatalogueOptionData(BaseModel):
    """Stable option contract for platform select widgets."""

    code: str
    display_name: str


class CatalogueOptionsResponse(BaseModel):
    release: ReleaseData
    catalogue: CatalogueData
    options: list[CatalogueOptionData]
    total: int
    page: int
    page_size: int


def catalogue_options(values: CatalogueValuesResponse) -> CatalogueOptionsResponse:
    options: list[CatalogueOptionData] = []
    for value in values.values:
        code = value.code.strip()
        display_name = value.display_name.strip()
        if not code or not display_name:
            raise ValueError("Catalogue options require non-empty code and display_name")
        options.append(CatalogueOptionData(code=code, display_name=display_name))

    return CatalogueOptionsResponse(
        release=values.release,
        catalogue=values.catalogue,
        options=options,
        total=values.total,
        page=values.page,
        page_size=values.page_size,
    )


class CatalogueSnapshotData(CatalogueData):
    values: list[CatalogueValueData] = Field(default_factory=list)


class CatalogueSnapshotResponse(BaseModel):
    release: ReleaseData
    catalogues: list[CatalogueSnapshotData]
