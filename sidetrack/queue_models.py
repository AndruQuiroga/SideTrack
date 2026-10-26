"""Application-owned durable job and scheduling records."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from sidetrack.db import Base


class BackgroundJob(Base):
    __tablename__ = "background_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    queue_job_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    task: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(16), default="queued")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class JobSchedule(Base):
    __tablename__ = "job_schedules"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    task: Mapped[str] = mapped_column(String(128))
    arguments: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    queue: Mapped[str] = mapped_column(String(32), default="default")
    next_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    interval_seconds: Mapped[int | None] = mapped_column(Integer)


class ScheduleOccurrence(Base):
    __tablename__ = "job_schedule_occurrences"
    __table_args__ = (UniqueConstraint("schedule_id", "revision", "due_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    schedule_id: Mapped[str] = mapped_column(
        ForeignKey("job_schedules.id", ondelete="CASCADE"), index=True
    )
    revision: Mapped[int] = mapped_column(Integer)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RequestPacing(Base):
    __tablename__ = "job_request_pacing"

    name: Mapped[str] = mapped_column(String(32), primary_key=True)
    next_request_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
