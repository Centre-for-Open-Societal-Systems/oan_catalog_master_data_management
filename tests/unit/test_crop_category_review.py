import json
from pathlib import Path

from scripts.crop_catalogue.review_crop_categories import build_review

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = PROJECT_ROOT / "crop_catalog_scripts"
WORKBOOK = PROJECT_ROOT / "crop_catalog_variety_included.xlsx"
REVIEW_DIR = PROJECT_ROOT / "scripts" / "crop_catalogue" / "review"


def test_crop_category_review_is_reproducible_and_covers_source_contract():
    review_csv, report_json = build_review(SOURCE_DIR, WORKBOOK)

    assert review_csv == (REVIEW_DIR / "crop_category_review.csv").read_text(encoding="utf-8")
    assert report_json == (REVIEW_DIR / "crop_category_review_report.json").read_text(encoding="utf-8")

    report = json.loads(report_json)
    assert report["counts"] == {
        "source_categories": 7,
        "source_crops": 150,
        "source_crops_with_category": 122,
        "source_crops_missing_category": 28,
        "taxonomy_categories": 8,
        "taxonomy_crop_types": 119,
        "matched_crops": 120,
        "unresolved_crops": 30,
        "crop_variety_rows": 902,
        "crop_variety_rows_with_category": 236,
        "crop_variety_rows_missing_category": 666,
    }
    assert report["category_status_counts"] == {
        "ALIGNED": 119,
        "CATEGORY_MISSING": 28,
        "DIVERGENT": 1,
        "SOURCE_CATEGORY_ONLY": 2,
    }
    assert report["crop_variety_category_mismatches"] == []
