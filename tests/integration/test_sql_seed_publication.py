import importlib.util
import os
import shutil
import sys
from pathlib import Path

import psycopg2
import pytest
import yaml

TEST_DSN = os.environ.get("CATALOGUE_TEST_DB_DSN")
pytestmark = pytest.mark.skipif(
    not TEST_DSN,
    reason="CATALOGUE_TEST_DB_DSN must point to a disposable PostgreSQL database",
)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = PROJECT_ROOT / "docker" / "db-seed" / "run_sql_seeds.py"
MIGRATION_RUNNER_PATH = PROJECT_ROOT / "docker" / "db-migration" / "migrate_database.py"
MIGRATIONS_PATH = PROJECT_ROOT / "scripts" / "migrations"
MANIFEST_PATH = PROJECT_ROOT / "scripts" / "seed_db_sql" / "manifest.yaml"
SPEC = importlib.util.spec_from_file_location("run_sql_seeds", RUNNER_PATH)
runner = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(runner)
MIGRATION_SPEC = importlib.util.spec_from_file_location("publication_migration_runner", MIGRATION_RUNNER_PATH)
migration_runner = importlib.util.module_from_spec(MIGRATION_SPEC)
assert MIGRATION_SPEC.loader is not None
sys.modules[MIGRATION_SPEC.name] = migration_runner
MIGRATION_SPEC.loader.exec_module(migration_runner)


def rebuild_schema(conn):
    with conn.cursor() as cursor:
        cursor.execute("DROP SCHEMA public CASCADE")
        cursor.execute("CREATE SCHEMA public")
    conn.commit()
    migration_runner.run(
        conn,
        migration_runner.discover_migrations(MIGRATIONS_PATH),
        expected_version="014",
    )


def scalar(conn, statement):
    with conn.cursor() as cursor:
        cursor.execute(statement)
        return cursor.fetchone()[0]


def publish(conn, manifest_path=MANIFEST_PATH, trigger="TEST"):
    manifest = runner.load_manifest(manifest_path)
    scripts = runner.validate_manifest(manifest, manifest_path)
    checksum = runner.manifest_checksum(manifest_path, scripts)
    runner.run(conn, manifest, scripts, checksum, trigger)
    return manifest, checksum


