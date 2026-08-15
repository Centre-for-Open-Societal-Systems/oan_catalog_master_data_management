from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHART = ROOT / "deployments" / "charts" / "openg2p-catalogue"


def test_catalogue_api_discovery_alias_is_enabled_by_default() -> None:
    values = (CHART / "values.yaml").read_text(encoding="utf-8")

    assert "discovery:" in values
    assert "enabled: true" in values
    assert "name: catalogue-api" in values


def test_discovery_service_selects_the_catalogue_api_pods() -> None:
    service = (CHART / "templates" / "catalogue-api" / "service.yaml").read_text(
        encoding="utf-8"
    )

    assert '.Values.catalogueAPI.service.discovery.enabled' in service
    assert '.Values.catalogueAPI.service.discovery.name' in service
    assert 'include "catalogue.selectorLabels" .' in service
    assert "app.kubernetes.io/component: service-discovery" in service


def test_chart_documents_cross_namespace_discovery_requirements() -> None:
    readme = (CHART / "README.md").read_text(encoding="utf-8")

    assert "catalogue-api.<catalogue-namespace>.svc.cluster.local" in readme
    assert "networkPolicy.ingressNamespaces" in readme
    assert "catalogue-values" in readme


def test_unified_image_installs_the_catalogue_api_package() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "COPY catalogue-api /src/catalogue-api" in dockerfile
    assert "pip install --no-cache-dir psycopg2-binary PyYAML /src/catalogue-api" in dockerfile


def test_widget_handoff_documents_live_reads_and_opt_in_sync() -> None:
    guide = (ROOT / "docs" / "widget-integration.md").read_text(encoding="utf-8")

    assert "service: catalogue" in guide
    assert "path: /v1/catalogue-values" in guide
    assert "relation_type: category" in guide
    assert "relation_type: crop" in guide
    assert "Attribute synchronization is not part of the default widget path" in guide
