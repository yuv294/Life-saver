from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
import uuid


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    estimated_hours: Optional[float] = Field(None, gt=0)
    deadline: Optional[datetime] = None
    complexity: str = Field("medium", pattern="^(low|medium|high)$")
    depends_on: List[str] = Field(default_factory=list)
    importance: str = Field("medium", pattern="^(low|medium|high)$")
    urgency: str = Field("medium", pattern="^(low|medium|high)$")


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(pending|in_progress|completed|abandoned)$")
    estimated_hours: Optional[float] = Field(None, gt=0)
    actual_hours: Optional[float] = Field(None, gt=0)
    deadline: Optional[datetime] = None
    complexity: Optional[str] = Field(None, pattern="^(low|medium|high)$")
    importance: Optional[str] = Field(None, pattern="^(low|medium|high)$")
    urgency: Optional[str] = Field(None, pattern="^(low|medium|high)$")
    depends_on: Optional[List[str]] = None
    fcm_token: Optional[str] = None


class TaskReschedule(BaseModel):
    new_datetime: datetime
    reason: Optional[str] = Field(
        None,
        description="Required if reschedule_count >= 2. One of: ambiguity, blocked_externally, low_energy, no_longer_needed",
    )


class TaskComplete(BaseModel):
    actual_hours: Optional[float] = Field(None, gt=0, description="Real time spent; defaults to the estimate")


class ContextSaveCreate(BaseModel):
    raw_brain_dump: str = Field(..., min_length=1)


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: Optional[str]
    skill_tags: List[str]
    complexity: str
    estimated_hours: Optional[float]
    actual_hours: Optional[float]
    deadline: Optional[datetime]
    status: str
    reschedule_count: int
    cascade_severity: int
    depends_on: List[str]
    scheduled_for: Optional[datetime]
    calendar_event_id: Optional[str]
    procrastination_trigger: Optional[str]
    importance: str
    urgency: str
    eisenhower_quadrant: Optional[int]
    created_at: datetime
    updated_at: datetime


class RescheduleWindow(BaseModel):
    start: datetime
    end: datetime
    energy_score: float
    tasks_displaced: int
    cascade_impact: int
    label: str


class RescheduleOptions(BaseModel):
    task_id: uuid.UUID
    reschedule_count: int
    windows: List[RescheduleWindow]
    no_options: bool = False
    no_options_alternatives: List[str] = Field(default_factory=list)
    requires_reason: bool = False
