"""
Tasks router — CRUD + skill tagging + rescheduling + context saves + cluster view.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from database import get_db
from auth import get_current_user
from models.user import User
from models.task import Task
from models.context_save import ContextSave
from models.behavioral_event import BehavioralEvent
from models.skill_cluster import SkillCluster
from schemas.task import (
    TaskCreate, TaskUpdate, TaskReschedule, TaskResponse, RescheduleOptions, RescheduleWindow,
    ContextSaveCreate, TaskComplete,
)
from services.gemini_service import classify_skills, compress_context
from services.graph_service import GraphService, detect_skill_clusters
from services.calendar_service import CalendarService
from services.chrono_service import ChronoService
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import uuid
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Auto-tag skills via Gemini
    skill_data = await classify_skills(
        task_title=payload.title,
        task_description=payload.description or "",
    )

    task = Task(
        user_id=current_user.id,
        title=payload.title,
        description=payload.description,
        skill_tags=skill_data.get("skill_tags", []),
        complexity=skill_data.get("complexity", payload.complexity),
        estimated_hours=payload.estimated_hours,
        deadline=payload.deadline,
        depends_on=[str(d) for d in payload.depends_on],
        importance=skill_data.get("importance", payload.importance),
        urgency=skill_data.get("urgency", payload.urgency),
        eisenhower_quadrant=skill_data.get("eisenhower_quadrant"),
    )
    db.add(task)
    await db.flush()  # get the ID

    # Recalculate cascade severity + clusters for all tasks
    all_tasks_result = await db.execute(
        select(Task).where(Task.user_id == current_user.id, Task.status.in_(["pending", "in_progress"]))
    )
    all_tasks = list(all_tasks_result.scalars().all())
    await _recompute_cascades(all_tasks, db)
    await _recompute_clusters(current_user.id, all_tasks, db)

    # Log behavioral event
    db.add(BehavioralEvent(
        user_id=current_user.id,
        task_id=task.id,
        event_type="task_started",
        metadata_={"auto_tagged_skills": skill_data.get("skill_tags", [])},
    ))

    await db.commit()
    await db.refresh(task)
    return task


@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Task).where(Task.user_id == current_user.id)
    if status_filter:
        q = q.where(Task.status == status_filter)
    q = q.order_by(Task.deadline.asc().nulls_last(), Task.cascade_severity.desc())
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/clusters")
async def get_clusters(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Task).where(
            Task.user_id == current_user.id,
            Task.status.in_(["pending", "in_progress"]),
        )
    )
    tasks = result.scalars().all()
    clusters = detect_skill_clusters(tasks)
    return {"clusters": clusters, "total_tasks": len(tasks)}


@router.get("/next-session")
async def next_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the highest-priority skill cluster for starting work right now."""
    result = await db.execute(
        select(Task).where(
            Task.user_id == current_user.id,
            Task.status.in_(["pending", "in_progress"]),
        )
    )
    tasks = result.scalars().all()
    if not tasks:
        return {"cluster": None, "message": "No pending tasks"}
    clusters = detect_skill_clusters(tasks)
    if not clusters:
        return {"cluster": None}
    # Sort by cascade_severity of contained tasks (proxy for priority)
    task_map = {str(t.id): t for t in tasks}
    for cluster in clusters:
        cluster["max_cascade"] = max(
            (task_map[tid].cascade_severity for tid in cluster["task_ids"] if tid in task_map),
            default=0,
        )
    best = max(clusters, key=lambda c: (c["max_cascade"], c["estimated_total_hours"]))
    return {"cluster": best}


