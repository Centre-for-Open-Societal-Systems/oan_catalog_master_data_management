import importlib.util
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ETAG_PATH = PROJECT_ROOT / "catalogue-api" / "src" / "openg2p_catalogue_service" / "helpers" / "etag.py"
SPEC = importlib.util.spec_from_file_location("catalogue_etag", ETAG_PATH)
etag = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(etag)


def test_release_etag_is_strong_and_quoted():
    assert etag.release_etag("abc123") == '"abc123"'


def test_if_none_match_accepts_lists_weak_tags_and_wildcard():
    current = '"abc123"'
    assert etag.matches_if_none_match('"old", "abc123"', current)
    assert etag.matches_if_none_match('W/"abc123"', current)
    assert etag.matches_if_none_match("*", current)


def test_if_none_match_rejects_a_different_release():
    assert not etag.matches_if_none_match('"old"', '"abc123"')
    assert not etag.matches_if_none_match(None, '"abc123"')
