from collections.abc import Callable
from typing import Any

from iam_core.user_auth.middleware import ResolvePermissionMiddleware
from starlette.requests import Request

CATALOGUE_READ_PERMISSION = "catalogue.read"
GEOGRAPHY_READ_PERMISSION = "geography.read"
STATISTICS_READ_PERMISSION = "statistics.read"
SNAPSHOT_READ_PERMISSION = "snapshot.read"

PUBLIC_PATHS = frozenset({"/ping", "/health/live", "/health/ready", "/metrics"})


class CataloguePermissionMiddleware(ResolvePermissionMiddleware):
    """Default-deny IAM authorization with explicit operational exceptions."""

    def __init__(self, app, **kwargs):
        kwargs["allow_by_default"] = False
        super().__init__(app, **kwargs)

    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]):
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)
        return await super().dispatch(request, call_next)
