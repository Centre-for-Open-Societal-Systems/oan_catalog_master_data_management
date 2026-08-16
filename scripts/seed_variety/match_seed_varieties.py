#!/usr/bin/env python3
"""Build deterministic seed-variety matches and a review report."""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.crop_taxonomy.transform_workbook import transform_workbook
from scripts.seed_variety.generate_seed_sql import (
    EXPECTED_ROWS,
    SeedVarietyAdapterError,
)

SOURCE_ROW_PATTERN = re.compile(
    r"^\s*\((?P<source_id>\d+),\s*(?P<seed_crop_id>\d+),\s*"
    r"'(?P<crop_name>(?:''|[^'])*)',\s*'(?P<common_name>(?:''|[^'])*)',",
    re.MULTILINE,
)
SOURCE_RECORD_ID_PATTERN = re.compile(r"^moa-variety-(\d+)$")

# Reviewed only where the Ethio-Seed crop is an unambiguous lexical/scope
# variant of one workbook crop type. Ambiguous species and broad forage groups
# intentionally remain unresolved.
REVIEWED_TYPE_ALIASES = {
    4: "barley",  # Food Barley
    5: "barley",  # Malt Barley
    25: "haricot-bean",  # Common/Haricot bean
    40: "potato",  # Irish potato
    50: "pepper",  # Sweet/Hot Pepper
    115: "lima-bean-butter-bean",  # Lima bean
}


@dataclass(frozen=True, slots=True)
class SeedSourceRow:
    source_variety_id: int
    seed_crop_id: int
    crop_name_raw: str
    common_name_raw: str


@dataclass(frozen=True, slots=True)
class MatchDecision:
    source_variety_id: int
    seed_crop_id: int
    crop_name_raw: str
    common_name_raw: str
    expected_type_code: str | None
    matched_variety_code: str | None
    match_method: str
    match_status: str
    review_reason: str
    source_id_candidate: str | None


def normalize_key(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.replace("…", ""))
    value = "".join(character for character in value if not unicodedata.combining(character))
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def parse_source_rows(source_sql: str) -> list[SeedSourceRow]:
    rows = [
        SeedSourceRow(
            source_variety_id=int(match.group("source_id")),
            seed_crop_id=int(match.group("seed_crop_id")),
            crop_name_raw=match.group("crop_name").replace("''", "'"),
            common_name_raw=match.group("common_name").replace("''", "'"),
        )
        for match in SOURCE_ROW_PATTERN.finditer(source_sql)
    ]
    if len(rows) != EXPECTED_ROWS:
        raise SeedVarietyAdapterError(f"Parsed {len(rows)} source rows; expected {EXPECTED_ROWS}")
    return rows


def seed_variety_keys(row: SeedSourceRow, type_display_name: str) -> set[str]:
    common_key = normalize_key(row.common_name_raw)
    keys = {common_key}
    for prefix in (normalize_key(row.crop_name_raw), normalize_key(type_display_name)):
        if prefix and common_key.startswith(prefix):
            remainder = common_key[len(prefix) :]
            if remainder:
                keys.add(remainder)
    return {key for key in keys if key}


