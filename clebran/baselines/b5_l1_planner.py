"""B5 + L1-rollout planner (B5L1P) — the L1-as-rollout-engine arm
(paper 3 §6, "next push").

The B5L1P arm is the B5 control (single population + central
library) **augmented with a planner-seeded individual, where the
L2 planner uses a hybrid L1-then-interpreter rollout engine
instead of the perfect clebran interpreter**. The hybrid prefers
the GPL1's prediction on the primitives it has learned (vmirror,
hmirror, rot*, cmirror, dmirror, bottomhalf, cellwise, paint,
replace — 9 of 12 primitives where GPL1 is shape-perfect on
frontier OOD), and falls back to the interpreter on miss.

The trade-off is accuracy vs rollout speed. Paper 3 §6 names
this as the explicit "next push" of the world-modeling direction:

  *"The learned L1's job is to be a fast approximation of the
  perfect L1, with a tolerable accuracy loss in exchange for
  rollout speed — and the clebran rig is the right test bed for
  measuring that accuracy / speed trade-off against an L2
  planner using the perfect L1 as the ground truth."*

The fallback-then-L1 pattern (not the other way around) ensures
the arm's accuracy floor is the interpreter's — the L1 is silent,
not wrong, on primitives it hasn't learned. The speedup is
real but bounded: the L1 only helps on the ~12 primitives GPL1
has covered, not on the 2/3-arg primitives (`fill`, `paint`,
`replace` with default args, `hconcat`, `vconcat`, scaling, ...)
that the L2 planner's `_default_candidates` uses heavily.

The comparison is against B5+planner (B5P, the perfect-L1 planner
arm) at matched candidate-evaluations on the 30-task frontier
subset. The B5P arm is null at 4M (paper 3, 20 seeds: B5
12.45 ± 1.15 vs B5P 12.35 ± 0.99, mean delta −0.10, t = 0.26).
A faster L1-rollout planner could *either* match B5P (the
interpreter is not a binding constraint) or regress if the L1's
errors compound through the planner's ranking.

Usage::

    uv run python -m clebran.baselines.b5_l1_planner --seed 1 --budget 1000000
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from ..fitness import Evaluator
from ..lineage import Lineage
from ..world_model.l1_gp import GPL1
from ..world_model.l1_rollout import make_l1_rollout
from ..world_model.l2_planner import L2Planner, _safe_call
from .common import RunLog, run_prefix, subset_pool, subset_tasks


def _load_gpl1_from_log_or_train(
    seed: int,
    budget: int,
    trace_path: Path = Path("data/traces.jsonl"),
    exclude_frontier: bool = True,
) -> GPL1:
    """Build a GPL1 from the trace dataset. Used to construct the
    hybrid L1 rollout for the planner.

    Parameters
    ----------
    seed : int
        The seed is unused for the GPL1 (which is deterministic
        given a fixed trace dataset and a fixed ``pop_size``,
        ``n_generations``, ``max_program_len``, and GP ``seed``)
        but is kept in the signature for symmetry with other arms.
    budget : int
        Unused (kept for symmetry with other arms).
    trace_path : Path, default ``data/traces.jsonl``
        The trace dataset.
    exclude_frontier : bool, default True
        If True, exclude the frontier subset's task IDs from the
        GPL1's training set so the L1 is OOD w.r.t. the test
        subset.
    """
    rows = [json.loads(l) for l in trace_path.read_text(encoding="utf-8").splitlines()]
    if exclude_frontier:
        frontier = json.loads((trace_path.parent / "frontier_subset.json").read_text(encoding="utf-8"))
        exclude_ids = {t["task_id"] for t in frontier["tasks"]}
        train = [r for r in rows if r["task_id"] not in exclude_ids]
    else:
        train = rows
    train_grid = [r for r in train
                  if r["state"]["kind"] == "grid"
                  and r["next_state"]["kind"] == "grid"]
    return GPL1(train_grid, pop_size=50, n_generations=8,
                max_program_len=3, seed=0, verbose=False)


def run_single(
    seed: int,
    budget: int = 1_000_000,
    pop_size: int = 100,
    run_name: str | None = None,
    p_fragment: float = 0.15,
    arm: str = "B5L1P",
    self_mine: bool = True,
    mine_every: int = 5,
    planner_max_steps: int = 20,
    planner_lookahead: int = 1,
    planner_distance: str = "hamming",
    planner_top_k: int = 1,
    trace_path: Path = Path("data/traces.jsonl"),
    exclude_frontier: bool = True,
) -> dict:
    """Run the B5 + L1-rollout-planner arm on the frontier subset
    for a single seed.

    Differences from ``b5_planner.run_single`` (the B5P arm):

    * The L2 planner is constructed with a hybrid
      L1-then-interpreter rollout engine (``make_l1_rollout(gp)``)
      instead of the perfect interpreter.
    * The GPL1 is trained on non-frontier tasks (so the L1 is OOD
      w.r.t. the test subset).
    * The arm name is ``B5L1P`` (B5 + L1-rollout planner).
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
        suffix = f"k{planner_top_k}" if planner_top_k > 1 else ""
        log_name = f"{prefix}{arm.lower()}{suffix}_seed{seed}"
    else:
        log_name = run_name
    log = RunLog(log_name)
    log.write({"event": "start", "arm": arm, "seed": seed, "budget": budget,
               "pool_size": len(pool), "pop_size": pop_size,
               "self_mine": self_mine, "planner_max_steps": planner_max_steps,
               "planner_lookahead": planner_lookahead,
               "planner_distance": planner_distance,
               "planner_top_k": planner_top_k,
               "trace_path": str(trace_path),
               "exclude_frontier": exclude_frontier})

    # Build the GPL1 (the learned L1).
    gp = _load_gpl1_from_log_or_train(
        seed=seed, budget=budget, trace_path=trace_path,
        exclude_frontier=exclude_frontier,
    )
    n_learned = sum(1 for evo in gp.evolved.values()
                    if evo is not None and evo.program is not None)
    log.write({"event": "l1_build", "n_primitives_learned": n_learned,
               "evolved_primitives": sorted(p for p, e in gp.evolved.items()
                                            if e is not None and e.program is not None)})

    # Build the L2 planner with the L1-then-interpreter rollout.
    rollout = make_l1_rollout(gp)
    planner = L2Planner(
        lookahead=planner_lookahead,
        distance=planner_distance,
        rollout_fn=rollout,
    )
    log.write({"event": "planner_build", "rollout": "L1-then-interpreter",
               "n_primitives_learned": n_learned})

    # First seeding — standard phase-1 closure, then planner seeds
    # on top. The planner uses ALL demo pairs, not just the first,
    # and uses loop avoidance so it doesn't oscillate.
    for tid in tasks:
        lin.seed_population(tid)
        if planner_top_k > 1:
            lin.seed_with_planner_topk(
                tid, k=planner_top_k,
                planner=planner,
                lookahead=planner_lookahead, distance=planner_distance,
            )
        else:
            lin.seed_with_planner(tid, max_steps=planner_max_steps,
                                  planner=planner,
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
    ap.add_argument("--planner-lookahead", type=int, default=1)
    ap.add_argument("--planner-distance", default="hamming",
                    choices=["hamming", "component", "color_set", "structural"])
    ap.add_argument("--planner-top-k", type=int, default=1)
    ap.add_argument("--no-self-mine", action="store_true")
    ap.add_argument("--trace-path", type=Path, default=Path("data/traces.jsonl"))
    ap.add_argument("--no-exclude-frontier", action="store_true")
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
        trace_path=args.trace_path,
        exclude_frontier=not args.no_exclude_frontier,
    )
    print()
    print(f"B5+L1-rollout-planner (seed={args.seed}, budget={args.budget}):")
    print(f"  solved:       {summary['n_solved']} / {len(subset_tasks())}")
    print(f"  evo-solved:   {summary['n_evo_solved']}")
    print(f"  test-exact:   {summary['n_test_exact']}")
    print(f"  mean length:  {summary['mean_solution_length']:.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())