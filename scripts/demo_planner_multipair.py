"""Run the L2 planner on a task's demo pairs (multi-pair) and
print the resulting program. Used to extract planner-seeded
program structure for the paper."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from clebran.world_model.l2_planner import L2Planner, _grid_hamming
from clebran.data.loader import load_task


def fmt_program(prog) -> str:
    """Format a clebran Program as IR text."""
    out = []
    for stmt in prog.statements:
        head = stmt.fn
        head_str = head[1] if head[0] == "prim" else repr(head)
        arg_strs = []
        for a in stmt.args:
            if a[0] == "in":
                arg_strs.append("I")
            elif a[0] == "reg":
                arg_strs.append(f"x{a[1]}")
            elif a[0] == "const":
                arg_strs.append(a[1])
            elif a[0] == "lit":
                arg_strs.append(repr(a[1]))
            else:
                arg_strs.append(repr(a))
        out.append(f"  {head_str}({', '.join(arg_strs)})")
    return "\n".join(out)


def main():
    task_id = sys.argv[1] if len(sys.argv) > 1 else "f76d97a5"
    t = load_task("training", task_id)
    demos = [(tuple(tuple(row) for row in inp),
              tuple(tuple(row) for row in out))
             for inp, out in t.train]
    print(f"=== Task {task_id} ({len(demos)} demos) ===")
    for i, (inp, out) in enumerate(demos[:3]):
        print(f"\ndemo {i}: input {len(inp)}x{len(inp[0])}, "
              f"target {len(out)}x{len(out[0])}")
        print(f"  input:")
        for row in inp[:6]:
            print(f"   {row}")
        if len(inp) > 6:
            print(f"   ... ({len(inp)} rows total)")
        print(f"  target:")
        for row in out[:6]:
            print(f"   {row}")
        if len(out) > 6:
            print(f"   ... ({len(out)} rows total)")
    print()
    # Multi-pair planning.
    p = L2Planner(lookahead=1)
    out = p.plan_to_program(demos, max_steps=20)
    print(f"planner-seeded program ({len(out['program'].statements)} statements):")
    print(fmt_program(out["program"]))
    print(f"\nsolved: {out['solved']}")
    print(f"final distances: {out['final_distances']}")
    if out["trace"]:
        last_step = out["trace"][-1]
        print(f"last step distance: {last_step['distance']:.2f}")


if __name__ == "__main__":
    main()
