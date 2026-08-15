import logging
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
import yaml
from fastapi import FastAPI
from openg2p_catalogue_service import observability
from openg2p_catalogue_service.observability import ObservabilityController, ObservabilityMiddleware

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def operations_app():
    app = FastAPI()
    app.include_router(ObservabilityController().router)
    app.add_middleware(ObservabilityMiddleware)
    return app


@pytest.mark.asyncio
async def test_liveness_and_metrics_are_dependency_free_and_include_request_metrics():
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=operations_app()), base_url="http://test"
    ) as client:
        live = await client.get("/health/live", headers={"X-Request-ID": "registry/request 42"})
        metrics = await client.get("/metrics")

    assert live.status_code == 200
    assert live.json() == {"status": "alive"}
    assert live.headers["x-request-id"] == "registryrequest42"
    assert metrics.status_code == 200
    assert "catalogue_http_requests_total" in metrics.text
    assert 'route="/health/live"' in metrics.text


@pytest.mark.asyncio
async def test_readiness_reports_current_schema(monkeypatch):
    async def healthy_database(_country_code):
        return {"schema_version": "005"}

    monkeypatch.setattr(observability, "_database_health", healthy_database)
    monkeypatch.setattr(
        observability.Settings,
        "get_config",
        lambda: SimpleNamespace(
            default_country_code="ETH",
            expected_schema_version="005",
            readiness_timeout_seconds=1,
        ),
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=operations_app()), base_url="http://test"
    ) as client:
        response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["checks"] == {"database": "up", "schema": "current"}


@pytest.mark.asyncio
async def test_readiness_rejects_schema_mismatch_and_database_failure(monkeypatch):
    config = SimpleNamespace(
        default_country_code="ETH",
        expected_schema_version="005",
        readiness_timeout_seconds=1,
    )
    monkeypatch.setattr(observability.Settings, "get_config", lambda: config)

    async def old_schema(_country_code):
        return {"schema_version": "003"}

    monkeypatch.setattr(observability, "_database_health", old_schema)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=operations_app()), base_url="http://test"
    ) as client:
        mismatch = await client.get("/health/ready")
    assert mismatch.status_code == 503
    assert mismatch.json()["checks"] == {"database": "up", "schema": "mismatch"}

    async def unavailable(_country_code):
        raise RuntimeError("secret database detail")

    monkeypatch.setattr(observability, "_database_health", unavailable)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=operations_app()), base_url="http://test"
    ) as client:
        failed = await client.get("/health/ready")
    assert failed.status_code == 503
    assert failed.json()["checks"] == {"database": "down", "schema": "unknown"}
    assert "secret database detail" not in failed.text


@pytest.mark.asyncio
async def test_request_log_contains_bounded_operational_context(caplog):
    caplog.set_level(logging.INFO, logger="openg2p.catalogue.observability")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=operations_app()), base_url="http://test"
    ) as client:
        await client.get("/health/live?country_code=ETH&release_version=v1")

    record = next(record for record in caplog.records if record.msg == "catalogue_http_request_completed")
    assert record.event == "catalogue_http_request_completed"
    assert record.http_route == "/health/live"
    assert record.http_status_code == 200
    assert record.country_code == "ETH"
    assert record.requested_release_version == "v1"
    assert record.duration_ms >= 0


def test_chart_configures_dependency_aware_probes_and_optional_prometheus_resources():
    chart = PROJECT_ROOT / "deployments" / "charts" / "openg2p-catalogue"
    values = yaml.safe_load((chart / "values.yaml").read_text(encoding="utf-8"))
    deployment = (chart / "templates" / "catalogue-api" / "deployment.yaml").read_text(encoding="utf-8")
    virtual_service = (chart / "templates" / "catalogue-api" / "virtualservice.yaml").read_text(
        encoding="utf-8"
    )

    assert values["monitoring"]["serviceMonitor"]["enabled"] is False
    assert values["monitoring"]["prometheusRule"]["enabled"] is False
    assert "path: /health/live" in deployment
    assert "path: /health/ready" in deployment
    assert "PROMETHEUS_MULTIPROC_DIR" in deployment
    assert "exact: /metrics" in virtual_service
    assert (chart / "templates" / "servicemonitor.yaml").is_file()
    assert (chart / "templates" / "prometheusrule.yaml").is_file()
