import csv
import io
import json
from pathlib import Path

from scripts.livestock.generate_seed_sql import build_outputs

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = PROJECT_ROOT / "livestock_catalog"
OUTPUT_SQL = PROJECT_ROOT / "scripts" / "seed_db_sql" / "import_livestock_data.sql"
REVIEW_CSV = PROJECT_ROOT / "scripts" / "livestock" / "review" / "livestock_registry_validation.csv"
REPORT_JSON = PROJECT_ROOT / "scripts" / "livestock" / "review" / "livestock_transform_report.json"


def test_livestock_seed_and_review_artifacts_are_reproducible():
    sql_output, review_output, report_output = build_outputs(SOURCE_DIR)

    assert sql_output == OUTPUT_SQL.read_text(encoding="utf-8")
    assert review_output == REVIEW_CSV.read_text(encoding="utf-8")
    assert report_output == REPORT_JSON.read_text(encoding="utf-8")
    assert "DROP TABLE" not in sql_output.upper()
    assert "CREATE TABLE" not in sql_output.upper()
    assert "INSERT INTO g2p_livestock_registry_entry" in sql_output
    assert "('beehive', 'Beehive'" in sql_output


def test_livestock_source_counts_and_registry_quality_flags_are_preserved():
    _, review_output, report_output = build_outputs(SOURCE_DIR)
    report = json.loads(report_output)
    rows = list(csv.DictReader(io.StringIO(review_output)))

    assert report["dataset_counts"] == {
        "livestock_body_condition": 5,
        "livestock_breed": 94,
        "livestock_catalog": 5,
        "livestock_gender": 4,
        "livestock_location_type": 3,
        "livestock_population": 40,
        "livestock_production_type": 13,
        "livestock_production_type_species": 34,
        "livestock_record_status": 6,
        "livestock_registry_entry": 12,
    }
    assert report["validation_counts"] == {
        "breed_outside_national_standard": 5,
        "breed_species_mismatch": 1,
        "breed_unrecognised": 2,
        "production_type_species_mismatch": 3,
    }
    assert len(rows) == 12
    assert sum(row["breed_unrecognised"] == "TRUE" for row in rows) == 2
    assert sum(row["breed_species_mismatch"] == "TRUE" for row in rows) == 1
    assert sum(row["production_type_species_mismatch"] == "TRUE" for row in rows) == 3
