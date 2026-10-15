"""
Scheduler tests. Pure Python: no database, Firebase or Gemini needed.

Each behaviour is checked against the greedy solver everywhere, and against CP-SAT
whenever OR-Tools is installed (it is in CI and in the Docker image).
"""

from datetime import datetime, timedelta, timezone

from services.scheduler_service import solve_schedule, solve_schedule_detailed

try:
    import ortools  # noqa: F401
    HAVE_ORTOOLS = True
except ImportError:  # pragma: no cover
    HAVE_ORTOOLS = False

BASE = datetime(2026, 1, 5, 6, 0, tzinfo=timezone.utc)  # a Monday, 06:00 UTC

# hour-of-day -> energy, same shape as the app's default curve
CURVE = {6: .5, 7: .65, 8: .8, 9: .95, 10: 1.0, 11: .95, 12: .75, 13: .6, 14: .55,
         15: .65, 16: .7, 17: .65, 18: .55, 19: .5, 20: .45, 21: .35, 22: .25, 23: .15}


def make_windows(hours=48):
    out = []
    for i in range(hours * 2):
        s = BASE + timedelta(minutes=30 * i)
        out.append({
            "start": s.isoformat(),
            "end": (s + timedelta(minutes=30)).isoformat(),
            "energy_score": CURVE.get(s.hour, 0.3),
        })
    return out


def at(hours_from_base):
    return (BASE + timedelta(hours=hours_from_base)).isoformat()


def task(tid, hours=1.0, deadline_h=None, deps=None, cascade=0):
    return {
        "id": tid,
        "estimated_hours": hours,
        "deadline": at(deadline_h) if deadline_h is not None else None,
        "depends_on": deps or [],
        "cascade_severity": cascade,
    }


def modes():
    return ["greedy", "cp-sat"] if HAVE_ORTOOLS else ["greedy"]


def run(mode, tasks, events=None, windows=None):
    return solve_schedule_detailed(
        tasks, windows or make_windows(), events or [], force_greedy=(mode == "greedy"),
    )


def span(a):
    return datetime.fromisoformat(a["start"]), datetime.fromisoformat(a["end"])


def by_id(result):
    return {a["task_id"]: a for a in result["assignments"]}


# ── duration, overlap, calendar, deadlines ────────────────────────────────────

def test_task_duration_is_honoured():
    for mode in modes():
        a = by_id(run(mode, [task("t", hours=2.5)]))["t"]
        s, e = span(a)
        assert e - s == timedelta(hours=2.5), mode
        assert a["slots"] == 5


def test_assignments_never_overlap():
    for mode in modes():
        tasks = [task(f"t{i}", hours=1.5) for i in range(10)]
        spans = sorted(span(a) for a in run(mode, tasks)["assignments"])
        for (_, e1), (s2, _) in zip(spans, spans[1:]):
            assert e1 <= s2, mode


def test_calendar_events_are_avoided():
    event = {"start": at(3), "end": at(6)}  # 09:00-12:00, the best energy window
    for mode in modes():
        res = run(mode, [task(f"t{i}", hours=1.0) for i in range(4)], events=[event])
        ev_s, ev_e = datetime.fromisoformat(event["start"]), datetime.fromisoformat(event["end"])
        for a in res["assignments"]:
            s, e = span(a)
            assert e <= ev_s or s >= ev_e, mode


def test_task_is_not_split_around_a_calendar_event():
    # one 2h gap only: 10:00-12:00 free, everything else blocked
    events = [{"start": at(0), "end": at(4)}, {"start": at(6), "end": at(60)}]
    for mode in modes():
        res = run(mode, [task("fits", hours=2.0), task("too_long", hours=3.0)], events=events)
        placed = by_id(res)
        assert "fits" in placed
        assert "too_long" not in placed
        assert any(u["task_id"] == "too_long" for u in res["unscheduled"])


def test_deadline_is_respected():
    for mode in modes():
        res = run(mode, [task("t", hours=2.0, deadline_h=5)])
        _, end = span(by_id(res)["t"])
        assert end <= BASE + timedelta(hours=5), mode


