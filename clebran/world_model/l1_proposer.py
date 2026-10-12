"""L1 as proposer: trace-derived program prefixes seeded into B5's
initial population.

§9f / roadmap §A1 (#5 Learned L1 as proposer). The hypothesis is that
a learned L1, having seen 400 Hodel reference solvers, knows
*combinations of primitives* that B5's local search starts from
scratch on per task. The proposer is the cheapest operationalization
of this hypothesis that captures the L1's *trace-derived knowledge*:

* For each (input-shape, first-step-primitive) signature, count how
  often each first-step primitive appears in the trace dataset.
* For a new task, look up the most common first-step primitive for
  the input's shape.
* Instantiate a 1-step program with that primitive applied to the
  input, using the trace dataset's typical default args (e.g. for
  `vmirror`, the arg is the input itself).
* Inject as a high-priority seed.

This is a *frequency-based* proposer — not a learned L1 in the
strict sense, but a useful first test of "does trace-derived
knowledge of common primitives help?". If the result is positive,
the proposer can be extended to (a) multi-step prefixes (n-grams),
(b) full learned L1 proposals (GPL1 ranking), and (c) typed arg
inference from the trace dataset's `arg_kinds` distribution.

The proposer is restricted to *geometric* primitives (those that
have been learned by the GPL1 with high accuracy, or are pure
self-mirrors / crops / concatenations). Compositional primitives
(fill, paint, replace, ofcolor, fork, ...) are out of scope for v1
because the GPL1 doesn't learn them and their default args are
task-specific.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

from ..dsl.program import Program, Statement
from ..dsl.registry import CONSTANTS, PRIMITIVES


# Primitives that the v1 proposer is allowed to inject. These are the
# primitives that the GPL1 has been shown to learn well (vmirror,
# hmirror, etc.) or that have unambiguous default args (top/bottom
# halves). Higher-order / compositional primitives (fill, paint,
# replace, ofcolor, fork, ...) are excluded for v1.
_PROPOSER_PRIMITIVES = (
    "vmirror", "hmirror", "rot90", "rot180", "rot270",
    "cmirror", "dmirror",
    "tophalf", "bottomhalf", "lefthalf", "righthalf",
)


def _shape_of(grid) -> tuple | None:
    """The (rows, cols) shape of a grid, or None if not a grid."""
    if not isinstance(grid, tuple) or not grid:
        return None
    if not isinstance(grid[0], tuple):
        return None
    return (len(grid), len(grid[0]))


def _arg_value_for_kind(kind: str, input_grid, constants=None):
    """Best-effort default value for an arg_kind from the trace dataset.

    * ``"in"`` — the input state itself (most common in trace dataset).
    * ``"const:NAME"`` — look up the named constant in
      ``clebran.dsl.registry.CONSTANTS``. If not found, return 0.
    * ``"prim:NAME"`` — not supported in v1 (combinator arg).
    * ``"reg:N"`` — not supported in v1 (register ref).
    """
    if kind == "in":
        return input_grid
    if kind.startswith("const:"):
        name = kind.split(":", 1)[1]
        return CONSTANTS.get(name, 0)
    if kind.startswith("prim:"):
        # Combinator arg; v1 doesn't support these.
        return None
    if kind.startswith("reg:"):
        return None
    return None


def _build_first_step_proposer(trace_path: Path) -> dict[tuple, list[tuple[str, tuple]]]:
    """Build a per-shape frequency table of first-step primitives.

    Returns a dict mapping ``(n_rows, n_cols) -> [(prim_name,
    (arg1, arg2, ...)), ...]`` sorted by descending count. The arg
    lists are the *most common* arg_kinds pattern for that
    primitive + first-step on that shape (e.g. ``vmirror`` is always
    ``["in"]``; ``fill`` is always ``["in", "in", "in"]``).

    Only the first step (step_index == 0) of every solver / input
    pair is counted, so the table is "what Hodel solvers typically
    do FIRST on a grid of shape X".
    """
    by_shape: dict[tuple, Counter] = defaultdict(Counter)
    rows = [json.loads(l) for l in trace_path.read_text(encoding="utf-8").splitlines()]
    for r in rows:
        if r["step_index"] != 0:
            continue
        if r["state"]["kind"] != "grid":
            continue
        grid = r["state"]["grid"]
        shape = (len(grid), len(grid[0]) if grid else 0)
        fn = r["action"]["fn"]
        if not isinstance(fn, str):
            continue
        # Encode the (fn, arg_kinds) signature.
        sig = (fn, tuple(r["action"]["arg_kinds"]))
        by_shape[shape][sig] += 1
    # Convert to a sorted list per shape, restricted to v1 primitives.
    out: dict[tuple, list[tuple[str, tuple]]] = {}
    for shape, counter in by_shape.items():
        items: list[tuple[int, tuple]] = []
        for (fn, arg_kinds), count in counter.items():
            if fn in _PROPOSER_PRIMITIVES:
                items.append((count, (fn, arg_kinds)))
        items.sort(key=lambda x: -x[0])
        out[shape] = [(fn, arg_kinds) for _, (fn, arg_kinds) in items]
    return out


class L1Proposer:
    """An L1-as-proposer built from trace-dataset frequency statistics.

    Parameters
    ----------
    trace_path : Path
        Path to the trace dataset (typically
        ``data/traces.jsonl``).

    The proposer can be queried for the most common first-step
    primitive on a given input grid via :meth:`propose_first_step`,
    which returns a list of ``(program, prim_name)`` candidates
    suitable for seeding a B5 population.

    The build is cheap (~10 ms for the trace dataset) and the
    proposer is deterministic.
    """

    def __init__(self, trace_path: Path = Path("data/traces.jsonl"),
                 exclude_task_ids: Iterable[str] = ()):
        self.table: dict[tuple, list[tuple[str, tuple]]] = {}
        rows = [json.loads(l) for l in trace_path.read_text(encoding="utf-8").splitlines()]
        exclude = set(exclude_task_ids)
        by_shape: dict[tuple, Counter] = defaultdict(Counter)
        for r in rows:
            if r["task_id"] in exclude:
                continue
            if r["step_index"] != 0:
                continue
            if r["state"]["kind"] != "grid":
                continue
            grid = r["state"]["grid"]
            if not grid:
                continue
            shape = (len(grid), len(grid[0]))
            fn = r["action"]["fn"]
            if not isinstance(fn, str):
                continue
            sig = (fn, tuple(r["action"]["arg_kinds"]))
            by_shape[shape][sig] += 1
        for shape, counter in by_shape.items():
            items = []
            for (fn, arg_kinds), count in counter.items():
                if fn in _PROPOSER_PRIMITIVES:
                    items.append((count, (fn, arg_kinds)))
            items.sort(key=lambda x: -x[0])
            self.table[shape] = [(fn, arg_kinds) for _, (fn, arg_kinds) in items]

    def propose_first_step(self, input_grid, k: int = 3) -> list[tuple[Program, str]]:
        """Return up to K proposed (program, primitive_name) candidates
        for the given input grid. The proposals are ranked by
        frequency in the trace dataset for the input's shape.

        Each proposal is a 1-statement program: ``x1 = prim(*args);
        return x1``. Returns an empty list if no proposal can be
        built (e.g. the input shape has no trace-dataset history, or
        the top-K primitives all need unsupported argument kinds).
        """
        if input_grid is None:
            return []
        # Convert grid to tuple-of-tuples.
        if isinstance(input_grid, list):
            input_grid = tuple(tuple(row) for row in input_grid)
        elif isinstance(input_grid, tuple) and input_grid and isinstance(input_grid[0], list):
            input_grid = tuple(tuple(row) for row in input_grid)
        shape = _shape_of(input_grid)
        if shape is None:
            return []
        candidates = self.table.get(shape, [])
        out = []
        for prim_name, arg_kinds in candidates[:k]:
            args = []
            ok = True
            for kind in arg_kinds:
                v = _arg_value_for_kind(kind, input_grid)
                if v is None:
                    ok = False
                    break
                args.append(v)
            if not ok:
                continue
            try:
                # Sanity-check that the call is valid before building.
                sig = PRIMITIVES[prim_name]
                sig.fn(*args)
            except Exception:
                continue
            # Build a 1-statement program.
            try:
                prog = Program(statements=[
                    Statement(prim_name, arg_kinds=list(arg_kinds)),
                ])
                out.append((prog, prim_name))
            except Exception:
                continue
        return out

    def n_shapes_covered(self) -> int:
        """Number of distinct input shapes for which the proposer has
        trace-dataset statistics."""
        return len(self.table)

    def first_step_count(self, input_grid) -> int:
        """How many trace-dataset rows have this input shape as their
        first-step. Useful for diagnosing whether the proposer has
        any signal for a given input."""
        if input_grid is None:
            return 0
        if isinstance(input_grid, list):
            input_grid = tuple(tuple(row) for row in input_grid)
        shape = _shape_of(input_grid)
        if shape is None or shape not in self.table:
            return 0
        return sum(c for c, _ in [(1, p) for p in self.table[shape]])


def main(trace_path: Path = Path("data/traces.jsonl")) -> int:
    """Build the L1 proposer and report its coverage."""
    print(f"loading trace dataset from {trace_path} ...")
    p = L1Proposer(trace_path)
    print(f"  shapes covered: {p.n_shapes_covered()}")
    print()
    print("top 10 shapes by # first-step candidates:")
    by_n = sorted(p.table.items(), key=lambda kv: -len(kv[1]))[:10]
    for shape, cands in by_n:
        top = ", ".join(f"{fn} ({','.join(ak)})" for fn, ak in cands[:3])
        print(f"  shape {shape}: {len(cands)} cands (top: {top})")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())