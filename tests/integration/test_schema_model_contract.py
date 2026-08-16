import importlib.util
import os
import sys
from pathlib import Path

import openg2p_catalogue_service.models  # noqa: F401
import psycopg2
import pytest
from openg2p_fastapi_common.models import BaseORMModel

TEST_DSN = os.environ.get("CATALOGUE_TEST_DB_DSN")
pytestmark = pytest.mark.skipif(
    not TEST_DSN,
    reason="CATALOGUE_TEST_DB_DSN must point to a disposable PostgreSQL database",
)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = PROJECT_ROOT / "docker" / "db-migration" / "migrate_database.py"
MIGRATIONS_PATH = PROJECT_ROOT / "scripts" / "migrations"
SPEC = importlib.util.spec_from_file_location("schema_contract_migration_runner", RUNNER_PATH)
runner = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


def catalogue_model_tables():
    return {
        mapper.local_table.name: mapper.local_table
        for mapper in BaseORMModel.registry.mappers
        if mapper.class_.__module__.startswith("openg2p_catalogue_service.models")
    }


def test_sql_migrations_and_orm_models_have_identical_tables_columns_and_primary_keys():
    conn = psycopg2.connect(TEST_DSN)
    try:
        with conn.cursor() as cursor:
            cursor.execute("DROP SCHEMA public CASCADE")
            cursor.execute("CREATE SCHEMA public")
        conn.commit()
        migrations = runner.discover_migrations(MIGRATIONS_PATH)
        runner.run(conn, migrations, expected_version=migrations[-1].version)

        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT columns.table_name, columns.column_name
                  FROM information_schema.columns columns
                  JOIN information_schema.tables tables
                    ON tables.table_schema = columns.table_schema
                   AND tables.table_name = columns.table_name
                 WHERE columns.table_schema = 'public'
                   AND tables.table_type = 'BASE TABLE'
                 ORDER BY columns.table_name, columns.ordinal_position
                """)
            database_columns: dict[str, set[str]] = {}
            for table_name, column_name in cursor.fetchall():
                database_columns.setdefault(table_name, set()).add(column_name)

            cursor.execute("""
                SELECT tc.table_name, kcu.column_name
                  FROM information_schema.table_constraints tc
                  JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                   AND tc.constraint_schema = kcu.constraint_schema
                 WHERE tc.table_schema = 'public'
                   AND tc.constraint_type = 'PRIMARY KEY'
                """)
            database_primary_keys: dict[str, set[str]] = {}
            for table_name, column_name in cursor.fetchall():
                database_primary_keys.setdefault(table_name, set()).add(column_name)

        model_tables = catalogue_model_tables()
        assert set(database_columns) == set(model_tables)
        for table_name, table in model_tables.items():
            assert database_columns[table_name] == {column.name for column in table.columns}
            assert database_primary_keys[table_name] == {column.name for column in table.primary_key.columns}
    finally:
        conn.close()
