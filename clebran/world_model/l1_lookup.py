"""Lookup-table L1: a perfect-L1 cache for the clebran world model.

The lookup-table L1 is the simplest possible "learned" L1: at
construction, build a hash table mapping ``(state, action)`` →
``next_state`` from the trace dataset. At predict time, do a
dict lookup. On miss, fall back to the perfect L1 (the clebran
interpreter).

This is the *memorisation upper bound* for any L1 that is
restricted to the trace dataset's distribution. The interesting
question for the comparison is:

* **Hit rate on the test set** — how much of the test set was
  seen in training? A high hit rate means the trace dataset
  generalises across the frontier subset; a low hit rate means
  the L1 has to fall back to the slow perfect L1.
* **Speed-up at predict time** — at 100% hit rate, a dict lookup
  is ~1000× faster than the interpreter. At 0% hit rate, the
  lookup table adds a hash overhead and is *slower* than the
  interpreter alone.

**No generalisation.** A lookup-table L1 with a hash on the full
state is a *memoriser*, not a learner: it cannot predict on
unseen states. The k-NN L1 is a partial fix (it can match
near-duplicate states), and the GP-evolved L1 is a more
ambitious fix (it can match a primitive's behaviour in
closed-form).

**Hash key.** We hash on the *full* state tuple (not just the
shape) for grid→grid transitions, and on (None, action) for
non-grid rows. The full state hash gives a true memoriser; a
shape-only hash would be a lossy cache.
"""
from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path
from typing import Iterable

from ..dsl.registry import PRIMITIVES


# ----- helpers ------------------------------------------------------------

def _grid_key(grid: list[list[int]] | tuple) -> tuple | None:
    """Hashable key for a grid. Returns None for non-grid states."""
    if grid is None:
        return None
    if isinstance(grid, tuple):
        return grid
    return tuple(tuple(row) for row in grid)


def _action_key(action: dict) -> tuple:
    """Hashable key for an action: (fn, arg_kinds)."""
    return (action["fn"], tuple(action["arg_kinds"]))


def _row_key(row: dict) -> tuple | None:
    """Hashable key for a row's (state, action). Returns None if
    the state isn't hashable (e.g. the row has a non-grid, non-int
    state — we only handle grid→grid for the L1 lookup)."""
    state = row["state"]
    if state["kind"] != "grid":
        return None
    state_key = _grid_key(state["grid"])
    if state_key is None:
        return None
    return (state_key, _action_key(row["action"]))


def _next_state_key(row: dict) -> dict:
    """The serialised next_state for storage / comparison."""
    return row["next_state"]


# ----- the L1 -------------------------------------------------------------

