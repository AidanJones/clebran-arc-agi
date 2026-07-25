"""Build the (state, action, next_state) trace dataset.

Runs every Hodel reference solver through clebran's deterministic
interpreter in single-step trace mode, and writes one JSONL row per
trace step to ``data/traces.jsonl``.

Each row is::

    {
      "task_id":   "<arc task id>",
      "input_idx": <0-based index into the demo pairs>,
      "step_index": <0-based index into the program statements>,
      "state":      <grid before the step>,
      "action": {
        "fn":        <primitive name>,
        "arg_kinds": [<arg kind encoding>...]
      },
      "next_state": <grid after the step>,
      "program_len": <total statements in the program>
    }

``arg_kinds`` is a list of compact strings — one of:

    "in"          input grid (Hodel's ``I``)
    "reg:N"       reference to register N (Hodel's ``x1`` etc.)
    "const:NAME"  a constant from arc-dsl/constants.py
    "prim:NAME"   a primitive passed as a first-class value

A learned L1 predictor (state, action) -> next_state can be trained
directly on this dataset. The clebran interpreter is a perfect oracle
for it; the *learned* version is a compression / generalisation
experiment.

Usage::

    uv run python scripts/build_traces.py
    uv run python scripts/build_traces.py --out data/traces.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Make sure we run from the repo root regardless of cwd.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from clebran.data.loader import load_task  # noqa: E402
from clebran.dsl.interpreter import ExecutionError, run_trace  # noqa: E402
from clebran.dsl.solver_parse import parse_all_solvers  # noqa: E402


def _arg_kind(arg: tuple) -> str:
    """Compact string form of a parsed arg tuple (kind, payload)."""
    kind, payload = arg
    if kind == "in":
        return "in"
    if kind == "reg":
        return f"reg:{payload}"
    if kind == "const":
        return f"const:{payload}"
    if kind == "prim":
        return f"prim:{payload}"
    return f"unknown:{kind}:{payload}"


def _grid_to_list(grid) -> list[list[int]]:
    """Convert a grid (tuple-of-tuples) to a JSON-friendly list of lists."""
    return [list(row) for row in grid]


def _serialise_register(value) -> dict:
    """Serialise a register value, recording its type and a JSON-friendly payload.

    Register values in the clebran IR are typed: grids (tuples of tuples of
    ints), ints, tuples of grids, frozensets of grid patches, etc. The
    serialised form is::

        {
          "kind":  "grid" | "int" | "tuple" | "other",
          "grid":  [[...]]  (only if kind == "grid")
          "int":   <int>    (only if kind == "int")
          "size":  <len>    (only if kind in {"tuple", "other"})
        }
    """
    if isinstance(value, tuple) and value and all(
        isinstance(row, tuple) and all(isinstance(c, int) for c in row) for row in value
    ):
        return {"kind": "grid", "grid": _grid_to_list(value)}
    if isinstance(value, int) and not isinstance(value, bool):
        return {"kind": "int", "int": value}
    if isinstance(value, (tuple, list, frozenset, set)):
        return {"kind": "tuple", "size": len(value)}
    return {"kind": "other"}


def _build_one(task_id: str, prog, input_idx: int, input_grid, fh) -> int:
    """Run one (task, demo-pair) and append trace steps to fh. Returns #steps."""
    n_steps = 0
    try:
        regs = run_trace(prog, input_grid)
    except ExecutionError as e:
        print(f"  [skip {task_id}#{input_idx}] execution error: {e}")
        return 0
    except Exception as e:  # noqa: BLE001
        print(f"  [skip {task_id}#{input_idx}] unexpected: {type(e).__name__}: {e}")
        return 0

    # The "state" for the k-th step is the previous register (or the input
    # grid for k=0). We serialise it as a typed register; the consumer can
    # decide how to encode non-grid registers (which are common — e.g. an
    # `objects(I, ...)` call returns a tuple of patches, not a grid).
    for k, reg_value in enumerate(regs):
        prev_value = input_grid if k == 0 else regs[k - 1]
        stmt = prog.statements[k]
        # stmt.fn is an Arg tuple like ("prim", "vmirror") — the head of the
        # statement. Unwrap it the same way we unwrap the args.
        head_kind, head_name = stmt.fn
        row = {
            "task_id": task_id,
            "input_idx": input_idx,
            "step_index": k,
            "state": _serialise_register(prev_value),
            "action": {
                "fn": head_name,
                "fn_kind": head_kind,            # "prim" | "reg" | "abstr"
                "arg_kinds": [_arg_kind(a) for a in stmt.args],
            },
            "next_state": _serialise_register(reg_value),
            "program_len": len(regs),
        }
        fh.write(json.dumps(row) + "\n")
        n_steps += 1
    return n_steps


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "data" / "traces.jsonl",
        help="Output JSONL path (default: data/traces.jsonl)",
    )
    ap.add_argument(
        "--tasks",
        type=str,
        default=None,
        help="Optional comma-separated list of task IDs to include (debug).",
    )
    args = ap.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)

    print(f"loading Hodel solvers from clebran/dsl/_vendor/solvers.py ...")
    t0 = time.time()
    progs = parse_all_solvers()
    print(f"  parsed {len(progs)} solvers in {time.time() - t0:.1f}s")

    if args.tasks:
        keep = set(t.strip() for t in args.tasks.split(","))
        progs = {tid: p for tid, p in progs.items() if tid in keep}
        print(f"  filtered to {len(progs)} tasks")

    n_tasks = 0
    n_pairs = 0
    n_steps = 0
    n_skipped = 0
    t0 = time.time()
    with args.out.open("w", encoding="utf-8") as fh:
        for task_id, prog in progs.items():
            try:
                task = load_task("training", task_id)
            except FileNotFoundError:
                n_skipped += 1
                continue
            n_tasks += 1
            n_pairs += len(task.train)
            for i, (inp, _out) in enumerate(task.train):
                n_steps += _build_one(task_id, prog, i, inp, fh)
            if n_tasks % 50 == 0:
                rate = n_steps / max(time.time() - t0, 1e-6)
                print(
                    f"  [{n_tasks:>3}/{len(progs)} tasks] "
                    f"{n_pairs} pairs, {n_steps} steps "
                    f"({rate:.0f} steps/s)"
                )

    size_kb = args.out.stat().st_size / 1024
    print()
    print(f"wrote {args.out} ({size_kb:,.1f} KB)")
    print(
        f"  tasks used:  {n_tasks} / {len(progs)} parsed"
        f"  (skipped {n_skipped} with missing training files)"
    )
    print(f"  demo pairs:  {n_pairs}")
    print(f"  trace steps: {n_steps}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
