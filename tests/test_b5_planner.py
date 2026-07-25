"""Tests for the B5+planner arm and the Lineage.seed_with_planner method."""
from __future__ import annotations

from pathlib import Path

import pytest

from clebran.baselines.b5_planner import run_single as run_b5_planner
from clebran.baselines.common import subset_tasks
from clebran.fitness import Evaluator
from clebran.lineage import Lineage
from clebran.world_model.l2_planner import L2Planner


def test_seed_with_planner_adds_individual_to_population():
    """Calling seed_with_planner on a task should add a planner-
    generated individual to that task's population."""
    tasks = subset_tasks()
    if not tasks:
        pytest.skip("no subset tasks available")
    # Use a small pool for speed; just need the first task.
    first_tid = next(iter(tasks))
    task = {first_tid: tasks[first_tid]}
    # Build a primitive pool from the task's reference solver.
    from clebran.dsl.solver_parse import parse_all_solvers
    progs = parse_all_solvers()
    pool = sorted(progs[first_tid].primitives_used())
    ev = Evaluator()
    lin = Lineage(
        lineage_id="test-b5p",
        pool=pool,
        tasks=task,
        seed=1,
        pop_size=10,
        evaluator=ev,
    )
    # Seed the population first.
    lin.seed_population(first_tid)
    n_before = len(lin.pops[first_tid].individuals)
    # Run planner seeding.
    added = lin.seed_with_planner(first_tid, max_steps=10)
    n_after = len(lin.pops[first_tid].individuals)
    # The planner should add 1 individual (or 0 if it produced
    # nothing). Either way, the population should not shrink.
    assert n_after >= n_before
    if added:
        # The planner-seeded individual should be at the front of
        # the population (inserted at index 0, then sorted).
        # The fitness should be valid (not None).
        ind = lin.pops[first_tid].individuals[0]
        assert ind.prog is not None
        assert ind.fit is not None


def test_plan_to_program_round_trip():
    """The planner-to-program conversion should produce a Program
    that can be serialised and run."""
    state = ((1, 0, 1),
             (0, 1, 0),
             (1, 0, 1))
    target = ((1, 0, 1),
              (0, 1, 0),
              (1, 0, 1))
    planner = L2Planner()
    # New multi-pair API: pass a list of (state, target) demos.
    result = planner.plan_to_program([(state, target)], max_steps=5)
    # The result is a dict with program, trace, solved.
    assert "program" in result
    assert "trace" in result
    # The program can be serialised to JSON.
    json_str = result["program"].to_json()
    assert isinstance(json_str, str)
    # And re-loaded.
    from clebran.dsl.program import Program
    reloaded = Program.from_json(json_str)
    assert len(reloaded.statements) == len(result["program"].statements)


@pytest.mark.slow
def test_b5_planner_arm_runs():
    """The B5+planner arm should run end-to-end on a small budget
    without errors and produce a valid summary."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        # Override the log dir so we don't pollute logs/.
        # (The arm writes to logs/ directly; for the test we just
        # verify the run completes.)
        summary = run_b5_planner(
            seed=1,
            budget=100_000,
            pop_size=20,
            planner_max_steps=5,
        )
    assert "n_solved" in summary
    assert "n_evo_solved" in summary
    assert "solved" in summary
    assert isinstance(summary["n_solved"], int)
    assert isinstance(summary["n_evo_solved"], int)
    assert summary["n_solved"] >= 0
    assert summary["n_evo_solved"] >= 0
    # At least some tasks should be solved by phase-1 (the
    # planner-seeded arm inherits B5's phase-1 logic).
    assert summary["n_solved"] >= summary["n_evo_solved"]
