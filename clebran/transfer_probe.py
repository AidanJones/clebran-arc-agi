"""Paired transfer probe — does a *taught* concept transfer to a task needing it?

The curriculum frontier run found the mechanism works (lineages solved ~78% of
received teaching tasks) but bought nothing on real tasks. Two explanations are
confounded there: (a) concepts genuinely don't transfer, or (b) the curricula
were simply aimed at the wrong target — they are generated from what the
*sender solved*, and under divergence that is systematically not what the
*receiver needs*.

This probe separates them with a controlled teach → test protocol:

    phase 1 (teach)  fixed budget, evolve ONLY on curriculum tasks, in
                     prerequisite order (gated); mine the library afterwards
    phase 2 (test)   remaining budget, evolve ONLY on the target task,
                     carrying the phase-1 library (fragments + abstractions)

    taught arm    curriculum = prerequisite decomposition of the target's own
                  solver — i.e. exactly the concepts the target needs
    control arm   curriculum from an unrelated program, matched in task count,
                  budget and seed

If the taught arm solves the target more often / sooner, concepts *do* transfer
when relevant and the curriculum null is a targeting problem. If not, taught
concepts genuinely fail to transfer — a deeper finding.

Usage:
    uv run python -m clebran.transfer_probe --targets 6 --seeds 4
"""
from __future__ import annotations

import argparse
import json
import random
import statistics as st

from .baselines.common import LOG_DIR, subset_pool
from .curriculum import prerequisite_curriculum
from .data.loader import load_task
from .dsl.solver_parse import parse_all_solvers
from .fitness import Evaluator
from .lineage import Lineage
from .subset import load_subset

RESULTS = LOG_DIR / "transfer_probe.jsonl"


def build_curricula(target_id: str, control_id: str, seed: int) -> tuple[list, list]:
    """The relevant curriculum (the target's own prerequisite decomposition)
    and an unrelated control, **truncated to the same length** so the two arms
    divert identical teaching effort."""
    progs = parse_all_solvers()
    rng_a = random.Random(f"{seed}:{target_id}:rel")
    rng_b = random.Random(f"{seed}:{target_id}:ctl")
    rel = prerequisite_curriculum(progs[target_id], rng_a, n_pairs=4, max_items=4)
    ctl = prerequisite_curriculum(progs[control_id], rng_b, n_pairs=4, max_items=4)
    k = min(len(rel), len(ctl))
    return rel[:k], ctl[:k]


def run_arm(
    target_id: str,
    seed: int,
    curriculum: list,
    arm: str,
    total_budget: int = 700_000,
    teach_cap: int = 200_000,
    pop_size: int = 100,
    control_source_id: str | None = None,
) -> dict:
    """One arm: teach on `curriculum` (≤ teach_cap), then spend the *rest of the
    shared total budget* on the target. Total compute is identical across arms —
    teaching efficiently simply leaves more budget for the target, which is a
    legitimate advantage rather than a confound."""
    target = load_task("training", target_id)
    ev = Evaluator()
    lin = Lineage(
        lineage_id=f"probe-{arm}-{target_id}-s{seed}",
        pool=subset_pool(), tasks={target_id: target}, seed=seed,
        pop_size=pop_size, evaluator=ev,
    )
    depth_max = max((d for d, _ in curriculum), default=1)
    for depth, t in curriculum:
        lin.add_task(t, source="teacher", score=float(depth_max - depth + 1))

    # ---- phase 1: teach (curriculum only, prerequisite-gated) ----
    sched_rng = random.Random(seed + 31)
    cap = min(teach_cap, total_budget)
    while ev.evaluations < cap:
        aux = [t for t in lin.schedulable_tasks() if t in lin.aux_task_ids]
        if not aux:
            break
        for tid in sched_rng.sample(aux, len(aux)):
            if ev.evaluations >= cap:
                break
            lin.step_generation(tid)
    taught_solved = sum(1 for t in lin.aux_task_ids if lin.pops[t].solved)
    lin.mine_own_abstractions()          # promote what was learned to named units
    teach_used = ev.evaluations

    # ---- phase 2: test (target only, carrying the phase-1 library) ----
    while ev.evaluations < total_budget and not lin.pops[target_id].solved:
        lin.step_generation(target_id)
    solved = lin.pops[target_id].solved
    return {
        "target": target_id, "seed": seed, "arm": arm,
        "control_source": control_source_id,
        "curriculum_items": len(curriculum),
        "curriculum_solved": taught_solved,
        "teach_evals": teach_used,
        "test_evals": ev.evaluations - teach_used,
        "total_evals": ev.evaluations,
        "solved": bool(solved),
        "evals_to_solve": (ev.evaluations - teach_used) if solved else None,
        "abstractions": len(lin.abstractions),
    }


