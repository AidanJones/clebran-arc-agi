"""Aggregate sweep results into the H2/H3 comparison table (§7, §8.1).

Reads logs/sweep_results.jsonl (one summary per arm×seed) and prints:
  - solve rate per arm, mean ± sd over seeds
  - compute-matching audit (total evals within ±1% across arms)
  - reuse rate for channel arms
  - divergence stats for multi-lineage arms
  - the H2/H3 verdicts per the §7 decision rules
  - cost axis (roadmap §9a): evals-per-solve column
"""
from __future__ import annotations

import json
import statistics as st
from collections import defaultdict

from ..baselines.common import LOG_DIR


def load_results(path=None) -> dict[str, list[dict]]:
    path = path or (LOG_DIR / "sweep_results.jsonl")
    by_arm: dict[str, list[dict]] = defaultdict(list)
    seen = {}
    for line in path.read_text().splitlines():
        r = json.loads(line)
        seen[(r["arm"], r["seed"])] = r  # keep latest per arm×seed
    for (arm, _), r in sorted(seen.items()):
        by_arm[arm].append(r)
    return by_arm


def _solved(r: dict) -> int:
    return r.get("solved_union", r.get("solved"))


def _fmt(vals: list[float]) -> str:
    if len(vals) == 1:
        return f"{vals[0]:.2f}"
    return f"{st.mean(vals):.2f} ± {st.stdev(vals):.2f}"


def _evo_solved(r: dict) -> float | None:
    """Count of tasks the arm reached only via the evolutionary loop
    (None for older logs that predate phase tagging)."""
    if "solved_evolution" in r:
        return float(len(r["solved_evolution"]))
    return None


def _evals_per_solve(r: dict) -> float | None:
    """Coarse cost axis: total evals / solved count (roadmap §9a).

    Only defined for arms that solved at least one task.
    """
    s = _solved(r)
    if s == 0:
        return None
    return r["evals"] / s


