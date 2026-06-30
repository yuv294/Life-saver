"""
Agent trigger endpoints — called by Cloud Scheduler (and directly in dev/demo).
Protected by internal secret header.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from auth import require_internal, get_current_user
from models.user import User
from agents.morning_brief_agent import run_morning_brief
from agents.scheduling_agent import run_scheduling_agent
from agents.procrastination_agent import run_procrastination_check
from agents.backlog_audit_agent import run_backlog_audit
from pydantic import BaseModel
from typing import List, Optional
import logging
import uuid

router = APIRouter(prefix="/agents", tags=["agents"])
logger = logging.getLogger(__name__)


class ScheduleRequest(BaseModel):
    task_ids: List[str]


class UserAgentRequest(BaseModel):
    user_id: str


# ── Cloud Scheduler endpoints (internal secret required) ──────────────────────

@router.post("/morning-brief/{user_id}")
async def trigger_morning_brief(
    user_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_internal),
):
    """Cloud Scheduler calls this daily at 6am for each active user."""
    background_tasks.add_task(run_morning_brief, user_id, db)
    return {"status": "morning brief queued", "user_id": user_id}


@router.post("/backlog-audit/{user_id}")
async def trigger_backlog_audit(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_internal),
):
    """Cloud Scheduler calls this every Sunday at 9am."""
    result = await run_backlog_audit(user_id, db)
    return result


@router.post("/update-models/{user_id}")
async def trigger_model_update(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_internal),
):
    """Cloud Scheduler calls this nightly at 11pm — refreshes procrastination patterns."""
    diagnoses = await run_procrastination_check(user_id, db)
    return {"user_id": user_id, "diagnoses": diagnoses}


# ── User-triggered endpoints (Firebase auth required) ─────────────────────────

@router.post("/me/morning-brief")
async def my_morning_brief(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run the morning-brief agent now and return the narrative (for the dashboard card)."""
    brief = await run_morning_brief(str(current_user.id), db)
    return {"brief": brief}


@router.post("/me/schedule")
async def schedule_tasks(
    payload: ScheduleRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger Gemini scheduling agent for specific tasks."""
    background_tasks.add_task(
        run_scheduling_agent, str(current_user.id), payload.task_ids, db
    )
    return {"status": "scheduling agent queued", "task_count": len(payload.task_ids)}


@router.post("/me/procrastination-check")
async def procrastination_check(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    diagnoses = await run_procrastination_check(str(current_user.id), db)
    return {"diagnoses": diagnoses}


@router.post("/me/tasks/{task_id}/procrastination")
async def procrastination_for_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Analyze why a SPECIFIC task is being avoided ('Why am I avoiding this?')."""
    from sqlalchemy import select
    from models.task import Task
    from agents.procrastination_agent import ProcrastinationService

    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    diagnosis = await ProcrastinationService(db).detect(str(task.id))
    return {"task_id": str(task.id), "task_title": task.title, **diagnosis}


@router.post("/me/backlog-audit")
async def backlog_audit(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await run_backlog_audit(str(current_user.id), db)
    return result


@router.post("/me/resequence")
async def resequence(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Recovery plans for overdue tasks (re-sequencing + at-risk downstream)."""
    from agents.resequence_agent import run_resequence
    plans = await run_resequence(str(current_user.id), db)
    return {"plans": plans, "overdue_count": len(plans)}


@router.post("/me/gmail-scan")
async def gmail_scan(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Scan Gmail inbox for commitments and return candidate tasks."""
    from services.gmail_service import GmailService
    svc = GmailService(current_user.google_access_token, current_user.google_refresh_token)
    candidates = await svc.scan_commitments(lookback_days=3)
    return {"candidates": candidates, "count": len(candidates)}
