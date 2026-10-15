"""
Task scheduler: places tasks into 30-minute energy windows.

Primary solver is OR-Tools CP-SAT; a deterministic greedy heuristic is used if
OR-Tools is not installed (and as the baseline in benchmarks/scheduler_benchmark.py).

What the model respects
  * duration       - a task needs ceil(estimated_hours / slot_length) contiguous slots
  * calendar       - slots overlapping a calendar event are unavailable
  * deadlines      - a task must finish at or before its deadline
  * dependencies   - a task starts after everything it depends on has finished
  * no double-booking - at most one task per slot

Objective: schedule as many tasks as possible (tasks that unblock more downstream
work are weighted higher), then maximise the energy of the slots they land in.
Tasks that cannot be placed are returned in `unscheduled` with a reason instead of
being silently dropped.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Reward for scheduling one task. Must dominate any energy term so the solver never
# trades a scheduled task for a slightly better slot. Energy term is at most
# 100 * slots_per_task (a few thousand), so 100_000 is safely larger.
_SCHEDULE_REWARD = 100_000


# ── Parsing / grid ────────────────────────────────────────────────────────────

def _parse_dt(value: Any) -> datetime:
    """ISO string or datetime -> timezone-aware datetime (naive values are read as UTC)."""
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@dataclass
class _Slot:
    start: datetime
    end: datetime
    energy: float
    free: bool = True


@dataclass
class _Prepared:
    idx: int
    task_id: str
    k: int                      # slots needed
    allowed: List[int]          # feasible start-slot indices
    deadline: Optional[datetime]
    deps: List[int]             # indices of prerequisite tasks (present in this batch)
    cascade: int
    reason_if_unplaceable: str = ""
    raw_deps_missing: List[str] = field(default_factory=list)


def _build_grid(
    energy_windows: List[Dict[str, Any]],
    calendar_events: List[Dict[str, Any]],
) -> List[_Slot]:
    blocked: List[Tuple[datetime, datetime]] = []
    for ev in calendar_events or []:
        try:
            blocked.append((_parse_dt(ev["start"]), _parse_dt(ev["end"])))
        except Exception:
            continue

    grid: List[_Slot] = []
    for w in sorted(energy_windows or [], key=lambda w: _parse_dt(w["start"])):
        start, end = _parse_dt(w["start"]), _parse_dt(w["end"])
        free = not any(bs < end and start < be for bs, be in blocked)
        grid.append(_Slot(start=start, end=end, energy=float(w["energy_score"]), free=free))
    return grid


def _filter_free_windows(
    energy_windows: List[Dict[str, Any]],
    calendar_events: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Return the energy windows (unchanged dicts) that do not overlap a calendar event.

    Kept as a public-ish helper: routers/tasks.py uses it to propose reschedule windows.
    """
    blocked: List[Tuple[datetime, datetime]] = []
    for ev in calendar_events or []:
        try:
            blocked.append((_parse_dt(ev["start"]), _parse_dt(ev["end"])))
        except Exception:
            continue
    free = []
    for w in energy_windows or []:
        ws, we = _parse_dt(w["start"]), _parse_dt(w["end"])
        if not any(bs < we and ws < be for bs, be in blocked):
            free.append(w)
    return free


def _slot_hours(grid: List[_Slot]) -> float:
    return (grid[0].end - grid[0].start).total_seconds() / 3600.0


def _usable_run_lengths(grid: List[_Slot]) -> List[int]:
    """run[i] = number of consecutive usable (free and time-contiguous) slots ending at i."""
    run = [0] * len(grid)
    for i, slot in enumerate(grid):
        if not slot.free:
            run[i] = 0
        elif i > 0 and run[i - 1] > 0 and grid[i - 1].end == slot.start:
            run[i] = run[i - 1] + 1
        else:
            run[i] = 1
    return run


