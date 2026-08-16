import asyncio
import logging
import re
import time
import uuid
from collections.abc import Callable

from fastapi import Response
from openg2p_fastapi_common.controller import BaseController
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    multiprocess,
)
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .config import Settings
from .engine import get_engine

LOGGER = logging.getLogger("openg2p.catalogue.observability")
SAFE_REQUEST_ID = re.compile(r"[^A-Za-z0-9._:-]")

HTTP_REQUESTS = Counter(
    "catalogue_http_requests_total",
    "Catalogue API HTTP requests.",
    ("method", "route", "status_code"),
)
HTTP_DURATION = Histogram(
    "catalogue_http_request_duration_seconds",
    "Catalogue API HTTP request duration.",
    ("method", "route"),
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
READINESS_CHECKS = Counter(
    "catalogue_readiness_checks_total",
    "Catalogue API readiness checks.",
    ("result",),
)
READINESS_DURATION = Histogram(
    "catalogue_readiness_check_duration_seconds",
    "Catalogue API readiness check duration.",
)
ACTIVE_RELEASE_TIMESTAMP = Gauge(
    "catalogue_active_release_timestamp_seconds",
    "Activation time of the current catalogue release.",
    ("country_code",),
    multiprocess_mode="max",
)
LAST_SUCCESSFUL_IMPORT_TIMESTAMP = Gauge(
    "catalogue_last_successful_import_timestamp_seconds",
    "Completion time of the latest successful or skipped SQL import.",
    ("country_code",),
    multiprocess_mode="max",
)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Record bounded-cardinality request metrics and structured request logs."""

    async def dispatch(self, request: Request, call_next: Callable):
        started = time.monotonic()
        request_id = _request_id(request.headers.get("X-Request-ID"))
        status_code = 500
        response = None
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            duration = time.monotonic() - started
            route = request.scope.get("route")
            route_path = getattr(route, "path", "unmatched")
            HTTP_REQUESTS.labels(request.method, route_path, str(status_code)).inc()
            HTTP_DURATION.labels(request.method, route_path).observe(duration)
            LOGGER.info(
                "catalogue_http_request_completed",
                extra={
                    "event": "catalogue_http_request_completed",
                    "request_id": request_id,
                    "http_method": request.method,
                    "http_route": route_path,
                    "http_status_code": status_code,
                    "duration_ms": round(duration * 1000, 3),
                    "country_code": request.query_params.get("country_code"),
                    "requested_release_version": request.query_params.get("release_version"),
                    "catalogue_release_version": (
                        response.headers.get("X-Catalogue-Release") if response is not None else None
                    ),
                },
            )


class ObservabilityController(BaseController):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.router.tags += ["Operations"]
        self.router.add_api_route("/health/live", self.live, methods=["GET"])
        self.router.add_api_route("/health/ready", self.ready, methods=["GET"])
        self.router.add_api_route("/metrics", self.metrics, methods=["GET"], include_in_schema=False)

    async def live(self):
        return {"status": "alive"}

    async def ready(self):
        started = time.monotonic()
        config = Settings.get_config()
        result = "not_ready"
        try:
            health = await asyncio.wait_for(
                _database_health(config.default_country_code),
                timeout=config.readiness_timeout_seconds,
            )
            schema_ready = health["schema_version"] == config.expected_schema_version
            if schema_ready:
                result = "ready"
                status_code = 200
            else:
                status_code = 503
            body = {
                "status": result,
                "checks": {
                    "database": "up",
                    "schema": "current" if schema_ready else "mismatch",
                },
                "schema_version": health["schema_version"],
                "expected_schema_version": config.expected_schema_version,
            }
        # Readiness must turn every dependency failure into 503 instead of
        # letting an unexpected driver failure become an unhandled response.
        except Exception as error:  # noqa: BLE001
            status_code = 503
            body = {
                "status": result,
                "checks": {"database": "down", "schema": "unknown"},
                "expected_schema_version": config.expected_schema_version,
            }
            LOGGER.warning(
                "catalogue_readiness_failed",
                extra={"event": "catalogue_readiness_failed", "error_type": type(error).__name__},
            )
        finally:
            READINESS_CHECKS.labels(result).inc()
            READINESS_DURATION.observe(time.monotonic() - started)
        return JSONResponse(body, status_code=status_code)

    async def metrics(self):
        return Response(content=_metrics_payload(), headers={"Content-Type": CONTENT_TYPE_LATEST})


async def _database_health(country_code: str) -> dict[str, str | None]:
    async with get_engine().connect() as connection:
        schema_version = (
            await connection.execute(
                text("SELECT version FROM catalogue_schema_migrations ORDER BY version::bigint DESC LIMIT 1")
            )
        ).scalar_one_or_none()
        active_release_timestamp = (
            await connection.execute(
                text(
                    "SELECT EXTRACT(EPOCH FROM activated_at) "
                    "FROM catalogue_releases WHERE country_code = :country_code AND status = 'ACTIVE'"
                ),
                {"country_code": country_code},
            )
        ).scalar_one_or_none()
        successful_import_timestamp = (
            await connection.execute(
                text(
                    "SELECT EXTRACT(EPOCH FROM MAX(finished_at)) FROM catalogue_import_runs "
                    "WHERE country_code = :country_code AND status IN ('PUBLISHED', 'SKIPPED')"
                ),
                {"country_code": country_code},
            )
        ).scalar_one_or_none()

    ACTIVE_RELEASE_TIMESTAMP.labels(country_code).set(float(active_release_timestamp or 0))
    LAST_SUCCESSFUL_IMPORT_TIMESTAMP.labels(country_code).set(float(successful_import_timestamp or 0))
    return {"schema_version": schema_version}


def _metrics_payload() -> bytes:
    import os

    if os.environ.get("PROMETHEUS_MULTIPROC_DIR") or os.environ.get("prometheus_multiproc_dir"):
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
        return generate_latest(registry)
    return generate_latest(REGISTRY)


def _request_id(supplied: str | None) -> str:
    if supplied:
        normalized = SAFE_REQUEST_ID.sub("", supplied)[:128]
        if normalized:
            return normalized
    return str(uuid.uuid4())
