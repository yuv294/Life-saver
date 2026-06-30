"""
Missed-task re-sequencing agent.

When a task's deadline has passed and it's still open, this generates a recovery
plan: which downstream tasks are now at risk and how to re-sequence the work.
Falls back to a deterministic plan when Gemini is unavailable.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.task import Task
from services.gemini_service import simple_generate
from services.graph_service import build_dependency_dag, get_cascade_severity
from datetime import datetime, timezone
import json
import logging

logger = logging.getLogger(__name__)


def _aware(dt: datetime) -> datetime:
    """Return dt as a UTC-aware datetime (DB datetimes may be naive)."""
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


RESEQUENCE_PROMPT = """A task is overdue. Produce a short, calm recovery plan.

Overdue task: "{title}" (was due {deadline}, ~{hours}h of work)
Days overdue: {days_over}
Downstream tasks it now puts at risk: {blocked}

Return ONLY this JSON:
{{
  "summary": "one calm sentence naming the situation and the stakes",
  "reorder": ["concrete step 1", "step 2", "step 3"],
  "deprioritize": "the one thing to drop or defer to make room",
  "message": "a warm push-notification body under 140 chars"
}}
No markdown fences."""


def _fallback(title: str, days_over: int, blocked_titles: list) -> dict:
    n = len(blocked_titles)
    blocks = f"blocks {n} downstream task{'s' if n != 1 else ''}" if n else "has no downstream tasks"
    return {
        "summary": f"“{title}” is {days_over} day{'s' if days_over != 1 else ''} overdue and {blocks}.",
        "reorder": [
            f"Spend 15 focused minutes on “{title}” now to break the stall",
            "Tell anyone waiting on it that it's moving",
            "Pull the nearest downstream task's deadline back by a few days" if n else "Re-set a realistic deadline",
        ],
        "deprioritize": (f"Defer “{blocked_titles[-1]}” — it's the least time-critical of the blocked set."
                         if n else "Drop one low-value task this week to create room."),
        "message": (f"“{title}” is overdue and {n} task{'s' if n != 1 else ''} wait on it — 15 min now gets you moving."
                    if n else f"“{title}” slipped past its deadline — a small step now resets momentum."),
    }


async def resequence_for_task(task: Task, all_tasks: list, db: AsyncSession) -> dict:
    G = build_dependency_dag(all_tasks)
    casc = get_cascade_severity(G, str(task.id))
    blocked_titles = casc.get("at_risk_titles", [])
    now = datetime.now(timezone.utc)
    deadline = task.deadline
    days_over = (now - _aware(deadline)).days if deadline else 0

    blocked_str = "; ".join(blocked_titles) if blocked_titles else "none"
    prompt = RESEQUENCE_PROMPT.format(
        title=task.title,
        deadline=deadline.strftime("%b %d") if deadline else "no date",
        hours=task.estimated_hours or 1,
        days_over=max(0, days_over),
        blocked=blocked_str,
    )
    raw = await simple_generate(prompt)
    raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    try:
        plan = json.loads(raw)
    except (json.JSONDecodeError, AttributeError):
        plan = _fallback(task.title, max(0, days_over), blocked_titles)

    return {
        "task_id": str(task.id),
        "task_title": task.title,
        "days_overdue": max(0, days_over),
        "at_risk_titles": blocked_titles,
        "critical_path_affected": casc.get("critical_path_affected", False),
        **plan,
    }


async def run_resequence(user_id: str, db: AsyncSession, limit: int = 3) -> list:
    """Find overdue open tasks and return a recovery plan for the most impactful ones."""
    # Load ALL active tasks so the cascade graph sees no-deadline dependents too.
    result = await db.execute(
        select(Task).where(
            Task.user_id == user_id,
            Task.status.in_(["pending", "in_progress"]),
        )
    )
    all_tasks = list(result.scalars().all())
    now = datetime.now(timezone.utc)

    overdue = [t for t in all_tasks if t.deadline and _aware(t.deadline) < now]
    overdue.sort(key=lambda t: (-(t.cascade_severity or 0), _aware(t.deadline)))

    plans = []
    for task in overdue[:limit]:
        plans.append(await resequence_for_task(task, all_tasks, db))
    return plans
