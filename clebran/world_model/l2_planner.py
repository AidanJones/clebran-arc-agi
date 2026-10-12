"""L2 planner: greedy planning with the clebran interpreter as a perfect
L1 world model.

The L2 planner is the next step in the world-model direction (§9f in
``roadmap.md``): given a current grid state and a target grid, it
*imagines* the result of each candidate primitive and picks the one
whose predicted next-state has the minimum Hamming distance to the
target. The clebran interpreter provides the perfect L1 prediction
(``PRIMITIVES[name].fn(*args)``); the planner is a thin layer on top.

This is the upper bound for any learned world model: if the
interpreter-as-oracle planner cannot make progress toward the target,
no learned approximation can either (and the cost is compute, not
accuracy — the interpreter is exact).

**Candidate set.** The planner iterates over a fixed set of primitives
with hand-defined default-argument strategies, restricted to
grid→grid transitions (the planner only picks when the predicted
next-state is a grid of the same shape as the target; otherwise the
primitive is skipped). The default set is the most common grid→grid
primitives in the Hodel reference solvers
(``scripts/inspect_traces.py``): ``vmirror``, ``hmirror``, ``rot90``,
``rot180``, ``rot270``, ``tophalf``, ``bottomhalf``, ``lefthalf``,
``righthalf``, ``trim``, ``hconcat``, ``vconcat``, ``replace``,
``fill``, ``paint``, ``cover``, ``normalize`` — applied to the state
itself — plus a few 2-argument compositions with self-arguments
(``vconcat(I, I)``, ``vconcat(I, vmirror(I))``, etc.) and 3-argument
``fill``/``paint``/``replace`` with common default colour
strategies.

**Multi-pair planning.** The canonical ARC fitness is *multi-pair*:
a program must produce the right output for *all* demonstration
pairs, not just the first one. ``L2Planner.plan_demos`` (and the
high-level ``plan_to_program``) takes a list of (input, target)
demos and picks the primitive that *minimises the mean Hamming
distance across all demos* (with a ``+inf`` penalty if any demo's
shape doesn't match the target). This is the natural extension of
the single-pair greedy planner.

**Lookahead.** ``L2Planner.lookahead`` (default 1) controls how many
steps the planner considers. ``lookahead=1`` is greedy one-step;
``lookahead=2`` rolls out every (candidate, candidate) pair and
picks the 2-step prefix that minimises the multi-pair distance at
the end. With ~30 candidates and 2 steps, the branching factor is
~900, which is still cheap (one interpreter call per leaf).

**Loop avoidance.** The iterative planner (``plan_iteratively``)
keeps a small set of recently-visited states; a candidate that
produces an already-visited state is heavily penalised (+inf), so
the planner doesn't oscillate.

**Evaluation.** The planner is evaluated on the trace dataset by
asking, at the *first* step of every (input, target) demo pair, which
primitive the planner picks, what its minimum distance to target is,
and how often that matches the Hodel solver's first primitive. A
multi-pair version of this evaluation is also provided
(``evaluate_multipair``).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Iterable

from ..dsl.program import Program, Statement
from ..dsl.registry import CONSTANTS, PRIMITIVES


# ---- helpers -------------------------------------------------------------

def _grid_hamming(a: tuple, b: tuple) -> int | float:
    """Cell-wise Hamming distance between two same-shape grids, or
    +inf if shapes differ."""
    if len(a) != len(b):
        return float("inf")
    d = 0
    for ra, rb in zip(a, b):
        if len(ra) != len(rb):
            return float("inf")
        for xa, xb in zip(ra, rb):
            if xa != xb:
                d += 1
    return d


def _connected_components(diff_cells: set) -> int:
    """Count the number of 4-connected components in a set of (i, j)
    cell coordinates. Used as the *object-aware* distance: each
    component is one "object change" between state and target."""
    if not diff_cells:
        return 0
    visited: set = set()
    components = 0
    for cell in diff_cells:
        if cell in visited:
            continue
        components += 1
        # Iterative BFS so deep grids don't blow the recursion limit.
        stack = [cell]
        while stack:
            c = stack.pop()
            if c in visited:
                continue
            visited.add(c)
            i, j = c
            for di, dj in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                ni, nj = i + di, j + dj
                if (ni, nj) in diff_cells and (ni, nj) not in visited:
                    stack.append((ni, nj))
    return components


def _component_distance(a: tuple, b: tuple) -> int | float:
    """Object-aware distance: number of 4-connected components in the
    symmetric difference of two same-shape grids, or +inf if shapes
    differ. Each component represents one "object change" — a moved
    object contributes 2 components (vacated area + new position); a
    fill of one region contributes 1 component.

    This is the diagnostic for *why* Hamming fails: a 50-cell fill
    scores 1.0 here but 50.0 in Hamming, so a candidate that fills a
    small region in the right way outranks a candidate that fills a
    large region in the wrong way.
    """
    if len(a) != len(b):
        return float("inf")
    diff: set = set()
    for i, (ra, rb) in enumerate(zip(a, b)):
        if len(ra) != len(rb):
            return float("inf")
        for j, (xa, xb) in enumerate(zip(ra, rb)):
            if xa != xb:
                diff.add((i, j))
    return _connected_components(diff)


def _color_set_distance(a: tuple, b: tuple) -> int | float:
    """Color-set distance: number of distinct colors present in one
    grid but not the other. A task that *adds* a new color scores 1;
    a task that *replaces* a color scores 2; a task that preserves
    the color set scores 0.

    Useful for tasks like "change all red to blue" (replace-style)
    where the color set matters but the cell positions don't.
    """
    if len(a) != len(b) or not a or not a[0]:
        return float("inf")
    colors_a = {c for row in a for c in row}
    colors_b = {c for row in b for c in row}
    # |A \ B| + |B \ A|
    return len(colors_a - colors_b) + len(colors_b - colors_a)


def _structural_distance(a: tuple, b: tuple,
                          alpha: float = 1.0,
                          beta: float = 0.05,
                          gamma: float = 2.0) -> float:
    """Structural / object-aware distance that combines:

      * component_count: number of disconnected regions of
        disagreement (each is one "object change");
      * hamming / 20.0: scaled cell-wise disagreement, capped at
        one extra "object change" per 20 cells of mismatch
        (empirically chosen so a 5-cell fix costs ~0.25 components);
      * color_set_distance: number of colors in one but not the
        other (multiplied by 2 so color mismatches dominate
        positional jitter).

    Both alpha, beta, gamma are tunable but the defaults are
    chosen so the metric stays in the same magnitude as the raw
    component_count (~1–5 for "object-changed" tasks), and the
    hamming penalty is bounded so a single 5-cell move doesn't
    outscore a 50-cell fill.

    Returns +inf if the grids differ in shape.
    """
    comp = _component_distance(a, b)
    ham = _grid_hamming(a, b)
    cols = _color_set_distance(a, b)
    if comp == float("inf") or ham == float("inf") or cols == float("inf"):
        return float("inf")
    return alpha * comp + beta * ham + gamma * cols


# ---- the named distance functions ----------------------------------------

# A dict mapping distance name -> callable, so callers (CLI, REPL, tests)
# can switch by name without importing every metric.
DISTANCES: dict[str, Callable] = {
    "hamming":     _grid_hamming,
    "component":   _component_distance,
    "color_set":   _color_set_distance,
    "structural":  _structural_distance,
}


def _mean_dists(dists: list[float]) -> float:
    """Mean of a list of distances, treating +inf as a hard veto
    (the result is +inf if any distance is +inf)."""
    finite_count = 0
    total = 0.0
    for d in dists:
        if d == float("inf"):
            return float("inf")
        total += d
        finite_count += 1
    return total / max(1, finite_count)


def _most_common_color(grid: tuple) -> int:
    """Return the most common non-background cell value in a grid."""
    if not grid or not grid[0]:
        return 0
    from collections import Counter
    flat = [c for row in grid for c in row]
    return Counter(flat).most_common(1)[0][0]


def _safe_call(fn_name: str, *args) -> object | None:
    """Call a primitive by name with try/except, returning None on any
    error. Used by the planner to safely probe each candidate. This is
    the *perfect* L1: the clebran interpreter itself, called directly.

    The planner can swap this for a learned-L1 rollout function via
    the ``rollout_fn`` constructor argument — see ``L1Rollout`` in
    ``l1_rollout.py`` for a hybrid that prefers the GPL1's prediction
    on the primitives it has learned, and falls back to the
    interpreter on miss. The trade-off is accuracy vs rollout speed:
    paper 3's §6 conclusion names this as the explicit "next push"
    ("The learned L1's job is to be a fast approximation of the
    perfect L1, with a tolerable accuracy loss in exchange for
    rollout speed").
    """
    try:
        return PRIMITIVES[fn_name].fn(*args)
    except Exception:
        return None


# ---- the candidate set ---------------------------------------------------

def _default_candidates(state: tuple, target: tuple) -> list[tuple[str, tuple]]:
    """Return a list of (primitive_name, args) candidate actions for
    the given state. The args are *already evaluated*; the planner
    just calls the primitive on them.

    The default candidate set is the most common grid→grid
    primitives in the Hodel reference solvers, with smart
    default-argument strategies that match how the Hodel solvers
    typically use them.

    Coverage of the top 20 grid→grid primitives in the trace
    dataset (1,731 grid→grid transitions across 400 tasks):
    fill, vconcat, paint, replace, hconcat, vmirror, hmirror, rot90,
    tophalf, bottomhalf, lefthalf, crop, rot270, righthalf, rot180,
    dmirror, upscale, switch, compress, downscale.
    """
    mc = _most_common_color(state)
    cands: list[tuple[str, tuple]] = []

    # 1-arg grid→grid primitives — apply to the state itself.
    # Includes the 16 most common in the trace dataset.
    for name in ("vmirror", "hmirror", "dmirror", "rot90", "rot180", "rot270",
                 "tophalf", "bottomhalf", "lefthalf", "righthalf",
                 "trim", "compress", "normalize", "hconcat", "vconcat",
                 "replace", "fill", "paint", "cover"):
        sig = PRIMITIVES.get(name)
        if sig is None or sig.arity != 1:
            continue
        cands.append((name, (state,)))

    # 2-arg self-compositions — typical Hodel patterns (vconcat,
    # hconcat with self / mirror).
    for second_arg in (state, _safe_call("vmirror", state) or state,
                      _safe_call("hmirror", state) or state,
                      _safe_call("dmirror", state) or state,
                      _safe_call("rot90", state) or state):
        if second_arg is None:
            continue
        for name in ("vconcat", "hconcat"):
            sig = PRIMITIVES.get(name)
            if sig is None:
                continue
            cands.append((name, (state, second_arg)))
            cands.append((name, (second_arg, state)))

    # 2-arg downscale / hupscale / upscale — typical factor=2.
    for name in ("downscale", "hupscale", "upscale"):
        sig = PRIMITIVES.get(name)
        if sig is None:
            continue
        cands.append((name, (state, 2)))

    # 3-arg fill / paint / replace with common defaults.
    cands.append(("fill", (state, mc, ((mc,),))))
    cands.append(("fill", (state, 0, ((0,),))))
    cands.append(("fill", (state, 0, state)))   # clear
    cands.append(("paint", (state, ((0, 0),), mc)))
    cands.append(("paint", (state, ((0, 0),), 0)))
    cands.append(("underfill", (state, mc, ((mc,),))))
    cands.append(("underpaint", (state, ((0, 0),), mc)))
    for c in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9):
        if c != mc:
            cands.append(("replace", (state, mc, c)))
            cands.append(("replace", (state, c, mc)))
    # 3-arg switch(c1, c2) — only useful when c1 != c2; try the
    # two most common colors.
    if mc != 0:
        cands.append(("switch", (state, mc, 0)))
        cands.append(("switch", (state, 0, mc)))

    # 3-arg crop(grid, start, dims) — try origin and full size, which
    # is a no-op (so the planner will skip it via infinite distance).
    # Try a small interior crop too.
    h, w = len(state), len(state[0]) if state else 0
    if h > 1 and w > 1:
        cands.append(("crop", (state, (0, 0), (h - 1, w - 1))))
        cands.append(("crop", (state, (0, 0), (1, w))))
        cands.append(("crop", (state, (0, 0), (h, 1))))

    return cands


# ---- planner -> program conversion ---------------------------------------

_CONST_BY_VALUE: dict = {}
for _name, (_val, _t) in CONSTANTS.items():
    if isinstance(_val, int) and not isinstance(_val, bool):
        _CONST_BY_VALUE.setdefault(_val, []).append(_name)


def _classify_arg(value, input_grid, register_history) -> tuple:
    """Classify an evaluated argument value into an IR arg tuple.

    ``input_grid`` is the task's input grid; ``register_history`` is
    the list of register values produced by the *prior* planner
    steps (one entry per step). Returns the appropriate
    ``(kind, payload)`` tuple.

    Priority:
      1. The input grid → ``("in", None)``
      2. A constant value in arc-dsl → ``("const", name)``
      3. A primitive function (callable from PRIMITIVES) → ``("prim", name)``
      4. A literal value (tuple, int, grid that's not the input) → ``("lit", value)``
    """
    if value is input_grid:
        return ("in", None)
    if isinstance(value, int) and not isinstance(value, bool):
        names = _CONST_BY_VALUE.get(value)
        if names:
            return ("const", names[0])
    if callable(value):
        for name, sig in PRIMITIVES.items():
            if sig.fn is value:
                return ("prim", name)
    return ("lit", value)


def _trace_to_program(input_grid, trace: list[dict]) -> Program:
    """Convert a planner's iterative trace into a clebran Program.

    Each step in the trace has a chosen primitive and evaluated
    args. We classify each arg into an IR arg tuple (using
    ``_classify_arg``) and produce a Statement. The output Program
    is the linear sequence of statements, ready to be evaluated
    by the clebran fitness function.
    """
    statements: list[Statement] = []
    register_history: list = []
    for step_record in trace:
        primitive = step_record.get("primitive")
        if primitive is None:
            break
        args = step_record.get("args")
        if args is None:
            break
        classified = tuple(_classify_arg(a, input_grid, register_history)
                           for a in args)
        statements.append(
            Statement(fn=("prim", primitive), args=classified)
        )
        # Run the interpreter to populate the next register for
        # later classification.
        from ..dsl.interpreter import _invoke, _check_size
        try:
            out = _invoke(("prim", primitive),
                          list(args), register_history, {})
            _check_size(out)
            register_history.append(out)
        except Exception:
            break
    return Program(statements=statements)


# ---- the planner ---------------------------------------------------------

class L2Planner:
    """Greedy / lookahead planner using the clebran interpreter as L1.

    Parameters
    ----------
    candidate_fn : callable, optional
        A function ``(state, target) -> [(name, args), ...]`` returning
        the candidate actions to consider. Defaults to
        ``_default_candidates``.
    distance : str or callable, default "hamming"
        The distance metric. Either a name from ``DISTANCES``
        (``"hamming"``, ``"component"``, ``"color_set"``,
        ``"structural"``) or a callable ``(state, target) -> float``.
        See the module docstring for the metric definitions; the
        default is cell-wise Hamming, which is too coarse for many
        ARC tasks — the structural metric is the natural upgrade.
    lookahead : int, default 1
        Planning depth. ``1`` = greedy one-step (the default; cheap
        and effective for most ARC tasks). ``2`` rolls out every
        (candidate, candidate) pair and picks the 2-step prefix that
        minimises the multi-pair distance at the end.
    loop_penalty : float, default 1e9
        Penalty added to a candidate's distance if it produces a
        state already in the iterative planner's visited set. Used
        only by ``plan_iteratively``; ignored by ``plan`` and
        ``plan_demos``.
    """

    def __init__(self, candidate_fn: Callable | None = None,
                 distance: "str | Callable" = "hamming",
                 lookahead: int = 1,
                 loop_penalty: float = 1e9,
                 rollout_fn: Callable | None = None):
        """Construct an L2 planner.

        Parameters
        ----------
        candidate_fn : callable, optional
            ``(state, target) -> list[(primitive_name, args)]``. The
            candidate-generator. Defaults to ``_default_candidates``.
        distance : str or callable, default "hamming"
            Distance metric name (one of ``DISTANCES``) or a custom
            ``(next_state, target) -> float`` callable.
        lookahead : int, default 1
            Lookahead depth for the iterative planner. ``1`` is
            greedy; ``2`` does two-step lookahead.
        loop_penalty : float, default 1e9
            Penalty added to a candidate's distance if it produces a
            state already in the iterative planner's visited set.
        rollout_fn : callable, optional
            ``(primitive_name, *args) -> result_or_None`` — the
            rollout engine. The planner uses this to predict
            ``(state, action) → next_state`` for each candidate.
            Defaults to ``_safe_call`` (the clebran interpreter —
            the *perfect* L1). Pass an L1-rollout function to use
            a learned L1 (e.g. ``L1Rollout(gp_l1).predict``) —
            see ``l1_rollout.py`` for the hybrid
            L1-then-interpreter pattern that trades accuracy for
            rollout speed (paper 3 §6, "the learned L1's job is
            to be a fast approximation of the perfect L1").
        """
        if lookahead < 1:
            raise ValueError("lookahead must be >= 1")
        self.candidate_fn = candidate_fn or _default_candidates
        if isinstance(distance, str):
            if distance not in DISTANCES:
                raise ValueError(
                    f"unknown distance {distance!r}; "
                    f"choose from {sorted(DISTANCES)} or pass a callable"
                )
            self.distance_fn = DISTANCES[distance]
            self.distance_name = distance
        else:
            self.distance_fn = distance
            self.distance_name = getattr(distance, "__name__", "custom")
        self.lookahead = lookahead
        self.loop_penalty = loop_penalty
        self.rollout_fn = rollout_fn or _safe_call

    # -- single-pair greedy -------------------------------------------------

    def plan(self, state: tuple, target: tuple,
             forbid_states: set | None = None) -> dict:
        """Return the best primitive and its predicted next-state.

        ``state`` and ``target`` are tuples-of-tuples (grids).
        ``forbid_states`` is an optional set of states to penalise
        (the planner adds ``loop_penalty`` to a candidate's distance
        if it produces any of these states). Returns a dict::

            {
              "primitive":  <name of the chosen primitive>,
              "args":       <tuple of args passed to the primitive>,
              "next_state": <the predicted next state (a grid tuple)>,
              "distance":   <distance to target under the configured metric>,
            }

        If no candidate produces a valid grid→grid transition, the
        result has ``primitive=None`` and ``distance=+inf``.
        """
        best = {"primitive": None, "args": None, "next_state": None,
                "distance": float("inf")}
        for name, args in self.candidate_fn(state, target):
            result = self.rollout_fn(name, *args)
            if result is None or not isinstance(result, tuple):
                continue
            if not result or not isinstance(result[0], tuple):
                continue
            d = self.distance_fn(result, target)
            if d == float("inf"):
                continue
            if forbid_states and result in forbid_states:
                d += self.loop_penalty
            if d < best["distance"]:
                best = {
                    "primitive": name,
                    "args": args,
                    "next_state": result,
                    "distance": d,
                }
        return best

    # -- multi-pair greedy --------------------------------------------------

    def plan_demos(self, demos: list[tuple[tuple, tuple]],
                   forbid_states: set | None = None) -> dict:
        """Multi-pair variant of ``plan``.

        ``demos`` is a list of (state, target) tuples. The planner
        evaluates each candidate once *per demo* (calling the
        primitive on the corresponding state), and picks the
        candidate that minimises the *mean* Hamming distance to the
        targets across all demos. A candidate that fails on any demo
        (e.g. wrong shape) is given ``+inf`` and never picked.

        This is the natural extension of ``plan`` for ARC tasks
        where the same program must satisfy multiple demonstrations.
        """
        if not demos:
            return {"primitive": None, "args": None, "next_state": None,
                    "distance": float("inf")}

        # All demos are guaranteed to share a candidate set (we
        # only use the first state's candidate set, since the
        # candidate-fn signature is (state, target) -> cands and
        # the state is the only state-varying input).
        first_state, first_target = demos[0]
        best = {"primitive": None, "args": None, "next_state": None,
                "distance": float("inf")}
        for name, args in self.candidate_fn(first_state, first_target):
            # Evaluate this candidate on every demo. To do this
            # correctly, we need to remap the args to use each
            # demo's state — by analogy, the first arg slot that
            # contained the first state should contain the current
            # demo's state. (All default candidates use `state` as
            # the first arg, so a 1:1 substitution works.)
            dists: list[float] = []
            next_states: list = []
            bad = False
            for st, tg in demos:
                # Substitute the first state in `args` with `st`.
                remapped = tuple(st if a is first_state else a for a in args)
                result = self.rollout_fn(name, *remapped)
                if result is None or not isinstance(result, tuple):
                    bad = True
                    break
                if not result or not isinstance(result[0], tuple):
                    bad = True
                    break
                d = self.distance_fn(result, tg)
                if d == float("inf"):
                    bad = True
                    break
                dists.append(d)
                next_states.append(result)
            if bad:
                continue
            mean_d = _mean_dists(dists)
            if forbid_states and any(ns in forbid_states for ns in next_states):
                mean_d += self.loop_penalty
            if mean_d < best["distance"]:
                best = {
                    "primitive": name,
                    "args": args,            # original (first-state) args
                    "next_state": next_states[0],   # next state for first demo
                    "distance": mean_d,
                    "_per_demo_distances": dists,
                }
        return best

    # -- lookahead ---------------------------------------------------------

    def top_k_candidates(self, demos: list[tuple[tuple, tuple]],
                          k: int = 3) -> list[dict]:
        """Return the top-K multi-pair candidates, sorted by ascending
        mean distance. Each entry is a dict::

            {
              "primitive":  <name of the primitive>,
              "args":       <tuple of args (with the first-state substituted)>,
              "next_state": <the predicted next state for the first demo>,
              "distance":   <mean multi-pair distance under the configured metric>,
              "_per_demo_distances": <list of per-demo distances>,
            }

        Used by ``Lineage.seed_with_planner_topk`` to seed the
        top-K planner candidates (one planner call, K program
        evaluations).

        ``k`` is clamped to the number of valid candidates. If
        ``k <= 0`` or there are no valid candidates, the result
        is an empty list.
        """
        if k <= 0 or not demos:
            return []
        # Replicate the multi-pair candidate evaluation from
        # plan_demos, but collect all valid candidates and sort.
        first_state, first_target = demos[0]
        valid: list[dict] = []
        for name, args in self.candidate_fn(first_state, first_target):
            dists: list[float] = []
            next_states: list = []
            bad = False
            for st, tg in demos:
                remapped = tuple(st if a is first_state else a for a in args)
                result = self.rollout_fn(name, *remapped)
                if result is None or not isinstance(result, tuple):
                    bad = True; break
                if not result or not isinstance(result[0], tuple):
                    bad = True; break
                d = self.distance_fn(result, tg)
                if d == float("inf"):
                    bad = True; break
                dists.append(d)
                next_states.append(result)
            if bad:
                continue
            mean_d = _mean_dists(dists)
            valid.append({
                "primitive": name,
                "args": args,
                "next_state": next_states[0],
                "distance": mean_d,
                "_per_demo_distances": dists,
                "_per_demo_next_states": next_states,
            })
        # Sort by distance, then by primitive name for stable
        # ordering of ties.
        valid.sort(key=lambda c: (c["distance"], c["primitive"]))
        return valid[:k]

    def _lookahead_best(self, demos: list[tuple[tuple, tuple]],
                        depth: int,
                        forbid_states: set | None = None) -> dict:
        """Recursive helper: return the best (mean_d, sequence) of
        length up to ``depth`` starting from ``demos``.

        At depth=1, this is just ``plan_demos`` (greedy one-step).
        At depth=2, for each candidate, simulate one step, then call
        ``_lookahead_best`` recursively on the resulting
        (next_state, target) pairs at depth-1. Pick the candidate
        that minimises the total distance (step 1 + step 2).

        Returns a dict with::

            {
              "primitive":   <the first primitive in the sequence>,
              "args":        <the first primitive's args>,
              "next_state":  <the next state for the first demo>,
              "distance":    <total mean distance over `depth` steps>,
              "_sequence":   [(primitive, args, next_state_per_demo), ...],
            }
        """
        if depth <= 1 or self.lookahead <= 1:
            return self.plan_demos(demos, forbid_states=forbid_states)

        first_step = self.plan_demos(demos, forbid_states=forbid_states)
        if first_step["primitive"] is None:
            return first_step

        # Try each candidate, not just the best — to avoid
        # the trap of greedy local optima. We materialise the
        # first-step candidates with their per-demo results.
        first_state, first_target = demos[0]
        first_step_options: list[dict] = []
        for name, args in self.candidate_fn(first_state, first_target):
            dists: list[float] = []
            next_states: list = []
            bad = False
            for st, tg in demos:
                remapped = tuple(st if a is first_state else a for a in args)
                result = self.rollout_fn(name, *remapped)
                if result is None or not isinstance(result, tuple):
                    bad = True; break
                if not result or not isinstance(result[0], tuple):
                    bad = True; break
                d = self.distance_fn(result, tg)
                if d == float("inf"):
                    bad = True; break
                dists.append(d)
                next_states.append(result)
            if bad:
                continue
            if forbid_states and any(ns in forbid_states for ns in next_states):
                dists = [d + self.loop_penalty for d in dists]
            first_step_options.append({
                "name": name, "args": args,
                "dists": dists, "next_states": next_states,
            })

        best = None
        for opt in first_step_options:
            # Recurse: at the new state for each demo, what is the
            # best sequence of (depth - 1) more steps?
            sub_demos = [(ns, tg) for ns, (_, tg) in
                         zip(opt["next_states"], demos)]
            sub = self._lookahead_best(sub_demos, depth - 1,
                                       forbid_states=forbid_states)
            if sub["primitive"] is None:
                # The remainder can't improve; use first step's
                # distance alone as a lower bound on the total.
                total = _mean_dists(opt["dists"])
            else:
                # Use first-step mean + sub-distance as the total.
                # This is an upper bound on the achievable distance
                # with this prefix.
                total = _mean_dists(opt["dists"]) + sub["distance"]
            if best is None or total < best["distance"]:
                best = {
                    "primitive": opt["name"],
                    "args": opt["args"],
                    "next_state": opt["next_states"][0],
                    "distance": total,
                    "_sequence": [opt] + (sub.get("_sequence", [])
                                          if sub.get("primitive") else []),
                }
        return best if best is not None else first_step

    # -- iterative planner (single-pair, with loop avoidance) ---------------

    def plan_iteratively(self, state: tuple, target: tuple,
                         max_steps: int = 20) -> dict:
        """Apply the planner repeatedly until either the predicted
        next-state matches the target exactly, the planner can't
        improve, or ``max_steps`` is reached. Returns a trace of
        the planning process.

        The iterative planner uses single-pair ``plan`` with loop
        avoidance: candidates that produce an already-visited state
        are penalised by ``loop_penalty`` (default 1e9). This
        prevents oscillation in tasks like ``fill(I, mc, ZERO)``
        where the identity is a local minimum.
        """
        trace = []
        current = state
        visited: set = {state}
        for step in range(max_steps):
            best = self.plan(current, target, forbid_states=visited)
            trace.append({
                "step": step,
                "state": current,
                **best,
            })
            if best["primitive"] is None:
                break
            if best["distance"] == 0:
                break
            current = best["next_state"]
            visited.add(current)
        return {
            "trace": trace,
            "final_state": current,
            "final_distance": trace[-1]["distance"] if trace else float("inf"),
            "solved": trace[-1]["distance"] == 0 if trace else False,
        }

    # -- high-level: multi-pair iterative to program ------------------------

    def plan_to_program(self, demos: list[tuple[tuple, tuple]],
                        max_steps: int = 20,
                        forbid_states: set | None = None) -> dict:
        """Plan iteratively across multiple demos, then convert the
        trace to a clebran Program. The first demo's input grid is
        used as the IR's `I` reference.

        Returns::

            {
              "program":   <the clebran Program>,
              "trace":     <the planning trace>,
              "solved":    <True iff the planner's final state == target
                            on ALL demos>,
              "final_states":  <list of final states, one per demo>,
              "final_distances": <list of final distances, one per demo>,
            }
        """
        if not demos:
            return {"program": Program(statements=[]), "trace": [],
                    "solved": False, "final_states": [],
                    "final_distances": []}

        first_state = demos[0][0]
        trace: list[dict] = []
        current_states: list = [st for st, _ in demos]
        targets: list = [tg for _, tg in demos]
        visited: set = set()
        if forbid_states is not None:
            visited = set(forbid_states)
        for st in current_states:
            visited.add(st)

        for step in range(max_steps):
            sub_demos = list(zip(current_states, targets))
            best = self._lookahead_best(
                sub_demos, depth=self.lookahead,
                forbid_states=visited,
            )
            if best["primitive"] is None:
                break
            # Trace entry — record the (primitive, args) chosen at
            # this step and the per-demo next states.
            per_demo_next_states = []
            if "_sequence" in best and best["_sequence"]:
                # Lookahead: the first step's next_states are in
                # the sequence.
                per_demo_next_states = best["_sequence"][0]["next_states"]
            else:
                # Greedy: re-evaluate to get per-demo next states.
                first_state_now = current_states[0]
                for st, tg in sub_demos:
                    args = best["args"]
                    remapped = tuple(
                        st if a is first_state_now else a for a in args
                    )
                    ns = self.rollout_fn(best["primitive"], *remapped)
                    per_demo_next_states.append(ns)
            per_demo_dists = [
                _grid_hamming(ns, tg) if ns is not None else float("inf")
                for ns, tg in zip(per_demo_next_states, targets)
            ]
            trace.append({
                "step": step,
                "primitives_per_demo": current_states,
                "primitive": best["primitive"],
                "args": best["args"],
                "next_state": per_demo_next_states[0],
                "per_demo_next_states": per_demo_next_states,
                "per_demo_distances": per_demo_dists,
                "distance": _mean_dists(per_demo_dists),
            })
            if all(ns is not None and _grid_hamming(ns, tg) == 0
                   for ns, tg in zip(per_demo_next_states, targets)):
                current_states = list(per_demo_next_states)
                break
            if not per_demo_next_states or any(
                    ns is None for ns in per_demo_next_states):
                break
            current_states = list(per_demo_next_states)
            visited.update(current_states)
            if all(ns is not None and _grid_hamming(ns, tg) != float("inf")
                   for ns, tg in zip(per_demo_next_states, targets)):
                if all(d == 0 for d in per_demo_dists):
                    break
            # If we can't improve anymore, stop.
            if trace[-1]["distance"] >= float("inf") - 1:
                break

        program = _trace_to_program(first_state, trace)
        final_dists = [
            _grid_hamming(st, tg)
            for st, tg in zip(current_states, targets)
        ]
        return {
            "program": program,
            "trace": trace,
            "solved": all(d == 0 for d in final_dists),
            "final_states": current_states,
            "final_distances": final_dists,
        }


# ---- evaluation ----------------------------------------------------------

def _final_target(rows: list[dict], task_id: str, input_idx: int) -> tuple | None:
    """Find the last register for the given (task_id, input_idx) —
    that's the solver's final output, which is the planner's target
    for the first step."""
    target = None
    for r in rows:
        if r["task_id"] != task_id or r["input_idx"] != input_idx:
            continue
        if r["next_state"]["kind"] == "grid":
            target = tuple(tuple(row) for row in r["next_state"]["grid"])
    return target


def _hodel_first_primitive(rows: list[dict], task_id: str, input_idx: int) -> dict | None:
    """Find the Hodel solver's first primitive for the given
    (task_id, input_idx)."""
    for r in rows:
        if (r["task_id"] == task_id and r["input_idx"] == input_idx
                and r["step_index"] == 0):
            return r["action"]
    return None


def evaluate(rows: list[dict], verbose: bool = True,
             also_iterative: bool = True, max_iter_steps: int = 20,
             lookahead: int = 1) -> dict:
    """Run the L2 planner on every (task_id, input_idx) demo pair
    in the trace dataset, at the *first* step. Report:

    * the mean minimum Hamming distance to the solver's final output,
    * the mean identity distance (i.e. the distance if the planner
      takes no action — just keep the input),
    * the rate at which the planner's choice matches the Hodel
      solver's first primitive (restricted to cases where the
      solver's first primitive is in the planner's candidate set).

    If ``also_iterative`` is True, also reports the iterative
    planner's solve rate (the fraction of pairs where the
    iterative planner reaches the target exactly within
    ``max_iter_steps``).
    """
    pairs: dict[tuple, list[dict]] = {}
    for r in rows:
        pairs.setdefault((r["task_id"], r["input_idx"]), []).append(r)

    n_pairs = 0
    n_planner_improves = 0
    n_planner_matches_hodel = 0
    n_hodel_in_candidate_set = 0
    dists_planner: list[float] = []
    dists_identity: list[float] = []
    n_iterative_solved = 0
    n_iterative_runs = 0
    for (tid, iidx), pair_rows in pairs.items():
        # The input grid is the state of the step_index=0 row.
        state = None
        for r in pair_rows:
            if r["step_index"] == 0 and r["state"]["kind"] == "grid":
                state = tuple(tuple(row) for row in r["state"]["grid"])
                break
        if state is None:
            continue
        target = _final_target(pair_rows, tid, iidx)
        if target is None:
            continue
        n_pairs += 1
        identity_distance = _grid_hamming(state, target)
        dists_identity.append(identity_distance)
        # Run the one-step planner.
        planner = L2Planner(lookahead=lookahead)
        best = planner.plan(state, target)
        d = best["distance"] if best["distance"] != float("inf") else identity_distance
        dists_planner.append(d)
        if d < identity_distance:
            n_planner_improves += 1
        hodel = _hodel_first_primitive(pair_rows, tid, iidx)
        if hodel is not None:
            candidates = _default_candidates(state, target)
            hodel_in_set = any(name == hodel["fn"] for name, _ in candidates)
            if hodel_in_set:
                n_hodel_in_candidate_set += 1
                if best["primitive"] == hodel["fn"]:
                    n_planner_matches_hodel += 1
        if also_iterative and identity_distance != float("inf"):
            n_iterative_runs += 1
            outcome = planner.plan_iteratively(state, target,
                                              max_steps=max_iter_steps)
            if outcome["solved"]:
                n_iterative_solved += 1
    if n_pairs == 0:
        return {"n_pairs": 0}
    finite = [(p, i) for p, i in zip(dists_planner, dists_identity)
              if p != float("inf") and i != float("inf")]
    if finite:
        mean_planner = sum(p for p, _ in finite) / len(finite)
        mean_identity = sum(i for _, i in finite) / len(finite)
    else:
        mean_planner = float("nan")
        mean_identity = float("nan")
    if verbose:
        print(f"  demo pairs evaluated: {n_pairs}")
        print(f"  (finite-distance pairs: {len(finite)})")
        print(f"  identity  mean distance to target: {mean_identity:.2f}")
        print(f"  planner   mean distance to target: {mean_planner:.2f}")
        print(f"  planner improves over identity:  {n_planner_improves} "
              f"/ {n_pairs} = {n_planner_improves/n_pairs:.1%}")
        print(f"  Hodel first primitive in candidate set: "
              f"{n_hodel_in_candidate_set}")
        match_str = (f"{n_planner_matches_hodel} / "
                     f"{n_hodel_in_candidate_set} = "
                     f"{(n_planner_matches_hodel/n_hodel_in_candidate_set):.1%}"
                     if n_hodel_in_candidate_set else "n/a")
        print(f"  planner matches Hodel (when in candidate set): {match_str}")
        if also_iterative:
            print(f"  iterative planner (max {max_iter_steps} steps) "
                  f"solves: {n_iterative_solved} / {n_iterative_runs} "
                  f"= {n_iterative_solved/n_iterative_runs:.1%}"
                  if n_iterative_runs else "  iterative: n/a")
    return {
        "n_pairs": n_pairs,
        "n_finite_pairs": len(finite),
        "mean_planner_distance": mean_planner,
        "mean_identity_distance": mean_identity,
        "n_planner_improves": n_planner_improves,
        "n_hodel_in_candidate_set": n_hodel_in_candidate_set,
        "n_planner_matches_hodel": n_planner_matches_hodel,
        "n_iterative_runs": n_iterative_runs,
        "n_iterative_solved": n_iterative_solved,
    }


# ---- CLI entry point -----------------------------------------------------

def main(trace_path: Path = Path("data/traces.jsonl"),
         lookahead: int = 1) -> int:
    print(f"loading trace dataset from {trace_path} ...")
    rows = [json.loads(l) for l in trace_path.read_text(encoding="utf-8").splitlines()]
    print(f"  loaded {len(rows):,} rows\n")
    print(f"evaluating L2 planner (one-step, lookahead={lookahead}, "
          f"on every demo pair):")
    print()
    metrics = evaluate(rows, lookahead=lookahead)
    print()
    return 0
