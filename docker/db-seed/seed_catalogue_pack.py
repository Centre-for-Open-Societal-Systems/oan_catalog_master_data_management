#!/usr/bin/env python3
"""Validate and atomically publish a catalogue pack."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
import psycopg2.extras

NAMESPACE = uuid.UUID("cc1a77af-f811-44ed-867f-890c45cc99ae")


class PackValidationError(ValueError):
    pass


def read_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def normalized_catalogue(document: dict, domain: str | None = None) -> dict:
    """Accept the new catalogue contract and the reference repo's codelist shape."""
    code = document.get("code") or document.get("attribute_code") or document.get("attribute_id")
    display_name = document.get("display_name") or document.get("attribute_display") or code
    source_to_code = {
        value.get("value_id") or value.get("code") or value.get("value_code"): (
            value.get("code") or value.get("value_code") or value.get("value_id")
        )
        for value in document.get("values", [])
    }
    values = []
    for value in document.get("values", []):
        value_code = value.get("code") or value.get("value_code") or value.get("value_id")
        parent = value.get("parent_code") or value.get("parent_value_id")
        values.append(
            {
                "code": value_code,
                "parent_code": source_to_code.get(parent, parent),
                "display_name": value.get("display_name") or value.get("value_display") or value_code,
                "display_name_i18n": value.get("display_name_i18n") or value.get("display_i18n") or {},
                "semantic_roles": value.get("semantic_roles") or value.get("roles") or [],
                "sort_order": value.get("sort_order"),
                "valid_from": value.get("valid_from"),
                "valid_to": value.get("valid_to"),
                "status": value.get("status", "ACTIVE"),
                "metadata": value.get("metadata") or {},
            }
        )
    return {
        "code": code,
        "domain": document.get("domain", domain),
        "display_name": display_name,
        "display_name_i18n": document.get("display_name_i18n") or document.get("display_i18n") or {},
        "is_hierarchical": bool(document.get("is_hierarchical", document.get("hierarchical", False))),
        "status": document.get("status", "ACTIVE"),
        "values": values,
    }


def load_pack(pack_dir: Path, domains: list[str]) -> tuple[dict, list[dict]]:
    manifest_path = pack_dir / "manifest.json"
    if not manifest_path.exists():
        raise PackValidationError(f"Pack is missing {manifest_path}")
    manifest = read_json(manifest_path)

    catalogues: list[dict] = []
    core_dir = pack_dir / "catalogues"
    if not core_dir.is_dir():
        core_dir = pack_dir / "codelists"
    if core_dir.is_dir():
        for path in sorted(core_dir.glob("*.json")):
            catalogues.append(normalized_catalogue(read_json(path)))

    for domain in domains:
        domain_dir = pack_dir / "domains" / domain
        if not domain_dir.is_dir():
            raise PackValidationError(f"Unknown catalogue domain: {domain}")
        for path in sorted(domain_dir.glob("*.json")):
            catalogues.append(normalized_catalogue(read_json(path), domain=domain))

    return manifest, catalogues


def validate_pack(manifest: dict, catalogues: list[dict]) -> None:
    for key in ("country", "version"):
        if not manifest.get(key):
            raise PackValidationError(f"Manifest field '{key}' is required")
    if len(manifest["country"]) != 3:
        raise PackValidationError("Manifest country must be an alpha-3 code")
    if not catalogues:
        raise PackValidationError("Pack contains no catalogues")

    catalogue_codes: set[str] = set()
    for catalogue in catalogues:
        code = catalogue.get("code")
        if not code:
            raise PackValidationError("Every catalogue requires a code")
        if code in catalogue_codes:
            raise PackValidationError(f"Duplicate catalogue code: {code}")
        catalogue_codes.add(code)

        values = catalogue["values"]
        value_codes = [value.get("code") for value in values]
        if any(not value_code for value_code in value_codes):
            raise PackValidationError(f"Catalogue {code} has a value without a code")
        if len(value_codes) != len(set(value_codes)):
            raise PackValidationError(f"Catalogue {code} has duplicate value codes")

        known = set(value_codes)
        parent_by_code = {value["code"]: value.get("parent_code") for value in values}
        for value_code, parent_code in parent_by_code.items():
            if parent_code and parent_code not in known:
                raise PackValidationError(f"{code}.{value_code} has unknown parent {parent_code}")

            seen = {value_code}
            cursor = parent_code
            while cursor:
                if cursor in seen:
                    raise PackValidationError(f"Catalogue {code} contains a parent cycle at {cursor}")
                seen.add(cursor)
                cursor = parent_by_code.get(cursor)