def _prepare(tasks: List[Dict[str, Any]], grid: List[_Slot]) -> List[_Prepared]:
    hours_per_slot = _slot_hours(grid)
    run = _usable_run_lengths(grid)
    index_of = {str(t["id"]): i for i, t in enumerate(tasks)}
    prepared: List[_Prepared] = []

    for i, t in enumerate(tasks):
        hours = float(t.get("estimated_hours") or 1.0)
        k = max(1, math.ceil(hours / hours_per_slot - 1e-9))
        deadline = _parse_dt(t["deadline"]) if t.get("deadline") else None

        allowed = [
            s for s in range(len(grid) - k + 1)
            if run[s + k - 1] >= k and (deadline is None or grid[s + k - 1].end <= deadline)
        ]
        deps = [index_of[str(d)] for d in (t.get("depends_on") or []) if str(d) in index_of and index_of[str(d)] != i]
        reason = ""
        if not allowed:
            reason = (
                "no free window long enough before the deadline"
                if deadline else "no free window long enough in the planning horizon"
            )
        prepared.append(_Prepared(
            idx=i, task_id=str(t["id"]), k=k, allowed=allowed, deadline=deadline,
            deps=deps, cascade=int(t.get("cascade_severity") or 0), reason_if_unplaceable=reason,
        ))
    return prepared


def _block_energy(grid: List[_Slot], s: int, k: int) -> float:
    return sum(grid[j].energy for j in range(s, s + k))


def _assignment(p: _Prepared, s: int, grid: List[_Slot]) -> Dict[str, Any]:
    return {
        "task_id": p.task_id,
        "start": grid[s].start.isoformat(),
        "end": grid[s + p.k - 1].end.isoformat(),
        "energy_score": round(_block_energy(grid, s, p.k) / p.k, 4),  # mean over the block
        "window_index": s,
        "slots": p.k,
    }


# ── Solvers ───────────────────────────────────────────────────────────────────

