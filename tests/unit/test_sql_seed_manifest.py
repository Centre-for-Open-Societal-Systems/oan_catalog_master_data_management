import re
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SEED_DIR = PROJECT_ROOT / "scripts" / "seed_db_sql"
MIGRATION_DIR = PROJECT_ROOT / "scripts" / "migrations"


def load_manifest():
    with (SEED_DIR / "manifest.yaml").open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def test_manifest_declares_every_sql_file_once_in_explicit_order():
    manifest = load_manifest()
    scripts = manifest["scripts"]
    declared_files = [script["filename"] for script in scripts]
    actual_files = sorted(path.name for path in SEED_DIR.glob("*.sql"))
    orders = [script["order"] for script in scripts]

    assert sorted(declared_files) == actual_files
    assert len(declared_files) == len(set(declared_files))
    assert len(orders) == len(set(orders))
    assert orders == sorted(orders)


def test_manifest_tables_are_owned_by_migrations():
    manifest = load_manifest()
    migration_sql = "\n".join(
        path.read_text(encoding="utf-8").lower() for path in sorted(MIGRATION_DIR.glob("*.sql"))
    )

    for script in manifest["scripts"]:
        for table in script["staging_tables"] + script["canonical_targets"]:
            assert re.search(
                rf"create (?:table|view) (?:if not exists )?{re.escape(table.lower())}(?:\s*\(|\s+as)",
                migration_sql,
            )


def test_statistics_are_not_classified_as_catalogue_values():
    manifest = load_manifest()
    by_id = {script["id"]: script for script in manifest["scripts"]}

    assert "livestock_population_statistics" in by_id["livestock"]["canonical_targets"]
    assert "seed_demand_summary_statistics" in by_id["seeds"]["canonical_targets"]
    assert by_id["locations"]["dataset_kind"] == "geography"


def test_kebele_seed_declares_reviewed_hierarchy_counts():
    by_id = {script["id"]: script for script in load_manifest()["scripts"]}
    kebeles = by_id["kebeles"]

    assert kebeles["order"] > by_id["locations"]["order"]
    assert kebeles["expected_rows"] == {
        "g2p_zone": 125,
        "g2p_woreda": 1379,
        "g2p_kebele": 19570,
    }
    assert kebeles["expected_match_status_rows"] == {
        "MATCHED": 19535,
        "UNRESOLVED": 35,
    }


def test_livestock_seed_declares_complete_reference_counts():
    livestock = {script["id"]: script for script in load_manifest()["scripts"]}["livestock"]

    assert livestock["expected_rows"] == {
        "g2p_livestock_type": 5,
        "g2p_livestock_population": 40,
        "g2p_livestock_breed": 94,
        "g2p_livestock_gender": 4,
        "g2p_livestock_location_type": 3,
        "g2p_livestock_body_condition": 5,
        "g2p_livestock_production_type": 13,
        "g2p_livestock_production_type_species": 34,
        "g2p_livestock_record_status": 6,
        "g2p_livestock_registry_entry": 12,
    }
    assert "beehive" in livestock["required_catalogue_values"]["livestock_type"]
    assert livestock["allowed_unlinked_production_types"] == ["Egg"]
    assert livestock["expected_uncoded_breeds"] == 4
    assert livestock["expected_live_record_statuses"] == ["ACTIVE"]
    assert "catalogue_value_relations" in livestock["canonical_targets"]


def test_crop_dependencies_publish_as_related_catalogues():
    by_id = {script["id"]: script for script in load_manifest()["scripts"]}

    assert by_id["catalog-related"]["order"] < by_id["crops"]["order"]
    assert by_id["catalog-related"]["staging_tables"] == [
        "g2p_crop_category",
        "g2p_ecological_zone",
    ]
    assert "catalogue_value_relations" in by_id["catalog-related"]["canonical_targets"]
    crops = by_id["crops"]
    assert crops["expected_rows"] == {"g2p_crop": 150}
    assert crops["expected_record_source_rows"] == {
        "SQL_CROP_CATALOG": 129,
        "WORKBOOK_ADDITION": 21,
    }
    assert crops["expected_taxonomy_match_status_rows"] == {
        "MATCHED": 120,
        "UNRESOLVED": 30,
    }
    assert crops["expected_category_source_rows"] == {
        "SQL_CROP_CATALOG": 17,
        "WORKBOOK_TAXONOMY_MAPPING": 105,
        "UNRESOLVED": 28,
    }


def test_crop_taxonomy_seed_declares_complete_relational_structure():
    by_id = {script["id"]: script for script in load_manifest()["scripts"]}
    taxonomy = by_id["crop-taxonomy"]

    assert taxonomy["order"] > by_id["crops"]["order"]
    assert taxonomy["canonical_targets"] == [
        "catalogues",
        "catalogue_values",
        "catalogue_value_relations",
        "crop_variety_source_records",
        "crop_characteristic_definitions",
        "crop_variety_characteristics",
    ]
    assert taxonomy["expected_rows"] == {
        "g2p_crop_taxonomy_category": 8,
        "g2p_crop_taxonomy_type": 119,
        "g2p_crop_variety": 1359,
        "g2p_crop_variety_source_record": 1360,
        "g2p_crop_characteristic_definition": 359,
        "g2p_crop_variety_characteristic": 10322,
    }
    assert taxonomy["allowed_missing_type_source_ids"] == ["fine-bush"]


def test_seed_variety_match_counts_are_release_gates():
    by_id = {script["id"]: script for script in load_manifest()["scripts"]}
    matches = by_id["seed-variety-matches"]

    assert matches["order"] > by_id["seed-varieties"]["order"]
    assert matches["expected_match_status_rows"] == {
        "MATCHED": 309,
        "UNRESOLVED": 593,
    }
    assert matches["expected_match_method_rows"] == {
        "EXACT_SOURCE_ID": 1,
        "EXACT_NAME_AND_CROP": 308,
        "UNRESOLVED": 593,
    }
    assert matches["expected_consolidated_crop_variety_rows"] == 1952
    assert matches["canonical_targets"] == [
        "catalogues",
        "catalogue_values",
        "catalogue_value_relations",
        "seed_variety_source_records",
    ]
