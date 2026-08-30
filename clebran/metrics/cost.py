"""Acquisition-efficiency analysis (roadmap §9a).

The repo's headline endpoint is *solve count* at matched compute. Roadmap §9a
argues this is the endpoint Chollet says is uninformative — skill can be bought
with unlimited priors or training data. The right axis is **acquisition
efficiency** (cost-to-solve: evals consumed to reach a solution).

This module re-scores existing 4M-eval sweeps on the cost axis without
running any new compute:

  * For every arm, per-seed: ``evals_per_solve = total_evals / solved``,
    a coarse summary-level acquisition efficiency.
  * For B5 and B5+planner (the only arms with per-solve evals preserved
    in ``logs/``), the detailed distribution: median evals-to-solve,
    IQR, and the phase1 / evolution-phase split (the comparison that
    excludes the deterministic seeding layer).

The headline question: *does the cost axis re-rank the arms, or does it
confirm the solve-count picture?* Either outcome is informative.

CLI:

    uv run python -m clebran.metrics.cost                 # all arms at 4M
    uv run python -m clebran.metrics.cost --arm B5 B5+planner   # detail
"""
from __future__ import annotations

import argparse
import json
import statistics as st
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from ..baselines.common import LOG_DIR

# Frozen 20-seed 4M-eval summary locations (from the headline experiment).
# Raw per-solve evals for B5 and B5+planner live in logs/; the older arms
# were committed as summary-level summaries inside the experiment folders.
_RECOVERED_SUMMARY = (
    Path("experiments") / "2026-07-22_frontier_recovered_scaled" / "summaries.jsonl"
)
_CURRICULUM_SUMMARY = (
    Path("experiments") / "2026-07-23_frontier_curriculum" / "summaries.jsonl"
)


@dataclass
class ArmSeed:
    arm: str
    seed: int
    evals: int
    solved: int
    solved_evolution: int
    # Per-solve evals (only available for B5 / B5+planner / B5D).
    per_solve_evals: list[int] | None = None
    per_solve_phase: list[str] | None = None
    # Dream metrics (B5D only).
    n_dream_added: int = 0
    n_dream_solved: int = 0
    # Per-solve evals split by source task (frontier vs dream). For B5D
    # we can also distinguish dream-task solves, which count as practice
    # but are not "real" frontier solves.
    per_solve_task: list[str] | None = None


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines()]


def _solved_field(r: dict) -> int:
    return int(r.get("solved_union", r.get("solved", 0)))


def _load_arm_seeds_from_summaries(
    path: Path, arms: Iterable[str]
) -> list[ArmSeed]:
    rows = _load_jsonl(path)
    out: list[ArmSeed] = []
    seen: set[tuple[str, int]] = set()
    for r in rows:
        if r.get("event") != "summary":
            continue
        arm = r["arm"]
        if arm not in arms:
            continue
        key = (arm, r["seed"])
        if key in seen:
            continue  # keep latest
        seen.add(key)
        out.append(
            ArmSeed(
                arm=arm,
                seed=r["seed"],
                evals=int(r["evals"]),
                solved=_solved_field(r),
                solved_evolution=len(r.get("solved_evolution") or []),
            )
        )
    return out


def _load_per_solve_from_log(path: Path, arm: str, budget: int = 4_000_000) -> ArmSeed | None:
    """Pull per-solve evals (and phase) from a B5/B5+planner/B5D run log.

    Filters out non-matching budgets (e.g. leftover 100K pilot logs).
    Handles several summary schemas:
      * B5-style:  solved: int, solved_tasks: list, solved_evolution: list
      * B5+planner:  n_solved: int, n_evo_solved: int, solved: list
      * B5D-style:  solved: int (frontier only), n_dream_added, n_dream_solved
    In all cases we return the integer count and the per-solve event list.
    """
    if not path.exists():
        return None
    per_solve: list[int] = []
    per_phase: list[str] = []
    per_task: list[str] = []
    solved_total = 0
    evals_total = 0
    solved_evo = 0
    seed = None
    matched_budget = False
    n_dream_added = 0
    n_dream_solved = 0
    for line in path.read_text().splitlines():
        r = json.loads(line)
        if r.get("event") == "start":
            seed = r["seed"]
            if r.get("budget") == budget:
                matched_budget = True
        elif r.get("event") == "solve":
            per_solve.append(int(r["evals"]))
            per_phase.append(r.get("phase", "?"))
            per_task.append(r.get("task", "?"))
        elif r.get("event") == "summary":
            evals_total = int(r.get("evals", 0))
            # Schema dispatch: prefer n_solved if present, else solved
            if "n_solved" in r:
                solved_total = int(r["n_solved"])
                solved_evo = int(r.get("n_evo_solved", 0))
            else:
                # B5 / B5D-style: solved is an int; solved_evolution is a list
                s = r.get("solved", 0)
                solved_total = int(s) if isinstance(s, (int, float)) else len(s)
                solved_evo = len(r.get("solved_evolution") or [])
            n_dream_added = int(r.get("n_dream_added", 0))
            n_dream_solved = int(r.get("n_dream_solved", 0))
    if not matched_budget or seed is None:
        return None  # wrong-budget or empty log
    return ArmSeed(
        arm=arm,
        seed=seed,
        evals=evals_total,
        solved=solved_total,
        solved_evolution=solved_evo,
        per_solve_evals=per_solve,
        per_solve_phase=per_phase,
        per_solve_task=per_task,
        n_dream_added=n_dream_added,
        n_dream_solved=n_dream_solved,
    )


