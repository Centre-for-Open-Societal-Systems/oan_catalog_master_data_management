from openg2p_fastapi_common.service import BaseService
from sqlalchemy import func, select
from sqlalchemy.orm import aliased

from ..engine import get_session_maker
from ..models import GeographyLevel, GeographyUnit
from ..schemas import (
    GeographyLevelData,
    GeographyLevelsResponse,
    GeographyUnitData,
    GeographyUnitsResponse,
    ReleaseData,
)
from .release_service import ResourceNotFoundError, release_data, resolve_release


def geography_level_data(row: GeographyLevel, parent_level_code: str | None) -> GeographyLevelData:
    return GeographyLevelData(
        code=row.code,
        display_name=row.display_name,
        display_name_i18n=row.display_name_i18n,
        level_order=row.level_order,
        parent_level_code=parent_level_code,
    )


def geography_unit_data(row: GeographyUnit, level_code: str, parent_code: str | None) -> GeographyUnitData:
    return GeographyUnitData(
        code=row.code,
        level_code=level_code,
        parent_code=parent_code,
        display_name=row.display_name,
        display_name_amh=row.display_name_amh,
        display_name_i18n=row.display_name_i18n,
        latitude=row.latitude,
        longitude=row.longitude,
        valid_from=row.valid_from,
        valid_to=row.valid_to,
        status=row.status,
        aliases=row.aliases or [],
        metadata=row.unit_metadata or {},
    )


class GeographyService(BaseService):
    async def get_levels(
        self,
        country_code: str | None = None,
        release_version: str | None = None,
    ) -> GeographyLevelsResponse:
        parent_level = aliased(GeographyLevel)
        async with get_session_maker()() as session:
            release = await resolve_release(session, country_code, release_version)
            rows = (
                await session.execute(
                    select(GeographyLevel, parent_level.code)
                    .outerjoin(
                        parent_level,
                        GeographyLevel.parent_level_id == parent_level.geography_level_id,
                    )
                    .where(GeographyLevel.release_id == release.release_id)
                    .order_by(GeographyLevel.level_order)
                )
            ).all()
        return GeographyLevelsResponse(
            release=release_data(release),
            levels=[geography_level_data(level, parent_code) for level, parent_code in rows],
        )

    async def get_units(
        self,
        country_code: str | None = None,
        release_version: str | None = None,
        level_code: str | None = None,
        parent_code: str | None = None,
        status: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> GeographyUnitsResponse:
        parent = aliased(GeographyUnit)
        async with get_session_maker()() as session:
            release = await resolve_release(session, country_code, release_version)
            filters = [GeographyLevel.release_id == release.release_id]
            if level_code is not None:
                filters.append(GeographyLevel.code == level_code)
            if parent_code is not None:
                filters.append(parent.code == parent_code)
            if status is not None:
                filters.append(GeographyUnit.status == status.upper())
            if search is not None:
                search_pattern = f"%{search.strip()}%"
                filters.append(
                    GeographyUnit.code.ilike(search_pattern)
                    | GeographyUnit.display_name.ilike(search_pattern)
                    | GeographyUnit.display_name_amh.ilike(search_pattern)
                )

            source = (
                select(GeographyUnit, GeographyLevel.code, parent.code)
                .join(
                    GeographyLevel,
                    GeographyUnit.geography_level_id == GeographyLevel.geography_level_id,
                )
                .outerjoin(parent, GeographyUnit.parent_unit_id == parent.geography_unit_id)
                .where(*filters)
            )
            total = (await session.execute(select(func.count()).select_from(source.subquery()))).scalar_one()
            rows = (
                await session.execute(
                    source.order_by(GeographyLevel.level_order, GeographyUnit.code)
                    .limit(page_size)
                    .offset((page - 1) * page_size)
                )
            ).all()

        return GeographyUnitsResponse(
            release=release_data(release),
            units=[
                geography_unit_data(unit, resolved_level_code, resolved_parent_code)
                for unit, resolved_level_code, resolved_parent_code in rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_unit(
        self,
        unit_code: str,
        country_code: str | None = None,
        release_version: str | None = None,
        level_code: str | None = None,
    ) -> tuple[ReleaseData, GeographyUnitData]:
        parent = aliased(GeographyUnit)
        async with get_session_maker()() as session:
            release = await resolve_release(session, country_code, release_version)
            stmt = (
                select(GeographyUnit, GeographyLevel.code, parent.code)
                .join(
                    GeographyLevel,
                    GeographyUnit.geography_level_id == GeographyLevel.geography_level_id,
                )
                .outerjoin(parent, GeographyUnit.parent_unit_id == parent.geography_unit_id)
                .where(
                    GeographyLevel.release_id == release.release_id,
                    GeographyUnit.code == unit_code,
                )
            )
            if level_code is not None:
                stmt = stmt.where(GeographyLevel.code == level_code)
            rows = (await session.execute(stmt.limit(2))).all()

        if not rows:
            raise ResourceNotFoundError(f"Unknown geography unit: {unit_code}")
        if len(rows) > 1:
            raise ResourceNotFoundError(f"Geography unit code {unit_code} is ambiguous; supply level_code")
        unit, resolved_level_code, resolved_parent_code = rows[0]
        return release_data(release), geography_unit_data(unit, resolved_level_code, resolved_parent_code)
