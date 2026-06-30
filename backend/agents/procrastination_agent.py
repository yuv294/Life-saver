"""
Procrastination Fingerprinter — classifies avoidance trigger and generates intervention.
"""

from services.gemini_service import simple_generate
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from models.task import Task
from datetime import datetime, timezone
import json
import logging
import uuid

logger = logging.getLogger(__name__)

PROCRASTINATION_PROMPT = """Analyze why this task is being avoided.

Task: {title}
Description: {description}
Skill tags: {skill_tags}
Complexity: {complexity}
Times deferred: {reschedule_count}
Days since created: {days_old}
Opened without progress: {open_without_progress_count} times
Similar tasks completed: {similar_completion_rate}%
Importance: {importance} | Urgency: {urgency}

Classify ONE trigger: ambiguity | fear | overwhelm | boredom | resentment

Return ONLY this JSON:
{{
  "trigger": "ambiguity",
  "trigger_explanation": "One sentence.",
  "intervention": "One specific action to break the avoidance loop.",
  "first_step": "Smallest possible action under 5 minutes.",
  "estimated_start_minutes": 5,
  "anti_list_candidate": false
}}"""

TRIGGER_STRATEGIES = {
    "ambiguity": "Define what 'done' looks like in one sentence.",
    "fear": "Reframe as exploration — the goal is learning, not perfection.",
    "overwhelm": "Find the minimum viable version. What 10% gives 80% of the value?",
    "boredom": "Time-box to 25 minutes, pair with something enjoyable after.",
    "resentment": "Question whether this task still belongs on your list.",
}


class ProcrastinationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def detect(self, task_id: str) -> dict:
        result = await self.db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            return {"error": "task not found"}

        days_old = (datetime.now(timezone.utc) - task.created_at.replace(tzinfo=timezone.utc)).days
        primary_skill = (task.skill_tags or ["administrative"])[0]

        completed_result = await self.db.execute(
            select(func.count()).where(
                Task.user_id == task.user_id,
                Task.status == "completed",
                Task.skill_tags.contains([primary_skill]),
            )
        )
        total_result = await self.db.execute(
            select(func.count()).where(
                Task.user_id == task.user_id,
                Task.skill_tags.contains([primary_skill]),
            )
        )
        similar_rate = int(
            ((completed_result.scalar() or 0) / max(total_result.scalar() or 1, 1)) * 100
        )

        prompt = PROCRASTINATION_PROMPT.format(
            title=task.title,
            description=task.description or "No description",
            skill_tags=", ".join(task.skill_tags or []),
            complexity=task.complexity,
            reschedule_count=task.reschedule_count,
            days_old=days_old,
            open_without_progress_count=task.open_without_progress_count,
            similar_completion_rate=similar_rate,
            importance=task.importance,
            urgency=task.urgency,
        )

        text = await simple_generate(prompt)
        text = text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Procrastination parse failed for task %s", task_id)
            data = {
                "trigger": "ambiguity",
                "trigger_explanation": "Unable to classify — defaulting to ambiguity.",
                "intervention": TRIGGER_STRATEGIES["ambiguity"],
                "first_step": "Write one sentence describing what done looks like.",
                "estimated_start_minutes": 5,
                "anti_list_candidate": False,
            }

        await self.db.execute(
            update(Task).where(Task.id == task.id).values(
                procrastination_trigger=data.get("trigger")
            )
        )
        await self.db.commit()
        return data


async def run_procrastination_check(user_id: str, db: AsyncSession) -> list:
    result = await db.execute(
        select(Task).where(
            Task.user_id == user_id,
            Task.status.in_(["pending", "in_progress"]),
            Task.reschedule_count >= 2,
        ).order_by(Task.open_without_progress_count.desc()).limit(3)
    )
    tasks = result.scalars().all()
    service = ProcrastinationService(db)
    diagnoses = []
    for task in tasks:
        diagnosis = await service.detect(str(task.id))
        diagnoses.append({"task_id": str(task.id), "task_title": task.title, **diagnosis})
    return diagnoses
