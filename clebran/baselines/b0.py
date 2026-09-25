"""B0 — single population, all the compute (§7).

Round-robin over unsolved subset tasks, one generation each, until the
candidate-evaluation budget is exhausted or everything is solved.

B5 — the Stitch central-library control (§7): the *same* single population,
but it periodically mines its own solutions into a growing abstraction
library (the compression miner) and reuses it in further search — a
DreamCoder/Stitch wake-sleep analogue with no multi-agent divergence and no
channel. B5 vs B6/B7 isolates whether the divergence + communication
structure adds anything over centralized abstraction reuse alone.

B5D — B5 + *dreaming* (roadmap §9b): after every solve, the lineage
synthesises a variant task from its own solution (DreamCoder wake/sleep
"fantasies") and adds it to its task pool. The synthetic task costs real
candidate-evaluations when the lineage works on it (matched compute), so
this measures whether *self-directed practice* buys more than practising
on the original frontier — the "how you learned it" capability gap.

B5D-NM — B5D + *failure-mode dreaming* (roadmap §9b extension, the
discovery-bottleneck principle #1): the lineage additionally dreams from
*near-miss* programs — high-fitness but not-fully-correct individuals
representing the loci of *why* the lineage fails on a task. Variants of
the near-miss force the lineage to bridge the gap; bridging is where new
primitives are discovered. This is a primitive version of the L3 evoker
(9f.4): a lineage that practises on its own failures, not its successes.
"""
from __future__ import annotations

import argparse
import random

from ..curriculum import generate_task
from ..fitness import Evaluator
from ..lineage import Lineage
from ..metrics.recovery import abstraction_stats
from .common import RunLog, run_prefix, subset_pool, subset_tasks


def _budget_suffix(budget: int) -> str:
    """Return a budget-suffixed log-name tag so runs at different budgets
    don't overwrite each other. e.g. 4_000_000 -> '4m', 1_000_000 -> '1m',
    500_000 -> '500k', anything else -> str(budget)."""
    if budget % 1_000_000 == 0:
        return f"{budget // 1_000_000}m"
    if budget % 1_000 == 0:
        return f"{budget // 1_000}k"
    return str(budget)