class LookupTableL1:
    """A lookup-table L1: a perfect cache over the training rows.

    Parameters
    ----------
    rows : list of dict
        Training rows from the trace dataset. Each row must have
        ``state.kind == "grid"`` and ``next_state.kind == "grid"``
        to be cached.
    fallback : callable or None
        A function ``(state, action) -> next_state`` called when
        the lookup misses. If None, a miss raises KeyError (the
        caller is expected to handle misses by either calling
        the perfect L1 itself or marking the prediction as
        "unknown").

    The class is intentionally minimal: it provides ``predict``,
    a hit/miss counter, and a speed benchmark. There is no
    notion of "training" beyond the initial dict build.
    """

    def __init__(self, rows: Iterable[dict], fallback=None):
        self.table: dict[tuple, dict] = {}
        self.fallback = fallback
        # Track which keys are ambiguous (multiple training rows
        # for the same (state, action) but different next_states).
        # This is rare but possible: the trace dataset is built
        # from 400 different tasks, and the same primitive can
        # produce different outputs on different inputs.
        self._n_inserts = 0
        self._n_collisions = 0
        self._n_hits = 0
        self._n_misses = 0
        for r in rows:
            key = _row_key(r)
            if key is None:
                continue
            ns = _next_state_key(r)
            if key in self.table:
                # Don't replace the existing entry; just count it
                # as a collision (the first one wins). This makes
                # the table a deterministic cache.
                self._n_collisions += 1
            else:
                self.table[key] = ns
                self._n_inserts += 1

    def predict(self, state_grid, action: dict):
        """Return the cached next_state for the (state, action) pair,
        or call the fallback if no entry exists.

        ``state_grid`` is a list-of-lists or tuple-of-tuples.
        ``action`` is a dict ``{fn, fn_kind, arg_kinds}``.
        """
        key = (_grid_key(state_grid), _action_key(action))
        if key in self.table:
            self._n_hits += 1
            return self.table[key]
        self._n_misses += 1
        if self.fallback is not None:
            return self.fallback(state_grid, action)
        raise KeyError(
            f"LookupTableL1: no entry for action {action!r} and "
            f"given state; provide a fallback to handle misses."
        )

    @property
    def n_rows(self) -> int:
        return self._n_inserts

    @property
    def n_collisions(self) -> int:
        return self._n_collisions

    @property
    def hit_rate(self) -> float:
        total = self._n_hits + self._n_misses
        return self._n_hits / total if total else 0.0

    def reset_counters(self) -> None:
        """Reset the hit/miss counters (useful for benchmarks)."""
        self._n_hits = 0
        self._n_misses = 0

    def benchmark(self, test_rows: list[dict], n_repeats: int = 3,
                  also_benchmark_fallback: bool = True) -> dict:
        """Measure predict-time speed on ``test_rows``.

        Returns a dict with:
          * ``hits`` / ``misses`` / ``hit_rate`` — coverage of the
            test set in the cached rows.
          * ``lookup_time_us`` — mean per-row time, in microseconds,
            averaged over ``n_repeats`` runs (best of n_repeats).
          * ``fallback_time_us`` — mean per-row time when the
            lookup misses and the fallback is called (perfect L1).
            Only present if ``also_benchmark_fallback``.
          * ``speedup`` — fallback_time / lookup_time. >1.0 means
            the lookup is faster than the fallback.
        """
        # Restrict to grid→grid test rows (the lookup only handles those).
        test = [r for r in test_rows
                if r["state"]["kind"] == "grid"
                and r["next_state"]["kind"] == "grid"]
        # Pre-extract state grids + actions so the timing loop is
        # pure lookup work.
        queries = []
        for r in test:
            queries.append((
                tuple(tuple(row) for row in r["state"]["grid"]),
                (r["action"]["fn"], tuple(r["action"]["arg_kinds"])),
            ))
        # Run the timing loop. We use time.perf_counter_ns() for
        # sub-microsecond resolution; for very fast lookups the
        # call overhead would otherwise dominate.
        best_us = float("inf")
        for _ in range(n_repeats):
            self.reset_counters()
            t0 = time.perf_counter_ns()
            for state_key, action_key in queries:
                _ = self.table.get((state_key, action_key))
            t1 = time.perf_counter_ns()
            elapsed_us = (t1 - t0) / 1000.0
            if elapsed_us < best_us:
                best_us = elapsed_us
        per_row_us = best_us / max(1, len(queries))
        out = {
            "n_test_rows": len(test),
            "hits": self._n_hits,
            "misses": self._n_misses,
            "hit_rate": self.hit_rate,
            "lookup_time_us": per_row_us,
            "predictions_per_sec": 1e6 / per_row_us if per_row_us else 0.0,
        }
        if also_benchmark_fallback and self.fallback is not None:
            fb_best = float("inf")
            for _ in range(n_repeats):
                t0 = time.perf_counter_ns()
                for r in test:
                    state = tuple(tuple(row) for row in r["state"]["grid"])
                    _ = safe_perfect_l1(state, r["action"])
                t1 = time.perf_counter_ns()
                elapsed_us = (t1 - t0) / 1000.0
                if elapsed_us < fb_best:
                    fb_best = elapsed_us
            out["fallback_time_us"] = fb_best / max(1, len(test))
            out["speedup"] = (
                out["fallback_time_us"] / per_row_us if per_row_us else 0.0
            )
        return out


# ----- the perfect L1 fallback -------------------------------------------