def pick_targets(n: int) -> list[str]:
    """Composition-requiring subset tasks (reference depth ≥ 3) — shallow ones
    leave no room for a taught concept to matter."""
    progs = parse_all_solvers()
    rows = [r for r in load_subset() if r["depth"] >= 3]
    rows.sort(key=lambda r: (r["depth"], r["task_id"]))
    return [r["task_id"] for r in rows if r["task_id"] in progs][:n]


def run(n_targets: int, seeds: list[int], total_budget: int, teach_cap: int) -> None:
    targets = pick_targets(n_targets)
    pool_ids = [r["task_id"] for r in load_subset()]
    with RESULTS.open("a") as fh:
        for tgt in targets:
            for seed in seeds:
                # deterministic unrelated control source, never the target
                others = sorted(t for t in pool_ids if t != tgt)
                ctrl = random.Random(f"ctl:{tgt}:{seed}").choice(others)
                rel_c, ctl_c = build_curricula(tgt, ctrl, seed)
                if not rel_c:
                    continue  # target admits no teachable decomposition
                for arm, curr in (("taught", rel_c), ("control", ctl_c)):
                    r = run_arm(
                        tgt, seed, curr, arm, total_budget, teach_cap,
                        control_source_id=None if arm == "taught" else ctrl,
                    )
                    fh.write(json.dumps(r) + "\n")
                    fh.flush()
                    print(f"{arm:7} {tgt} s{seed}: curriculum "
                          f"{r['curriculum_solved']}/{r['curriculum_items']} "
                          f"learned, teach {r['teach_evals']:,} -> target "
                          f"{'SOLVED' if r['solved'] else 'no'}")


def analyze(path=None) -> None:
    path = path or RESULTS
    rows = [json.loads(l) for l in path.read_text().splitlines()]
    if not rows:
        print("no probe results yet")
        return
    by_arm: dict[str, list[dict]] = {}
    for r in rows:
        by_arm.setdefault(r["arm"], []).append(r)

    print(f"{'arm':8} {'n':>3} {'target solve rate':>18} {'curriculum learned':>19} "
          f"{'mean evals-to-solve':>20}")
    for arm in ("taught", "control"):
        rs = by_arm.get(arm, [])
        if not rs:
            continue
        rate = sum(r["solved"] for r in rs) / len(rs)
        learned = st.mean(
            r["curriculum_solved"] / max(r["curriculum_items"], 1) for r in rs
        )
        ets = [r["evals_to_solve"] for r in rs if r["evals_to_solve"] is not None]
        print(f"{arm:8} {len(rs):>3} {rate:>17.2%} {learned:>18.0%} "
              f"{(f'{st.mean(ets):,.0f}' if ets else '-'):>20}")

    t, c = by_arm.get("taught", []), by_arm.get("control", [])
    if t and c:
        # paired by (target, seed): did teaching the *relevant* concept help?
        ct = {(r["target"], r["seed"]): r["solved"] for r in c}
        pairs = [(r["solved"], ct[(r["target"], r["seed"])])
                 for r in t if (r["target"], r["seed"]) in ct]
        wins = sum(1 for a, b in pairs if a and not b)
        losses = sum(1 for a, b in pairs if b and not a)
        both = sum(1 for a, b in pairs if a and b)
        neither = sum(1 for a, b in pairs if not a and not b)
        print(f"\npaired over {len(pairs)} (target, seed) pairs:")
        print(f"  taught-only solves : {wins}")
        print(f"  control-only solves: {losses}")
        print(f"  both / neither     : {both} / {neither}")
        print("\nTransfer shows up as taught-only >> control-only. Equal counts "
              "mean the relevant curriculum bought nothing a random one didn't.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", type=int, default=6)
    ap.add_argument("--seeds", nargs="+", type=int, default=[1, 2, 3, 4])
    ap.add_argument("--total", type=int, default=700_000)
    ap.add_argument("--teach-cap", type=int, default=200_000)
    ap.add_argument("--analyze", action="store_true")
    args = ap.parse_args()
    if args.analyze:
        analyze()
    else:
        run(args.targets, args.seeds, args.total, args.teach_cap)
        analyze()
