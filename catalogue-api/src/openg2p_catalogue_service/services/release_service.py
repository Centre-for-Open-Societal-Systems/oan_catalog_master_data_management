from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import Settings
from ..models import CatalogueRelease
from ..schemas import ReleaseData


class ResourceNotFoundError(LookupError):
    pass


def release_data(row: CatalogueRelease) -> ReleaseData:
    return ReleaseData(
        country_code=row.country_code,
        version=row.version,
        schema_version=row.schema_version,
        checksum=row.checksum,
        source=row.source,
        status=row.status,
        activated_at=row.activated_at,
    )


async def resolve_release(
    session: AsyncSession,
    country_code: str | None = None,
    release_version: str | None = None,
) -> CatalogueRelease:
    """Resolve an active release or an explicitly pinned published release."""
    normalized_country = (country_code or Settings.get_config().default_country_code).upper()
    stmt = select(CatalogueRelease).where(CatalogueRelease.country_code == normalized_country)
    if release_version is None:
        stmt = stmt.where(CatalogueRelease.status == "ACTIVE")
    else:
        stmt = stmt.where(
            CatalogueRelease.version == release_version,
            CatalogueRelease.status.in_(("ACTIVE", "RETIRED")),
        )

    release = (await session.execute(stmt)).scalars().first()
    if release is None:
        qualifier = "active" if release_version is None else f"published version {release_version}"
        raise ResourceNotFoundError(f"No {qualifier} catalogue release for {normalized_country}")
    return release
