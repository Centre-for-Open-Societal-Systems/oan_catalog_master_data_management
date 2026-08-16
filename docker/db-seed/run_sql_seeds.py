#!/usr/bin/env python3
"""Execute versioned SQL sources and atomically publish a catalogue release."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import psycopg2
import psycopg2.extras
import yaml
from psycopg2 import sql

NAMESPACE = uuid.UUID("cc1a77af-f811-44ed-867f-890c45cc99ae")
LOCK_NAME = "openg2p-catalogue-sql-seed"
IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")
VALID_DATASET_KINDS = {"catalogue", "geography", "statistics", "mixed"}


class SeedError(RuntimeError):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def stable_id(*parts: object) -> str:
    return str(uuid.uuid5(NAMESPACE, ":".join(str(part) for part in parts)))


def livestock_breed_public_code(
    source_id: int,
    breed_code: str | None,
    species_code: str,
    display_name: str,
) -> str:
    if breed_code:
        return breed_code
    slug = re.sub(r"[^a-z0-9]+", "-", display_name.casefold()).strip("-")
    if not slug:
        raise SeedError(f"Cannot derive a public code for livestock breed {source_id}")
    return f"etlits-{species_code}-{slug}"


def json_default(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f"Cannot encode {type(value).__name__} as JSON")


def json_value(value):
    return psycopg2.extras.Json(value, dumps=lambda item: json.dumps(item, default=json_default))


def load_manifest(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        manifest = yaml.safe_load(handle)
    if not isinstance(manifest, dict):
        raise SeedError("Seed manifest must be a YAML object")
    return manifest


def validate_manifest(manifest: dict, manifest_path: Path) -> list[dict]:
    for field in ("schema_version", "country_code", "source_version", "scripts"):
        if not manifest.get(field):
            raise SeedError(f"Manifest field '{field}' is required")
    country = str(manifest["country_code"]).upper()
    if len(country) != 3 or not country.isalpha():
        raise SeedError("country_code must be an alpha-3 code")

    scripts = manifest["scripts"]
    if not isinstance(scripts, list) or not scripts:
        raise SeedError("Manifest must declare at least one script")

    seen_ids: set[str] = set()
    seen_files: set[str] = set()
    seen_orders: set[int] = set()
    base_dir = manifest_path.parent.resolve()
    for item in scripts:
        for field in (
            "id",
            "filename",
            "order",
            "dataset_kind",
            "staging_tables",
            "canonical_targets",
        ):
            if field not in item:
                raise SeedError(f"Manifest script is missing '{field}'")
        script_id = str(item["id"])
        filename = str(item["filename"])
        order = int(item["order"])
        if script_id in seen_ids or filename in seen_files or order in seen_orders:
            raise SeedError(f"Duplicate script id, filename, or order at '{script_id}'")
        seen_ids.add(script_id)
        seen_files.add(filename)
        seen_orders.add(order)
        if item["dataset_kind"] not in VALID_DATASET_KINDS:
            raise SeedError(f"Unsupported dataset_kind for {script_id}: {item['dataset_kind']}")

        script_path = (base_dir / filename).resolve()
        if script_path.parent != base_dir or not script_path.is_file():
            raise SeedError(f"SQL file is missing or outside the seed directory: {filename}")
        item["path"] = script_path

        for table in item["staging_tables"] + item["canonical_targets"]:
            if not IDENTIFIER.fullmatch(table):
                raise SeedError(f"Unsafe table identifier in manifest: {table}")
        staging_table_names = set(item["staging_tables"])
        for expectation in ("expected_minimum_rows", "expected_rows"):
            for table in item.get(expectation, {}):
                if table not in staging_table_names:
                    raise SeedError(f"{expectation} references undeclared staging table: {table}")

    return sorted(scripts, key=lambda item: int(item["order"]))


def file_checksum(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def manifest_checksum(manifest_path: Path, scripts: list[dict]) -> str:
    digest = hashlib.sha256()
    digest.update(manifest_path.read_bytes())
    for item in scripts:
        digest.update(item["filename"].encode())
        digest.update(item["path"].read_bytes())
    return "sha256:" + digest.hexdigest()


def connect():
    return psycopg2.connect(
        dbname=os.environ.get("PGDATABASE", os.environ.get("CATALOGUE_DB", "catalogue")),
        host=os.environ.get("PGHOST", "localhost"),
        port=os.environ.get("PGPORT", "5432"),
        user=os.environ.get("PGUSER", "postgres"),
        password=os.environ.get("PGPASSWORD", ""),
        connect_timeout=int(os.environ.get("PGCONNECT_TIMEOUT", "10")),
        application_name="catalogue-sql-seed",
    )


def acquire_lock(conn) -> None:
    with conn.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(hashtext(%s))", (LOCK_NAME,))
        if not cursor.fetchone()[0]:
            conn.rollback()
            raise SeedError("Another catalogue SQL seed run is already active")
    conn.commit()


def release_lock(conn) -> None:
    with conn.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_unlock(hashtext(%s))", (LOCK_NAME,))
    conn.commit()


def record_run(conn, manifest: dict, scripts: list[dict], checksum: str, trigger: str) -> str:
    run_id = str(uuid.uuid4())
    now = utc_now()
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO catalogue_import_runs
              (import_run_id, country_code, source_version, manifest_checksum,
               status, trigger, started_at, metadata)
            VALUES (%s, %s, %s, %s, 'PENDING', %s, %s, %s)
            """,
            (
                run_id,
                str(manifest["country_code"]).upper(),
                str(manifest["source_version"]),
                checksum,
                trigger,
                now,
                json_value({"schema_version": str(manifest["schema_version"])}),
            ),
        )
        rows = [
            (
                str(uuid.uuid4()),
                run_id,
                item["id"],
                item["filename"],
                file_checksum(item["path"]),
                int(item["order"]),
                item["dataset_kind"],
                "PENDING",
            )
            for item in scripts
        ]
        psycopg2.extras.execute_values(
            cursor,
            """
            INSERT INTO catalogue_import_scripts
              (import_script_id, import_run_id, script_id, filename, checksum,
               execution_order, dataset_kind, status)
            VALUES %s
            """,
            rows,
        )
    conn.commit()
    return run_id


