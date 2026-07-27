"""Find a multi-step L2 planner trajectory to use as a paper example."""
from __future__ import annotations
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from clebran.world_model.l2_planner import L2Planner, _grid_hamming


def main():
    rows = [json.loads(l) for l in
            open("data/traces.jsonl", encoding="utf-8")]
    # Group by (task_id, input_idx).
    pairs = {}
    for r in rows:
        key = (r["task_id"], r["input_idx"])
        pairs.setdefault(key, []).append(r)

    # Find candidates with Hodel programs of length 2-4 and shape 3-5.
    candidates = []
    for (tid, iidx), pair_rows in pairs.items():
        program_len = max(r["program_len"] for r in pair_rows)
        first = next((r for r in pair_rows
                      if r["step_index"] == 0 and r["state"]["kind"] == "grid"),
                     None)
        if first is None:
            continue
        s = first["state"]["grid"]
        h, w = len(s), len(s[0]) if s else 0
        if 3 <= h <= 5 and 3 <= w <= 5 and 2 <= program_len <= 4:
            candidates.append((tid, iidx, program_len, h, w))

    # Try each candidate; pick the first that the planner solves in 2-4 steps.
    for tid, iidx, plen, h, w in candidates[:30]:
        pair_rows = pairs[(tid, iidx)]
        first = next((r for r in pair_rows
                      if r["step_index"] == 0 and r["state"]["kind"] == "grid"),
                     None)
        state = tuple(tuple(row) for row in first["state"]["grid"])
        target = None
        for r in pair_rows:
            if r["next_state"]["kind"] == "grid":
                target = tuple(tuple(row) for row in r["next_state"]["grid"])
        if target is None:
            continue
        if _grid_hamming(state, target) == 0:
            continue
        p = L2Planner(lookahead=1)
        out = p.plan_iteratively(state, target, max_steps=10)
        if out["solved"] and 1 < len(out["trace"]) <= 4:
            print(f"task {tid} (input {iidx}, program_len {plen}, "
                  f"shape {h}x{w}, {len(out['trace'])} steps)")
            print(f"  primitives: "
                  f"{[s['primitive'] for s in out['trace']]}")


if __name__ == "__main__":
    main()
