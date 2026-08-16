from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from openg2p_fastapi_common.app import Initializer as BaseInitializer

from .controllers import (
    CatalogueController,
    CropTaxonomyController,
    GeographyController,
    LivestockController,
    SeedVarietyController,
    StatisticsController,
)
from .observability import ObservabilityController
from .services import (
    CatalogueService,
    CropTaxonomyService,
    GeographyService,
    LivestockService,
    SeedVarietyService,
    SnapshotService,
    StatisticsService,
)


class Initializer(BaseInitializer):
    def initialize(self, **kwargs):
        super().initialize(**kwargs)
        CatalogueService()
        CropTaxonomyService()
        GeographyService()
        LivestockService()
        SeedVarietyService()
        StatisticsService()
        SnapshotService()
        CatalogueController().post_init()
        CropTaxonomyController().post_init()
        GeographyController().post_init()
        LivestockController().post_init()
        SeedVarietyController().post_init()
        StatisticsController().post_init()
        ObservabilityController().post_init()
        FastAPICache.init(InMemoryBackend(), prefix="catalogue-api-cache")
