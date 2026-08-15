import uuid
from datetime import datetime

from openg2p_fastapi_common.models import BaseORMModel
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


class LivestockRegistryEntry(BaseORMModel):
    __tablename__ = "livestock_registry_entries"
    __table_args__ = (
        UniqueConstraint(
            "release_id",
            "source_entry_id",
            name="uq_livestock_registry_release_source",
        ),
    )

    registry_entry_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    release_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("catalogue_releases.release_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_entry_id: Mapped[str] = mapped_column(String, nullable=False)
    species_code: Mapped[str] = mapped_column(String, nullable=False, index=True)
    breed_name: Mapped[str] = mapped_column(String, nullable=False)
    breed_source_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    breed_code: Mapped[str | None] = mapped_column(String, nullable=True)
    breed_species_code: Mapped[str | None] = mapped_column(String, nullable=True)
    breed_in_national_standard: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    gender_code: Mapped[str] = mapped_column(String, nullable=False)
    location_type_code: Mapped[str] = mapped_column(String, nullable=False)
    body_condition_code: Mapped[str] = mapped_column(String, nullable=False)
    production_type_code: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, index=True)
    source_created_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_updated_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    production_type_species_valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
