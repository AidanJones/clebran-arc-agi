"""Analyze the 20-seed 4M-eval sweep results.

Reads the b5_seed{N}.jsonl and b5p_seed{N}.jsonl files, builds
the per-seed solved/evo-solved tables, computes means and SDs,
and reports the per-seed delta. Used to update the world-modeling
paper §3.3 from the 5-seed to the 20-seed headline.
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

LOG_DIR = Path("logs")


def summary(log_path: Path) -> dict | None:
    if not log_path.exists():
        return None
    for line in log_path.read_text(encoding="utf-8").splitlines():
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if d.get("event") == "summary":
            return d
    return None


def get_solved_tasks(path: Path) -> set:
    """Return the set of solved task IDs from a single run's summary.

    B5 logs use ``solved_tasks`` (a set) for the task IDs; B5P
    logs use ``solved`` (a list). Both formats are normalised here.
    """
    s = summary(path)
    if s is None:
        return set()
    tasks = s.get("solved_tasks")
    if isinstance(tasks, (set, list)):
        return set(tasks)
    tasks = s.get("solved")
    if isinstance(tasks, (set, list)):
        return set(tasks)
    return set()


def main():
    rows = []
    b5_all_solved: set = set()
    b5p_all_solved: set = set()
    for s in range(1, 21):
        b5 = summary(LOG_DIR / f"b5_seed{s}.jsonl")
        # b5p_seed1.jsonl is a 100K smoke test, not the 4M run.
        # The 4M seed-1 run was archived as b5p_seed1_k1_4M_run1.jsonl.
        if s == 1:
            b5p_path = LOG_DIR / "b5p_seed1_k1_4M_run1.jsonl"
        else:
            b5p_path = LOG_DIR / f"b5p_seed{s}.jsonl"
        b5p = summary(b5p_path)
        if b5 is None or b5p is None:
            print(f"seed={s}: missing log (b5={b5 is not None}, b5p={b5p is not None})")
            continue
        # b5 has 'solved' as int + 'solved_tasks' as a set of task IDs.
        # b5p has 'solved' as a list of task IDs.
        b5_solved_count = b5.get("solved", b5.get("n_solved"))
        if isinstance(b5_solved_count, list):
            b5_solved_count = len(b5_solved_count)
        b5_all_solved.update(get_solved_tasks(LOG_DIR / f"b5_seed{s}.jsonl"))
        b5p_solved = b5p.get("solved", b5p.get("n_solved"))
        if isinstance(b5p_solved, list):
            b5p_solved_count = len(b5p_solved)
            b5p_all_solved.update(b5p_solved)
        else:
            b5p_solved_count = b5p_solved
            b5p_all_solved.update(get_solved_tasks(b5p_path))
        b5_evo = b5.get("solved_evolution", [])
        if not isinstance(b5_evo, list):
            b5_evo = []
        b5p_evo = b5p.get("n_evo_solved", 0)
        rows.append({
            "seed": s,
            "b5_solved": b5_solved_count,
            "b5_evo": len(b5_evo),
            "b5p_solved": b5p_solved_count,
            "b5p_evo": b5p_evo,
        })
    if not rows:
        print("no complete runs yet")
        return
    # Per-seed table.
    print(f"{'seed':>4s}  {'B5':>4s}  {'B5+P':>5s}  {'delta':>5s}")
    for r in rows:
        print(f"{r['seed']:>4d}  {r['b5_solved']:>4d}  "
              f"{r['b5p_solved']:>5d}  "
              f"{r['b5p_solved'] - r['b5_solved']:>+5d}")
    # Summary stats.
    b5 = [r["b5_solved"] for r in rows]
    b5p = [r["b5p_solved"] for r in rows]
    deltas = [r["b5p_solved"] - r["b5_solved"] for r in rows]
    print()
    print(f"  N (paired seeds): {len(rows)}")
    print(f"  B5:   solved = {statistics.mean(b5):.2f} ± {statistics.stdev(b5):.2f}")
    print(f"  B5+P: solved = {statistics.mean(b5p):.2f} ± {statistics.stdev(b5p):.2f}")
    print(f"  delta (B5+P - B5): mean = {statistics.mean(deltas):+.2f}, "
          f"sd = {statistics.stdev(deltas):.2f}")
    se = statistics.stdev(deltas) / (len(deltas) ** 0.5)
    print(f"  SE on mean delta: {se:.3f}")
    if se:
        print(f"  t-statistic: {abs(statistics.mean(deltas)) / se:.2f}")
    # Per-seed evo.
    b5_evo = [r["b5_evo"] for r in rows]
    b5p_evo = [r["b5p_evo"] for r in rows]
    print()
    print(f"  B5 evo-solved:   {statistics.mean(b5_evo):.2f} ± {statistics.stdev(b5_evo):.2f}")
    print(f"  B5+P evo-solved: {statistics.mean(b5p_evo):.2f} ± {statistics.stdev(b5p_evo):.2f}")
    # Unique task analysis.
    print()
    print(f"  B5 union of solved tasks:   {len(b5_all_solved)}")
    print(f"  B5+P union of solved tasks: {len(b5p_all_solved)}")
    only_b5 = b5_all_solved - b5p_all_solved
    only_b5p = b5p_all_solved - b5_all_solved
    print(f"  B5 only (B5 solves, B5+P never): {sorted(only_b5)}")
    print(f"  B5+P only (B5+P solves, B5 never): {sorted(only_b5p)}")
    print(f"  intersection: {len(b5_all_solved & b5p_all_solved)}")


if __name__ == "__main__":
    main()
