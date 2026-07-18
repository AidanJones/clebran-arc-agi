"""Aggregate sweep results into the H2/H3 comparison table (§7, §8.1).

Reads logs/sweep_results.jsonl (one summary per arm×seed) and prints:
  - solve rate per arm, mean ± sd over seeds
  - compute-matching audit (total evals within ±1% across arms)
  - reuse rate for channel arms
  - divergence stats for multi-lineage arms
  - the H2/H3 verdicts per the §7 decision rules
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


def report(path=None) -> dict:
    by_arm = load_results(path)
    print(f"{'arm':4} {'n':>2} {'solved/30':>14} {'test-exact':>14} "
          f"{'evals':>12} {'reuse':>8} {'jaccard':>8}")
    stats = {}
    for arm in sorted(by_arm):
        rs = by_arm[arm]
        solved = [float(_solved(r)) for r in rs]
        test = [float(r.get("test_exact", 0)) for r in rs]
        evals = [r["evals"] for r in rs]
        reuse = [r["reuse_rate"] for r in rs if "reuse_rate" in r]
        jac = [r["divergence"]["mean"] for r in rs if "divergence" in r]
        stats[arm] = {
            "n": len(rs), "solved": solved, "mean": st.mean(solved),
            "evals": evals,
        }
        print(
            f"{arm:4} {len(rs):>2} {_fmt(solved):>14} {_fmt(test):>14} "
            f"{int(st.mean(evals)):>12} "
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
    def cmp(a: str, b: str) -> str | None:
        if a not in stats or b not in stats:
            return None
        da, db = stats[a]["solved"], stats[b]["solved"]
        if len(da) < 2 or len(db) < 2:
            return f"{a}={st.mean(da):.2f} vs {b}={st.mean(db):.2f} (too few seeds)"
        diff = st.mean(da) - st.mean(db)
        # Welch t-ish heuristic: difference vs pooled sd
        sd = ((st.stdev(da) ** 2 / len(da)) + (st.stdev(db) ** 2 / len(db))) ** 0.5
        sig = "significant" if sd > 0 and abs(diff) > 2 * sd else "not significant"
        return f"{a}−{b} = {diff:+.2f} ({sig}; pooled se {sd:.2f})"

    print("\nH2 (transfer helps): supported iff B2 > B1 and B2 > B0")
    for pair in (("B2", "B1"), ("B2", "B0")):
        v = cmp(*pair)
        if v:
            print("  ", v)
            verdicts[f"{pair[0]}>{pair[1]}"] = v
    print("H3 (constraint matters): supported iff B2 > B3")
    v = cmp("B2", "B3")
    if v:
        print("  ", v)
        verdicts["B2>B3"] = v
    return {"stats": {k: v["mean"] for k, v in stats.items()}, "verdicts": verdicts}


if __name__ == "__main__":
    report()