def load_all_4m_seeds() -> dict[str, list[ArmSeed]]:
    """Return per-arm lists of ArmSeed at 4M evals (n≈20 each)."""
    out: dict[str, list[ArmSeed]] = defaultdict(list)

    # Frozen summary-level: B0, B1, B2, B6, B7
    for s in _load_arm_seeds_from_summaries(
        _RECOVERED_SUMMARY, ["B0", "B1", "B2", "B6", "B7"]
    ):
        out[s.arm].append(s)

    # Frozen summary-level: B8, B9
    for s in _load_arm_seeds_from_summaries(_CURRICULUM_SUMMARY, ["B8", "B9"]):
        out[s.arm].append(s)

    # Per-solve level: B5 and B5+planner
    # Files of the form b5_<budget>_seed<int>.jsonl, e.g.
    #   b5_1m_seed*.jsonl — 1M pilot
    #   b5_4m_seed*.jsonl — 4M headline sweep
    # Plus b5p_seed* (B5+planner) and b5d_seed* (B5+planner dreaming).
    # Skips .incomplete.*, *_k1_4M_run1, etc.
    import re
    seed_pat = re.compile(r"^b5(?:p|d)?(?:_\d+m)?_seed(\d+)$")

    b5p_files = [f for f in LOG_DIR.glob("b5p_seed*.jsonl")
                 if seed_pat.match(f.stem)]
    for f in sorted(b5p_files):
        m = seed_pat.match(f.stem)
        seed = int(m.group(1))
        a = _load_per_solve_from_log(f, "B5+planner")
        if a:
            a.seed = seed
            out["B5+planner"].append(a)

    b5_files = [f for f in LOG_DIR.glob("b5_seed*.jsonl")
                if seed_pat.match(f.stem)]
    for f in sorted(b5_files):
        m = seed_pat.match(f.stem)
        seed = int(m.group(1))
        a = _load_per_solve_from_log(f, "B5")
        if a:
            a.seed = seed
            out["B5"].append(a)

    # 1M B5 pilot (B5 baseline at 1M, run separately for the 9b comparison).
    b5_1m_files = [f for f in LOG_DIR.glob("b5_1m_seed*.jsonl")
                   if seed_pat.match(f.stem)]
    for f in sorted(b5_1m_files):
        m = seed_pat.match(f.stem)
        seed = int(m.group(1))
        a = _load_per_solve_from_log(f, "B5-1M", budget=1_000_000)
        if a:
            a.seed = seed
            out["B5-1M"].append(a)

    # 4M B5 baseline (the headline 4M run with the new naming convention
    # b5_4m_seed*.jsonl to prevent overwrites from 1M pilots).
    b5_4m_files = [f for f in LOG_DIR.glob("b5_4m_seed*.jsonl")
                   if seed_pat.match(f.stem)]
    for f in sorted(b5_4m_files):
        m = seed_pat.match(f.stem)
        seed = int(m.group(1))
        a = _load_per_solve_from_log(f, "B5-4M", budget=4_000_000)
        if a:
            a.seed = seed
            out["B5-4M"].append(a)

    # Per-solve level: B5D (B5 + dreaming, roadmap §9b)
    b5d_files = [f for f in LOG_DIR.glob("b5d*.jsonl")
                 if seed_pat.match(f.stem)]
    for f in sorted(b5d_files):
        m = seed_pat.match(f.stem)
        seed = int(m.group(1))
        a = _load_per_solve_from_log(f, "B5D", budget=1_000_000)
        if a:
            a.seed = seed
            out["B5D"].append(a)

    # 4M B5D (the dreaming pilot at 4M, the next escalation).
    b5d_4m_files = [f for f in LOG_DIR.glob("b5d_4m_seed*.jsonl")
                    if seed_pat.match(f.stem)]
    for f in sorted(b5d_4m_files):
        m = seed_pat.match(f.stem)
        seed = int(m.group(1))
        a = _load_per_solve_from_log(f, "B5D-4M", budget=4_000_000)
        if a:
            a.seed = seed
            out["B5D-4M"].append(a)

    # Dedup per arm by seed (keep last; multiple b5 seed-1 files exist from retries)
    for arm in list(out):
        dedup: dict[int, ArmSeed] = {}
        for s in out[arm]:
            dedup[s.seed] = s
        out[arm] = sorted(dedup.values(), key=lambda s: s.seed)
    return out