def test_sql_sources_publish_and_then_skip_unchanged_release():
    conn = psycopg2.connect(TEST_DSN)
    try:
        rebuild_schema(conn)
        publish(conn, trigger="MANUAL")

        assert scalar(conn, "SELECT count(*) FROM catalogue_releases WHERE status='ACTIVE'") == 1
        assert scalar(conn, "SELECT count(*) FROM catalogue_schema_migrations") == 14
        assert scalar(conn, "SELECT count(*) FROM catalogues") == 15
        assert scalar(conn, "SELECT count(*) FROM catalogue_values") == 3400
        assert scalar(conn, "SELECT count(*) FROM catalogue_value_relations") == 5720
        assert scalar(conn, "SELECT count(*) FROM g2p_crop") == 150
        assert (
            scalar(
                conn,
                "SELECT count(*) FROM g2p_crop WHERE record_source='WORKBOOK_ADDITION'",
            )
            == 21
        )
        assert scalar(conn, "SELECT sum(varieties_count) FROM g2p_crop") == 952
        assert scalar(conn, "SELECT count(*) FROM g2p_crop_taxonomy_category") == 8
        assert scalar(conn, "SELECT count(*) FROM g2p_crop_taxonomy_type") == 119
        assert scalar(conn, "SELECT count(*) FROM g2p_crop_variety") == 1359
        assert scalar(conn, "SELECT count(*) FROM g2p_crop_variety_source_record") == 1360
        assert scalar(conn, "SELECT count(*) FROM g2p_crop_characteristic_definition") == 359
        assert scalar(conn, "SELECT count(*) FROM g2p_crop_variety_characteristic") == 10322
        assert scalar(conn, "SELECT count(*) FROM crop_variety_source_records") == 1360
        assert scalar(conn, "SELECT count(*) FROM crop_characteristic_definitions") == 359
        assert scalar(conn, "SELECT count(*) FROM crop_variety_characteristics") == 10322
        assert scalar(conn, "SELECT count(*) FROM g2p_seed_variety_source_record") == 902
        assert scalar(conn, "SELECT count(*) FROM seed_variety_source_records") == 902
        assert (
            scalar(
                conn,
                "SELECT count(*) FROM seed_variety_source_records "
                "WHERE crop_value_id IS NOT NULL "
                "AND consolidated_crop_variety_value_id IS NOT NULL",
            )
            == 902
        )
        assert scalar(conn, "SELECT count(*) FROM g2p_livestock_type") == 5
        assert scalar(conn, "SELECT count(*) FROM g2p_livestock_breed") == 94
        assert scalar(conn, "SELECT count(*) FROM g2p_livestock_gender") == 4
        assert scalar(conn, "SELECT count(*) FROM g2p_livestock_location_type") == 3
        assert scalar(conn, "SELECT count(*) FROM g2p_livestock_body_condition") == 5
        assert scalar(conn, "SELECT count(*) FROM g2p_livestock_production_type") == 13
        assert scalar(conn, "SELECT count(*) FROM g2p_livestock_production_type_species") == 34
        assert scalar(conn, "SELECT count(*) FROM g2p_livestock_record_status") == 6
        assert (
            scalar(
                conn,
                """
                SELECT count(*)
                  FROM catalogue_value_relations relation
                  JOIN catalogue_values source
                    ON source.catalogue_value_id = relation.source_value_id
                  JOIN catalogues catalogue
                    ON catalogue.catalogue_id = source.catalogue_id
                 WHERE catalogue.code = 'livestock_breed'
                   AND relation.relation_type = 'species'
                """,
            )
            == 94
        )
        assert (
            scalar(
                conn,
                """
                SELECT count(*)
                  FROM catalogue_value_relations relation
                  JOIN catalogue_values source
                    ON source.catalogue_value_id = relation.source_value_id
                  JOIN catalogues catalogue
                    ON catalogue.catalogue_id = source.catalogue_id
                 WHERE catalogue.code = 'livestock_production_type'
                   AND relation.relation_type = 'valid_for_species'
                """,
            )
            == 34
        )
        assert (
            scalar(
                conn,
                """
                SELECT count(*)
                  FROM catalogue_value_relations relation
                  JOIN catalogue_values source
                    ON source.catalogue_value_id = relation.source_value_id
                  JOIN catalogues catalogue
                    ON catalogue.catalogue_id = source.catalogue_id
                 WHERE catalogue.code = 'livestock_location_type'
                   AND relation.relation_type = 'ecological_zone'
                """,
            )
            == 3
        )
        assert (
            scalar(
                conn,
                "SELECT count(*) FROM seed_variety_source_records WHERE match_status='MATCHED'",
            )
            == 309
        )
        assert (
            scalar(
                conn,
                """
                SELECT count(*)
                  FROM catalogue_value_relations relation
                  JOIN catalogue_values source
                    ON source.catalogue_value_id = relation.source_value_id
                  JOIN catalogues source_catalogue
                    ON source_catalogue.catalogue_id = source.catalogue_id
                  JOIN catalogue_values target
                    ON target.catalogue_value_id = relation.target_value_id
                  JOIN catalogues target_catalogue
                    ON target_catalogue.catalogue_id = target.catalogue_id
                 WHERE source_catalogue.code = 'crop'
                   AND relation.relation_type = 'category'
                   AND target_catalogue.code = 'crop_category'
                """,
            )
            == 122
        )
        assert (
            scalar(
                conn,
                """
                SELECT count(*)
                  FROM catalogue_value_relations relation
                  JOIN catalogue_values source
                    ON source.catalogue_value_id = relation.source_value_id
                  JOIN catalogues source_catalogue
                    ON source_catalogue.catalogue_id = source.catalogue_id
                  JOIN catalogue_values target
                    ON target.catalogue_value_id = relation.target_value_id
                  JOIN catalogues target_catalogue
                    ON target_catalogue.catalogue_id = target.catalogue_id
                 WHERE source_catalogue.code = 'crop_type'
                   AND relation.relation_type = 'category'
                   AND target_catalogue.code = 'crop_category'
                """,
            )
            == 119
        )
        assert (
            scalar(
                conn,
                """
                SELECT count(*)
                  FROM catalogue_value_relations relation
                  JOIN catalogue_values source
                    ON source.catalogue_value_id = relation.source_value_id
                  JOIN catalogues source_catalogue
                    ON source_catalogue.catalogue_id = source.catalogue_id
                  JOIN catalogue_values target
                    ON target.catalogue_value_id = relation.target_value_id
                  JOIN catalogues target_catalogue
                    ON target_catalogue.catalogue_id = target.catalogue_id
                 WHERE source_catalogue.code = 'crop_type'
                   AND relation.relation_type = 'category'
                   AND target_catalogue.code = 'crop_taxonomy_category'
                """,
            )
            == 119
        )
        assert (
            scalar(
                conn,
                """
                SELECT count(*)
                  FROM catalogue_value_relations relation
                  JOIN catalogue_values source
                    ON source.catalogue_value_id = relation.source_value_id
                  JOIN catalogues source_catalogue
                    ON source_catalogue.catalogue_id = source.catalogue_id
                  JOIN catalogue_values target
                    ON target.catalogue_value_id = relation.target_value_id
                  JOIN catalogues target_catalogue
                    ON target_catalogue.catalogue_id = target.catalogue_id
                 WHERE source_catalogue.code = 'crop_variety'
                   AND relation.relation_type = 'crop_type'
                   AND target_catalogue.code = 'crop_type'
                """,
            )
            == 1359
        )
        assert (
            scalar(
                conn,
                """
                SELECT count(*)
                  FROM catalogue_value_relations relation
                  JOIN catalogue_values source
                    ON source.catalogue_value_id = relation.source_value_id
                  JOIN catalogues source_catalogue
                    ON source_catalogue.catalogue_id = source.catalogue_id
                  JOIN catalogue_values target
                    ON target.catalogue_value_id = relation.target_value_id
                  JOIN catalogues target_catalogue
                    ON target_catalogue.catalogue_id = target.catalogue_id
                 WHERE source_catalogue.code = 'crop_variety'
                   AND relation.relation_type = 'crop'
                   AND target_catalogue.code = 'crop'
                """,
            )
            == 2034
        )
        assert (
            scalar(
                conn,
                "SELECT count(*) FROM catalogue_values value "
                "JOIN catalogues catalogue ON catalogue.catalogue_id=value.catalogue_id "
                "WHERE catalogue.code='crop_variety'",
            )
            == 1952
        )
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT relation.relation_type, count(*)
                  FROM catalogue_value_relations relation
                  JOIN catalogue_values source
                    ON source.catalogue_value_id = relation.source_value_id
                  JOIN catalogues source_catalogue
                    ON source_catalogue.catalogue_id = source.catalogue_id
                 WHERE source_catalogue.code = 'seed_variety'
                 GROUP BY relation.relation_type
                """)
            assert dict(cursor.fetchall()) == {
                "category": 309,
                "crop_type": 309,
                "crop_variety": 309,
                "seed_crop": 902,
            }
        assert scalar(conn, "SELECT count(*) FROM g2p_zone") == 125
        assert scalar(conn, "SELECT count(*) FROM g2p_woreda") == 1379
        assert scalar(conn, "SELECT count(*) FROM g2p_kebele") == 19570
        assert scalar(conn, "SELECT count(*) FROM g2p_kebele WHERE match_status='MATCHED'") == 19535
        assert scalar(conn, "SELECT count(*) FROM geography_levels") == 4
        assert scalar(conn, "SELECT count(*) FROM geography_units") == 21053
        assert (
            scalar(
                conn,
                """
                SELECT count(*)
                  FROM geography_units unit
                  JOIN geography_levels level
                    ON level.geography_level_id = unit.geography_level_id
                 WHERE level.code = 'kebele' AND unit.parent_unit_id IS NOT NULL
                """,
            )
            == 19535
        )
        assert (
            scalar(
                conn,
                "SELECT count(*) FROM geography_units WHERE display_name_amh IS NULL",
            )
            == 21053
        )
        assert scalar(conn, "SELECT count(*) FROM livestock_population_statistics") == 40
        assert scalar(conn, "SELECT count(*) FROM seed_demand_summary_statistics") == 1
        assert scalar(conn, "SELECT count(*) FROM seed_demand_trend_statistics") == 5
        assert scalar(conn, "SELECT count(*) FROM seed_demand_by_crop_statistics") == 18

        publish(conn, trigger="SCHEDULED")
        assert (
            scalar(
                conn,
                "SELECT count(*) FROM catalogue_import_runs WHERE status='SKIPPED'",
            )
            == 1
        )
        assert scalar(conn, "SELECT count(*) FROM catalogue_releases") == 1
    finally:
        conn.close()


def test_failed_validation_preserves_the_active_release(tmp_path):
    conn = psycopg2.connect(TEST_DSN)
    try:
        rebuild_schema(conn)
        publish(conn)
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT release_id, version, checksum FROM catalogue_releases WHERE status='ACTIVE'"
            )
            original_release = cursor.fetchone()

        copied = tmp_path / "seed_db_sql"
        shutil.copytree(MANIFEST_PATH.parent, copied)
        invalid_manifest_path = copied / "manifest.yaml"
        invalid_manifest = yaml.safe_load(invalid_manifest_path.read_text(encoding="utf-8"))
        invalid_manifest["source_version"] = "ETH-invalid-minimums"
        crop_script = next(item for item in invalid_manifest["scripts"] if item["id"] == "crops")
        crop_script["expected_rows"]["g2p_crop"] = 999_999
        invalid_manifest_path.write_text(yaml.safe_dump(invalid_manifest, sort_keys=False), encoding="utf-8")

        with pytest.raises(runner.SeedError, match="expected exactly"):
            publish(conn, invalid_manifest_path, trigger="SCHEDULED")

        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT release_id, version, checksum FROM catalogue_releases WHERE status='ACTIVE'"
            )
            assert cursor.fetchone() == original_release
        assert scalar(conn, "SELECT count(*) FROM catalogue_releases") == 1
        assert scalar(conn, "SELECT count(*) FROM catalogue_import_runs WHERE status='FAILED'") == 1
    finally:
        conn.close()


def test_unknown_crop_category_preserves_the_active_release(tmp_path):
    conn = psycopg2.connect(TEST_DSN)
    try:
        rebuild_schema(conn)
        first_manifest, _ = publish(conn)

        copied = tmp_path / "seed_db_sql"
        shutil.copytree(MANIFEST_PATH.parent, copied)
        invalid_manifest_path = copied / "manifest.yaml"
        invalid_manifest = yaml.safe_load(invalid_manifest_path.read_text(encoding="utf-8"))
        invalid_manifest["source_version"] = "ETH-invalid-crop-category"
        invalid_manifest_path.write_text(yaml.safe_dump(invalid_manifest, sort_keys=False), encoding="utf-8")
        crop_sql = copied / "import_crop_catalog.sql"
        crop_sql.write_text(
            crop_sql.read_text(encoding="utf-8")
            + "\nUPDATE g2p_crop SET category_id = 999999 WHERE id = 1;\n",
            encoding="utf-8",
        )

        with pytest.raises(runner.SeedError, match="crops with unknown categories"):
            publish(conn, invalid_manifest_path, trigger="SCHEDULED")

        with conn.cursor() as cursor:
            cursor.execute("SELECT version, status FROM catalogue_releases")
            assert cursor.fetchall() == [(first_manifest["source_version"], "ACTIVE")]
        assert scalar(conn, "SELECT count(*) FROM catalogue_import_runs WHERE status='FAILED'") == 1
    finally:
        conn.close()


def test_unreviewed_livestock_production_relationship_preserves_active_release(
    tmp_path,
):
    conn = psycopg2.connect(TEST_DSN)
    try:
        rebuild_schema(conn)
        first_manifest, _ = publish(conn)

        copied = tmp_path / "seed_db_sql"
        shutil.copytree(MANIFEST_PATH.parent, copied)
        invalid_manifest_path = copied / "manifest.yaml"
        invalid_manifest = yaml.safe_load(invalid_manifest_path.read_text(encoding="utf-8"))
        invalid_manifest["source_version"] = "ETH-invalid-livestock-relations"
        invalid_manifest_path.write_text(yaml.safe_dump(invalid_manifest, sort_keys=False), encoding="utf-8")
        livestock_sql = copied / "import_livestock_data.sql"
        livestock_sql.write_text(
            livestock_sql.read_text(encoding="utf-8")
            + """
