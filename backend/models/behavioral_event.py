from sqlalchemy import String, ForeignKey, func, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from database import Base
import uuid
from datetime import datetime


VALID_EVENT_TYPES = {
    "task_started",
    "task_completed",
    "task_paused",
    "task_opened_no_progress",
    "app_opened",
    "notification_tapped",
    "brief_read",
    "reschedule_requested",
    "recovery_day_declared",
    "voice_task_added",
    "context_saved",
    "context_restored",
    "cluster_session_started",
}


class BehavioralEvent(Base):
    __tablename__ = "behavioral_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