def _safe_div(num: float, den: float) -> float:
    return num / den if den else float("inf")


def _per_solve_stats(evals: list[int]) -> dict[str, float]:
    if not evals:
        return {"n": 0, "mean": float("nan"), "median": float("nan"),
                "p25": float("nan"), "p75": float("nan"), "min": float("nan")}
    s = sorted(evals)
    n = len(s)
    return {
        "n": n,
        "mean": st.mean(s),
        "median": s[n // 2],
        "p25": s[n // 4],
        "p75": s[3 * n // 4],
        "min": min(s),
    }


def evals_per_solve_table(by_arm: dict[str, list[ArmSeed]]) -> list[dict]:
    """Per-arm: solved, evals-per-solve (4M / solved) mean ± sd across seeds.

    Seeds that solved zero tasks have undefined evals-per-solve; they are
    counted as ``n_unsolved`` and excluded from the SD (so the SD reflects
    the cost *conditional on* solving at least one task, not the variance
    across a mix of zero-and-nonzero outcomes).
    """
    rows = []
    for arm in sorted(by_arm):
        seeds = by_arm[arm]
        eps = [
            float(s.evals) / s.solved
            for s in seeds
            if s.solved > 0
        ]
        solved = [float(s.solved) for s in seeds]
        evo = [float(s.solved_evolution) for s in seeds]
        n_unsolved = sum(1 for s in seeds if s.solved == 0)
        rows.append({
            "arm": arm,
            "n_seeds": len(seeds),
            "n_solving": len(eps),
            "n_unsolved": n_unsolved,
            "solved_mean": st.mean(solved) if solved else 0.0,
            "solved_sd": st.stdev(solved) if len(solved) > 1 else 0.0,
            "evo_mean": st.mean(evo) if evo else 0.0,
            "evo_sd": st.stdev(evo) if len(evo) > 1 else 0.0,
            "evals_per_solve_mean": st.mean(eps) if eps else float("inf"),
            "evals_per_solve_sd": st.stdev(eps) if len(eps) > 1 else 0.0,
        })
    rows.sort(key=lambda r: r["evals_per_solve_mean"])  # lower = better
    return rows


def per_solve_detail(
    b5: list[ArmSeed], b5p: list[ArmSeed]
) -> dict[str, dict]:
    """Detailed per-solve evals distribution for B5 and B5+planner.

    Splits into phase1 (deterministic seeding, identical across arms) and
    evolution (the comparison that excludes the seed). The evolution-only
    cost is the meaningful acquisition-efficiency endpoint.
    """
    def _gather(seeds: list[ArmSeed], phase: str | None = None) -> list[int]:
        out = []
        for s in seeds:
            if s.per_solve_evals is None:
                continue
            if phase is None:
                out.extend(s.per_solve_evals)
            else:
                out.extend(
                    e for e, p in zip(s.per_solve_evals, s.per_solve_phase or [])
                    if p == phase
                )
        return out

    return {
        "B5 (all)": _per_solve_stats(_gather(b5)),
        "B5 (phase1)": _per_solve_stats(_gather(b5, "phase1")),
        "B5 (evolution)": _per_solve_stats(_gather(b5, "evolution")),
        "B5+planner (all)": _per_solve_stats(_gather(b5p)),
        "B5+planner (phase1)": _per_solve_stats(_gather(b5p, "phase1")),
        "B5+planner (evolution)": _per_solve_stats(_gather(b5p, "evolution")),
    }


def _print_evals_per_solve_table(rows: list[dict]) -> None:
    print(
        f"{'arm':14} {'n':>3} {'solving':>7} {'unsol':>5} "
        f"{'solved/30':>14} {'evo-solved':>14} {'evals/solve':>20}"
    )
    print("-" * 85)
    for r in rows:
        eps_str = (
            f"{r['evals_per_solve_mean']:>14,.0f} ± {int(r['evals_per_solve_sd']):>5,}"
            if r["evals_per_solve_mean"] != float("inf")
            else f"{'(none solved)':>20}"
        )
        print(
            f"{r['arm']:14} {r['n_seeds']:>3} {r['n_solving']:>7} {r['n_unsolved']:>5} "
            f"{r['solved_mean']:>6.2f} ± {r['solved_sd']:>5.2f}  "
            f"{r['evo_mean']:>5.2f} ± {r['evo_sd']:>5.2f}  "
            f"{eps_str}"
        )


def _print_per_solve_detail(detail: dict[str, dict]) -> None:
    print(
        f"\n{'arm':24} {'n':>5} {'mean':>12} {'median':>12} "
        f"{'p25':>12} {'p75':>12} {'min':>12}"
    )
    print("-" * 95)
    for label, s in detail.items():
        if s["n"] == 0:
            print(f"{label:24} {'(no per-solve data)':>50}")
            continue
        print(
            f"{label:24} {s['n']:>5} "
            f"{s['mean']:>12,.0f} {s['median']:>12,.0f} "
            f"{s['p25']:>12,.0f} {s['p75']:>12,.0f} {s['min']:>12,.0f}"
        )


def _welch_p(a: list[float], b: list[float]) -> float | None:
    """Welch-style two-sample t on the available means (normal-approx p).

    Returns None if either group has fewer than 2 values.
    """
    if len(a) < 2 or len(b) < 2:
        return None
    diff = st.mean(a) - st.mean(b)
    sd = (st.stdev(a) ** 2 / len(a) + st.stdev(b) ** 2 / len(b)) ** 0.5
    if sd == 0:
        return None
    t = diff / sd
    import math
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(t) / math.sqrt(2))))
    return p


