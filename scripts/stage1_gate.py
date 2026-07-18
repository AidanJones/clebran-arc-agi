"""Stage-1 acceptance check (§8.1 row 1): B0 solves all 10 D1 tasks on
every seed; log solve count mean±sd, evals-per-solve, mean solution length."""
import json
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from clebran.subset import load_subset  # noqa: E402

sub = {r["task_id"]: r for r in load_subset()}
d1 = {t for t, r in sub.items() if r["bucket"] == "D1"}

rows = []
for path in sorted(Path("logs").glob("b0_seed*.jsonl")):
    recs = [json.loads(l) for l in path.read_text().splitlines()]
    summary = next(r for r in reversed(recs) if r["event"] == "summary")
    solved = set(summary["solved_tasks"])
    rows.append(summary | {"d1_missing": sorted(d1 - solved)})

print(f"{'seed':>4} {'solved':>6} {'test✓':>5} {'meanlen':>7} {'evals/solve':>11}  D1 gate")
gate_ok = True
for r in rows:
    n = r["solved"]
    eps = r["evals"] / n if n else float("inf")
    miss = r["d1_missing"]
    ok = not miss
    gate_ok &= ok
    print(f"{r['seed']:>4} {n:>5}/30 {r['test_exact']:>5} "
          f"{r['mean_solution_len']:>7} {int(eps):>11}  "
          f"{'PASS' if ok else 'FAIL missing ' + ','.join(miss)}")

solves = [r["solved"] for r in rows]
if len(solves) > 1:
    print(f"\nB0 solve count: {st.mean(solves):.2f} ± {st.stdev(solves):.2f} "
          f"over {len(solves)} seeds")
print(f"Stage-1 hard gate (all D1 on every seed): "
      f"{'PASS' if gate_ok else 'FAIL'}")
