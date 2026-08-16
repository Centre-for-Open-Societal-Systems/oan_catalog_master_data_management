from pydantic import BaseModel

from .catalogue import CatalogueSnapshotData, ReleaseData
from .geography import GeographySnapshotData
from .statistics import AgricultureStatisticsSnapshotData


class MasterDataSnapshotResponse(BaseModel):
    """Complete registry projection from exactly one immutable release."""

    release: ReleaseData
    catalogues: list[CatalogueSnapshotData]
    geography: GeographySnapshotData
    agriculture_statistics: AgricultureStatisticsSnapshotData
