"""B0 — single population, all the compute (§7).

Round-robin over unsolved subset tasks, one generation each, until the
candidate-evaluation budget is exhausted or everything is solved.
"""
from __future__ import annotations

import argparse

from ..fitness import Evaluator
from ..lineage import Lineage
from .common import RunLog, subset_pool, subset_tasks


def run_b0(
    seed: int,
    budget: int = 500_000,
    pop_size: int = 100,
    run_name: str | None = None,
    p_fragment: float = 0.15,
) -> dict:
    tasks = subset_tasks()
    pool = subset_pool()
    ev = Evaluator()
    lin = Lineage(
        lineage_id=f"b0-s{seed}",
        pool=pool,
        tasks=tasks,
        seed=seed,
        pop_size=pop_size,
        evaluator=ev,
        p_fragment=p_fragment,
    )
    log = RunLog(run_name or f"b0_seed{seed}")
    log.write({"event": "start", "arm": "B0", "seed": seed, "budget": budget,
               "pool_size": len(pool), "pop_size": pop_size})

    epoch = 0
    while ev.evaluations < budget:
        unsolved = [t for t in tasks if not lin.pops[t].solved]
        if not unsolved:
            break
        for tid in unsolved:
            if ev.evaluations >= budget:
                break
            before = lin.pops[tid].solved
            lin.step_generation(tid)
            if lin.pops[tid].solved and not before:
                sol = lin.pops[tid].solution
                log.write({
                    "event": "solve", "task": tid, "epoch": epoch,
                    "evals": ev.evaluations, "len": sol.fit.length,
                    "test_exact": ev.test_exact(sol.prog, tasks[tid]),
                    "program": sol.prog.to_json(),
                })
        epoch += 1
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
    summary = {
        "event": "summary", "arm": "B0", "seed": seed,
        "evals": ev.evaluations, "budget": budget,
        "solved": len(solved), "solved_tasks": sorted(solved),
        "test_exact": test_exact, "mean_solution_len": round(mean_len, 2),
        "primitive_usage": lin.primitive_usage(),
    }
    log.write(summary)
    log.close()
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--budget", type=int, default=500_000)
    ap.add_argument("--pop", type=int, default=100)
    args = ap.parse_args()
    s = run_b0(seed=args.seed, budget=args.budget, pop_size=args.pop)
    print(f"B0 seed={s['seed']}: solved {s['solved']}/30 "
          f"(test-exact {s['test_exact']}) in {s['evals']} evals; "
          f"mean len {s['mean_solution_len']}")
