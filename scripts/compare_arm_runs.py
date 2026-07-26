"""Compare B5 vs B5+planner at 4M on the frontier subset.

Reads the b5_seed*.jsonl and b5p_seed*.jsonl logs and produces a
side-by-side summary table. Use this after running the
``scripts/run_topk_sweep.sh`` (B5+planner) and
``scripts/run_b5_sweep.sh`` (B5) sweeps.

Usage:
    uv run python scripts/compare_arm_runs.py
"""
from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path


LOGS = Path("logs")


def collect_runs(pattern: str, arm: str) -> list[dict]:
    """Collect completed runs matching the glob pattern and arm name."""
    runs = []
    for log_path in sorted(LOGS.glob(pattern)):
        # Skip the backup files (e.g. ``b5p_seed1_k1_4M_run1.jsonl``)
        if "_k1_4M_run" in log_path.name:
            continue
        try:
            events = [json.loads(l) for l in
                      log_path.read_text(encoding="utf-8").splitlines()]
        except Exception:
            continue
        if not events:
            continue
        start = events[0]
        summary = events[-1]
        if start.get("event") != "start" or start.get("arm") != arm:
            continue
        if summary.get("event") != "summary":
            continue
        # Only include 4M-budget runs.
        if start.get("budget") != 4000000:
            continue
        # Normalize the field names: B5 logs use the older format
        # (solved=test_exact=count, solved_tasks=list); B5+planner
        # logs use the newer format (n_solved=count, n_test_exact=count,
        # solved=list).
        n_solved = (summary.get("n_solved")
                    if summary.get("n_solved") is not None
                    else summary.get("solved", 0))
        n_evo_solved = (summary.get("n_evo_solved")
                        if summary.get("n_evo_solved") is not None
                        else (len(summary.get("solved_evolution", []))
                              if isinstance(summary.get("solved_evolution"),
                                            (list, set))
                              else 0))
        n_test_exact = (summary.get("n_test_exact")
                        if summary.get("n_test_exact") is not None
                        else summary.get("test_exact", 0))
        mean_length = (summary.get("mean_solution_length")
                       if summary.get("mean_solution_length") is not None
                       else summary.get("mean_solution_len", 0.0))
        solved_tasks = sorted(summary.get("solved", [])
                             if isinstance(summary.get("solved"), list)
                             else sorted(summary.get("solved_tasks", [])
                                        if isinstance(summary.get("solved_tasks"),
                                                      (list, set))
                                        else []))
        runs.append({
            "seed": start.get("seed"),
            "K": start.get("planner_top_k", None),
            "n_solved": n_solved,
            "n_evo_solved": n_evo_solved,
            "n_test_exact": n_test_exact,
            "mean_length": mean_length,
            "solved_tasks": solved_tasks,
        })
    return runs


def summarise(runs: list[dict], arm_name: str) -> dict:
    if not runs:
        return {"arm": arm_name, "n": 0}
    n = len(runs)
    solved = [r["n_solved"] for r in runs]
    evo = [r["n_evo_solved"] for r in runs]
    texact = [r["n_test_exact"] for r in runs]
    lens = [r["mean_length"] for r in runs]
    all_tasks = set()
    for r in runs:
        all_tasks.update(r["solved_tasks"])
    return {
        "arm": arm_name,
        "n": n,
        "solved_mean": statistics.mean(solved),
        "solved_sd": statistics.stdev(solved) if n > 1 else 0.0,
        "evo_mean": statistics.mean(evo),
        "test_exact_mean": statistics.mean(texact),
        "mean_len_mean": statistics.mean(lens),
        "solved_per_seed": solved,
        "n_unique_tasks": len(all_tasks),
    }


def main():
    b5_runs = collect_runs("b5_seed*.jsonl", arm="B5")
    b5p_k1_runs = [r for r in collect_runs("b5p_seed*.jsonl", arm="B5P")
                    if r["K"] == 1]
    b5p_k3_runs = [r for r in collect_runs("b5pk3_seed*.jsonl", arm="B5P")
                    if r["K"] == 3]
    b5p_k5_runs = [r for r in collect_runs("b5pk5_seed*.jsonl", arm="B5P")
                    if r["K"] == 5]

    b5_sum = summarise(b5_runs, "B5 (control)")
    b5p_k1_sum = summarise(b5p_k1_runs, "B5+planner (K=1)")
    b5p_k3_sum = summarise(b5p_k3_runs, "B5+planner (K=3)")
    b5p_k5_sum = summarise(b5p_k5_runs, "B5+planner (K=5)")

    rows = [b5_sum, b5p_k1_sum, b5p_k3_sum, b5p_k5_sum]
    print(f"{'arm':>22s}  {'n':>3s}  {'solved':>14s}  {'evo':>6s}  "
          f"{'texact':>7s}  {'len':>5s}  {'unique':>7s}")
    print("-" * 80)
    for r in rows:
        if r["n"] == 0:
            print(f"{r['arm']:>22s}  {0:>3}  (no runs)")
            continue
        solved_str = f"{r['solved_mean']:5.2f} +/- {r['solved_sd']:4.2f}"
        print(f"{r['arm']:>22s}  {r['n']:>3}  {solved_str:>14s}  "
              f"{r['evo_mean']:>6.2f}  {r['test_exact_mean']:>7.2f}  "
              f"{r['mean_len_mean']:>5.2f}  {r['n_unique_tasks']:>7}")

    print()
    for r in rows:
        if r["n"] == 0:
            continue
        print(f"{r['arm']}: solved per seed = {r['solved_per_seed']}")


if __name__ == "__main__":
    main()
