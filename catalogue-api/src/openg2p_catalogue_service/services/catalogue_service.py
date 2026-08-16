from openg2p_fastapi_common.service import BaseService
from sqlalchemy import func, select
from sqlalchemy.orm import aliased

from ..engine import get_session_maker
from ..models import Catalogue, CatalogueRelease, CatalogueValue, CatalogueValueRelation
from ..schemas import (
    CatalogueData,
    CatalogueListResponse,
    CatalogueSnapshotData,
    CatalogueSnapshotResponse,
    CatalogueValueData,
    CatalogueValueRelationData,
    CatalogueValuesResponse,
    ReleaseData,
)
from .release_service import ResourceNotFoundError, release_data, resolve_release

CatalogueNotFoundError = ResourceNotFoundError


def catalogue_data(row: Catalogue) -> CatalogueData:
    return CatalogueData(
        code=row.code,
        domain=row.domain,
        display_name=row.display_name,
        display_name_i18n=row.display_name_i18n,
        is_hierarchical=row.is_hierarchical,
        status=row.status,
    )


def catalogue_value_data(
    row: CatalogueValue,
    parent_code: str | None,
    relations: list[CatalogueValueRelationData] | None = None,
) -> CatalogueValueData:
    return CatalogueValueData(
        code=row.code,
        parent_code=parent_code,
        display_name=row.display_name,
        display_name_i18n=row.display_name_i18n,
        semantic_roles=row.semantic_roles or [],
        sort_order=row.sort_order,
        valid_from=row.valid_from,
        valid_to=row.valid_to,
        status=row.status,
        metadata=row.value_metadata or {},
        relations=relations or [],
    )


async def value_relations(session, source_value_ids: list[str]):
    relations_by_source: dict[str, list[CatalogueValueRelationData]] = {
        value_id: [] for value_id in source_value_ids
    }
    if not source_value_ids:
        return relations_by_source

    target = aliased(CatalogueValue)
    target_catalogue = aliased(Catalogue)
    rows = (
        await session.execute(
            select(
                CatalogueValueRelation.source_value_id,
                CatalogueValueRelation.relation_type,
                target_catalogue.code,
                target.code,
                target.display_name,
            )
            .join(target, CatalogueValueRelation.target_value_id == target.catalogue_value_id)
            .join(target_catalogue, target.catalogue_id == target_catalogue.catalogue_id)
            .where(CatalogueValueRelation.source_value_id.in_(source_value_ids))
            .order_by(
                CatalogueValueRelation.source_value_id,
                CatalogueValueRelation.relation_type,
                target_catalogue.code,
                target.code,
            )
        )
    ).all()
    for source_value_id, relation_type, catalogue_code, code, display_name in rows:
        relations_by_source[source_value_id].append(
            CatalogueValueRelationData(
                type=relation_type,
                target_catalogue_code=catalogue_code,
                target_code=code,
                target_display_name=display_name,
            )
        )
    return relations_by_source


