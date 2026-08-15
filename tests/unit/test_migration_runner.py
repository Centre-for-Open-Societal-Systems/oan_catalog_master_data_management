import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = PROJECT_ROOT / "docker" / "db-migration" / "migrate_database.py"
MIGRATIONS_PATH = PROJECT_ROOT / "scripts" / "migrations"
SPEC = importlib.util.spec_from_file_location("migrate_database", RUNNER_PATH)
runner = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


def test_discovers_ordered_immutable_migrations():
    migrations = runner.discover_migrations(MIGRATIONS_PATH)

    assert [item.version for item in migrations] == [
        "001",
        "002",
        "003",
        "004",
        "005",
        "006",
        "007",
        "008",
        "009",
        "010",
        "011",
        "012",
        "013",
        "014",
    ]
    assert all(item.checksum.startswith("sha256:") for item in migrations)
    assert all("BEGIN;" not in item.sql and not item.sql.endswith("COMMIT;") for item in migrations)


def test_helm_expected_version_matches_latest_migration():
    migrations = runner.discover_migrations(MIGRATIONS_PATH)
    values = yaml.safe_load(
        (PROJECT_ROOT / "deployments" / "charts" / "openg2p-catalogue" / "values.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert values["schemaMigration"]["expectedVersion"] == migrations[-1].version


def test_rejects_invalid_filename(tmp_path):
    (tmp_path / "first.sql").write_text("BEGIN; SELECT 1; COMMIT;", encoding="utf-8")

    with pytest.raises(runner.MigrationError, match="Invalid migration filename"):
        runner.discover_migrations(tmp_path)


def test_rejects_duplicate_version(tmp_path):
    (tmp_path / "001_first.sql").write_text("BEGIN; SELECT 1; COMMIT;", encoding="utf-8")
    (tmp_path / "001_second.sql").write_text("BEGIN; SELECT 2; COMMIT;", encoding="utf-8")

    with pytest.raises(runner.MigrationError, match="Duplicate migration version"):
        runner.discover_migrations(tmp_path)


def test_rejects_a_gap_in_migration_versions(tmp_path):
    (tmp_path / "001_first.sql").write_text("BEGIN; SELECT 1; COMMIT;", encoding="utf-8")
    (tmp_path / "003_third.sql").write_text("BEGIN; SELECT 3; COMMIT;", encoding="utf-8")

    with pytest.raises(runner.MigrationError, match="contiguous"):
        runner.discover_migrations(tmp_path)


def test_rejects_missing_transaction_wrapper(tmp_path):
    (tmp_path / "001_first.sql").write_text("SELECT 1;", encoding="utf-8")

    with pytest.raises(runner.MigrationError, match="BEGIN/COMMIT"):
        runner.discover_migrations(tmp_path)


def test_rejects_changed_applied_migration():
    migration = runner.discover_migrations(MIGRATIONS_PATH)[0]
    history = [
        {
            "version": migration.version,
            "filename": migration.filename,
            "checksum": "sha256:changed",
        }
    ]

    with pytest.raises(runner.MigrationError, match="Checksum mismatch"):
        runner.validate_history([migration], history)


def test_rejects_deployment_version_that_does_not_match_bundle():
    migrations = runner.discover_migrations(MIGRATIONS_PATH)

    with pytest.raises(runner.MigrationError, match="does not match expected"):
        runner.run(None, migrations, expected_version="999")
