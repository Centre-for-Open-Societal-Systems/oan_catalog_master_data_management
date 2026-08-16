#!/usr/bin/env python3
"""Apply and verify ordered, immutable PostgreSQL schema migrations."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import psycopg2

RUNNER_VERSION = "1.0"
LOCK_NAME = "openg2p-catalogue-schema-migrations"
MIGRATION_NAME = re.compile(r"^(?P<version>[0-9]{3,})_[a-z0-9_]+\.sql$")
BEGIN_WRAPPER = re.compile(r"^\s*BEGIN\s*;", re.IGNORECASE)
COMMIT_WRAPPER = re.compile(r"COMMIT\s*;\s*$", re.IGNORECASE)


class MigrationError(RuntimeError):
    pass


class SchemaNotCurrentError(MigrationError):
    pass


@dataclass(frozen=True)
class Migration:
    version: str
    filename: str
    path: Path
    checksum: str
    sql: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def file_checksum(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def migration_body(path: Path) -> str:
    """Remove the legacy transaction wrapper; the runner owns the transaction."""
    source = path.read_text(encoding="utf-8")
    begin = BEGIN_WRAPPER.search(source)
    commit = COMMIT_WRAPPER.search(source)
    if begin is None or begin.start() != 0 or commit is None or commit.end() != len(source):
        raise MigrationError(f"Migration {path.name} must contain exactly one outer BEGIN/COMMIT wrapper")
    body = source[begin.end() : commit.start()].strip()
    if not body:
        raise MigrationError(f"Migration {path.name} is empty")
    return body


def discover_migrations(directory: Path) -> list[Migration]:
    directory = directory.resolve()
    if not directory.is_dir():
        raise MigrationError(f"Migration directory does not exist: {directory}")

    sql_files = sorted(directory.glob("*.sql"))
    if not sql_files:
        raise MigrationError(f"No SQL migrations found in {directory}")

    migrations: list[Migration] = []
    seen_versions: set[str] = set()
    for path in sql_files:
        match = MIGRATION_NAME.fullmatch(path.name)
        if match is None:
            raise MigrationError(f"Invalid migration filename {path.name}; expected NNN_description.sql")
        version = match.group("version")
        if version in seen_versions:
            raise MigrationError(f"Duplicate migration version: {version}")
        seen_versions.add(version)
        migrations.append(
            Migration(
                version=version,
                filename=path.name,
                path=path,
                checksum=file_checksum(path),
                sql=migration_body(path),
            )
        )

    migrations.sort(key=lambda item: int(item.version))
    expected_versions = list(range(1, len(migrations) + 1))
    actual_versions = [int(item.version) for item in migrations]
    if actual_versions != expected_versions:
        raise MigrationError(
            "Migration versions must be contiguous starting at 001; "
            f"found {', '.join(item.version for item in migrations)}"
        )
    return migrations


def connect():
    return psycopg2.connect(
        dbname=os.environ.get("CATALOGUE_DB", os.environ.get("PGDATABASE", "catalogue")),
        host=os.environ.get("PGHOST", "localhost"),
        port=os.environ.get("PGPORT", "5432"),
        user=os.environ.get("PGUSER", "postgres"),
        password=os.environ.get("PGPASSWORD", ""),
        connect_timeout=int(os.environ.get("PGCONNECT_TIMEOUT", "10")),
        application_name="catalogue-schema-migration",
    )


def connect_with_retry(wait_seconds: int):
    deadline = time.monotonic() + wait_seconds
    while True:
        try:
            return connect()
        except psycopg2.OperationalError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(min(3, max(0.1, deadline - time.monotonic())))


def ensure_history_table(conn) -> None:
    with conn.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS catalogue_schema_migrations (
                version       VARCHAR PRIMARY KEY,
                filename      VARCHAR NOT NULL UNIQUE,
                checksum      VARCHAR NOT NULL,
                applied_at    TIMESTAMPTZ NOT NULL,
                execution_ms  BIGINT NOT NULL,
                runner_version VARCHAR NOT NULL
            )
            """)
    conn.commit()


