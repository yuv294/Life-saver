from sqlalchemy import String, Integer, Date, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from database import Base
import uuid
from datetime import datetime, date


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    google_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(Text)
    fcm_token: Mapped[str | None] = mapped_column(Text)
    skill_profile: Mapped[dict] = mapped_column(JSONB, default=dict)
    chronotype_model: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    streak_count: Mapped[int] = mapped_column(Integer, default=0)
    last_active_date: Mapped[date | None] = mapped_column(Date)
    recovery_days_used: Mapped[int] = mapped_column(Integer, default=0)
    # Google OAuth tokens — stored so agents can act on the user's behalf
    google_access_token: Mapped[str | None] = mapped_column(Text)
    google_refresh_token: Mapped[str | None] = mapped_column(Text)
    google_token_expiry: Mapped[str | None] = mapped_column(Text)  # ISO 8601 string
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
