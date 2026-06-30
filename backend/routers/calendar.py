from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from auth import get_current_user
from models.user import User
from services.calendar_service import CalendarService
from datetime import datetime, timezone, timedelta

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("/events")
async def get_events(
    start_date: str = Query(..., description="YYYY-MM-DD"),
    end_date: str = Query(..., description="YYYY-MM-DD"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = CalendarService(current_user.google_access_token, current_user.google_refresh_token)
    events = await svc.get_events(start_date, end_date)
    return {"events": events, "count": len(events)}


@router.get("/free-slots")
async def find_free_slots(
    duration_hours: float = Query(1.0, description="Required block duration in hours"),
    days_ahead: int = Query(7, description="How many days forward to look"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = CalendarService(current_user.google_access_token, current_user.google_refresh_token)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    end = (datetime.now(timezone.utc) + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    slots = await svc.find_free_slots(today, end, duration_hours)
    return {"free_slots": slots}


@router.get("/vacation-finder")
async def find_vacation_windows(
    min_days: int = Query(2),
    max_days: int = Query(7),
    horizon_days: int = Query(90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Find low-pressure break windows over the next `horizon_days` by scanning a
    CONTINUOUS daily pressure map (free days included), grouping consecutive
    low-pressure days, and scoring each window's blast radius.
    """
    from sqlalchemy import select
    from models.task import Task

    result = await db.execute(
        select(Task).where(
            Task.user_id == current_user.id,
            Task.status.in_(["pending", "in_progress"]),
            Task.deadline.isnot(None),
        )
    )
    tasks = list(result.scalars().all())

    today = datetime.now(timezone.utc).date()

    if len(tasks) < 2:
        return {
            "windows": [],
            "total_found": 0,
            "message": "Add deadlines to a few tasks and I'll find your breathing room.",
        }

    # Continuous daily pressure map (0 for free days). Weight = cascade impact + 1.
    pressure = {today + timedelta(days=i): 0 for i in range(horizon_days)}
    deadline_days: dict = {}
    for t in tasks:
        dl = t.deadline.date() if t.deadline else None
        if dl is None or dl < today or (dl - today).days >= horizon_days:
            continue
        pressure[dl] = pressure.get(dl, 0) + (t.cascade_severity + 1)
        deadline_days.setdefault(dl, []).append(t)

    peak = max(pressure.values(), default=1) or 1
    threshold = max(1, peak * 0.25)

    days = sorted(pressure.keys())
    low = [d for d in days if pressure[d] < threshold]

    # Group consecutive low-pressure days into windows
    runs = []
    if low:
        start = prev = low[0]
        for d in low[1:]:
            if (d - prev).days > 1:
                runs.append((start, prev))
                start = d
            prev = d
        runs.append((start, prev))

    windows = []
    for start, end in runs:
        duration = (end - start).days + 1
        if duration < min_days:
            continue
        clipped_end = min(end, start + timedelta(days=max_days - 1))
        dur = (clipped_end - start).days + 1
        # blast radius: deadline load in the 7 days AFTER the break (prep you'd lose)
        look = [start + timedelta(days=dur + i) for i in range(7)]
        at_risk = [t.title for d in look for t in deadline_days.get(d, [])]
        blast = sum(pressure.get(d, 0) for d in look)
        windows.append({
            "start": start.isoformat(),
            "end": clipped_end.isoformat(),
            "duration_days": dur,
            "blast_radius": blast,
            "tasks_at_risk": at_risk[:5],
            "recommendation": (
                "Clear runway — a great time to step away." if blast == 0
                else "Doable, but you'll have deadlines waiting right after."
            ),
        })

    windows.sort(key=lambda w: (w["blast_radius"], w["start"]))
    return {"windows": windows[:5], "total_found": len(windows)}