class CatalogueService(BaseService):
    async def _release(
        self,
        country_code: str | None = None,
        release_version: str | None = None,
    ) -> CatalogueRelease:
        async with get_session_maker()() as session:
            return await resolve_release(session, country_code, release_version)

    async def get_current_release(
        self,
        country_code: str | None = None,
        release_version: str | None = None,
    ) -> ReleaseData:
        return release_data(await self._release(country_code, release_version))

    async def get_catalogues(
        self,
        country_code: str | None = None,
        domain: str | None = None,
        release_version: str | None = None,
    ) -> CatalogueListResponse:
        async with get_session_maker()() as session:
            release = await resolve_release(session, country_code, release_version)
            stmt = select(Catalogue).where(Catalogue.release_id == release.release_id)
            if domain is not None:
                stmt = stmt.where(Catalogue.domain == domain)
            rows = (await session.execute(stmt.order_by(Catalogue.code))).scalars().all()
        return CatalogueListResponse(
            release=release_data(release),
            catalogues=[catalogue_data(row) for row in rows],
        )

    async def get_values(
        self,
        catalogue_code: str,
        country_code: str | None = None,
        release_version: str | None = None,
        status: str | None = None,
        parent_code: str | None = None,
        relation_type: str | None = None,
        related_catalogue_code: str | None = None,
        related_value_code: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> CatalogueValuesResponse:
        parent = aliased(CatalogueValue)

        async with get_session_maker()() as session:
            release = await resolve_release(session, country_code, release_version)
            catalogue_stmt = select(Catalogue).where(
                Catalogue.release_id == release.release_id,
                Catalogue.code == catalogue_code,
            )
            catalogue = (await session.execute(catalogue_stmt)).scalars().first()
            if catalogue is None:
                raise CatalogueNotFoundError(f"Unknown catalogue: {catalogue_code}")

            filters = [CatalogueValue.catalogue_id == catalogue.catalogue_id]
            if status is not None:
                filters.append(CatalogueValue.status == status.upper())
            if search is not None:
                search_pattern = f"%{search.strip()}%"
                filters.append(
                    CatalogueValue.code.ilike(search_pattern)
                    | CatalogueValue.display_name.ilike(search_pattern)
                )
            if relation_type or related_catalogue_code or related_value_code:
                related_relation = aliased(CatalogueValueRelation)
                related_value = aliased(CatalogueValue)
                related_catalogue = aliased(Catalogue)
                relation_filters = [related_relation.source_value_id == CatalogueValue.catalogue_value_id]
                if relation_type is not None:
                    relation_filters.append(related_relation.relation_type == relation_type)
                if related_catalogue_code is not None:
                    relation_filters.append(related_catalogue.code == related_catalogue_code)
                if related_value_code is not None:
                    relation_filters.append(related_value.code == related_value_code)
                filters.append(
                    select(1)
                    .select_from(related_relation)
                    .join(
                        related_value,
                        related_relation.target_value_id == related_value.catalogue_value_id,
                    )
                    .join(
                        related_catalogue,
                        related_value.catalogue_id == related_catalogue.catalogue_id,
                    )
                    .where(*relation_filters)
                    .exists()
                )

            total_stmt = (
                select(func.count())
                .select_from(CatalogueValue)
                .outerjoin(parent, CatalogueValue.parent_value_id == parent.catalogue_value_id)
                .where(*filters)
            )
            if parent_code is not None:
                total_stmt = total_stmt.where(parent.code == parent_code)
            total = (await session.execute(total_stmt)).scalar_one()

            values_stmt = (
                select(CatalogueValue, parent.code)
                .outerjoin(parent, CatalogueValue.parent_value_id == parent.catalogue_value_id)
                .where(*filters)
                .order_by(CatalogueValue.sort_order.asc().nullslast(), CatalogueValue.code)
                .limit(page_size)
                .offset((page - 1) * page_size)
            )
            if parent_code is not None:
                values_stmt = values_stmt.where(parent.code == parent_code)
            rows = (await session.execute(values_stmt)).all()

            relations_by_source = await value_relations(
                session, [value.catalogue_value_id for value, _ in rows]
            )

        values = [
            catalogue_value_data(
                value,
                parent_code,
                relations_by_source[value.catalogue_value_id],
            )
            for value, parent_code in rows
        ]
        return CatalogueValuesResponse(
            release=release_data(release),
            catalogue=catalogue_data(catalogue),
            values=values,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_snapshot(
        self,
        country_code: str | None = None,
        release_version: str | None = None,
    ) -> CatalogueSnapshotResponse:
        """Return every catalogue value from one consistent active release."""
        parent = aliased(CatalogueValue)
        async with get_session_maker()() as session:
            release = await resolve_release(session, country_code, release_version)
            catalogue_rows = (
                (
                    await session.execute(
                        select(Catalogue)
                        .where(Catalogue.release_id == release.release_id)
                        .order_by(Catalogue.code)
                    )
                )
                .scalars()
                .all()
            )
            value_rows = (
                await session.execute(
                    select(CatalogueValue, parent.code, Catalogue.code)
                    .join(Catalogue, CatalogueValue.catalogue_id == Catalogue.catalogue_id)
                    .outerjoin(parent, CatalogueValue.parent_value_id == parent.catalogue_value_id)
                    .where(Catalogue.release_id == release.release_id)
                    .order_by(
                        Catalogue.code,
                        CatalogueValue.sort_order.asc().nullslast(),
                        CatalogueValue.code,
                    )
                )
            ).all()
            relations_by_source = await value_relations(
                session, [value.catalogue_value_id for value, _, _ in value_rows]
            )

        values_by_catalogue: dict[str, list[CatalogueValueData]] = {row.code: [] for row in catalogue_rows}
        for value, parent_code, catalogue_code in value_rows:
            values_by_catalogue[catalogue_code].append(
                catalogue_value_data(
                    value,
                    parent_code,
                    relations_by_source[value.catalogue_value_id],
                )
            )

        return CatalogueSnapshotResponse(
            release=release_data(release),
            catalogues=[
                CatalogueSnapshotData(
                    **catalogue_data(row).model_dump(),
                    values=values_by_catalogue[row.code],
                )
                for row in catalogue_rows
            ],
        )