def active_release_for_source(conn, manifest: dict, checksum: str):
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT release_id, checksum, status
              FROM catalogue_releases
             WHERE country_code = %s AND version = %s
            """,
            (str(manifest["country_code"]).upper(), str(manifest["source_version"])),
        )
        row = cursor.fetchone()
    if row and row[1] != checksum:
        raise SeedError(
            "The source_version already exists with different content; "
            "increment source_version instead of changing an immutable release"
        )
    return row


def mark_skipped(conn, run_id: str, release_id: str) -> None:
    now = utc_now()
    with conn.cursor() as cursor:
        cursor.execute(
            """
            UPDATE catalogue_import_runs
               SET release_id=%s, status='SKIPPED', finished_at=%s,
                   metadata=COALESCE(metadata, '{}'::jsonb) || %s::jsonb
             WHERE import_run_id=%s
            """,
            (release_id, now, json.dumps({"reason": "release already active"}), run_id),
        )
        cursor.execute(
            """
            UPDATE catalogue_import_scripts
               SET status='SKIPPED', finished_at=%s
             WHERE import_run_id=%s
            """,
            (now, run_id),
        )
    conn.commit()


def staging_tables(scripts: list[dict]) -> list[str]:
    return sorted({table for item in scripts for table in item["staging_tables"]})


def truncate_staging(cursor, scripts: list[dict]) -> None:
    tables = staging_tables(scripts)
    identifiers = sql.SQL(", ").join(sql.Identifier(table) for table in tables)
    cursor.execute(sql.SQL("TRUNCATE TABLE {} RESTART IDENTITY CASCADE").format(identifiers))


def table_count(cursor, table: str) -> int:
    cursor.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table)))
    return cursor.fetchone()[0]


def execute_scripts(cursor, run_id: str, scripts: list[dict]) -> None:
    for item in scripts:
        started_at = utc_now()
        cursor.execute(
            """
            UPDATE catalogue_import_scripts
               SET status='RUNNING', started_at=%s
             WHERE import_run_id=%s AND script_id=%s
            """,
            (started_at, run_id, item["id"]),
        )
        cursor.execute(item["path"].read_text(encoding="utf-8"))
        counts = {table: table_count(cursor, table) for table in item["staging_tables"]}
        cursor.execute(
            """
            UPDATE catalogue_import_scripts
               SET status='SUCCEEDED', finished_at=%s, affected_rows=%s
             WHERE import_run_id=%s AND script_id=%s
            """,
            (utc_now(), json_value(counts), run_id, item["id"]),
        )
        print(f"[sql-seed] executed {item['filename']}: {counts}")


def validate_staging(cursor, manifest: dict, scripts: list[dict]) -> None:
    for item in scripts:
        for table, minimum in item.get("expected_minimum_rows", {}).items():
            actual = table_count(cursor, table)
            if actual < int(minimum):
                raise SeedError(f"{table} contains {actual} rows; expected at least {minimum}")
        for table, expected in item.get("expected_rows", {}).items():
            actual = table_count(cursor, table)
            if actual != int(expected):
                raise SeedError(f"{table} contains {actual} rows; expected exactly {expected}")

    locations = next((item for item in scripts if item["id"] == "locations"), None)
    if locations:
        cursor.execute("""
            SELECT DISTINCT substring(code FROM 1 FOR 6)
              FROM g2p_woreda
             WHERE zone IS NULL
             ORDER BY 1
            """)
        actual_orphans = [row[0] for row in cursor.fetchall()]
        allowed_orphans = sorted(locations.get("allowed_missing_parent_codes", []))
        if actual_orphans != allowed_orphans:
            raise SeedError(
                f"Unexpected geography orphans: actual={actual_orphans}, allowed={allowed_orphans}"
            )

    livestock = next((item for item in scripts if item["id"] == "livestock"), None)
    if livestock:
        required = livestock.get("required_catalogue_values", {}).get("livestock_type", [])
        cursor.execute("SELECT lower(species_code) FROM g2p_livestock_type")
        actual = {row[0] for row in cursor.fetchall()}
        expected_species = set(required)
        if actual != expected_species:
            raise SeedError(
                f"Unexpected livestock types: actual={sorted(actual)}, expected={sorted(expected_species)}"
            )

        cursor.execute("""
            SELECT breed.id, breed.breed_code, livestock.species_code, breed.name
              FROM g2p_livestock_breed breed
              JOIN g2p_livestock_type livestock ON livestock.id = breed.species_id
             ORDER BY breed.id
            """)
        public_breed_codes = [livestock_breed_public_code(*row) for row in cursor.fetchall()]
        if len(public_breed_codes) != len(set(public_breed_codes)):
            raise SeedError("Livestock breeds produce duplicate public codes")

        cursor.execute("SELECT count(*) FROM g2p_livestock_breed WHERE breed_code IS NULL")
        actual_uncoded_breeds = cursor.fetchone()[0]
        expected_uncoded_breeds = int(livestock.get("expected_uncoded_breeds", 0))
        if actual_uncoded_breeds != expected_uncoded_breeds:
            raise SeedError(
                "Unexpected uncoded livestock breed count: "
                f"actual={actual_uncoded_breeds}, expected={expected_uncoded_breeds}"
            )

        cursor.execute("""
            SELECT production.code
              FROM g2p_livestock_production_type production
             WHERE NOT EXISTS (
                   SELECT 1
                     FROM g2p_livestock_production_type_species valid_species
                    WHERE valid_species.production_type_code = production.code
             )
             ORDER BY production.code
            """)
        actual_unlinked = [row[0] for row in cursor.fetchall()]
        expected_unlinked = sorted(livestock.get("allowed_unlinked_production_types", []))
        if actual_unlinked != expected_unlinked:
            raise SeedError(
                "Unexpected unlinked livestock production types: "
                f"actual={actual_unlinked}, expected={expected_unlinked}"
            )

        cursor.execute("""
            SELECT code
              FROM g2p_livestock_record_status
             WHERE is_live_master_data
             ORDER BY code
            """)
        actual_live_statuses = [row[0] for row in cursor.fetchall()]
        expected_live_statuses = sorted(livestock.get("expected_live_record_statuses", []))
        if actual_live_statuses != expected_live_statuses:
            raise SeedError(
                "Unexpected live livestock record statuses: "
                f"actual={actual_live_statuses}, expected={expected_live_statuses}"
            )

        cursor.execute("""
            SELECT count(*)
              FROM g2p_livestock_location_type
             WHERE ecological_zone_id IS NULL
            """)
        if cursor.fetchone()[0]:
            raise SeedError("Livestock location types must resolve to ecological zones")

        cursor.execute("""
            SELECT count(*)
              FROM g2p_livestock_body_condition
             WHERE code <> 'BCS' || bcs_score::text
            """)
        if cursor.fetchone()[0]:
            raise SeedError("Livestock body-condition codes and scores disagree")

        expected_registry_flags = livestock.get("expected_registry_validation_rows", {})
        for flag, expected_count in expected_registry_flags.items():
            if flag not in {
                "breed_unrecognised",
                "breed_outside_national_standard",
                "breed_species_mismatch",
                "production_type_species_mismatch",
            }:
                raise SeedError(f"Unsupported livestock registry validation flag: {flag}")
            cursor.execute(f"SELECT count(*) FROM g2p_livestock_registry_validation WHERE {flag}")
            actual_count = cursor.fetchone()[0]
            if actual_count != int(expected_count):
                raise SeedError(f"Unexpected {flag} count: actual={actual_count}, expected={expected_count}")

    cursor.execute("""
        SELECT count(*)
          FROM g2p_crop crop
         WHERE crop.category_id IS NOT NULL
           AND NOT EXISTS (
               SELECT 1 FROM g2p_crop_category category
                WHERE category.id = crop.category_id
           )
        """)
    orphan_crop_categories = cursor.fetchone()[0]
    if orphan_crop_categories:
        raise SeedError(f"Found {orphan_crop_categories} crops with unknown categories")

    crops = next((item for item in scripts if item["id"] == "crops"), None)
    if crops:
        for field, column in (
            ("expected_record_source_rows", "record_source"),
            ("expected_taxonomy_match_status_rows", "taxonomy_match_status"),
            ("expected_varieties_count_source_rows", "varieties_count_source"),
            ("expected_category_source_rows", "category_source"),
        ):
            expected = {str(key): int(value) for key, value in crops.get(field, {}).items()}
            cursor.execute(
                sql.SQL("""
                SELECT {column}, count(*)
                  FROM g2p_crop
                 GROUP BY {column}
                 ORDER BY {column}
                """).format(column=sql.Identifier(column))
            )
            actual = {str(key): int(value) for key, value in cursor.fetchall()}
            if actual != expected:
                raise SeedError(f"Unexpected crop {column} counts: actual={actual}, expected={expected}")

        cursor.execute("""
            SELECT count(*)
              FROM g2p_crop crop
             WHERE (crop.taxonomy_match_status = 'MATCHED'
                    AND (crop.taxonomy_type_code IS NULL OR NOT EXISTS (
                        SELECT 1
                          FROM g2p_crop_taxonomy_type taxonomy
                         WHERE taxonomy.type_code = crop.taxonomy_type_code
                    )))
                OR (crop.taxonomy_match_status = 'UNRESOLVED'
                    AND crop.taxonomy_type_code IS NOT NULL)
            """)
        if cursor.fetchone()[0]:
            raise SeedError("Crop taxonomy match status and type references disagree")

        cursor.execute("""
            SELECT count(*)
              FROM g2p_crop_taxonomy_type crop_type
             WHERE NOT EXISTS (
                   SELECT 1
                     FROM g2p_crop crop
                    WHERE crop.taxonomy_type_code = crop_type.type_code
                      AND crop.category_id IS NOT NULL
             )
            """)
        if cursor.fetchone()[0]:
            raise SeedError("Every crop type must resolve to an SQL crop category")

    cursor.execute("""
        SELECT count(*)
          FROM g2p_crop crop
         WHERE (crop.varieties_count_source = 'SQL_CROP_VARIETY'
                AND crop.varieties_count <> (
                    SELECT count(*)
                      FROM g2p_seed_variety_source_record variety
                     WHERE variety.seed_crop_id = crop.id
                ))
            OR (crop.varieties_count_source = 'WORKBOOK_CROP_VARIETY'
                AND crop.varieties_count <> (
                    SELECT count(*)
                      FROM g2p_crop_variety variety
                     WHERE variety.type_code = crop.taxonomy_type_code
                ))
            OR crop.varieties_count_source NOT IN (
                'SQL_CROP_VARIETY', 'WORKBOOK_CROP_VARIETY'
            )
        """)
    if cursor.fetchone()[0]:
        raise SeedError("One or more computed crop varieties_count values are stale")

    cursor.execute("""
        SELECT count(*)
          FROM g2p_crop crop
         WHERE crop.preferred_ecological_zone_id IS NOT NULL
           AND NOT EXISTS (
               SELECT 1 FROM g2p_ecological_zone zone
                WHERE zone.id = crop.preferred_ecological_zone_id
           )
        """)
    orphan_ecological_zones = cursor.fetchone()[0]
    if orphan_ecological_zones:
        raise SeedError(f"Found {orphan_ecological_zones} crops with unknown preferred ecological zones")

    cursor.execute("""
        SELECT count(*)
          FROM g2p_seed_demand_trend_by_crop demand
         WHERE NOT EXISTS (
               SELECT 1 FROM g2p_seed_catalog seed WHERE seed.id = demand.crop_id
         )
        """)
    orphan_seed_facts = cursor.fetchone()[0]
    if orphan_seed_facts:
        raise SeedError(f"Found {orphan_seed_facts} seed-demand rows with unknown crops")

    crop_taxonomy = next((item for item in scripts if item["id"] == "crop-taxonomy"), None)
    if crop_taxonomy:
        cursor.execute("""
            SELECT type_code
              FROM g2p_crop_taxonomy_type
             WHERE source_id IS NULL
             ORDER BY type_code
            """)
        missing_source_ids = [row[0] for row in cursor.fetchall()]
        allowed_missing_source_ids = sorted(crop_taxonomy.get("allowed_missing_type_source_ids", []))
        if missing_source_ids != allowed_missing_source_ids:
            raise SeedError(
                "Unexpected crop types without source IDs: "
                f"actual={missing_source_ids}, allowed={allowed_missing_source_ids}"
            )

        cursor.execute("""
            SELECT count(*)
              FROM g2p_crop_variety variety
             WHERE NOT EXISTS (
                   SELECT 1
                     FROM g2p_crop_variety_source_record source_record
                    WHERE source_record.variety_code = variety.variety_code
             )
            """)
        varieties_without_sources = cursor.fetchone()[0]
        if varieties_without_sources:
            raise SeedError(f"Found {varieties_without_sources} crop varieties without source records")

    seed_variety_matches = next(
        (item for item in scripts if item["id"] == "seed-variety-matches"),
        None,
    )
    if seed_variety_matches:
        for field, column in (
            ("expected_match_status_rows", "match_status"),
            ("expected_match_method_rows", "match_method"),
        ):
            expected = {str(key): int(value) for key, value in seed_variety_matches.get(field, {}).items()}
            cursor.execute(
                sql.SQL("""
                SELECT {column}, count(*)
                  FROM g2p_seed_variety_source_record
                 GROUP BY {column}
                 ORDER BY {column}
                """).format(column=sql.Identifier(column))
            )
            actual = {str(key): int(value) for key, value in cursor.fetchall()}
            if actual != expected:
                raise SeedError(
                    f"Unexpected seed-variety {column} counts: actual={actual}, expected={expected}"
                )

        expected_union = int(seed_variety_matches["expected_consolidated_crop_variety_rows"])
        cursor.execute("""
            SELECT (SELECT count(*) FROM g2p_crop_variety)
                 + (SELECT count(*)
                      FROM g2p_seed_variety_source_record
                     WHERE match_status <> 'MATCHED')
            """)
        actual_union = cursor.fetchone()[0]
        if actual_union != expected_union:
            raise SeedError(
                "Unexpected consolidated crop-variety count: "
                f"actual={actual_union}, expected={expected_union}"
            )

    kebeles = next((item for item in scripts if item["id"] == "kebeles"), None)
    if kebeles:
        for field, column in (
            ("expected_match_status_rows", "match_status"),
            ("expected_match_method_rows", "match_method"),
        ):
            expected = {str(key): int(value) for key, value in kebeles.get(field, {}).items()}
            cursor.execute(
                sql.SQL("""
                SELECT {column}, count(*)
                  FROM g2p_kebele
                 GROUP BY {column}
                 ORDER BY {column}
                """).format(column=sql.Identifier(column))
            )
            actual = {str(key): int(value) for key, value in cursor.fetchall()}
            if actual != expected:
                raise SeedError(f"Unexpected kebele {column} counts: actual={actual}, expected={expected}")


def insert_catalogue(cursor, release_id: str, code: str, display_name: str) -> str:
    catalogue_id = stable_id("catalogue", release_id, code)
    cursor.execute(
        """
        INSERT INTO catalogues
          (catalogue_id, release_id, code, domain, display_name,
           display_name_i18n, is_hierarchical, status)
        VALUES (%s, %s, %s, 'agriculture', %s, '{}'::jsonb, false, 'ACTIVE')
        """,
        (catalogue_id, release_id, code, display_name),
    )
    return catalogue_id


def publish_reference_catalogue(
    cursor,
    release_id: str,
    catalogue_code: str,
    display_name: str,
    staging_table: str,
) -> tuple[str, dict[int, str]]:
    catalogue_id = insert_catalogue(cursor, release_id, catalogue_code, display_name)
    cursor.execute(
        sql.SQL("SELECT id, name, description FROM {} ORDER BY id").format(sql.Identifier(staging_table))
    )
    rows = []
    value_ids = {}
    for source_id, name, description in cursor.fetchall():
        value_id = stable_id("value", catalogue_id, source_id)
        value_ids[source_id] = value_id
        rows.append(
            (
                value_id,
                catalogue_id,
                str(source_id),
                name,
                json.dumps({}),
                json.dumps([]),
                "ACTIVE",
                json.dumps(
                    {"source_id": source_id, "description": description},
                    default=json_default,
                ),
            )
        )
    psycopg2.extras.execute_values(
        cursor,
        """
        INSERT INTO catalogue_values
          (catalogue_value_id, catalogue_id, code, display_name,
           display_name_i18n, semantic_roles, status, metadata)
        VALUES %s
        """,
        rows,
    )
    return catalogue_id, value_ids


def publish_crop_taxonomy(
    cursor,
    release_id: str,
    sql_category_value_ids: dict[int, str],
    crop_value_ids: dict[int, str],
    crop_ids_by_type: dict[str, list[int]],
    crop_category_ids_by_type: dict[str, list[int]],
) -> None:
    """Publish the Excel taxonomy and connect it to the consolidated SQL hierarchy."""
    category_catalogue_id = insert_catalogue(
        cursor, release_id, "crop_taxonomy_category", "Crop Taxonomy Category"
    )
    cursor.execute("""
        SELECT category_code, source_id, display_name, display_name_i18n,
               image_url, description, status
          FROM g2p_crop_taxonomy_category
         ORDER BY category_code
        """)
    taxonomy_category_value_ids: dict[str, str] = {}
    category_rows = []
    for row in cursor.fetchall():
        value_id = stable_id("value", category_catalogue_id, row[0])
        taxonomy_category_value_ids[row[0]] = value_id
        category_rows.append(
            (
                value_id,
                category_catalogue_id,
                row[0],
                row[2],
                json.dumps(row[3] or {}, ensure_ascii=False),
                json.dumps(["crop_category"]),
                row[6],
                json.dumps(
                    {
                        "source_id": row[1],
                        "image_url": row[4],
                        "description": row[5],
                    },
                    default=json_default,
                ),
            )
        )
    psycopg2.extras.execute_values(
        cursor,
        """
        INSERT INTO catalogue_values
          (catalogue_value_id, catalogue_id, code, display_name,
           display_name_i18n, semantic_roles, status, metadata)
        VALUES %s
        """,
        category_rows,
    )

    type_catalogue_id = insert_catalogue(cursor, release_id, "crop_type", "Crop Type")
    cursor.execute("""
        SELECT type_code, source_id, category_code, display_name,
               display_name_i18n, scientific_name, centre, image_url,
               description, source_reported_variety_count, status
          FROM g2p_crop_taxonomy_type
         ORDER BY type_code
        """)
    type_value_ids: dict[str, str] = {}
    type_rows = []
    type_relation_rows = []
    for row in cursor.fetchall():
        value_id = stable_id("value", type_catalogue_id, row[0])
        type_value_ids[row[0]] = value_id
        type_rows.append(
            (
                value_id,
                type_catalogue_id,
                row[0],
                row[3],
                json.dumps(row[4] or {}, ensure_ascii=False),
                json.dumps(["crop_type"]),
                row[10],
                json.dumps(
                    {
                        "source_id": row[1],
                        "scientific_name": row[5],
                        "centre": row[6],
                        "image_url": row[7],
                        "description": row[8],
                        "source_reported_variety_count": row[9],
                    },
                    default=json_default,
                ),
            )
        )
        target_id = taxonomy_category_value_ids[row[2]]
        type_relation_rows.append(
            (
                stable_id("relation", value_id, "category", target_id),
                value_id,
                "category",
                target_id,
            )
        )
        for category_id in crop_category_ids_by_type.get(row[0], []):
            sql_category_target_id = sql_category_value_ids[category_id]
            type_relation_rows.append(
                (
                    stable_id("relation", value_id, "category", sql_category_target_id),
                    value_id,
                    "category",
                    sql_category_target_id,
                )
            )
    psycopg2.extras.execute_values(
        cursor,
        """
        INSERT INTO catalogue_values
          (catalogue_value_id, catalogue_id, code, display_name,
           display_name_i18n, semantic_roles, status, metadata)
        VALUES %s
        """,
        type_rows,
        page_size=500,
    )
    psycopg2.extras.execute_values(
        cursor,
        """
        INSERT INTO catalogue_value_relations
          (relation_id, source_value_id, relation_type, target_value_id)
        VALUES %s
        """,
        type_relation_rows,
        page_size=500,
    )

    variety_catalogue_id = insert_catalogue(cursor, release_id, "crop_variety", "Crop Variety")
    cursor.execute("""
        SELECT variety.variety_code, variety.type_code, variety.display_name,
               variety.display_name_i18n, variety.status,
               count(source_record.source_record_code) AS source_record_count
          FROM g2p_crop_variety variety
          LEFT JOIN g2p_crop_variety_source_record source_record
            ON source_record.variety_code = variety.variety_code
         GROUP BY variety.variety_code, variety.type_code, variety.display_name,
                  variety.display_name_i18n, variety.status
         ORDER BY variety.variety_code
        """)
    variety_value_ids: dict[str, str] = {}
    variety_rows = []
    variety_relation_rows = []
    for row in cursor.fetchall():
        value_id = stable_id("value", variety_catalogue_id, row[0])
        variety_value_ids[row[0]] = value_id
        variety_rows.append(
            (
                value_id,
                variety_catalogue_id,
                row[0],
                row[2],
                json.dumps(row[3] or {}, ensure_ascii=False),
                json.dumps(["crop_variety"]),
                row[4],
                json.dumps({"source_record_count": row[5]}, default=json_default),
            )
        )
        target_id = type_value_ids[row[1]]
        variety_relation_rows.append(
            (
                stable_id("relation", value_id, "crop_type", target_id),
                value_id,
                "crop_type",
                target_id,
            )
        )
        for crop_id in crop_ids_by_type.get(row[1], []):
            crop_target_id = crop_value_ids[crop_id]
            variety_relation_rows.append(
                (
                    stable_id("relation", value_id, "crop", crop_target_id),
                    value_id,
                    "crop",
                    crop_target_id,
                )
            )
    psycopg2.extras.execute_values(
        cursor,
        """
        INSERT INTO catalogue_values
          (catalogue_value_id, catalogue_id, code, display_name,
           display_name_i18n, semantic_roles, status, metadata)
        VALUES %s
        """,
        variety_rows,
        page_size=500,
    )
    psycopg2.extras.execute_values(
        cursor,
        """
        INSERT INTO catalogue_value_relations
          (relation_id, source_value_id, relation_type, target_value_id)
        VALUES %s
        """,
        variety_relation_rows,
        page_size=500,
    )

    publish_crop_variety_details(
        cursor,
        release_id,
        taxonomy_category_value_ids,
        variety_value_ids,
    )


def publish_crop_variety_details(
    cursor,
    release_id: str,
    category_value_ids: dict[str, str],
    variety_value_ids: dict[str, str],
) -> None:
    definition_ids: dict[str, str] = {}
    cursor.execute("""
        SELECT characteristic_code, display_name, value_type,
               default_unit_code, applicable_category_code, description
          FROM g2p_crop_characteristic_definition
         ORDER BY characteristic_code
        """)
    definition_rows = []
    for row in cursor.fetchall():
        definition_id = stable_id("crop-characteristic-definition", release_id, row[0])
        definition_ids[row[0]] = definition_id
        definition_rows.append(
            (
                definition_id,
                release_id,
                row[0],
                row[1],
                row[2],
                row[3],
                category_value_ids.get(row[4]),
                row[5],
            )
        )
    psycopg2.extras.execute_values(
        cursor,
        """
        INSERT INTO crop_characteristic_definitions
          (characteristic_definition_id, release_id, characteristic_code,
           display_name, value_type, default_unit_code,
           applicable_category_value_id, description)
        VALUES %s
        """,
        definition_rows,
        page_size=500,
    )

    cursor.execute("""
        SELECT source.source_record_code, source.variety_code,
               source.source_row_number, source.centre, source.release_year_raw,
               source.release_year, source.source_url, source.altitude_min_m,
               source.altitude_max_m, source.rainfall_min_mm,
               source.rainfall_max_mm, source.days_to_maturity_min,
               source.days_to_maturity_max, source.yield_research_min_qt_ha,
               source.yield_research_max_qt_ha, source.yield_farmer_min_qt_ha,
               source.yield_farmer_max_qt_ha, source.seed_rate_kg_ha,
               source.adaptation_area, source.planting_date_text,
               source.crop_pest_reaction
          FROM g2p_crop_variety_source_record source
         ORDER BY source.source_record_code
        """)
    source_record_ids: dict[str, str] = {}
    source_rows = []
    for row in cursor.fetchall():
        source_record_id = stable_id("crop-variety-source-record", release_id, row[0])
        source_record_ids[row[0]] = source_record_id
        source_rows.append(
            (
                source_record_id,
                release_id,
                variety_value_ids[row[1]],
                row[0],
            )
            + row[2:]
        )
    psycopg2.extras.execute_values(
        cursor,
        """
        INSERT INTO crop_variety_source_records
          (variety_source_record_id, release_id, variety_value_id,
           source_record_code, source_row_number, centre, release_year_raw,
           release_year, source_url, altitude_min_m, altitude_max_m,
           rainfall_min_mm, rainfall_max_mm, days_to_maturity_min,
           days_to_maturity_max, yield_research_min_qt_ha,
           yield_research_max_qt_ha, yield_farmer_min_qt_ha,
           yield_farmer_max_qt_ha, seed_rate_kg_ha, adaptation_area,
           planting_date_text, crop_pest_reaction)
        VALUES %s
        """,
        source_rows,
        page_size=500,
    )

    cursor.execute("""
        SELECT source_record_code, characteristic_code, raw_value,
               value_text, value_numeric, value_boolean, value_min,
               value_max, unit_code
          FROM g2p_crop_variety_characteristic
         ORDER BY source_record_code, characteristic_code
        """)
    characteristic_rows = [
        (
            source_record_ids[row[0]],
            definition_ids[row[1]],
        )
        + row[2:]
        for row in cursor.fetchall()
    ]
    psycopg2.extras.execute_values(
        cursor,
        """
        INSERT INTO crop_variety_characteristics
          (variety_source_record_id, characteristic_definition_id,
           raw_value, value_text, value_numeric, value_boolean,
           value_min, value_max, unit_code)
        VALUES %s
        """,
        characteristic_rows,
        page_size=500,
    )


def publish_seed_varieties(
    cursor,
    release_id: str,
    seed_crop_value_ids: dict[int, str],
    crop_value_ids: dict[int, str],
) -> None:
    """Publish Ethio-Seed listings and merge them into crop_variety."""
    seed_variety_catalogue_id = insert_catalogue(cursor, release_id, "seed_variety", "Seed Variety")
    crop_variety_catalogue_id = stable_id("catalogue", release_id, "crop_variety")
    crop_type_catalogue_id = stable_id("catalogue", release_id, "crop_type")
    category_catalogue_id = stable_id("catalogue", release_id, "crop_taxonomy_category")

    cursor.execute("""
        SELECT seed.source_variety_id, seed.seed_crop_id, seed.crop_name_raw,
               seed.common_name_raw, seed.category_raw, seed.release_year,
               seed.release_date, seed.release_raw, seed.maintainer,
               seed.source_classification, seed.details_url,
               seed.matched_variety_code, seed.match_method, seed.match_status,
               seed.review_note, variety.type_code, crop_type.category_code
               , seed.crop_id
          FROM g2p_seed_variety_source_record seed
          LEFT JOIN g2p_crop_variety variety
            ON variety.variety_code = seed.matched_variety_code
          LEFT JOIN g2p_crop_taxonomy_type crop_type
            ON crop_type.type_code = variety.type_code
         ORDER BY seed.source_variety_id
        """)

    value_rows = []
    consolidated_value_rows = []
    relation_rows = []
    source_record_rows = []
    for row in cursor.fetchall():
        source_variety_id = row[0]
        code = f"ethioseed-{source_variety_id}"
        value_id = stable_id("value", seed_variety_catalogue_id, code)
        seed_crop_value_id = seed_crop_value_ids[row[1]]
        crop_value_id = crop_value_ids[row[17]]
        matched_crop_variety_value_id = None
        consolidated_code = row[11] if row[13] == "MATCHED" else code
        consolidated_crop_variety_value_id = stable_id(
            "value", crop_variety_catalogue_id, consolidated_code
        )

        value_rows.append(
            (
                value_id,
                seed_variety_catalogue_id,
                code,
                row[3],
                json.dumps({}),
                json.dumps(["seed_variety"]),
                "ACTIVE",
                json.dumps(
                    {
                        "source_variety_id": source_variety_id,
                        "match_status": row[13],
                        "match_method": row[12],
                    },
                    default=json_default,
                ),
            )
        )
        relation_rows.append(
            (
                stable_id("relation", value_id, "seed_crop", seed_crop_value_id),
                value_id,
                "seed_crop",
                seed_crop_value_id,
            )
        )

        if row[13] != "MATCHED":
            consolidated_value_rows.append(
                (
                    consolidated_crop_variety_value_id,
                    crop_variety_catalogue_id,
                    consolidated_code,
                    row[3],
                    json.dumps({}),
                    json.dumps(["crop_variety"]),
                    "ACTIVE",
                    json.dumps(
                        {
                            "record_source": "SQL_CROP_VARIETY",
                            "source_variety_id": source_variety_id,
                            "crop_name_raw": row[2],
                            "category_raw": row[4],
                            "release_year": row[5],
                            "release_date": row[6],
                            "release_raw": row[7],
                            "maintainer": row[8],
                            "source_classification": row[9],
                            "details_url": row[10],
                            "match_status": row[13],
                            "match_method": row[12],
                            "review_note": row[14],
                        },
                        default=json_default,
                    ),
                )
            )

        relation_rows.append(
            (
                stable_id(
                    "relation",
                    consolidated_crop_variety_value_id,
                    "crop",
                    crop_value_id,
                ),
                consolidated_crop_variety_value_id,
                "crop",
                crop_value_id,
            )
        )

        if row[13] == "MATCHED":
            matched_crop_variety_value_id = stable_id("value", crop_variety_catalogue_id, row[11])
            crop_type_value_id = stable_id("value", crop_type_catalogue_id, row[15])
            category_value_id = stable_id("value", category_catalogue_id, row[16])
            relation_rows.extend(
                (
                    (
                        stable_id(
                            "relation",
                            value_id,
                            "crop_variety",
                            matched_crop_variety_value_id,
                        ),
                        value_id,
                        "crop_variety",
                        matched_crop_variety_value_id,
                    ),
                    (
                        stable_id("relation", value_id, "crop_type", crop_type_value_id),
                        value_id,
                        "crop_type",
                        crop_type_value_id,
                    ),
                    (
                        stable_id("relation", value_id, "category", category_value_id),
                        value_id,
                        "category",
                        category_value_id,
                    ),
                )
            )

        source_record_rows.append(
            (
                stable_id("seed-variety-source-record", release_id, source_variety_id),
                release_id,
                value_id,
                seed_crop_value_id,
                crop_value_id,
                consolidated_crop_variety_value_id,
                matched_crop_variety_value_id,
                source_variety_id,
                row[2],
                row[3],
                row[4],
                row[5],
                row[6],
                row[7],
                row[8],
                row[9],
                row[10],
                row[12],
                row[13],
                row[14],
            )
        )

    psycopg2.extras.execute_values(
        cursor,
        """
        INSERT INTO catalogue_values
          (catalogue_value_id, catalogue_id, code, display_name,
           display_name_i18n, semantic_roles, status, metadata)
        VALUES %s
        """,
        value_rows,
        page_size=500,
    )
    if consolidated_value_rows:
        psycopg2.extras.execute_values(
            cursor,
            """
            INSERT INTO catalogue_values
              (catalogue_value_id, catalogue_id, code, display_name,
               display_name_i18n, semantic_roles, status, metadata)
            VALUES %s
            """,
            consolidated_value_rows,
            page_size=500,
        )
    psycopg2.extras.execute_values(
        cursor,
        """
        INSERT INTO catalogue_value_relations
          (relation_id, source_value_id, relation_type, target_value_id)
        VALUES %s
        ON CONFLICT (source_value_id, relation_type, target_value_id) DO NOTHING
        """,
        relation_rows,
        page_size=500,
    )
    psycopg2.extras.execute_values(
        cursor,
        """
        INSERT INTO seed_variety_source_records
          (seed_variety_source_record_id, release_id, seed_variety_value_id,
           seed_crop_value_id, crop_value_id,
           consolidated_crop_variety_value_id, matched_crop_variety_value_id,
           source_variety_id,
           crop_name_raw, common_name_raw, category_raw, release_year,
           release_date, release_raw, maintainer, source_classification,
           details_url, match_method, match_status, review_note)
        VALUES %s
        """,
        source_record_rows,
        page_size=500,
    )


def insert_catalogue_values(cursor, rows: list[tuple]) -> None:
    if not rows:
        return
    psycopg2.extras.execute_values(
        cursor,
        """
        INSERT INTO catalogue_values
          (catalogue_value_id, catalogue_id, code, display_name,
           display_name_i18n, semantic_roles, status, metadata)
        VALUES %s
        """,
        rows,
        page_size=500,
    )


def insert_catalogue_relations(cursor, rows: list[tuple]) -> None:
    if not rows:
        return
    psycopg2.extras.execute_values(
        cursor,
        """
        INSERT INTO catalogue_value_relations
          (relation_id, source_value_id, relation_type, target_value_id)
        VALUES %s
        """,
        rows,
        page_size=500,
    )


def publish_livestock_catalogues(
    cursor,
    release_id: str,
    ecological_zone_value_ids: dict[int, str],
) -> None:
    species_catalogue_id = insert_catalogue(cursor, release_id, "livestock_type", "Livestock Type")
    cursor.execute("""
        SELECT species_code,
               COALESCE(name, initcap(replace(species_code, '_', ' '))),
               description, icon_url, dataset_id, scientific_name, subfamily,
               species_type_code, chart_color, ear_tag_range,
               in_lis_population, in_etlits_registry
          FROM g2p_livestock_type
         ORDER BY species_code
        """)
    species_value_ids: dict[str, str] = {}
    species_rows = []
    for row in cursor.fetchall():
        value_id = stable_id("value", species_catalogue_id, row[0])
        species_value_ids[row[0]] = value_id
        species_rows.append(
            (
                value_id,
                species_catalogue_id,
                row[0],
                row[1],
                json.dumps({}),
                json.dumps(["livestock_type"]),
                "ACTIVE",
                json.dumps(
                    {
                        "description": row[2],
                        "icon_url": row[3],
                        "dataset_id": row[4],
                        "scientific_name": row[5],
                        "subfamily": row[6],
                        "species_type_code": row[7],
                        "chart_color": row[8],
                        "ear_tag_range": row[9],
                        "in_lis_population": row[10],
                        "in_etlits_registry": row[11],
                    },
                    default=json_default,
                ),
            )
        )
    insert_catalogue_values(cursor, species_rows)

    breed_catalogue_id = insert_catalogue(cursor, release_id, "livestock_breed", "Livestock Breed")
    cursor.execute("""
        SELECT breed.id, breed.breed_code, breed.name, breed.abbreviation,
               species.species_code, breed.breed_type,
               breed.in_national_standard, breed.in_etlits_registry,
               breed.source
          FROM g2p_livestock_breed breed
          JOIN g2p_livestock_type species ON species.id = breed.species_id
         ORDER BY breed.id
        """)
    breed_rows = []
    relation_rows = []
    for row in cursor.fetchall():
        code = livestock_breed_public_code(row[0], row[1], row[4], row[2])
        value_id = stable_id("value", breed_catalogue_id, code)
        breed_rows.append(
            (
                value_id,
                breed_catalogue_id,
                code,
                row[2],
                json.dumps({}),
                json.dumps(["livestock_breed"]),
                "ACTIVE",
                json.dumps(
                    {
                        "source_id": row[0],
                        "breed_code": row[1],
                        "abbreviation": row[3],
                        "breed_type": row[5],
                        "in_national_standard": row[6],
                        "in_etlits_registry": row[7],
                        "source": row[8],
                    },
                    default=json_default,
                ),
            )
        )
        target_id = species_value_ids[row[4]]
        relation_rows.append(
            (
                stable_id("relation", value_id, "species", target_id),
                value_id,
                "species",
                target_id,
            )
        )
    insert_catalogue_values(cursor, breed_rows)

    gender_catalogue_id = insert_catalogue(cursor, release_id, "livestock_gender", "Livestock Gender")
    cursor.execute("""
        SELECT code, name, description, in_etlits_registry
          FROM g2p_livestock_gender
         ORDER BY code
        """)
    gender_rows = [
        (
            stable_id("value", gender_catalogue_id, row[0]),
            gender_catalogue_id,
            row[0],
            row[1],
            json.dumps({}),
            json.dumps(["livestock_gender"]),
            "ACTIVE",
            json.dumps(
                {"description": row[2], "in_etlits_registry": row[3]},
                default=json_default,
            ),
        )
        for row in cursor.fetchall()
    ]
    insert_catalogue_values(cursor, gender_rows)

    location_catalogue_id = insert_catalogue(
        cursor, release_id, "livestock_location_type", "Livestock Location Type"
    )
    cursor.execute("""
        SELECT code, name, ethiopian_zone_name, altitude_description,
               ecological_zone_id, description
          FROM g2p_livestock_location_type
         ORDER BY code
        """)
    location_rows = []
    for row in cursor.fetchall():
        value_id = stable_id("value", location_catalogue_id, row[0])
        location_rows.append(
            (
                value_id,
                location_catalogue_id,
                row[0],
                row[1],
                json.dumps({}),
                json.dumps(["livestock_location_type"]),
                "ACTIVE",
                json.dumps(
                    {
                        "ethiopian_zone_name": row[2],
                        "altitude_description": row[3],
                        "description": row[5],
                    },
                    default=json_default,
                ),
            )
        )
        target_id = ecological_zone_value_ids[row[4]]
        relation_rows.append(
            (
                stable_id("relation", value_id, "ecological_zone", target_id),
                value_id,
                "ecological_zone",
                target_id,
            )
        )
    insert_catalogue_values(cursor, location_rows)

    condition_catalogue_id = insert_catalogue(
        cursor, release_id, "livestock_body_condition", "Livestock Body Condition"
    )
    cursor.execute("""
        SELECT code, bcs_score, condition_label, fatness_label,
               etlits_label, description
          FROM g2p_livestock_body_condition
         ORDER BY bcs_score
        """)
    condition_rows = [
        (
            stable_id("value", condition_catalogue_id, row[0]),
            condition_catalogue_id,
            row[0],
            row[2],
            json.dumps({}),
            json.dumps(["livestock_body_condition"]),
            "ACTIVE",
            json.dumps(
                {
                    "bcs_score": row[1],
                    "condition_label": row[2],
                    "fatness_label": row[3],
                    "etlits_label": row[4],
                    "description": row[5],
                },
                default=json_default,
            ),
        )
        for row in cursor.fetchall()
    ]
    insert_catalogue_values(cursor, condition_rows)

    production_catalogue_id = insert_catalogue(
        cursor, release_id, "livestock_production_type", "Livestock Production Type"
    )
    cursor.execute("""
        SELECT code, name, standard_purpose, in_national_standard,
               in_etlits_registry, description
          FROM g2p_livestock_production_type
         ORDER BY code
        """)
    production_rows = [
        (
            stable_id("value", production_catalogue_id, row[0]),
            production_catalogue_id,
            row[0],
            row[1],
            json.dumps({}),
            json.dumps(["livestock_production_type"]),
            "ACTIVE",
            json.dumps(
                {
                    "standard_purpose": row[2],
                    "in_national_standard": row[3],
                    "in_etlits_registry": row[4],
                    "description": row[5],
                },
                default=json_default,
            ),
        )
        for row in cursor.fetchall()
    ]
    insert_catalogue_values(cursor, production_rows)
    cursor.execute("""
        SELECT valid_species.production_type_code, species.species_code
          FROM g2p_livestock_production_type_species valid_species
          JOIN g2p_livestock_type species ON species.id = valid_species.species_id
         ORDER BY valid_species.production_type_code, species.species_code
        """)
    for production_code, species_code in cursor.fetchall():
        value_id = stable_id("value", production_catalogue_id, production_code)
        target_id = species_value_ids[species_code]
        relation_rows.append(
            (
                stable_id("relation", value_id, "valid_for_species", target_id),
                value_id,
                "valid_for_species",
                target_id,
            )
        )

    status_catalogue_id = insert_catalogue(
        cursor,
        release_id,
        "etlits_livestock_record_status",
        "ET-LITS Livestock Record Status",
    )
    cursor.execute("""
        SELECT code, name, sort_order, is_live_master_data, description
          FROM g2p_livestock_record_status
         ORDER BY sort_order
        """)
    status_rows = [
        (
            stable_id("value", status_catalogue_id, row[0]),
            status_catalogue_id,
            row[0],
            row[1],
            json.dumps({}),
            json.dumps(["etlits_livestock_record_status"]),
            row[2],
            "ACTIVE",
            json.dumps(
                {"is_live_master_data": row[3], "description": row[4]},
                default=json_default,
            ),
        )
        for row in cursor.fetchall()
    ]
    psycopg2.extras.execute_values(
        cursor,
        """
        INSERT INTO catalogue_values
          (catalogue_value_id, catalogue_id, code, display_name,
           display_name_i18n, semantic_roles, sort_order, status, metadata)
        VALUES %s
        """,
        status_rows,
    )
    insert_catalogue_relations(cursor, relation_rows)


def publish_catalogues(cursor, release_id: str) -> None:
    _, category_value_ids = publish_reference_catalogue(
        cursor,
        release_id,
        "crop_category",
        "Crop Category",
        "g2p_crop_category",
    )
    _, ecological_zone_value_ids = publish_reference_catalogue(
        cursor,
        release_id,
        "ecological_zone",
        "Ecological Zone",
        "g2p_ecological_zone",
    )
    crop_catalogue_id = insert_catalogue(cursor, release_id, "crop", "Crop")
    cursor.execute("""
        SELECT id, name, description, category_id, known_for,
               num_field_inspection_needed, isolation_distance,
               preferred_ecological_zone_id, scientific_name, centre,
               varieties_count, image_url, display_name_amh,
               taxonomy_type_code, taxonomy_source_id,
               taxonomy_category_code, taxonomy_description,
               record_source, varieties_count_source,
               taxonomy_match_method, taxonomy_match_status,
               category_source
          FROM g2p_crop ORDER BY id
        """)
    crop_rows = []
    crop_relations = []
    crop_value_ids: dict[int, str] = {}
    crop_ids_by_type: dict[str, list[int]] = {}
    crop_category_ids_by_type: dict[str, list[int]] = {}
    for row in cursor.fetchall():
        metadata = {
            "source_id": row[0],
            "description": row[2],
            "known_for": row[4],
            "num_field_inspection_needed": row[5],
            "isolation_distance": row[6],
            "scientific_name": row[8],
            "centre": row[9],
            "varieties_count": row[10],
            "image_url": row[11],
            "taxonomy_type_code": row[13],
            "taxonomy_source_id": row[14],
            "taxonomy_category_code": row[15],
            "taxonomy_description": row[16],
            "record_source": row[17],
            "varieties_count_source": row[18],
            "taxonomy_match_method": row[19],
            "taxonomy_match_status": row[20],
            "category_source": row[21],
        }
        crop_value_id = stable_id("value", crop_catalogue_id, row[0])
        crop_value_ids[row[0]] = crop_value_id
        if row[13]:
            crop_ids_by_type.setdefault(row[13], []).append(row[0])
            if row[3] is not None:
                category_ids = crop_category_ids_by_type.setdefault(row[13], [])
                if row[3] not in category_ids:
                    category_ids.append(row[3])
        crop_rows.append(
            (
                crop_value_id,
                crop_catalogue_id,
                str(row[0]),
                row[1],
                json.dumps({"am": row[12]} if row[12] else {}, ensure_ascii=False),
                json.dumps(["crop"]),
                "ACTIVE",
                json.dumps(metadata, default=json_default),
            )
        )
        crop_relations.append((crop_value_id, row[3], row[7]))
    psycopg2.extras.execute_values(
        cursor,
        """
        INSERT INTO catalogue_values
          (catalogue_value_id, catalogue_id, code, display_name,
           display_name_i18n, semantic_roles, status, metadata)
        VALUES %s
        """,
        crop_rows,
    )

    relation_rows = []
    for crop_value_id, category_id, ecological_zone_id in crop_relations:
        if category_id is not None:
            target_value_id = category_value_ids[category_id]
            relation_rows.append(
                (
                    stable_id("relation", crop_value_id, "category", target_value_id),
                    crop_value_id,
                    "category",
                    target_value_id,
                )
            )
        if ecological_zone_id is not None:
            target_value_id = ecological_zone_value_ids[ecological_zone_id]
            relation_rows.append(
                (
                    stable_id(
                        "relation",
                        crop_value_id,
                        "preferred_ecological_zone",
                        target_value_id,
                    ),
                    crop_value_id,
                    "preferred_ecological_zone",
                    target_value_id,
                )
            )
    if relation_rows:
        psycopg2.extras.execute_values(
            cursor,
            """
            INSERT INTO catalogue_value_relations
              (relation_id, source_value_id, relation_type, target_value_id)
            VALUES %s
            """,
            relation_rows,
        )

    publish_crop_taxonomy(
        cursor,
        release_id,
        category_value_ids,
        crop_value_ids,
        crop_ids_by_type,
        crop_category_ids_by_type,
    )

    publish_livestock_catalogues(cursor, release_id, ecological_zone_value_ids)

    seed_catalogue_id = insert_catalogue(cursor, release_id, "seed_crop", "Seed Crop")
    cursor.execute("SELECT id, name FROM g2p_seed_catalog ORDER BY id")
    seed_source_rows = cursor.fetchall()
    seed_crop_value_ids = {row[0]: stable_id("value", seed_catalogue_id, row[0]) for row in seed_source_rows}
    seed_rows = [
        (
            seed_crop_value_ids[row[0]],
            seed_catalogue_id,
            str(row[0]),
            row[1],
            json.dumps({}),
            json.dumps([]),
            "ACTIVE",
            json.dumps({"source_id": row[0]}),
        )
        for row in seed_source_rows
    ]
    psycopg2.extras.execute_values(
        cursor,
        """
        INSERT INTO catalogue_values
          (catalogue_value_id, catalogue_id, code, display_name,
           display_name_i18n, semantic_roles, status, metadata)
        VALUES %s
        """,
        seed_rows,
    )
    publish_seed_varieties(
        cursor,
        release_id,
        seed_crop_value_ids,
        crop_value_ids,
    )


def publish_geography(cursor, release_id: str) -> None:
    level_ids = {
        code: stable_id("geography-level", release_id, code)
        for code in ("region", "zone", "woreda", "kebele")
    }
    levels = [
        (level_ids["region"], release_id, "region", "Region", 1, None),
        (level_ids["zone"], release_id, "zone", "Zone", 2, level_ids["region"]),
        (level_ids["woreda"], release_id, "woreda", "Woreda", 3, level_ids["zone"]),
        (level_ids["kebele"], release_id, "kebele", "Kebele", 4, level_ids["woreda"]),
    ]
    psycopg2.extras.execute_values(
        cursor,
        """
        INSERT INTO geography_levels
          (geography_level_id, release_id, code, display_name, level_order, parent_level_id)
        VALUES %s
        """,
        levels,
    )

    cursor.execute("""
        SELECT id, code, name, display_name_amh, admin0_name, admin0_pcod,
               admin1_pcod, admin1_refn
          FROM g2p_region ORDER BY code
        """)
    region_ids: dict[int, str] = {}
    region_rows = []
    for row in cursor.fetchall():
        unit_id = stable_id("geography-unit", release_id, row[1])
        region_ids[row[0]] = unit_id
        metadata = {
            "admin0_name": row[4],
            "admin0_pcod": row[5],
            "admin1_pcod": row[6],
            "admin1_refn": row[7],
        }
        region_rows.append(
            (
                unit_id,
                level_ids["region"],
                row[1],
                row[2],
                row[3],
                None,
                "ACTIVE",
                json_value(metadata),
            )
        )
    psycopg2.extras.execute_values(
        cursor,
        """
        INSERT INTO geography_units
          (geography_unit_id, geography_level_id, code, display_name, display_name_amh,
           parent_unit_id, status, metadata)
        VALUES %s
        """,
        region_rows,
    )

    cursor.execute("""
        SELECT id, code, name, display_name_amh, admin2_pcod, admin2_refn, admin2_altn,
               admin2_al_1, lat, long, shape_length, shape_area, region
          FROM g2p_zone ORDER BY code
        """)
    zone_ids: dict[int, str] = {}
    zone_rows = []
    for row in cursor.fetchall():
        unit_id = stable_id("geography-unit", release_id, row[1])
        zone_ids[row[0]] = unit_id
        metadata = {
            "admin2_pcod": row[4],
            "admin2_refn": row[5],
            "admin2_altn": row[6],
            "admin2_al_1": row[7],
            "shape_length": row[10],
            "shape_area": row[11],
        }
        zone_rows.append(
            (
                unit_id,
                level_ids["zone"],
                row[1],
                row[2],
                row[3],
                region_ids[row[12]],
                row[8],
                row[9],
                "ACTIVE",
                json.dumps(metadata, default=json_default),
            )
        )
    psycopg2.extras.execute_values(
        cursor,
        """
        INSERT INTO geography_units
          (geography_unit_id, geography_level_id, code, display_name, display_name_amh,
           parent_unit_id, latitude, longitude, status, metadata)
        VALUES %s
        """,
        zone_rows,
    )

    cursor.execute("""
        SELECT code, name, display_name_amh, admin3_pcod, admin3_refn, admin3_altn,
               admin3_al_1, shape_length, shape_area, zone
          FROM g2p_woreda ORDER BY code
        """)
    woreda_ids = {}
    woreda_rows = []
    for row in cursor.fetchall():
        metadata = {
            "admin3_pcod": row[3],
            "admin3_refn": row[4],
            "admin3_altn": row[5],
            "admin3_al_1": row[6],
            "shape_length": row[7],
            "shape_area": row[8],
        }
        unit_id = stable_id("geography-unit", release_id, row[0])
        woreda_ids[row[0]] = unit_id
        woreda_rows.append(
            (
                unit_id,
                level_ids["woreda"],
                row[0],
                row[1],
                row[2],
                zone_ids.get(row[9]),
                "ACTIVE",
                json.dumps(
                    metadata
                    | (
                        {
                            "data_quality": "MISSING_PARENT",
                            "source_parent_code": row[0][:6],
                        }
                        if row[9] is None
                        else {}
                    ),
                    default=json_default,
                ),
            )
        )
    psycopg2.extras.execute_values(
        cursor,
        """
        INSERT INTO geography_units
          (geography_unit_id, geography_level_id, code, display_name, display_name_amh,
           parent_unit_id, status, metadata)
        VALUES %s
        """,
        woreda_rows,
        page_size=500,
    )

    cursor.execute("""
        SELECT code, display_name, display_name_amh, source_code,
               source_region_code, source_zone_code, source_woreda_code,
               matched_woreda_code, match_method, match_status, review_note
          FROM g2p_kebele
         WHERE match_status = 'MATCHED'
         ORDER BY code
        """)
    kebele_rows = []
    for row in cursor.fetchall():
        kebele_rows.append(
            (
                stable_id("geography-unit", release_id, row[0]),
                level_ids["kebele"],
                row[0],
                row[1],
                row[2],
                woreda_ids[row[7]],
                "ACTIVE",
                json.dumps(
                    {
                        "source_code": row[3],
                        "source_region_code": row[4],
                        "source_zone_code": row[5],
                        "source_woreda_code": row[6],
                        "match_method": row[8],
                        "match_status": row[9],
                        "review_note": row[10],
                    },
                    default=json_default,
                ),
            )
        )
    psycopg2.extras.execute_values(
        cursor,
        """
        INSERT INTO geography_units
          (geography_unit_id, geography_level_id, code, display_name,
           display_name_amh, parent_unit_id, status, metadata)
        VALUES %s
        """,
        kebele_rows,
        page_size=500,
    )


def publish_statistics(cursor, release_id: str, source: str | None) -> None:
    cursor.execute("""
        SELECT livestock.species_code, population.census_year,
               population.population_total, population.source_record_count
          FROM g2p_livestock_population population
          JOIN g2p_livestock_type livestock ON livestock.id = population.species_code
         ORDER BY livestock.species_code, population.census_year
        """)
    rows = [
        (
            stable_id("livestock-stat", release_id, row[0], row[1]),
            release_id,
            row[0],
            row[1],
            row[2],
            row[3],
            source,
        )
        for row in cursor.fetchall()
    ]
    psycopg2.extras.execute_values(
        cursor,
        """
        INSERT INTO livestock_population_statistics
          (statistic_id, release_id, species_code, census_year,
           population_total, source_record_count, source)
        VALUES %s
        """,
        rows,
    )
    cursor.execute("""
        SELECT budget_year, total_entries, total_quantity_demanded,
               average_quantity_per_entry, total_estimated_land_ha,
               average_estimated_land_ha
          FROM g2p_seed_demand_summary ORDER BY budget_year
        """)
    rows = [(stable_id("seed-summary", release_id, row[0]), release_id) + row for row in cursor.fetchall()]
    psycopg2.extras.execute_values(
        cursor,
        """
        INSERT INTO seed_demand_summary_statistics
          (statistic_id, release_id, budget_year, total_entries,
           total_quantity_demanded, average_quantity_per_entry,
           total_estimated_land_ha, average_estimated_land_ha)
        VALUES %s
        """,
        rows,
    )
    cursor.execute("""
        SELECT budget_year, seed_class, quantity_demanded
          FROM g2p_seed_demand_trend ORDER BY budget_year, seed_class
        """)
    rows = [
        (stable_id("seed-trend", release_id, row[0], row[1]), release_id) + row for row in cursor.fetchall()
    ]
    psycopg2.extras.execute_values(
        cursor,
        """
        INSERT INTO seed_demand_trend_statistics
          (statistic_id, release_id, budget_year, seed_class, quantity_demanded)
        VALUES %s
        """,
        rows,
    )

    cursor.execute("""
        SELECT crop_id, crop_name, budget_year, seed_class, quantity_demanded
          FROM g2p_seed_demand_trend_by_crop
         ORDER BY crop_id, budget_year, seed_class
        """)
    rows = [
        (
            stable_id("seed-crop-stat", release_id, row[0], row[2], row[3]),
            release_id,
            str(row[0]),
            row[1],
            row[2],
            row[3],
            row[4],
        )
        for row in cursor.fetchall()
    ]
    psycopg2.extras.execute_values(
        cursor,
        """
        INSERT INTO seed_demand_by_crop_statistics
          (statistic_id, release_id, crop_code, crop_name, budget_year,
           seed_class, quantity_demanded)
        VALUES %s
        """,
        rows,
    )


def publish_livestock_registry(cursor, release_id: str) -> None:
    cursor.execute("""
        SELECT registry.id,
               registry.species_code,
               registry.breed_name,
               registry.breed_id,
               breed.breed_code,
               breed_species.species_code,
               breed.in_national_standard,
               registry.gender_code,
               registry.location_type_code,
               registry.body_condition_code,
               registry.production_type_code,
               registry.status,
               registry.created_on,
               registry.updated_on,
               NOT validation.production_type_species_mismatch
          FROM g2p_livestock_registry_entry registry
          JOIN g2p_livestock_registry_validation validation
            ON validation.id = registry.id
          LEFT JOIN g2p_livestock_breed breed
            ON breed.id = registry.breed_id
          LEFT JOIN g2p_livestock_type breed_species
            ON breed_species.id = breed.species_id
         ORDER BY registry.id
        """)
    rows = [
        (
            stable_id("livestock-registry", release_id, row[0]),
            release_id,
        )
        + row
        for row in cursor.fetchall()
    ]
    psycopg2.extras.execute_values(
        cursor,
        """
        INSERT INTO livestock_registry_entries
          (registry_entry_id, release_id, source_entry_id, species_code,
           breed_name, breed_source_id, breed_code, breed_species_code,
           breed_in_national_standard, gender_code, location_type_code,
           body_condition_code, production_type_code, status,
           source_created_on, source_updated_on,
           production_type_species_valid)
        VALUES %s
        """,
        rows,
    )


def publish_release(cursor, manifest: dict, checksum: str, scripts: list[dict]) -> str:
    country = str(manifest["country_code"]).upper()
    version = str(manifest["source_version"])
    release_id = stable_id("release", country, version)
    release_manifest = {key: value for key, value in manifest.items() if key != "scripts"}
    release_manifest["scripts"] = [
        {key: value for key, value in item.items() if key != "path"}
        | {"checksum": file_checksum(item["path"])}
        for item in scripts
    ]
    cursor.execute(
        """
        INSERT INTO catalogue_releases
          (release_id, country_code, version, schema_version, checksum,
           source, status, manifest, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, 'STAGED', %s, %s)
        """,
        (
            release_id,
            country,
            version,
            str(manifest["schema_version"]),
            checksum,
            manifest.get("source"),
            json_value(release_manifest),
            utc_now(),
        ),
    )

    publish_catalogues(cursor, release_id)
    publish_geography(cursor, release_id)
    publish_statistics(cursor, release_id, manifest.get("source"))
    publish_livestock_registry(cursor, release_id)

    cursor.execute(
        """
        UPDATE catalogue_releases
           SET status='RETIRED'
         WHERE country_code=%s AND status='ACTIVE' AND release_id<>%s
        """,
        (country, release_id),
    )
    cursor.execute(
        """
        UPDATE catalogue_releases
           SET status='ACTIVE', activated_at=%s
         WHERE release_id=%s
        """,
        (utc_now(), release_id),
    )
    return release_id


def mark_failed(
    conn,
    run_id: str,
    script_id: str | None,
    execution_completed: bool,
    error: Exception,
) -> None:
    with conn.cursor() as cursor:
        if script_id:
            cursor.execute(
                """
                SELECT execution_order
                  FROM catalogue_import_scripts
                 WHERE import_run_id=%s AND script_id=%s
                """,
                (run_id, script_id),
            )
            failed_order = cursor.fetchone()[0]
            cursor.execute(
                """
                UPDATE catalogue_import_scripts
                   SET status=CASE
                       WHEN execution_order < %s THEN 'ROLLED_BACK'
                       WHEN execution_order > %s THEN 'NOT_RUN'
                       ELSE status
                   END,
                       finished_at=CASE WHEN execution_order < %s THEN %s ELSE finished_at END
                 WHERE import_run_id=%s AND script_id<>%s
                """,
                (
                    failed_order,
                    failed_order,
                    failed_order,
                    utc_now(),
                    run_id,
                    script_id,
                ),
            )
            cursor.execute(
                """
                UPDATE catalogue_import_scripts
                   SET status='FAILED', finished_at=%s, error=%s
                 WHERE import_run_id=%s AND script_id=%s
                """,
                (utc_now(), str(error), run_id, script_id),
            )
        elif execution_completed:
            cursor.execute(
                """
                UPDATE catalogue_import_scripts
                   SET status='ROLLED_BACK', finished_at=%s
                 WHERE import_run_id=%s
                """,
                (utc_now(), run_id),
            )
        else:
            cursor.execute(
                """
                UPDATE catalogue_import_scripts
                   SET status='NOT_RUN', finished_at=%s
                 WHERE import_run_id=%s
                """,
                (utc_now(), run_id),
            )
        cursor.execute(
            """
            UPDATE catalogue_import_runs
               SET status='FAILED', finished_at=%s, error_summary=%s
             WHERE import_run_id=%s
            """,
            (utc_now(), str(error), run_id),
        )
    conn.commit()


def run(conn, manifest: dict, scripts: list[dict], checksum: str, trigger: str) -> None:
    run_id = record_run(conn, manifest, scripts, checksum, trigger)
    current_script_id: str | None = None
    execution_completed = False
    try:
        with conn, conn.cursor() as cursor:
            existing_release = active_release_for_source(conn, manifest, checksum)
            if existing_release and existing_release[2] == "ACTIVE":
                mark_skipped(conn, run_id, existing_release[0])
                print(f"[sql-seed] {manifest['source_version']} is already active; skipped")
                return
            if existing_release:
                raise SeedError(
                    f"Release {manifest['source_version']} already exists in state {existing_release[2]}"
                )

            cursor.execute(
                "UPDATE catalogue_import_runs SET status='RUNNING' WHERE import_run_id=%s",
                (run_id,),
            )
            truncate_staging(cursor, scripts)
            for item in scripts:
                current_script_id = item["id"]
                execute_scripts(cursor, run_id, [item])
            current_script_id = None
            execution_completed = True
            cursor.execute(
                "UPDATE catalogue_import_runs SET status='VALIDATING' WHERE import_run_id=%s",
                (run_id,),
            )
            validate_staging(cursor, manifest, scripts)
            cursor.execute(
                "UPDATE catalogue_import_runs SET status='PUBLISHING' WHERE import_run_id=%s",
                (run_id,),
            )
            release_id = publish_release(cursor, manifest, checksum, scripts)
            cursor.execute(
                """
                    UPDATE catalogue_import_runs
                       SET release_id=%s, status='PUBLISHED', finished_at=%s
                     WHERE import_run_id=%s
                    """,
                (release_id, utc_now(), run_id),
            )
        print(f"[sql-seed] published {manifest['country_code']}/{manifest['source_version']}")
    except Exception as error:
        conn.rollback()
        mark_failed(conn, run_id, current_script_id, execution_completed, error)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--expected-country")
    parser.add_argument(
        "--trigger",
        choices=("MANUAL", "HELM", "SCHEDULED"),
        default=os.environ.get("SQL_SEED_TRIGGER", "MANUAL").upper(),
    )
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    manifest = load_manifest(manifest_path)
    scripts = validate_manifest(manifest, manifest_path)
    if args.expected_country and str(manifest["country_code"]).upper() != args.expected_country.upper():
        raise SeedError(
            f"Manifest country {manifest['country_code']} does not match "
            f"deployment country {args.expected_country}"
        )
    checksum = manifest_checksum(manifest_path, scripts)
    print(f"[sql-seed] validated {len(scripts)} scripts; checksum={checksum}")
    if args.validate_only:
        return

    conn = connect()
    locked = False
    try:
        acquire_lock(conn)
        locked = True
        run(conn, manifest, scripts, checksum, args.trigger)
    finally:
        if locked:
            conn.rollback()
            release_lock(conn)
        conn.close()


if __name__ == "__main__":
    main()
