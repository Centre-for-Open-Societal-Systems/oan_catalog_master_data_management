import uuid
from datetime import date, datetime

from openg2p_fastapi_common.models import BaseORMModel
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class CatalogueRelease(BaseORMModel):
    __tablename__ = "catalogue_releases"
    __table_args__ = (
        UniqueConstraint("country_code", "version", name="uq_catalogue_release_country_version"),
        Index(
            "uq_catalogue_active_country",
            "country_code",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
    )

    release_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    country_code: Mapped[str] = mapped_column(String(3), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String, nullable=False)
    schema_version: Mapped[str] = mapped_column(String, nullable=False, default="1.0")
    checksum: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="STAGED", index=True)
    manifest: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Catalogue(BaseORMModel):
    __tablename__ = "catalogues"
    __table_args__ = (UniqueConstraint("release_id", "code", name="uq_catalogue_release_code"),)

    catalogue_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    release_id: Mapped[str] = mapped_column(
        String, ForeignKey("catalogue_releases.release_id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String, nullable=False, index=True)
    domain: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    display_name_i18n: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_hierarchical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="ACTIVE")


class CatalogueValue(BaseORMModel):
    __tablename__ = "catalogue_values"
    __table_args__ = (
        UniqueConstraint("catalogue_id", "code", name="uq_catalogue_value_code"),
        CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from",
            name="ck_catalogue_value_dates",
        ),
    )

    catalogue_value_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    catalogue_id: Mapped[str] = mapped_column(
        String, ForeignKey("catalogues.catalogue_id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String, nullable=False, index=True)
    parent_value_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("catalogue_values.catalogue_value_id"), nullable=True, index=True
    )
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    display_name_i18n: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    semantic_roles: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    sort_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="ACTIVE")
    value_metadata: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)


class CatalogueValueRelation(BaseORMModel):
    __tablename__ = "catalogue_value_relations"
    __table_args__ = (
        UniqueConstraint(
            "source_value_id",
            "relation_type",
            "target_value_id",
            name="uq_catalogue_value_relation",
        ),
        CheckConstraint(
            "source_value_id <> target_value_id",
            name="ck_catalogue_value_relation_not_self",
        ),
    )

    relation_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source_value_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("catalogue_values.catalogue_value_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relation_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    target_value_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("catalogue_values.catalogue_value_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


class CatalogueSeedRun(BaseORMModel):
    __tablename__ = "catalogue_seed_runs"

    seed_run_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    release_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("catalogue_releases.release_id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(String, nullable=True)
