from sqlalchemy import String, Integer, Float, Text, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy import DateTime
from database import Base
import uuid
from datetime import datetime


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    skill_tags: Mapped[list] = mapped_column(ARRAY(String), default=list)
    complexity: Mapped[str] = mapped_column(String(10), default="medium")
    estimated_hours: Mapped[float | None] = mapped_column(Float)
    actual_hours: Mapped[float | None] = mapped_column(Float)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    reschedule_count: Mapped[int] = mapped_column(Integer, default=0)
    cascade_severity: Mapped[int] = mapped_column(Integer, default=0)
    # stored as string UUIDs for PostgreSQL ARRAY compatibility
    depends_on: Mapped[list] = mapped_column(ARRAY(String), default=list)
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    calendar_event_id: Mapped[str | None] = mapped_column(Text)
    procrastination_trigger: Mapped[str | None] = mapped_column(String(20))
    last_opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    open_without_progress_count: Mapped[int] = mapped_column(Integer, default=0)
    # Eisenhower matrix
    importance: Mapped[str] = mapped_column(String(10), default="medium")
    urgency: Mapped[str] = mapped_column(String(10), default="medium")
    eisenhower_quadrant: Mapped[int | None] = mapped_column(Integer)
    # Extra metadata stored as JSONB for flexibility
    extra: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
