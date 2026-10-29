"""Operator recovery receipts; domain objects remain domain-owned."""

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from sidetrack.db import Base


class ArtworkRecovery(Base):
    __tablename__ = "artwork_recoveries"
    plan_digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    entries: Mapped[list[dict]] = mapped_column(JSON)
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    reversed: Mapped[bool] = mapped_column(Boolean, default=False)
