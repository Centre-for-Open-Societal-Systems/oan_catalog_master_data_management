from openg2p_fastapi_common.service import BaseService
from sqlalchemy import func, select
from sqlalchemy.orm import aliased

from ..engine import get_session_maker
from ..models import (
    Catalogue,
    CatalogueValue,
    CatalogueValueRelation,
    SeedVarietySourceRecord,
)
from ..schemas import (
    CropTaxonomyReferenceData,
    SeedVarietyData,
    SeedVarietyDetailResponse,
    SeedVarietyListResponse,
)
from .release_service import ResourceNotFoundError, release_data, resolve_release

SeedVarietyNotFoundError = ResourceNotFoundError


def reference_data(value: CatalogueValue | None) -> CropTaxonomyReferenceData | None:
    if value is None:
        return None
    return CropTaxonomyReferenceData(
        code=value.code,
        display_name=value.display_name,
        display_name_i18n=value.display_name_i18n,
    )


class SeedVarietyService(BaseService):
    async def get_seed_varieties(
        self,
        country_code: str | None = None,
        release_version: str | None = None,
        seed_crop_code: str | None = None,
        crop_variety_code: str | None = None,
        crop_type_code: str | None = None,
        category_code: str | None = None,
        match_status: str | None = None,
        release_year: int | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 100,
        seed_variety_code: str | None = None,
    ) -> SeedVarietyListResponse:
        seed_variety = aliased(CatalogueValue)
        seed_crop = aliased(CatalogueValue)
        crop_variety = aliased(CatalogueValue)
        crop_type = aliased(CatalogueValue)
        category = aliased(CatalogueValue)
        seed_variety_catalogue = aliased(Catalogue)
        crop_type_relation = aliased(CatalogueValueRelation)
        category_relation = aliased(CatalogueValueRelation)

        async with get_session_maker()() as session:
            release = await resolve_release(session, country_code, release_version)
            filters = [
                SeedVarietySourceRecord.release_id == release.release_id,
                seed_variety_catalogue.release_id == release.release_id,
                seed_variety_catalogue.code == "seed_variety",
            ]
            if seed_variety_code is not None:
                filters.append(seed_variety.code == seed_variety_code)
            if seed_crop_code is not None:
                filters.append(seed_crop.code == seed_crop_code)
            if crop_variety_code is not None:
                filters.append(crop_variety.code == crop_variety_code)
            if crop_type_code is not None:
                filters.append(crop_type.code == crop_type_code)
            if category_code is not None:
                filters.append(category.code == category_code)
            if match_status is not None:
                filters.append(SeedVarietySourceRecord.match_status == match_status.upper())
            if release_year is not None:
                filters.append(SeedVarietySourceRecord.release_year == release_year)
            if search is not None:
                pattern = f"%{search.strip()}%"
                filters.append(
                    seed_variety.code.ilike(pattern)
                    | seed_variety.display_name.ilike(pattern)
                    | SeedVarietySourceRecord.crop_name_raw.ilike(pattern)
                    | SeedVarietySourceRecord.common_name_raw.ilike(pattern)
                )

            stmt = (
                select(
                    SeedVarietySourceRecord,
                    seed_variety,
                    seed_crop,
                    crop_variety,
                    crop_type,
                    category,
                )
                .join(
                    seed_variety,
                    seed_variety.catalogue_value_id == SeedVarietySourceRecord.seed_variety_value_id,
                )
                .join(
                    seed_variety_catalogue,
                    seed_variety.catalogue_id == seed_variety_catalogue.catalogue_id,
                )
                .join(
                    seed_crop,
                    seed_crop.catalogue_value_id == SeedVarietySourceRecord.seed_crop_value_id,
                )
                .outerjoin(
                    crop_variety,
                    crop_variety.catalogue_value_id == SeedVarietySourceRecord.matched_crop_variety_value_id,
                )
                .outerjoin(
                    crop_type_relation,
                    (crop_type_relation.source_value_id == seed_variety.catalogue_value_id)
                    & (crop_type_relation.relation_type == "crop_type"),
                )
                .outerjoin(
                    crop_type,
                    crop_type.catalogue_value_id == crop_type_relation.target_value_id,
                )
                .outerjoin(
                    category_relation,
                    (category_relation.source_value_id == seed_variety.catalogue_value_id)
                    & (category_relation.relation_type == "category"),
                )
                .outerjoin(
                    category,
                    category.catalogue_value_id == category_relation.target_value_id,
                )
                .where(*filters)
            )
            total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
            rows = (
                await session.execute(
                    stmt.order_by(seed_variety.code).limit(page_size).offset((page - 1) * page_size)
                )
            ).all()

        varieties = [
            SeedVarietyData(
                code=variety.code,
                display_name=variety.display_name,
                status=variety.status,
                source_variety_id=source.source_variety_id,
                seed_crop=reference_data(seed_crop_value),
                matched_crop_variety=reference_data(crop_variety_value),
                crop_type=reference_data(crop_type_value),
                category=reference_data(category_value),
                crop_name_raw=source.crop_name_raw,
                common_name_raw=source.common_name_raw,
                category_raw=source.category_raw,
                release_year=source.release_year,
                release_date=source.release_date,
                release_raw=source.release_raw,
                maintainer=source.maintainer,
                source_classification=source.source_classification,
                details_url=source.details_url,
                match_method=source.match_method,
                match_status=source.match_status,
                review_note=source.review_note,
            )
            for source, variety, seed_crop_value, crop_variety_value, crop_type_value, category_value in rows
        ]
        return SeedVarietyListResponse(
            release=release_data(release),
            varieties=varieties,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_seed_variety_detail(
        self,
        seed_variety_code: str,
        country_code: str | None = None,
        release_version: str | None = None,
    ) -> SeedVarietyDetailResponse:
        result = await self.get_seed_varieties(
            country_code=country_code,
            release_version=release_version,
            seed_variety_code=seed_variety_code,
            page=1,
            page_size=1,
        )
        if not result.varieties:
            raise SeedVarietyNotFoundError(f"Unknown seed variety: {seed_variety_code}")
        return SeedVarietyDetailResponse(
            release=result.release,
            variety=result.varieties[0],
        )
