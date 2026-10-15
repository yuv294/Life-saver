#!/usr/bin/env python3
"""
Measure the *deployed* LifeSaver API: latency percentiles, error rate and which scheduler
solver is live. Standard library only - run it from any laptop.

    export LIFESAVER_TOKEN="<Firebase ID token>"          # see README: "Getting a token"
    python scripts/measure_deployed.py --base-url https://YOUR-SERVICE.a.run.app

What it does
  * GET endpoints, sequential, --n times each (default 30) after one warm-up call
  * POST /tasks --creates times (default 10): the end-to-end task-creation path including
    Gemini skill tagging. The tasks are titled "[bench] ..." and set to "abandoned" afterwards
  * POST /agents/me/morning-brief --briefs times (default 3): the multi-tool Gemini agent chain
  * --cold: records the first /health call separately. Only meaningful if the service has been
    idle for 15+ minutes (Cloud Run scales to zero), so run it first after a break.

Nothing is sent anywhere except your own service. The token is never written to disk.
"""

import argparse
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BENCH_TITLES = [
    "[bench] Write the project report", "[bench] Email the landlord about the lease",
    "[bench] Prepare slides for Friday's review", "[bench] Go for a 5k run",
    "[bench] Debug the failing integration test", "[bench] Plan a surprise birthday dinner",
    "[bench] File the reimbursement form", "[bench] Design the landing page mockup",
    "[bench] Call the bank about the card", "[bench] Revise for the algorithms quiz",
]


def call(base, path, token, method="GET", body=None, timeout=60):
    url = base.rstrip("/") + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if token and path != "/health":
        req.add_header("Authorization", f"Bearer {token}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    t0 = time.perf_counter()
    status, payload = 0, None
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            raw = resp.read()
    except urllib.error.HTTPError as e:
        status, raw = e.code, e.read()
    except Exception:
        raw = b""
    ms = (time.perf_counter() - t0) * 1000
    try:
        payload = json.loads(raw) if raw else None
    except ValueError:
        payload = None
    return status, ms, payload


def pct(values, q):
    values = sorted(values)
    if not values:
        return float("nan")
    k = (len(values) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return values[lo] + (values[hi] - values[lo]) * (k - lo)


def summarise(label, samples):
    ok = [ms for st, ms in samples if 200 <= st < 300]
    errors = len(samples) - len(ok)
    return {
        "endpoint": label, "requests": len(samples), "errors": errors,
        "error_rate": errors / len(samples) if samples else 0.0,
        "p50_ms": pct(ok, 0.5), "p95_ms": pct(ok, 0.95), "p99_ms": pct(ok, 0.99),
        "min_ms": min(ok) if ok else float("nan"), "max_ms": max(ok) if ok else float("nan"),
        "status_codes": {str(c): sum(1 for s, _ in samples if s == c) for c in sorted({s for s, _ in samples})},
    }


def table(rows):
    out = ["| Endpoint | n | errors | p50 (ms) | p95 (ms) | max (ms) |", "|---|---|---|---|---|---|"]
    for r in rows:
        out.append(f"| {r['endpoint']} | {r['requests']} | {r['errors']} | {r['p50_ms']:.0f} | {r['p95_ms']:.0f} | {r['max_ms']:.0f} |")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--token", default=os.environ.get("LIFESAVER_TOKEN", ""),
                    help="Firebase ID token (or env LIFESAVER_TOKEN). Use 'dev' only against a local dev-bypass server.")
    ap.add_argument("--n", type=int, default=30, help="requests per GET endpoint")
    ap.add_argument("--creates", type=int, default=10)
    ap.add_argument("--briefs", type=int, default=3)
    ap.add_argument("--cold", action="store_true", help="record the first /health call as the cold-start sample")
    ap.add_argument("--read-only", action="store_true", help="skip POST /tasks and morning-brief")
    ap.add_argument("--out", default="metrics")
    args = ap.parse_args()

    if not args.token and not args.read_only:
        print("No token given: only /health will work. Set LIFESAVER_TOKEN or pass --token.", file=sys.stderr)

    report = {"measured_at": datetime.now(timezone.utc).isoformat(), "base_url": args.base_url}

    first_status, first_ms, _ = call(args.base_url, "/health", args.token)
    report["first_request"] = {"status": first_status, "ms": first_ms, "treat_as_cold_start": args.cold}
    print(f"first /health: HTTP {first_status} in {first_ms:.0f} ms" + ("  (cold-start sample)" if args.cold else ""))
    if first_status != 200:
        print("Service did not answer /health with 200 - check the URL.", file=sys.stderr)
        sys.exit(2)

    get_paths = ["/health"]
    if args.token:
        get_paths += ["/tasks", "/tasks/clusters", "/schedule/energy-windows", "/schedule/optimize", "/users/me/planning-summary"]

    rows, optimize_info = [], None
    for path in get_paths:
        call(args.base_url, path, args.token)  # warm-up, not recorded
        samples = []
        for _ in range(args.n):
            st, ms, body = call(args.base_url, path, args.token)
            samples.append((st, ms))
            if path == "/schedule/optimize" and st == 200 and isinstance(body, dict):
                optimize_info = {k: body.get(k) for k in ("solver", "solve_time_ms", "task_count")}
        rows.append(summarise(f"GET {path}", samples))
        print(f"GET {path}: p50 {rows[-1]['p50_ms']:.0f} ms, p95 {rows[-1]['p95_ms']:.0f} ms, errors {rows[-1]['errors']}")

    created_ids = []
    if args.token and not args.read_only:
        samples = []
        for i in range(args.creates):
            st, ms, body = call(args.base_url, "/tasks", args.token, "POST",
                                {"title": BENCH_TITLES[i % len(BENCH_TITLES)], "estimated_hours": 1})
            samples.append((st, ms))
            if st == 201 and isinstance(body, dict) and body.get("id"):
                created_ids.append(body["id"])
        rows.append(summarise("POST /tasks (incl. Gemini tagging)", samples))
        print(f"POST /tasks: p50 {rows[-1]['p50_ms']:.0f} ms, p95 {rows[-1]['p95_ms']:.0f} ms, errors {rows[-1]['errors']}")

        samples = []
        for _ in range(args.briefs):
            st, ms, _ = call(args.base_url, "/agents/me/morning-brief", args.token, "POST", timeout=120)
            samples.append((st, ms))
        rows.append(summarise("POST /agents/me/morning-brief (Gemini agent chain)", samples))
        print(f"morning-brief: p50 {rows[-1]['p50_ms']:.0f} ms, errors {rows[-1]['errors']}")

        for task_id in created_ids:  # clean up the benchmark tasks
            call(args.base_url, f"/tasks/{task_id}", args.token, "PATCH", {"status": "abandoned"})
        print(f"cleaned up {len(created_ids)} benchmark tasks (status=abandoned)")

    report["endpoints"] = rows
    report["schedule_optimize_response"] = optimize_info
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    (out / f"deployed-{stamp}.json").write_text(json.dumps(report, indent=2))
    md = table(rows)
    if optimize_info:
        md += f"\n\n/schedule/optimize reported solver = `{optimize_info.get('solver')}`"
    (out / f"deployed-{stamp}.md").write_text(md + "\n")
    print("\n" + md + f"\n\nsaved to {out}/deployed-{stamp}.(json|md)")


if __name__ == "__main__":
    main()
