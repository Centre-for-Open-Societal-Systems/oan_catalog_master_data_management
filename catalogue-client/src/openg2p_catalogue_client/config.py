from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CatalogueClientConfig:
    base_url: str
    token_url: str
    client_id: str
    client_secret: str
    country_code: str
    scope: str | None = None
    timeout_seconds: float = 30.0
    max_attempts: int = 3
    retry_backoff_seconds: float = 0.5

    def __post_init__(self):
        for field_name in ("base_url", "token_url", "client_id", "client_secret", "country_code"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} must not be empty")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least one")
        if self.retry_backoff_seconds < 0:
            raise ValueError("retry_backoff_seconds must not be negative")

        object.__setattr__(self, "base_url", self.base_url.rstrip("/"))
        object.__setattr__(self, "country_code", self.country_code.upper())
