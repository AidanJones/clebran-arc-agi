"""Arm runners B1–B4 (§7) — thin wrappers over the orchestrator — and the
matched-compute sweep driver used for the H2/H3 table.

  B1: N isolated lineages (CH-NONE), best-of-ensemble union
  B2: N lineages + CH-CONSTRAINED, fragment payload   (main treatment)
  B3: N lineages + CH-UNCONSTRAINED, fragment payload (tests H3)
  B4: N lineages + CH-CONSTRAINED, signal payload
"""
from __future__ import annotations

import argparse
import json

from ..channel import make_channel
from ..orchestrator import run_multi
from .b0 import run_b0, run_b5, run_b5_dream, run_b5_dream_near_miss
from .b5_planner import run_single as run_b5_planner
from .b5_l1_proposer import run_single as run_b5_l1_proposer
from .b5_l1_planner import run_single as run_b5_l1_planner
from .common import LOG_DIR, run_prefix

ARM_CHANNEL = {
    "B1": dict(kind="none"),
    "B2": dict(kind="constrained", payload="fragment"),
    "B3": dict(kind="unconstrained", payload="fragment"),
    "B4": dict(kind="constrained", payload="signal"),
    # recovered-primitive channel (roadmap item 3): lineages gossip their own
    # discovered subroutines. B6 constrained vs B7 unconstrained is the H3
    # test on a *discovered* vocabulary. (B5 is reserved for Stitch, spec §7.)
    "B6": dict(kind="constrained", payload="abstraction"),
    "B7": dict(kind="unconstrained", payload="abstraction"),
    # curriculum channel (roadmap 7b): lineages communicate by exporting
    # synthetic tasks that show what they learned. B8 constrained vs B9
    # unconstrained is the H3 test on *teaching sets*.
    "B8": dict(kind="constrained", payload="curriculum"),
    "B9": dict(kind="unconstrained", payload="curriculum"),
}


def run_arm(
    arm: str,
    seed: int,
    budget: int,
    n_lineages: int = 3,
    pop_size: int = 100,
    frag_k: int = 4,
    frag_m: int = 3,
) -> dict:
    if arm == "B0":
        return run_b0(seed=seed, budget=budget, pop_size=pop_size)
    if arm == "B5":
        return run_b5(seed=seed, budget=budget, pop_size=pop_size)
    if arm == "B5D":
        return run_b5_dream(seed=seed, budget=budget, pop_size=pop_size)
    if arm == "B5D-NM":
        return run_b5_dream_near_miss(seed=seed, budget=budget, pop_size=pop_size)
    if arm == "B5P":
        return run_b5_planner(seed=seed, budget=budget, pop_size=pop_size)
    if arm == "B5L1":
        return run_b5_l1_proposer(seed=seed, budget=budget, pop_size=pop_size)
    if arm == "B5L1P":
        return run_b5_l1_planner(seed=seed, budget=budget, pop_size=pop_size)
    spec = dict(ARM_CHANNEL[arm])
    kind = spec.pop("kind")
    if kind == "constrained":
        chan = make_channel(kind, max_fragment_size=frag_k, max_messages=frag_m, **spec)
    else:
        chan = make_channel(kind, **spec)
    return run_multi(
        arm=arm,
        channel=chan,
        seed=seed,
        n_lineages=n_lineages,
        budget=budget,
        pop_size=pop_size,
        max_frag_size=frag_k,
        run_name=f"{run_prefix()}{arm.lower()}_seed{seed}",
    )


def sweep(arms: list[str], seeds: list[int], budget: int, **kw) -> None:
    results = []
    for arm in arms:
        for seed in seeds:
            s = run_arm(arm, seed, budget, **kw)
            print(
                f"{arm} seed={seed}: solved "
                f"{s.get('solved_union', s.get('solved'))}/30 "
                f"evals={s['evals']}"
            )
            results.append(s)
    out = LOG_DIR / "sweep_results.jsonl"
    with out.open("a") as fh:
        for r in results:
            fh.write(json.dumps(r) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", nargs="+", default=["B0", "B1", "B2"])
    ap.add_argument("--seeds", nargs="+", type=int, default=[1, 2, 3, 4, 5])
    ap.add_argument("--budget", type=int, default=500_000)
    ap.add_argument("--lineages", type=int, default=3)
    ap.add_argument("--pop", type=int, default=100)
    args = ap.parse_args()
    sweep(
        args.arms, args.seeds, args.budget,
        n_lineages=args.lineages, pop_size=args.pop,
    )
