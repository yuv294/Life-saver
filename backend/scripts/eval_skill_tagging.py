#!/usr/bin/env python3
"""
Evaluate LifeSaver's Gemini skill tagging against YOUR hand labels, and compare it to the
keyword-heuristic fallback the app uses when Gemini is unavailable.

1. Fill in the `true_tags` column of scripts/tag_eval_template.csv yourself (the labels must
   be your own judgement - that is what makes the result meaningful). Use only:
   analytical, creative, communicative, administrative, relational, physical
   Separate multiple tags with ';' and put the most important one first.
2. From backend/ with your virtualenv active and GEMINI_API_KEY set (GEMINI_ENABLED=true):

       python scripts/eval_skill_tagging.py --csv scripts/tag_eval_template.csv

Reports: exact-set match, mean Jaccard, micro precision/recall/F1, primary-skill accuracy,
Gemini-vs-heuristic comparison, how often the app silently fell back to heuristics, and
latency. Free-tier Gemini is rate-limited, hence --sleep (seconds between calls).
"""

import argparse
import asyncio
import csv
import json
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from services.gemini_service import VALID_SKILL_TAGS, _heuristic_skills, classify_skills  # noqa: E402


def load(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            tags = [t.strip().lower() for t in (r.get("true_tags") or "").split(";") if t.strip()]
            if not tags:
                continue
            bad = [t for t in tags if t not in VALID_SKILL_TAGS]
            if bad:
                sys.exit(f"Invalid tag(s) {bad} in row: {r['title']!r}")
            rows.append({"title": r["title"], "description": r.get("description") or "", "true": tags})
    return rows


def jaccard(a, b):
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if (a | b) else 1.0


def score(rows, preds):
    tp = fp = fn = 0
    exact = prim = 0
    jac = []
    for r, p in zip(rows, preds):
        t, q = set(r["true"]), set(p)
        tp += len(t & q)
        fp += len(q - t)
        fn += len(t - q)
        exact += t == q
        prim += (p[0] == r["true"][0]) if p else 0
        jac.append(jaccard(t, q))
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    return {
        "n": len(rows), "exact_match": exact / len(rows), "mean_jaccard": sum(jac) / len(jac),
        "precision": prec, "recall": rec, "f1": 2 * prec * rec / (prec + rec) if prec + rec else 0.0,
        "primary_skill_accuracy": prim / len(rows),
    }


def pct(values, q):
    values = sorted(values)
    k = (len(values) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return values[lo] + (values[hi] - values[lo]) * (k - lo)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--sleep", type=float, default=6.5, help="seconds between Gemini calls (free tier ~10/min)")
    ap.add_argument("--out", default="metrics")
    args = ap.parse_args()

    rows = load(args.csv)
    if len(rows) < 20:
        print(f"Only {len(rows)} labelled rows - label at least 30-40 for a result worth quoting.", file=sys.stderr)

    gemini_preds, heur_preds, latencies, fallbacks = [], [], [], 0
    for i, r in enumerate(rows, 1):
        t0 = time.perf_counter()
        out = await classify_skills(r["title"], r["description"])
        latencies.append((time.perf_counter() - t0) * 1000)
        if out.get("_source") == "heuristic":
            fallbacks += 1
        gemini_preds.append(out.get("skill_tags") or [])
        heur_preds.append(_heuristic_skills(r["title"], r["description"])["skill_tags"])
        print(f"[{i}/{len(rows)}] {r['title'][:50]:50s} true={r['true']} pred={gemini_preds[-1]} ({out.get('_source', 'gemini')})")
        if i < len(rows):
            await asyncio.sleep(args.sleep)

    report = {
        "labelled_tasks": len(rows),
        "gemini": score(rows, gemini_preds),
        "keyword_heuristic": score(rows, heur_preds),
        "gemini_fell_back_to_heuristic": fallbacks,
        "latency_ms": {"p50": pct(latencies, 0.5), "p95": pct(latencies, 0.95)},
    }
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "skill_tagging_eval.json").write_text(json.dumps(report, indent=2))

    g, h = report["gemini"], report["keyword_heuristic"]
    print("\n| Metric | Gemini | Keyword heuristic |\n|---|---|---|")
    for key, label in [("exact_match", "Exact tag-set match"), ("mean_jaccard", "Mean Jaccard"),
                       ("precision", "Micro precision"), ("recall", "Micro recall"), ("f1", "Micro F1"),
                       ("primary_skill_accuracy", "Primary-skill accuracy")]:
        print(f"| {label} | {g[key]:.1%} | {h[key]:.1%} |")
    print(f"\nn = {len(rows)} hand-labelled tasks; {fallbacks} Gemini calls fell back to heuristics; "
          f"latency p50 {report['latency_ms']['p50']:.0f} ms, p95 {report['latency_ms']['p95']:.0f} ms")
    if fallbacks:
        print("Fallbacks mean the Gemini column is partly heuristic output - rerun with a billed key or a larger --sleep.")


if __name__ == "__main__":
    asyncio.run(main())
