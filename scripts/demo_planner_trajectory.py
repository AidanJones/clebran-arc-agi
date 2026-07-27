"""Generate a small L2 planner trajectory for a simple ARC task.

Picks a task from the trace dataset, runs the L2 planner on it, and
prints the resulting step-by-step state transitions in a format
suitable for embedding in the paper. The output is a list of
``(step, state, action, distance)`` tuples.

This is a *demo* script — its output is meant to be pasted into
the paper, not run as part of the test suite. Use it via:
    uv run python scripts/demo_planner_trajectory.py [task_id]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from clebran.world_model.l2_planner import (
    L2Planner, _grid_hamming,
)


def fmt_grid(grid, max_rows=8, max_cols=10):
    """Format a grid as a list of strings, one per row."""
    if not grid:
        return "[]"
    rows = []
    for i, row in enumerate(grid):
        if i >= max_rows:
            rows.append(f"  ... ({len(grid) - max_rows} more rows)")
            break
        # Truncate wide grids.
        if len(row) > max_cols:
            row = list(row[:max_cols]) + ["…"]
        rows.append("  " + " ".join(f"{c:>2d}" for c in row))
    return "\n".join(rows)


def run_task(task_id):
    rows = [json.loads(l) for l in
            open("data/traces.jsonl", encoding="utf-8")]
    # Find the first demo pair (input_idx 0) for this task.
    task_rows = [r for r in rows
                 if r["task_id"] == task_id and r["input_idx"] == 0]
    if not task_rows:
        print(f"task {task_id!r} not found in trace dataset")
        return
    # The first step's state is the input grid.
    first = next((r for r in task_rows
                  if r["step_index"] == 0 and r["state"]["kind"] == "grid"),
                 None)
    if first is None:
        print(f"task {task_id!r} has no grid first step")
        return
    state = tuple(tuple(row) for row in first["state"]["grid"])
    # The last register (across all input_idx rows) is the target.
    target = None
    for r in task_rows:
        if r["next_state"]["kind"] == "grid":
            target = tuple(tuple(row) for row in r["next_state"]["grid"])
    if target is None:
        print(f"task {task_id!r} has no grid target")
        return
    # Run the planner.
    planner = L2Planner(distance="hamming", lookahead=1)
    print(f"=== Task {task_id} ===")
    print(f"input grid ({len(state)}x{len(state[0])}):")
    print(fmt_grid(state))
    print(f"\ntarget grid ({len(target)}x{len(target[0])}):")
    print(fmt_grid(target))
    print(f"\nidentity Hamming distance: {_grid_hamming(state, target)}")
    # Single-step planning.
    print("\n--- single-step planner ---")
    one = planner.plan(state, target)
    if one["primitive"] is None:
        print("(no candidate improves over identity)")
    else:
        print(f"chosen primitive: {one['primitive']!r} {one['args']}")
        print(f"next state:")
        print(fmt_grid(one["next_state"]))
        print(f"distance: {one['distance']}")
    # Iterative planning.
    print("\n--- iterative planner (max 20 steps) ---")
    out = planner.plan_iteratively(state, target, max_steps=20)
    for i, step in enumerate(out["trace"]):
        print(f"\nstep {i+1}:")
        print(f"  state:")
        print(fmt_grid(step["state"]))
        if step["primitive"] is None:
            print("  (planner can't improve)")
            break
        print(f"  chosen primitive: {step['primitive']!r}")
        print(f"  next state:")
        print(fmt_grid(step["next_state"]))
        print(f"  distance to target: {step['distance']}")
        if step["distance"] == 0:
            print("  ✓ SOLVED")
            break
    print(f"\nfinal state solved: {out['solved']}")


if __name__ == "__main__":
    task_id = sys.argv[1] if len(sys.argv) > 1 else "f76d97a5"
    run_task(task_id)
