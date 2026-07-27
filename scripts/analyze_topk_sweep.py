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
    in_progress: list[dict] = []
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
            # Run still in progress — report as in-progress.
            latest_epoch = None
            for e in reversed(events):
                if e.get("event") == "epoch":
                    latest_epoch = e
                    break
            in_progress.append({
                "seed": start.get("seed"),
                "log": log_path.name,
                "evals": latest_epoch.get("evals") if latest_epoch else None,
                "solved": latest_epoch.get("solved") if latest_epoch else None,
            })
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
        print(json.dumps({"rows": rows, "in_progress": in_progress}, indent=2))
    else:
        if not rows and not in_progress:
            print("no runs found")
            return
        print(f"{'K':>3s}  {'n':>3s}  {'solved':>14s}  {'evo':>10s}  "
              f"{'texact':>8s}  {'len':>5s}")
        print("-" * 60)
        for r in rows:
            # n_seeds is the count of *completed* runs (those with
            # a summary event). The solved_per_seed list may
            # include in-progress runs as a tail - we slice it.
            completed_solves = r["solved_per_seed"][:r["n_seeds"]]
            if completed_solves:
                r["solved_mean"] = statistics.mean(completed_solves)
                r["solved_sd"] = (statistics.stdev(completed_solves)
                                   if len(completed_solves) > 1 else 0.0)
            solved_str = (f"{r['solved_mean']:5.2f} +/- "
                          f"{r['solved_sd']:4.2f}")
            print(f"{r['K']:>3}  {r['n_seeds']:>3}  {solved_str:>14s}  "
                  f"{r['evo_mean']:>10.2f}  {r['test_exact_mean']:>8.2f}  "
                  f"{r['mean_len_mean']:>5.2f}")
        for r in rows:
            print(f"K={r['K']} solved per seed: {r['solved_per_seed']}")
        if in_progress:
            print()
            print("in progress (not included in the mean):")
            for ip in in_progress:
                print(f"  seed={ip['seed']}  log={ip['log']}  "
                      f"evals={ip['evals']}  solved={ip['solved']}")


if __name__ == "__main__":
    main()
