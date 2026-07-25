"""B5+planner — the L2 world-model-guided central-library arm (§9f in
``roadmap.md``).

The B5+planner arm is the B5 control (single population + central
library via the Stitch-style compression miner) **augmented with a
planner-seeded individual in the initial population of every task**.
The planner uses the clebran interpreter as a perfect L1 world model
to roll out candidate primitives greedily and pick the one whose
predicted next-state is closest to the target; the resulting linear
program is the seed.

The L1 prediction is the clebran interpreter — exact, deterministic,
free in candidate-evaluation budget. The cost is wall-clock (one
planner call per task per seed) and one program evaluation per task
(counted against the budget).

The comparison is against B5 at matched candidate-evaluations on
the 30-task frontier subset: does the planner-seeded individual
accelerate the GP search?

Usage::

    uv run python -m clebran.baselines.b5_planner --seed 1 --budget 1000000
"""
from __future__ import annotations

import argparse
import random

from ..fitness import Evaluator
from ..lineage import Lineage
from .common import RunLog, run_prefix, subset_pool, subset_tasks


def run_single(
    seed: int,
    budget: int = 1_000_000,
    pop_size: int = 100,
    run_name: str | None = None,
    p_fragment: float = 0.15,
    arm: str = "B5P",
    self_mine: bool = True,
    mine_every: int = 5,
    planner_max_steps: int = 20,
    planner_lookahead: int = 1,
    planner_distance: str = "hamming",
    planner_top_k: int = 1,
) -> dict:
    """Run the B5+planner arm on the frontier subset for a single seed.

    Differences from ``b0.run_single`` (the B0/B5 arm):

    * After the standard ``seed_population`` step, also seed each
      task's population with the L2 planner's iterative best
      program. The planner uses the interpreter as a perfect L1
      (§9f in ``roadmap.md``).
    * ``self_mine=True`` by default (this *is* the B5 variant — the
      central library is the headline).
    * ``planner_lookahead`` controls the planner's depth. ``1`` =
      greedy one-step (default). ``2`` = two-step lookahead (more
      compute, fewer local-optimum traps).
    * ``planner_distance`` controls the planner's distance metric.
      ``"hamming"`` (default), ``"component"``, ``"color_set"``, or
      ``"structural"``. The structural / component metrics are
      *object-aware* — they score primitives on structural match
      (number of disconnected disagreement regions) rather than
      cell-wise Hamming, which is the right metric for tasks that
      change a small region of the grid.
    * ``planner_top_k`` controls how many planner candidates are
      seeded. ``1`` (default) seeds just the planner's best
      program. ``3`` or ``5`` seeds the top-K candidates (one
      planner call, K program evaluations) — see
      ``Lineage.seed_with_planner_topk``.
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
    log = RunLog(run_name or f"{run_prefix()}{arm.lower()}_seed{seed}")
    log.write({"event": "start", "arm": arm, "seed": seed, "budget": budget,
               "pool_size": len(pool), "pop_size": pop_size,
               "self_mine": self_mine, "planner_max_steps": planner_max_steps,
               "planner_lookahead": planner_lookahead,
               "planner_distance": planner_distance,
               "planner_top_k": planner_top_k})

    # First seeding — standard phase-1 closure, then planner seeds
    # on top. The planner uses ALL demo pairs, not just the first,
    # and uses loop avoidance so it doesn't oscillate.
    for tid in tasks:
        lin.seed_population(tid)
        if planner_top_k > 1:
            lin.seed_with_planner_topk(
                tid, k=planner_top_k,
                lookahead=planner_lookahead, distance=planner_distance,
            )
        else:
            lin.seed_with_planner(tid, max_steps=planner_max_steps,
                                  lookahead=planner_lookahead,
                                  distance=planner_distance)

    sched_rng = random.Random(seed + 777)
    epoch = 0
    while ev.evaluations < budget:
        unsolved = [t for t in tasks if not lin.pops[t].solved]
        if not unsolved:
            break
        w = lin.task_weights()
        picks = sched_rng.choices(
            unsolved, weights=[w.get(t, 0.15) for t in unsolved],
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--budget", type=int, default=1_000_000)
    ap.add_argument("--pop-size", type=int, default=100)
    ap.add_argument("--planner-max-steps", type=int, default=20)
    ap.add_argument("--planner-lookahead", type=int, default=1,
                    help="L2 planner depth (1=greedy, 2=two-step lookahead)")
    ap.add_argument("--planner-distance", default="hamming",
                    choices=["hamming", "component", "color_set", "structural"],
                    help="L2 planner distance metric (hamming=cell-wise, "
                         "component=connected components in symmetric "
                         "difference, color_set=color-set overlap, "
                         "structural=hybrid)")
    ap.add_argument("--planner-top-k", type=int, default=1,
                    help="Number of top planner candidates to seed as "
                         "individuals in the initial population (1 = "
                         "just the planner's best; 3 or 5 = top-K).")
    ap.add_argument("--no-self-mine", action="store_true",
                    help="Disable central library mining (B0 mode)")
    args = ap.parse_args()
    summary = run_single(
        seed=args.seed,
        budget=args.budget,
        pop_size=args.pop_size,
        self_mine=not args.no_self_mine,
        planner_max_steps=args.planner_max_steps,
        planner_lookahead=args.planner_lookahead,
        planner_distance=args.planner_distance,
        planner_top_k=args.planner_top_k,
    )
    print()
    print(f"B5+planner (seed={args.seed}, budget={args.budget}):")
    print(f"  solved:       {summary['n_solved']} / {len(subset_tasks())}")
    print(f"  evo-solved:   {summary['n_evo_solved']}")
    print(f"  test-exact:   {summary['n_test_exact']}")
    print(f"  mean length:  {summary['mean_solution_length']:.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
