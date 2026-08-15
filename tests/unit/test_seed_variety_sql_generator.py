from pathlib import Path

import pytest

from scripts.seed_variety.generate_seed_sql import (
    EXPECTED_ROWS,
    SeedVarietyAdapterError,
    extract_values,
    render_seed_sql,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_SQL = PROJECT_ROOT / "crop_catalog_scripts" / "05_insert_crop_variety.sql"
GENERATED_SQL = PROJECT_ROOT / "scripts" / "seed_db_sql" / "import_seed_variety.sql"


def test_generated_seed_variety_sql_is_current_and_preserves_all_rows():
    generated = render_seed_sql(SOURCE_SQL)

    assert generated == GENERATED_SQL.read_text(encoding="utf-8")
    assert f"Preserved source rows: {EXPECTED_ROWS}" in generated
    assert "seed crops represented: 67" in generated
    assert "INSERT INTO g2p_seed_variety_source_record" in generated
    assert "ON CONFLICT (source_variety_id) DO UPDATE" in generated
    assert "DROP TABLE" not in generated
    assert "CREATE TABLE" not in generated
    assert "matched_variety_code" not in generated
    assert "Jan. 1, 202" in generated


def test_adapter_rejects_destructive_or_structurally_incomplete_sources():
    with pytest.raises(SeedVarietyAdapterError, match="data only"):
        extract_values("DROP TABLE crop_variety;")
    with pytest.raises(SeedVarietyAdapterError, match="INSERT"):
        extract_values("SELECT 1;")
