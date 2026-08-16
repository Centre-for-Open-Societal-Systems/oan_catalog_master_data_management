from fastapi import Response

from ..config import Settings
from .etag import matches_if_none_match, release_etag


def apply_release_cache_headers(
    response: Response,
    checksum: str,
    release_version: str,
    if_none_match: str | None = None,
) -> Response | None:
    etag = release_etag(checksum)
    headers = {
        "ETag": etag,
        "Cache-Control": f"public, max-age={Settings.get_config().cache_expire_seconds}",
        "X-Catalogue-Release": release_version,
    }
    if matches_if_none_match(if_none_match, etag):
        return Response(status_code=304, headers=headers)
    for name, value in headers.items():
        response.headers[name] = value
    return None