def run_single(
    seed: int,
    budget: int = 500_000,
    pop_size: int = 100,
    run_name: str | None = None,
    p_fragment: float = 0.15,
    arm: str = "B0",
    self_mine: bool = False,
    mine_every: int = 5,
    dream: bool = False,
    dream_source: str = "solved",
    dream_near_miss_min: float = 0.4,
    dream_near_miss_aggressive: bool = False,
    lam_mdl: float = 1.05,
    fitness_mode: str = "accuracy",
) -> dict:
    tasks = subset_tasks()
    pool = subset_pool()
    ev = Evaluator(lam_mdl=lam_mdl, fitness_mode=fitness_mode)
    lin = Lineage(
        lineage_id=f"{arm.lower()}-s{seed}",
        pool=pool,
        tasks=tasks,
        seed=seed,
        pop_size=pop_size,
        evaluator=ev,
        p_fragment=p_fragment,
        fitness_mode=fitness_mode,
    )
    log = RunLog(
        run_name
        or f"{run_prefix()}{arm.lower()}_{_budget_suffix(budget)}_seed{seed}"
    )
    log.write({"event": "start", "arm": arm, "seed": seed, "budget": budget,
               "pool_size": len(pool), "pop_size": pop_size,
               "self_mine": self_mine, "dream": dream,
               "dream_source": dream_source,
               "dream_near_miss_min": dream_near_miss_min})

    sched_rng = random.Random(seed + 777)
    # Independent RNG for dream-task generation (deterministic, isolated
    # from the scheduling RNG so dream count and identity are reproducible
    # given the seed).
    dream_rng = random.Random(seed + 31337) if dream else None
    # Failure-mode dreaming: track per-task last-dreamed-from program hash
    # so we don't re-dream from the same near-miss every epoch. Dream only
    # fires when the best near-miss for a task has *changed* (got better).
    near_miss_last_hash: dict[str, str] = {}
    near_miss_synthesised = 0
    n_dream_added = 0
    n_dream_solved = 0

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
            # In novelty mode, pop.solved rarely flips (the most-novel
            # individual is unlikely to also be a solver). Track test-exact
            # archive size instead so we still emit a solve event when a
            # *test-exact* solver appears (regardless of whether it's the
            # most-novel individual in the population).
            te_before = ev.test_exact_count(tasks[tid])
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
            elif ev.fitness_mode == "novelty":
                # Novelty mode: emit a solve event whenever a *new*
                # test-exact solver appears for this task (pop.solved
                # doesn't track it). Use the most-novel individual
                # (pop.individuals[0]) as the reference for length,
                # since pop.solution is only set on accuracy-mode
                # solves.
                te_after = ev.test_exact_count(tasks[tid])
                if te_after > te_before:
                    ind = lin.pops[tid].individuals[0] if lin.pops[tid].individuals else None
                    log.write({
                        "event": "solve", "task": tid, "epoch": epoch,
                        "evals": ev.evaluations,
                        "len": ind.fit.length if ind else 0,
                        "phase": "novelty",
                        "test_exact": True,
                        "n_test_exact_for_task": te_after,
                    })
                # ----- dreaming hook (roadmap §9b) -----
                # After every solve, synthesise a variant task from the
                # just-solved program and add it to the lineage's task
                # pool. The synthetic task costs real candidate-evaluations
                # when the lineage works on it (matched compute vs B5).
                # The dream-task *generation* itself is "free" — it calls
                # `run_safe` directly, not through the Evaluator.
                if dream_rng is not None and dream_source in ("solved", "both"):
                    synth = generate_task(
                        sol.prog, dream_rng,
                        abstractions=lin.abstractions,
                        n_pairs=4,
                    )
                    if synth is not None:
                        # auxiliary=False so the task joins the real task
                        # pool (no prerequisite gating). source="dream_solved"
                        # so we can analyse solved-source vs near-miss-source
                        # dreams separately.
                        added = lin.add_task(
                            synth, auxiliary=False, source="dream_solved",
                            score=float(sol.fit.length),
                        )
                        if added:
                            tasks[synth.task_id] = synth
                            n_dream_added += 1
                            log.write({
                                "event": "dream_add",
                                "task": synth.task_id,
                                "from_solve": tid,
                                "epoch": epoch,
                                "evals": ev.evaluations,
                                "n_pairs": len(synth.train) + len(synth.test),
                                "source": "dream_solved",
                            })
        epoch += 1
        # ----- failure-mode dreaming hook (roadmap §9b #1) -----
        # At the end of each epoch, for each unsolved task, find the best
        # near-miss (solved_frac >= dream_near_miss_min but not solved_all).
        # If it's a *new* near-miss (program hash differs from last epoch's),
        # dream from it. This forces the lineage to practise on its own
        # failures: variants of the near-miss are easy-to-evaluate tasks
        # the lineage already has a partial answer for. Bridging the gap
        # is where new primitives are discovered (the discovery-bottleneck
        # principle, README §"The discovery bottleneck").
        if dream_rng is not None and dream_source in ("near_miss", "both"):
            for tid in list(tasks):
                if lin.pops[tid].solved:
                    continue
                pop = lin.pops[tid]
                if not pop.individuals:
                    continue
                # Pick the best individual by fitness key.
                best = max(pop.individuals, key=lambda ind: ind.fit.key)
                if best.fit.solved_frac < dream_near_miss_min:
                    continue
                if best.fit.solved_all:
                    continue  # already a solver; would be picked up by the solved-source path
                # Drop the "hash differs" check if aggressive=True: dream from
                # each task's best near-miss every epoch (more dreams, more
                # material for discovery).
                if not dream_near_miss_aggressive:
                    prog_hash = best.prog.to_json()  # JSON is stable, used as hash
                    if near_miss_last_hash.get(tid) == prog_hash:
                        continue  # same near-miss as last epoch; skip
                    near_miss_last_hash[tid] = prog_hash
                synth = generate_task(
                    best.prog, dream_rng,
                    abstractions=lin.abstractions,
                    n_pairs=4,
                )
                if synth is not None:
                    added = lin.add_task(
                        synth, auxiliary=False, source="dream_near_miss",
                        score=float(best.fit.solved_frac),
                    )
                    if added:
                        tasks[synth.task_id] = synth
                        n_dream_added += 1
                        near_miss_synthesised += 1
                        log.write({
                            "event": "dream_add",
                            "task": synth.task_id,
                            "from_solve": tid,
                            "epoch": epoch,
                            "evals": ev.evaluations,
                            "n_pairs": len(synth.train) + len(synth.test),
                            "source": "dream_near_miss",
                            "source_solved_frac": round(best.fit.solved_frac, 3),
                        })
        # wake-sleep: grow the central library from solutions so far
        if self_mine and epoch % mine_every == 0:
            lin.mine_own_abstractions()
        log.write({
            "event": "epoch", "epoch": epoch, "evals": ev.evaluations,
            "solved": len(lin.solved_tasks()),
            "n_dream_added": n_dream_added,
            "n_dream_near_miss": near_miss_synthesised,
        })

    if ev.fitness_mode == "novelty":
        # Novelty mode: pop.solution is the most-novel individual, not
        # necessarily a solver. The test-exact archive (populated whenever
        # *any* candidate passes all train + test pairs, regardless of mode)
        # is the source of truth for test-exact solves.
        solved_real = {tid for tid in ev.test_exact_tasks()
                       if not tid.startswith("gen_")}
        test_exact = len(solved_real)
        # Phase bookkeeping is undefined in novelty mode (no "best" program).
        by_phase_real = {"phase1": set(), "evolution": set()}
        mean_len = 0.0
        summary = {
            "event": "summary", "arm": arm, "seed": seed,
            "evals": ev.evaluations, "budget": budget,
            "solved": len(solved_real),
            "solved_tasks": sorted(solved_real),
            "solved_phase1": [],
            "solved_evolution": [],
            "solved_dream": [],
            "n_dream_added": n_dream_added,
            "n_dream_solved": 0,
            "n_dream_near_miss_synthesised": near_miss_synthesised,
            "test_exact": test_exact,
            "mean_solution_len": 0.0,
            "novelty_archive_size": sum(
                ev.novelty_archive_size(tasks[tid]) for tid in tasks
            ),
            "novelty_archive_per_task": {
                tid: ev.novelty_archive_size(tasks[tid]) for tid in tasks
            },
            "primitive_usage": lin.primitive_usage(),
        }
        if self_mine:
            summary["abstraction_stats"] = {lin.lineage_id: abstraction_stats(lin)}
        log.write(summary)
        log.close()
        return summary

    solved = lin.solved_tasks()
    # Split solved into real (frontier) vs dream-sourced, by task-ID prefix.
    solved_real = {t for t in solved if not t.startswith("gen_")}
    solved_dream = {t for t in solved if t.startswith("gen_")}
    test_exact = sum(
        1 for tid in solved_real
        if ev.test_exact(lin.pops[tid].solution.prog, tasks[tid])
    )
    mean_len = (
        sum(lin.pops[t].solution.fit.length for t in solved_real) / len(solved_real)
        if solved_real else 0.0
    )
    by_phase = lin.solved_by_phase()
    by_phase_real = {
        k: {t for t in v if not t.startswith("gen_")} for k, v in by_phase.items()
    }
    summary = {
        "event": "summary", "arm": arm, "seed": seed,
        "evals": ev.evaluations, "budget": budget,
        # Headline "solved frontier tasks" — dream tasks excluded.
        "solved": len(solved_real),
        "solved_tasks": sorted(solved_real),
        "solved_phase1": sorted(by_phase_real["phase1"]),
        "solved_evolution": sorted(by_phase_real["evolution"]),
        # Dream bookkeeping.
        "solved_dream": sorted(solved_dream),
        "n_dream_added": n_dream_added,
        "n_dream_solved": len(solved_dream),
        "n_dream_near_miss_synthesised": near_miss_synthesised,
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
           run_name: str | None = None,
           lam_mdl: float = 1.05) -> dict:
    """B5: single population + self-mined growing abstraction library.

    `lam_mdl` is the NEO-style adaptive-length factor: tiebreak is
    `cell_acc * lam_mdl^(-len)`. Default 1.05. Larger values push
    harder for shorter programs (more compositional search).
    """
    return run_single(seed, budget, pop_size, run_name, arm="B5",
                      self_mine=True, lam_mdl=lam_mdl)


