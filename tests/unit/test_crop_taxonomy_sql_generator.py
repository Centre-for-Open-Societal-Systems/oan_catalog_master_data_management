from pathlib import Path

import pytest

from scripts.crop_taxonomy.generate_seed_sql import (
    render_seed_sql,
    sql_boolean,
    sql_number,
    sql_text,
)
from scripts.crop_taxonomy.transform_workbook import TransformError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKBOOK = PROJECT_ROOT / "crop_catalog_variety_included.xlsx"
GENERATED_SQL = PROJECT_ROOT / "scripts" / "seed_db_sql" / "import_crop_taxonomy.sql"


def test_generated_seed_sql_is_current_and_covers_all_relational_tables():
    generated = render_seed_sql(WORKBOOK)

    assert generated == GENERATED_SQL.read_text(encoding="utf-8")
    assert "categories=8, crop_types=119, varieties=1359" in generated
    for table in (
        "g2p_crop_taxonomy_category",
        "g2p_crop_taxonomy_type",
        "g2p_crop_variety",
        "g2p_crop_variety_source_record",
        "g2p_crop_characteristic_definition",
        "g2p_crop_variety_characteristic",
    ):
        assert f"INSERT INTO {table}" in generated


def test_sql_literals_escape_text_and_reject_unsafe_typed_values():
    assert sql_text("Farmer's field") == "'Farmer''s field'"
    assert sql_text("") == "NULL"
    assert sql_number("12.50") == "12.50"
    assert sql_boolean(True) == "TRUE"
    with pytest.raises(TransformError, match="Unsafe numeric SQL value"):
        sql_number("1; DROP TABLE catalogues")
