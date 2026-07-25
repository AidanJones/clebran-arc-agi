"""Multi-pair evaluation of the L2 planner.

This is the metric that matters for the B5+planner arm: for each
task, the planner plans against ALL of the task's demo pairs
simultaneously (not just the first one), and we report the
iterative solve rate (the fraction of tasks where the planner
reaches the target on every demo).

This is a much stricter test than the single-pair evaluation in
``clebran/world_model/l2_planner.py::evaluate``: the planner has
to find a program that works on every demo, not just one.

Usage::

    uv run python scripts/evaluate_planner_multipair.py
    uv run python scripts/evaluate_planner_multipair.py --lookahead 2
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from clebran.world_model.l2_planner import L2Planner, _grid_hamming


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--traces", type=Path,
                    default=REPO_ROOT / "data" / "traces.jsonl")
    ap.add_argument("--max-steps", type=int, default=20)
    ap.add_argument("--lookahead", type=int, default=1)
    ap.add_argument("--distance", default="hamming",
                    choices=["hamming", "component", "color_set", "structural"])
    args = ap.parse_args()

    rows = [json.loads(l) for l in args.traces.read_text(encoding="utf-8").splitlines()]
    print(f"loaded {len(rows):,} rows from {args.traces}")

    # Group rows by (task_id, input_idx). For each task, we want
    # the (input, target) of each demo. The Hodel traces include
    # one row per (task_id, input_idx, step_index) triple; the
    # *input* of a task's first demo is at step_index=0, and the
    # *target* is the last row's next_state (the solver's final
    # output).
    by_task: dict[str, dict[int, dict]] = defaultdict(dict)
    for r in rows:
        tid = r["task_id"]
        iidx = r["input_idx"]
        # The input is at step_index=0.
        if r["step_index"] == 0 and r["state"]["kind"] == "grid":
            by_task[tid].setdefault(iidx, {})["input"] = r["state"]
        # The target is the last row's next_state (a grid).
        if r["next_state"]["kind"] == "grid":
            by_task[tid].setdefault(iidx, {})["target"] = r["next_state"]

    # Build (input, target) demo lists per task.
    task_demos: dict[str, list[tuple]] = {}
    for tid, demos in by_task.items():
        demos_list: list[tuple] = []
        for iidx, info in demos.items():
            if "input" in info and "target" in info:
                inp = tuple(tuple(r) for r in info["input"]["grid"])
                tgt = tuple(tuple(r) for r in info["target"]["grid"])
                demos_list.append((inp, tgt))
        if demos_list:
            task_demos[tid] = demos_list

    n_tasks = len(task_demos)
    n_total_demos = sum(len(d) for d in task_demos.values())
    print(f"  tasks: {n_tasks}, total demos: {n_total_demos}")
    print()

    planner = L2Planner(lookahead=args.lookahead, distance=args.distance)

    n_solved = 0
    n_partial = 0
    n_no_program = 0
    n_total_steps = 0
    n_with_finite_demos = 0
    for tid, demos in task_demos.items():
        # Filter to demos that are grid→grid with the same shape
        # (the planner only handles those).
        finite_demos = []
        for st, tg in demos:
            d = _grid_hamming(st, tg)
            if d != float("inf"):
                finite_demos.append((st, tg))
        if not finite_demos:
            continue
        n_with_finite_demos += 1
        result = planner.plan_to_program(finite_demos,
                                         max_steps=args.max_steps)
        n_total_steps += len(result["trace"])
        if result["solved"]:
            n_solved += 1
        elif len(result["trace"]) > 0:
            n_partial += 1
        else:
            n_no_program += 1

    print(f"  distance:                       {args.distance}")
    print(f"  lookahead:                      {args.lookahead}")
    print(f"  finite-shape tasks evaluated: {n_with_finite_demos}")
    print(f"  planner solves (all demos exactly): "
          f"{n_solved} / {n_with_finite_demos} "
          f"= {n_solved/n_with_finite_demos:.1%}"
          if n_with_finite_demos else "  none")
    print(f"  planner partial (some progress but not solved): "
          f"{n_partial}")
    print(f"  planner no-program (couldn't find any candidate): "
          f"{n_no_program}")
    print(f"  mean steps per task: "
          f"{n_total_steps/n_with_finite_demos:.1f}"
          if n_with_finite_demos else "  n/a")


if __name__ == "__main__":
    raise SystemExit(main())