def run_b5_dream(seed: int, budget: int = 500_000, pop_size: int = 100,
                 run_name: str | None = None,
                 lam_mdl: float = 1.05) -> dict:
    """B5D: B5 + dreaming (roadmap §9b).

    After every solve, the lineage synthesises a variant task from its
    own solution and adds it to its task pool. The synthetic task costs
    real candidate-evaluations when the lineage works on it (matched
    compute vs B5).
    """
    return run_single(seed, budget, pop_size, run_name, arm="B5D",
                      self_mine=True, dream=True, dream_source="solved",
                      lam_mdl=lam_mdl)


def run_b5_novelty(seed: int, budget: int = 500_000, pop_size: int = 100,
                   run_name: str | None = None,
                   lam_mdl: float = 1.05) -> dict:
    """B5N: B5 + novelty-search primary score (roadmap §1 #4, discovery-
    bottleneck menu).

    Same lineage machinery as B5 (central library, library mining,
    AOS, fragment injection, restart, hall-of-fame) but the
    primary selection criterion is *behavioral novelty* (mean
    nearest-neighbor Hamming distance to the population's outputs on
    the task) instead of task accuracy. Tests whether searching the
    program space by diversity finds anything test-exact that B5
    doesn't. Library mining stays accuracy-driven (only programs that
    solve all train pairs are mined into the library).
    """
    return run_single(seed, budget, pop_size, run_name, arm="B5N",
                      self_mine=True, lam_mdl=lam_mdl,
                      fitness_mode="novelty")


