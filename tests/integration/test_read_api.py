import importlib.util
import os
import shutil
import sys
from pathlib import Path

import psycopg2
import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

TEST_DSN = os.environ.get("CATALOGUE_TEST_DB_DSN")
pytestmark = pytest.mark.skipif(
    not TEST_DSN,
    reason="CATALOGUE_TEST_DB_DSN must point to a disposable PostgreSQL database",
)
if TEST_DSN:
    os.environ["CATALOGUE_API_DB_DATASOURCE"] = TEST_DSN.replace("postgresql://", "postgresql+asyncpg://", 1)
os.environ["CATALOGUE_API_DEFAULT_COUNTRY_CODE"] = "ETH"

from openg2p_catalogue_service.controllers import (
    CatalogueController,
    CropTaxonomyController,
    GeographyController,
    LivestockController,
    SeedVarietyController,
    StatisticsController,
)
from openg2p_catalogue_service.services import (
    CatalogueService,
    CropTaxonomyService,
    GeographyService,
    LivestockService,
    SeedVarietyService,
    SnapshotService,
    StatisticsService,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = PROJECT_ROOT / "docker" / "db-seed" / "run_sql_seeds.py"
MIGRATION_RUNNER_PATH = PROJECT_ROOT / "docker" / "db-migration" / "migrate_database.py"
MIGRATIONS_PATH = PROJECT_ROOT / "scripts" / "migrations"
MANIFEST_PATH = PROJECT_ROOT / "scripts" / "seed_db_sql" / "manifest.yaml"
SPEC = importlib.util.spec_from_file_location("read_api_sql_seeds", RUNNER_PATH)
runner = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(runner)
MIGRATION_SPEC = importlib.util.spec_from_file_location("read_api_migration_runner", MIGRATION_RUNNER_PATH)
migration_runner = importlib.util.module_from_spec(MIGRATION_SPEC)
assert MIGRATION_SPEC.loader is not None
sys.modules[MIGRATION_SPEC.name] = migration_runner
MIGRATION_SPEC.loader.exec_module(migration_runner)


def rebuild_and_seed_database():
    conn = psycopg2.connect(TEST_DSN)
    try:
        with conn.cursor() as cursor:
            cursor.execute("DROP SCHEMA public CASCADE")
            cursor.execute("CREATE SCHEMA public")
        conn.commit()
        migration_runner.run(
            conn,
            migration_runner.discover_migrations(MIGRATIONS_PATH),
            expected_version="014",
        )

        manifest = runner.load_manifest(MANIFEST_PATH)
        scripts = runner.validate_manifest(manifest, MANIFEST_PATH)
        checksum = runner.manifest_checksum(MANIFEST_PATH, scripts)
        runner.run(conn, manifest, scripts, checksum, "TEST")
    finally:
        conn.close()


@pytest.fixture(scope="module")
def client():
    rebuild_and_seed_database()

    CatalogueService()
    CropTaxonomyService()
    GeographyService()
    LivestockService()
    SeedVarietyService()
    StatisticsService()
    SnapshotService()

    app = FastAPI()
    app.include_router(CatalogueController().router)
    app.include_router(CropTaxonomyController().router)
    app.include_router(GeographyController().router)
    app.include_router(LivestockController().router)
    app.include_router(SeedVarietyController().router)
    app.include_router(StatisticsController().router)
    with TestClient(app) as test_client:
        yield test_client


def test_catalogue_reads_are_filterable_paginated_and_version_pinnable(client):
    release_response = client.get("/v1/releases/current")
    assert release_response.status_code == 200
    release = release_response.json()
    assert release["country_code"] == "ETH"
    assert release["status"] == "ACTIVE"
    assert release_response.headers["x-catalogue-release"] == release["version"]

    catalogues = client.get("/v1/catalogues").json()
    assert [item["code"] for item in catalogues["catalogues"]] == [
        "crop",
        "crop_category",
        "crop_taxonomy_category",
        "crop_type",
        "crop_variety",
        "ecological_zone",
        "etlits_livestock_record_status",
        "livestock_body_condition",
        "livestock_breed",
        "livestock_gender",
        "livestock_location_type",
        "livestock_production_type",
        "livestock_type",
        "seed_crop",
        "seed_variety",
    ]

    values_response = client.get(
        "/v1/catalogues/crop/values",
        params={
            "page_size": 2,
            "search": "Barley",
            "release_version": release["version"],
        },
    )
    assert values_response.status_code == 200
    values = values_response.json()
    assert values["total"] >= 1
    assert len(values["values"]) <= 2
    assert all("barley" in item["display_name"].lower() for item in values["values"])

    all_crops = client.get("/v1/catalogues/crop/values", params={"page_size": 1000}).json()
    assert all_crops["total"] == 150
    maize_enriched = next(item for item in all_crops["values"] if item["code"] == "1")
    assert maize_enriched["metadata"]["scientific_name"] == "Zea mays L."
    assert maize_enriched["metadata"]["centre"] == "BKARC"
    assert maize_enriched["metadata"]["varieties_count"] == 99
    assert maize_enriched["metadata"]["varieties_count_source"] == "SQL_CROP_VARIETY"
    papaya = next(item for item in all_crops["values"] if item["metadata"]["taxonomy_type_code"] == "papaya")
    assert papaya["display_name_i18n"] == {"am": "ፓፓያ"}
    assert papaya["metadata"]["record_source"] == "WORKBOOK_ADDITION"
    assert papaya["metadata"]["varieties_count_source"] == "WORKBOOK_CROP_VARIETY"

    maize = client.get(
        "/v1/catalogues/crop/values",
        params={"search": "Maize", "release_version": release["version"]},
    ).json()["values"][0]
    assert maize["code"] == "1"
    assert maize["relations"] == [
        {
            "type": "category",
            "target_catalogue_code": "crop_category",
            "target_code": "1",
            "target_display_name": "Cereal Crops",
        },
        {
            "type": "preferred_ecological_zone",
            "target_catalogue_code": "ecological_zone",
            "target_code": "2",
            "target_display_name": "Weyna Dega",
        },
    ]
    assert "category_id" not in maize["metadata"]
    assert "preferred_ecological_zone_id" not in maize["metadata"]

    categories = client.get("/v1/catalogues/crop_category/values").json()
    assert categories["total"] == 7
    assert categories["values"][0]["display_name"] == "Cereal Crops"

    category_options = client.get(
        "/v1/catalogue-values",
        params={"catalogue_code": "crop_category"},
    )
    assert category_options.status_code == 200
    assert category_options.headers["etag"] == f'"{release["checksum"]}"'
    assert category_options.headers["x-catalogue-release"] == release["version"]
    assert category_options.headers["cache-control"].startswith("public, max-age=")
    option_payload = category_options.json()
    assert option_payload["total"] == 7
    assert option_payload["options"][0] == {
        "code": "1",
        "display_name": "Cereal Crops",
    }
    assert set(option_payload["options"][0]) == {"code", "display_name"}

    unchanged_options = client.get(
        "/v1/catalogue-values",
        params={"catalogue_code": "crop_category"},
        headers={"If-None-Match": category_options.headers["etag"]},
    )
    assert unchanged_options.status_code == 304
    assert unchanged_options.content == b""
    assert unchanged_options.headers["etag"] == category_options.headers["etag"]
    assert unchanged_options.headers["x-catalogue-release"] == release["version"]

    cereal_options = client.get(
        "/v1/catalogue-values",
        params={
            "catalogue_code": "crop",
            "relation_type": "category",
            "related_catalogue_code": "crop_category",
            "related_value_code": "1",
        },
    ).json()
    assert cereal_options["total"] == 14
    assert all(set(option) == {"code", "display_name"} for option in cereal_options["options"])

    maize_variety_options = client.get(
        "/v1/catalogue-values",
        params={
            "catalogue_code": "crop_variety",
            "relation_type": "crop",
            "related_catalogue_code": "crop",
            "related_value_code": "1",
            "page_size": 1000,
        },
    ).json()
    assert maize_variety_options["total"] > 0
    assert all(
        set(option) == {"code", "display_name"}
        for option in maize_variety_options["options"]
    )

    cereal_crops = client.get(
        "/v1/catalogues/crop/values",
        params={
            "relation_type": "category",
            "related_catalogue_code": "crop_category",
            "related_value_code": "1",
        },
    ).json()
    assert cereal_crops["total"] == 14
    assert all(
        any(
            relation["type"] == "category" and relation["target_code"] == "1"
            for relation in crop["relations"]
        )
        for crop in cereal_crops["values"]
    )

    cattle_breeds = client.get(
        "/v1/catalogues/livestock_breed/values",
        params={
            "relation_type": "species",
            "related_catalogue_code": "livestock_type",
            "related_value_code": "cattle",
        },
    ).json()
    assert cattle_breeds["total"] == 35
    boran = next(value for value in cattle_breeds["values"] if value["code"] == "1.01.10")
    assert boran["metadata"]["breed_type"] == "Indigenous"
    assert boran["relations"] == [
        {
            "type": "species",
            "target_catalogue_code": "livestock_type",
            "target_code": "cattle",
            "target_display_name": "Cattle",
        }
    ]

    goat_breeds = client.get(
        "/v1/catalogues/livestock_breed/values",
        params={"search": "Boer"},
    ).json()
    assert goat_breeds["values"][0]["code"] == "etlits-goat-boer"

    locations = client.get("/v1/catalogues/livestock_location_type/values").json()
    assert locations["total"] == 3
    low_land = next(value for value in locations["values"] if value["code"] == "Low Land")
    assert low_land["relations"][0]["target_catalogue_code"] == "ecological_zone"
    assert low_land["relations"][0]["target_code"] == "1"

    cattle_production_types = client.get(
        "/v1/catalogues/livestock_production_type/values",
        params={
            "relation_type": "valid_for_species",
            "related_value_code": "cattle",
        },
    ).json()
    assert cattle_production_types["total"] == 10

    conditions = client.get("/v1/catalogues/livestock_body_condition/values").json()
    assert conditions["total"] == 5
    statuses = client.get("/v1/catalogues/etlits_livestock_record_status/values").json()
    assert statuses["total"] == 6
    assert statuses["values"][0]["code"] == "PENDING"

    taxonomy_categories = client.get("/v1/catalogues/crop_taxonomy_category/values").json()
    assert taxonomy_categories["total"] == 8

    cereal_types = client.get(
        "/v1/catalogues/crop_type/values",
        params={
            "relation_type": "category",
            "related_catalogue_code": "crop_taxonomy_category",
            "related_value_code": "cereal",
        },
    ).json()
    assert cereal_types["total"] == 14
    assert all(
        any(
            relation["type"] == "category"
            and relation["target_code"] == "cereal"
            for relation in item["relations"]
        )
        for item in cereal_types["values"]
    )

    maize_varieties = client.get(
        "/v1/catalogues/crop_variety/values",
        params={
            "relation_type": "crop_type",
            "related_catalogue_code": "crop_type",
            "related_value_code": "maize",
        },
    ).json()
    assert maize_varieties["total"] == 84
    assert any(item["display_name"] == "Melkassa 1Q" for item in maize_varieties["values"])

    consolidated_maize_varieties = client.get(
        "/v1/catalogues/crop_variety/values",
        params={
            "relation_type": "crop",
            "related_catalogue_code": "crop",
            "related_value_code": "1",
            "page_size": 200,
        },
    ).json()
    assert consolidated_maize_varieties["total"] == 135
    assert any(
        item["code"] == "maize-melkassa-1-q"
        for item in consolidated_maize_varieties["values"]
    )
    assert any(
        item["code"] == "ethioseed-107"
        for item in consolidated_maize_varieties["values"]
    )

    melkassa = client.get("/v1/crop-varieties/maize-melkassa-1-q")
    assert melkassa.status_code == 200
    detail = melkassa.json()["variety"]
    assert detail["display_name"] == "Melkassa 1Q"
    assert detail["crop_type"]["code"] == "maize"
    assert detail["category"]["code"] == "cereal"
    assert len(detail["source_records"]) == 2
    assert {item["release_year"] for item in detail["source_records"]} == {2001, 2013}
    assert all(item["characteristics"] for item in detail["source_records"])

    missing_variety = client.get("/v1/crop-varieties/does-not-exist")
    assert missing_variety.status_code == 404
    assert "Unknown crop variety" in missing_variety.json()["detail"]

    missing = client.get(
        "/v1/catalogues",
        params={"release_version": "does-not-exist"},
    )
    assert missing.status_code == 404


def test_seed_varieties_are_filterable_and_expose_match_provenance(client):
    matched_response = client.get(
        "/v1/seed-varieties",
        params={"match_status": "MATCHED", "page_size": 5},
    )
    assert matched_response.status_code == 200
    matched = matched_response.json()
    assert matched["total"] == 309
    assert len(matched["varieties"]) == 5
    assert all(item["seed_crop"] for item in matched["varieties"])
    assert all(item["matched_crop_variety"] for item in matched["varieties"])
    assert all(item["crop_type"] for item in matched["varieties"])
    assert all(item["category"] for item in matched["varieties"])

    first = matched["varieties"][0]
    filtered = client.get(
        "/v1/seed-varieties",
        params={
            "crop_variety_code": first["matched_crop_variety"]["code"],
            "page_size": 10,
        },
    ).json()
    assert filtered["total"] >= 1
    assert all(
        item["matched_crop_variety"]["code"] == first["matched_crop_variety"]["code"]
        for item in filtered["varieties"]
    )

    unresolved = client.get(
        "/v1/seed-varieties",
        params={"match_status": "UNRESOLVED", "page_size": 1},
    ).json()
    assert unresolved["total"] == 593
    assert unresolved["varieties"][0]["seed_crop"] is not None
    assert unresolved["varieties"][0]["matched_crop_variety"] is None
    assert unresolved["varieties"][0]["crop_type"] is None
    assert unresolved["varieties"][0]["category"] is None

    detail_response = client.get(f"/v1/seed-varieties/{first['code']}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["variety"]["source_variety_id"] == first["source_variety_id"]
    assert detail["variety"]["details_url"]
    assert detail_response.headers["etag"]

    missing = client.get("/v1/seed-varieties/ethioseed-999999")
    assert missing.status_code == 404


def test_livestock_catalogue_exposes_typed_registry_contract(client):
    species_response = client.get("/v1/livestock/species")
    assert species_response.status_code == 200
    species = species_response.json()
    assert species["total"] == 5
    cattle = next(item for item in species["species"] if item["code"] == "cattle")
    assert cattle["scientific_name"] == "Bos taurus & Bos indicus"
    assert cattle["in_lis_population"] is True
    beehive = next(item for item in species["species"] if item["code"] == "beehive")
    assert beehive["in_lis_population"] is False
    assert beehive["in_etlits_registry"] is True

    indigenous_cattle = client.get(
        "/v1/livestock/breeds",
        params={"species_code": "cattle", "breed_type": "Indigenous"},
    ).json()
    assert indigenous_cattle["total"] == 25
    assert all(item["species"]["code"] == "cattle" for item in indigenous_cattle["breeds"])
    assert all(item["breed_type"] == "Indigenous" for item in indigenous_cattle["breeds"])
    boran = next(item for item in indigenous_cattle["breeds"] if item["code"] == "1.01.10")
    assert boran["breed_code"] == "1.01.10"
    assert boran["in_etlits_registry"] is True

    references = client.get("/v1/livestock/reference-data").json()
    assert len(references["genders"]) == 4
    assert len(references["location_types"]) == 3
    assert len(references["body_conditions"]) == 5
    assert len(references["production_types"]) == 13
    assert len(references["record_statuses"]) == 6
    milk = next(item for item in references["production_types"] if item["code"] == "Milk")
    assert {item["code"] for item in milk["valid_species"]} == {
        "camel",
        "cattle",
        "goat",
    }

    cached = client.get(
        "/v1/livestock/species",
        headers={"If-None-Match": species_response.headers["etag"]},
    )
    assert cached.status_code == 304
    assert cached.content == b""


def test_livestock_registry_snapshot_and_validation_are_published(client):
    entries_response = client.get("/v1/livestock/registry-entries", params={"page_size": 100})
    assert entries_response.status_code == 200
    entries = entries_response.json()
    assert entries["total"] == 12
    assert len(entries["entries"]) == 12

    known = next(item for item in entries["entries"] if item["id"] == "livestock-008569662215")
    assert known["species_code"] == "cattle"
    assert known["breed_id"] == 10
    assert known["breed_code"] == "1.01.10"
    assert not any(
        known["validation"][flag]
        for flag in (
            "breed_unrecognised",
            "breed_outside_national_standard",
            "breed_species_mismatch",
            "production_type_species_mismatch",
        )
    )

    unrecognised = client.get("/v1/livestock/registry-entries", params={"search": "BoranR"}).json()
    assert unrecognised["total"] == 1
    assert unrecognised["entries"][0]["validation"]["breed_unrecognised"] is True

    validations = client.get("/v1/livestock/registry-validation", params={"page_size": 100}).json()
    assert validations["total"] == 12
    assert sum(item["breed_unrecognised"] for item in validations["validations"]) == 2
    assert sum(item["breed_outside_national_standard"] for item in validations["validations"]) == 5
    assert sum(item["breed_species_mismatch"] for item in validations["validations"]) == 1
    assert sum(item["production_type_species_mismatch"] for item in validations["validations"]) == 3

    issues = client.get(
        "/v1/livestock/registry-validation",
        params={"has_issues": True, "page_size": 100},
    ).json()
    assert issues["total"] == 9
    assert all(
        any(
            item[flag]
            for flag in (
                "breed_unrecognised",
                "breed_outside_national_standard",
                "breed_species_mismatch",
                "production_type_species_mismatch",
            )
        )
        for item in issues["validations"]
    )


def test_geography_reads_expose_hierarchy_and_filters(client):
    levels = client.get("/v1/geography/levels").json()
    assert [item["code"] for item in levels["levels"]] == [
        "region",
        "zone",
        "woreda",
        "kebele",
    ]
    assert levels["levels"][1]["parent_level_code"] == "region"
    assert levels["levels"][3]["parent_level_code"] == "woreda"

    regions = client.get(
        "/v1/geography/units",
        params={"level_code": "region", "page_size": 20},
    ).json()
    assert regions["total"] == 14
    assert all(item["level_code"] == "region" for item in regions["units"])

    first_region = regions["units"][0]
    assert "display_name_amh" in first_region
    assert first_region["display_name_amh"] is None
    detail = client.get(
        f"/v1/geography/units/{first_region['code']}",
        params={"level_code": "region"},
    ).json()
    assert detail["unit"]["code"] == first_region["code"]

    children = client.get(
        "/v1/geography/units",
        params={"level_code": "zone", "parent_code": first_region["code"]},
    ).json()
    assert all(item["parent_code"] == first_region["code"] for item in children["units"])

    kebeles = client.get(
        "/v1/geography/units",
        params={"level_code": "kebele", "parent_code": "ET140101"},
    ).json()
    assert kebeles["total"] == 1
    assert kebeles["units"][0]["code"] == "ET140101101001"
    assert kebeles["units"][0]["parent_code"] == "ET140101"
    assert kebeles["units"][0]["metadata"]["match_method"] == "EXACT_WOREDA_CODE"


def test_statistics_reads_support_domain_filters(client):
    livestock = client.get(
        "/v1/statistics/livestock-population",
        params={"species_code": "cattle", "page_size": 100},
    ).json()
    assert livestock["total"] > 0
    assert all(item["species_code"] == "cattle" for item in livestock["statistics"])

    crop = client.get(
        "/v1/statistics/seed-demand/by-crop",
        params={"page_size": 1},
    ).json()
    assert crop["total"] == 18
    assert len(crop["statistics"]) == 1


def test_snapshot_is_complete_and_honors_if_none_match(client):
    response = client.get("/v1/snapshots/current")
    assert response.status_code == 200
    body = response.json()
    assert len(body["catalogues"]) == 15
    assert len(body["geography"]["units"]) == 21053
    assert len(body["agriculture_statistics"]["livestock_population"]) == 40
    assert len(body["agriculture_statistics"]["seed_demand_by_crop"]) == 18
    crop_catalogue = next(item for item in body["catalogues"] if item["code"] == "crop")
    maize = next(item for item in crop_catalogue["values"] if item["code"] == "1")
    assert {relation["type"] for relation in maize["relations"]} == {
        "category",
        "preferred_ecological_zone",
    }

    cached = client.get(
        "/v1/snapshots/current",
        headers={"If-None-Match": response.headers["etag"]},
    )
    assert cached.status_code == 304
    assert cached.content == b""
    assert cached.headers["etag"] == response.headers["etag"]


def test_openapi_contract_exposes_all_registry_routes_parameters_and_conditional_reads(
    client,
):
    contract = client.app.openapi()
    expected_paths = {
        "/v1/releases/current",
        "/v1/catalogues",
        "/v1/catalogue-values",
        "/v1/catalogues/{catalogue_code}/values",
        "/v1/crop-varieties/{variety_code}",
        "/v1/seed-varieties",
        "/v1/seed-varieties/{seed_variety_code}",
        "/v1/snapshots/current",
        "/v1/geography/levels",
        "/v1/geography/units",
        "/v1/geography/units/{unit_code}",
        "/v1/livestock/species",
        "/v1/livestock/breeds",
        "/v1/livestock/reference-data",
        "/v1/livestock/registry-entries",
        "/v1/livestock/registry-validation",
        "/v1/statistics/livestock-population",
        "/v1/statistics/seed-demand/summary",
        "/v1/statistics/seed-demand/trends",
        "/v1/statistics/seed-demand/by-crop",
    }
    assert set(contract["paths"]) == expected_paths
    assert all(set(methods) == {"get"} for methods in contract["paths"].values())
    assert all("304" in methods["get"]["responses"] for methods in contract["paths"].values())

    value_parameters = {
        parameter["name"]: parameter
        for parameter in contract["paths"]["/v1/catalogues/{catalogue_code}/values"]["get"]["parameters"]
    }
    assert set(value_parameters) == {
        "catalogue_code",
        "country_code",
        "release_version",
        "status",
        "parent_code",
        "relation_type",
        "related_catalogue_code",
        "related_value_code",
        "search",
        "page",
        "page_size",
        "If-None-Match",
    }
    assert value_parameters["catalogue_code"]["required"] is True
    assert value_parameters["page"]["schema"]["minimum"] == 1
    assert value_parameters["page_size"]["schema"]["maximum"] == 1000

    option_parameters = {
        parameter["name"]: parameter
        for parameter in contract["paths"]["/v1/catalogue-values"]["get"]["parameters"]
    }
    assert set(option_parameters) == {
        "catalogue_code",
        "country_code",
        "release_version",
        "status",
        "parent_code",
        "relation_type",
        "related_catalogue_code",
        "related_value_code",
        "search",
        "page",
        "page_size",
        "If-None-Match",
    }
    assert option_parameters["catalogue_code"]["required"] is True
    assert option_parameters["page"]["schema"]["minimum"] == 1
    assert option_parameters["page_size"]["schema"]["maximum"] == 1000

    seed_parameters = {
        parameter["name"]: parameter
        for parameter in contract["paths"]["/v1/seed-varieties"]["get"]["parameters"]
    }
    assert {
        "seed_crop_code",
        "crop_variety_code",
        "crop_type_code",
        "category_code",
        "match_status",
        "release_year",
        "search",
        "page",
        "page_size",
    }.issubset(seed_parameters)
    release_year_schema = next(
        item for item in seed_parameters["release_year"]["schema"]["anyOf"] if item.get("type") == "integer"
    )
    assert release_year_schema["minimum"] == 1800
    assert release_year_schema["maximum"] == 2200

    breed_parameters = {
        parameter["name"]: parameter
        for parameter in contract["paths"]["/v1/livestock/breeds"]["get"]["parameters"]
    }
    assert {
        "country_code",
        "release_version",
        "species_code",
        "breed_type",
        "in_national_standard",
        "in_etlits_registry",
        "search",
        "page",
        "page_size",
        "If-None-Match",
    } == set(breed_parameters)


def test_http_validation_empty_results_and_not_found_contract(client):
    assert client.get("/v1/catalogues/crop/values", params={"page": 0}).status_code == 422
    assert client.get("/v1/geography/units", params={"page_size": 1001}).status_code == 422
    assert client.get("/v1/geography/units", params={"search": ""}).status_code == 422

    empty = client.get(
        "/v1/statistics/livestock-population",
        params={"species_code": "not-a-species"},
    )
    assert empty.status_code == 200
    assert empty.json()["total"] == 0
    assert empty.json()["statistics"] == []

    missing = client.get("/v1/geography/units/does-not-exist")
    assert missing.status_code == 404
    assert "Unknown geography unit" in missing.json()["detail"]


def test_release_upgrade_changes_current_etag_and_preserves_pinned_release(client, tmp_path):
    old_response = client.get("/v1/releases/current")
    old_release = old_response.json()
    old_etag = old_response.headers["etag"]

    copied = tmp_path / "seed_db_sql"
    shutil.copytree(MANIFEST_PATH.parent, copied)
    upgraded_manifest_path = copied / "manifest.yaml"
    upgraded_manifest = yaml.safe_load(upgraded_manifest_path.read_text(encoding="utf-8"))
    upgraded_manifest["source_version"] = "ETH-read-api-contract-v2"
    upgraded_manifest_path.write_text(yaml.safe_dump(upgraded_manifest, sort_keys=False), encoding="utf-8")
    conn = psycopg2.connect(TEST_DSN)
    try:
        manifest = runner.load_manifest(upgraded_manifest_path)
        scripts = runner.validate_manifest(manifest, upgraded_manifest_path)
        checksum = runner.manifest_checksum(upgraded_manifest_path, scripts)
        runner.run(conn, manifest, scripts, checksum, "TEST")
    finally:
        conn.close()

    current = client.get("/v1/releases/current")
    assert current.status_code == 200
    assert current.json()["version"] == upgraded_manifest["source_version"]
    assert current.headers["etag"] != old_etag

    old_pinned = client.get(
        "/v1/releases/current",
        params={"release_version": old_release["version"]},
    )
    assert old_pinned.status_code == 200
    assert old_pinned.json()["status"] == "RETIRED"
    assert old_pinned.headers["etag"] == old_etag

    old_values = client.get(
        "/v1/catalogues/crop/values",
        params={"release_version": old_release["version"], "page_size": 1},
    )
    assert old_values.status_code == 200
    assert old_values.json()["release"]["version"] == old_release["version"]

    changed = client.get("/v1/snapshots/current", headers={"If-None-Match": old_etag})
    assert changed.status_code == 200
    unchanged = client.get(
        "/v1/snapshots/current",
        headers={"If-None-Match": current.headers["etag"]},
    )
    assert unchanged.status_code == 304
