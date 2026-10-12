"""B5+L1-proposer — the L1-as-proposer arm (roadmap §A1, A1 first
concrete test).

The B5+L1-proposer arm is the B5 control (single population + central
library via the Stitch-style compression miner) **augmented with an
L1-proposer-seeded individual in the initial population of every
task**. The proposer queries the trace dataset's frequency statistics
for the most common first-step primitive on grids of the input's
shape (roadmap §A1 hypothesis: the L1 has seen 400 reference solvers
and learned strategies for combining primitives that B5's local
search starts from scratch on).

The proposer is restricted to *geometric* primitives (vmirror,
hmirror, rot90/180/270, cmirror, dmirror, top/bottom/left/righthalf)
for v1 because (a) the GPL1 has been shown to learn them with
100% OOD accuracy (scoping pilot 2026-10-07) and (b) their default
args are unambiguous (the input grid itself for mirrors and
rotations, and the appropriate half for the half-crop primitives).
Compositional primitives (fill, paint, replace, ofcolor, fork, ...)
are excluded for v1 because their default args are task-specific
and the GPL1 doesn't learn them.

Usage::

    uv run python -m clebran.baselines.b5_l1_proposer --seed 1 --budget 1000000

The comparison is against B5 at matched candidate-evaluations on the
30-task frontier subset: does the L1-proposer-seeded individual
accelerate the GP search?
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

from ..fitness import Evaluator
from ..lineage import Lineage
from ..world_model.l1_proposer import L1Proposer
from .common import RunLog, run_prefix, subset_pool, subset_tasks


def run_single(
    seed: int,
    budget: int = 1_000_000,
    pop_size: int = 100,
    run_name: str | None = None,
    p_fragment: float = 0.15,
    arm: str = "B5L1",
    self_mine: bool = True,
    mine_every: int = 5,
    trace_path: Path = Path("data/traces.jsonl"),
    proposer_k: int = 3,
    exclude_frontier: bool = True,
) -> dict:
    """Run the B5+L1-proposer arm on the frontier subset for a single
    seed.

    Differences from ``b0.run_single`` (the B0/B5 arm):

    * After the standard ``seed_population`` step, also seed each
      task's population with the L1 proposer's top-K first-step
      primitives for the input's shape.
    * ``self_mine=True`` by default (this *is* the B5 variant — the
      central library is the headline).
    * ``trace_path`` is the trace dataset the proposer builds from.
    * ``proposer_k`` controls how many top proposals are added per
      task (default 3). The maximum is capped at ``pop_size // 4``
      inside ``Lineage.seed_with_l1_proposer``.
    * ``exclude_frontier=True`` builds the proposer only on
      non-frontier tasks (so the frontier subset is held-out OOD).
      Set ``exclude_frontier=False`` to use the entire trace
      dataset (including frontier tasks).
    """
    tasks = subset_tasks()
    pool = subset_pool()
    ev = Evaluator()
    lin = Lineage(
        lineage_id=f"{arm.lower()}-s{seed}",
        pool=pool,
        tasks=tasks,
        seed=seed,
        pop_size=pop_size,
        evaluator=ev,
        p_fragment=p_fragment,
    )
    if run_name is None:
        prefix = run_prefix()
        log_name = f"{prefix}{arm.lower()}_seed{seed}"
    else:
        log_name = run_name
    log = RunLog(log_name)
    log.write({"event": "start", "arm": arm, "seed": seed, "budget": budget,
               "pool_size": len(pool), "pop_size": pop_size,
               "self_mine": self_mine, "trace_path": str(trace_path),
               "proposer_k": proposer_k,
               "exclude_frontier": exclude_frontier})

    # Build the L1 proposer. We exclude the frontier subset's
    # task IDs so the proposer is truly OOD w.r.t. the test
    # subset.
    exclude_task_ids = []
    if exclude_frontier:
        exclude_task_ids = list(tasks.keys())
    proposer = L1Proposer(trace_path=trace_path,
                          exclude_task_ids=exclude_task_ids)
    log.write({"event": "proposer_build",
               "n_shapes_covered": proposer.n_shapes_covered()})

    # First seeding — standard phase-1 closure, then L1-proposer seeds
    # on top.
    for tid in tasks:
        lin.seed_population(tid)
        lin.seed_with_l1_proposer(tid, proposer, k=proposer_k)

    sched_rng = random.Random(seed + 777)
    epoch = 0
    while ev.evaluations < budget:
        unsolved = [t for t in tasks if not lin.pops[t].solved]
        if not unsolved:
            break
        w = lin.task_weights()
        picks = sched_rng.choices(
            unsolved, weights=[t_weight(t, w) for t in unsolved],
            k=len(unsolved),
        )
        for tid in picks:
            if ev.evaluations >= budget:
                break
            before = lin.pops[tid].solved
            lin.step_generation(tid)
            if lin.pops[tid].solved and not before:
                sol = lin.pops[tid].solution
                log.write({
                    "event": "solve", "task": tid, "epoch": epoch,
                    "evals": ev.evaluations, "len": sol.fit.length,
                    "phase": lin.pops[tid].solved_phase,
                    "test_exact": ev.test_exact(sol.prog, tasks[tid]),
                    "program": sol.prog.to_json(),
                    "abstractions": {
                        n: lin.abstractions[n].to_dict()
                        for n in list(sol.prog.abstractions_used())
                    },
                })
        epoch += 1
        if self_mine and epoch % mine_every == 0:
            lin.mine_own_abstractions()
        log.write({
            "event": "epoch", "epoch": epoch, "evals": ev.evaluations,
            "solved": len(lin.solved_tasks()),
        })

    solved = lin.solved_tasks()
    test_exact = sum(
        1 for tid in solved
        if ev.test_exact(lin.pops[tid].solution.prog, tasks[tid])
    )
    mean_len = (
        sum(lin.pops[t].solution.fit.length for t in solved) / len(solved)
        if solved else 0.0
    )
    by_phase = lin.solved_by_phase()
    n_evo_solved = by_phase.get("evolution", 0)
    summary = {
        "arm": arm,
        "seed": seed,
        "budget": budget,
        "evals": ev.evaluations,
        "n_solved": len(solved),
        "n_test_exact": test_exact,
        "n_evo_solved": len(n_evo_solved) if isinstance(n_evo_solved, set) else n_evo_solved,
        "mean_solution_length": mean_len,
        "solved": sorted(list(solved)),
    }
    log.write({"event": "summary", **summary})
    return summary


def t_weight(tid, w):
    """Forward to the sched_rng.choices `weights` arg; expects a dict."""
    return w.get(tid, 0.15)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--budget", type=int, default=1_000_000)
    ap.add_argument("--pop-size", type=int, default=100)
    ap.add_argument("--proposer-k", type=int, default=3,
                    help="Number of top L1-proposer candidates to "
                         "seed per task (capped at pop_size // 4).")
    ap.add_argument("--trace-path", type=Path, default=Path("data/traces.jsonl"),
                    help="Trace dataset path for the L1 proposer.")
    ap.add_argument("--no-exclude-frontier", action="store_true",
                    help="Don't exclude frontier tasks from the "
                         "proposer's training data (use the entire "
                         "trace dataset).")
    ap.add_argument("--no-self-mine", action="store_true",
                    help="Disable central library mining (B0 mode).")
    args = ap.parse_args()
    summary = run_single(
        seed=args.seed,
        budget=args.budget,
        pop_size=args.pop_size,
        self_mine=not args.no_self_mine,
        trace_path=args.trace_path,
        proposer_k=args.proposer_k,
        exclude_frontier=not args.no_exclude_frontier,
    )
    print()
    print(f"B5+L1-proposer (seed={args.seed}, budget={args.budget}):")
    print(f"  solved:       {summary['n_solved']} / {len(subset_tasks())}")
    print(f"  evo-solved:   {summary['n_evo_solved']}")
    print(f"  test-exact:   {summary['n_test_exact']}")
    print(f"  mean length:  {summary['mean_solution_length']:.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())