def _solve_cp_sat(
    prepared: List[_Prepared],
    grid: List[_Slot],
    cp_model: Any,
    time_limit_s: float,
    num_workers: Optional[int],
) -> Tuple[Dict[int, int], str]:
    model = cp_model.CpModel()
    x: Dict[Tuple[int, int], Any] = {}
    sched: List[Any] = []
    intervals: List[Any] = []
    objective_terms: List[Any] = []
    start_expr: Dict[int, Any] = {}

    for p in prepared:
        chosen = []
        for s in p.allowed:
            v = model.NewBoolVar(f"x_{p.idx}_{s}")
            x[(p.idx, s)] = v
            chosen.append(v)
            intervals.append(model.NewOptionalFixedSizeIntervalVar(s, p.k, v, f"iv_{p.idx}_{s}"))
            energy_points = int(round(100 * _block_energy(grid, s, p.k)))
            objective_terms.append(v * (_SCHEDULE_REWARD * (1 + p.cascade) + energy_points))
        placed = model.NewBoolVar(f"sched_{p.idx}")
        if chosen:
            model.Add(sum(chosen) == placed)
            start_expr[p.idx] = sum(s * x[(p.idx, s)] for s in p.allowed)
        else:
            model.Add(placed == 0)
        sched.append(placed)

    if intervals:
        model.AddNoOverlap(intervals)

    for p in prepared:
        for d in p.deps:
            q = prepared[d]
            # A task can only be scheduled if its prerequisite is, and must start after it ends.
            model.AddImplication(sched[p.idx], sched[d])
            if p.idx in start_expr and d in start_expr:
                model.Add(start_expr[p.idx] >= start_expr[d] + q.k).OnlyEnforceIf(sched[p.idx])

    if objective_terms:
        model.Maximize(sum(objective_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    # The schedule reward (100000 per task) dwarfs the energy points (about 100 per slot), so a loose gap
    # would let the solver ignore energy entirely (a lone task landed in a poor slot at 0.3%). 1e-5 keeps
    # energy meaningful; the time limit bounds the latency on harder instances.
    solver.parameters.relative_gap_limit = 1e-5
    if num_workers:
        solver.parameters.num_workers = num_workers
    status = solver.Solve(model)
    status_name = solver.StatusName(status)

    placements: Dict[int, int] = {}
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for (i, s), v in x.items():
            if solver.Value(v):
                placements[i] = s
    return placements, status_name


def _solve_greedy(prepared: List[_Prepared], grid: List[_Slot]) -> Dict[int, int]:
    """
    Earliest-deadline-first heuristic. Each task takes the highest-energy free window
    that respects its deadline and prerequisites. Myopic: an early-deadline task can
    take a slot a later task needed, which is exactly what CP-SAT avoids.
    """
    far_future = datetime.max.replace(tzinfo=timezone.utc)
    order = sorted(
        prepared,
        key=lambda p: (p.deadline is None, p.deadline or far_future, -p.cascade, p.idx),
    )
    used = [False] * len(grid)
    placements: Dict[int, int] = {}
    resolved: set = set()
    pending = list(order)

    progress = True
    while pending and progress:
        progress = False
        for p in list(pending):
            if any(d not in resolved for d in p.deps):
                continue
            pending.remove(p)
            resolved.add(p.idx)
            progress = True
            if any(d not in placements for d in p.deps):
                continue  # a prerequisite could not be placed
            earliest = max((placements[d] + prepared[d].k for d in p.deps), default=0)
            best: Optional[Tuple[int, float]] = None
            for s in p.allowed:
                if s < earliest or any(used[s:s + p.k]):
                    continue
                energy = _block_energy(grid, s, p.k)
                if best is None or energy > best[1]:
                    best = (s, energy)
            if best is not None:
                placements[p.idx] = best[0]
                for j in range(best[0], best[0] + p.k):
                    used[j] = True
    return placements


# ── Public API ────────────────────────────────────────────────────────────────

def solve_schedule_detailed(
    tasks: List[Dict[str, Any]],
    energy_windows: List[Dict[str, Any]],
    calendar_events: List[Dict[str, Any]],
    *,
    time_limit_s: float = 2.0,
    num_workers: Optional[int] = None,
    force_greedy: bool = False,
) -> Dict[str, Any]:
    """
    tasks: [{id, estimated_hours, deadline, depends_on, cascade_severity, ...}]
    energy_windows: ChronoService.get_energy_windows() output (equal-length slots)
    calendar_events: [{start, end}]

    Returns {assignments, unscheduled, solver, status, solve_time_ms, total_energy}.
    """
    t0 = time.perf_counter()
    empty = {
        "assignments": [], "unscheduled": [], "solver": "none", "status": "EMPTY",
        "solve_time_ms": 0.0, "total_energy": 0.0,
    }
    grid = _build_grid(energy_windows, calendar_events)
    if not tasks:
        return empty
    if not grid:
        return {**empty, "unscheduled": [
            {"task_id": str(t["id"]), "reason": "no energy windows available"} for t in tasks
        ]}

    prepared = _prepare(tasks, grid)

    solver_name, status_name = "greedy", "HEURISTIC"
    cp_model = None
    if not force_greedy:
        try:
            from ortools.sat.python import cp_model  # type: ignore
        except ImportError:
            logger.warning("OR-Tools not installed - using greedy scheduler")

    if cp_model is not None:
        placements, status_name = _solve_cp_sat(prepared, grid, cp_model, time_limit_s, num_workers)
        solver_name = "cp-sat"
    else:
        placements = _solve_greedy(prepared, grid)

    assignments = [
        _assignment(p, placements[p.idx], grid)
        for p in sorted(prepared, key=lambda p: placements.get(p.idx, 10 ** 9))
        if p.idx in placements
    ]
    unscheduled = []
    for p in prepared:
        if p.idx in placements:
            continue
        if p.reason_if_unplaceable:
            reason = p.reason_if_unplaceable
        elif any(d not in placements for d in p.deps):
            reason = "a prerequisite task could not be scheduled (or dependencies are circular)"
        else:
            reason = "not enough free capacity before its deadline alongside other tasks"
        unscheduled.append({"task_id": p.task_id, "reason": reason})

    total_energy = sum(_block_energy(grid, s, prepared[i].k) for i, s in placements.items()) * _slot_hours(grid)
    return {
        "assignments": assignments,
        "unscheduled": unscheduled,
        "solver": solver_name,
        "status": status_name,
        "solve_time_ms": round((time.perf_counter() - t0) * 1000, 2),
        "total_energy": round(total_energy, 4),
    }


def solve_schedule(
    tasks: List[Dict[str, Any]],
    energy_windows: List[Dict[str, Any]],
    calendar_events: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Backwards-compatible wrapper: returns just the assignments list."""
    return solve_schedule_detailed(tasks, energy_windows, calendar_events)["assignments"]