def perfect_l1_fallback(state_grid, action: dict) -> dict:
    """The perfect L1: call the clebran primitive on the state.

    Restricted to actions with all-`in`/constant args (no register
    references). Mirrors the constraint in ``InterpreterL1.predict``.

    The default-arg strategies match the L2 planner's
    ``_default_candidates`` function: 1-arg primitives take the
    state directly, scaling primitives take factor=2, fill takes
    ``(state, 0, state)`` (which clears the state), paint takes
    ``(state, ((0, 0),), mc)`` (paint the origin), and replace
    takes ``(state, mc, 0)`` (replace the most common color with
    background). The L2 planner also has a few other variants
    (vconcat with self/mirror) that this fallback omits for speed.
    """
    fn_name = action["fn"]
    if action.get("fn_kind") != "prim":
        raise NotImplementedError(
            f"perfect_l1_fallback only handles prim heads, got "
            f"{action.get('fn_kind')!r}"
        )
    sig = PRIMITIVES[fn_name]
    from .l2_planner import _most_common_color
    mc = _most_common_color(state_grid)
    if sig.arity == 1:
        return _serialize_result(sig.fn(state_grid))
    if sig.arity == 2:
        if fn_name in ("downscale", "hupscale", "upscale"):
            return _serialize_result(sig.fn(state_grid, 2))
        if fn_name in ("vconcat", "hconcat"):
            return _serialize_result(sig.fn(state_grid, state_grid))
        raise NotImplementedError(
            f"perfect_l1_fallback: 2-arg primitive {fn_name!r} "
            f"not in the default-arg table"
        )
    if sig.arity == 3:
        if fn_name == "paint":
            return _serialize_result(sig.fn(state_grid, ((0, 0),), mc))
        if fn_name == "replace":
            return _serialize_result(sig.fn(state_grid, mc, 0))
        if fn_name == "switch":
            return _serialize_result(sig.fn(state_grid, mc, 0))
        if fn_name == "underpaint":
            return _serialize_result(sig.fn(state_grid, ((0, 0),), mc))
        raise NotImplementedError(
            f"perfect_l1_fallback: 3-arg primitive {fn_name!r} "
            f"not in the default-arg table"
        )
    raise NotImplementedError(
        f"perfect_l1_fallback: arity {sig.arity} not handled"
    )


def safe_perfect_l1(state_grid, action: dict):
    """A version of ``perfect_l1_fallback`` that catches all
    exceptions and returns ``None`` on error. Useful for the
    benchmark, where we want to time the *successful* interpreter
    call path, not the error path.
    """
    try:
        return perfect_l1_fallback(state_grid, action)
    except Exception:
        return None


def _serialize_result(value) -> dict:
    """Convert a clebran primitive result into the serialised
    ``{kind, ...}`` form used by the trace dataset."""
    if isinstance(value, tuple) and value and isinstance(value[0], tuple):
        return {"kind": "grid", "grid": [list(row) for row in value]}
    if isinstance(value, int):
        return {"kind": "int", "value": value}
    if isinstance(value, tuple):
        return {"kind": "tuple", "value": [list(v) if isinstance(v, tuple) else v
                                          for v in value]}
    return {"kind": "other"}


# ----- CLI entry point ----------------------------------------------------