def _permutation_p(a: list[float], b: list[float], n: int = 10_000) -> float | None:
    """Two-sided permutation p on the difference of medians.

    Use this when the per-solve distribution is heavy-tailed (it is here:
    some seeds solve a hard task at 3.5M evals while others solve at 50K).
    More robust than a t-test on the means.
    """
    import random
    if len(a) < 2 or len(b) < 2:
        return None
    obs = st.median(b) - st.median(a)
    if obs == 0:
        return 1.0
    pool = list(a) + list(b)
    n_a = len(a)
    rng = random.Random(0xC1EBAA)  # deterministic for reproducibility
    ge = 0
    for _ in range(n):
        rng.shuffle(pool)
        diff = st.median(pool[n_a:]) - st.median(pool[:n_a])
        if abs(diff) >= abs(obs):
            ge += 1
    return ge / n


def main(argv: list[str] | None = None) -> dict:
    # Force UTF-8 output (Windows consoles default to cp1252)
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument(
        "--arm", nargs="+",
        help="restrict detail to these arms (default: B5 B5+planner)",
    )
    p.add_argument(
        "--json", action="store_true",
        help="emit JSON instead of human-readable table",
    )
    args = p.parse_args(argv)

    by_arm = load_all_4m_seeds()
    if not by_arm:
        print("(no 4M data found)")
        return {}

    rows = evals_per_solve_table(by_arm)

    if args.json:
        out = {"evals_per_solve": rows}
        if "B5" in by_arm and "B5+planner" in by_arm:
            out["per_solve_detail"] = per_solve_detail(
                by_arm["B5"], by_arm["B5+planner"]
            )
        print(json.dumps(out, indent=2))
        return out

    print("=" * 72)
    print("ACQUISITION EFFICIENCY AT 4M CANDIDATE-EVALUATIONS (re-score, no new runs)")
    print("=" * 72)
    print()
    print("Per-arm summary (sorted by evals-per-solve, lower = more efficient):")
    _print_evals_per_solve_table(rows)

    if "B5" in by_arm and "B5+planner" in by_arm:
        b5 = by_arm["B5"]
        b5p = by_arm["B5+planner"]
        # Filter to seeds with per-solve events (the budget filter has already
        # been applied in _load_per_solve_from_log)
        b5_with_evals = [s for s in b5 if s.per_solve_evals]
        b5p_with_evals = [s for s in b5p if s.per_solve_evals]
        print(
            f"\nB5 and B5+planner have per-solve evals preserved "
            f"({len(b5_with_evals)} / {len(b5p_with_evals)} seeds at 4M)."
        )
        detail = per_solve_detail(b5_with_evals, b5p_with_evals)
        _print_per_solve_detail(detail)

        # B5 vs B5+planner: does the planner *cost* anything?
        eps_b5 = [
            float(s.evals) / s.solved for s in b5_with_evals if s.solved > 0
        ]
        eps_b5p = [
            float(s.evals) / s.solved for s in b5p_with_evals if s.solved > 0
        ]
        evo_b5 = [s.solved_evolution for s in b5_with_evals]
        evo_b5p = [s.solved_evolution for s in b5p_with_evals]
        print("\nB5 vs B5+planner (headline 4M result, re-scored on cost):")
        if eps_b5 and eps_b5p:
            print(
                f"  evals/solve (n={len(eps_b5)}/{len(eps_b5p)}): "
                f"B5 {st.mean(eps_b5):,.0f}  B5+planner {st.mean(eps_b5p):,.0f}  "
                f"diff {st.mean(eps_b5p) - st.mean(eps_b5):+,.0f}"
            )
        print(
            f"  evo-solved:  B5 {st.mean(evo_b5):.2f}    "
            f"B5+planner {st.mean(evo_b5p):.2f}  "
            f"diff {st.mean(evo_b5p) - st.mean(evo_b5):+.2f}"
        )
        if eps_b5 and eps_b5p:
            p_eps = _welch_p(eps_b5p, eps_b5)
            if p_eps is not None:
                print(f"  welch-t p (eps, B5+planner > B5):  {p_eps:.3f}")

        # Apples-to-apples: B5 evolution-only vs B5+planner (all evolution).
        # B5+planner has 0 phase1 solves -- the planner seed bypasses the
        # seeding layer -- so the cost-axis comparison is *evolution only*.
        evo_evals_b5 = [
            e for s in b5_with_evals for e, p in zip(
                s.per_solve_evals or [], s.per_solve_phase or []
            ) if p == "evolution"
        ]
        evo_evals_b5p = [
            e for s in b5p_with_evals for e in (s.per_solve_evals or [])
        ]
        if evo_evals_b5 and evo_evals_b5p:
            mb5 = st.median(evo_evals_b5)
            mb5p = st.median(evo_evals_b5p)
            ab5 = st.mean(evo_evals_b5)
            ab5p = st.mean(evo_evals_b5p)
            print(
                f"\nApples-to-apples (evolution-phase solves only):"
            )
            print(
                f"  B5      n={len(evo_evals_b5):>3}  "
                f"median={mb5:>10,.0f}  mean={ab5:>10,.0f}"
            )
            print(
                f"  B5+plan n={len(evo_evals_b5p):>3}  "
                f"median={mb5p:>10,.0f}  mean={ab5p:>10,.0f}"
            )
            print(
                f"  median diff: {mb5p - mb5:+,.0f}  "
                f"({(mb5p - mb5) / mb5 * 100:+.1f}%)  "
                f"mean diff: {ab5p - ab5:+,.0f}"
            )
            # Permutation test on the median
            p_perm = _permutation_p(evo_evals_b5, evo_evals_b5p)
            if p_perm is not None:
                verdict = "significant" if p_perm < 0.05 else "not significant"
                print(
                    f"  permutation p (median, 10k shuffles): {p_perm:.3f}  ({verdict})"
                )

    # B5 vs B5D (roadmap §9b: dreaming). Use the 1M B5 baseline (B5-1M)
    # if available, since we ran both arms at 1M.
    b5_for_dream = by_arm.get("B5-1M") or by_arm.get("B5")
    if b5_for_dream and "B5D" in by_arm:
        b5_seeds = b5_for_dream
        b5d_seeds = by_arm["B5D"]
        b5_label = "B5-1M" if "B5-1M" in by_arm else "B5"
        print(f"\n=== {b5_label} vs B5D (roadmap §9b: dreaming) ===")
        # Headline: solved (frontier) and evals/solve
        b5_solved = [float(s.solved) for s in b5_seeds]
        b5d_solved = [float(s.solved) for s in b5d_seeds]
        b5_eps = [float(s.evals) / s.solved for s in b5_seeds if s.solved > 0]
        b5d_eps = [float(s.evals) / s.solved for s in b5d_seeds if s.solved > 0]
        print(
            f"  frontier solves:   {b5_label} {st.mean(b5_solved):.2f} ± {st.stdev(b5_solved) if len(b5_solved) > 1 else 0:.2f}  "
            f"B5D {st.mean(b5d_solved):.2f} ± {st.stdev(b5d_solved) if len(b5d_solved) > 1 else 0:.2f}  "
            f"diff {st.mean(b5d_solved) - st.mean(b5_solved):+.2f}"
        )
        if b5_eps and b5d_eps:
            print(
                f"  evals/solve:       {b5_label} {st.mean(b5_eps):,.0f}  "
                f"B5D {st.mean(b5d_eps):,.0f}  "
                f"diff {st.mean(b5d_eps) - st.mean(b5_eps):+,.0f}"
            )
            # Per-seed welch-t on evals/solve (same unit on both sides).
            p = _welch_p(b5_eps, b5d_eps)
            if p is not None:
                print(
                    f"  welch-t p (per-seed evals/solve, B5 vs B5D): {p:.3f}"
                )
        # Dream utilization: how many of the dream tasks get solved?
        dream_added = [s.n_dream_added for s in b5d_seeds]
        dream_solved = [s.n_dream_solved for s in b5d_seeds]
        if any(dream_added):
            util = [
                s / a if a else 0.0
                for s, a in zip(dream_solved, dream_added)
            ]
            print(
                f"  dream utilization: B5D added={st.mean(dream_added):.1f} "
                f"solved={st.mean(dream_solved):.1f} "
                f"rate={st.mean(util):.1%}"
            )
            # Cost split: per-solve evals for frontier vs dream solves
            frontier_eps = []
            dream_eps = []
            for s in b5d_seeds:
                if s.per_solve_evals and s.per_solve_task:
                    for e, t in zip(s.per_solve_evals, s.per_solve_task):
                        if t.startswith("gen_"):
                            dream_eps.append(e)
                        else:
                            frontier_eps.append(e)
            if frontier_eps and dream_eps:
                # Per-seed mean of cumulative evals-at-frontier-solve.
                # This is a different unit than the per-seed evals/solve
                # ratio above (it tells you *when* a frontier solve
                # happened, not the per-task cost) — useful for seeing
                # whether the dreaming pushes frontier solves earlier or
                # later in the run.
                per_seed_frontier = []
                for s in b5d_seeds:
                    if s.per_solve_evals and s.per_solve_task:
                        fe = [
                            e for e, t in zip(
                                s.per_solve_evals, s.per_solve_task
                            ) if not t.startswith("gen_")
                        ]
                        if fe:
                            per_seed_frontier.append(st.mean(fe))
                if per_seed_frontier:
                    print(
                        f"  frontier solve-time: B5D cumulative-evals-at-solve "
                        f"(per-seed mean) = {st.mean(per_seed_frontier):,.0f}  "
                        f"vs B5 evals/solve ratio {st.mean(b5_eps):,.0f}  "
                        f"(different units; frontier solves happen mid-run, ratio is total/avg)"
                    )
                print(
                    f"  per-solve split:   frontier n={len(frontier_eps)} "
                    f"median={st.median(frontier_eps):,.0f}  "
                    f"dream n={len(dream_eps)} "
                    f"median={st.median(dream_eps):,.0f}"
                )

    # H2 / H3 cost-axis re-ranking
    if {"B0", "B1", "B2"} <= set(by_arm):
        print("\nH2/H3 verdicts re-scored on evals-per-solve (lower = better):")
        for a, b, lbl in (("B2", "B1", "H2: B2 > B1 (transfer)"),
                          ("B2", "B0", "H2: B2 > B0 (transfer)"),
                          ("B2", "B3", "H3: B2 > B3 (constraint)")):
            if a in by_arm and b in by_arm:
                ea = [float(s.evals) / s.solved for s in by_arm[a] if s.solved > 0]
                eb = [float(s.evals) / s.solved for s in by_arm[b] if s.solved > 0]
                # transfer helps = LOWER evals per solve for B2
                if ea and eb:
                    diff = st.mean(eb) - st.mean(ea)
                    p = _welch_p(ea, eb)
                    ps = f"{p:.3f}" if p is not None else "n/a"
                    print(f"  {lbl:35s}  diff={diff:+,.0f}  p(B2<B{('1' if b=='B1' else '0')})={ps}")

    return {"evals_per_solve": rows}


if __name__ == "__main__":
    main()
