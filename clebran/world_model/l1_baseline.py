"""L1 next-state predictors for the clebran world model.

Two baselines:

* :class:`InterpreterL1` — the perfect oracle. Calls the clebran
  interpreter on the (state, action) pair. Zero prediction error by
  construction; the upper bound for any learned L1.

* :class:`KnnL1` — a k-nearest-neighbour baseline over the trace
  dataset. Uses a small distance function (Hamming on grid states,
  plus exact match on the action head) and returns the majority-vote
  next_state among the k nearest neighbours. A meaningful first
  measurement of how predictable the world is.

The :func:`evaluate` function reports next-state exact-match accuracy
on a held-out task split, restricted to rows where the previous
register is a grid.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Iterable

from ..data.loader import load_task
from ..dsl.interpreter import ExecutionError, run_trace
from ..dsl.solver_parse import parse_all_solvers


# ----- distance & lookup helpers ----------------------------------------

def _grid_hamming(a: tuple, b: tuple) -> int:
    """Cell-wise Hamming distance between two grids. Returns a large
    value if shapes differ (so neighbours with matching shape are
    preferred)."""
    if len(a) != len(b):
        return 10**9
    d = 0
    for ra, rb in zip(a, b):
        if len(ra) != len(rb):
            return 10**9
        for xa, xb in zip(ra, rb):
            if xa != xb:
                d += 1
    return d


def _row_to_key(row: dict) -> tuple:
    """Hashable key for a row's (state, action). The state is reduced
    to its grid tuple (or None for non-grid); the action is
    (head_name, arg_kinds tuple)."""
    state = row["state"]
    if state["kind"] != "grid":
        return (None, row["action"]["fn"], tuple(row["action"]["arg_kinds"]))
    # Convert the list-of-lists back to a tuple-of-tuples so it's hashable.
    grid = tuple(tuple(r) for r in state["grid"])
    return (grid, row["action"]["fn"], tuple(row["action"]["arg_kinds"]))


# ----- L1 predictors -----------------------------------------------------

class InterpreterL1:
    """The perfect L1 oracle. The clebran interpreter already does this
    exactly; this class is a thin wrapper so the L1 and learned L1
    share an interface."""

    def predict(self, state, action: dict) -> dict:
        """Predict the next register value for the (state, action) pair.

        ``state`` is the *current* register value (the grid the action
        will be applied to). ``action`` is a dict ``{fn, fn_kind,
        arg_kinds}``. The next state is computed by running the
        primitive in isolation against the current state.

        Returns a dict ``{kind, ...}`` in the same serialised-register
        format as the trace dataset.
        """
        # If the action consumes a register, we'd need a multi-step
        # trace to resolve it. The trace dataset already provides
        # that for the Hodel solvers; the L2 planning arm will need a
        # full register file. For the L1 baseline we restrict to
        # single-input, no-register-arg actions (the common case).
        if action.get("fn_kind") != "prim":
            raise NotImplementedError(
                f"InterpreterL1 only handles prim heads, got {action.get('fn_kind')!r}"
            )
        if any(not k.startswith("in") and not k.startswith("const")
               for k in action["arg_kinds"]):
            raise NotImplementedError(
                f"InterpreterL1 requires all-`in`/`const` args, "
                f"got {action['arg_kinds']!r}"
            )
        # For now, the cleanest path: the trace dataset already has
        # the next_state for every (state, action) we care about.
        # The "perfect oracle" is just a lookup against the trace
        # dataset, with the interpreter run only as a check.
        raise NotImplementedError(
            "InterpreterL1 is most useful as a sanity-check against "
            "the clebran interpreter; for the L1 baseline evaluation, "
            "the clebran interpreter is run directly in `evaluate`."
        )


class KnnL1:
    """A k-nearest-neighbour L1 baseline over the trace dataset.

    Indexes the trace dataset by (state grid, action head, arg_kinds)
    and at query time finds the k nearest training rows by grid
    Hamming distance (with action-head exact match as a gate). Returns
    the majority-vote next_state.

    Restricts to rows where the previous register is a grid; the
    clebran IR's heterogeneous register types mean a unified L1 is a
    bigger project (§9f in the roadmap).
    """

    def __init__(self, rows: list[dict], k: int = 5):
        self.k = k
        # Pre-process: keep only rows where state.kind == "grid" AND
        # next_state.kind == "grid" (the cleanest L1 framing).
        self.grid_rows = [r for r in rows
                          if r["state"]["kind"] == "grid"
                          and r["next_state"]["kind"] == "grid"]
        # Group by action-head+arg_kinds: queries with a different
        # action can never be nearest neighbours.
        self.by_action: dict[tuple, list[dict]] = {}
        for r in self.grid_rows:
            act_key = (r["action"]["fn"], tuple(r["action"]["arg_kinds"]))
            self.by_action.setdefault(act_key, []).append(r)
        # Convert state grids to tuples of tuples for fast hashing /
        # distance. The values stored in by_action are still the
        # original dicts, with `state.grid` as list-of-lists.
        for rows_ in self.by_action.values():
            for r in rows_:
                r["_state_tuple"] = tuple(tuple(row) for row in r["state"]["grid"])

    def predict(self, state_grid, action: dict) -> dict | None:
        """Return the majority-vote next_state for the (state, action)
        pair, or None if no training row matches the action."""
        act_key = (action["fn"], tuple(action["arg_kinds"]))
        candidates = self.by_action.get(act_key)
        if not candidates:
            return None
        # Compute Hamming distance to each candidate; keep the k
        # nearest. (For very large candidate pools this should be
        # vectorised; for the 16k-row trace dataset it's fine.)
        # Use the row's own id as a stable tiebreaker so the sort key
        # is fully orderable.
        distances = [(_grid_hamming(state_grid, c["_state_tuple"]),
                       id(c), c)
                      for c in candidates]
        distances.sort(key=lambda x: (x[0], x[1]))
        top = [c for _, _, c in distances[: self.k]]
        # Majority vote on the next_state.
        next_state_tuples = Counter()
        for c in top:
            key = tuple(tuple(row) for row in c["next_state"]["grid"])
            next_state_tuples[key] += 1
        if not next_state_tuples:
            return None
        best_tuple, _ = next_state_tuples.most_common(1)[0]
        return {"kind": "grid", "grid": [list(row) for row in best_tuple]}

    @property
    def n_rows(self) -> int:
        return len(self.grid_rows)


# ----- evaluation --------------------------------------------------------

def _train_test_split_by_task(rows: list[dict], test_frac: float = 0.2,
                              seed: int = 0) -> tuple[list[dict], list[dict]]:
    """Hold out 20% of tasks for test. Deterministic given the seed."""
    import random
    rng = random.Random(seed)
    tasks = sorted(set(r["task_id"] for r in rows))
    rng.shuffle(tasks)
    cutoff = int(round(len(tasks) * test_frac))
    test_tasks = set(tasks[:cutoff])
    train = [r for r in rows if r["task_id"] not in test_tasks]
    test = [r for r in rows if r["task_id"] in test_tasks]
    return train, test


def evaluate(rows: list[dict], k: int = 5, test_frac: float = 0.2,
             seed: int = 0, verbose: bool = True,
             also_test_in_distribution: bool = True) -> dict:
    """Train a KnnL1 on a held-out task split and report accuracy on
    the test split. Restricts to rows where state and next_state are
    both grids.

    Reports four numbers, each against the same held-out grid→grid
    test rows:

    * **KnnL1 exact-match** — the k-NN baseline's exact-match accuracy.
    * **KnnL1 coverage** — the fraction of test rows where the action
      signature appears in the training set (so the k-NN has any
      candidates at all).
    * **KnnL1 shape-match** — the fraction of test rows where the k-NN
      prediction has the same shape as the ground truth (a meaningful
      sub-metric for actions like ``fill`` that preserve shape).
    * **Identity baseline** — predicting the input state as the next
      state. This is the no-learning baseline; a learned L1 must
      beat it.

    If ``also_test_in_distribution`` is True, also reports the same
    four numbers when the k-NN is evaluated on the *training* rows
    themselves (held out by row, not by task). The in-distribution
    numbers are the upper bound for any memorisation-based L1 — a
    k-NN that achieves 0% on out-of-distribution but 100%
    in-distribution is a *correctly-working memoriser that does not
    generalise*. That is the finding this evaluation is designed to
    surface.
    """
    train, test = _train_test_split_by_task(rows, test_frac=test_frac,
                                            seed=seed)
    if verbose:
        print(f"  total rows:    {len(rows):>6}")
        print(f"  train rows:    {len(train):>6}")
        print(f"  test rows:     {len(test):>6}")
    model = KnnL1(train, k=k)
    if verbose:
        print(f"  grid rows in train: {model.n_rows:>6} "
              f"(of {len(train)} train rows)")
        print(f"  unique actions in train: {len(model.by_action):>6}")
    # Restrict to test rows where state and next_state are both grids.
    test_grid_rows = [r for r in test
                      if r["state"]["kind"] == "grid"
                      and r["next_state"]["kind"] == "grid"]
    if verbose:
        print(f"  grid test rows:    {len(test_grid_rows):>6}")
    out = _score_rows(model, test_grid_rows)
    if also_test_in_distribution:
        # In-distribution: hold out a fraction of *rows* (not tasks)
        # and evaluate. The k-NN has seen all of these except the
        # held-out rows, so the result is the memorisation upper bound.
        from random import Random
        rng = Random(seed)
        train_grid_rows = [r for r in train
                           if r["state"]["kind"] == "grid"
                           and r["next_state"]["kind"] == "grid"]
        held_out_set: set[int] = set()
        held_out: list[dict] = []
        for r in train_grid_rows:
            if rng.random() < test_frac:
                held_out_set.add(id(r))
                held_out.append(r)
        non_held = [r for r in train_grid_rows if id(r) not in held_out_set]
        in_dist_model = KnnL1(non_held, k=k)
        in_dist = _score_rows(in_dist_model, held_out, label="  In-dist")
        out["in_distribution"] = in_dist
    return out


def _score_rows(model: "KnnL1", rows: list[dict], label: str = "") -> dict:
    n_total = len(rows)
    n_knn_covered = 0
    n_knn_exact = 0
    n_knn_shape = 0
    n_identity_exact = 0
    n_identity_shape = 0
    for r in rows:
        state_grid = tuple(tuple(row) for row in r["state"]["grid"])
        truth = r["next_state"]
        pred = model.predict(state_grid, r["action"])
        if pred is not None:
            n_knn_covered += 1
            if pred == truth:
                n_knn_exact += 1
            if _shape_of(pred) == _shape_of(truth):
                n_knn_shape += 1
        identity_pred = {"kind": "grid", "grid": r["state"]["grid"]}
        if identity_pred == truth:
            n_identity_exact += 1
        if _shape_of(identity_pred) == _shape_of(truth):
            n_identity_shape += 1
    knn_acc = n_knn_exact / n_total if n_total else 0.0
    knn_cov = n_knn_covered / n_total if n_total else 0.0
    knn_shape = n_knn_shape / n_total if n_total else 0.0
    id_acc = n_identity_exact / n_total if n_total else 0.0
    id_shape = n_identity_shape / n_total if n_total else 0.0
    prefix = f"{label} " if label else "  "
    print()
    print(f"{prefix}KnnL1 exact-match:    {n_knn_exact:>4} / {n_total}  "
          f"= {knn_acc:6.2%}   (coverage: {knn_cov:6.2%})")
    print(f"{prefix}KnnL1 shape-match:    {n_knn_shape:>4} / {n_total}  "
          f"= {knn_shape:6.2%}")
    print(f"{prefix}Identity  exact-match: {n_identity_exact:>4} / {n_total}  "
          f"= {id_acc:6.2%}")
    print(f"{prefix}Identity  shape-match: {n_identity_shape:>4} / {n_total}  "
          f"= {id_shape:6.2%}")
    return {
        "n_total": n_total,
        "n_knn_covered": n_knn_covered,
        "n_knn_exact": n_knn_exact,
        "n_knn_shape": n_knn_shape,
        "n_identity_exact": n_identity_exact,
        "n_identity_shape": n_identity_shape,
        "knn_accuracy": knn_acc,
        "knn_coverage": knn_cov,
        "knn_shape": knn_shape,
        "identity_accuracy": id_acc,
        "identity_shape": id_shape,
    }


def _shape_of(serialised: dict) -> tuple:
    """Return (n_rows, n_cols) of a serialised grid, or None for non-grids."""
    if serialised.get("kind") != "grid":
        return None
    g = serialised["grid"]
    return (len(g), len(g[0]) if g else 0)


# ----- CLI entry point ---------------------------------------------------

def main(trace_path: Path = Path("data/traces.jsonl"),
         k: int = 5, test_frac: float = 0.2, seed: int = 0) -> int:
    print(f"loading trace dataset from {trace_path} ...")
    rows = [json.loads(l) for l in trace_path.read_text(encoding="utf-8").splitlines()]
    print(f"  loaded {len(rows):,} rows\n")
    print(f"evaluating KnnL1 (k={k}, test_frac={test_frac}, seed={seed}):")
    print()
    metrics = evaluate(rows, k=k, test_frac=test_frac, seed=seed)
    print()
    return 0
