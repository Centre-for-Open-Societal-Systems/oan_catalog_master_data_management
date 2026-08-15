from collections import defaultdict

from openg2p_fastapi_common.service import BaseService
from sqlalchemy import select
from sqlalchemy.orm import aliased

from ..engine import get_session_maker
from ..models import (
    Catalogue,
    CatalogueValue,
    CatalogueValueRelation,
    CropCharacteristicDefinition,
    CropVarietyCharacteristic,
    CropVarietySourceRecord,
)
from ..schemas import (
    CropTaxonomyReferenceData,
    CropVarietyCharacteristicData,
    CropVarietyDetailData,
    CropVarietyDetailResponse,
    CropVarietySourceRecordData,
)
from .release_service import ResourceNotFoundError, release_data, resolve_release

CropVarietyNotFoundError = ResourceNotFoundError


class CropTaxonomyService(BaseService):
    async def get_variety_detail(
        self,
        variety_code: str,
        country_code: str | None = None,
        release_version: str | None = None,
    ) -> CropVarietyDetailResponse:
        variety_catalogue = aliased(Catalogue)
        crop_type_catalogue = aliased(Catalogue)
        category_catalogue = aliased(Catalogue)
        variety_value = aliased(CatalogueValue)
        crop_type_value = aliased(CatalogueValue)
        category_value = aliased(CatalogueValue)
        crop_type_relation = aliased(CatalogueValueRelation)
        category_relation = aliased(CatalogueValueRelation)

        async with get_session_maker()() as session:
            release = await resolve_release(session, country_code, release_version)
            identity = (
                await session.execute(
                    select(variety_value, crop_type_value, category_value)
                    .join(
                        variety_catalogue,
                        variety_value.catalogue_id == variety_catalogue.catalogue_id,
                    )
                    .join(
                        crop_type_relation,
                        (crop_type_relation.source_value_id == variety_value.catalogue_value_id)
                        & (crop_type_relation.relation_type == "crop_type"),
                    )
                    .join(
                        crop_type_value,
                        crop_type_value.catalogue_value_id == crop_type_relation.target_value_id,
                    )
                    .join(
                        crop_type_catalogue,
                        crop_type_value.catalogue_id == crop_type_catalogue.catalogue_id,
                    )
                    .join(
                        category_relation,
                        (category_relation.source_value_id == crop_type_value.catalogue_value_id)
                        & (category_relation.relation_type == "category"),
                    )
                    .join(
                        category_value,
                        category_value.catalogue_value_id == category_relation.target_value_id,
                    )
                    .join(
                        category_catalogue,
                        category_value.catalogue_id == category_catalogue.catalogue_id,
                    )
                    .where(
                        variety_catalogue.release_id == release.release_id,
                        variety_catalogue.code == "crop_variety",
                        crop_type_catalogue.release_id == release.release_id,
                        crop_type_catalogue.code == "crop_type",
                        category_catalogue.release_id == release.release_id,
                        category_catalogue.code == "crop_taxonomy_category",
                        variety_value.code == variety_code,
                    )
                )
            ).first()
            if identity is None:
                raise CropVarietyNotFoundError(f"Unknown crop variety: {variety_code}")
            variety, crop_type, category = identity

            source_records = (
                (
                    await session.execute(
                        select(CropVarietySourceRecord)
                        .where(
                            CropVarietySourceRecord.release_id == release.release_id,
                            CropVarietySourceRecord.variety_value_id == variety.catalogue_value_id,
                        )
                        .order_by(
                            CropVarietySourceRecord.source_row_number.asc().nullslast(),
                            CropVarietySourceRecord.source_record_code,
                        )
                    )
                )
                .scalars()
                .all()
            )
            source_ids = [item.variety_source_record_id for item in source_records]
            characteristics_by_source: dict[str, list[CropVarietyCharacteristicData]] = defaultdict(list)
            if source_ids:
                characteristic_rows = (
                    await session.execute(
                        select(
                            CropVarietyCharacteristic,
                            CropCharacteristicDefinition,
                        )
                        .join(
                            CropCharacteristicDefinition,
                            CropCharacteristicDefinition.characteristic_definition_id
                            == CropVarietyCharacteristic.characteristic_definition_id,
                        )
                        .where(
                            CropVarietyCharacteristic.variety_source_record_id.in_(source_ids),
                            CropCharacteristicDefinition.release_id == release.release_id,
                        )
                        .order_by(
                            CropVarietyCharacteristic.variety_source_record_id,
                            CropCharacteristicDefinition.characteristic_code,
                        )
                    )
                ).all()
                for characteristic, definition in characteristic_rows:
                    characteristics_by_source[characteristic.variety_source_record_id].append(
                        CropVarietyCharacteristicData(
                            code=definition.characteristic_code,
                            display_name=definition.display_name,
                            value_type=definition.value_type,
                            raw_value=characteristic.raw_value,
                            value_text=characteristic.value_text,
                            value_numeric=characteristic.value_numeric,
                            value_boolean=characteristic.value_boolean,
                            value_min=characteristic.value_min,
                            value_max=characteristic.value_max,
                            unit_code=characteristic.unit_code,
                        )
                    )

        return CropVarietyDetailResponse(
            release=release_data(release),
            variety=CropVarietyDetailData(
                code=variety.code,
                display_name=variety.display_name,
                display_name_i18n=variety.display_name_i18n,
                status=variety.status,
                crop_type=CropTaxonomyReferenceData(
                    code=crop_type.code,
                    display_name=crop_type.display_name,
                    display_name_i18n=crop_type.display_name_i18n,
                ),
                category=CropTaxonomyReferenceData(
                    code=category.code,
                    display_name=category.display_name,
                    display_name_i18n=category.display_name_i18n,
                ),
                source_records=[
                    CropVarietySourceRecordData(
                        source_record_code=item.source_record_code,
                        source_row_number=item.source_row_number,
                        centre=item.centre,
                        release_year_raw=item.release_year_raw,
                        release_year=item.release_year,
                        source_url=item.source_url,
                        altitude_min_m=item.altitude_min_m,
                        altitude_max_m=item.altitude_max_m,
                        rainfall_min_mm=item.rainfall_min_mm,
                        rainfall_max_mm=item.rainfall_max_mm,
                        days_to_maturity_min=item.days_to_maturity_min,
                        days_to_maturity_max=item.days_to_maturity_max,
                        yield_research_min_qt_ha=item.yield_research_min_qt_ha,
                        yield_research_max_qt_ha=item.yield_research_max_qt_ha,
                        yield_farmer_min_qt_ha=item.yield_farmer_min_qt_ha,
                        yield_farmer_max_qt_ha=item.yield_farmer_max_qt_ha,
                        seed_rate_kg_ha=item.seed_rate_kg_ha,
                        adaptation_area=item.adaptation_area,
                        planting_date_text=item.planting_date_text,
                        crop_pest_reaction=item.crop_pest_reaction,
                        characteristics=characteristics_by_source[item.variety_source_record_id],
                    )
                    for item in source_records
                ],
            ),
        )
