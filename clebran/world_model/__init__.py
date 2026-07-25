"""L1 next-state predictors and evaluation.

A *world model* in the clebran substrate is a function
``(register_value, action) -> next_register_value`` — the L1 in the
L1/L2/L3 taxonomy of Agentic World Modeling (arXiv:2604.22748). The
clebran interpreter is a perfect L1 (zero prediction error by
construction); the open question is whether a *learned* approximation
generalises well enough to be useful for planning.

The trace dataset (``data/traces.jsonl``, built by
``scripts/build_traces.py``) provides the training signal: one row per
trace step with the typed register state, the primitive call, and the
resulting typed register state.

This package currently provides two L1 baselines:

* :class:`InterpreterL1` — the perfect oracle. Returns the next register
  value computed by the clebran interpreter. The upper bound for any
  learned L1.
* :class:`KnnL1` — a k-nearest-neighbour baseline over the trace dataset.
  Uses Hamming distance on grid states (with a fallback for non-grid
  states) and exact match on the action head. A meaningful first
  measurement of how much room there is for compression.

The :func:`evaluate` function reports next-state exact-match accuracy
on a held-out task split, restricted to the rows where the previous
register is a grid (the natural L1 framing for grid-state transitions).
"""
from __future__ import annotations

from .l1_baseline import InterpreterL1, KnnL1, evaluate
from .l2_planner import L2Planner, evaluate as evaluate_l2

__all__ = ["InterpreterL1", "KnnL1", "evaluate",
           "L2Planner", "evaluate_l2"]
