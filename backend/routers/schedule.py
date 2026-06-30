"""
Schedule optimizer endpoint — runs OR-Tools CSP solver over the user's tasks.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from auth import get_current_user
from models.user import User
from models.task import Task
from services.chrono_service import ChronoService
from services.calendar_service import CalendarService
from services.scheduler_service import solve_schedule
from datetime import datetime, timezone, timedelta

router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.get("/optimize")
async def optimize_schedule(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Run the OR-Tools CSP solver to produce an optimal task schedule.
    Returns list of task→timeslot assignments.
    """
    result = await db.execute(
        select(Task).where(
            Task.user_id == current_user.id,
            Task.status.in_(["pending", "in_progress"]),
        )
    )
    tasks = result.scalars().all()
    if not tasks:
        return {"assignments": [], "message": "No pending tasks to schedule"}

    chrono = ChronoService(db)
    energy_windows = await chrono.get_energy_windows(str(current_user.id))

    calendar_svc = CalendarService(current_user.google_access_token, current_user.google_refresh_token)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    end = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")
    calendar_events = await calendar_svc.get_events(today, end)

    task_dicts = [
        {
            "id": str(t.id),
            "title": t.title,
            "estimated_hours": t.estimated_hours or 1.0,
            "deadline": t.deadline.isoformat() if t.deadline else None,
            "skill_tags": t.skill_tags or [],
            "depends_on": t.depends_on or [],
            "cascade_severity": t.cascade_severity,
        }
        for t in tasks
    ]

    assignments = solve_schedule(task_dicts, energy_windows, calendar_events)
    return {"assignments": assignments, "task_count": len(tasks)}


@router.get("/energy-windows")
async def get_energy_windows(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    chrono = ChronoService(db)
    windows = await chrono.get_energy_windows(str(current_user.id))
    return {"windows": windows[:48], "hours_shown": 24}  # first 24h (48 × 30-min slots)


@router.get("/best-slot/{skill}")
async def best_slot_for_skill(
    skill: str,
    duration_hours: float = 1.0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    chrono = ChronoService(db)
    slot = await chrono.best_slot_for_skill(str(current_user.id), skill, duration_hours)
    return slot
