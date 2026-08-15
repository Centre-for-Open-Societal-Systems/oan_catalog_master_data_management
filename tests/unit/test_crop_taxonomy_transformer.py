from pathlib import Path

from scripts.crop_taxonomy.transform_workbook import (
    characteristic_code,
    parse_decimal_range,
    parse_release_year,
    split_localized_name,
    transform_workbook,
    write_outputs,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKBOOK = PROJECT_ROOT / "crop_catalog_variety_included.xlsx"


def test_name_localization_preserves_non_amharic_parenthetical_text():
    english, amharic = split_localized_name("Ziziphus (Kurkura) (ኩርኩራ)")

    assert english == "Ziziphus (Kurkura)"
    assert amharic == "ኩርኩራ"


def test_range_parser_is_conservative_and_supports_source_units():
    assert parse_decimal_range("2300-2600 m.a.s.l") == (2300, 2600)
    assert parse_decimal_range(">900 mm") == (900, None)
    assert parse_decimal_range("<1600 m.a.s.l") == (None, 1600)
    assert parse_decimal_range("60-100qt/ha qt/ha") == (60, 100)
    assert parse_decimal_range("80 for row planting and 120 for broadcasting kg/ha") == (
        None,
        None,
    )


def test_release_year_does_not_guess_ambiguous_values():
    assert parse_release_year("2013") == 2013
    assert parse_release_year("1989/99") is None
    assert parse_release_year("-1970") is None
    assert parse_release_year("19999/00") is None


def test_characteristic_mapping_resolves_reviewed_header_cases():
    assert characteristic_code("plantHeight") == "plant_height"
    assert characteristic_code("rainfall") == "rainfall"
    assert characteristic_code("rainFall") == "rainfall"
    assert characteristic_code("1000SeedWeight") == "seed_weight_1000"


def test_real_workbook_builds_expected_taxonomy_and_reports_source_issues(tmp_path):
    result = transform_workbook(WORKBOOK)

    assert result.has_errors is False
    assert result.report["counts"] == {
        "source_categories": 8,
        "source_crop_types": 119,
        "source_variety_records": 1360,
        "categories": 8,
        "crop_types": 119,
        "varieties": 1359,
        "source_records": 1360,
        "characteristic_definitions": 359,
        "characteristic_values": 10322,
        "errors": 0,
        "warnings": 10,
    }
    fine_bush = next(item for item in result.crop_types if item["type_code"] == "fine-bush")
    assert fine_bush["source_id"] == ""
    assert fine_bush["category_code"] == "fruit-and-vegetables"

    melkassa = [
        item
        for item in result.varieties
        if item["type_code"] == "maize" and item["display_name"] == "Melkassa 1Q"
    ]
    assert len(melkassa) == 1
    melkassa_sources = [
        item for item in result.source_records if item["variety_code"] == melkassa[0]["variety_code"]
    ]
    assert len(melkassa_sources) == 2
    assert {item["release_year"] for item in melkassa_sources} == {2001, 2013}

    finding_codes = [item["code"] for item in result.report["findings"]]
    assert "MISSING_TYPE_SOURCE_ID" in finding_codes
    assert "MULTIPLE_VARIETY_SOURCE_RECORDS" in finding_codes
    assert "FRACTIONAL_MATURITY_NOT_PROJECTED" in finding_codes
    assert finding_codes.count("VARIETY_COUNT_MISMATCH") == 5

    write_outputs(result, tmp_path)
    assert {path.name for path in tmp_path.iterdir()} == {
        "crop_categories.csv",
        "crop_types.csv",
        "crop_varieties.csv",
        "crop_variety_source_records.csv",
        "crop_characteristic_definitions.csv",
        "crop_variety_characteristics.csv",
        "validation_report.json",
    }
    assert (tmp_path / "validation_report.json").read_text(encoding="utf-8").endswith("\n")
