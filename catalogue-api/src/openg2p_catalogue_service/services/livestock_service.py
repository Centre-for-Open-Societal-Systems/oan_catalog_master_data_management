import asyncio

from openg2p_fastapi_common.service import BaseService
from sqlalchemy import and_, func, or_, select

from ..engine import get_session_maker
from ..models import LivestockRegistryEntry
from ..schemas import (
    CatalogueValueData,
    LivestockBodyConditionData,
    LivestockBreedData,
    LivestockBreedListResponse,
    LivestockGenderData,
    LivestockLocationTypeData,
    LivestockProductionTypeData,
    LivestockRecordStatusData,
    LivestockReferenceData,
    LivestockReferenceDataResponse,
    LivestockRegistryEntryData,
    LivestockRegistryEntryListResponse,
    LivestockRegistryValidationData,
    LivestockRegistryValidationResponse,
    LivestockSpeciesData,
    LivestockSpeciesListResponse,
)
from .catalogue_service import CatalogueNotFoundError, CatalogueService
from .release_service import release_data, resolve_release

LivestockReferenceNotFoundError = CatalogueNotFoundError


def related_reference(value: CatalogueValueData, relation_type: str) -> LivestockReferenceData:
    relation = next(
        (item for item in value.relations if item.type == relation_type),
        None,
    )
    if relation is None:
        raise LivestockReferenceNotFoundError(f"Livestock value {value.code} has no {relation_type} relation")
    return LivestockReferenceData(
        code=relation.target_code,
        display_name=relation.target_display_name,
    )


def species_data(value: CatalogueValueData) -> LivestockSpeciesData:
    metadata = value.metadata
    return LivestockSpeciesData(
        code=value.code,
        display_name=value.display_name,
        status=value.status,
        description=metadata.get("description"),
        icon_url=metadata.get("icon_url"),
        dataset_id=metadata.get("dataset_id"),
        scientific_name=metadata.get("scientific_name"),
        subfamily=metadata.get("subfamily"),
        species_type_code=metadata.get("species_type_code"),
        chart_color=metadata.get("chart_color"),
        ear_tag_range=metadata.get("ear_tag_range"),
        in_lis_population=bool(metadata.get("in_lis_population")),
        in_etlits_registry=bool(metadata.get("in_etlits_registry")),
    )


def breed_data(value: CatalogueValueData) -> LivestockBreedData:
    metadata = value.metadata
    return LivestockBreedData(
        code=value.code,
        display_name=value.display_name,
        status=value.status,
        species=related_reference(value, "species"),
        source_id=metadata["source_id"],
        breed_code=metadata.get("breed_code"),
        abbreviation=metadata.get("abbreviation"),
        breed_type=metadata["breed_type"],
        in_national_standard=bool(metadata.get("in_national_standard")),
        in_etlits_registry=bool(metadata.get("in_etlits_registry")),
        source=metadata["source"],
    )


def registry_validation(row: LivestockRegistryEntry) -> LivestockRegistryValidationData:
    return LivestockRegistryValidationData(
        id=row.source_entry_id,
        status=row.status,
        species_code=row.species_code,
        breed_name=row.breed_name,
        breed_code=row.breed_code,
        breed_species_code=row.breed_species_code,
        production_type_code=row.production_type_code,
        breed_unrecognised=row.breed_source_id is None,
        breed_outside_national_standard=(
            row.breed_source_id is not None and row.breed_in_national_standard is False
        ),
        breed_species_mismatch=(
            row.breed_source_id is not None and row.breed_species_code != row.species_code
        ),
        production_type_species_mismatch=(not row.production_type_species_valid),
    )


def registry_entry_data(row: LivestockRegistryEntry) -> LivestockRegistryEntryData:
    return LivestockRegistryEntryData(
        id=row.source_entry_id,
        species_code=row.species_code,
        breed_name=row.breed_name,
        breed_id=row.breed_source_id,
        breed_code=row.breed_code,
        breed_species_code=row.breed_species_code,
        gender_code=row.gender_code,
        location_type_code=row.location_type_code,
        body_condition_code=row.body_condition_code,
        production_type_code=row.production_type_code,
        status=row.status,
        created_on=row.source_created_on,
        updated_on=row.source_updated_on,
        validation=registry_validation(row),
    )


