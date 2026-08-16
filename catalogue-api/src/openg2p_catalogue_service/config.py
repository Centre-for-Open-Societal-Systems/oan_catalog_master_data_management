from openg2p_fastapi_common.config import Settings as BaseSettings
from pydantic_settings import SettingsConfigDict

from . import __version__


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="catalogue_api_", env_file=".env", extra="allow")

    openapi_title: str = "OpenG2P Catalogue Service"
    openapi_description: str = "Versioned catalogue/reference values for OpenG2P services."
    openapi_version: str = __version__

    db_driver: str = "postgresql+asyncpg"
    db_username: str = "postgres"
    db_password: str = "password"
    db_hostname: str = "localhost"
    db_port: int = 5432
    db_dbname: str = "catalogue"

    default_country_code: str = "XKM"
    cache_expire_seconds: int = 300
    expected_schema_version: str = "014"
    readiness_timeout_seconds: float = 5.0