def build_match_plan(source_sql: str, workbook: Path) -> tuple[list[MatchDecision], dict]:
    source_rows = parse_source_rows(source_sql)
    transformed = transform_workbook(workbook)
    if transformed.has_errors:
        raise SeedVarietyAdapterError("Crop taxonomy workbook contains structural errors")

    types_by_code = {row["type_code"]: row for row in transformed.crop_types}
    type_codes_by_name: dict[str, list[str]] = defaultdict(list)
    for row in transformed.crop_types:
        type_codes_by_name[normalize_key(row["display_name"])].append(row["type_code"])

    varieties_by_code = {row["variety_code"]: row for row in transformed.varieties}
    variety_codes_by_type_name: dict[tuple[str, str], list[str]] = defaultdict(list)
    for row in transformed.varieties:
        variety_codes_by_type_name[(row["type_code"], normalize_key(row["display_name"]))].append(
            row["variety_code"]
        )

    source_id_candidates: dict[int, set[str]] = defaultdict(set)
    for row in transformed.source_records:
        match = SOURCE_RECORD_ID_PATTERN.fullmatch(row["source_record_code"])
        if match:
            source_id_candidates[int(match.group(1))].add(row["variety_code"])

    decisions: list[MatchDecision] = []
    for row in source_rows:
        raw_type_candidates = type_codes_by_name.get(normalize_key(row.crop_name_raw), [])
        alias_type = REVIEWED_TYPE_ALIASES.get(row.seed_crop_id)
        if alias_type:
            type_candidates = [alias_type]
            type_resolution = "REVIEWED_TYPE_ALIAS"
        else:
            type_candidates = raw_type_candidates
            type_resolution = "EXACT_TYPE_NAME"

        source_candidates = sorted(source_id_candidates.get(row.source_variety_id, set()))
        source_candidate = source_candidates[0] if len(source_candidates) == 1 else None
        if len(type_candidates) != 1 or type_candidates[0] not in types_by_code:
            reason = "NO_CROP_TYPE_MATCH" if not type_candidates else "AMBIGUOUS_CROP_TYPE_MATCH"
            decisions.append(
                MatchDecision(
                    row.source_variety_id,
                    row.seed_crop_id,
                    row.crop_name_raw,
                    row.common_name_raw,
                    None,
                    None,
                    "UNRESOLVED",
                    "UNRESOLVED",
                    reason,
                    source_candidate,
                )
            )
            continue

        type_code = type_candidates[0]
        keys = seed_variety_keys(row, types_by_code[type_code]["display_name"])
        name_candidates = {
            code for key in keys for code in variety_codes_by_type_name.get((type_code, key), [])
        }
        compatible_source_candidates = {
            code
            for code in source_candidates
            if varieties_by_code[code]["type_code"] == type_code
            and normalize_key(varieties_by_code[code]["display_name"]) in keys
        }

        if len(name_candidates) == 1:
            matched_code = next(iter(name_candidates))
            method = (
                "EXACT_SOURCE_ID" if matched_code in compatible_source_candidates else "EXACT_NAME_AND_CROP"
            )
            reasons = [type_resolution]
            if source_candidates and matched_code not in source_candidates:
                reasons.append("SOURCE_ID_NAMESPACE_DISAGREES")
            decisions.append(
                MatchDecision(
                    row.source_variety_id,
                    row.seed_crop_id,
                    row.crop_name_raw,
                    row.common_name_raw,
                    type_code,
                    matched_code,
                    method,
                    "MATCHED",
                    ";".join(reasons),
                    source_candidate,
                )
            )
        elif len(name_candidates) > 1:
            decisions.append(
                MatchDecision(
                    row.source_variety_id,
                    row.seed_crop_id,
                    row.crop_name_raw,
                    row.common_name_raw,
                    type_code,
                    None,
                    "CONFLICT",
                    "CONFLICT",
                    "MULTIPLE_EXACT_NAME_CANDIDATES:" + ",".join(sorted(name_candidates)),
                    source_candidate,
                )
            )
        else:
            reason = "NO_EXACT_VARIETY_NAME_MATCH"
            if source_candidates:
                reason += ";SOURCE_ID_NOT_COMPATIBLE_WITH_CROP_AND_NAME"
            decisions.append(
                MatchDecision(
                    row.source_variety_id,
                    row.seed_crop_id,
                    row.crop_name_raw,
                    row.common_name_raw,
                    type_code,
                    None,
                    "UNRESOLVED",
                    "UNRESOLVED",
                    reason,
                    source_candidate,
                )
            )

    status_counts = Counter(item.match_status for item in decisions)
    method_counts = Counter(item.match_method for item in decisions)
    reason_counts = Counter(item.review_reason for item in decisions)
    report = {
        "format_version": 1,
        "source_rows": len(decisions),
        "status_counts": dict(sorted(status_counts.items())),
        "method_counts": dict(sorted(method_counts.items())),
        "reason_counts": dict(sorted(reason_counts.items())),
        "reviewed_type_aliases": REVIEWED_TYPE_ALIASES,
    }
    return decisions, report


def sql_text(value: str | None) -> str:
    if value is None:
        return "NULL"
    return "'" + value.replace("'", "''") + "'"


def render_match_sql(decisions: list[MatchDecision]) -> str:
    values = []
    for item in decisions:
        values.append(
            "  ("
            + ", ".join(
                (
                    str(item.source_variety_id),
                    sql_text(item.matched_variety_code),
                    sql_text(item.match_method),
                    sql_text(item.match_status),
                    sql_text(item.review_reason),
                )
            )
            + ")"
        )
    return (
        """-- GENERATED FILE: do not edit manually.
-- Regenerate with scripts/seed_variety/match_seed_varieties.py.
-- Only crop-scoped exact matches are published; fuzzy candidates remain unresolved.

UPDATE g2p_seed_variety_source_record AS target
   SET matched_variety_code = plan.matched_variety_code,
       match_method = plan.match_method,
       match_status = plan.match_status,
       review_note = plan.review_note
  FROM (VALUES
"""
        + ",\n".join(values)
        + """
       ) AS plan(
           source_variety_id, matched_variety_code,
           match_method, match_status, review_note
       )
 WHERE target.source_variety_id = plan.source_variety_id;
"""
    )


def render_review_csv(decisions: list[MatchDecision]) -> str:
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(
        handle,
        fieldnames=list(asdict(decisions[0])),
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(asdict(item) for item in decisions)
    return handle.getvalue()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_sql", type=Path)
    parser.add_argument("workbook", type=Path)
    parser.add_argument("output_sql", type=Path)
    parser.add_argument("review_csv", type=Path)
    parser.add_argument("report_json", type=Path)
    parser.add_argument("--check", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        decisions, report = build_match_plan(
            args.source_sql.read_text(encoding="utf-8"),
            args.workbook,
        )
    except (OSError, SeedVarietyAdapterError) as error:
        print(f"seed variety matching failed: {error}", file=sys.stderr)
        return 2
    generated_sql = render_match_sql(decisions)
    generated_csv = render_review_csv(decisions)
    generated_json = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.check:
        current = (
            args.output_sql.is_file()
            and args.output_sql.read_text(encoding="utf-8") == generated_sql
            and args.review_csv.is_file()
            and args.review_csv.read_text(encoding="utf-8") == generated_csv
            and args.report_json.is_file()
            and args.report_json.read_text(encoding="utf-8") == generated_json
        )
        if not current:
            print("generated seed-variety match artifacts are stale", file=sys.stderr)
            return 1
        print("generated seed-variety match artifacts are current")
        return 0

    args.output_sql.parent.mkdir(parents=True, exist_ok=True)
    args.output_sql.write_text(generated_sql, encoding="utf-8")
    args.review_csv.parent.mkdir(parents=True, exist_ok=True)
    args.review_csv.write_text(generated_csv, encoding="utf-8")
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(generated_json, encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
