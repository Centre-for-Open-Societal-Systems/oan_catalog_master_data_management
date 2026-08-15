#!/usr/bin/env python3
"""Enrich the SQL crop catalogue with reviewed workbook crop-type data."""

from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path

from scripts.crop_taxonomy.transform_workbook import normalized_key, transform_workbook
from scripts.livestock.generate_seed_sql import extract_inserts, sql_literal
from scripts.seed_variety.match_seed_varieties import REVIEWED_TYPE_ALIASES

CROP_COLUMNS = (
    "id",
    "name",
    "description",
    "category_id",
    "known_for",
    "num_field_inspection_needed",
    "isolation_distance",
    "preferred_ecological_zone_id",
    "scientific_name",
    "centre",
    "varieties_count",
    "image_url",
    "display_name_amh",
    "taxonomy_type_code",
    "taxonomy_source_id",
    "taxonomy_category_code",
    "taxonomy_description",
    "record_source",
    "varieties_count_source",
    "taxonomy_match_method",
    "taxonomy_match_status",
    "category_source",
)

ADDITIONAL_REVIEWED_TYPE_ALIASES = {
    27: "grass-pea",
    39: "camelina",
    66: "lemon-grass",
    67: "spearmint",
    70: "geranium",
    76: "majoram-oregano",
}

ALL_REVIEWED_TYPE_ALIASES = REVIEWED_TYPE_ALIASES | ADDITIONAL_REVIEWED_TYPE_ALIASES

LEGACY_CATEGORY_BY_TAXONOMY = {
    "cereal": 1,
    "food-legume": 2,
    "oil-seeds": 3,
    "roots-and-tubers": 5,
    "fruit-and-vegetables": 5,
    "industrial-crops": 10,
    "spices-condiments-medicinal-aromatic": 10,
    "stimulant-crops": 10,
}

FRUIT_TYPE_CODES = {"fig", "papaya", "peach", "ziziphus-kurkura"}
ORIGINAL_SQL_MAX_ID = 132

VARIETY_CROP_ID_PATTERN = re.compile(r"^\s*\(\d+,\s*(?P<crop_id>\d+),", re.MULTILINE)


def crop_name_key(value: str) -> str:
    return normalized_key(re.sub(r"\s*\([^)]*\).*", "", value))


def computed_variety_counts(variety_sql: str) -> Counter[int]:
    counts = Counter(int(match.group("crop_id")) for match in VARIETY_CROP_ID_PATTERN.finditer(variety_sql))
    if sum(counts.values()) != 902:
        raise ValueError(f"Parsed {sum(counts.values())} crop-variety rows; expected 902")
    return counts


def matched_type(crop: dict, types_by_name: dict, types_by_code: dict):
    source_type_code = crop.get("taxonomy_type_code")
    if source_type_code and source_type_code in types_by_code:
        return types_by_code[source_type_code], "SOURCE_TYPE_CODE"
    matched = types_by_name.get(crop_name_key(crop["name"]))
    if matched is not None:
        return matched, "EXACT_NORMALIZED_NAME"
    alias = ALL_REVIEWED_TYPE_ALIASES.get(crop["id"])
    return (types_by_code.get(alias), "REVIEWED_TYPE_ALIAS") if alias else (None, "UNRESOLVED")


def legacy_category_for_new_type(crop_type: dict) -> int:
    if crop_type["type_code"] in FRUIT_TYPE_CODES:
        return 6
    return LEGACY_CATEGORY_BY_TAXONOMY[crop_type["category_code"]]


