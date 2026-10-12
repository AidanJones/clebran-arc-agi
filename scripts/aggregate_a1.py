"""Aggregate the A1 (L1-as-proposer) experiment logs into a summary.

Reads `logs/b5l1_*.jsonl` (B5+L1-proposer) and compares against the
B5-1M baseline from the discovery-bottleneck menu pilots (the B5
control used by #1–#4, frozen at `experiments/2026-08-31_b5d_nm_1m/`
under `logs/b5_1m_seed{1..5}.jsonl`).

Outputs an `analysis.txt` with per-arm mean / standard error for
frontier solves, evo-solved, evals/solve, and per-task overlap.

Usage::

    uv run python -m scripts.aggregate_a1
"""
from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
LOG_DIR = REPO / "logs"
ANALYSIS = REPO / "experiments" / "2026-10-07_a1_l1_proposer" / "analysis"


def read_summaries(log_paths: list[Path]) -> list[dict]:
    summaries = []
    for p in log_paths:
        if not p.exists():
            print(f"  WARNING: {p} not found, skipping")
            continue
        last_event = None
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("event") == "summary":
                last_event = ev
        if last_event is not None:
            summaries.append(last_event)
    return summaries


def _extract_field(s: dict, primary: str, aliases: list[str]) -> any:
    """Extract a field from a summary, trying the primary name and
    any aliases (different log schemas)."""
    for f in [primary] + aliases:
        if f in s:
            return s[f]
    return None