def test_deadline_that_cannot_be_met_is_reported_not_crashed():
    for mode in modes():
        res = run(mode, [task("late", hours=4.0, deadline_h=1)])
        assert res["assignments"] == []
        assert res["unscheduled"][0]["task_id"] == "late"
        assert "deadline" in res["unscheduled"][0]["reason"]


def test_single_task_lands_in_the_peak_energy_window():
    for mode in modes():
        a = by_id(run(mode, [task("t", hours=1.0)]))["t"]
        start, _ = span(a)
        assert start.hour in (9, 10), (mode, start)


# ── dependencies (regression: the original CP-SAT code crashed on any dependency) ──

def test_dependencies_run_in_order():
    tasks = [task("b", hours=1.0, deps=["a"]), task("a", hours=1.0)]
    for mode in modes():
        placed = by_id(run(mode, tasks))
        assert span(placed["a"])[1] <= span(placed["b"])[0], mode


def test_dependency_chain_of_three():
    tasks = [task("c", deps=["b"]), task("b", deps=["a"]), task("a")]
    for mode in modes():
        placed = by_id(run(mode, tasks))
        assert span(placed["a"])[1] <= span(placed["b"])[0] <= span(placed["b"])[1] <= span(placed["c"])[0], mode


def test_unknown_dependency_id_is_ignored():
    for mode in modes():
        res = run(mode, [task("t", deps=["already-completed-task"])])
        assert [a["task_id"] for a in res["assignments"]] == ["t"]


def test_circular_dependencies_are_reported_not_crashed():
    tasks = [task("a", deps=["b"]), task("b", deps=["a"]), task("ok")]
    for mode in modes():
        res = run(mode, tasks)
        assert {a["task_id"] for a in res["assignments"]} == {"ok"}, mode
        assert {u["task_id"] for u in res["unscheduled"]} == {"a", "b"}


def test_task_is_unscheduled_when_its_prerequisite_cannot_be_scheduled():
    tasks = [task("big", hours=100.0), task("child", deps=["big"])]
    for mode in modes():
        res = run(mode, tasks)
        assert res["assignments"] == [], mode
        assert {u["task_id"] for u in res["unscheduled"]} == {"big", "child"}


# ── capacity / overall behaviour ──────────────────────────────────────────────

def test_overloaded_day_schedules_what_fits_and_reports_the_rest():
    tasks = [task(f"t{i}", hours=2.0, deadline_h=8) for i in range(10)]  # 20h of work, 8h available
    for mode in modes():
        res = run(mode, tasks)
        assert len(res["assignments"]) <= 4
        assert len(res["assignments"]) + len(res["unscheduled"]) == 10


def test_empty_inputs():
    assert solve_schedule([], make_windows(), []) == []
    res = solve_schedule_detailed([task("t")], [], [])
    assert res["assignments"] == [] and res["unscheduled"][0]["reason"] == "no energy windows available"


def test_solve_schedule_wrapper_returns_assignment_list():
    out = solve_schedule([task("t", hours=1.0)], make_windows(), [])
    assert isinstance(out, list) and out[0]["task_id"] == "t"


CONTENTION = [
    task("early_flexible", hours=2.0, deadline_h=6),   # 06:00-12:00 holds exactly 3 x 2h
    task("tight", hours=2.0, deadline_h=5),
    task("also_tight", hours=2.0, deadline_h=5),
]


def test_greedy_is_myopic_on_a_contention_case():
    """Documents the baseline's weakness: the two tight tasks take the high-energy slots
    and leave no 2h gap for the third, although a packing of all three exists."""
    res = run("greedy", CONTENTION)
    assert len(res["assignments"]) == 2


def test_cp_sat_packs_all_three_where_greedy_cannot():
    if not HAVE_ORTOOLS:
        return
    res = run("cp-sat", CONTENTION)
    assert res["solver"] == "cp-sat" and res["status"] in ("OPTIMAL", "FEASIBLE")
    assert len(res["assignments"]) == 3 and res["unscheduled"] == []
