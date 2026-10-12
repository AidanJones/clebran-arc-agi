"""Aggregate the A3 (L1-as-rollout-engine) experiment logs.

Compares B5L1P (B5 + L1-rollout planner) against B5P (B5 +
perfect-interpreter planner) and B5 (control). The A3 hypothesis
is that the L1 rollout is fast enough to be a drop-in
replacement for the interpreter without losing accuracy — paper
3 §6 names this as the explicit "next push" of the
world-modeling direction.

Inputs:
* logs/b5l1p_seed{1..5}.jsonl (this experiment)
* logs/b5planner_seed{1..5}.jsonl (B5P control; frozen 4M run
  if available, but the B5P 1M logs are not committed)
* logs/b5_1m_seed{1..5}.jsonl (B5 control, frozen
  2026-08-31 to 2026-09-24)

For the 1M pilot, the natural comparison is B5L1P vs B5 (the B5P
arm has not been run at 1M as a control in the project; B5P at 4M
is in paper 3). So the headline table compares B5L1P vs B5 at
1M × 5 seeds.

Output: experiments/2026-10-12_a3_l1_rollout_planner/analysis/analysis.txt
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
LOG_DIR = REPO / "logs"
ANALYSIS = REPO / "experiments" / "2026-10-12_a3_l1_rollout_planner" / "analysis"


def _extract_field(s: dict, primary: str, aliases: list[str]) -> any:
    for f in [primary] + aliases:
        if f in s:
            return s[f]
    return None


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


def main() -> int:
    b5l1p_logs = sorted(LOG_DIR.glob("b5l1p_seed*.jsonl"))
    b5_logs = sorted(LOG_DIR.glob("b5_1m_seed*.jsonl"))
    b5planner_logs = sorted(LOG_DIR.glob("b5planner_*.jsonl"))
    print(f"B5L1P logs found:        {len(b5l1p_logs)}")
    print(f"B5 (control) logs:       {len(b5_logs)}")
    print(f"B5P logs found:           {len(b5planner_logs)}")

    b5l1p_summaries = read_summaries(b5l1p_logs)
    b5_summaries = read_summaries(b5_logs)
    b5p_summaries = read_summaries(b5planner_logs)
    print(f"B5L1P summaries:         {len(b5l1p_summaries)}")
    print(f"B5 summaries:            {len(b5_summaries)}")
    print(f"B5P summaries:            {len(b5p_summaries)}")

    if not b5l1p_summaries:
        print("No B5L1P logs yet — exiting")
        return 0

    out_lines = []
    out_lines.append("=" * 72)
    out_lines.append("A3 (first concrete test) — B5 + L1-rollout planner (2026-10-12)")
    out_lines.append("=" * 72)
    out_lines.append("")
    out_lines.append(f"B5L1P logs:    {len(b5l1p_summaries)} seeds")
    out_lines.append(f"B5 (control) logs:  {len(b5_summaries)} seeds")
    if b5p_summaries:
        out_lines.append(f"B5P logs:      {len(b5p_summaries)} seeds")
    out_lines.append("")
    out_lines.append("Per-arm frontier solves / 30 (mean ± SE):")
    b5l1p_mean, b5l1p_se, _ = stats(b5l1p_summaries, "n_solved")
    b5_mean, b5_se, _ = stats(b5_summaries, "n_solved", ["solved"])
    b5p_mean, b5p_se, _ = stats(b5p_summaries, "n_solved", ["solved"])
    out_lines.append(f"  B5L1P (B5 + L1-rollout planner):    {b5l1p_mean:5.2f} ± {b5l1p_se:.2f}")
    if b5p_summaries:
        out_lines.append(f"  B5P   (B5 + perfect-interpret planner): {b5p_mean:5.2f} ± {b5p_se:.2f}")
    out_lines.append(f"  B5    (control):                    {b5_mean:5.2f} ± {b5_se:.2f}")
    out_lines.append(f"  delta (B5L1P - B5):                 {b5l1p_mean - b5_mean:+.2f}")
    if b5p_summaries:
        out_lines.append(f"  delta (B5L1P - B5P):                {b5l1p_mean - b5p_mean:+.2f}")
    out_lines.append("")
    out_lines.append("Per-arm evo-solved / 30 (mean ± SE):")
    b5l1p_e, b5l1p_e_se, _ = stats(b5l1p_summaries, "n_evo_solved")
    b5_e, b5_e_se, _ = stats(b5_summaries, "n_evo_solved",
                              ["evo_solved_count"])
    if b5_e == 0 and b5_summaries and "solved_evolution" in b5_summaries[0]:
        b5_e_vals = [len(s.get("solved_evolution", [])) for s in b5_summaries]
        b5_e = statistics.mean(b5_e_vals)
        b5_e_se = statistics.stdev(b5_e_vals) / (len(b5_e_vals) ** 0.5) if len(b5_e_vals) > 1 else 0.0
    b5p_e, b5p_e_se, _ = stats(b5p_summaries, "n_evo_solved",
                                ["evo_solved_count"])
    if b5p_e == 0 and b5p_summaries and "solved_evolution" in b5p_summaries[0]:
        b5p_e_vals = [len(s.get("solved_evolution", [])) for s in b5p_summaries]
        b5p_e = statistics.mean(b5p_e_vals)
        b5p_e_se = statistics.stdev(b5p_e_vals) / (len(b5p_e_vals) ** 0.5) if len(b5p_e_vals) > 1 else 0.0
    out_lines.append(f"  B5L1P:  {b5l1p_e:5.2f} ± {b5l1p_e_se:.2f}")
    if b5p_summaries:
        out_lines.append(f"  B5P:    {b5p_e:5.2f} ± {b5p_e_se:.2f}")
    out_lines.append(f"  B5:     {b5_e:5.2f} ± {b5_e_se:.2f}")
    out_lines.append(f"  delta:  {b5l1p_e - b5_e:+.2f}")
    out_lines.append("")
    out_lines.append("Per-arm test-exact / 30 (mean ± SE):")
    b5l1p_te, b5l1p_te_se, _ = stats(b5l1p_summaries, "n_test_exact")
    b5_te, b5_te_se, _ = stats(b5_summaries, "n_test_exact",
                                ["test_exact"])
    b5p_te, b5p_te_se, _ = stats(b5p_summaries, "n_test_exact",
                                  ["test_exact"])
    out_lines.append(f"  B5L1P:  {b5l1p_te:5.2f} ± {b5l1p_te_se:.2f}")
    if b5p_summaries:
        out_lines.append(f"  B5P:    {b5p_te:5.2f} ± {b5p_te_se:.2f}")
    out_lines.append(f"  B5:     {b5_te:5.2f} ± {b5_te_se:.2f}")
    out_lines.append(f"  delta:  {b5l1p_te - b5_te:+.2f}")
    out_lines.append("")
    out_lines.append("Per-seed frontier solves / 30:")
    out_lines.append("  seed  | B5L1P | B5  | delta")
    out_lines.append("  ------+-------+-----+------")
    by_seed_b5l1p = {s["seed"]: _extract_field(s, "n_solved", [])
                     for s in b5l1p_summaries}
    by_seed_b5 = {s["seed"]: _extract_field(s, "n_solved", ["solved"])
                  for s in b5_summaries}
    seeds = sorted(set(by_seed_b5l1p.keys()) | set(by_seed_b5.keys()))
    for seed in seeds:
        b5l1p_v = by_seed_b5l1p.get(seed, "-")
        b5_v = by_seed_b5.get(seed, "-")
        delta = (b5l1p_v - b5_v) if (isinstance(b5l1p_v, (int, float)) and isinstance(b5_v, (int, float))) else "-"
        out_lines.append(f"  {seed:>4d}  | {b5l1p_v!s:>5} | {b5_v!s:>3} | {delta!s:>5}")
    out_lines.append("")
    b5l1p_tasks = set()
    for s in b5l1p_summaries:
        b5l1p_tasks.update(s.get("solved", []))
    b5_tasks = set()
    for s in b5_summaries:
        b5_tasks.update(s.get("solved_tasks", s.get("solved", [])))
    unique_b5l1p = b5l1p_tasks - b5_tasks
    unique_b5 = b5_tasks - b5l1p_tasks
    overlap = b5l1p_tasks & b5_tasks
    out_lines.append(f"Tasks solved by any B5L1P seed:  {len(b5l1p_tasks)} ({sorted(b5l1p_tasks)})")
    out_lines.append(f"Tasks solved by any B5 seed:     {len(b5_tasks)} ({sorted(b5_tasks)})")
    out_lines.append(f"Overlap:                          {len(overlap)}")
    out_lines.append(f"Unique to B5L1P:                  {len(unique_b5l1p)} ({sorted(unique_b5l1p)})")
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