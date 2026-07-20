"""Recovered-primitive frontier sweep (roadmap item 3 payoff measurement).

Compares, on the D2/D3 frontier at matched compute, whether a *discovered*
vocabulary helps and whether the constraint matters for it:

    B0  single population (reference)
    B1  isolated lineages (no channel)
    B2  constrained channel, fragment payload   (given-primitive transfer)
    B6  constrained channel, abstraction payload (recovered-primitive transfer)
    B7  unconstrained channel, abstraction payload

Key comparisons (on evolution-phase solves — the only place a channel can act):
    B6 > B1   recovered-primitive transfer helps
    B6 vs B2  recovered vs given-primitive transfer
    B6 > B7   the constraint matters for a discovered vocabulary (H3)

This is compute-heavy (5 arms × N seeds × ~3M evals ≈ several hours). Launch
the runs in parallel with scripts/frontier_recovered_sweep.sh (it sets
CLEBRAN_SUBSET=frontier_subset), then `--analyze`.

    CLEBRAN_SUBSET=frontier_subset uv run python -m clebran.baselines.frontier_sweep --run  --arm B6 --seed 1 --budget 3000000
    uv run python -m clebran.baselines.frontier_sweep --analyze
"""
from __future__ import annotations

import argparse
import json
import statistics as st

from ..metrics.report import _recovery_table
from .arms import run_arm
from .common import LOG_DIR

ARMS = ["B0", "B1", "B2", "B6", "B7"]


def _summaries() -> dict[str, list[dict]]:
    """Latest summary per arm×seed from the frontier_*_seed*.jsonl logs."""
    by_arm: dict[str, list[dict]] = {}
    for arm in ARMS:
        rows = []
        for path in sorted(LOG_DIR.glob(f"frontier_{arm.lower()}_seed*.jsonl")):
            lines = path.read_text().splitlines()
            for line in reversed(lines):
                r = json.loads(line)
                if r.get("event") == "summary":
                    rows.append(r)
                    break
        if rows:
            by_arm[arm] = rows
    return by_arm


def _evo(r: dict) -> float:
    return float(len(r.get("solved_evolution", [])))


def _fmt(vals: list[float]) -> str:
    if not vals:
        return "-"
    if len(vals) == 1:
        return f"{vals[0]:.2f}"
    return f"{st.mean(vals):.2f}±{st.stdev(vals):.2f}"


def _cmp(by_arm, a, b, f) -> str | None:
    if a not in by_arm or b not in by_arm:
        return None
    da, db = [f(r) for r in by_arm[a]], [f(r) for r in by_arm[b]]
    if len(da) < 2 or len(db) < 2:
        return f"{a}={st.mean(da):.2f} vs {b}={st.mean(db):.2f} (too few seeds)"
    diff = st.mean(da) - st.mean(db)
    se = ((st.stdev(da) ** 2 / len(da)) + (st.stdev(db) ** 2 / len(db))) ** 0.5
    sig = "significant" if se > 0 and abs(diff) > 2 * se else "not significant"
    return f"{a}-{b} = {diff:+.2f} ({sig}; se {se:.2f})"


def analyze() -> None:
    by_arm = _summaries()
    if not by_arm:
        print("no frontier_*_seed*.jsonl logs yet — run the sweep first")
        return
    print(f"{'arm':4} {'n':>2} {'solved/30':>12} {'evo-solved':>12} "
          f"{'reuse':>10}")
    for arm in ARMS:
        rs = by_arm.get(arm)
        if not rs:
            continue
        solved = [float(r.get("solved_union", r.get("solved", 0))) for r in rs]
        evo = [_evo(r) for r in rs]
        reuse = [r["reuse_rate"] for r in rs if "reuse_rate" in r]
        print(f"{arm:4} {len(rs):>2} {_fmt(solved):>12} {_fmt(evo):>12} "
              f"{(_fmt(reuse) if reuse else '-'):>10}")

    evals = [r["evals"] for rs in by_arm.values() for r in rs]
    if evals:
        spread = (max(evals) - min(evals)) / max(evals)
        print(f"\ncompute audit: eval spread {spread:.2%} "
              f"({'PASS' if spread <= 0.01 else 'FAIL'} ±1%)")

    print("\nevolution-phase solve comparisons:")
    for a, b, label in (
        ("B6", "B1", "recovered-primitive transfer helps"),
        ("B6", "B2", "recovered vs given-primitive transfer"),
        ("B6", "B7", "constraint matters for a discovered vocabulary (H3)"),
        ("B2", "B1", "given-primitive transfer helps (H2)"),
    ):
        v = _cmp(by_arm, a, b, _evo)
        if v:
            print(f"  {v}   [{label}]")

    _recovery_table(by_arm)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--analyze", action="store_true")
    ap.add_argument("--arm", default="B6")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--budget", type=int, default=3_000_000)
    ap.add_argument("--pop", type=int, default=100)
    args = ap.parse_args()
    if args.run:
        s = run_arm(args.arm, args.seed, args.budget, pop_size=args.pop)
        print(f"{args.arm} seed={args.seed}: "
              f"solved {s.get('solved_union', s.get('solved'))}/30 "
              f"evo {len(s.get('solved_evolution', []))} "
              f"reuse {s.get('reuse_rate', '-')}")
    if args.analyze or not args.run:
        analyze()
