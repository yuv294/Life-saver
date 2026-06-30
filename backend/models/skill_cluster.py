from sqlalchemy import String, Float, ForeignKey, func, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from database import Base
import uuid
from datetime import datetime


class SkillCluster(Base):
    __tablename__ = "skill_clusters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str | None] = mapped_column(String(255))
    dominant_skill: Mapped[str | None] = mapped_column(String(50))
    skill_tags: Mapped[list] = mapped_column(ARRAY(String), default=list)
    task_ids: Mapped[list] = mapped_column(ARRAY(String), default=list)  # UUID strings
    estimated_total_hours: Mapped[float | None] = mapped_column(Float)
    suggested_session_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
