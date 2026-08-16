class CatalogueClientError(RuntimeError):
    """Base error raised by the registry client."""


class CatalogueAuthenticationError(CatalogueClientError):
    """The client-credentials token could not be obtained."""


class CatalogueResponseError(CatalogueClientError):
    """The Catalogue Service returned a terminal HTTP response."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"Catalogue Service returned HTTP {status_code}: {message}")


class CatalogueProtocolError(CatalogueClientError):
    """The response violated the registry synchronization contract."""
