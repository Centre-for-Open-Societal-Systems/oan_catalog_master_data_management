#!/usr/bin/env python3
"""Reconcile crop categories from the source SQL bundle with the workbook taxonomy."""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from scripts.crop_taxonomy.transform_workbook import normalized_key, transform_workbook
from scripts.livestock.generate_seed_sql import extract_inserts
from scripts.seed_variety.match_seed_varieties import REVIEWED_TYPE_ALIASES

CATEGORY_FILE = "02_insert_crop_category.sql"
CROP_FILE = "04_insert_crop_catalog.sql"
VARIETY_FILE = "05_insert_crop_variety.sql"

# A taxonomy category may correspond to more than one legacy category because
# the source SQL combines roots, tubers, and vegetables but separates fruits.
COMPATIBLE_LEGACY_CATEGORIES = {
    "cereal": {1},
    "food-legume": {2},
    "oil-seeds": {3},
    "roots-and-tubers": {5},
    "fruit-and-vegetables": {5, 6},
    "industrial-crops": {10},
    "spices-condiments-medicinal-aromatic": {10},
    "stimulant-crops": {10},
}

VARIETY_PREFIX_PATTERN = re.compile(
    r"^\s*\(\d+,\s*(?P<crop_id>\d+),\s*"
    r"'(?P<crop_name>(?:''|[^'])*)',\s*'(?P<common_name>(?:''|[^'])*)',\s*"
    r"(?P<category>NULL|'(?:''|[^'])*'),",
    re.MULTILINE,
)

REVIEW_FIELDS = (
    "crop_id",
    "crop_name",
    "source_category_id",
    "source_category_name",
    "taxonomy_type_code",
    "taxonomy_type_name",
    "taxonomy_category_code",
    "taxonomy_category_name",
    "match_method",
    "match_status",
    "category_status",
    "review_note",
)


def crop_name_key(value: str) -> str:
    """Normalize a legacy crop label while dropping a trailing scientific name."""
    return normalized_key(re.sub(r"\s*\([^)]*\).*", "", value))


def parse_variety_categories(source_sql: str) -> list[tuple[int, str | None]]:
    rows = []
    for match in VARIETY_PREFIX_PATTERN.finditer(source_sql):
        raw_category = match.group("category")
        category = None if raw_category == "NULL" else raw_category[1:-1].replace("''", "'")
        rows.append((int(match.group("crop_id")), category))
    if len(rows) != 902:
        raise ValueError(f"Parsed {len(rows)} crop-variety rows; expected 902")
    return rows


def normalized_category_name(value: str) -> str:
    aliases = {"oil crop": "oil crops"}
    key = normalized_key(value)
    return normalized_key(aliases.get(value.casefold(), key))


