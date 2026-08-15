import importlib.util
import os
import shutil
import sys
from pathlib import Path

import psycopg2
import pytest

TEST_DSN = os.environ.get("CATALOGUE_TEST_DB_DSN")
pytestmark = pytest.mark.skipif(
    not TEST_DSN,
    reason="CATALOGUE_TEST_DB_DSN must point to a disposable PostgreSQL database",
)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = PROJECT_ROOT / "docker" / "db-migration" / "migrate_database.py"
MIGRATIONS_PATH = PROJECT_ROOT / "scripts" / "migrations"
SPEC = importlib.util.spec_from_file_location("migration_lifecycle", RUNNER_PATH)
runner = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


def reset_database(conn):
    with conn.cursor() as cursor:
        cursor.execute("DROP SCHEMA public CASCADE")
        cursor.execute("CREATE SCHEMA public")
    conn.commit()


def scalar(conn, statement):
    with conn.cursor() as cursor:
        cursor.execute(statement)
        return cursor.fetchone()[0]


def test_migrations_apply_once_and_verify_current():
    conn = psycopg2.connect(TEST_DSN)
    try:
        reset_database(conn)
        migrations = runner.discover_migrations(MIGRATIONS_PATH)

        assert runner.run(conn, migrations, expected_version="014") == 14
        assert scalar(conn, "SELECT count(*) FROM catalogue_schema_migrations") == 14
        assert scalar(conn, "SELECT max(version::integer) FROM catalogue_schema_migrations") == 14
        assert scalar(conn, "SELECT to_regclass('public.geography_units') IS NOT NULL")
        assert scalar(conn, "SELECT to_regclass('public.g2p_kebele') IS NOT NULL")
        assert scalar(conn, "SELECT to_regclass('public.g2p_livestock_registry_entry') IS NOT NULL")
        assert scalar(conn, "SELECT to_regclass('public.livestock_registry_entries') IS NOT NULL")
        assert scalar(conn, "SELECT to_regclass('public.g2p_livestock_registry_validation') IS NOT NULL")
        assert scalar(conn, "SELECT to_regclass('public.livestock_registry_validation') IS NOT NULL")
        assert (
            scalar(
                conn,
                "SELECT count(*) FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name='g2p_crop' "
                "AND column_name IN ('scientific_name', 'centre', 'varieties_count', "
                "'image_url', 'display_name_amh', 'taxonomy_type_code', "
                "'taxonomy_source_id', 'taxonomy_category_code', "
                "'taxonomy_description', 'record_source', 'varieties_count_source', "
                "'taxonomy_match_method', 'taxonomy_match_status', 'category_source')",
            )
            == 14
        )
        assert (
            scalar(
                conn,
                "SELECT count(*) FROM information_schema.columns "
                "WHERE table_schema='public' AND column_name='display_name_amh' "
                "AND table_name IN ('g2p_region', 'g2p_zone', 'g2p_woreda', 'geography_units')",
            )
            == 4
        )

        expected_crop_tables = (
            "'g2p_crop_taxonomy_category', 'g2p_crop_taxonomy_type', "
            "'g2p_crop_variety', 'g2p_crop_variety_source_record', "
            "'g2p_crop_characteristic_definition', 'g2p_crop_variety_characteristic'"
        )
        assert (
            scalar(
                conn,
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name IN ("
                f"{expected_crop_tables})",
            )
            == 6
        )
        assert (
            scalar(
                conn,
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name IN ("
                "'crop_variety_source_records', "
                "'crop_characteristic_definitions', "
                "'crop_variety_characteristics')",
            )
            == 3
        )
        assert (
            scalar(
                conn,
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name IN ("
                "'g2p_seed_variety_source_record', "
                "'seed_variety_source_records')",
            )
            == 2
        )
        assert (
            scalar(
                conn,
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name IN ("
                "'g2p_livestock_breed', 'g2p_livestock_gender', "
                "'g2p_livestock_location_type', 'g2p_livestock_body_condition', "
                "'g2p_livestock_production_type', "
                "'g2p_livestock_production_type_species', "
                "'g2p_livestock_record_status')",
            )
            == 7
        )
        assert (
            scalar(
                conn,
                "SELECT count(*) FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name='g2p_livestock_type' "
                "AND column_name IN ('scientific_name', 'subfamily', "
                "'species_type_code', 'chart_color', 'ear_tag_range', "
                "'in_lis_population', 'in_etlits_registry')",
            )
            == 7
        )

        assert runner.run(conn, migrations, expected_version="014") == 0
        runner.verify_current(conn, migrations, expected_version="014")
        assert scalar(conn, "SELECT count(*) FROM catalogue_schema_migrations") == 14
    finally:
        conn.close()


def test_upgrade_from_previous_schema_version_applies_only_pending_migration():
    conn = psycopg2.connect(TEST_DSN)
    try:
        reset_database(conn)
        migrations = runner.discover_migrations(MIGRATIONS_PATH)

        assert runner.run(conn, migrations[:13], expected_version="013") == 13
        assert scalar(conn, "SELECT max(version::integer) FROM catalogue_schema_migrations") == 13

        assert runner.run(conn, migrations, expected_version="014") == 1
        runner.verify_current(conn, migrations, expected_version="014")
        assert scalar(conn, "SELECT count(*) FROM catalogue_schema_migrations") == 14
    finally:
        conn.close()


def test_livestock_reference_staging_enforces_typed_relations():
    conn = psycopg2.connect(TEST_DSN)
    try:
        reset_database(conn)
        migrations = runner.discover_migrations(MIGRATIONS_PATH)
        runner.run(conn, migrations, expected_version="014")
        conn.autocommit = True

        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO g2p_ecological_zone (id, name)
                VALUES (1, 'Kolla')
                """)
            cursor.execute("""
                INSERT INTO g2p_livestock_type
                  (id, species_code, name, scientific_name, species_type_code,
                   in_lis_population, in_etlits_registry)
                VALUES (1, 'cattle', 'Cattle', 'Bos taurus & Bos indicus', 1, TRUE, TRUE)
                """)
            cursor.execute("""
                INSERT INTO g2p_livestock_breed
                  (id, breed_code, name, species_id, breed_type,
                   in_national_standard, source)
                VALUES (10, '1.01.10', 'Boran', 1, 'Indigenous', TRUE, 'MOA 2024')
                """)
            cursor.execute("""
                INSERT INTO g2p_livestock_location_type
                  (code, name, ecological_zone_id)
                VALUES ('Low Land', 'Low land', 1)
                """)
            cursor.execute("""
                INSERT INTO g2p_livestock_production_type
                  (code, name, in_national_standard)
                VALUES ('Milk', 'Milk', TRUE)
                """)
            cursor.execute("""
                INSERT INTO g2p_livestock_production_type_species
                  (production_type_code, species_id)
                VALUES ('Milk', 1)
                """)
            cursor.execute("""
                INSERT INTO g2p_livestock_gender (code, name)
                VALUES ('Female', 'Female')
                """)
            cursor.execute("""
                INSERT INTO g2p_livestock_body_condition
                  (code, bcs_score, condition_label, fatness_label)
                VALUES ('BCS3', 3, 'Good', 'Moderate')
                """)
            cursor.execute("""
                INSERT INTO g2p_livestock_record_status
                  (code, name, sort_order, is_live_master_data)
                VALUES ('ACTIVE', 'Active', 5, TRUE)
                """)
            cursor.execute("""
                INSERT INTO g2p_livestock_registry_entry
                  (id, species_code, breed_name, breed_id, gender_code,
                   location_type_code, body_condition_code, production_type_code,
                   status, created_on, updated_on)
                VALUES
                  ('valid', 'cattle', 'Boran', 10, 'Female', 'Low Land',
                   'BCS3', 'Milk', 'ACTIVE', now(), now()),
                  ('unknown-breed', 'cattle', 'Test', NULL, 'Female', 'Low Land',
                   'BCS3', 'Milk', 'ACTIVE', now(), now())
                """)

        assert scalar(conn, "SELECT count(*) FROM g2p_livestock_breed") == 1
        assert scalar(conn, "SELECT count(*) FROM g2p_livestock_production_type_species") == 1
        assert scalar(conn, "SELECT count(*) FROM g2p_livestock_registry_entry") == 2
        assert (
            scalar(
                conn,
                "SELECT count(*) FROM g2p_livestock_registry_validation WHERE breed_unrecognised",
            )
            == 1
        )

        with conn.cursor() as cursor:
            with pytest.raises(psycopg2.errors.CheckViolation):
                cursor.execute("""
                    INSERT INTO g2p_livestock_breed
                      (id, name, species_id, breed_type, source)
                    VALUES (11, 'Invalid', 1, 'Unknown', 'Test')
                    """)
            with pytest.raises(psycopg2.errors.ForeignKeyViolation):
                cursor.execute("""
                    INSERT INTO g2p_livestock_breed
                      (id, name, species_id, breed_type, source)
                    VALUES (12, 'Unknown species', 999, 'Exotic', 'Test')
                    """)
            with pytest.raises(psycopg2.errors.CheckViolation):
                cursor.execute("""
                    INSERT INTO g2p_livestock_body_condition
                      (code, bcs_score, condition_label, fatness_label)
                    VALUES ('BCS6', 6, 'Invalid', 'Invalid')
                    """)
            with pytest.raises(psycopg2.errors.CheckViolation):
                cursor.execute("""
                    INSERT INTO g2p_livestock_type (species_code, name)
                    VALUES ('Camel', 'Camel')
                    """)
    finally:
        conn.close()


def test_crop_taxonomy_staging_enforces_relations_and_typed_ranges():
    conn = psycopg2.connect(TEST_DSN)
    try:
        reset_database(conn)
        migrations = runner.discover_migrations(MIGRATIONS_PATH)
        runner.run(conn, migrations, expected_version="014")
        conn.autocommit = True

        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO g2p_crop_taxonomy_category
                  (category_code, source_id, display_name)
                VALUES ('cereal', 'cropcategory-80402', 'Cereal')
                """)
            cursor.execute("""
                INSERT INTO g2p_crop_taxonomy_type
                  (type_code, source_id, category_code, display_name,
                   source_reported_variety_count)
                VALUES ('maize', 'croptype-592280314975', 'cereal', 'Maize', 85)
                """)
            cursor.execute("""
                INSERT INTO g2p_crop_variety
                  (variety_code, type_code, display_name)
                VALUES ('maize-melkassa-1q', 'maize', 'Melkassa 1Q')
                """)
            cursor.execute("""
                INSERT INTO g2p_crop_variety_source_record
                  (source_record_code, variety_code, source_row_number, centre,
                   release_year_raw, release_year, altitude_min_m, altitude_max_m)
                VALUES
                  ('workbook-350', 'maize-melkassa-1q', 384,
                   'Melkassa Agricultural Research Center', '2013', 2013, 1000, 1750),
                  ('workbook-389', 'maize-melkassa-1q', 423,
                   'Melkassa Agricultural Research Center', '2001', 2001, 1000, 1750)
                """)
            cursor.execute("""
                INSERT INTO g2p_crop_characteristic_definition
                  (characteristic_code, display_name, value_type, default_unit_code,
                   applicable_category_code)
                VALUES ('grain_type', 'Grain type', 'TEXT', NULL, 'cereal')
                """)
            cursor.execute("""
                INSERT INTO g2p_crop_variety_characteristic
                  (source_record_code, characteristic_code, raw_value, value_text)
                VALUES ('workbook-350', 'grain_type', 'Semi-dent', 'Semi-dent')
                """)

        assert scalar(conn, "SELECT count(*) FROM g2p_crop_variety_source_record") == 2
        assert scalar(conn, "SELECT count(*) FROM g2p_crop_variety_characteristic") == 1

        with conn.cursor() as cursor:
            with pytest.raises(psycopg2.errors.ForeignKeyViolation):
                cursor.execute("""
                    INSERT INTO g2p_crop_taxonomy_type
                      (type_code, category_code, display_name)
                    VALUES ('unknown-type', 'unknown-category', 'Unknown')
                    """)
            with pytest.raises(psycopg2.errors.CheckViolation):
                cursor.execute("""
                    INSERT INTO g2p_crop_variety_source_record
                      (source_record_code, variety_code, centre, release_year_raw,
                       altitude_min_m, altitude_max_m)
                    VALUES ('bad-range', 'maize-melkassa-1q', 'Test', '-', 2000, 1000)
                    """)
    finally:
        conn.close()


def test_seed_variety_staging_enforces_source_and_match_integrity():
    conn = psycopg2.connect(TEST_DSN)
    try:
        reset_database(conn)
        migrations = runner.discover_migrations(MIGRATIONS_PATH)
        runner.run(conn, migrations, expected_version="014")
        conn.autocommit = True

        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO g2p_seed_catalog (id, name) VALUES (1, 'Maize')")
            cursor.execute("INSERT INTO g2p_crop (id, name) VALUES (1, 'Maize')")
            cursor.execute("""
                INSERT INTO g2p_crop_taxonomy_category
                  (category_code, source_id, display_name)
                VALUES ('cereal', 'cropcategory-cereal', 'Cereal')
                """)
            cursor.execute("""
                INSERT INTO g2p_crop_taxonomy_type
                  (type_code, category_code, display_name)
                VALUES ('maize', 'cereal', 'Maize')
                """)
            cursor.execute("""
                INSERT INTO g2p_crop_variety
                  (variety_code, type_code, display_name)
                VALUES ('maize-mh141', 'maize', 'MH141')
                """)
            cursor.execute("""
                INSERT INTO g2p_seed_variety_source_record
                  (source_variety_id, seed_crop_id, crop_name_raw,
                   common_name_raw, release_year, release_date, release_raw,
                   source_classification, details_url)
                VALUES
                  (2, 1, 'Maize', 'Maize-MH141', 2020, DATE '2020-01-01',
                   'Jan. 1, 2020', 'Domestic',
                   'https://ethioseed.moa.gov.et/seed-variety-details/2/')
                """)
            cursor.execute("""
                INSERT INTO g2p_seed_variety_source_record
                  (source_variety_id, seed_crop_id, crop_name_raw,
                   common_name_raw, details_url, matched_variety_code,
                   match_method, match_status)
                VALUES
                  (3, 1, 'Maize', 'Maize-MH141 duplicate source',
                   'https://ethioseed.moa.gov.et/seed-variety-details/3/',
                   'maize-mh141', 'EXACT_SOURCE_ID', 'MATCHED')
                """)

        assert scalar(conn, "SELECT count(*) FROM g2p_seed_variety_source_record") == 2

        with conn.cursor() as cursor:
            with pytest.raises(psycopg2.errors.CheckViolation):
                cursor.execute("""
                    INSERT INTO g2p_seed_variety_source_record
                      (source_variety_id, seed_crop_id, crop_name_raw,
                       common_name_raw, details_url, matched_variety_code,
                       match_method, match_status)
                    VALUES
                      (4, 1, 'Maize', 'Invalid unresolved match',
                       'https://ethioseed.moa.gov.et/seed-variety-details/4/',
                       'maize-mh141', 'UNRESOLVED', 'UNRESOLVED')
                    """)
            with pytest.raises(psycopg2.errors.ForeignKeyViolation):
                cursor.execute("""
                    INSERT INTO g2p_seed_variety_source_record
                      (source_variety_id, seed_crop_id, crop_name_raw,
                       common_name_raw, details_url)
                    VALUES
                      (5, 999, 'Unknown', 'Unknown variety',
                       'https://ethioseed.moa.gov.et/seed-variety-details/5/')
                    """)
    finally:
        conn.close()


def test_advisory_lock_rejects_a_concurrent_migration_runner():
    lock_conn = psycopg2.connect(TEST_DSN)
    competing_conn = psycopg2.connect(TEST_DSN)
    try:
        reset_database(lock_conn)
        migrations = runner.discover_migrations(MIGRATIONS_PATH)
        runner.run(lock_conn, migrations, expected_version="014")

        runner.acquire_lock(lock_conn)
        with pytest.raises(runner.MigrationError, match="already active"):
            runner.run(competing_conn, migrations, expected_version="014")
        runner.release_lock(lock_conn)

        assert runner.run(competing_conn, migrations, expected_version="014") == 0
    finally:
        lock_conn.close()
        competing_conn.close()


def test_database_newer_than_application_bundle_is_rejected():
    conn = psycopg2.connect(TEST_DSN)
    try:
        reset_database(conn)
        migrations = runner.discover_migrations(MIGRATIONS_PATH)
        runner.run(conn, migrations, expected_version="014")
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO catalogue_schema_migrations
                  (version, filename, checksum, applied_at, execution_ms, runner_version)
                VALUES ('015', '015_future.sql', 'sha256:future', now(), 0, 'future')
                """)
        conn.commit()

        with pytest.raises(runner.MigrationError, match="newer than"):
            runner.verify_current(conn, migrations, expected_version="014")
    finally:
        conn.close()


def test_checksum_drift_is_rejected(tmp_path):
    conn = psycopg2.connect(TEST_DSN)
    try:
        reset_database(conn)
        copied = tmp_path / "migrations"
        shutil.copytree(MIGRATIONS_PATH, copied)
        original = runner.discover_migrations(copied)
        runner.run(conn, original, expected_version="014")

        first = copied / "001_catalogue_schema.sql"
        first.write_text(first.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        changed = runner.discover_migrations(copied)
        with pytest.raises(runner.MigrationError, match="Checksum mismatch"):
            runner.run(conn, changed, expected_version="014")
    finally:
        conn.close()


def test_failed_migration_rolls_back_only_its_version(tmp_path):
    conn = psycopg2.connect(TEST_DSN)
    try:
        reset_database(conn)
        copied = tmp_path / "migrations"
        shutil.copytree(MIGRATIONS_PATH, copied)
        (copied / "015_broken.sql").write_text(
            """BEGIN;
CREATE TABLE should_be_rolled_back (id INTEGER PRIMARY KEY);
SELECT missing_column FROM table_that_does_not_exist;
COMMIT;
""",
            encoding="utf-8",
        )
        migrations = runner.discover_migrations(copied)

        with pytest.raises(psycopg2.Error):
            runner.run(conn, migrations, expected_version="015")

        assert scalar(conn, "SELECT count(*) FROM catalogue_schema_migrations") == 14
        assert not scalar(conn, "SELECT to_regclass('public.should_be_rolled_back') IS NOT NULL")
    finally:
        conn.close()
