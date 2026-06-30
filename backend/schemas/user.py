from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime, date
import uuid


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: Optional[str]
    avatar_url: Optional[str]
    skill_profile: dict
    streak_count: int
    last_active_date: Optional[date]
    recovery_days_used: int
    created_at: datetime


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    fcm_token: Optional[str] = None


class OAuthTokenUpdate(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    expiry: Optional[str] = None


class PlanningAccuracy(BaseModel):
    skill: str
    estimated_hours: float
    actual_hours: float
    inflation_factor: float
    sample_count: int


class StreakStatus(BaseModel):
    streak_count: int
    last_active_date: Optional[date]
    recovery_days_remaining: int
    is_recovery_day_active: bool