def applied_history(conn) -> list[dict]:
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT version, filename, checksum, applied_at, execution_ms, runner_version
              FROM catalogue_schema_migrations
             ORDER BY version::bigint
            """)
        return [
            {
                "version": row[0],
                "filename": row[1],
                "checksum": row[2],
                "applied_at": row[3],
                "execution_ms": row[4],
                "runner_version": row[5],
            }
            for row in cursor.fetchall()
        ]


def history_table_exists(conn) -> bool:
    with conn.cursor() as cursor:
        cursor.execute("SELECT to_regclass('public.catalogue_schema_migrations') IS NOT NULL")
        return bool(cursor.fetchone()[0])


def validate_history(migrations: list[Migration], history: list[dict]) -> None:
    if len(history) > len(migrations):
        raise MigrationError("Database schema is newer than the bundled migration set")

    for index, applied in enumerate(history):
        expected = migrations[index]
        if applied["version"] != expected.version or applied["filename"] != expected.filename:
            raise MigrationError(
                "Migration history is not a prefix of the bundled migration set: "
                f"database has {applied['version']}/{applied['filename']}, "
                f"bundle expects {expected.version}/{expected.filename}"
            )
        if applied["checksum"] != expected.checksum:
            raise MigrationError(
                f"Checksum mismatch for applied migration {expected.filename}; "
                "applied migrations are immutable"
            )


def acquire_lock(conn) -> None:
    with conn.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(hashtext(%s))", (LOCK_NAME,))
        if not cursor.fetchone()[0]:
            conn.rollback()
            raise MigrationError("Another catalogue schema migration is already active")
    conn.commit()


def release_lock(conn) -> None:
    with conn.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_unlock(hashtext(%s))", (LOCK_NAME,))
    conn.commit()


def apply_pending(conn, migrations: list[Migration]) -> int:
    ensure_history_table(conn)
    history = applied_history(conn)
    validate_history(migrations, history)
    applied_count = 0

    for migration in migrations[len(history) :]:
        started = time.monotonic()
        try:
            with conn.cursor() as cursor:
                cursor.execute(migration.sql)
                execution_ms = int((time.monotonic() - started) * 1000)
                cursor.execute(
                    """
                    INSERT INTO catalogue_schema_migrations
                      (version, filename, checksum, applied_at, execution_ms, runner_version)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        migration.version,
                        migration.filename,
                        migration.checksum,
                        utc_now(),
                        execution_ms,
                        RUNNER_VERSION,
                    ),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        applied_count += 1
        print(f"[migration] applied {migration.filename}", flush=True)

    return applied_count


def verify_current(
    conn,
    migrations: list[Migration],
    expected_version: str | None = None,
) -> None:
    if not history_table_exists(conn):
        raise SchemaNotCurrentError("Schema migration history has not been initialized")
    history = applied_history(conn)
    validate_history(migrations, history)
    bundled_version = migrations[-1].version
    if expected_version is not None and bundled_version != expected_version:
        raise MigrationError(
            f"Bundled migration version {bundled_version} does not match expected {expected_version}"
        )
    if len(history) != len(migrations):
        current = history[-1]["version"] if history else "none"
        raise SchemaNotCurrentError(
            f"Database schema is at {current}; bundled version {bundled_version} is not fully applied"
        )


def verify_with_retry(
    conn,
    migrations: list[Migration],
    expected_version: str | None,
    wait_seconds: int,
) -> None:
    deadline = time.monotonic() + wait_seconds
    while True:
        try:
            verify_current(conn, migrations, expected_version)
            return
        except SchemaNotCurrentError:
            conn.rollback()
            if time.monotonic() >= deadline:
                raise
            time.sleep(min(3, max(0.1, deadline - time.monotonic())))


def run(
    conn,
    migrations: list[Migration],
    expected_version: str | None = None,
    verify_only: bool = False,
) -> int:
    bundled_version = migrations[-1].version
    if expected_version is not None and bundled_version != expected_version:
        raise MigrationError(
            f"Bundled migration version {bundled_version} does not match expected {expected_version}"
        )
    if verify_only:
        verify_current(conn, migrations, expected_version)
        print(f"[migration] schema is current at {bundled_version}", flush=True)
        return 0

    acquire_lock(conn)
    try:
        count = apply_pending(conn, migrations)
        verify_current(conn, migrations, expected_version)
    finally:
        conn.rollback()
        release_lock(conn)
    if count == 0:
        print(f"[migration] schema already current at {bundled_version}", flush=True)
    else:
        print(f"[migration] applied {count} migration(s); current={bundled_version}", flush=True)
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--migrations", type=Path, default=Path("/migration/sql"))
    parser.add_argument("--expected-version")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--wait-seconds", type=int, default=0)
    args = parser.parse_args()

    try:
        migrations = discover_migrations(args.migrations)
        conn = connect_with_retry(max(0, args.wait_seconds))
        try:
            if args.verify_only:
                verify_with_retry(
                    conn,
                    migrations,
                    args.expected_version,
                    max(0, args.wait_seconds),
                )
                print(
                    f"[migration] schema is current at {migrations[-1].version}",
                    flush=True,
                )
            else:
                run(conn, migrations, args.expected_version)
        finally:
            conn.close()
    except Exception as error:
        print(f"[migration] failed: {error}", file=sys.stderr, flush=True)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
