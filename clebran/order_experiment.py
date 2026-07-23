"""Order / process experiment — "not what you know, but how you learned it".

The purest test of the reorientation (roadmap 9). Every prior experiment varied
*what* was communicated. This one holds the **content** fixed — the exact same k
prerequisite sub-tasks of a target — and varies only the **order** in which a
learner acquires them, then measures downstream **acquisition efficiency**
(evals-to-solve the target). If order matters with content held constant, that
is Chollet's "how you learned it" isolated from "what you know". If it is flat,
the thesis is null in this substrate.

Four arms, identical curriculum content and identical total budget:

    cold      no curriculum (absolute reference)
    forward   prerequisite order — foundations first (gated: a step unlocks
              once its shallower prerequisite is solved)
    reverse   hardest first (gated the other way)
    shuffled  all steps available at once, ungated (order destroyed)

All three teaching arms share the *same* task set; only the prerequisite
`score` assigned at add_task differs, which is what the order-aware gate keys
on. So this isolates order and nothing else.

Usage:
    uv run python -m clebran.order_experiment --targets 10 --seeds 1 2 3 4 5
    uv run python -m clebran.order_experiment --analyze
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

RESULTS = LOG_DIR / "order_experiment.jsonl"
ORDERS = ("cold", "forward", "reverse", "shuffled")


def _score(order: str, depth: int, depth_max: int) -> float:
    if order == "forward":
        return float(depth_max - depth + 1)   # shallow = high = unlocks first
    if order == "reverse":
        return float(depth)                    # deep = high = unlocks first
    return 0.0                                  # shuffled: all equal → nothing gated


def run_arm(
    target_id: str,
    seed: int,
    curriculum: list,
    order: str,
    total_budget: int = 500_000,
    teach_cap: int = 150_000,
    pop_size: int = 100,
) -> dict:
    target = load_task("training", target_id)
    ev = Evaluator()
    lin = Lineage(
        lineage_id=f"order-{order}-{target_id}-s{seed}",
        pool=subset_pool(), tasks={target_id: target}, seed=seed,
        pop_size=pop_size, evaluator=ev,
    )
    depth_max = max((d for d, _ in curriculum), default=1)
    for depth, t in curriculum:
        lin.add_task(t, source="teacher", score=_score(order, depth, depth_max))

    # ---- phase 1: teach in the arm's order (gated by score) ----
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
    lin.mine_own_abstractions()
    teach_used = ev.evaluations

    # ---- phase 2: test on the target, carrying the phase-1 library ----
    while ev.evaluations < total_budget and not lin.pops[target_id].solved:
        lin.step_generation(target_id)
    solved = lin.pops[target_id].solved
    return {
        "target": target_id, "seed": seed, "order": order,
        "curriculum_items": len(curriculum),
        "curriculum_solved": taught_solved,
        "teach_evals": teach_used,
        "test_evals": ev.evaluations - teach_used,
        "solved": bool(solved),
        "evals_to_solve": (ev.evaluations - teach_used) if solved else None,
    }


def pick_targets(n: int) -> list[str]:
    """Depth ≥ 3 subset tasks whose prerequisite decomposition has ≥ 2 grid
    steps — order can only matter when there is more than one thing to order."""
    progs = parse_all_solvers()
    out = []
    for r in sorted(load_subset(), key=lambda r: (r["depth"], r["task_id"])):
        if r["depth"] < 3 or r["task_id"] not in progs:
            continue
        curr = prerequisite_curriculum(
            progs[r["task_id"]], random.Random(0), n_pairs=4, max_items=5)
        if len(curr) >= 2:
            out.append(r["task_id"])
        if len(out) >= n:
            break
    return out


def run(n_targets: int, seeds: list[int], total_budget: int, teach_cap: int) -> None:
    progs = parse_all_solvers()
    targets = pick_targets(n_targets)
    with RESULTS.open("a") as fh:
        for tgt in targets:
            for seed in seeds:
                curr = prerequisite_curriculum(
                    progs[tgt], random.Random(f"{seed}:{tgt}"),
                    n_pairs=4, max_items=5)
                cells = []
                for order in ORDERS:
                    c = [] if order == "cold" else curr
                    r = run_arm(tgt, seed, c, order, total_budget, teach_cap)
                    fh.write(json.dumps(r) + "\n")
                    fh.flush()
                    ets = f"{r['evals_to_solve']:,}" if r["solved"] else "unsolved"
                    cells.append(f"{order}={ets}")
                print(f"{tgt} s{seed} ({len(curr)} steps): " + "  ".join(cells))


def _perm(a: list[float], b: list[float], N: int = 20000) -> tuple[float, float]:
    if len(a) < 2 or len(b) < 2:
        return (st.mean(a) - st.mean(b) if a and b else 0.0), 1.0
    obs = st.mean(a) - st.mean(b)
    pool = a + b
    rng = random.Random(0)
    hits = 0
    for _ in range(N):
        rng.shuffle(pool)
        if abs(st.mean(pool[:len(a)]) - st.mean(pool[len(a):])) >= abs(obs):
            hits += 1
    return obs, hits / N


def analyze(path=None) -> None:
    path = path or RESULTS
    rows = [json.loads(l) for l in path.read_text().splitlines()]
    if not rows:
        print("no order-experiment results yet")
        return
    by = {(r["target"], r["seed"], r["order"]): r for r in rows}
    keys = sorted({(r["target"], r["seed"]) for r in rows})

    print(f"{'order':9} {'n':>3} {'target solve rate':>18} "
          f"{'curriculum learned':>19} {'mean evals-to-solve':>20}")
    for o in ORDERS:
        rs = [by[(t, s, o)] for (t, s) in keys if (t, s, o) in by]
        if not rs:
            continue
        rate = sum(r["solved"] for r in rs) / len(rs)
        learned = st.mean(
            r["curriculum_solved"] / max(r["curriculum_items"], 1)
            for r in rs if r["order"] != "cold"
        ) if o != "cold" else float("nan")
        ets = [r["evals_to_solve"] for r in rs if r["evals_to_solve"] is not None]
        lp = "-" if o == "cold" else f"{learned:.0%}"
        print(f"{o:9} {len(rs):>3} {rate:>17.1%} {lp:>19} "
              f"{(f'{st.mean(ets):,.0f}' if ets else '-'):>20}")

    # cost is the endpoint: compare evals-to-solve on pairs solved by BOTH arms
    def cost(order):
        return {(r["target"], r["seed"]): r["evals_to_solve"]
                for (t, s, order_), r in by.items()
                if order_ == order and r["solved"]}

    print("\nacquisition efficiency — paired evals-to-solve "
          "(lower = learned in a way that transfers better):")
    for a, b, label in (
        ("forward", "shuffled", "ordering the SAME content vs not"),
        ("forward", "reverse", "dependency direction (foundations vs hardest first)"),
        ("forward", "cold", "well-ordered teaching vs no teaching"),
        ("shuffled", "cold", "unordered teaching vs no teaching"),
    ):
        ca, cb = cost(a), cost(b)
        common = sorted(set(ca) & set(cb))
        if len(common) < 2:
            print(f"  {a} vs {b}: too few common solves ({len(common)})")
            continue
        va = [ca[k] for k in common]
        vb = [cb[k] for k in common]
        diff, p = _perm(va, vb)
        print(f"  {a:8} - {b:8} = {diff:+9,.0f}  perm p={p:.3f}  "
              f"(n={len(common)})  [{label}]")

    print("\nProcess matters iff forward is significantly cheaper than shuffled "
          "(same content, different order). Flat = the thesis is null here.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", type=int, default=10)
    ap.add_argument("--seeds", nargs="+", type=int, default=[1, 2, 3, 4, 5])
    ap.add_argument("--total", type=int, default=500_000)
    ap.add_argument("--teach-cap", type=int, default=150_000)
    ap.add_argument("--analyze", action="store_true")
    args = ap.parse_args()
    if args.analyze:
        analyze()
    else:
        run(args.targets, args.seeds, args.total, args.teach_cap)
        analyze()
