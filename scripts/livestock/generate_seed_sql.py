#!/usr/bin/env python3
"""Generate safe livestock staging SQL from the reviewed source SQL bundle."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

SOURCE_FILES = (
    "02_insert_livestock_catalog.sql",
    "03_insert_livestock_population.sql",
    "04_insert_livestock_breed.sql",
    "05_insert_livestock_reference.sql",
    "06_insert_livestock_registry.sql",
)
EXPECTED_COUNTS = {
    "livestock_catalog": 5,
    "livestock_population": 40,
    "livestock_breed": 94,
    "livestock_gender": 4,
    "livestock_location_type": 3,
    "livestock_body_condition": 5,
    "livestock_production_type": 13,
    "livestock_production_type_species": 34,
    "livestock_record_status": 6,
    "livestock_registry_entry": 12,
}
BREED_TYPES = {"Indigenous", "Exotic", "Cross"}


class LivestockTransformError(RuntimeError):
    """Raised when a reviewed source violates the transformation contract."""


def sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def parse_literal(token: str) -> Any:
    token = token.strip()
    if token == "NULL":
        return None
    if token == "TRUE":
        return True
    if token == "FALSE":
        return False
    if token.startswith("'") and token.endswith("'"):
        return token[1:-1].replace("''", "'")
    if re.fullmatch(r"-?\d+", token):
        return int(token)
    raise LivestockTransformError(f"Unsupported SQL literal: {token}")


def split_sql_fields(tuple_body: str) -> list[str]:
    fields: list[str] = []
    start = 0
    in_quote = False
    index = 0
    while index < len(tuple_body):
        character = tuple_body[index]
        if character == "'":
            if in_quote and index + 1 < len(tuple_body) and tuple_body[index + 1] == "'":
                index += 2
                continue
            in_quote = not in_quote
        elif character == "," and not in_quote:
            fields.append(tuple_body[start:index].strip())
            start = index + 1
        index += 1
    if in_quote:
        raise LivestockTransformError("Unterminated quoted SQL literal")
    fields.append(tuple_body[start:].strip())
    return fields


def parse_values(values_sql: str) -> list[list[Any]]:
    rows: list[list[Any]] = []
    index = 0
    while index < len(values_sql):
        while index < len(values_sql) and values_sql[index] in " \t\r\n,":
            index += 1
        if index == len(values_sql):
            break
        if values_sql[index] != "(":
            raise LivestockTransformError(f"Expected a value tuple near: {values_sql[index : index + 40]!r}")
        start = index + 1
        index += 1
        in_quote = False
        while index < len(values_sql):
            character = values_sql[index]
            if character == "'":
                if in_quote and index + 1 < len(values_sql) and values_sql[index + 1] == "'":
                    index += 2
                    continue
                in_quote = not in_quote
            elif character == ")" and not in_quote:
                break
            index += 1
        if index >= len(values_sql):
            raise LivestockTransformError("Unterminated SQL value tuple")
        rows.append([parse_literal(field) for field in split_sql_fields(values_sql[start:index])])
        index += 1
    return rows


def extract_inserts(sql: str) -> dict[str, list[dict[str, Any]]]:
    inserts: dict[str, list[dict[str, Any]]] = {}
    pattern = re.compile(
        r'INSERT\s+INTO\s+"(?P<table>[a-z_]+)"\s*'
        r"\((?P<columns>.*?)\)\s+VALUES\s*",
        re.IGNORECASE | re.DOTALL,
    )
    position = 0
    while match := pattern.search(sql, position):
        index = match.end()
        in_quote = False
        while index < len(sql):
            character = sql[index]
            if character == "'":
                if in_quote and index + 1 < len(sql) and sql[index + 1] == "'":
                    index += 2
                    continue
                in_quote = not in_quote
            elif character == ";" and not in_quote:
                break
            index += 1
        if index >= len(sql):
            raise LivestockTransformError(f"Unterminated INSERT for {match.group('table')}")
        columns = re.findall(r'"([a-z_]+)"', match.group("columns"), re.IGNORECASE)
        parsed_rows = parse_values(sql[match.end() : index])
        table = match.group("table").lower()
        for parsed in parsed_rows:
            if len(parsed) != len(columns):
                raise LivestockTransformError(
                    f"{table} row has {len(parsed)} values for {len(columns)} columns"
                )
            inserts.setdefault(table, []).append(dict(zip(columns, parsed, strict=True)))
        position = index + 1
    return inserts


def load_sources(source_dir: Path) -> tuple[dict[str, list[dict[str, Any]]], dict[str, str]]:
    datasets: dict[str, list[dict[str, Any]]] = {}
    checksums: dict[str, str] = {}
    for filename in SOURCE_FILES:
        path = source_dir / filename
        if not path.is_file():
            raise LivestockTransformError(f"Missing livestock source: {path}")
        content = path.read_text(encoding="utf-8")
        if "DROP TABLE" in content.upper() or "CREATE TABLE" in content.upper():
            raise LivestockTransformError(f"Data source unexpectedly contains DDL: {path}")
        checksums[filename] = hashlib.sha256(content.encode()).hexdigest()
        for table, rows in extract_inserts(content).items():
            if table in datasets:
                raise LivestockTransformError(f"Duplicate INSERT dataset: {table}")
            datasets[table] = rows

    for table, expected in EXPECTED_COUNTS.items():
        actual = len(datasets.get(table, []))
        if actual != expected:
            raise LivestockTransformError(f"{table} has {actual} rows; expected {expected}")
    unexpected = set(datasets) - set(EXPECTED_COUNTS)
    if unexpected:
        raise LivestockTransformError(f"Unexpected livestock datasets: {sorted(unexpected)}")
    return datasets, checksums


def validate_sources(datasets: dict[str, list[dict[str, Any]]]) -> None:
    species = {row["species_code"] for row in datasets["livestock_catalog"]}
    if len(species) != len(datasets["livestock_catalog"]):
        raise LivestockTransformError("Duplicate livestock species codes")
    if {code.casefold() for code in species} != {
        "beehive",
        "camel",
        "cattle",
        "goat",
        "sheep",
    }:
        raise LivestockTransformError("Livestock species set differs from the reviewed source")

    breeds = datasets["livestock_breed"]
    breed_ids = {row["id"] for row in breeds}
    if len(breed_ids) != len(breeds):
        raise LivestockTransformError("Duplicate livestock breed IDs")
    breed_codes = [row["breed_code"] for row in breeds if row["breed_code"] is not None]
    if len(breed_codes) != len(set(breed_codes)):
        raise LivestockTransformError("Duplicate non-null livestock breed codes")
    for row in breeds:
        if row["species_code"] not in species:
            raise LivestockTransformError(f"Breed {row['id']} has unknown species")
        if row["breed_type"] not in BREED_TYPES:
            raise LivestockTransformError(f"Breed {row['id']} has invalid breed type")

    ecological_zone_ids = {1, 2, 3}
    for row in datasets["livestock_location_type"]:
        if row["crop_catalog_ecological_zone_id"] not in ecological_zone_ids:
            raise LivestockTransformError(f"Unknown ecological zone in {row['code']}")

    production_codes = {row["code"] for row in datasets["livestock_production_type"]}
    for row in datasets["livestock_production_type_species"]:
        if row["production_type_code"] not in production_codes:
            raise LivestockTransformError("Production/species link has unknown production type")
        if row["species_code"] not in species:
            raise LivestockTransformError("Production/species link has unknown species")

    genders = {row["code"] for row in datasets["livestock_gender"]}
    locations = {row["code"] for row in datasets["livestock_location_type"]}
    conditions = {row["code"] for row in datasets["livestock_body_condition"]}
    statuses = {row["code"] for row in datasets["livestock_record_status"]}
    for row in datasets["livestock_registry_entry"]:
        for field, allowed in (
            ("species_code", species),
            ("gender_code", genders),
            ("location_type_code", locations),
            ("body_condition_code", conditions),
            ("production_type_code", production_codes),
            ("status", statuses),
        ):
            if row[field] not in allowed:
                raise LivestockTransformError(f"Registry row {row['id']} has unknown {field}: {row[field]}")
        if row["breed_id"] is not None and row["breed_id"] not in breed_ids:
            raise LivestockTransformError(f"Registry row {row['id']} has unknown breed ID")


def values_block(rows: list[list[Any]]) -> str:
    return ",\n  ".join("(" + ", ".join(sql_literal(value) for value in row) + ")" for row in rows)


def direct_upsert(
    table: str,
    columns: list[str],
    rows: list[list[Any]],
    conflict_columns: list[str],
    update_columns: list[str],
) -> str:
    assignments = ",\n    ".join(f"{column} = EXCLUDED.{column}" for column in update_columns)
    return (
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES\n  {values_block(rows)}\n"
        f"ON CONFLICT ({', '.join(conflict_columns)}) DO UPDATE SET\n    {assignments};"
    )


def source_join_upsert(
    table: str,
    target_columns: list[str],
    source_columns: list[str],
    rows: list[list[Any]],
    select_expressions: list[str],
    joins: str,
    conflict_columns: list[str],
    update_columns: list[str],
) -> str:
    assignments = ",\n    ".join(f"{column} = EXCLUDED.{column}" for column in update_columns)
    return f"""INSERT INTO {table} ({", ".join(target_columns)})
