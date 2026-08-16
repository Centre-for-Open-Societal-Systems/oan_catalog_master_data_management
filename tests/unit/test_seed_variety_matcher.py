from pathlib import Path

from scripts.seed_variety.match_seed_varieties import (
    build_match_plan,
    render_match_sql,
    render_review_csv,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_SQL = PROJECT_ROOT / "crop_catalog_scripts" / "05_insert_crop_variety.sql"
WORKBOOK = PROJECT_ROOT / "crop_catalog_variety_included.xlsx"
MATCH_SQL = PROJECT_ROOT / "scripts" / "seed_db_sql" / "import_seed_variety_matches.sql"
REVIEW_CSV = PROJECT_ROOT / "scripts" / "seed_variety" / "review" / "seed_variety_match_review.csv"


def test_match_artifacts_are_current_and_only_accept_crop_scoped_exact_matches():
    decisions, report = build_match_plan(SOURCE_SQL.read_text(encoding="utf-8"), WORKBOOK)

    assert len(decisions) == 902
    assert report["status_counts"] == {"MATCHED": 309, "UNRESOLVED": 593}
    assert report["method_counts"] == {
        "EXACT_NAME_AND_CROP": 308,
        "EXACT_SOURCE_ID": 1,
        "UNRESOLVED": 593,
    }
    assert render_match_sql(decisions) == MATCH_SQL.read_text(encoding="utf-8")
    assert render_review_csv(decisions) == REVIEW_CSV.read_text(encoding="utf-8")


def test_source_id_collision_is_rejected_but_exact_crop_name_match_is_accepted():
    decisions, _ = build_match_plan(SOURCE_SQL.read_text(encoding="utf-8"), WORKBOOK)
    by_id = {item.source_variety_id: item for item in decisions}

    # Source ID 350 points to Melkassa 1Q in the workbook but Malt Barley HB1963
    # in the archived list. Crop-scoped name matching chooses HB1963 instead.
    assert by_id[350].source_id_candidate == "maize-melkassa-1-q"
    assert by_id[350].matched_variety_code == "barley-hb-1963"
    assert by_id[350].match_method == "EXACT_NAME_AND_CROP"
    assert "SOURCE_ID_NAMESPACE_DISAGREES" in by_id[350].review_reason

    assert by_id[266].matched_variety_code == "sorghum-fendisha-1"
    assert by_id[266].match_method == "EXACT_SOURCE_ID"


def test_unknown_and_non_exact_varieties_remain_unresolved():
    decisions, _ = build_match_plan(SOURCE_SQL.read_text(encoding="utf-8"), WORKBOOK)
    by_id = {item.source_variety_id: item for item in decisions}

    assert by_id[2].match_status == "UNRESOLVED"
    assert by_id[2].matched_variety_code is None
    assert by_id[921].match_status == "UNRESOLVED"
