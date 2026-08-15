import uuid
from datetime import datetime

from openg2p_fastapi_common.models import BaseORMModel
from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class CatalogueImportRun(BaseORMModel):
    """One attempt to turn a set of SQL sources into a catalogue release."""

    __tablename__ = "catalogue_import_runs"

    import_run_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    release_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("catalogue_releases.release_id"),
        nullable=True,
        index=True,
    )
    country_code: Mapped[str] = mapped_column(String(3), nullable=False, index=True)
    source_version: Mapped[str] = mapped_column(String, nullable=False, index=True)
    manifest_checksum: Mapped[str] = mapped_column(String, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="PENDING", index=True)
    trigger: Mapped[str] = mapped_column(String, nullable=False, default="MANUAL")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_summary: Mapped[str | None] = mapped_column(String, nullable=True)
    run_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)


class CatalogueImportScript(BaseORMModel):
    """Execution and checksum record for one SQL file in an import run."""

    __tablename__ = "catalogue_import_scripts"
    __table_args__ = (UniqueConstraint("import_run_id", "script_id", name="uq_import_run_script"),)

    import_script_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    import_run_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("catalogue_import_runs.import_run_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    script_id: Mapped[str] = mapped_column(String, nullable=False)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    checksum: Mapped[str] = mapped_column(String, nullable=False)
    execution_order: Mapped[int] = mapped_column(Integer, nullable=False)
    dataset_kind: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="PENDING", index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    affected_rows: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(String, nullable=True)
