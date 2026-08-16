import importlib.util
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SEED_SCRIPT = PROJECT_ROOT / "docker" / "db-seed" / "seed_catalogue_pack.py"
SPEC = importlib.util.spec_from_file_location("seed_catalogue_pack", SEED_SCRIPT)
seed_catalogue_pack = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(seed_catalogue_pack)


def test_fixture_pack_is_valid_and_checksum_is_stable():
    pack = PROJECT_ROOT / "tests" / "fixtures" / "packs" / "XKM"
    manifest, catalogues = seed_catalogue_pack.load_pack(pack, [])

    seed_catalogue_pack.validate_pack(manifest, catalogues)

    assert manifest["country"] == "XKM"
    assert [catalogue["code"] for catalogue in catalogues] == ["gender"]
    assert seed_catalogue_pack.pack_checksum(manifest, catalogues) == (
        "sha256:a8b404027aad0946ac03ab991e83eaa063a138549bf53aed6135f8395fa9d3c7"
    )
