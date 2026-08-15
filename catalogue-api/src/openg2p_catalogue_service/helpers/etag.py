def release_etag(checksum: str) -> str:
    return f'"{checksum}"'


def matches_if_none_match(if_none_match: str | None, etag: str) -> bool:
    if not if_none_match:
        return False
    for candidate in if_none_match.split(","):
        candidate = candidate.strip()
        if candidate.startswith("W/"):
            candidate = candidate[2:].strip()
        if candidate in ("*", etag):
            return True
    return False