class LivestockService(BaseService):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.catalogue_service = CatalogueService.get_component()

    async def get_species(
        self,
        country_code: str | None = None,
        release_version: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> LivestockSpeciesListResponse:
        result = await self.catalogue_service.get_values(
            "livestock_type",
            country_code=country_code,
            release_version=release_version,
            search=search,
            page=page,
            page_size=page_size,
        )
        return LivestockSpeciesListResponse(
            release=result.release,
            species=[species_data(value) for value in result.values],
            total=result.total,
            page=result.page,
            page_size=result.page_size,
        )

    async def get_breeds(
        self,
        country_code: str | None = None,
        release_version: str | None = None,
        species_code: str | None = None,
        breed_type: str | None = None,
        in_national_standard: bool | None = None,
        in_etlits_registry: bool | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> LivestockBreedListResponse:
        release = await self.catalogue_service.get_current_release(country_code, release_version)
        result = await self.catalogue_service.get_values(
            "livestock_breed",
            country_code=country_code,
            release_version=release.version,
            search=search,
            page=1,
            page_size=1000,
        )
        values = list(result.values)
        for source_page in range(2, (result.total - 1) // 1000 + 2):
            next_page = await self.catalogue_service.get_values(
                "livestock_breed",
                country_code=country_code,
                release_version=release.version,
                search=search,
                page=source_page,
                page_size=1000,
            )
            values.extend(next_page.values)
        breeds = [breed_data(value) for value in values]
        if species_code is not None:
            breeds = [item for item in breeds if item.species.code == species_code]
        if breed_type is not None:
            breeds = [item for item in breeds if item.breed_type == breed_type]
        if in_national_standard is not None:
            breeds = [item for item in breeds if item.in_national_standard is in_national_standard]
        if in_etlits_registry is not None:
            breeds = [item for item in breeds if item.in_etlits_registry is in_etlits_registry]
        total = len(breeds)
        offset = (page - 1) * page_size
        return LivestockBreedListResponse(
            release=release,
            breeds=breeds[offset : offset + page_size],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_reference_data(
        self,
        country_code: str | None = None,
        release_version: str | None = None,
    ) -> LivestockReferenceDataResponse:
        release = await self.catalogue_service.get_current_release(country_code, release_version)
        gender, location, condition, production, status = await asyncio.gather(
            *(
                self.catalogue_service.get_values(
                    catalogue_code,
                    country_code=country_code,
                    release_version=release.version,
                    page=1,
                    page_size=1000,
                )
                for catalogue_code in (
                    "livestock_gender",
                    "livestock_location_type",
                    "livestock_body_condition",
                    "livestock_production_type",
                    "etlits_livestock_record_status",
                )
            )
        )
        return LivestockReferenceDataResponse(
            release=release,
            genders=[
                LivestockGenderData(
                    code=value.code,
                    display_name=value.display_name,
                    description=value.metadata.get("description"),
                    in_etlits_registry=bool(value.metadata.get("in_etlits_registry")),
                )
                for value in gender.values
            ],
            location_types=[
                LivestockLocationTypeData(
                    code=value.code,
                    display_name=value.display_name,
                    ethiopian_zone_name=value.metadata.get("ethiopian_zone_name"),
                    altitude_description=value.metadata.get("altitude_description"),
                    description=value.metadata.get("description"),
                    ecological_zone=related_reference(value, "ecological_zone"),
                )
                for value in location.values
            ],
            body_conditions=[
                LivestockBodyConditionData(
                    code=value.code,
                    display_name=value.display_name,
                    bcs_score=value.metadata["bcs_score"],
                    condition_label=value.metadata["condition_label"],
                    fatness_label=value.metadata["fatness_label"],
                    etlits_label=value.metadata.get("etlits_label"),
                    description=value.metadata.get("description"),
                )
                for value in condition.values
            ],
            production_types=[
                LivestockProductionTypeData(
                    code=value.code,
                    display_name=value.display_name,
                    standard_purpose=value.metadata.get("standard_purpose"),
                    in_national_standard=bool(value.metadata.get("in_national_standard")),
                    in_etlits_registry=bool(value.metadata.get("in_etlits_registry")),
                    description=value.metadata.get("description"),
                    valid_species=[
                        LivestockReferenceData(
                            code=relation.target_code,
                            display_name=relation.target_display_name,
                        )
                        for relation in value.relations
                        if relation.type == "valid_for_species"
                    ],
                )
                for value in production.values
            ],
            record_statuses=[
                LivestockRecordStatusData(
                    code=value.code,
                    display_name=value.display_name,
                    sort_order=value.sort_order or 0,
                    is_live_master_data=bool(value.metadata.get("is_live_master_data")),
                    description=value.metadata.get("description"),
                )
                for value in status.values
            ],
        )

    @staticmethod
    def _registry_filters(
        release_id: str,
        species_code: str | None,
        status: str | None,
        breed_id: int | None,
        search: str | None,
    ):
        filters = [LivestockRegistryEntry.release_id == release_id]
        if species_code is not None:
            filters.append(LivestockRegistryEntry.species_code == species_code.casefold())
        if status is not None:
            filters.append(LivestockRegistryEntry.status == status.upper())
        if breed_id is not None:
            filters.append(LivestockRegistryEntry.breed_source_id == breed_id)
        if search is not None:
            pattern = f"%{search.strip()}%"
            filters.append(
                or_(
                    LivestockRegistryEntry.source_entry_id.ilike(pattern),
                    LivestockRegistryEntry.breed_name.ilike(pattern),
                )
            )
        return filters

    async def get_registry_entries(
        self,
        country_code: str | None = None,
        release_version: str | None = None,
        species_code: str | None = None,
        status: str | None = None,
        breed_id: int | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> LivestockRegistryEntryListResponse:
        async with get_session_maker()() as session:
            release = await resolve_release(session, country_code, release_version)
            filters = self._registry_filters(release.release_id, species_code, status, breed_id, search)
            stmt = select(LivestockRegistryEntry).where(*filters)
            total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
            rows = (
                (
                    await session.execute(
                        stmt.order_by(LivestockRegistryEntry.source_entry_id)
                        .limit(page_size)
                        .offset((page - 1) * page_size)
                    )
                )
                .scalars()
                .all()
            )
        return LivestockRegistryEntryListResponse(
            release=release_data(release),
            entries=[registry_entry_data(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_registry_validation(
        self,
        country_code: str | None = None,
        release_version: str | None = None,
        species_code: str | None = None,
        status: str | None = None,
        has_issues: bool | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> LivestockRegistryValidationResponse:
        async with get_session_maker()() as session:
            release = await resolve_release(session, country_code, release_version)
            filters = self._registry_filters(release.release_id, species_code, status, None, None)
            issues = or_(
                LivestockRegistryEntry.breed_source_id.is_(None),
                and_(
                    LivestockRegistryEntry.breed_source_id.is_not(None),
                    LivestockRegistryEntry.breed_in_national_standard.is_(False),
                ),
                and_(
                    LivestockRegistryEntry.breed_source_id.is_not(None),
                    LivestockRegistryEntry.breed_species_code != LivestockRegistryEntry.species_code,
                ),
                LivestockRegistryEntry.production_type_species_valid.is_(False),
            )
            if has_issues is True:
                filters.append(issues)
            elif has_issues is False:
                filters.append(~issues)
            stmt = select(LivestockRegistryEntry).where(*filters)
            total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
            rows = (
                (
                    await session.execute(
                        stmt.order_by(LivestockRegistryEntry.source_entry_id)
                        .limit(page_size)
                        .offset((page - 1) * page_size)
                    )
                )
                .scalars()
                .all()
            )
        return LivestockRegistryValidationResponse(
            release=release_data(release),
            validations=[registry_validation(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )
