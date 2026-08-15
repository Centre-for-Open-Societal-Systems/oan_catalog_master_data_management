import importlib.util
from collections import Counter
from pathlib import Path

from scripts.crop_taxonomy.transform_workbook import transform_workbook

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNNER_SCRIPT = PROJECT_ROOT / "docker" / "db-seed" / "run_sql_seeds.py"
MANIFEST_PATH = PROJECT_ROOT / "scripts" / "seed_db_sql" / "manifest.yaml"
SPEC = importlib.util.spec_from_file_location("run_sql_seeds", RUNNER_SCRIPT)
run_sql_seeds = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(run_sql_seeds)


def test_runner_validates_and_orders_manifest():
    manifest = run_sql_seeds.load_manifest(MANIFEST_PATH)
    scripts = run_sql_seeds.validate_manifest(manifest, MANIFEST_PATH)

    assert [script["id"] for script in scripts] == [
        "locations",
        "kebeles",
        "catalog-related",
        "crops",
        "crop-taxonomy",
        "livestock",
        "seeds",
        "seed-varieties",
        "seed-variety-matches",
    ]
    assert run_sql_seeds.staging_tables(scripts) == sorted(
        {
            "g2p_crop",
            "g2p_crop_category",
            "g2p_crop_characteristic_definition",
            "g2p_crop_taxonomy_category",
            "g2p_crop_taxonomy_type",
            "g2p_crop_variety",
            "g2p_crop_variety_characteristic",
            "g2p_crop_variety_source_record",
            "g2p_ecological_zone",
            "g2p_livestock_population",
            "g2p_livestock_body_condition",
            "g2p_livestock_breed",
            "g2p_livestock_gender",
            "g2p_livestock_location_type",
            "g2p_livestock_production_type",
            "g2p_livestock_production_type_species",
            "g2p_livestock_record_status",
            "g2p_livestock_registry_entry",
            "g2p_livestock_type",
            "g2p_kebele",
            "g2p_region",
            "g2p_seed_catalog",
            "g2p_seed_demand_summary",
            "g2p_seed_demand_trend",
            "g2p_seed_demand_trend_by_crop",
            "g2p_seed_variety_source_record",
            "g2p_woreda",
            "g2p_zone",
        }
    )


def test_runner_checksum_is_deterministic_and_content_sensitive(tmp_path):
    manifest = run_sql_seeds.load_manifest(MANIFEST_PATH)
    scripts = run_sql_seeds.validate_manifest(manifest, MANIFEST_PATH)
    first = run_sql_seeds.manifest_checksum(MANIFEST_PATH, scripts)
    second = run_sql_seeds.manifest_checksum(MANIFEST_PATH, scripts)

    assert first == second
    assert first.startswith("sha256:")

    copied_manifest = tmp_path / "manifest.yaml"
    copied_sql = tmp_path / "one.sql"
    copied_manifest.write_text(
        """
schema_version: "1.0"
country_code: ETH
source_version: test-v1
scripts:
  - id: one
    filename: one.sql
    order: 1
    dataset_kind: catalogue
    staging_tables: [g2p_crop]
    canonical_targets: [catalogues]
""".lstrip(),
        encoding="utf-8",
    )
    copied_sql.write_text("SELECT 1;\n", encoding="utf-8")
    copied = run_sql_seeds.load_manifest(copied_manifest)
    copied_scripts = run_sql_seeds.validate_manifest(copied, copied_manifest)
    before = run_sql_seeds.manifest_checksum(copied_manifest, copied_scripts)
    copied_sql.write_text("SELECT 2;\n", encoding="utf-8")
    after = run_sql_seeds.manifest_checksum(copied_manifest, copied_scripts)

    assert before != after


def test_stable_ids_are_repeatable_and_scoped():
    first = run_sql_seeds.stable_id("value", "catalogue-a", "1")

    assert first == run_sql_seeds.stable_id("value", "catalogue-a", "1")
    assert first != run_sql_seeds.stable_id("value", "catalogue-b", "1")


def test_livestock_breed_public_codes_preserve_standard_and_namespace_etlits_values():
    assert run_sql_seeds.livestock_breed_public_code(10, "1.01.10", "cattle", "Boran") == "1.01.10"
    assert run_sql_seeds.livestock_breed_public_code(91, None, "goat", "Boer") == "etlits-goat-boer"


