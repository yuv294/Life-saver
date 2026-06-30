"""
Scheduling Agent — takes a task (or list) and autonomously places it on Google Calendar.

Agentic chain:
  get_energy_windows() → get_calendar_events(next 7 days) → [for each task] create_calendar_event()
  → send_push_notification()
"""

from services.gemini_service import run_agent
from services.calendar_service import CalendarService
from services.firebase_service import FirebaseService
from services.chrono_service import ChronoService
from services.graph_service import GraphService
from services.gmail_service import GmailService
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from models.user import User
from models.task import Task
from datetime import datetime, timezone, timedelta
import uuid
import logging

logger = logging.getLogger(__name__)

SCHEDULING_SYSTEM_PROMPT = """You are an intelligent calendar assistant. Your job is to schedule tasks
onto the user's Google Calendar autonomously, respecting their energy levels and existing commitments.

Workflow for EACH task you need to schedule:
1. Call get_energy_windows() to get predicted energy for the next 48 hours.
2. Call get_calendar_events(start_date, end_date) for the next 7 days.
3. Find the best FREE slot that:
   - Matches the task's skill type to the user's energy peaks
   - Is before the task deadline
   - Doesn't conflict with existing events
   - Is long enough for the estimated_hours
4. Call create_calendar_event() to block the slot.
5. Call send_push_notification() to confirm to the user.

Skill → energy time preferences:
- analytical: 8am-12pm (peak cognition)
- creative: 9am-1pm
- administrative: 1pm-5pm
- communicative: 10am-4pm
- relational: 9am-3pm
- physical: 7am-10am or 5pm-7pm

If no good slot exists before the deadline, schedule at the nearest available time and
send a warning notification about the tight timeline.

Execute autonomously. Do not ask for confirmation."""


async def run_scheduling_agent(
    user_id: str,
    task_ids: list,
    db: AsyncSession,
) -> str:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return "User not found"

    # Load tasks
    tasks_result = await db.execute(
        select(Task).where(
            Task.id.in_([uuid.UUID(tid) for tid in task_ids]),
            Task.user_id == uuid.UUID(user_id),
        )
    )
    tasks = tasks_result.scalars().all()
    if not tasks:
        return "No tasks found to schedule"

    calendar_svc = CalendarService(user.google_access_token, user.google_refresh_token)
    firebase_svc = FirebaseService()
    chrono_svc = ChronoService(db)
    graph_svc = GraphService(db)
    gmail_svc = GmailService(user.google_access_token, user.google_refresh_token)

    # Patch firebase to use user's FCM token
    _orig = firebase_svc.send_push
    async def _send(title, body, fcm_token=None, **kwargs):
        return await _orig(title=title, body=body, fcm_token=fcm_token or user.fcm_token, **kwargs)
    firebase_svc.send_push = _send

    class TaskShim:
        async def list_tasks(self, uid):
            return [
                {
                    "id": str(t.id),
                    "title": t.title,
                    "skill_tags": t.skill_tags,
                    "deadline": t.deadline.isoformat() if t.deadline else None,
                    "estimated_hours": t.estimated_hours or 1.0,
                    "cascade_severity": t.cascade_severity,
                    "status": t.status,
                }
                for t in tasks
            ]
        async def reschedule(self, task_id, new_datetime, reason=None, user_id=None):
            return {"status": "scheduled", "task_id": task_id, "at": new_datetime}

    class ProcrastinationShim:
        async def detect(self, task_id):
            return {}

    services = {
        "calendar": calendar_svc,
        "firebase": firebase_svc,
        "chrono": chrono_svc,
        "graph": graph_svc,
        "gmail": gmail_svc,
        "tasks": TaskShim(),
        "procrastination": ProcrastinationShim(),
    }

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    end_date = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")

    task_list = "\n".join(
        f"- {t.title} (est. {t.estimated_hours or 1}h, "
        f"deadline: {t.deadline.isoformat() if t.deadline else 'no deadline'}, "
        f"skills: {', '.join(t.skill_tags or ['administrative'])})"
        for t in tasks
    )

    user_message = (
        f"Today is {today}. Please schedule the following tasks on my calendar "
        f"between now and {end_date}:\n{task_list}"
    )

    return await run_agent(
        system_prompt=SCHEDULING_SYSTEM_PROMPT,
        user_message=user_message,
        user_id=user_id,
        services=services,
    )
