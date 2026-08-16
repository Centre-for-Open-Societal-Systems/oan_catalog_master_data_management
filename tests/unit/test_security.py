from pathlib import Path

import httpx
import pytest
import yaml
from fastapi import FastAPI
from iam_core.user_auth.decorators import get_required_permissions, require_permissions
from iam_core.user_auth.middleware import ValidateAndRefreshTokenMiddleware
from openg2p_catalogue_service.controllers import (
    CatalogueController,
    GeographyController,
    LivestockController,
    SeedVarietyController,
    StatisticsController,
)
from openg2p_catalogue_service.security import (
    CATALOGUE_READ_PERMISSION,
    GEOGRAPHY_READ_PERMISSION,
    PUBLIC_PATHS,
    SNAPSHOT_READ_PERMISSION,
    STATISTICS_READ_PERMISSION,
    CataloguePermissionMiddleware,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_every_registry_handler_has_an_explicit_permission():
    expected = {
        CatalogueController.get_current_release: {CATALOGUE_READ_PERMISSION},
        CatalogueController.get_catalogues: {CATALOGUE_READ_PERMISSION},
        CatalogueController.get_catalogue_values: {CATALOGUE_READ_PERMISSION},
        CatalogueController.get_catalogue_options: {CATALOGUE_READ_PERMISSION},
        CatalogueController.get_current_snapshot: {SNAPSHOT_READ_PERMISSION},
        GeographyController.get_levels: {GEOGRAPHY_READ_PERMISSION},
        GeographyController.get_units: {GEOGRAPHY_READ_PERMISSION},
        GeographyController.get_unit: {GEOGRAPHY_READ_PERMISSION},
        LivestockController.get_species: {CATALOGUE_READ_PERMISSION},
        LivestockController.get_breeds: {CATALOGUE_READ_PERMISSION},
        LivestockController.get_reference_data: {CATALOGUE_READ_PERMISSION},
        LivestockController.get_registry_entries: {CATALOGUE_READ_PERMISSION},
        LivestockController.get_registry_validation: {CATALOGUE_READ_PERMISSION},
        SeedVarietyController.get_seed_varieties: {CATALOGUE_READ_PERMISSION},
        SeedVarietyController.get_seed_variety: {CATALOGUE_READ_PERMISSION},
        StatisticsController.get_livestock_population: {STATISTICS_READ_PERMISSION},
        StatisticsController.get_seed_demand_summary: {STATISTICS_READ_PERMISSION},
        StatisticsController.get_seed_demand_trends: {STATISTICS_READ_PERMISSION},
        StatisticsController.get_seed_demand_by_crop: {STATISTICS_READ_PERMISSION},
    }

    assert all(get_required_permissions(handler) == permissions for handler, permissions in expected.items())


def test_permission_middleware_cannot_be_switched_back_to_allow_by_default():
    middleware = CataloguePermissionMiddleware(lambda scope, receive, send: None)
    assert middleware._allow_by_default is False
    assert PUBLIC_PATHS == {"/ping", "/health/live", "/health/ready", "/metrics"}


@pytest.mark.asyncio
async def test_default_deny_runtime_behavior_and_public_health_exception():
    app = FastAPI()

    @app.get("/ping")
    async def ping():
        return {"message": "pong"}

    @app.get("/unmarked")
    async def unmarked():
        return {"unsafe": True}

    @app.get("/protected")
    @require_permissions(CATALOGUE_READ_PERMISSION)
    async def protected():
        return {"protected": True}

    app.add_middleware(CataloguePermissionMiddleware, client_id="catalogue-service")
    app.add_middleware(ValidateAndRefreshTokenMiddleware)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/ping")).status_code == 200
        assert (await client.get("/unmarked")).status_code == 401
        assert (await client.get("/protected")).status_code == 401


def test_helm_security_defaults_and_images_are_non_root():
    values = yaml.safe_load(
        (PROJECT_ROOT / "deployments" / "charts" / "openg2p-catalogue" / "values.yaml").read_text(
            encoding="utf-8"
        )
    )
    pod_security = values["catalogueAPI"]["podSecurityContext"]
    container_security = values["catalogueAPI"]["containerSecurityContext"]

    assert values["networkPolicy"]["enabled"] is True
    assert pod_security["runAsNonRoot"] is True
    assert pod_security["seccompProfile"]["type"] == "RuntimeDefault"
    assert container_security["allowPrivilegeEscalation"] is False
    assert container_security["readOnlyRootFilesystem"] is True
    assert container_security["capabilities"]["drop"] == ["ALL"]

    for dockerfile in (
        PROJECT_ROOT / "docker" / "catalogue-api" / "Dockerfile",
        PROJECT_ROOT / "docker" / "db-migration" / "Dockerfile",
        PROJECT_ROOT / "docker" / "db-seed" / "Dockerfile",
        PROJECT_ROOT / "docker" / "db-seed" / "Dockerfile.sql",
    ):
        assert "USER 10001:10001" in dockerfile.read_text(encoding="utf-8")


def test_auth_configuration_contains_no_default_allow_escape_hatch():
    main_source = (
        PROJECT_ROOT / "catalogue-api" / "src" / "openg2p_catalogue_service" / "main.py"
    ).read_text(encoding="utf-8")
    assert "allow_by_default=True" not in main_source
    assert "CataloguePermissionMiddleware" in main_source