def build_review(source_dir: Path, workbook: Path) -> tuple[str, str]:
    categories = extract_inserts((source_dir / CATEGORY_FILE).read_text(encoding="utf-8"))["crop_category"]
    crops = extract_inserts((source_dir / CROP_FILE).read_text(encoding="utf-8"))["crop_catalog"]
    variety_categories = parse_variety_categories((source_dir / VARIETY_FILE).read_text(encoding="utf-8"))
    taxonomy = transform_workbook(workbook)
    if taxonomy.has_errors:
        raise ValueError("Crop taxonomy workbook contains structural errors")

    category_names = {row["id"]: row["name"] for row in categories}
    taxonomy_category_names = {row["category_code"]: row["display_name"] for row in taxonomy.categories}
    types_by_name = {normalized_key(row["display_name"]): row for row in taxonomy.crop_types}
    types_by_code = {row["type_code"]: row for row in taxonomy.crop_types}

    review_rows = []
    for crop in sorted(crops, key=lambda row: row["id"]):
        source_type_code = crop.get("taxonomy_type_code")
        taxonomy_type = types_by_code.get(source_type_code) if source_type_code else None
        match_method = "SOURCE_TYPE_CODE" if taxonomy_type else "EXACT_NORMALIZED_NAME"
        if taxonomy_type is None:
            taxonomy_type = types_by_name.get(crop_name_key(crop["name"]))
        if taxonomy_type is None:
            alias = REVIEWED_TYPE_ALIASES.get(crop["id"])
            taxonomy_type = types_by_code.get(alias) if alias else None
            match_method = "REVIEWED_TYPE_ALIAS" if taxonomy_type else "UNRESOLVED"

        source_category_id = crop["category_id"]
        if taxonomy_type is None:
            match_status = "UNRESOLVED"
            category_status = "SOURCE_CATEGORY_ONLY" if source_category_id is not None else "CATEGORY_MISSING"
            note = "No reviewed workbook crop-type match"
        elif source_category_id is None:
            match_status = "MATCHED"
            category_status = "CATEGORY_MISSING"
            note = "Taxonomy category is available but the source crop category is NULL"
        elif source_category_id in COMPATIBLE_LEGACY_CATEGORIES[taxonomy_type["category_code"]]:
            match_status = "MATCHED"
            category_status = "ALIGNED"
            note = ""
        else:
            match_status = "MATCHED"
            category_status = "DIVERGENT"
            note = "Source and workbook classifications disagree; manual decision required"

        review_rows.append(
            {
                "crop_id": crop["id"],
                "crop_name": crop["name"],
                "source_category_id": source_category_id,
                "source_category_name": category_names.get(source_category_id, ""),
                "taxonomy_type_code": taxonomy_type["type_code"] if taxonomy_type else "",
                "taxonomy_type_name": taxonomy_type["display_name"] if taxonomy_type else "",
                "taxonomy_category_code": taxonomy_type["category_code"] if taxonomy_type else "",
                "taxonomy_category_name": (
                    taxonomy_category_names[taxonomy_type["category_code"]] if taxonomy_type else ""
                ),
                "match_method": match_method,
                "match_status": match_status,
                "category_status": category_status,
                "review_note": note,
            }
        )

    category_by_crop: dict[int, set[str]] = defaultdict(set)
    for crop_id, category in variety_categories:
        if category:
            category_by_crop[crop_id].add(category)
    variety_category_mismatches = []
    crops_by_id = {row["id"]: row for row in crops}
    for crop_id, values in sorted(category_by_crop.items()):
        source_category_id = crops_by_id[crop_id]["category_id"]
        source_category_name = category_names.get(source_category_id)
        if source_category_name is None or any(
            normalized_category_name(value) != normalized_category_name(source_category_name)
            for value in values
        ):
            variety_category_mismatches.append(
                {
                    "crop_id": crop_id,
                    "crop_name": crops_by_id[crop_id]["name"],
                    "source_category": source_category_name,
                    "variety_categories": sorted(values),
                }
            )

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=REVIEW_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(review_rows)

    report = {
        "format_version": 1,
        "source_contract": {
            "directory": source_dir.name,
            "category_file": CATEGORY_FILE,
            "crop_file": CROP_FILE,
            "variety_file": VARIETY_FILE,
        },
        "counts": {
            "source_categories": len(categories),
            "source_crops": len(crops),
            "source_crops_with_category": sum(row["category_id"] is not None for row in crops),
            "source_crops_missing_category": sum(row["category_id"] is None for row in crops),
            "taxonomy_categories": len(taxonomy.categories),
            "taxonomy_crop_types": len(taxonomy.crop_types),
            "matched_crops": sum(row["match_status"] == "MATCHED" for row in review_rows),
            "unresolved_crops": sum(row["match_status"] == "UNRESOLVED" for row in review_rows),
            "crop_variety_rows": len(variety_categories),
            "crop_variety_rows_with_category": sum(
                category is not None for _, category in variety_categories
            ),
            "crop_variety_rows_missing_category": sum(category is None for _, category in variety_categories),
        },
        "category_status_counts": dict(
            sorted(Counter(row["category_status"] for row in review_rows).items())
        ),
        "match_method_counts": dict(sorted(Counter(row["match_method"] for row in review_rows).items())),
        "crop_variety_category_counts": dict(
            sorted(Counter(category or "NULL" for _, category in variety_categories).items())
        ),
        "crop_variety_category_mismatches": variety_category_mismatches,
    }
    return output.getvalue(), json.dumps(report, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    review_csv, report_json = build_review(args.source_dir, args.workbook)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "crop_category_review.csv").write_text(review_csv, encoding="utf-8")
    (args.output_dir / "crop_category_review_report.json").write_text(report_json, encoding="utf-8")
    print(report_json, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
