"""
Task tool wrappers for Gemini function calling.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from models.task import Task
from typing import List, Dict, Any
import uuid


async def list_tasks(user_id: str, db: AsyncSession) -> List[Dict[str, Any]]:
    result = await db.execute(
        select(Task).where(
            Task.user_id == uuid.UUID(user_id),
            Task.status.in_(["pending", "in_progress"]),
        )
    )
    tasks = result.scalars().all()
    return [
        {
            "id": str(t.id),
            "title": t.title,
            "skill_tags": t.skill_tags,
            "deadline": t.deadline.isoformat() if t.deadline else None,
            "estimated_hours": t.estimated_hours,
            "cascade_severity": t.cascade_severity,
            "reschedule_count": t.reschedule_count,
            "open_without_progress_count": t.open_without_progress_count,
            "status": t.status,
            "procrastination_trigger": t.procrastination_trigger,
        }
        for t in tasks
    ]


async def reschedule_task(
    task_id: str,
    new_datetime: str,
    db: AsyncSession,
    user_id: str,
    reason: str = "",
) -> Dict[str, Any]:
    await db.execute(
        update(Task)
        .where(Task.id == uuid.UUID(task_id), Task.user_id == uuid.UUID(user_id))
        .values(
            scheduled_for=new_datetime,
            reschedule_count=Task.reschedule_count + 1,
        )
    )
    await db.commit()
    return {"task_id": task_id, "rescheduled_to": new_datetime, "reason": reason}
