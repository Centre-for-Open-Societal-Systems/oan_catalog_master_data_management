def normalized_pagination(page: int, page_size: int, maximum: int = 1000) -> tuple[int, int]:
    return max(1, page), min(max(1, page_size), maximum)
