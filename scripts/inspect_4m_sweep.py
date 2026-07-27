"""Inspect 4M sweep seed-level data for the world-modeling paper."""
from __future__ import annotations
import json
import sys
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"


def summarize(path: Path) -> dict:
    """Read a log and return the summary + solved sets.

    The B5 baseline log uses {solved: int, solved_phase1: [...], solved_evolution: [...],
    test_exact: int, mean_solution_len: float}. The B5+planner log uses
    {n_solved: int, n_evo_solved: int, n_test_exact: int, mean_solution_length: float,
    solved: [...tasks]}. We normalise to a common shape.
    """
    lines = path.read_text(encoding="utf-8").strip().split("\n")
    summary = None
    for line in lines:
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if d.get("event") == "summary":
            summary = d
            break
    if summary is None:
        return {"file": path.name, "error": "no summary"}
    # B5+planner format
    if "n_solved" in summary:
        solved = summary.get("n_solved")
        evo = summary.get("n_evo_solved", 0)
        test_exact = summary.get("n_test_exact", 0)
        mean_len = summary.get("mean_solution_length", 0.0)
        all_tasks = set(summary.get("solved", []))
        # We don't have phase1/evo split for B5+planner; treat the seed's
        # all_solved set as one block and report evo count separately.
        return {
            "file": path.name,
            "arm": summary.get("arm"),
            "seed": summary.get("seed"),
            "budget": summary.get("budget"),
            "solved": solved,
            "phase1": solved - evo,
            "evo": evo,
            "test_exact": test_exact,
            "mean_len": mean_len,
            "all_tasks": all_tasks,
        }
    # B5 baseline format
    phase1_tasks = set(summary.get("solved_phase1", []))
    evo_tasks = set(summary.get("solved_evolution", []))
    return {
        "file": path.name,
        "arm": summary.get("arm"),
        "seed": summary.get("seed"),
        "budget": summary.get("budget"),
        "solved": summary.get("solved"),
        "phase1": len(phase1_tasks),
        "evo": len(evo_tasks),
        "test_exact": summary.get("test_exact"),
        "mean_len": summary.get("mean_solution_len"),
        "all_tasks": phase1_tasks | evo_tasks,
        "phase1_tasks": phase1_tasks,
        "evo_tasks": evo_tasks,
    }


def main() -> int:
    print("=" * 78)
    print("B5 baseline (control) — 4M evals, 5 seeds")
    print("=" * 78)
    b5_rows = []
    for s in range(1, 6):
        path = LOG_DIR / f"b5_seed{s}.jsonl"
        if not path.exists():
            print(f"  missing: {path}")
            continue
        row = summarize(path)
        b5_rows.append(row)
        print(f"  b5_seed{s}: solved={row['solved']:>2}  phase1={row['phase1']:>2}  evo={row['evo']:>2}  test_exact={row['test_exact']:>2}  mean_len={row['mean_len']:.2f}")

    print()
    print("=" * 78)
    print("B5+planner (K=1, L=1, hamming) — 4M evals, 5 seeds")
    print("=" * 78)
    b5p_rows = []
    for s in range(1, 6):
        # The K=1 logs use `b5p_seedN.jsonl`
        path = LOG_DIR / f"b5p_seed{s}.jsonl"
        if not path.exists():
            print(f"  missing: {path}")
            continue
        row = summarize(path)
        b5p_rows.append(row)
        print(f"  b5p_seed{s}: solved={row['solved']:>2}  phase1={row['phase1']:>2}  evo={row['evo']:>2}  test_exact={row['test_exact']:>2}  mean_len={row['mean_len']:.2f}")

    print()
    print("=" * 78)
    print("Unique task analysis (across 5 seeds)")
    print("=" * 78)
    b5_solved = set()
    for r in b5_rows:
        # We don't have the full list in this format, just counts. Re-parse.
        path = LOG_DIR / f"b5_seed{r['seed']}.jsonl"
        lines = path.read_text(encoding="utf-8").strip().split("\n")
        for line in lines:
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get("event") == "summary":
                b5_solved.update(d.get("solved_phase1", []))
                b5_solved.update(d.get("solved_evolution", []))

    b5p_solved = set()
    for r in b5p_rows:
        b5p_solved.update(r.get("all_tasks", set()))

    print(f"  B5 union of solved tasks across 5 seeds: {len(b5_solved)} unique")
    print(f"  B5+planner union: {len(b5p_solved)} unique")
    only_b5 = b5_solved - b5p_solved
    only_b5p = b5p_solved - b5_solved
    print(f"  Only B5 (B5 solves, B5+planner never does): {sorted(only_b5)}")
    print(f"  Only B5+planner (B5+planner solves, B5 never does): {sorted(only_b5p)}")

    print()
    print()
    print("=" * 78)
    print("Per-seed delta (B5+planner - B5)")
    print("=" * 78)
    print(f"  {'seed':>4}  {'B5':>4}  {'B5+P':>5}  {'delta':>5}")
    for s in range(1, 6):
        b5 = next((r for r in b5_rows if r["seed"] == s), None)
        b5p = next((r for r in b5p_rows if r["seed"] == s), None)
        if b5 and b5p:
            print(f"  {s:>4}  {b5['solved']:>4}  {b5p['solved']:>5}  {b5p['solved'] - b5['solved']:>+4}")

    # Compute mean / sd
    import statistics
    if b5_rows and b5p_rows:
        b5_solves = [r["solved"] for r in b5_rows]
        b5p_solves = [r["solved"] for r in b5p_rows]
        b5_evo = [r["evo"] for r in b5_rows]
        b5p_evo = [r["evo"] for r in b5p_rows]
        b5_te = [r["test_exact"] for r in b5_rows]
        b5p_te = [r["test_exact"] for r in b5p_rows]
        print()
        print(f"  B5: solved={statistics.mean(b5_solves):.2f} ± {statistics.stdev(b5_solves):.2f}, evo={statistics.mean(b5_evo):.2f}, test_exact={statistics.mean(b5_te):.2f}")
        print(f"  B5+P: solved={statistics.mean(b5p_solves):.2f} ± {statistics.stdev(b5p_solves):.2f}, evo={statistics.mean(b5p_evo):.2f}, test_exact={statistics.mean(b5p_te):.2f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
