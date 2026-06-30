"""
Backlog Audit Agent — surfaces Anti-List candidates every Sunday at 9am.
"""

from services.gemini_service import simple_generate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.task import Task
from models.user import User
from services.firebase_service import FirebaseService
from datetime import datetime, timezone, timedelta
import json
import logging
import uuid

logger = logging.getLogger(__name__)

BACKLOG_AUDIT_PROMPT = """You are auditing a task backlog for tasks that no longer belong there.

Today: {today}
Tasks:
{task_list}

Identify 3-5 tasks to remove. A task qualifies if ANY:
- Not touched in 30+ days
- Rescheduled 5+ times
- cascade_severity=0 AND importance=low
- procrastination_trigger=resentment
- Created 60+ days ago, still pending

For each, recommend: abandon | delegate | defer_indefinitely

Return ONLY this JSON:
{{
  "candidates": [
    {{
      "task_id": "...",
      "task_title": "...",
      "recommendation": "abandon",
      "reason": "One sentence."
    }}
  ],
  "total_backlog_tasks": {total_count},
  "health_score": 75
}}"""


def _heuristic_candidates(candidates_pre: list, today: datetime, total: int) -> dict:
    """Deterministic Anti-List used when Gemini is unavailable (mode A) or returns nothing."""
    out = []
    for t in candidates_pre[:5]:
        age = (today - t.created_at.replace(tzinfo=timezone.utc)).days
        if t.reschedule_count >= 5:
            rec, reason = "defer_indefinitely", f"Rescheduled {t.reschedule_count}× — it keeps getting pushed; park it until it truly matters."
        elif (t.importance == "low" and (t.cascade_severity or 0) == 0) or age >= 60:
            rec, reason = "abandon", f"{age}d old, low importance, nothing depends on it — safe to let go."
        elif t.procrastination_trigger == "resentment":
            rec, reason = "delegate", "You resent this one — hand it off if you can."
        else:
            rec, reason = "delegate", "Stale and low-leverage — someone else may be better placed."
        out.append({"task_id": str(t.id), "task_title": t.title, "recommendation": rec, "reason": reason})
    health = max(40, round(100 * (1 - len(candidates_pre) / max(total, 1))))
    return {"candidates": out, "total_backlog_tasks": total, "health_score": health}


async def run_backlog_audit(user_id: str, db: AsyncSession) -> dict:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return {"error": "user not found"}

    tasks_result = await db.execute(
        select(Task).where(
            Task.user_id == uuid.UUID(user_id),
            Task.status.in_(["pending", "in_progress"]),
        )
    )
    tasks = tasks_result.scalars().all()
    if not tasks:
        return {"candidates": [], "total_backlog_tasks": 0, "health_score": 100}

    today = datetime.now(timezone.utc)
    candidates_pre = [
        t for t in tasks
        if (
            (t.last_opened_at and (today - t.last_opened_at.replace(tzinfo=timezone.utc)).days >= 30)
            or t.reschedule_count >= 5
            or t.procrastination_trigger == "resentment"
            or (today - t.created_at.replace(tzinfo=timezone.utc)).days >= 60
        )
    ]

    if not candidates_pre:
        if user.fcm_token:
            await FirebaseService().send_push(
                title="Backlog looks healthy!",
                body="No stale tasks found this week.",
                fcm_token=user.fcm_token,
                deep_link="/journey",
            )
        return {"candidates": [], "total_backlog_tasks": len(tasks), "health_score": 95}

    task_list = "\n".join(
        f"- id={t.id} | {t.title} | {(today - t.created_at.replace(tzinfo=timezone.utc)).days}d old "
        f"| rescheduled {t.reschedule_count}x | cascade={t.cascade_severity} "
        f"| importance={t.importance} | trigger={t.procrastination_trigger or 'none'}"
        for t in candidates_pre[:15]
    )

    prompt = BACKLOG_AUDIT_PROMPT.format(
        today=today.strftime("%Y-%m-%d"),
        task_list=task_list,
        total_count=len(tasks),
    )

    text = await simple_generate(prompt)
    text = (text or "").strip().lstrip("```json").lstrip("```").rstrip("```").strip()

    try:
        audit_result = json.loads(text)
    except json.JSONDecodeError:
        audit_result = {}

    # Fall back to the deterministic Anti-List if Gemini gave nothing usable.
    if not audit_result.get("candidates"):
        audit_result = _heuristic_candidates(candidates_pre, today, len(tasks))

    candidate_count = len(audit_result.get("candidates", []))
    if candidate_count > 0 and user.fcm_token:
        await FirebaseService().send_push(
            title=f"{candidate_count} tasks might be holding you back",
            body="Review in 2 minutes? Your backlog could be lighter.",
            fcm_token=user.fcm_token,
            deep_link="/tasks?filter=anti-list",
            data={"type": "backlog_audit"},
        )

    return audit_result