SELECT {", ".join(select_expressions)}
FROM (VALUES
  {values_block(rows)}
) AS source ({", ".join(source_columns)})
{joins}
ON CONFLICT ({", ".join(conflict_columns)}) DO UPDATE SET
    {assignments};"""


def render_seed_sql(datasets: dict[str, list[dict[str, Any]]], checksums: dict[str, str]) -> str:
    statements = [
        "-- GENERATED FILE: do not edit manually.",
        "-- Regenerate with scripts/livestock/generate_seed_sql.py.",
        "-- Destructive source DDL is not included; all reviewed data rows are included.",
    ]
    statements.extend(f"-- {name} SHA-256: {checksum}" for name, checksum in checksums.items())

    species_columns = [
        "species_code",
        "name",
        "description",
        "icon_url",
        "dataset_id",
        "scientific_name",
        "subfamily",
        "species_type_code",
        "chart_color",
        "ear_tag_range",
        "in_lis_population",
        "in_etlits_registry",
    ]
    species_rows = [
        [row[column].casefold() if column == "species_code" else row[column] for column in species_columns]
        for row in datasets["livestock_catalog"]
    ]
    statements.append(
        direct_upsert(
            "g2p_livestock_type",
            species_columns,
            species_rows,
            ["species_code"],
            species_columns[1:],
        )
    )
    statements.append(
        "SELECT setval('g2p_livestock_type_id_seq', (SELECT MAX(id) FROM g2p_livestock_type), TRUE);"
    )

    population_source_columns = [
        "source_species_code",
        "census_year",
        "population_total",
        "source_record_count",
    ]
    population_rows = [
        [row["species_code"].casefold()] + [row[column] for column in population_source_columns[1:]]
        for row in datasets["livestock_population"]
    ]
    statements.append(
        source_join_upsert(
            "g2p_livestock_population",
            ["species_code", "census_year", "population_total", "source_record_count"],
            population_source_columns,
            population_rows,
            [
                "species.id",
                "source.census_year",
                "source.population_total",
                "source.source_record_count",
            ],
            "JOIN g2p_livestock_type species\n  ON species.species_code = source.source_species_code",
            ["species_code", "census_year"],
            ["population_total", "source_record_count"],
        )
    )

    breed_source_columns = [
        "id",
        "breed_code",
        "name",
        "abbreviation",
        "source_species_code",
        "breed_type",
        "in_national_standard",
        "in_etlits_registry",
        "source_name",
    ]
    breed_rows = [
        [
            row["id"],
            row["breed_code"],
            row["name"],
            row["abbreviation"],
            row["species_code"].casefold(),
            row["breed_type"],
            row["in_national_standard"],
            row["in_etlits_registry"],
            row["source"],
        ]
        for row in datasets["livestock_breed"]
    ]
    statements.append(
        source_join_upsert(
            "g2p_livestock_breed",
            [
                "id",
                "breed_code",
                "name",
                "abbreviation",
                "species_id",
                "breed_type",
                "in_national_standard",
                "in_etlits_registry",
                "source",
            ],
            breed_source_columns,
            breed_rows,
            [
                "source.id",
                "source.breed_code",
                "source.name",
                "source.abbreviation",
                "species.id",
                "source.breed_type",
                "source.in_national_standard",
                "source.in_etlits_registry",
                "source.source_name",
            ],
            "JOIN g2p_livestock_type species\n  ON species.species_code = source.source_species_code",
            ["id"],
            [
                "breed_code",
                "name",
                "abbreviation",
                "species_id",
                "breed_type",
                "in_national_standard",
                "in_etlits_registry",
                "source",
            ],
        )
    )

    direct_specs = (
        (
            "livestock_gender",
            "g2p_livestock_gender",
            ["code", "name", "description", "in_etlits_registry"],
            ["code"],
        ),
        (
            "livestock_location_type",
            "g2p_livestock_location_type",
            [
                "code",
                "name",
                "ethiopian_zone_name",
                "altitude_description",
                "ecological_zone_id",
                "description",
            ],
            ["code"],
        ),
        (
            "livestock_body_condition",
            "g2p_livestock_body_condition",
            [
                "code",
                "bcs_score",
                "condition_label",
                "fatness_label",
                "etlits_label",
                "description",
            ],
            ["code"],
        ),
        (
            "livestock_production_type",
            "g2p_livestock_production_type",
            [
                "code",
                "name",
                "standard_purpose",
                "in_national_standard",
                "in_etlits_registry",
                "description",
            ],
            ["code"],
        ),
        (
            "livestock_record_status",
            "g2p_livestock_record_status",
            ["code", "name", "sort_order", "is_live_master_data", "description"],
            ["code"],
        ),
    )
    for source_table, target_table, target_columns, conflict_columns in direct_specs:
        source_columns = [
            "crop_catalog_ecological_zone_id" if column == "ecological_zone_id" else column
            for column in target_columns
        ]
        rows = [[row[column] for column in source_columns] for row in datasets[source_table]]
        statements.append(
            direct_upsert(
                target_table,
                target_columns,
                rows,
                conflict_columns,
                target_columns[1:],
            )
        )

    production_species_rows = [
        [row["production_type_code"], row["species_code"].casefold()]
        for row in datasets["livestock_production_type_species"]
    ]
    statements.append(f"""INSERT INTO g2p_livestock_production_type_species
  (production_type_code, species_id)
