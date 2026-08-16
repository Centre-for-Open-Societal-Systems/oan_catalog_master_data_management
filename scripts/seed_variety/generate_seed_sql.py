#!/usr/bin/env python3
"""Adapt the reviewed Ethio-Seed variety SQL to the catalogue staging contract."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

EXPECTED_ROWS = 902
INSERT_MARKER = 'INSERT INTO "crop_variety"'
ROW_PATTERN = re.compile(r"^\s*\((\d+),\s*(\d+),", re.MULTILINE)
DETAIL_URL_PATTERN = re.compile(r"seed-variety-details/(\d+)/")


class SeedVarietyAdapterError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class SourceSummary:
    row_count: int
    seed_crop_count: int
    source_sha256: str


def extract_values(source_sql: str) -> tuple[str, SourceSummary]:
    if any(token in source_sql.upper() for token in ("DROP TABLE", "CREATE TABLE", "\\I ")):
        raise SeedVarietyAdapterError("Variety source must contain data only, not DDL or psql includes")
    marker_position = source_sql.find(INSERT_MARKER)
    if marker_position < 0:
        raise SeedVarietyAdapterError("Expected crop_variety INSERT was not found")
    values_position = source_sql.find(" VALUES\n", marker_position)
    if values_position < 0:
        raise SeedVarietyAdapterError("Expected VALUES block was not found")
    values = source_sql[values_position + len(" VALUES\n") :].strip()
    if not values.endswith(";"):
        raise SeedVarietyAdapterError("Source INSERT must end with a semicolon")
    values = values[:-1]

    rows = [(int(source_id), int(seed_crop_id)) for source_id, seed_crop_id in ROW_PATTERN.findall(values)]
    source_ids = [source_id for source_id, _ in rows]
    detail_ids = [int(value) for value in DETAIL_URL_PATTERN.findall(values)]
    if len(rows) != EXPECTED_ROWS:
        raise SeedVarietyAdapterError(f"Source contains {len(rows)} rows; expected {EXPECTED_ROWS}")
    if len(source_ids) != len(set(source_ids)):
        raise SeedVarietyAdapterError("Source contains duplicate variety IDs")
    if sorted(source_ids) != sorted(detail_ids):
        raise SeedVarietyAdapterError("Variety IDs and details URL IDs do not match exactly")
    if any(source_id <= 0 or seed_crop_id <= 0 for source_id, seed_crop_id in rows):
        raise SeedVarietyAdapterError("Source and seed crop IDs must be positive")

    return values, SourceSummary(
        row_count=len(rows),
        seed_crop_count=len({seed_crop_id for _, seed_crop_id in rows}),
        source_sha256=hashlib.sha256(source_sql.encode()).hexdigest(),
    )


def render_seed_sql(source: Path) -> str:
    source_sql = source.read_text(encoding="utf-8")
    values, summary = extract_values(source_sql)
    return f"""-- GENERATED FILE: do not edit manually.
-- Regenerate with scripts/seed_variety/generate_seed_sql.py.
-- Source: {source.name}
-- Source SHA-256: {summary.source_sha256}
-- Preserved source rows: {summary.row_count}; seed crops represented: {summary.seed_crop_count}
-- Matching fields intentionally retain their migration defaults until Phase 3.

INSERT INTO g2p_seed_variety_source_record (
    source_variety_id,
    seed_crop_id,
    crop_name_raw,
    common_name_raw,
    category_raw,
    release_year,
    release_date,
    release_raw,
    maintainer,
    source_classification,
    details_url
) VALUES
{values}
ON CONFLICT (source_variety_id) DO UPDATE SET
    seed_crop_id = EXCLUDED.seed_crop_id,
    crop_name_raw = EXCLUDED.crop_name_raw,
    common_name_raw = EXCLUDED.common_name_raw,
    category_raw = EXCLUDED.category_raw,
    release_year = EXCLUDED.release_year,
    release_date = EXCLUDED.release_date,
    release_raw = EXCLUDED.release_raw,
    maintainer = EXCLUDED.maintainer,
    source_classification = EXCLUDED.source_classification,
    details_url = EXCLUDED.details_url;
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if output differs instead of rewriting the generated SQL",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        generated = render_seed_sql(args.source)
    except (OSError, SeedVarietyAdapterError) as error:
        print(f"seed variety SQL generation failed: {error}", file=sys.stderr)
        return 2
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != generated:
            print(f"generated SQL is stale: {args.output}", file=sys.stderr)
            return 1
        print(f"generated SQL is current: {args.output}")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(generated, encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