DELETE FROM g2p_livestock_production_type_species
 WHERE production_type_code = 'Wool'
   AND species_id = (SELECT id FROM g2p_livestock_type WHERE species_code = 'sheep');
INSERT INTO g2p_livestock_production_type_species
  (production_type_code, species_id)
SELECT 'Egg', id FROM g2p_livestock_type WHERE species_code = 'cattle';
""",
            encoding="utf-8",
        )

        with pytest.raises(
            runner.SeedError,
            match="Unexpected unlinked livestock production types",
        ):
            publish(conn, invalid_manifest_path, trigger="SCHEDULED")

        with conn.cursor() as cursor:
            cursor.execute("SELECT version, status FROM catalogue_releases")
            assert cursor.fetchall() == [(first_manifest["source_version"], "ACTIVE")]
        assert scalar(conn, "SELECT count(*) FROM catalogue_import_runs WHERE status='FAILED'") == 1
    finally:
        conn.close()


def test_new_source_version_atomically_retires_previous_release(tmp_path):
    conn = psycopg2.connect(TEST_DSN)
    try:
        rebuild_schema(conn)
        first_manifest, _ = publish(conn)

        copied = tmp_path / "seed_db_sql"
        shutil.copytree(MANIFEST_PATH.parent, copied)
        second_manifest_path = copied / "manifest.yaml"
        second_manifest = yaml.safe_load(second_manifest_path.read_text(encoding="utf-8"))
        second_manifest["source_version"] = "ETH-crop-taxonomy-v5"
        second_manifest_path.write_text(yaml.safe_dump(second_manifest, sort_keys=False), encoding="utf-8")
        publish(conn, second_manifest_path)

        with conn.cursor() as cursor:
            cursor.execute("SELECT version, status FROM catalogue_releases ORDER BY version")
            assert cursor.fetchall() == [
                (first_manifest["source_version"], "RETIRED"),
                (second_manifest["source_version"], "ACTIVE"),
            ]
            cursor.execute("""
                SELECT r.version, count(v.catalogue_value_id)
                  FROM catalogue_releases r
                  JOIN catalogues c ON c.release_id = r.release_id
                  JOIN catalogue_values v ON v.catalogue_id = c.catalogue_id
                 GROUP BY r.version
                 ORDER BY r.version
                """)
            assert cursor.fetchall() == [
                    (first_manifest["source_version"], 3400),
                    (second_manifest["source_version"], 3400),
            ]
        assert scalar(conn, "SELECT count(*) FROM catalogue_releases WHERE status='ACTIVE'") == 1
    finally:
        conn.close()


def test_seed_advisory_lock_rejects_concurrent_publishers():
    lock_conn = psycopg2.connect(TEST_DSN)
    competing_conn = psycopg2.connect(TEST_DSN)
    try:
        rebuild_schema(lock_conn)
        runner.acquire_lock(lock_conn)
        with pytest.raises(runner.SeedError, match="already active"):
            runner.acquire_lock(competing_conn)
        runner.release_lock(lock_conn)

        runner.acquire_lock(competing_conn)
        runner.release_lock(competing_conn)
    finally:
        lock_conn.close()
        competing_conn.close()
