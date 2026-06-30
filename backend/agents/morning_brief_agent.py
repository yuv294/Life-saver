"""
Morning Brief Agent — triggered daily at 6am via Cloud Scheduler.

Autonomous 7-step workflow:
  1. list_user_tasks()          → pending tasks with deadlines + cascade severity
  2. get_calendar_events(today) → what's already blocked
  3. get_energy_windows()       → today's predicted energy curve
  4. Gemini reasons             → picks Today's Mission, finds skill batch, flags risks
  5. Generates 4-sentence narrative brief
  6. send_push_notification()   → delivers brief to device
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
from models.behavioral_event import BehavioralEvent
from datetime import datetime, timezone
import logging
import uuid

logger = logging.getLogger(__name__)

MORNING_BRIEF_SYSTEM_PROMPT = """You are a proactive productivity coach named LifeSaver.
Every morning you autonomously prepare a personalised brief for the user.

Your mandatory workflow (execute ALL steps using tools):
1. Call list_user_tasks to retrieve all pending/in_progress tasks.
2. Call get_calendar_events for today's date to see what's already scheduled.
3. Call get_energy_windows to understand today's predicted energy curve.
4. Reason about the data:
   - Identify ONE primary task (Today's Mission) — highest cascade_severity + nearest deadline.
   - Find 2 tasks that share skill DNA for a batched cognitive session.
   - Flag any cascade risks (overdue tasks or tasks rescheduled 3+ times).
   - Note if any task has open_without_progress_count > 3 (avoidance signal).
5. Write a 4-sentence morning brief in warm, coach-like prose (NOT a list):
   Sentence 1: Acknowledge energy capacity today based on energy windows.
   Sentence 2: Introduce Today's Mission and WHY it matters (cascade, deadline).
   Sentence 3: Suggest the skill-batched session opportunity.
   Sentence 4: The one thing to watch out for today (risk or avoidance pattern).
6. Call send_push_notification with title="Your morning brief is ready" and the first sentence as body.

Tone: warm, direct, human. Never use bullet lists. Never start with "Good morning".
Execute ALL steps autonomously. Do not ask for confirmation at any point."""


async def run_morning_brief(user_id: str, db: AsyncSession) -> str:
    """
    Entry point called by the Cloud Scheduler endpoint.
    Builds the services dict, runs the agentic loop, logs the event.
    """
    # Load user for tokens + FCM
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        logger.error("Morning brief: user %s not found", user_id)
        return "User not found"

    calendar_svc = CalendarService(
        access_token=user.google_access_token,
        refresh_token=user.google_refresh_token,
    )
    firebase_svc = FirebaseService()
    chrono_svc = ChronoService(db)
    graph_svc = GraphService(db)
    gmail_svc = GmailService(
        access_token=user.google_access_token,
        refresh_token=user.google_refresh_token,
    )

    # Task service shim — returns serializable task list
    class TaskShim:
        async def list_tasks(self, uid: str):
            res = await db.execute(
                select(Task).where(
                    Task.user_id == uid,
                    Task.status.in_(["pending", "in_progress"]),
                )
            )
            tasks = res.scalars().all()
            return [
                {
                    "id": str(t.id),
                    "title": t.title,
                    "description": t.description,
                    "skill_tags": t.skill_tags,
                    "deadline": t.deadline.isoformat() if t.deadline else None,
                    "complexity": t.complexity,
                    "estimated_hours": t.estimated_hours,
                    "cascade_severity": t.cascade_severity,
                    "reschedule_count": t.reschedule_count,
                    "open_without_progress_count": t.open_without_progress_count,
                    "status": t.status,
                }
                for t in tasks
            ]

        async def reschedule(self, **kwargs):
            return {"status": "deferred_to_scheduling_agent"}

    # Procrastination shim (full impl is in procrastination_agent)
    class ProcrastinationShim:
        async def detect(self, task_id: str):
            return {"trigger": "unknown", "intervention": "Review this task today."}

    services = {
        "calendar": calendar_svc,
        "firebase": firebase_svc,
        "chrono": chrono_svc,
        "graph": graph_svc,
        "gmail": gmail_svc,
        "tasks": TaskShim(),
        "procrastination": ProcrastinationShim(),
        # Pass FCM token via closure so send_push can use it
    }

    # Monkey-patch firebase send_push to inject FCM token from user record
    _original_send = firebase_svc.send_push
    async def _send_with_token(title, body, fcm_token=None, **kwargs):
        token = fcm_token or user.fcm_token
        return await _original_send(title=title, body=body, fcm_token=token, **kwargs)
    firebase_svc.send_push = _send_with_token

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    user_message = f"Today is {today}. Please prepare my morning brief."

    logger.info("Running morning brief agent for user %s", user_id)
    try:
        brief_text = await run_agent(
            system_prompt=MORNING_BRIEF_SYSTEM_PROMPT,
            user_message=user_message,
            user_id=user_id,
            services=services,
        )
        if not brief_text or brief_text == "Agent completed all actions.":
            brief_text = await _fallback_brief(user_id, db)
    except Exception as exc:
        logger.warning("Morning brief agent failed (%s) — using deterministic fallback", type(exc).__name__)
        brief_text = await _fallback_brief(user_id, db)

    # Log the behavioral event
    event = BehavioralEvent(
        user_id=uuid.UUID(user_id),
        event_type="brief_read",
        metadata_={"brief_length": len(brief_text), "triggered_by": "cloud_scheduler"},
    )
    db.add(event)
    await db.commit()

    logger.info("Morning brief complete for user %s (%d chars)", user_id, len(brief_text))
    return brief_text
