"""B0 — single population, all the compute (§7).

Round-robin over unsolved subset tasks, one generation each, until the
candidate-evaluation budget is exhausted or everything is solved.

B5 — the Stitch central-library control (§7): the *same* single population,
but it periodically mines its own solutions into a growing abstraction
library (the compression miner) and reuses it in further search — a
DreamCoder/Stitch wake-sleep analogue with no multi-agent divergence and no
channel. B5 vs B6/B7 isolates whether the divergence + communication
structure adds anything over centralized abstraction reuse alone.
"""
from __future__ import annotations

import argparse
import random

from ..fitness import Evaluator
from ..lineage import Lineage
from ..metrics.recovery import abstraction_stats
from .common import RunLog, run_prefix, subset_pool, subset_tasks


def run_single(
    seed: int,
    budget: int = 500_000,
    pop_size: int = 100,
    run_name: str | None = None,
    p_fragment: float = 0.15,
    arm: str = "B0",
    self_mine: bool = False,
    mine_every: int = 5,
) -> dict:
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
               "self_mine": self_mine})

    sched_rng = random.Random(seed + 777)
    epoch = 0
    while ev.evaluations < budget:
        unsolved = [t for t in tasks if not lin.pops[t].solved]
        if not unsolved:
            break
        # progress-weighted schedule: same number of generations per epoch
        # as round-robin, skewed toward near-miss tasks
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
                        for n in sol.prog.abstractions_used()
                    },
                })
        epoch += 1
        # wake-sleep: grow the central library from solutions so far
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
    summary = {
        "event": "summary", "arm": arm, "seed": seed,
        "evals": ev.evaluations, "budget": budget,
        "solved": len(solved), "solved_tasks": sorted(solved),
        "solved_phase1": sorted(by_phase["phase1"]),
        "solved_evolution": sorted(by_phase["evolution"]),
        "test_exact": test_exact, "mean_solution_len": round(mean_len, 2),
        "primitive_usage": lin.primitive_usage(),
    }
    if self_mine:
        summary["abstraction_stats"] = {lin.lineage_id: abstraction_stats(lin)}
    log.write(summary)
    log.close()
    return summary


def run_b0(seed: int, budget: int = 500_000, pop_size: int = 100,
           run_name: str | None = None, p_fragment: float = 0.15) -> dict:
    return run_single(seed, budget, pop_size, run_name, p_fragment, arm="B0")


def run_b5(seed: int, budget: int = 500_000, pop_size: int = 100,
           run_name: str | None = None) -> dict:
    """B5: single population + self-mined growing abstraction library."""
    return run_single(seed, budget, pop_size, run_name, arm="B5",
                      self_mine=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--budget", type=int, default=500_000)
    ap.add_argument("--pop", type=int, default=100)
    ap.add_argument("--arm", choices=["B0", "B5"], default="B0")
    args = ap.parse_args()
    runner = run_b5 if args.arm == "B5" else run_b0
    s = runner(seed=args.seed, budget=args.budget, pop_size=args.pop)
    print(f"{args.arm} seed={s['seed']}: solved {s['solved']}/30 "
          f"(test-exact {s['test_exact']}) in {s['evals']} evals; "
          f"mean len {s['mean_solution_len']}")