def test_connection_prefers_standard_postgresql_database_variable(monkeypatch):
    captured = {}

    def fake_connect(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setenv("CATALOGUE_DB", "legacy_name")
    monkeypatch.setenv("PGDATABASE", "standard_name")
    monkeypatch.setattr(run_sql_seeds.psycopg2, "connect", fake_connect)

    run_sql_seeds.connect()

    assert captured["dbname"] == "standard_name"


def test_crop_taxonomy_publisher_creates_every_value_and_relation(monkeypatch):
    transformed = transform_workbook(PROJECT_ROOT / "crop_catalog_variety_included.xlsx")
    source_counts = Counter(item["variety_code"] for item in transformed.source_records)

    category_rows = [
        (
            item["category_code"],
            item["source_id"],
            item["display_name"],
            {"am": item["display_name_amh"]} if item["display_name_amh"] else None,
            item["image_url"],
            item["description"],
            item["status"],
        )
        for item in transformed.categories
    ]
    type_rows = [
        (
            item["type_code"],
            item["source_id"] or None,
            item["category_code"],
            item["display_name"],
            {"am": item["display_name_amh"]} if item["display_name_amh"] else None,
            item["scientific_name"],
            item["centre"],
            item["image_url"],
            item["description"],
            int(item["source_reported_variety_count"]),
            item["status"],
        )
        for item in transformed.crop_types
    ]
    variety_rows = [
        (
            item["variety_code"],
            item["type_code"],
            item["display_name"],
            {"am": item["display_name_amh"]} if item["display_name_amh"] else None,
            item["status"],
            source_counts[item["variety_code"]],
        )
        for item in transformed.varieties
    ]
    definition_rows = [
        (
            item["characteristic_code"],
            item["display_name"],
            item["value_type"],
            item["default_unit_code"] or None,
            item["applicable_category_code"] or None,
            item["description"],
        )
        for item in transformed.characteristic_definitions
    ]
    source_rows = [
        tuple(
            item[column] or None
            for column in (
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
            )
        )
        for item in transformed.source_records
    ]
    characteristic_rows = [
        tuple(
            item[column] or None
            for column in (
                "source_record_code",
                "characteristic_code",
                "raw_value",
                "value_text",
                "value_numeric",
                "value_boolean",
                "value_min",
                "value_max",
                "unit_code",
            )
        )
        for item in transformed.characteristics
    ]

    class FakeCursor:
        def __init__(self):
            self.rows = []

        def execute(self, statement):
            if "FROM g2p_crop_taxonomy_category" in statement:
                self.rows = category_rows
            elif "FROM g2p_crop_taxonomy_type" in statement:
                self.rows = type_rows
            elif "FROM g2p_crop_variety variety" in statement:
                self.rows = variety_rows
            elif "FROM g2p_crop_characteristic_definition" in statement:
                self.rows = definition_rows
            elif "FROM g2p_crop_variety_source_record source" in statement:
                self.rows = source_rows
            elif "FROM g2p_crop_variety_characteristic" in statement:
                self.rows = characteristic_rows
            else:
                raise AssertionError(f"Unexpected publisher query: {statement}")

        def fetchall(self):
            return self.rows

    inserted = []
    monkeypatch.setattr(
        run_sql_seeds,
        "insert_catalogue",
        lambda _cursor, _release_id, code, _name: f"catalogue-{code}",
    )
    monkeypatch.setattr(
        run_sql_seeds.psycopg2.extras,
        "execute_values",
        lambda _cursor, statement, rows, **_kwargs: inserted.append((statement, list(rows))),
    )

    crop_ids_by_type = {
        item[0]: [index]
        for index, item in enumerate(type_rows, start=1)
    }
    crop_value_ids = {
        crop_id: f"crop-{crop_id}"
        for crop_ids in crop_ids_by_type.values()
        for crop_id in crop_ids
    }
    run_sql_seeds.publish_crop_taxonomy(
        FakeCursor(),
        "release-1",
        {1: "sql-category-1"},
        crop_value_ids,
        crop_ids_by_type,
        {item[0]: [1] for item in type_rows},
    )

    assert [len(rows) for _, rows in inserted] == [
        8,
        119,
        238,
        1359,
        2718,
        359,
        1360,
        10322,
    ]
    type_relations = inserted[2][1]
    variety_relations = inserted[4][1]
    assert Counter(row[2] for row in type_relations) == {"category": 238}
    assert Counter(row[2] for row in variety_relations) == {
        "crop_type": 1359,
        "crop": 1359,
    }
    melkassa_id = run_sql_seeds.stable_id("value", "catalogue-crop_variety", "maize-melkassa-1-q")
    maize_id = run_sql_seeds.stable_id("value", "catalogue-crop_type", "maize")
    assert any(row[1] == melkassa_id and row[3] == maize_id for row in variety_relations)


def test_seed_variety_publisher_preserves_all_rows_and_links_only_matches(monkeypatch):
    source_rows = [
        (
            20,
            1,
            "Maize",
            "Melkassa-1Q",
            "Cereal",
            2008,
            None,
            "2008",
            "EIAR",
            "Domestic",
            "https://example.test/20",
            "maize-melkassa-1-q",
            "EXACT_NAME_AND_CROP",
            "MATCHED",
            None,
            "maize",
            "cereals",
            1,
        ),
        (
            21,
            2,
            "Wheat",
            "Unreviewed cultivar",
            "Cereal",
            None,
            None,
            None,
            None,
            None,
            "https://example.test/21",
            None,
            "UNRESOLVED",
            "UNRESOLVED",
            "No crop-scoped exact match",
            None,
            None,
            2,
        ),
    ]

    class FakeCursor:
        def execute(self, statement):
            assert "FROM g2p_seed_variety_source_record seed" in statement

        def fetchall(self):
            return source_rows

    inserted = []
    monkeypatch.setattr(
        run_sql_seeds,
        "insert_catalogue",
        lambda _cursor, _release_id, code, _name: f"catalogue-{code}",
    )
    monkeypatch.setattr(
        run_sql_seeds.psycopg2.extras,
        "execute_values",
        lambda _cursor, statement, rows, **_kwargs: inserted.append((statement, list(rows))),
    )

    run_sql_seeds.publish_seed_varieties(
        FakeCursor(),
        "release-1",
        {1: "seed-crop-1", 2: "seed-crop-2"},
        {1: "crop-1", 2: "crop-2"},
    )

    assert [len(rows) for _, rows in inserted] == [2, 1, 7, 2]
    assert Counter(row[2] for row in inserted[2][1]) == {
        "seed_crop": 2,
        "crop_variety": 1,
        "crop_type": 1,
        "category": 1,
        "crop": 2,
    }
    canonical_rows = inserted[3][1]
    assert canonical_rows[0][6] is not None
    assert canonical_rows[1][6] is None
    assert canonical_rows[0][18] == "MATCHED"
    assert canonical_rows[1][18] == "UNRESOLVED"