def report(path=None) -> dict:
    by_arm = load_results(path)
    print(
        f"{'arm':4} {'n':>2} {'solved/30':>14} {'evo-solved':>12} "
        f"{'test-exact':>14} {'evals':>12} {'evals/solve':>15} "
        f"{'reuse':>8} {'jaccard':>8}"
    )
    stats = {}
    for arm in sorted(by_arm):
        rs = by_arm[arm]
        solved = [float(_solved(r)) for r in rs]
        evo = [_evo_solved(r) for r in rs if _evo_solved(r) is not None]
        test = [float(r.get("test_exact", 0)) for r in rs]
        evals = [r["evals"] for r in rs]
        # Cost axis (roadmap §9a): evals-per-solve, computed only for
        # seeds that solved at least one task. SD reflects variance
        # *conditional on* solving, not a mix of 0 and non-zero outcomes.
        eps = [
            _evals_per_solve(r) for r in rs if _evals_per_solve(r) is not None
        ]
        eps_fmt = (
            _fmt(eps) if eps else "-"
        )
        reuse = [r["reuse_rate"] for r in rs if "reuse_rate" in r]
        jac = [r["divergence"]["mean"] for r in rs if "divergence" in r]
        stats[arm] = {
            "n": len(rs), "solved": solved, "mean": st.mean(solved),
            "evo": evo, "evals": evals, "evals_per_solve": eps,
        }
        print(
            f"{arm:4} {len(rs):>2} {_fmt(solved):>14} "
            f"{(_fmt(evo) if evo else '-'):>12} {_fmt(test):>14} "
            f"{int(st.mean(evals)):>12} {eps_fmt:>15} "
            f"{(_fmt(reuse) if reuse else '-'):>8} "
            f"{(_fmt(jac) if jac else '-'):>8}"
        )

    # compute-matching audit
    all_means = [st.mean(s["evals"]) for s in stats.values()]
    if len(all_means) > 1:
        spread = (max(all_means) - min(all_means)) / max(all_means)
        print(f"\ncompute audit: mean-evals spread across arms = "
              f"{spread:.2%} ({'PASS' if spread <= 0.01 else 'FAIL'} ±1%)")

    verdicts = {}
    def cmp(a: str, b: str, metric: str = "solved") -> str | None:
        if a not in stats or b not in stats:
            return None
        da, db = stats[a][metric], stats[b][metric]
        if len(da) < 2 or len(db) < 2:
            return f"{a}={st.mean(da):.2f} vs {b}={st.mean(db):.2f} (too few seeds)"
        diff = st.mean(da) - st.mean(db)
        # Welch t-ish heuristic: difference vs pooled sd
        sd = ((st.stdev(da) ** 2 / len(da)) + (st.stdev(db) ** 2 / len(db))) ** 0.5
        sig = "significant" if sd > 0 and abs(diff) > 2 * sd else "not significant"
        return f"{a}-{b} = {diff:+.2f} ({sig}; pooled se {sd:.2f})"

    for metric, label in (("solved", "all solves"),
                          ("evo", "evolution-phase solves only")):
        if metric == "evo" and not all(stats[a]["evo"] for a in stats):
            continue  # no phase data yet
        print(f"\n=== {label} ===")
        print("H2 (transfer helps): supported iff B2 > B1 and B2 > B0")
        for pair in (("B2", "B1"), ("B2", "B0")):
            v = cmp(*pair, metric=metric)
            if v:
                print("  ", v)
                verdicts[f"{metric}:{pair[0]}>{pair[1]}"] = v
        print("H3 (constraint matters): supported iff B2 > B3")
        v = cmp("B2", "B3", metric=metric)
        if v:
            print("  ", v)
            verdicts[f"{metric}:B2>B3"] = v

    # Cost axis (roadmap §9a): lower evals/solve = better. H2 transfer
    # is *cheaper* if B2 < B1; H3 constraint is *cheaper* if B2 < B3.
    if {"B0", "B1", "B2"} <= set(stats):
        print(
            "\n=== cost axis (evals/solve; lower = better) ==="
        )
        for a, b, lbl in (("B2", "B1", "H2: B2 < B1 (cheaper)"),
                          ("B2", "B0", "H2: B2 < B0 (cheaper)"),
                          ("B2", "B3", "H3: B2 < B3 (cheaper)")):
            v = cmp(a, b, metric="evals_per_solve")
            if v:
                print("  ", lbl, v)
    _recovery_table(by_arm)
    return {"stats": {k: v["mean"] for k, v in stats.items()}, "verdicts": verdicts}


def _recovery_table(by_arm: dict) -> None:
    """Recovered-vocabulary stats for abstraction-payload arms (B6/B7)."""
    def mean_of(rows, f):
        vals = [f(r) for r in rows if f(r) is not None]
        return sum(vals) / len(vals) if vals else None

    def arm_row(rs):
        stats = [
            v for r in rs for v in r.get("abstraction_stats", {}).values()
            if v.get("n", 0) > 0
        ]
        if not stats:
            return None
        topsims = [s["topsim"] for s in stats if s.get("topsim") is not None]
        return {
            "vocab": mean_of(stats, lambda s: s["n"]),
            "used_rate": mean_of(stats, lambda s: s.get("used_rate")),
            "cross_task": mean_of(stats, lambda s: s.get("reused_across_tasks")),
            "recv_used": mean_of(stats, lambda s: s.get("received_used")),
            "topsim": (sum(topsims) / len(topsims)) if topsims else None,
        }

    rows = {arm: arm_row(rs) for arm, rs in by_arm.items()}
    rows = {a: r for a, r in rows.items() if r}
    if not rows:
        return
    print("\n=== recovered vocabulary (abstraction-payload arms) ===")
    print(f"{'arm':4} {'vocab':>7} {'used-rate':>10} {'cross-task':>11} "
          f"{'recv-used':>10} {'topsim':>8}")
    for arm in sorted(rows):
        r = rows[arm]
        def f(x, p=2):
            return "-" if x is None else f"{x:.{p}f}"
        print(f"{arm:4} {f(r['vocab']):>7} {f(r['used_rate']):>10} "
              f"{f(r['cross_task']):>11} {f(r['recv_used']):>10} "
              f"{f(r['topsim']):>8}")


if __name__ == "__main__":
    report()
