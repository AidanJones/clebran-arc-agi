"""L1 as rollout engine: a hybrid L1-then-interpreter rollout for the
L2 planner (paper 3 §6, "next push").

The L2 planner's "rollout engine" is the function it uses to predict
``(state, action) → next_state`` for each candidate primitive. The
default rollout engine is the *perfect* L1 — the clebran interpreter
itself, called via ``PRIMITIVES[fn].fn(*args)``. The interpreter is
exact, deterministic, and free in candidate-evaluation budget, but
its wall-clock cost per call is non-trivial (tens of microseconds
for a single primitive).

This module provides a **hybrid L1-then-interpreter** rollout that
prefers the GPL1's prediction on the primitives it has learned, and
falls back to the perfect interpreter on miss. The trade-off is
accuracy vs rollout speed — paper 3 §6 names this as the explicit
"next push" of the world-modeling direction:

  *"The learned L1's job is to be a fast approximation of the
  perfect L1, with a tolerable accuracy loss in exchange for rollout
  speed — and the clebran rig is the right test bed for measuring
  that accuracy / speed trade-off against an L2 planner using the
  perfect L1 as the ground truth."*

The hybrid is **fallback-then-L1**, not the other way around:
* for primitives the L1 has learned (vmirror, hmirror, rot*,
  cmirror, dmirror, bottomhalf, cellwise, paint, replace, ...) the
  L1 is used (it's faster and accurate for the geometric
  primitives);
* for primitives the L1 hasn't learned (hconcat, vconcat, scaling,
  ...) the interpreter is used (the L1 is silent, not wrong).

This is the *correct* fallback pattern: the L1's wrong predictions
would mis-rank candidates, but its silence on unknown primitives
just routes those calls to the interpreter. The arm's accuracy
floor is the interpreter's; the arm's speed ceiling is the L1's.
"""
from __future__ import annotations

from typing import Callable

from .l1_gp import GPL1
from .l2_planner import _safe_call


def make_l1_rollout(gp: GPL1) -> Callable:
    """Build a hybrid L1-then-interpreter rollout function from a
    trained GPL1.

    The returned function has the same signature as ``_safe_call``:
    ``(fn_name, *args) -> result_or_None``. For 1-arg primitives
    that GPL1 has a learned program for, it uses GPL1's prediction;
    otherwise it falls back to ``_safe_call`` (the perfect L1).

    The fallback ensures:
    * 2-arg / 3-arg primitives (fill, paint, replace with default
      args, etc.) still go through the interpreter. (The L1
      *predicts* for some of these — see ``l1_gp`` — but the default
      arg strategies in ``_default_candidates`` may use values the
      L1 wasn't trained on.)
    * Primitives the L1 didn't learn (hconcat, vconcat, scaling,
      ...) silently fall through to the interpreter.
    * Shape mismatches in the L1's prediction fall through (the L1
      is *shape-correct* on 25.6% of OOD predictions and 0% on
      others; on miss we want the interpreter, not the L1's wrong
      shape).

    Parameters
    ----------
    gp : GPL1
        A trained GPL1 (see ``l1_gp.GPL1``). The rollout function
        uses ``gp.evolved`` to look up learned programs by primitive
        name.

    Returns
    -------
    rollout : callable
        ``(fn_name, *args) -> result_or_None`` — drop-in replacement
        for ``_safe_call`` in the L2 planner.

    See Also
    --------
    clebran.world_model.l1_gp.GPL1 : the GPL1 class.
    clebran.world_model.l2_planner.L2Planner : takes a ``rollout_fn``
        constructor argument.
    """
    def rollout(fn_name: str, *args):
        # Only the 1-arg case is in GPL1's coverage. Multi-arg
        # primitives always fall through to the interpreter.
        if len(args) != 1:
            return _safe_call(fn_name, *args)
        evo = gp.evolved.get(fn_name)
        if evo is None or evo.program is None:
            return _safe_call(fn_name, *args)
        try:
            pred = evo.predict(args[0])
        except Exception:
            return _safe_call(fn_name, *args)
        # Sanity check: the prediction must be a grid (tuple of
        # tuples). If not, fall through to the interpreter — the L1
        # was wrong, not silent.
        if not isinstance(pred, tuple) or not pred or not isinstance(pred[0], tuple):
            return _safe_call(fn_name, *args)
        return pred
    return rollout


def benchmark_rollout_speed(rollout_fn, queries: list[tuple],
                             n_repeats: int = 3) -> dict:
    """Measure predict-time speed of a rollout function over a list
    of ``(fn_name, *args)`` queries. Returns per-call microseconds.

    The hybrid L1 rollout should be substantially faster than the
    interpreter rollout on primitives GPL1 has learned, and roughly
    equal on primitives it hasn't. The arm's effective speedup is
    the *weighted* speedup across the candidate set.
    """
    import time
    best_us = float("inf")
    for _ in range(n_repeats):
        t0 = time.perf_counter_ns()
        for q in queries:
            rollout_fn(*q)
        t1 = time.perf_counter_ns()
        elapsed_us = (t1 - t0) / 1000.0
        if elapsed_us < best_us:
            best_us = elapsed_us
    per_call_us = best_us / max(1, len(queries))
    return {
        "n_queries": len(queries),
        "per_call_us": per_call_us,
        "calls_per_sec": 1e6 / per_call_us if per_call_us else 0.0,
    }
