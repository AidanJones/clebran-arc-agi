"""Identify frontier tasks B5-4M does/does not solve."""
import json
from pathlib import Path
from collections import defaultdict

# Load frontier subset
with open("data/frontier_subset.json") as f:
    frontier = json.load(f)
frontier_tasks = {t["task_id"]: t for t in frontier["tasks"]}
print(f"Frontier tasks: {len(frontier_tasks)}")
n_d2 = sum(1 for t in frontier_tasks.values() if t["bucket"] == "D2")
n_d3 = sum(1 for t in frontier_tasks.values() if t["bucket"] == "D3")
print(f"  D2: {n_d2}")
print(f"  D3: {n_d3}")

# Tally solves across B5 4M seeds
b5_solved = defaultdict(set)  # task_id -> set of seeds
logs_dir = Path("logs")
b5_logs = sorted(logs_dir.glob("b5_4m_seed*.jsonl"))
print(f"B5-4M logs: {len(b5_logs)}")
for log in b5_logs:
    seed = int(log.stem.split("seed")[-1])
    for line in log.read_text().splitlines():
        rec = json.loads(line)
        if rec.get("type") == "solve" and rec.get("solved") is True:
            tid = rec["task_id"]
            if tid in frontier_tasks:
                b5_solved[tid].add(seed)

n_seeds = len(b5_logs)
print()
solved_any = sorted(tid for tid, seeds in b5_solved.items() if len(seeds) > 0)
unsolved = sorted(tid for tid in frontier_tasks if len(b5_solved[tid]) == 0)
solved_some = sorted(tid for tid, s in b5_solved.items() if 0 < len(s) < n_seeds)
solved_all = sorted(tid for tid, s in b5_solved.items() if len(s) == n_seeds)
print(f"B5-4M solved always ({len(solved_all)}/{len(frontier_tasks)}): {solved_all}")
print(f"B5-4M solved sometimes ({len(solved_some)}/{len(frontier_tasks)}): {solved_some}")
print(f"B5-4M unsolved ({len(unsolved)}/{len(frontier_tasks)}): {unsolved}")
print()
print(f"Tasks solved by ANY seed: {len(solved_any)}")
print(f"Tasks solved by ALL {n_seeds} seeds: {len(solved_all)}")
print()
for tid in sorted(frontier_tasks, key=lambda t: (frontier_tasks[t]["bucket"], -len(b5_solved.get(t, set())), t)):
    bucket = frontier_tasks[tid]["bucket"]
    n = len(b5_solved.get(tid, set()))
    print(f"  {tid:12s} {bucket} solved {n}/{n_seeds}  tags={frontier_tasks[tid]['tags']}")
