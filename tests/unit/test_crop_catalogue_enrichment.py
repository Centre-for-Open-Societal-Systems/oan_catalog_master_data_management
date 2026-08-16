from pathlib import Path

from scripts.crop_catalogue.enrich_crop_catalog import enrich_rows, render_insert

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = PROJECT_ROOT / "crop_catalog_scripts"
WORKBOOK = PROJECT_ROOT / "crop_catalog_variety_included.xlsx"
SOURCE_OUTPUT = SOURCE_DIR / "04_insert_crop_catalog.sql"
SEED_OUTPUT = PROJECT_ROOT / "scripts" / "seed_db_sql" / "import_crop_catalog.sql"


def test_enriched_crop_catalogue_is_reproducible_and_computes_variety_counts():
    rows = enrich_rows(SOURCE_DIR, WORKBOOK)

    assert render_insert(rows, "crop_catalog", generated=False) == SOURCE_OUTPUT.read_text(encoding="utf-8")
    assert render_insert(rows, "g2p_crop", generated=True) == SEED_OUTPUT.read_text(encoding="utf-8")
    assert len(rows) == 150
    assert len({row["taxonomy_type_code"] for row in rows if row["taxonomy_type_code"]}) == 119
    assert sum(row["record_source"] == "WORKBOOK_ADDITION" for row in rows) == 21
    assert (
        sum(row["varieties_count"] for row in rows if row["varieties_count_source"] == "SQL_CROP_VARIETY")
        == 902
    )
    assert (
        sum(
            row["varieties_count"] for row in rows if row["varieties_count_source"] == "WORKBOOK_CROP_VARIETY"
        )
        == 50
    )

    maize = next(row for row in rows if row["id"] == 1)
    assert maize["scientific_name"] == "Zea mays L."
    assert maize["centre"] == "BKARC"
    assert maize["varieties_count"] == 99
    assert maize["varieties_count_source"] == "SQL_CROP_VARIETY"

    papaya = next(row for row in rows if row["taxonomy_type_code"] == "papaya")
    assert papaya["record_source"] == "WORKBOOK_ADDITION"
    assert papaya["category_id"] == 6
    assert papaya["display_name_amh"] == "ፓፓያ"
    assert papaya["varieties_count"] > 0
