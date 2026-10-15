#!/usr/bin/env python3
"""
Offline benchmark: OR-Tools CP-SAT vs an earliest-deadline-first greedy baseline on
synthetic scheduling instances. No database, network or API key required.

    python benchmarks/scheduler_benchmark.py --n 50 --seed 7 --out benchmarks/results

Every returned schedule is re-checked by an independent validator (overlap, calendar
clashes, deadlines, dependencies, duration), so the quality numbers below can only come
from schedules that satisfy every constraint.

Instances are synthetic and deliberately contended (a 48h horizon, 2-5 calendar
meetings, 8-16 tasks of 0.5-3h, 75% with deadlines, ~25% with a prerequisite). The
numbers describe this generator, not real users - say so when you quote them.
"""

import argparse
import json
import math
import random
import statistics
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.scheduler_service import solve_schedule_detailed  # noqa: E402

try:
    import ortools  # noqa: F401
    HAVE_ORTOOLS = True
except ImportError:
    HAVE_ORTOOLS = False

BASE = datetime(2026, 1, 5, 6, 0, tzinfo=timezone.utc)
CURVE = {6: .5, 7: .65, 8: .8, 9: .95, 10: 1.0, 11: .95, 12: .75, 13: .6, 14: .55,
         15: .65, 16: .7, 17: .65, 18: .55, 19: .5, 20: .45, 21: .35, 22: .25, 23: .15}
HORIZON_H = 48
TIME_LIMIT_S = 2.0  # same as the production default in solve_schedule_detailed


def windows():
    out = []
    for i in range(HORIZON_H * 2):
        s = BASE + timedelta(minutes=30 * i)
        out.append({"start": s.isoformat(), "end": (s + timedelta(minutes=30)).isoformat(),
                    "energy_score": CURVE.get(s.hour, 0.3)})
    return out


def make_instance(rng):
    events = []
    for _ in range(rng.randint(2, 5)):
        start_h = rng.randrange(0, 40) / 1.0 + rng.choice([0, 0.5])
        dur_h = rng.choice([1, 1.5, 2, 3])
        s = BASE + timedelta(hours=start_h)
        events.append({"start": s.isoformat(), "end": (s + timedelta(hours=dur_h)).isoformat()})

    n = rng.randint(8, 16)
    tasks = []
    for i in range(n):
        hours = rng.choice([0.5, 1, 1, 1.5, 2, 3])
        deadline = None
        if rng.random() < 0.75:
            deadline = (BASE + timedelta(hours=rng.uniform(hours + 2, 44))).isoformat()
        deps = []
        if i > 0 and rng.random() < 0.25:
            deps = [f"t{rng.randrange(0, i)}"]
        tasks.append({"id": f"t{i}", "estimated_hours": hours, "deadline": deadline,
                      "depends_on": deps, "cascade_severity": 0})

    children = {t["id"]: [] for t in tasks}  # cascade_severity = number of downstream tasks
    for t in tasks:
        for d in t["depends_on"]:
            children[d].append(t["id"])

    def descendants(tid, seen=None):
        seen = seen if seen is not None else set()
        for c in children[tid]:
            if c not in seen:
                seen.add(c)
                descendants(c, seen)
        return seen

    for t in tasks:
        t["cascade_severity"] = len(descendants(t["id"]))
    return tasks, events


def validate(tasks, events, assignments):
    """Independent constraint check. Every count must be 0."""
    v = {"overlap": 0, "calendar": 0, "deadline": 0, "dependency": 0, "duration": 0}
    by_id = {t["id"]: t for t in tasks}
    spans = {a["task_id"]: (datetime.fromisoformat(a["start"]), datetime.fromisoformat(a["end"])) for a in assignments}

    ordered = sorted(spans.values())
    v["overlap"] = sum(1 for (_, e1), (s2, _) in zip(ordered, ordered[1:]) if e1 > s2)

    blocked = [(datetime.fromisoformat(e["start"]), datetime.fromisoformat(e["end"])) for e in events]
    for s, e in spans.values():
        if any(bs < e and s < be for bs, be in blocked):
            v["calendar"] += 1

    for tid, (s, e) in spans.items():
        t = by_id[tid]
        need = timedelta(hours=math.ceil(t["estimated_hours"] * 2) / 2)
        if e - s != need:
            v["duration"] += 1
        if t["deadline"] and e > datetime.fromisoformat(t["deadline"]):
            v["deadline"] += 1
        for d in t["depends_on"]:
            if d not in spans or spans[d][1] > s:
                v["dependency"] += 1
    return v


def run_solver(name, tasks, events, workers):
    res = solve_schedule_detailed(tasks, windows(), events, time_limit_s=TIME_LIMIT_S, num_workers=workers,
                                  force_greedy=(name == "greedy"))
    hours = {t["id"]: t["estimated_hours"] for t in tasks}
    placed = [a["task_id"] for a in res["assignments"]]
    scheduled_hours = sum(hours[i] for i in placed)
    return {
        "scheduled": len(placed),
        "total": len(tasks),
        "scheduled_hours": scheduled_hours,
        "energy_hours": res["total_energy"],
        "energy_per_hour": (res["total_energy"] / scheduled_hours) if scheduled_hours else 0.0,
        "solve_ms": res["solve_time_ms"],
        "status": res["status"],
        "violations": validate(tasks, events, res["assignments"]),
    }


