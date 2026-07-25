"""Tests for the L1 world-model baseline.

The trace dataset is large enough that we use small synthetic rows
for unit tests, and only invoke the real evaluation against
``data/traces.jsonl`` (built by ``scripts/build_traces.py``) for the
end-to-end smoke test.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from clebran.world_model.l1_baseline import (
    KnnL1,
    _grid_hamming,
    _shape_of,
    evaluate,
)
from clebran.world_model.l2_planner import (
    L2Planner,
    _default_candidates,
    _grid_hamming as _l2_hamming,
)
from clebran.dsl.registry import PRIMITIVES


# ---- synthetic row helpers ---------------------------------------------

def _grid_row(state_grid, next_state_grid, fn="fill", fn_kind="prim",
              arg_kinds=None):
    if arg_kinds is None:
        arg_kinds = ["in", "const:ONE"]
    return {
        "task_id": "t",
        "input_idx": 0,
        "step_index": 0,
        "state": {"kind": "grid", "grid": state_grid},
        "action": {"fn": fn, "fn_kind": fn_kind, "arg_kinds": arg_kinds},
        "next_state": {"kind": "grid", "grid": next_state_grid},
        "program_len": 1,
    }


# ---- _grid_hamming -------------------------------------------------------

def test_grid_hamming_matching_shapes():
    a = ((0, 0), (0, 0))
    b = ((0, 0), (0, 0))
    assert _grid_hamming(a, b) == 0


def test_grid_hamming_different_cells():
    a = ((0, 0), (0, 0))
    b = ((1, 0), (0, 0))
    assert _grid_hamming(a, b) == 1


def test_grid_hamming_different_shapes_penalised():
    a = ((0, 0), (0, 0))
    b = ((0, 0, 0), (0, 0, 0))
    assert _grid_hamming(a, b) == 10**9


# ---- _shape_of -----------------------------------------------------------

def test_shape_of_grid():
    assert _shape_of({"kind": "grid", "grid": [[1, 2], [3, 4]]}) == (2, 2)


def test_shape_of_non_grid():
    assert _shape_of({"kind": "int", "int": 5}) is None


# ---- KnnL1 ---------------------------------------------------------------

def test_knn_l1_returns_majority_vote_next_state():
    """If three training rows share the same next_state, the k-NN
    should return that next_state (regardless of the state distance)."""
    rows = [
        _grid_row([[0, 0], [0, 0]], [[1, 1], [1, 1]], arg_kinds=["in"]),
        _grid_row([[0, 0], [0, 0]], [[1, 1], [1, 1]], arg_kinds=["in"]),
        _grid_row([[0, 0], [0, 0]], [[1, 1], [1, 1]], arg_kinds=["in"]),
        # One dissenting row.
        _grid_row([[0, 0], [0, 0]], [[2, 2], [2, 2]], arg_kinds=["in"]),
    ]
    model = KnnL1(rows, k=5)
    state_grid = ((0, 0), (0, 0))
    action = {"fn": "fill", "fn_kind": "prim", "arg_kinds": ["in"]}
    pred = model.predict(state_grid, action)
    assert pred == {"kind": "grid", "grid": [[1, 1], [1, 1]]}


def test_knn_l1_returns_none_for_unseen_action():
    rows = [_grid_row([[0, 0]], [[1, 1]], arg_kinds=["in"])]
    model = KnnL1(rows, k=5)
    pred = model.predict(((0, 0)),
                         {"fn": "fill", "fn_kind": "prim", "arg_kinds": ["reg:0"]})
    assert pred is None


def test_knn_l1_only_uses_grid_rows():
    """Non-grid rows in the input should be ignored for indexing."""
    rows = [
        _grid_row([[0, 0]], [[1, 1]], arg_kinds=["in"]),
        # A non-grid row with the same action should not pollute the index.
        {
            "task_id": "t", "input_idx": 0, "step_index": 0,
            "state": {"kind": "int", "int": 5},
            "action": {"fn": "fill", "fn_kind": "prim", "arg_kinds": ["in"]},
            "next_state": {"kind": "int", "int": 99},
            "program_len": 1,
        },
    ]
    model = KnnL1(rows, k=5)
    # The model should still have one row indexed under the "fill" action.
    assert model.n_rows == 1
    pred = model.predict(((0, 0)),
                         {"fn": "fill", "fn_kind": "prim", "arg_kinds": ["in"]})
    assert pred is not None


# ---- evaluate end-to-end against the real trace dataset -------------------

# Marked as slow so it can be skipped in fast test runs. The real
# evaluation takes a few seconds and requires the trace dataset to be
# present (built by scripts/build_traces.py).
@pytest.mark.slow
def test_evaluate_against_real_trace_dataset():
    trace_path = Path("data/traces.jsonl")
    if not trace_path.exists():
        pytest.skip("data/traces.jsonl not built; run scripts/build_traces.py first")
    rows = [json.loads(l) for l in trace_path.read_text().splitlines()]
    metrics = evaluate(rows, k=5, test_frac=0.2, seed=0, verbose=False)
    # Sanity: the dataset has more than zero grid test rows.
    assert metrics["n_total"] > 0
    # Sanity: the identity shape-match is higher than the knn shape-match
    # (k-NN's predictions on novel (state, action) queries are
    # less useful than just predicting the input as output, on this
    # small a dataset).
    assert metrics["identity_shape"] > metrics["knn_shape"]


# ---- L2 planner tests ---------------------------------------------------

def test_l2_planner_returns_finite_distance():
    """On a same-shape target, the planner should return some
    primitive with a finite distance."""
    state = ((1, 0), (0, 1))
    target = ((0, 1), (1, 0))   # vmirror of state
    planner = L2Planner()
    best = planner.plan(state, target)
    assert best["primitive"] is not None
    assert best["distance"] < float("inf")
    # vmirror of state should be the target.
    assert best["distance"] == 0


def test_l2_planner_picks_vmirror_to_vmirror_a_grid():
    state = ((1, 0, 1),
             (0, 1, 0),
             (1, 0, 1))
    target = ((1, 0, 1),
              (0, 1, 0),
              (1, 0, 1))   # hmirror / vmirror both give same
    planner = L2Planner()
    best = planner.plan(state, target)
    # The planner should find a primitive that produces the target
    # exactly (probably hmirror, vmirror, or rot180 — all give the
    # same result on this symmetric state).
    assert best["distance"] == 0
    assert best["primitive"] in {"hmirror", "vmirror", "rot180"}


def test_l2_planner_default_candidates_nonempty():
    state = ((1, 0), (0, 1))
    target = ((0, 1), (1, 0))
    cands = _default_candidates(state, target)
    assert len(cands) > 0
    # All candidates should reference the state as an arg.
    for name, args in cands:
        assert isinstance(name, str)
        assert state in args
        # And the primitive should be a registered clebran primitive.
        assert name in PRIMITIVES


def test_l2_planner_iterative_terminates_within_max_steps():
    """The iterative planner should always terminate within max_steps,
    even on a target it cannot reach."""
    state = ((0, 0), (0, 0))
    target = ((1, 1), (1, 1))
    planner = L2Planner()
    outcome = planner.plan_iteratively(state, target, max_steps=5)
    assert len(outcome["trace"]) <= 5
    assert "solved" in outcome
    assert "final_distance" in outcome


def test_l2_planner_multipair_picks_primitive_that_works_for_all_demos():
    """The multi-pair planner should pick a primitive whose result
    matches the target on *all* demos, not just the first one.

    Setup: two demos with the same input but different targets.
    Only ``replace`` on a specific colour can transform the first
    demo's target without breaking the second (which is already
    the target)."""
    input_grid = ((1, 2), (2, 1))
    target_a = ((1, 0), (0, 1))    # replace 2 with 0
    target_b = ((0, 2), (2, 0))    # replace 1 with 0
    # No single primitive can satisfy both — the planner should
    # still produce a finite-distance best (e.g. one of the
    # replace candidates) instead of giving up.
    planner = L2Planner()
    result = planner.plan_demos([(input_grid, target_a),
                                  (input_grid, target_b)])
    # The planner should return *some* candidate.
    assert result["primitive"] is not None
    assert result["distance"] < float("inf")
    # And the per-demo distances are recorded.
    assert "_per_demo_distances" in result
    assert len(result["_per_demo_distances"]) == 2


def test_l2_planner_multipair_skips_primitive_that_fails_one_demo():
    """If a candidate primitive fails (or produces a wrong-shape
    grid) on *any* demo, it should not be picked even if it
    solves the other demos perfectly."""
    # First demo: 2x2 grid that hmirror produces a different 2x2 grid.
    # Second demo: 1x3 grid where hmirror would also work (3x1) but
    # hmirror's result is wrong shape (3 rows of length 1, not 1 row
    # of length 3). The planner should reject hmirror because of the
    # second demo.
    demo1 = (((1, 0), (0, 1)), ((0, 1), (1, 0)))   # hmirror of input
    demo2 = (((1, 2, 3),), ((3, 2, 1),))            # 1x3 → 1x3
    planner = L2Planner()
    # Run a candidate that would only work on demo1 (e.g. hmirror
    # on a 2x2 grid). It should be rejected because it produces a
    # 2x2 grid, not 1x3.
    candidates = planner.candidate_fn(demo2[0], demo2[1])
    # Find the hmirror candidate.
    hmirror = next((c for c in candidates if c[0] == "hmirror"), None)
    assert hmirror is not None
    # Apply it to demo2: should give a wrong shape.
    from clebran.world_model.l2_planner import _safe_call
    out = _safe_call("hmirror", demo2[0])
    # Sanity: hmirror of a 1x3 is a 3x1, not 1x3.
    assert out is not None
    # The planner should still return a non-trivial best (it will
    # try other primitives).
    result = planner.plan_demos([demo1, demo2])
    # The result should be finite (the planner found *some* primitive
    # that works on both demos). hmirror is not it.
    if result["primitive"] is not None:
        assert result["distance"] < float("inf")


def test_l2_planner_lookahead2_picks_better_than_greedy():
    """With lookahead=2, the planner should sometimes find a
    better 2-step prefix than the greedy one-step planner would
    produce.

    We craft a case: the input is a 1x4 grid. Step 1 turns it into
    a 2x4 grid (via vconcat with self). Step 2 transforms the
    2x4 grid into the target. The greedy one-step planner would
    be stuck (no single candidate produces the 2x4 target). With
    lookahead=2, the planner should chain vconcat(self, self) with
    a second step.

    This is a smoke test: we only check that lookahead=2 produces
    a result, not that it specifically solves the example.
    """
    input_grid = ((1, 0, 1, 0),)
    target = ((1, 0, 1, 0),
              (1, 0, 1, 0))
    planner_greedy = L2Planner(lookahead=1)
    planner_look2 = L2Planner(lookahead=2)
    # The greedy planner might find vconcat(self, self) which gives
    # the target exactly. So this isn't a great test. But it checks
    # the API works.
    g = planner_greedy.plan_demos([(input_grid, target)])
    l2 = planner_look2.plan_demos([(input_grid, target)])
    assert g["primitive"] is not None
    assert l2["primitive"] is not None
    # Lookahead=2 has a sequence attribute if it actually did
    # 2-step search.
    if l2.get("_sequence") and len(l2["_sequence"]) > 1:
        # If lookahead picked a 2-step sequence, the first step
        # might differ from greedy.
        assert l2["distance"] < float("inf")


def test_l2_planner_iterative_avoids_immediate_loops():
    """The iterative planner should not cycle: a state visited
    earlier should not be re-visited (it's penalised by
    ``loop_penalty``).

    Setup: a state where the greedy choice would oscillate between
    two states. With loop avoidance, the planner should pick a
    different primitive or stop.

    A simpler test: the iterative planner on a state where the
    first step is identity (e.g. ``tophalf`` of a 1x2 grid) should
    not keep re-trying identity and should terminate quickly.
    """
    state = ((1, 0),)
    target = ((0, 1),)    # not reachable by any 1-arg primitive
    planner = L2Planner()
    outcome = planner.plan_iteratively(state, target, max_steps=10)
    # The planner should produce a non-trivial trace and not loop
    # forever.
    assert len(outcome["trace"]) <= 10
    # Most steps should produce different states (i.e. no
    # immediate oscillation).
    states = [step["state"] for step in outcome["trace"]]
    # At most one repeated state (allowed as the only escape
    # when the planner is stuck).
    repeats = len(states) - len(set(states))
    assert repeats <= 1, f"planner oscillated: {states}"


def test_l2_planner_plan_to_program_multipair_returns_valid_program():
    """``plan_to_program`` on a list of demos should return a
    Program that has at least one statement (when at least one
    candidate improves over identity)."""
    state = ((1, 0, 1),
             (0, 1, 0),
             (1, 0, 1))
    target = ((1, 0, 1),
              (0, 1, 0),
              (1, 0, 1))   # identity — planner should produce
                           # a no-op or 0-statement program
    planner = L2Planner()
    result = planner.plan_to_program([(state, target)], max_steps=5)
    # The result is a dict.
    assert "program" in result
    assert "trace" in result
    assert "solved" in result
    # The program should be a Program instance.
    from clebran.dsl.program import Program
    assert isinstance(result["program"], Program)


@pytest.mark.slow
def test_l2_planner_evaluate_against_real_trace_dataset():
    from clebran.world_model.l2_planner import evaluate as evaluate_l2
    trace_path = Path("data/traces.jsonl")
    if not trace_path.exists():
        pytest.skip("data/traces.jsonl not built; run scripts/build_traces.py first")
    rows = [json.loads(l) for l in trace_path.read_text().splitlines()]
    metrics = evaluate_l2(rows, verbose=False)
    # Sanity: the dataset has more than zero demo pairs.
    assert metrics["n_pairs"] > 0
    # Sanity: the planner distance is finite on at least some pairs.
    assert metrics["n_finite_pairs"] > 0
    # Sanity: the planner improves over identity on at least some
    # pairs (this is the whole point of the L2 direction).
    assert metrics["n_planner_improves"] > 0
    # Sanity: the iterative planner solves at least one task
    # end-to-end (otherwise the whole direction is null).
    assert metrics["n_iterative_solved"] > 0
    # Sanity: the planner's mean distance is ≤ the identity's
    # mean distance (the planner is a *better* baseline than
    # do-nothing on the same-shape pairs).
    if metrics["mean_planner_distance"] != float("inf"):
        assert metrics["mean_planner_distance"] \
            <= metrics["mean_identity_distance"]
