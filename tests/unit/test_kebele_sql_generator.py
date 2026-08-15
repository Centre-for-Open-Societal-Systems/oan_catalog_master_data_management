import importlib.util
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
GENERATOR_PATH = PROJECT_ROOT / "scripts" / "kebele" / "generate_seed_sql.py"
SPEC = importlib.util.spec_from_file_location("generate_kebele_seed", GENERATOR_PATH)
generator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(generator)


def test_kebele_seed_is_reproducible_and_preserves_match_provenance():
    sql_output, report, counts, zone_count, woreda_count = generator.build_seed(
        PROJECT_ROOT / "KebeleList.csv",
        PROJECT_ROOT / "woreda_data.csv",
        PROJECT_ROOT / "scripts" / "seed_db_sql" / "import_location_data.sql",
    )

    assert sql_output == (PROJECT_ROOT / "scripts" / "seed_db_sql" / "import_kebele_data.sql").read_text(
        encoding="utf-8"
    )
    assert report == (PROJECT_ROOT / "scripts" / "kebele" / "review" / "kebele_parent_matches.csv").read_text(
        encoding="utf-8"
    )
    assert counts == Counter(
        {
            "EXACT_WOREDA_CODE": 17882,
            "WOREDA_REFERENCE": 1629,
            "REVIEWED_CODE_HIERARCHY": 21,
            "REVIEWED_CROSSWALK": 3,
            "UNRESOLVED": 35,
        }
    )
    assert zone_count == 24
    assert woreda_count == 238
    assert "'ET140101101001', '1'" in sql_output
    assert "'ET070306', 'REVIEWED_CROSSWALK'" in sql_output
