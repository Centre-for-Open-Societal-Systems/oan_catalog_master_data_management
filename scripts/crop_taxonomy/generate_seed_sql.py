#!/usr/bin/env python3
"""Generate the immutable crop taxonomy SQL seed from the reviewed workbook."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Callable
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.crop_taxonomy.transform_workbook import TransformError, transform_workbook

NUMERIC = re.compile(r"^-?\d+(?:\.\d+)?$")
BATCH_SIZE = 250


def sql_text(value: object) -> str:
    if value is None or value == "":
        return "NULL"
    return "'" + str(value).replace("'", "''") + "'"


def sql_number(value: object) -> str:
    if value is None or value == "":
        return "NULL"
    rendered = str(value)
    if not NUMERIC.fullmatch(rendered):
        raise TransformError(f"Unsafe numeric SQL value: {value!r}")
    return rendered


def sql_boolean(value: object) -> str:
    if value is None or value == "":
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    normalized = str(value).casefold()
    if normalized not in {"true", "false"}:
        raise TransformError(f"Unsafe boolean SQL value: {value!r}")
    return normalized.upper()


def sql_i18n(amharic: object) -> str:
    if not amharic:
        return "NULL"
    payload = json.dumps({"am": str(amharic)}, ensure_ascii=False, sort_keys=True)
    return sql_text(payload) + "::jsonb"


def insert_statements(
    table: str,
    columns: list[str],
    rows: list[dict],
    renderers: dict[str, Callable[[object], str]] | None = None,
) -> list[str]:
    renderers = renderers or {}
    statements = []
    for offset in range(0, len(rows), BATCH_SIZE):
        batch = rows[offset : offset + BATCH_SIZE]
        values = []
        for row in batch:
            rendered = [renderers.get(column, sql_text)(row.get(column)) for column in columns]
            values.append("  (" + ", ".join(rendered) + ")")
        statements.append(f"INSERT INTO {table} ({', '.join(columns)}) VALUES\n" + ",\n".join(values) + ";")
    return statements


def render_seed_sql(workbook: Path) -> str:
    result = transform_workbook(workbook)
    if result.has_errors:
        errors = [item["message"] for item in result.report["findings"] if item["severity"] == "ERROR"]
        raise TransformError("Workbook contains structural errors: " + "; ".join(errors))

    for item in result.categories + result.crop_types + result.varieties:
        item["display_name_i18n"] = item.get("display_name_amh", "")

    definitions = []
    for item in result.characteristic_definitions:
        definition = dict(item)
        source_headers = definition.pop("source_header")
        definition["description"] = (
            f"{definition['description']} Source workbook header(s): {source_headers}."
        )
        definitions.append(definition)

    sections: list[tuple[str, list[str]]] = []
    sections.append(
        (
            "crop taxonomy categories",
            insert_statements(
                "g2p_crop_taxonomy_category",
                [
                    "category_code",
                    "source_id",
                    "display_name",
                    "display_name_i18n",
                    "image_url",
                    "description",
                    "status",
                ],
                result.categories,
                {"display_name_i18n": sql_i18n},
            ),
        )
    )
    sections.append(
        (
            "crop types",
            insert_statements(
                "g2p_crop_taxonomy_type",
                [
                    "type_code",
                    "source_id",
                    "category_code",
                    "display_name",
                    "display_name_i18n",
                    "scientific_name",
                    "centre",
                    "image_url",
                    "description",
                    "source_reported_variety_count",
                    "status",
                ],
                result.crop_types,
                {
                    "display_name_i18n": sql_i18n,
                    "source_reported_variety_count": sql_number,
                },
            ),
        )
    )
    sections.append(
        (
            "crop variety concepts",
            insert_statements(
                "g2p_crop_variety",
                [
                    "variety_code",
                    "type_code",
                    "display_name",
                    "display_name_i18n",
                    "status",
                ],
                result.varieties,
                {"display_name_i18n": sql_i18n},
            ),
        )
    )
    source_numeric_columns = {
        "source_row_number",
        "release_year",
        "altitude_min_m",
        "altitude_max_m",
        "rainfall_min_mm",
        "rainfall_max_mm",
        "days_to_maturity_min",
        "days_to_maturity_max",
        "yield_research_min_qt_ha",
        "yield_research_max_qt_ha",
        "yield_farmer_min_qt_ha",
        "yield_farmer_max_qt_ha",
        "seed_rate_kg_ha",
    }
    source_columns = [
        "source_record_code",
        "variety_code",
        "source_row_number",
        "centre",
        "release_year_raw",
        "release_year",
        "source_url",
        "altitude_min_m",
        "altitude_max_m",
        "rainfall_min_mm",
        "rainfall_max_mm",
        "days_to_maturity_min",
        "days_to_maturity_max",
        "yield_research_min_qt_ha",
        "yield_research_max_qt_ha",
        "yield_farmer_min_qt_ha",
        "yield_farmer_max_qt_ha",
        "seed_rate_kg_ha",
        "adaptation_area",
        "planting_date_text",
        "crop_pest_reaction",
    ]
    sections.append(
        (
            "individual workbook source records",
            insert_statements(
                "g2p_crop_variety_source_record",
                source_columns,
                result.source_records,
                {column: sql_number for column in source_numeric_columns},
            ),
        )
    )
    sections.append(
        (
            "characteristic definitions",
            insert_statements(
                "g2p_crop_characteristic_definition",
                [
                    "characteristic_code",
                    "display_name",
                    "value_type",
                    "default_unit_code",
                    "applicable_category_code",
                    "description",
                ],
                definitions,
            ),
        )
    )
    sections.append(
        (
            "relational crop variety characteristic values",
            insert_statements(
                "g2p_crop_variety_characteristic",
                [
                    "source_record_code",
                    "characteristic_code",
                    "raw_value",
                    "value_text",
                    "value_numeric",
                    "value_boolean",
                    "value_min",
                    "value_max",
                    "unit_code",
                ],
                result.characteristics,
                {
                    "value_numeric": sql_number,
                    "value_boolean": sql_boolean,
                    "value_min": sql_number,
                    "value_max": sql_number,
                },
            ),
        )
    )

    counts = result.report["counts"]
    lines = [
        "-- GENERATED FILE: do not edit manually.",
        "-- Regenerate with scripts/crop_taxonomy/generate_seed_sql.py.",
        f"-- Source workbook: {workbook.name}",
        f"-- Source SHA-256: {result.report['source_sha256']}",
        "-- The SQL seed runner owns the surrounding transaction and truncates staging tables.",
        "-- Validated row counts: "
        + ", ".join(
            f"{name}={counts[name]}"
            for name in (
                "categories",
                "crop_types",
                "varieties",
                "source_records",
                "characteristic_definitions",
                "characteristic_values",
            )
        ),
        "",
    ]
    for title, statements in sections:
        lines.append(f"-- {title}")
        lines.extend(statements)
        lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if output differs instead of rewriting the SQL file",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        generated = render_seed_sql(args.workbook)
    except TransformError as exc:
        print(f"crop taxonomy SQL generation failed: {exc}", file=sys.stderr)
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
