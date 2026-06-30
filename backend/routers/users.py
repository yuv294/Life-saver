from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database import get_db
from auth import get_current_user
from models.user import User
from models.task import Task
from models.behavioral_event import BehavioralEvent
from schemas.user import UserResponse, UserUpdate, OAuthTokenUpdate, PlanningAccuracy, StreakStatus
from datetime import datetime, timezone, date
from typing import List
import uuid

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_me(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post("/me/oauth-tokens")
async def store_oauth_tokens(
    payload: OAuthTokenUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Store Google OAuth tokens after the OAuth flow completes on the frontend."""
    current_user.google_access_token = payload.access_token
    if payload.refresh_token:
        current_user.google_refresh_token = payload.refresh_token
    if payload.expiry:
        current_user.google_token_expiry = payload.expiry
    await db.commit()
    return {"status": "tokens stored"}


@router.get("/me/streak", response_model=StreakStatus)
async def get_streak(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    # Check if user completed any task today to update streak
    result = await db.execute(
        select(func.count()).where(
            BehavioralEvent.user_id == current_user.id,
            BehavioralEvent.event_type == "task_completed",
            func.date(BehavioralEvent.timestamp) == today,
        )
    )
    completed_today = result.scalar() or 0

    streak = current_user.streak_count
    if completed_today > 0:
        if current_user.last_active_date != today:
            streak += 1
            current_user.streak_count = streak
            current_user.last_active_date = today
            await db.commit()

    return StreakStatus(
        streak_count=streak,
        last_active_date=current_user.last_active_date,
        recovery_days_remaining=max(0, 4 - current_user.recovery_days_used),
        is_recovery_day_active=False,
    )


@router.post("/me/recovery-day")
async def declare_recovery_day(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    remaining = 4 - current_user.recovery_days_used
    if remaining <= 0:
        raise HTTPException(status_code=400, detail="No recovery days remaining this month")
    current_user.recovery_days_used += 1
    db.add(BehavioralEvent(
        user_id=current_user.id,
        event_type="recovery_day_declared",
        metadata_={"days_used": current_user.recovery_days_used},
    ))
    await db.commit()
    return {
        "status": "recovery day active",
        "streak_protected": True,
        "days_remaining": remaining - 1,
    }


@router.get("/me/planning-accuracy", response_model=List[PlanningAccuracy])
async def planning_accuracy(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Per-skill estimated vs actual time inflation factors."""
    result = await db.execute(
        select(Task).where(
            Task.user_id == current_user.id,
            Task.status == "completed",
            Task.estimated_hours.isnot(None),
            Task.actual_hours.isnot(None),
        )
    )
    completed = result.scalars().all()

    skill_stats: dict = {}
    for task in completed:
        for skill in (task.skill_tags or ["administrative"]):
            if skill not in skill_stats:
                skill_stats[skill] = {"est": 0.0, "actual": 0.0, "count": 0}
            skill_stats[skill]["est"] += task.estimated_hours
            skill_stats[skill]["actual"] += task.actual_hours
            skill_stats[skill]["count"] += 1

    return [
        PlanningAccuracy(
            skill=skill,
            estimated_hours=round(v["est"], 2),
            actual_hours=round(v["actual"], 2),
            inflation_factor=round(v["actual"] / max(v["est"], 0.01), 2),
            sample_count=v["count"],
        )
        for skill, v in skill_stats.items()
        if v["count"] >= 2
    ]


@router.get("/me/planning-summary")
async def planning_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Overall estimate-vs-actual inflation across all completed tasks (+ per-skill)."""
    result = await db.execute(
        select(Task).where(
            Task.user_id == current_user.id,
            Task.status == "completed",
            Task.estimated_hours.isnot(None),
            Task.actual_hours.isnot(None),
        )
    )
    completed = list(result.scalars().all())
    total_est = sum(t.estimated_hours for t in completed)
    total_act = sum(t.actual_hours for t in completed)

    per_skill: dict = {}
    for t in completed:
        for s in (t.skill_tags or ["administrative"]):
            d = per_skill.setdefault(s, {"est": 0.0, "act": 0.0, "n": 0})
            d["est"] += t.estimated_hours
            d["act"] += t.actual_hours
            d["n"] += 1

    return {
        "overall_inflation": round(total_act / total_est, 2) if total_est else None,
        "sample_count": len(completed),
        "per_skill": {
            s: {"inflation": round(v["act"] / max(v["est"], 0.01), 2), "count": v["n"]}
            for s, v in per_skill.items()
        },
    }
