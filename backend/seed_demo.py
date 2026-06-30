"""
Demo seed — populates the local dev user with a coherent scenario so every feature
visibly works (skill clusters, cascade map, overdue recovery, backlog audit,
planning accuracy, skill levels, constellation, chronotype, streak).

Run from backend/:  venv\\Scripts\\python seed_demo.py
Safe to re-run — it wipes and rebuilds the dev user's tasks/events each time.
"""

import asyncio
import uuid
from datetime import datetime, timezone, timedelta, date

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from config import settings
import models  # noqa: F401  (register all models)
from models.user import User
from models.task import Task
from models.behavioral_event import BehavioralEvent
from models.context_save import ContextSave
from models.skill_cluster import SkillCluster
from routers.tasks import _recompute_cascades, _recompute_clusters

NOW = datetime.now(timezone.utc)
DEV_GOOGLE_ID = "dev-local-user"


def days(n: int) -> datetime:
    return NOW + timedelta(days=n)


def quad(importance: str, urgency: str) -> int:
    hi_imp, hi_urg = importance == "high", urgency == "high"
    if hi_imp and hi_urg:
        return 1
    if hi_imp and not hi_urg:
        return 2
    if not hi_imp and hi_urg:
        return 3
    return 4


def mk(title, skills, est, *, status="pending", actual=None, deadline=None,
       depends_on=None, importance="medium", urgency="medium",
       reschedule_count=0, open_no_progress=0, created_days_ago=2,
       last_opened_days_ago=None, description=None):
    t = Task(
        id=uuid.uuid4(),
        title=title,
        description=description,
        skill_tags=skills,
        complexity="high" if est >= 3 else "medium" if est >= 1 else "low",
        estimated_hours=est,
        actual_hours=actual,
        deadline=deadline,
        status=status,
        depends_on=[str(d) for d in (depends_on or [])],
        importance=importance,
        urgency=urgency,
        eisenhower_quadrant=quad(importance, urgency),
        reschedule_count=reschedule_count,
        open_without_progress_count=open_no_progress,
        created_at=NOW - timedelta(days=created_days_ago),
        last_opened_at=(NOW - timedelta(days=last_opened_days_ago)) if last_opened_days_ago is not None else None,
    )
    return t


