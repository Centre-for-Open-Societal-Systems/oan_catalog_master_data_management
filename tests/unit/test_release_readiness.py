import os
import subprocess
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_artifact_versions_are_aligned():
    result = subprocess.run(
        [sys.executable, "scripts/check-release-version.py", "--expected", "0.2.0"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "All release artifacts use version 0.2.0" in result.stdout


def test_compose_orders_database_migration_seed_and_api():
    compose = yaml.safe_load((PROJECT_ROOT / "compose.yaml").read_text(encoding="utf-8"))
    services = compose["services"]

    assert services["migrate"]["depends_on"]["postgres"]["condition"] == "service_healthy"
    assert services["seed"]["depends_on"]["migrate"]["condition"] == "service_completed_successfully"
    assert services["api"]["depends_on"]["seed"]["condition"] == "service_completed_successfully"
    assert services["api"]["environment"]["CATALOGUE_API_DEV_MODE"] == "true"
    assert "openg2p_catalogue_service.dev_main:app" in services["api"]["command"]
    assert services["api"]["image"] == "openg2p-catalogue-api:local"


def test_consumer_compose_uses_one_release_image_for_all_lifecycle_roles():
    compose = yaml.safe_load((PROJECT_ROOT / "compose.consumer.yaml").read_text(encoding="utf-8"))
    services = compose["services"]

    release_image = "${CATALOGUE_IMAGE:?Set CATALOGUE_IMAGE}:${CATALOGUE_IMAGE_TAG:-0.2.0}"
    assert services["migrate"]["image"] == release_image
    assert services["seed"]["image"] == release_image
    assert services["api"]["image"] == release_image
    assert services["migrate"]["command"][:2] == [
        "python",
        "/migration/migrate_database.py",
    ]
    assert services["seed"]["command"][:2] == ["python", "/seed/run_sql_seeds.py"]


def test_unified_release_dockerfile_contains_api_migrations_and_seed_bundle():
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "COPY catalogue-api /src/catalogue-api" in dockerfile
    assert "COPY scripts/migrations /migration/sql" in dockerfile
    assert "COPY scripts/seed_db_sql /seed/sql" in dockerfile
    assert "COPY docker/db-seed/run_sql_seeds.py /seed/run_sql_seeds.py" in dockerfile
    assert "ARG CATALOGUE_VERSION=0.2.0" in dockerfile
    assert 'org.opencontainers.image.version="${CATALOGUE_VERSION}"' in dockerfile
    assert "FASTAPI_COMMON_REF=develop" not in dockerfile
    assert "IAM_SERVICE_REF=1.3" not in dockerfile


def test_unified_image_publisher_is_explicit_and_version_guarded():
    source = (PROJECT_ROOT / "scripts" / "publish-unified-image.sh").read_text(encoding="utf-8")
    assert "check-release-version.py" in source
    assert 'docker build "${build_args[@]}"' in source
    assert 'docker push "${versioned_image}"' in source
    assert 'push_latest="false"' in source


def test_development_entry_point_is_explicitly_gated():
    environment = os.environ.copy()
    environment.pop("CATALOGUE_API_DEV_MODE", None)
    result = subprocess.run(
        [sys.executable, "-c", "import openg2p_catalogue_service.dev_main"],
        cwd=PROJECT_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "CATALOGUE_API_DEV_MODE=true" in result.stderr


def test_release_workflow_contains_security_and_distribution_gates():
    workflow = (PROJECT_ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert "check-release-version.py" in workflow
    assert "anchore/sbom-action" in workflow
    assert "aquasecurity/trivy-action" in workflow
    assert "gh-action-pypi-publish" in workflow
    assert "helm push" in workflow


def test_restore_script_requires_explicit_confirmation():
    source = (PROJECT_ROOT / "scripts" / "restore-database.sh").read_text(encoding="utf-8")
    assert "CONFIRM_CATALOGUE_RESTORE:-" in source
    assert '!= "RESTORE"' in source