def pack_checksum(manifest: dict, catalogues: list[dict]) -> str:
    canonical = json.dumps(
        {"manifest": manifest, "catalogues": catalogues},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def stable_id(*parts: str) -> str:
    return str(uuid.uuid5(NAMESPACE, ":".join(parts)))


def publish(conn, manifest: dict, catalogues: list[dict], checksum: str) -> None:
    country = manifest["country"].upper()
    version = str(manifest["version"])
    release_id = stable_id("release", country, version)
    now = datetime.now(timezone.utc)

    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT checksum, status FROM catalogue_releases WHERE country_code=%s AND version=%s",
            (country, version),
        )
        existing = cursor.fetchone()
        if existing:
            if existing[0] != checksum:
                raise PackValidationError(
                    f"Release {country}/{version} already exists with a different checksum; use a new version"
                )
            if existing[1] == "ACTIVE":
                print(f"[catalogue-seed] {country}/{version} is already active")
                return

        cursor.execute(
            """
            INSERT INTO catalogue_releases
              (release_id, country_code, version, schema_version, checksum, source,
               status, manifest, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, 'STAGED', %s, %s)
            ON CONFLICT (country_code, version) DO NOTHING
            """,
            (
                release_id,
                country,
                version,
                str(manifest.get("catalogue_schema_version", manifest.get("schema_version", "1.0"))),
                checksum,
                manifest.get("source"),
                psycopg2.extras.Json(manifest),
                now,
            ),
        )

        for catalogue in catalogues:
            catalogue_id = stable_id("catalogue", release_id, catalogue["code"])
            cursor.execute(
                """
                INSERT INTO catalogues
                  (catalogue_id, release_id, code, domain, display_name,
                   display_name_i18n, is_hierarchical, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    catalogue_id,
                    release_id,
                    catalogue["code"],
                    catalogue["domain"],
                    catalogue["display_name"],
                    psycopg2.extras.Json(catalogue["display_name_i18n"]),
                    catalogue["is_hierarchical"],
                    catalogue["status"],
                ),
            )

            value_ids = {
                value["code"]: stable_id("value", catalogue_id, value["code"])
                for value in catalogue["values"]
            }
            rows = [
                (
                    value_ids[value["code"]],
                    catalogue_id,
                    value["code"],
                    value_ids.get(value["parent_code"]),
                    value["display_name"],
                    json.dumps(value["display_name_i18n"]),
                    json.dumps(value["semantic_roles"]),
                    value["sort_order"],
                    value["valid_from"],
                    value["valid_to"],
                    value["status"],
                    json.dumps(value["metadata"]),
                )
                for value in catalogue["values"]
            ]
            if rows:
                psycopg2.extras.execute_values(
                    cursor,
                    """
                    INSERT INTO catalogue_values
                      (catalogue_value_id, catalogue_id, code, parent_value_id,
                       display_name, display_name_i18n, semantic_roles, sort_order,
                       valid_from, valid_to, status, metadata)
                    VALUES %s
                    """,
                    rows,
                    page_size=500,
                )

        cursor.execute(
            "UPDATE catalogue_releases SET status='RETIRED' WHERE country_code=%s AND status='ACTIVE'",
            (country,),
        )
        cursor.execute(
            "UPDATE catalogue_releases SET status='ACTIVE', activated_at=%s WHERE release_id=%s",
            (now, release_id),
        )
        cursor.execute(
            """
            INSERT INTO catalogue_seed_runs
              (seed_run_id, release_id, status, started_at, finished_at)
            VALUES (%s, %s, 'SUCCESS', %s, %s)
            """,
            (str(uuid.uuid4()), release_id, now, datetime.now(timezone.utc)),
        )
    conn.commit()
    print(f"[catalogue-seed] activated {country}/{version} ({checksum})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", required=True, type=Path)
    parser.add_argument("--domains", default=os.environ.get("CATALOGUE_DOMAINS", ""))
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    domains = [domain.strip() for domain in args.domains.split(",") if domain.strip()]
    manifest, catalogues = load_pack(args.pack, domains)
    validate_pack(manifest, catalogues)
    checksum = pack_checksum(manifest, catalogues)
    print(f"[catalogue-seed] validated {len(catalogues)} catalogues; checksum={checksum}")
    if args.validate_only:
        return

    conn = psycopg2.connect(
        dbname=os.environ.get("CATALOGUE_DB", "catalogue"),
        host=os.environ.get("PGHOST", "localhost"),
        port=os.environ.get("PGPORT", "5432"),
        user=os.environ.get("PGUSER", "postgres"),
        password=os.environ.get("PGPASSWORD", ""),
    )
    try:
        publish(conn, manifest, catalogues, checksum)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
