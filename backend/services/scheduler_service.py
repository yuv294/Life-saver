"""
OR-Tools CSP solver: assigns tasks to time windows respecting deadlines,
dependencies, energy match, and existing calendar events.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)


def solve_schedule(
    tasks: List[Dict[str, Any]],
    energy_windows: List[Dict[str, Any]],
    calendar_events: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Assign tasks to free energy windows using CP-SAT.

    tasks: list of {id, title, estimated_hours, deadline, skill_tags, depends_on}
    energy_windows: from ChronoService.get_energy_windows()
    calendar_events: list of {start, end} from CalendarService

    Returns: list of {task_id, start, end, energy_score, window_index}
    """
    try:
        from ortools.sat.python import cp_model
    except ImportError:
        logger.warning("OR-Tools not installed — using greedy scheduler")
        return _greedy_schedule(tasks, energy_windows, calendar_events)

    # Build free windows by removing calendar-blocked slots
    free_windows = _filter_free_windows(energy_windows, calendar_events)
    if not free_windows:
        return []

    model = cp_model.CpModel()
    n_tasks = len(tasks)
    n_windows = len(free_windows)

    # Flatten energy scores to integers (OR-Tools uses integer arithmetic)
    scores = [int(w["energy_score"] * 100) for w in free_windows]

    # Decision variables: assignment[i][j] = 1 if task i is in window j
    assignment = []
    for i in range(n_tasks):
        row = [model.NewBoolVar(f"a_{i}_{j}") for j in range(n_windows)]
        assignment.append(row)

    # Each task assigned to exactly one window
    for i in range(n_tasks):
        model.AddExactlyOne(assignment[i])

    # Window capacity: one task per window (simple model)
    for j in range(n_windows):
        model.AddAtMostOne(assignment[i][j] for i in range(n_tasks))

    # Deadline constraints: task must be in a window before its deadline
    for i, task in enumerate(tasks):
        if task.get("deadline"):
            deadline = datetime.fromisoformat(task["deadline"].replace("Z", "+00:00"))
            valid_windows = [
                j for j, w in enumerate(free_windows)
                if datetime.fromisoformat(w["start"]) < deadline
            ]
            if valid_windows:
                model.AddBoolOr([assignment[i][j] for j in valid_windows])

    # Dependency ordering: if task A depends on task B, place B in an earlier window
    task_index = {t["id"]: i for i, t in enumerate(tasks)}
    for i, task in enumerate(tasks):
        for dep_id in (task.get("depends_on") or []):
            if dep_id in task_index:
                j = task_index[dep_id]
                # Encode: window(j) < window(i)
                for wi in range(n_windows):
                    for wj in range(wi, n_windows):
                        model.AddImplication(assignment[i][wi], assignment[j].complement())

    # Objective: maximize sum of energy scores for selected windows
    objective_terms = []
    for i in range(n_tasks):
        for j in range(n_windows):
            objective_terms.append(assignment[i][j] * scores[j])
    model.Maximize(sum(objective_terms))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5.0
    status = solver.Solve(model)

    assignments = []
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for i in range(n_tasks):
            for j in range(n_windows):
                if solver.Value(assignment[i][j]):
                    w = free_windows[j]
                    assignments.append({
                        "task_id": tasks[i]["id"],
                        "start": w["start"],
                        "end": w["end"],
                        "energy_score": w["energy_score"],
                        "window_index": j,
                    })

    return assignments


def _filter_free_windows(
    energy_windows: List[Dict[str, Any]],
    calendar_events: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Remove windows that overlap with existing calendar events."""
    blocked = []
    for ev in calendar_events:
        try:
            start = datetime.fromisoformat(ev["start"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(ev["end"].replace("Z", "+00:00"))
            blocked.append((start, end))
        except Exception:
            continue

    free = []
    for w in energy_windows:
        ws = datetime.fromisoformat(w["start"])
        we = datetime.fromisoformat(w["end"])
        if not any(bs < we and ws < be for bs, be in blocked):
            free.append(w)
    return free


def _greedy_schedule(
    tasks: List[Dict[str, Any]],
    energy_windows: List[Dict[str, Any]],
    calendar_events: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Simple greedy: assign tasks to highest-energy free windows."""
    free = sorted(
        _filter_free_windows(energy_windows, calendar_events),
        key=lambda w: w["energy_score"],
        reverse=True,
    )
    assignments = []
    used_windows = set()
    sorted_tasks = sorted(tasks, key=lambda t: t.get("cascade_severity", 0), reverse=True)
    for i, task in enumerate(sorted_tasks):
        if i >= len(free):
            break
        for j, window in enumerate(free):
            if j not in used_windows:
                used_windows.add(j)
                assignments.append({
                    "task_id": task["id"],
                    "start": window["start"],
                    "end": window["end"],
                    "energy_score": window["energy_score"],
                    "window_index": j,
                })
                break
    return assignments