async def main():
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as db:
        # ── dev user ───────────────────────────────────────────────────────────
        user = (await db.execute(select(User).where(User.google_id == DEV_GOOGLE_ID))).scalar_one_or_none()
        if not user:
            user = User(google_id=DEV_GOOGLE_ID, email="dev@lifesaver.local", display_name="Dev User")
            db.add(user)
            await db.flush()
        user.streak_count = 6
        user.last_active_date = date.today()
        user.recovery_days_used = 1

        # ── wipe previous demo/test data for this user ──────────────────────────
        await db.execute(delete(BehavioralEvent).where(BehavioralEvent.user_id == user.id))
        await db.execute(delete(SkillCluster).where(SkillCluster.user_id == user.id))
        await db.execute(delete(Task).where(Task.user_id == user.id))  # cascades context_saves
        await db.flush()

        tasks: list[Task] = []
        events: list[BehavioralEvent] = []

        def add(t: Task) -> Task:
            t.user_id = user.id
            tasks.append(t)
            return t

        # ── COMPLETED work (constellation, wins, skill levels, planning accuracy) ─
        completed = [
            mk("Write the landing page copy", ["creative", "communicative"], 2, status="completed", actual=3, created_days_ago=9),
            mk("Draft the pitch deck slides", ["creative", "communicative"], 3, status="completed", actual=4.5, created_days_ago=8),
            mk("Design the app logo", ["creative"], 1.5, status="completed", actual=2, created_days_ago=8),
            mk("Write the project README", ["creative", "communicative"], 1, status="completed", actual=1.5, created_days_ago=7),
            mk("Analyze the user survey results", ["analytical"], 2, status="completed", actual=3, created_days_ago=7),
            mk("Debug the login redirect bug", ["analytical"], 1, status="completed", actual=2, created_days_ago=6),
            mk("Research competitor pricing", ["analytical"], 1.5, status="completed", actual=2, created_days_ago=5),
            mk("Reply to mentor feedback emails", ["communicative"], 0.5, status="completed", actual=1, created_days_ago=5),
            mk("Submit the travel expense report", ["administrative"], 0.5, status="completed", actual=0.5, created_days_ago=4),
            mk("Book the demo-day venue", ["administrative", "relational"], 0.5, status="completed", actual=1, created_days_ago=4),
        ]
        for t in completed:
            add(t)

        # ── DEPENDENCY CHAIN (skill cluster + cascade map + critical path) ───────
        schema = add(mk("Set up the database schema", ["analytical"], 2, deadline=days(1), importance="high", urgency="high"))
        api = add(mk("Build the REST API endpoints", ["analytical"], 4, deadline=days(2), depends_on=[schema.id], importance="high", urgency="high", status="in_progress"))
        tests = add(mk("Write API integration tests", ["analytical"], 2, deadline=days(3), depends_on=[api.id], importance="medium", urgency="medium"))
        deploy = add(mk("Deploy backend to Cloud Run", ["administrative", "analytical"], 1, deadline=days(4), depends_on=[api.id], importance="high", urgency="medium"))

        # ── CREATIVE cluster ────────────────────────────────────────────────────
        storyboard = add(mk("Storyboard the demo video", ["creative"], 1.5, deadline=days(2), status="in_progress",
                            importance="high", urgency="high", last_opened_days_ago=0))
        add(mk("Record and edit the demo video", ["creative"], 3, deadline=days(5), depends_on=[storyboard.id], importance="high", urgency="medium"))
        add(mk("Write the demo narration script", ["creative", "communicative"], 1, deadline=days(5), importance="medium", urgency="medium"))

        # ── COMMUNICATIVE / relational ──────────────────────────────────────────
        add(mk("Email the hackathon organizers", ["communicative"], 0.5, deadline=days(1), importance="high", urgency="high"))
        add(mk("Schedule a sync with the team", ["communicative", "relational"], 0.5, deadline=days(3), importance="medium", urgency="medium"))

        # ── OVERDUE task + dependent (overdue recovery agent) ────────────────────
        grant = add(mk("Finalize the grant application", ["administrative"], 3, deadline=days(-2),
                       importance="high", urgency="high", open_no_progress=3, created_days_ago=6, last_opened_days_ago=1))
        add(mk("Submit grant to the funding portal", ["administrative"], 0.5, depends_on=[grant.id], importance="high", urgency="medium"))

        # ── NEGLECTED task (anti-list / backlog audit candidate) ─────────────────
        add(mk("Refactor the legacy export module", ["analytical"], 5, importance="low", urgency="low",
               reschedule_count=6, open_no_progress=5, created_days_ago=45, last_opened_days_ago=35,
               description="Old tech-debt nobody has touched in weeks."))

        # ── FAR-OUT deadline (vacation finder gets clear windows) ────────────────
        add(mk("Plan the Q3 product roadmap", ["analytical", "creative"], 4, deadline=days(50), importance="medium", urgency="low"))

        db.add_all(tasks)
        await db.flush()

        # ── CONTEXT SAVE on the in-progress storyboard (breadcrumb on reopen) ────
        db.add(ContextSave(
            task_id=storyboard.id,
            raw_brain_dump="Sketched the opening hook and the problem scene. Stuck on how to show the skill graph visually. Next: storyboard the 'aha' moment with the morning brief.",
            breadcrumb="* [DONE] Opening hook + problem scene sketched\n* [THINKING] How to show the skill graph on screen\n* [NEXT] Storyboard the morning-brief 'aha' moment",
        ))

        # ── BEHAVIORAL EVENTS: chronotype (morning-biased) + streak ──────────────
        completion_hours = [9, 9, 10, 10, 10, 11, 9, 15, 14, 10, 9, 11, 10, 16, 9, 10]
        for i, hour in enumerate(completion_hours):
            ts = (NOW - timedelta(days=(i % 12) + 1)).replace(hour=hour, minute=15, second=0, microsecond=0)
            events.append(BehavioralEvent(user_id=user.id, event_type="task_completed", timestamp=ts,
                                          metadata_={"seed": True}))
        # a couple today → keeps streak consistent
        for hour in (9, 10):
            events.append(BehavioralEvent(user_id=user.id, event_type="task_completed",
                                          timestamp=NOW.replace(hour=hour, minute=0, second=0, microsecond=0),
                                          metadata_={"seed": True, "today": True}))
        # richness: starts, a reschedule, a context save event
        events.append(BehavioralEvent(user_id=user.id, task_id=api.id, event_type="task_started", timestamp=NOW - timedelta(hours=3)))
        events.append(BehavioralEvent(user_id=user.id, task_id=storyboard.id, event_type="task_started", timestamp=NOW - timedelta(hours=2)))
        events.append(BehavioralEvent(user_id=user.id, task_id=grant.id, event_type="reschedule_requested", timestamp=NOW - timedelta(days=1), metadata_={"reason": "low_energy"}))
        events.append(BehavioralEvent(user_id=user.id, task_id=storyboard.id, event_type="context_saved", timestamp=NOW - timedelta(hours=2)))
        db.add_all(events)
        await db.flush()

        # ── recompute cascade severity + skill clusters over active tasks ────────
        active = [t for t in tasks if t.status in ("pending", "in_progress")]
        await _recompute_cascades(active, db)
        await _recompute_clusters(user.id, active, db)

        await db.commit()

        # ── summary ──────────────────────────────────────────────────────────────
        done = [t for t in tasks if t.status == "completed"]
        active_ct = len(active)
        casc = sorted(((t.cascade_severity, t.title) for t in active), reverse=True)[:3]
        print(f"✅ Seeded dev user {user.id}")
        print(f"   {len(tasks)} tasks  ({len(done)} completed, {active_ct} active)")
        print(f"   {len(events)} behavioral events (chronotype + streak)")
        print(f"   streak={user.streak_count}, recovery_used={user.recovery_days_used}")
        print(f"   top cascades: {casc}")
        print(f"   overdue: 'Finalize the grant application' (-2d) blocks 'Submit grant to the funding portal'")
        print(f"   backlog candidate: 'Refactor the legacy export module' (45d old, 6 reschedules)")


if __name__ == "__main__":
    asyncio.run(main())
