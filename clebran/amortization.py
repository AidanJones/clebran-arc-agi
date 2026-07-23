"""Amortisation experiment (roadmap 8a) — does a curriculum pay off across N agents?

Every arm so far charged teaching to a single student, which is the worst
possible accounting for a transport mechanism: teaching cost is paid **once**,
its benefit is reaped **N times**. This measures the three quantities that make
the economics decidable, then the crossover is arithmetic.

    U  cold  — an untaught agent solves the target from scratch (full budget)
    L  learn — a taught agent's cost to work through the curriculum
    T  target— that taught agent's remaining cost to solve the target
    C  teach — the teacher's own cost to discover the solution, paid ONCE

    total for N students, taught   = C + N·(L + T)
    total for N students, untaught = N·U
    amortisation wins when          N > C / (U − L − T)
    which first requires             L + T < U      (the per-student condition)

The `cold` arm is `run_arm` with an empty curriculum: phase 1 has nothing to do,
so the whole budget goes to the target. Paired against the taught arm on the
same (target, seed) so the comparison is within-pair.

Usage:
    uv run python -m clebran.amortization --targets 8 --seeds 1 2 3 4 5
    uv run python -m clebran.amortization --analyze
"""
from __future__ import annotations

import argparse
import json
import random
import statistics as st

from .baselines.common import LOG_DIR
from .subset import load_subset
from .transfer_probe import build_curricula, pick_targets, run_arm

RESULTS = LOG_DIR / "amortization.jsonl"


def run(n_targets: int, seeds: list[int], total_budget: int, teach_cap: int) -> None:
    targets = pick_targets(n_targets)
    pool_ids = [r["task_id"] for r in load_subset()]
    with RESULTS.open("a") as fh:
        for tgt in targets:
            for seed in seeds:
                others = sorted(t for t in pool_ids if t != tgt)
                ctrl = random.Random(f"ctl:{tgt}:{seed}").choice(others)
                rel_c, _ = build_curricula(tgt, ctrl, seed)
                if not rel_c:
                    continue
                # cold: no curriculum at all — the honest untaught baseline
                cold = run_arm(tgt, seed, [], "cold", total_budget, teach_cap)
                taught = run_arm(tgt, seed, rel_c, "taught", total_budget, teach_cap)
                for r in (cold, taught):
                    fh.write(json.dumps(r) + "\n")
                fh.flush()
                print(
                    f"{tgt} s{seed}: cold {'solved' if cold['solved'] else 'no':6}"
                    f" U={cold['evals_to_solve'] or '-':>8} | "
                    f"taught {'solved' if taught['solved'] else 'no':6}"
                    f" L={taught['teach_evals']:>7,} T={taught['evals_to_solve'] or '-':>8}"
                )


def analyze(path=None, teacher_cost: float | None = None) -> None:
    path = path or RESULTS
    rows = [json.loads(l) for l in path.read_text().splitlines()]
    if not rows:
        print("no amortisation results yet")
        return
    by_key: dict[tuple, dict] = {}
    for r in rows:
        by_key[(r["target"], r["seed"], r["arm"])] = r
    pairs = []
    for (tgt, seed, arm), r in by_key.items():
        if arm != "taught":
            continue
        cold = by_key.get((tgt, seed, "cold"))
        if cold is not None:
            pairs.append((cold, r))

    both = [(c, t) for c, t in pairs if c["solved"] and t["solved"]]
    print(f"{len(pairs)} paired (target, seed) runs; both arms solved in {len(both)}")
    print(f"cold solve rate   {sum(c['solved'] for c, _ in pairs)/len(pairs):.1%}")
    print(f"taught solve rate {sum(t['solved'] for _, t in pairs):>2}/{len(pairs)}"
          f" = {sum(t['solved'] for _, t in pairs)/len(pairs):.1%}")
    if not both:
        print("\nno pairs where both solved — cannot compare per-student cost")
        return

    U = [c["evals_to_solve"] for c, _ in both]
    L = [t["teach_evals"] for _, t in both]
    T = [t["evals_to_solve"] for _, t in both]
    LT = [a + b for a, b in zip(L, T)]
    print(f"\nper-student cost on pairs where both solved (n={len(both)}):")
    print(f"  U  cold total              mean {st.mean(U):>9,.0f}  median {st.median(U):>9,.0f}")
    print(f"  L  taught: learn curriculum mean {st.mean(L):>9,.0f}  median {st.median(L):>9,.0f}")
    print(f"  T  taught: solve target     mean {st.mean(T):>9,.0f}  median {st.median(T):>9,.0f}")
    print(f"  L+T taught total            mean {st.mean(LT):>9,.0f}  median {st.median(LT):>9,.0f}")

    # per-student condition and crossover
    gain = st.mean(U) - st.mean(LT)
    C = teacher_cost if teacher_cost is not None else st.mean(U)
    print(f"\nper-student condition  L+T < U : "
          f"{'YES' if gain > 0 else 'NO'}  (U - (L+T) = {gain:+,.0f} per student)")
    if gain > 0:
        n_star = C / gain
        print(f"teacher cost C (≈ one cold solve) = {C:,.0f}")
        print(f"crossover  N* = C / (U - (L+T)) = {n_star:.1f}"
              f"  → a shared curriculum pays off from ~{max(1, int(n_star) + 1)} students on")
        print("\n  N   untaught total      taught total   winner")
        for N in (1, 2, 3, 5, 10, 25):
            un, ta = N * st.mean(U), C + N * st.mean(LT)
            print(f"  {N:>2}  {un:>15,.0f}  {ta:>15,.0f}   "
                  f"{'taught' if ta < un else 'untaught'}")
    else:
        print("teaching costs more per student than it saves — amortisation "
              "cannot rescue it at any N.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", type=int, default=8)
    ap.add_argument("--seeds", nargs="+", type=int, default=[1, 2, 3, 4, 5])
    ap.add_argument("--total", type=int, default=500_000)
    ap.add_argument("--teach-cap", type=int, default=150_000)
    ap.add_argument("--teacher-cost", type=float, default=None)
    ap.add_argument("--analyze", action="store_true")
    args = ap.parse_args()
    if args.analyze:
        analyze(teacher_cost=args.teacher_cost)
    else:
        run(args.targets, args.seeds, args.total, args.teach_cap)
        analyze(teacher_cost=args.teacher_cost)