@router.get("/{task_id}/cascade")
async def task_cascade(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Which downstream tasks this one blocks + whether it's on the critical path."""
    await _get_task_or_404(task_id, current_user.id, db)
    result = await GraphService(db).cascade_analysis(str(task_id), str(current_user.id))
    return result


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task_or_404(task_id, current_user.id, db)
    # Track open-without-progress if not updated recently
    db.add(BehavioralEvent(
        user_id=current_user.id,
        task_id=task.id,
        event_type="task_opened_no_progress",
    ))
    await db.execute(
        update(Task).where(Task.id == task_id).values(
            last_opened_at=datetime.now(timezone.utc),
            open_without_progress_count=Task.open_without_progress_count + 1,
        )
    )
    await db.commit()
    await db.refresh(task)
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: uuid.UUID,
    payload: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task_or_404(task_id, current_user.id, db)
    updates = payload.model_dump(exclude_unset=True)
    updates.pop("fcm_token", None)  # belongs on the user, not the task

    deps_changed = "depends_on" in updates

    if "status" in updates and updates["status"] == "completed":
        updates["actual_hours"] = updates.get("actual_hours", task.estimated_hours)
        db.add(BehavioralEvent(
            user_id=current_user.id,
            task_id=task.id,
            event_type="task_completed",
            metadata_={"actual_hours": updates.get("actual_hours")},
        ))
        # Reset open-without-progress on completion
        updates["open_without_progress_count"] = 0

    if updates:
        await db.execute(update(Task).where(Task.id == task_id).values(**updates))

    # If dependencies changed, recompute cascade severity across the graph
    if deps_changed:
        all_tasks = list((await db.execute(
            select(Task).where(
                Task.user_id == current_user.id,
                Task.status.in_(["pending", "in_progress"]),
            )
        )).scalars().all())
        await _recompute_cascades(all_tasks, db)

    await db.commit()
    await db.refresh(task)
    return task


@router.post("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: uuid.UUID,
    payload: Optional[TaskComplete] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a task complete, record actual_hours, and log the completion event."""
    task = await _get_task_or_404(task_id, current_user.id, db)
    actual = (payload.actual_hours if payload and payload.actual_hours is not None
              else task.estimated_hours)
    await db.execute(
        update(Task).where(Task.id == task_id).values(
            status="completed",
            actual_hours=actual,
            open_without_progress_count=0,
        )
    )
    db.add(BehavioralEvent(
        user_id=current_user.id,
        task_id=task.id,
        event_type="task_completed",
        metadata_={"actual_hours": actual, "estimated_hours": task.estimated_hours},
    ))
    await db.commit()
    await db.refresh(task)
    return task


_NO_OPTION_ALTERNATIVES = [
    "Start now — even 15 minutes of progress breaks the pattern",
    "Negotiate the deadline — draft an email to stakeholders",
    "Delegate — identify who else could own this",
    "Accept late delivery — acknowledge the consequence and move forward",
]


@router.get("/{task_id}/reschedule-options", response_model=RescheduleOptions)
async def reschedule_options(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Preview up to 3 viable windows (no mutation). Powers the reschedule modal."""
    task = await _get_task_or_404(task_id, current_user.id, db)

    chrono = ChronoService(db)
    energy_windows = await chrono.get_energy_windows(str(current_user.id))
    calendar_svc = CalendarService(current_user.google_access_token, current_user.google_refresh_token)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    end_date = (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%d")
    calendar_events = await calendar_svc.get_events(today, end_date)

    # other already-scheduled tasks (for displaced count)
    others = (await db.execute(
        select(Task).where(
            Task.user_id == current_user.id,
            Task.id != task_id,
            Task.scheduled_for.isnot(None),
        )
    )).scalars().all()
    scheduled_starts = [t.scheduled_for for t in others if t.scheduled_for]

    windows = _best_reschedule_windows(energy_windows, calendar_events, task, scheduled_starts)
    no_options = len(windows) == 0
    return RescheduleOptions(
        task_id=task_id,
        reschedule_count=task.reschedule_count,
        windows=windows,
        no_options=no_options,
        no_options_alternatives=_NO_OPTION_ALTERNATIVES if no_options else [],
        requires_reason=task.reschedule_count >= 2,
    )


@router.patch("/{task_id}/reschedule", response_model=RescheduleOptions)
async def reschedule_task(
    task_id: uuid.UUID,
    payload: TaskReschedule,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Commit a reschedule to the exact chosen window (with friction after 2 moves)."""
    task = await _get_task_or_404(task_id, current_user.id, db)

    requires_reason = task.reschedule_count >= 2
    if requires_reason and not payload.reason:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"reason is required after {task.reschedule_count} reschedules",
        )

    new_start = payload.new_datetime
    if new_start.tzinfo is None:
        new_start = new_start.replace(tzinfo=timezone.utc)

    new_count = task.reschedule_count + 1
    updates: dict = {"scheduled_for": new_start, "reschedule_count": new_count}

    # Mirror to Google Calendar if connected (no-op without a token)
    calendar_svc = CalendarService(current_user.google_access_token, current_user.google_refresh_token)
    if task.calendar_event_id:
        await calendar_svc.delete_event(task.calendar_event_id)
    end_dt = new_start + timedelta(hours=task.estimated_hours or 1.0)
    event = await calendar_svc.create_event(
        title=f"{task.title} — Work Session",
        start_time=new_start.isoformat(),
        end_time=end_dt.isoformat(),
        description=task.description or "",
    )
    if isinstance(event, dict) and event.get("id"):
        updates["calendar_event_id"] = event["id"]

    await db.execute(update(Task).where(Task.id == task_id).values(**updates))
    db.add(BehavioralEvent(
        user_id=current_user.id,
        task_id=task.id,
        event_type="reschedule_requested",
        metadata_={"reason": payload.reason, "new_time": new_start.isoformat(),
                   "auto_flagged": new_count >= 3},
    ))
    await db.commit()

    applied = RescheduleWindow(
        start=new_start,
        end=end_dt,
        energy_score=0.0,
        tasks_displaced=0,
        cascade_impact=task.cascade_severity,
        label="scheduled",
    )
    return RescheduleOptions(
        task_id=task_id,
        reschedule_count=new_count,
        windows=[applied],
        no_options=False,
        no_options_alternatives=[],
        requires_reason=new_count >= 2,
    )


@router.post("/{task_id}/context-save")
async def save_context(
    task_id: uuid.UUID,
    payload: ContextSaveCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _get_task_or_404(task_id, current_user.id, db)
    breadcrumb = await compress_context(payload.raw_brain_dump, task.title)
    ctx = ContextSave(
        task_id=task.id,
        breadcrumb=breadcrumb,
        raw_brain_dump=payload.raw_brain_dump,
    )
    db.add(ctx)
    db.add(BehavioralEvent(
        user_id=current_user.id,
        task_id=task.id,
        event_type="context_saved",
    ))
    await db.commit()
    return {"breadcrumb": breadcrumb, "task_id": str(task_id)}


@router.get("/{task_id}/context-save")
async def get_latest_context(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_task_or_404(task_id, current_user.id, db)
    result = await db.execute(
        select(ContextSave)
        .where(ContextSave.task_id == task_id)
        .order_by(ContextSave.created_at.desc())
        .limit(1)
    )
    ctx = result.scalar_one_or_none()
    if not ctx:
        return {"breadcrumb": None}
    return {"breadcrumb": ctx.breadcrumb, "saved_at": ctx.created_at.isoformat()}


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _get_task_or_404(task_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> Task:
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.user_id == user_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def _best_reschedule_windows(
    energy_windows: list,
    calendar_events: list,
    task: Task,
    scheduled_starts: Optional[list] = None,
    limit: int = 3,
) -> List[RescheduleWindow]:
    """
    Pick up to `limit` high-energy, free, future windows spread across the next 48h.
    Skips the next hour (buffer) and low/night energy slots.
    """
    from services.scheduler_service import _filter_free_windows

    scheduled_starts = scheduled_starts or []
    now = datetime.now(timezone.utc)
    free = _filter_free_windows(energy_windows, calendar_events)

    candidates = []
    for w in free:
        ws = datetime.fromisoformat(w["start"])
        if ws < now + timedelta(hours=1):
            continue
        if w["energy_score"] < 0.45:  # skip low/night energy
            continue
        candidates.append((ws, w))

    # highest energy first, then soonest
    candidates.sort(key=lambda c: (-c[1]["energy_score"], c[0]))

    chosen: list = []
    for ws, w in candidates:
        if all(abs((ws - c[0]).total_seconds()) >= 3 * 3600 for c in chosen):
            chosen.append((ws, w))
        if len(chosen) >= limit:
            break

    windows = []
    for ws, w in chosen:
        we = datetime.fromisoformat(w["end"])
        displaced = sum(
            1 for s in scheduled_starts
            if s and ws <= s.astimezone(timezone.utc) < we
        )
        windows.append(
            RescheduleWindow(
                start=ws,
                end=we,
                energy_score=w["energy_score"],
                tasks_displaced=displaced,
                cascade_impact=task.cascade_severity,
                label=w.get("label", "available"),
            )
        )

    # display soonest-first
    return sorted(windows, key=lambda w: w.start)


async def _recompute_cascades(tasks: list, db: AsyncSession):
    """Set each task's cascade_severity = number of downstream dependents."""
    import networkx as nx
    from services.graph_service import build_dependency_dag

    G = build_dependency_dag(tasks)
    for t in tasks:
        node = str(t.id)
        sev = len(nx.descendants(G, node)) if node in G else 0
        if t.cascade_severity != sev:
            t.cascade_severity = sev
            await db.execute(
                update(Task).where(Task.id == t.id).values(cascade_severity=sev)
            )


async def _recompute_clusters(user_id: uuid.UUID, tasks: list, db: AsyncSession):
    clusters = detect_skill_clusters(tasks)
    # Delete old clusters and re-insert
    await db.execute(delete(SkillCluster).where(SkillCluster.user_id == user_id))
    for c in clusters:
        db.add(SkillCluster(
            user_id=user_id,
            name=c["name"],
            dominant_skill=c["dominant_skill"],
            skill_tags=c["skill_tags"],
            task_ids=c["task_ids"],
            estimated_total_hours=c["estimated_total_hours"],
        ))