SELECT source.production_type_code, species.id
FROM (VALUES
  {values_block(production_species_rows)}
) AS source (production_type_code, source_species_code)
JOIN g2p_livestock_type species
  ON species.species_code = source.source_species_code
ON CONFLICT (production_type_code, species_id) DO NOTHING;""")

    registry_columns = [
        "id",
        "species_code",
        "breed_name",
        "breed_id",
        "gender_code",
        "location_type_code",
        "body_condition_code",
        "production_type_code",
        "status",
        "created_on",
        "updated_on",
    ]
    registry_rows = [
        [row[column].casefold() if column == "species_code" else row[column] for column in registry_columns]
        for row in datasets["livestock_registry_entry"]
    ]
    statements.append(
        direct_upsert(
            "g2p_livestock_registry_entry",
            registry_columns,
            registry_rows,
            ["id"],
            registry_columns[1:],
        )
    )
    return "\n\n".join(statements) + "\n"


def render_registry_review(datasets: dict[str, list[dict[str, Any]]]) -> tuple[str, Counter[str]]:
    breeds = {row["id"]: row for row in datasets["livestock_breed"]}
    valid_production_species = {
        (row["production_type_code"], row["species_code"])
        for row in datasets["livestock_production_type_species"]
    }
    fields = [
        "registry_id",
        "status",
        "species_code",
        "breed_name",
        "breed_id",
        "breed_code",
        "breed_species_code",
        "production_type_code",
        "breed_unrecognised",
        "breed_outside_national_standard",
        "breed_species_mismatch",
        "production_type_species_mismatch",
    ]
    review_rows = []
    counts: Counter[str] = Counter()
    for row in datasets["livestock_registry_entry"]:
        breed = breeds.get(row["breed_id"])
        flags = {
            "breed_unrecognised": breed is None,
            "breed_outside_national_standard": bool(breed is not None and not breed["in_national_standard"]),
            "breed_species_mismatch": bool(
                breed is not None and breed["species_code"] != row["species_code"]
            ),
            "production_type_species_mismatch": (row["production_type_code"], row["species_code"])
            not in valid_production_species,
        }
        for name, enabled in flags.items():
            if enabled:
                counts[name] += 1
        review_rows.append(
            {
                "registry_id": row["id"],
                "status": row["status"],
                "species_code": row["species_code"].casefold(),
                "breed_name": row["breed_name"],
                "breed_id": row["breed_id"] if row["breed_id"] is not None else "",
                "breed_code": breed["breed_code"] if breed else "",
                "breed_species_code": breed["species_code"].casefold() if breed else "",
                "production_type_code": row["production_type_code"],
                **{name: "TRUE" if enabled else "FALSE" for name, enabled in flags.items()},
            }
        )
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows(review_rows)
    return output.getvalue().replace("\r\n", "\n"), counts


def build_outputs(source_dir: Path) -> tuple[str, str, str]:
    datasets, checksums = load_sources(source_dir)
    validate_sources(datasets)
    seed_sql = render_seed_sql(datasets, checksums)
    review_csv, validation_counts = render_registry_review(datasets)
    report = {
        "dataset_counts": {table: len(datasets[table]) for table in sorted(datasets)},
        "registry_policy": "PUBLISHED_AS_RELEASE_SCOPED_REGISTRY_SNAPSHOT",
        "source_sha256": checksums,
        "validation_counts": dict(sorted(validation_counts.items())),
    }
    return seed_sql, review_csv, json.dumps(report, indent=2, sort_keys=True) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("output_sql", type=Path)
    parser.add_argument("--review-output", type=Path, required=True)
    parser.add_argument("--report-output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        outputs = build_outputs(args.source_dir)
    except (OSError, LivestockTransformError) as error:
        print(f"livestock SQL generation failed: {error}", file=sys.stderr)
        return 2
    targets = (args.output_sql, args.review_output, args.report_output)
    if args.check:
        stale = [
            str(path)
            for path, expected in zip(targets, outputs, strict=True)
            if not path.is_file() or path.read_text(encoding="utf-8") != expected
        ]
        if stale:
            print(f"generated livestock artifacts are stale: {', '.join(stale)}", file=sys.stderr)
            return 1
        print("generated livestock artifacts are current")
        return 0
    for path, content in zip(targets, outputs, strict=True):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