def main() -> int:
    # Find all b5l1 logs and b5 logs.
    b5l1_logs = sorted(LOG_DIR.glob("b5l1_seed*.jsonl"))
    b5_logs = sorted(LOG_DIR.glob("b5_1m_seed*.jsonl"))
    print(f"B5L1 logs found:    {len(b5l1_logs)}")
    print(f"B5 (control) logs:  {len(b5_logs)}")

    b5l1_summaries = read_summaries(b5l1_logs)
    b5_summaries = read_summaries(b5_logs)
    print(f"B5L1 summaries:     {len(b5l1_summaries)}")
    print(f"B5 summaries:       {len(b5_summaries)}")

    if not b5l1_summaries:
        print("No B5L1 logs yet — exiting")
        return 0

    def stats(summaries: list[dict], primary: str,
              aliases: list[str] = ()) -> tuple[float, float, int]:
        vals = [_extract_field(s, primary, list(aliases))
                for s in summaries]
        vals = [v for v in vals if v is not None]
        if not vals:
            return 0.0, 0.0, 0
        mean = statistics.mean(vals)
        sd = statistics.stdev(vals) if len(vals) > 1 else 0.0
        se = sd / (len(vals) ** 0.5) if len(vals) > 1 else 0.0
        return mean, se, len(vals)

    out_lines = []
    out_lines.append("=" * 72)
    out_lines.append("A1 — #5 Learned L1 as proposer (2026-10-07)")
    out_lines.append("=" * 72)
    out_lines.append("")
    out_lines.append(f"B5L1 logs:    {len(b5l1_summaries)} seeds")
    out_lines.append(f"B5 (control) logs:  {len(b5_summaries)} seeds")
    out_lines.append("")
    out_lines.append("Per-arm frontier solves / 30 (mean ± SE):")
    b5l1_mean, b5l1_se, _ = stats(b5l1_summaries, "n_solved")
    b5_mean, b5_se, _ = stats(b5_summaries, "n_solved", ["solved"])
    out_lines.append(f"  B5L1 (L1 proposer + B5):    {b5l1_mean:5.2f} ± {b5l1_se:.2f}")
    out_lines.append(f"  B5  (control):              {b5_mean:5.2f} ± {b5_se:.2f}")
    out_lines.append(f"  delta (B5L1 - B5):          {b5l1_mean - b5_mean:+.2f}")
    out_lines.append("")
    out_lines.append("Per-arm evo-solved / 30 (mean ± SE):")
    b5l1_e, b5l1_e_se, _ = stats(b5l1_summaries, "n_evo_solved")
    b5_e, b5_e_se, _ = stats(b5_summaries, "n_evo_solved",
                              ["evo_solved_count"])
    # If evo count is not in the summary, fall back to len(solved_evolution).
    if b5_e == 0 and b5_summaries and "solved_evolution" in b5_summaries[0]:
        b5_e_vals = [len(s.get("solved_evolution", [])) for s in b5_summaries]
        b5_e = statistics.mean(b5_e_vals)
        b5_e_se = statistics.stdev(b5_e_vals) / (len(b5_e_vals) ** 0.5) if len(b5_e_vals) > 1 else 0.0
    out_lines.append(f"  B5L1:  {b5l1_e:5.2f} ± {b5l1_e_se:.2f}")
    out_lines.append(f"  B5:    {b5_e:5.2f} ± {b5_e_se:.2f}")
    out_lines.append(f"  delta: {b5l1_e - b5_e:+.2f}")
    out_lines.append("")
    out_lines.append("Per-arm test-exact / 30 (mean ± SE):")
    b5l1_te, b5l1_te_se, _ = stats(b5l1_summaries, "n_test_exact")
    b5_te, b5_te_se, _ = stats(b5_summaries, "n_test_exact",
                                ["test_exact"])
    out_lines.append(f"  B5L1:  {b5l1_te:5.2f} ± {b5l1_te_se:.2f}")
    out_lines.append(f"  B5:    {b5_te:5.2f} ± {b5_te_se:.2f}")
    out_lines.append(f"  delta: {b5l1_te - b5_te:+.2f}")
    out_lines.append("")
    out_lines.append("Per-seed frontier solves / 30:")
    out_lines.append("  seed  | B5L1 | B5  | delta")
    out_lines.append("  ------+------+-----+------")
    by_seed_b5l1 = {s["seed"]: _extract_field(s, "n_solved", [])
                    for s in b5l1_summaries}
    by_seed_b5 = {s["seed"]: _extract_field(s, "n_solved", ["solved"])
                  for s in b5_summaries}
    seeds = sorted(set(by_seed_b5l1.keys()) | set(by_seed_b5.keys()))
    for seed in seeds:
        b5l1_v = by_seed_b5l1.get(seed, "-")
        b5_v = by_seed_b5.get(seed, "-")
        delta = (b5l1_v - b5_v) if (isinstance(b5l1_v, (int, float)) and isinstance(b5_v, (int, float))) else "-"
        out_lines.append(f"  {seed:>4d}  | {b5l1_v!s:>4} | {b5_v!s:>3} | {delta!s:>5}")
    out_lines.append("")
    # Tasks unique to each arm.
    b5l1_tasks = set()
    for s in b5l1_summaries:
        b5l1_tasks.update(s.get("solved", []))
    b5_tasks = set()
    for s in b5_summaries:
        b5_tasks.update(s.get("solved_tasks", s.get("solved", [])))
    unique_b5l1 = b5l1_tasks - b5_tasks
    unique_b5 = b5_tasks - b5l1_tasks
    overlap = b5l1_tasks & b5_tasks
    out_lines.append(f"Tasks solved by any B5L1 seed:    {len(b5l1_tasks)} ({sorted(b5l1_tasks)})")
    out_lines.append(f"Tasks solved by any B5 seed:      {len(b5_tasks)} ({sorted(b5_tasks)})")
    out_lines.append(f"Overlap:                          {len(overlap)}")
    out_lines.append(f"Unique to B5L1:                   {len(unique_b5l1)} ({sorted(unique_b5l1)})")
    out_lines.append(f"Unique to B5:                     {len(unique_b5)} ({sorted(unique_b5)})")
    out_lines.append("")

    text = "\n".join(out_lines)
    print(text)
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    (ANALYSIS / "analysis.txt").write_text(text, encoding="utf-8")
    print()
    print(f"wrote {ANALYSIS / 'analysis.txt'}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())