def run_b5_dream_near_miss(seed: int, budget: int = 500_000, pop_size: int = 100,
                            run_name: str | None = None,
                            near_miss_min: float = 0.4,
                            aggressive: bool = False,
                            lam_mdl: float = 1.05) -> dict:
    """B5D-NM: B5 + failure-mode dreaming (roadmap §9b #1).

    Like B5D, but the lineage dreams from *near-miss* programs (high
    fitness but not fully correct) instead of from solved programs.
    Variants of the near-miss force the lineage to practise on its own
    failures; bridging the gap is where new primitives are discovered
    (the discovery-bottleneck principle, README §"The discovery bottleneck").

    A primitive version of the L3 evoker (9f.4): a lineage that
    practises on its own failures, not its successes.

    If `aggressive=True`, drops the "hash differs" check: dreams from
    each task's best near-miss every epoch (more dreams, more material
    for discovery). The default (aggressive=False) only dreams when
    the near-miss has *improved* since last epoch.
    """
    return run_single(
        seed, budget, pop_size, run_name,
        arm="B5D-NM", self_mine=True, dream=True,
        dream_source="near_miss", dream_near_miss_min=near_miss_min,
        dream_near_miss_aggressive=aggressive, lam_mdl=lam_mdl,
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--budget", type=int, default=500_000)
    ap.add_argument("--pop", type=int, default=100)
    ap.add_argument(
        "--arm", choices=["B0", "B5", "B5N", "B5D", "B5D-NM"], default="B0",
    )
    ap.add_argument(
        "--near-miss-min", type=float, default=0.4,
        help="Minimum solved_frac for a near-miss to qualify (default 0.4).",
    )
    ap.add_argument(
        "--aggressive", action="store_true",
        help="Drop the 'hash differs' check: dream from each task's best near-miss every epoch.",
    )
    ap.add_argument(
        "--lam-mdl", type=float, default=None,
        help="Override the NEO adaptive-length factor (default 1.05 for B5; "
             "higher values push harder for shorter programs).",
    )
    args = ap.parse_args()
    if args.arm == "B5":
        runner = (lambda **kw: run_b5(lam_mdl=args.lam_mdl or 1.05, **kw))
    elif args.arm == "B5N":
        runner = (lambda **kw: run_b5_novelty(lam_mdl=args.lam_mdl or 1.05, **kw))
    elif args.arm == "B5D":
        runner = lambda **kw: run_b5_dream(
            lam_mdl=args.lam_mdl or 1.05, **kw
        )
    elif args.arm == "B5D-NM":
        runner = lambda **kw: run_b5_dream_near_miss(
            near_miss_min=args.near_miss_min, aggressive=args.aggressive,
            lam_mdl=args.lam_mdl or 1.05, **kw
        )
    else:
        runner = run_b0
    s = runner(seed=args.seed, budget=args.budget, pop_size=args.pop)
    extra = ""
    if args.arm in ("B5D", "B5D-NM"):
        extra = (
            f" dream_added={s.get('n_dream_added', 0)} "
            f"dream_solved={s.get('n_dream_solved', 0)}"
            f" dream_near_miss={s.get('n_dream_near_miss_synthesised', 0)}"
        )
    print(f"{args.arm} seed={s['seed']}: solved {s['solved']}/30 "
          f"(test-exact {s['test_exact']}) in {s['evals']} evals; "
          f"mean len {s['mean_solution_len']}{extra}")
