from datetime import datetime

from openg2p_fastapi_common.models import BaseORMModel
from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column


class CatalogueSchemaMigration(BaseORMModel):
    """Read-only ORM representation of migration-runner history."""

    __tablename__ = "catalogue_schema_migrations"

    version: Mapped[str] = mapped_column(String, primary_key=True)
    filename: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    checksum: Mapped[str] = mapped_column(String, nullable=False)
    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    execution_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    runner_version: Mapped[str] = mapped_column(String, nullable=False)