def main(trace_path: Path = Path("data/traces.jsonl"),
         test_frac: float = 0.2, seed: int = 0) -> int:
    """Build a LookupTableL1 on the trace dataset's training split and
    report the test-set hit rate, speed, and accuracy."""
    print(f"loading trace dataset from {trace_path} ...")
    rows = [json.loads(l) for l in trace_path.read_text(encoding="utf-8").splitlines()]
    print(f"  loaded {len(rows):,} rows")
    # Train/test split by task (same convention as the KnnL1
    # evaluation in l1_baseline.py).
    import random
    rng = random.Random(seed)
    tasks = sorted(set(r["task_id"] for r in rows))
    rng.shuffle(tasks)
    cutoff = int(round(len(tasks) * test_frac))
    test_tasks = set(tasks[:cutoff])
    train = [r for r in rows if r["task_id"] not in test_tasks]
    test = [r for r in rows if r["task_id"] in test_tasks]
    print(f"  train rows: {len(train):,}, test rows: {len(test):,}")
    # Restrict to grid→grid rows.
    train_grid = [r for r in train
                  if r["state"]["kind"] == "grid"
                  and r["next_state"]["kind"] == "grid"]
    test_grid = [r for r in test
                 if r["state"]["kind"] == "grid"
                 and r["next_state"]["kind"] == "grid"]
    print(f"  train grid rows: {len(train_grid):,}, test grid rows: {len(test_grid):,}")
    # Build the lookup table.
    print()
    print("building LookupTableL1 ...")
    l1 = LookupTableL1(train_grid, fallback=safe_perfect_l1)
    print(f"  table size: {l1.n_rows:,} entries")
    print(f"  collisions (same key, different next_state): {l1.n_collisions}")
    # First pass: count hits/misses (without timing).
    print()
    print("hit/miss rates on test rows (held-out tasks):")
    n_total = len(test_grid)
    n_hits = 0
    n_misses = 0
    for r in test_grid:
        state = tuple(tuple(row) for row in r["state"]["grid"])
        key = (state, (r["action"]["fn"], tuple(r["action"]["arg_kinds"])))
        if key in l1.table:
            n_hits += 1
        else:
            n_misses += 1
    print(f"  hits:   {n_hits} / {n_total} = {n_hits/n_total:.2%}")
    print(f"  misses: {n_misses} / {n_total} = {n_misses/n_total:.2%}")
    # In-distribution accuracy: hold out 20% of training rows
    # (not tasks) and check exact-match on the held-out rows
    # against the table built from the rest. This is the
    # memorisation upper bound.
    print()
    print("in-distribution accuracy (held-out rows, same tasks):")
    from random import Random
    in_dist_rng = Random(seed)
    in_dist_held_out: list[dict] = []
    in_dist_rest: list[dict] = []
    held_out_ids: set = set()
    for r in train_grid:
        if in_dist_rng.random() < test_frac:
            held_out_ids.add(id(r))
            in_dist_held_out.append(r)
        else:
            in_dist_rest.append(r)
    in_dist_l1 = LookupTableL1(in_dist_rest, fallback=safe_perfect_l1)
    n_in_dist_total = len(in_dist_held_out)
    n_in_dist_exact = 0
    for r in in_dist_held_out:
        state = tuple(tuple(row) for row in r["state"]["grid"])
        truth = r["next_state"]
        pred = in_dist_l1.predict(state, r["action"])
        if pred == truth:
            n_in_dist_exact += 1
    print(f"  exact-match: {n_in_dist_exact} / {n_in_dist_total} = "
          f"{n_in_dist_exact/n_in_dist_total:.2%}")
    print(f"  (table size: {in_dist_l1.n_rows:,} entries from "
          f"{len(in_dist_rest):,} rest-rows)")
    # Benchmark.
    print()
    print("benchmarking on test rows (best of 3 runs) ...")
    bench = l1.benchmark(test_grid, n_repeats=3)
    for k, v in bench.items():
        if isinstance(v, float):
            print(f"  {k:>22s} = {v:.4f}")
        else:
            print(f"  {k:>22s} = {v}")
    # Accuracy on the test set.
    print()
    print("accuracy on test rows:")
    n_exact = 0
    n_shape = 0
    n_exact_on_hit = 0
    n_exact_on_miss = 0
    n_hits_for_acc = 0
    n_misses_for_acc = 0
    for r in test_grid:
        state = tuple(tuple(row) for row in r["state"]["grid"])
        truth = r["next_state"]
        # Determine if the lookup will hit or miss.
        key = (state, (r["action"]["fn"], tuple(r["action"]["arg_kinds"])))
        is_hit = key in l1.table
        pred = l1.predict(state, r["action"])
        if pred == truth:
            n_exact += 1
            if is_hit:
                n_exact_on_hit += 1
                n_hits_for_acc += 1
            else:
                n_exact_on_miss += 1
                n_misses_for_acc += 1
        else:
            if is_hit:
                n_hits_for_acc += 1
            else:
                n_misses_for_acc += 1
        if (pred is not None
                and pred.get("kind") == "grid" and truth.get("kind") == "grid"
                and len(pred.get("grid", [])) == len(truth.get("grid", []))
                and (not pred.get("grid") or
                     len(pred["grid"][0]) == len(truth["grid"][0]))):
            n_shape += 1
    print(f"  exact-match (overall):  {n_exact} / {n_total} = {n_exact/n_total:.2%}")
    print(f"  shape-match (overall):  {n_shape} / {n_total} = {n_shape/n_total:.2%}")
    if n_hits_for_acc:
        print(f"  exact-match on hits:    {n_exact_on_hit} / {n_hits_for_acc} = "
              f"{n_exact_on_hit/n_hits_for_acc:.2%}")
    if n_misses_for_acc:
        print(f"  exact-match on misses:  {n_exact_on_miss} / {n_misses_for_acc} = "
              f"{n_exact_on_miss/n_misses_for_acc:.2%}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