def pct(values, q):
    values = sorted(values)
    if not values:
        return 0.0
    k = (len(values) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return values[lo] + (values[hi] - values[lo]) * (k - lo)


def mean_sd(values):
    return (statistics.mean(values), statistics.pstdev(values)) if values else (0.0, 0.0)


def summarise(rows):
    rate = [r["scheduled"] / r["total"] for r in rows]
    energy = [r["energy_per_hour"] for r in rows]
    ms = [r["solve_ms"] for r in rows]
    viol = sum(sum(r["violations"].values()) for r in rows)
    return {
        "instances": len(rows),
        "tasks_scheduled_rate_mean": mean_sd(rate)[0],
        "tasks_scheduled_rate_sd": mean_sd(rate)[1],
        "tasks_scheduled_total": sum(r["scheduled"] for r in rows),
        "tasks_total": sum(r["total"] for r in rows),
        "scheduled_hours_total": sum(r["scheduled_hours"] for r in rows),
        "energy_per_scheduled_hour_mean": mean_sd(energy)[0],
        "solve_ms_p50": pct(ms, 0.5), "solve_ms_p95": pct(ms, 0.95), "solve_ms_max": max(ms) if ms else 0.0,
        "constraint_violations": viol,
        "status_counts": {s: sum(1 for r in rows if r["status"] == s) for s in sorted({r["status"] for r in rows})},
    }


def head_to_head(cp_rows, greedy_rows):
    wins = ties = losses = energy_wins = 0
    for c, g in zip(cp_rows, greedy_rows):
        if c["scheduled"] > g["scheduled"]:
            wins += 1
        elif c["scheduled"] < g["scheduled"]:
            losses += 1
        else:
            ties += 1
            if c["energy_hours"] > g["energy_hours"] + 1e-9:
                energy_wins += 1
    return {"cp_more_tasks": wins, "same_tasks": ties, "cp_fewer_tasks": losses,
            "of_the_ties_cp_higher_energy": energy_wins}


def markdown(summary, h2h, args):
    g, c = summary["greedy"], summary.get("cp-sat")
    lines = [
        f"### Scheduler benchmark ({args.n} synthetic instances, seed {args.seed})",
        "",
        "| Metric | Greedy (EDF) | CP-SAT |",
        "|---|---|---|",
    ]

    def row(label, key, fmt):
        gv = fmt.format(g[key])
        cv = fmt.format(c[key]) if c else "n/a (OR-Tools not installed)"
        lines.append(f"| {label} | {gv} | {cv} |")

    row("Tasks scheduled (mean rate)", "tasks_scheduled_rate_mean", "{:.1%}")
    row("Tasks scheduled (total)", "tasks_scheduled_total", "{}")
    row("Hours scheduled (total)", "scheduled_hours_total", "{:.1f}")
    row("Mean energy per scheduled hour", "energy_per_scheduled_hour_mean", "{:.3f}")
    row("Solve time p50 (ms)", "solve_ms_p50", "{:.1f}")
    row("Solve time p95 (ms)", "solve_ms_p95", "{:.1f}")
    row("Constraint violations (validator)", "constraint_violations", "{}")
    if c:
        lines += ["", f"Head-to-head: CP-SAT scheduled more tasks in {h2h['cp_more_tasks']} instances, "
                      f"the same in {h2h['same_tasks']} (higher energy in {h2h['of_the_ties_cp_higher_energy']} of those), "
                      f"fewer in {h2h['cp_fewer_tasks']}.",
                  f"CP-SAT status counts: {c['status_counts']}."]
    lines += ["", "Synthetic instances: 48h horizon, 2-5 meetings, 8-16 tasks of 0.5-3h, 75% with deadlines, ~25% with a prerequisite."]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--workers", type=int, default=4, help="CP-SAT worker threads")
    ap.add_argument("--out", default="benchmarks/results")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    instances = [make_instance(rng) for _ in range(args.n)]
    solvers = ["greedy"] + (["cp-sat"] if HAVE_ORTOOLS else [])
    if not HAVE_ORTOOLS:
        print("OR-Tools is not installed: running the greedy baseline only (pip install ortools).", file=sys.stderr)

    results = {name: [] for name in solvers}
    t0 = time.perf_counter()
    for tasks, events in instances:
        for name in solvers:
            results[name].append(run_solver(name, tasks, events, args.workers))

    summary = {name: summarise(rows) for name, rows in results.items()}
    h2h = head_to_head(results["cp-sat"], results["greedy"]) if HAVE_ORTOOLS else None
    report = markdown(summary, h2h, args)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "scheduler_benchmark.json").write_text(json.dumps(
        {"args": vars(args), "summary": summary, "head_to_head": h2h, "per_instance": results}, indent=2))
    (out / "scheduler_benchmark.md").write_text(report + "\n")
    print(report)
    print(f"\n(total wall time {time.perf_counter() - t0:.1f}s; results in {out}/)")

    bad = sum(s["constraint_violations"] for s in summary.values())
    if bad:
        print(f"ERROR: {bad} constraint violations - a solver returned an invalid schedule", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
