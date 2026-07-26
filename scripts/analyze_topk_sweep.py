"""Analyze the B5+planner top-K sweep results.

Reads logs/b5p_seed{N}.jsonl files (re-written by the sweep; the
seed number encodes the run, and the planner_top_k field in the
start event encodes the K value) and produces a summary table
by K value.

Usage:
    uv run python scripts/analyze_topk_sweep.py
    uv run python scripts/analyze_topk_sweep.py --json
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
import statistics


LOGS = Path("logs")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="JSON output")
    args = ap.parse_args()

    # Find all the b5p_*.jsonl files (the sweep re-uses these names).
    by_k: dict[int, list[dict]] = defaultdict(list)
    for log_path in sorted(LOGS.glob("b5p_*.jsonl")):
        # Read all events; find the start event for K and the
        # final summary event for results.
        try:
            events = [json.loads(l) for l in
                      log_path.read_text(encoding="utf-8").splitlines()]
        except Exception:
            continue
        if not events:
            continue
        start = events[0]
        if start.get("event") != "start" or start.get("arm") != "B5P":
            continue
        K = start.get("planner_top_k", "?")
        summary = events[-1]
        if summary.get("event") != "summary":
            # Run still in progress — skip.
            continue
        by_k[K].append(summary)

    # Build the summary table.
    rows = []
    for K in sorted(by_k.keys()):
        runs = by_k[K]
        if not runs:
            continue
        n = len(runs)
        solved = [r.get("n_solved", 0) for r in runs]
        evo = [r.get("n_evo_solved", 0) for r in runs]
        texact = [r.get("n_test_exact", 0) for r in runs]
        lens = [r.get("mean_solution_length", 0.0) for r in runs]
        rows.append({
            "K": K,
            "n_seeds": n,
            "solved_mean": statistics.mean(solved),
            "solved_sd": statistics.stdev(solved) if n > 1 else 0.0,
            "evo_mean": statistics.mean(evo),
            "test_exact_mean": statistics.mean(texact),
            "mean_len_mean": statistics.mean(lens),
            "solved_per_seed": solved,
        })

    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        if not rows:
            print("no completed runs yet")
            return
        print(f"{'K':>3s}  {'n':>3s}  {'solved':>14s}  {'evo':>10s}  "
              f"{'texact':>8s}  {'len':>5s}")
        print("-" * 60)
        for r in rows:
            solved_str = (f"{r['solved_mean']:5.2f} +/- "
                          f"{r['solved_sd']:4.2f}")
            print(f"{r['K']:>3}  {r['n_seeds']:>3}  {solved_str:>14s}  "
                  f"{r['evo_mean']:>10.2f}  {r['test_exact_mean']:>8.2f}  "
                  f"{r['mean_len_mean']:>5.2f}")
        print()
        for r in rows:
            print(f"K={r['K']} solved per seed: {r['solved_per_seed']}")


if __name__ == "__main__":
    main()