def enrich_rows(source_dir: Path, workbook: Path) -> list[dict]:
    crops = extract_inserts((source_dir / "04_insert_crop_catalog.sql").read_text(encoding="utf-8"))[
        "crop_catalog"
    ]
    variety_counts = computed_variety_counts(
        (source_dir / "05_insert_crop_variety.sql").read_text(encoding="utf-8")
    )
    taxonomy = transform_workbook(workbook)
    if taxonomy.has_errors:
        raise ValueError("Crop taxonomy workbook contains structural errors")

    types_by_name = {normalized_key(row["display_name"]): row for row in taxonomy.crop_types}
    types_by_code = {row["type_code"]: row for row in taxonomy.crop_types}
    taxonomy_variety_counts = Counter(row["type_code"] for row in taxonomy.varieties)
    matched_codes = set()
    enriched = []
    for source in sorted(crops, key=lambda row: row["id"]):
        crop_type, detected_match_method = matched_type(source, types_by_name, types_by_code)
        if crop_type:
            matched_codes.add(crop_type["type_code"])
        record_source = source.get("record_source") or (
            "SQL_CROP_CATALOG" if source["id"] <= ORIGINAL_SQL_MAX_ID else "WORKBOOK_ADDITION"
        )
        count_from_workbook = record_source == "WORKBOOK_ADDITION"
        existing_category_source = source.get("category_source")
        source_category_id = (
            None
            if existing_category_source == "WORKBOOK_TAXONOMY_MAPPING"
            else source.get("category_id")
        )
        category_id = (
            source_category_id
            if source_category_id is not None
            else legacy_category_for_new_type(crop_type)
            if crop_type
            else None
        )
        category_source = (
            "SQL_CROP_CATALOG"
            if source_category_id is not None and record_source == "SQL_CROP_CATALOG"
            else "WORKBOOK_TAXONOMY_MAPPING"
            if category_id is not None
            else "UNRESOLVED"
        )
        if count_from_workbook:
            match_method = "WORKBOOK_ADDITION"
        elif source["id"] in ALL_REVIEWED_TYPE_ALIASES:
            match_method = "REVIEWED_TYPE_ALIAS"
        elif crop_type and types_by_name.get(crop_name_key(source["name"])) is crop_type:
            match_method = "EXACT_NORMALIZED_NAME"
        elif source.get("taxonomy_match_method"):
            match_method = source["taxonomy_match_method"]
        else:
            match_method = detected_match_method
        enriched.append(
            source
            | {
                "category_id": category_id,
                "scientific_name": crop_type["scientific_name"] or None if crop_type else None,
                "centre": crop_type["centre"] or None if crop_type else None,
                "varieties_count": (
                    taxonomy_variety_counts[crop_type["type_code"]]
                    if count_from_workbook and crop_type
                    else variety_counts[source["id"]]
                ),
                "image_url": crop_type["image_url"] or None if crop_type else None,
                "display_name_amh": crop_type["display_name_amh"] or None if crop_type else None,
                "taxonomy_type_code": crop_type["type_code"] if crop_type else None,
                "taxonomy_source_id": crop_type["source_id"] or None if crop_type else None,
                "taxonomy_category_code": crop_type["category_code"] if crop_type else None,
                "taxonomy_description": crop_type["description"] or None if crop_type else None,
                "record_source": record_source,
                "varieties_count_source": (
                    "WORKBOOK_CROP_VARIETY" if count_from_workbook else "SQL_CROP_VARIETY"
                ),
                "taxonomy_match_method": match_method,
                "taxonomy_match_status": "MATCHED" if crop_type else "UNRESOLVED",
                "category_source": category_source,
            }
        )

    next_id = max(row["id"] for row in crops) + 1
    for crop_type in sorted(taxonomy.crop_types, key=lambda row: row["type_code"]):
        if crop_type["type_code"] in matched_codes:
            continue
        enriched.append(
            {
                "id": next_id,
                "name": crop_type["display_name"],
                "description": crop_type["description"] or None,
                "category_id": legacy_category_for_new_type(crop_type),
                "known_for": None,
                "num_field_inspection_needed": 0,
                "isolation_distance": 0,
                "preferred_ecological_zone_id": None,
                "scientific_name": crop_type["scientific_name"] or None,
                "centre": crop_type["centre"] or None,
                "varieties_count": taxonomy_variety_counts[crop_type["type_code"]],
                "image_url": crop_type["image_url"] or None,
                "display_name_amh": crop_type["display_name_amh"] or None,
                "taxonomy_type_code": crop_type["type_code"],
                "taxonomy_source_id": crop_type["source_id"] or None,
                "taxonomy_category_code": crop_type["category_code"],
                "taxonomy_description": crop_type["description"] or None,
                "record_source": "WORKBOOK_ADDITION",
                "varieties_count_source": "WORKBOOK_CROP_VARIETY",
                "taxonomy_match_method": "WORKBOOK_ADDITION",
                "taxonomy_match_status": "MATCHED",
                "category_source": "WORKBOOK_TAXONOMY_MAPPING",
            }
        )
        next_id += 1
    return enriched


def render_insert(rows: list[dict], table: str, *, generated: bool) -> str:
    prefix = (
        "-- GENERATED FILE: do not edit manually.\n"
        "-- Regenerate with scripts/crop_catalogue/enrich_crop_catalog.py.\n"
        if generated
        else "-- crop_catalog\n-- Consolidated from crop_catalog_scripts and crop_catalog_variety_included.xlsx\n"
    )
    columns = ", ".join(f'"{column}"' for column in CROP_COLUMNS)
    values = []
    for row in rows:
        values.append("  (" + ", ".join(sql_literal(row[column]) for column in CROP_COLUMNS) + ")")
    conflict_updates = ", ".join(
        f'"{column}" = EXCLUDED."{column}"' for column in CROP_COLUMNS if column != "id"
    )
    sql = f'{prefix}-- Records: {len(rows)}\n\nINSERT INTO "{table}" ({columns}) VALUES\n' + ",\n".join(
        values
    )
    if generated:
        sql += f'\nON CONFLICT ("id") DO UPDATE SET {conflict_updates};\n'
    else:
        sql += ";\n"
    return sql


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--source-output", type=Path, required=True)
    parser.add_argument("--seed-output", type=Path, required=True)
    args = parser.parse_args()

    rows = enrich_rows(args.source_dir, args.workbook)
    args.source_output.write_text(render_insert(rows, "crop_catalog", generated=False), encoding="utf-8")
    args.seed_output.write_text(render_insert(rows, "g2p_crop", generated=True), encoding="utf-8")
    print(f"Enriched {len(rows)} crop rows; computed {sum(row['varieties_count'] for row in rows)} varieties")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
