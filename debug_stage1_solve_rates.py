"""Identify stage1 tasks B5-1M does/does not solve."""
import json
from pathlib import Path
from collections import defaultdict

# Load stage1 subset
with open("data/stage1_subset.json") as f:
    stage1 = json.load(f)
stage1_tasks = {t["task_id"]: t for t in stage1["tasks"]}
print(f"Stage1 tasks: {len(stage1_tasks)}")
for b in ("D1", "D2", "D3"):
    n = sum(1 for t in stage1_tasks.values() if t["bucket"] == b)
    print(f"  {b}: {n}")

# Tally solves across B5 1M seeds
b5_solved_1m = defaultdict(set)
b5_solved_4m = defaultdict(set)
logs_dir = Path("logs")
b5_1m_logs = sorted(logs_dir.glob("b5_1m_seed*.jsonl"))
b5_4m_logs = sorted(logs_dir.glob("b5_4m_seed*.jsonl"))
print(f"\nB5-1M logs: {len(b5_1m_logs)}")
print(f"B5-4M logs: {len(b5_4m_logs)}")

for log in b5_1m_logs:
    seed = int(log.stem.split("seed")[-1])
    for line in log.read_text().splitlines():
        rec = json.loads(line)
        if rec.get("event") == "solve" and rec.get("test_exact") is True:
            tid = rec["task"]
            if tid in stage1_tasks:
                b5_solved_1m[tid].add(seed)
for log in b5_4m_logs:
    seed = int(log.stem.split("seed")[-1])
    for line in log.read_text().splitlines():
        rec = json.loads(line)
        if rec.get("event") == "solve" and rec.get("test_exact") is True:
            tid = rec["task"]
            if tid in stage1_tasks:
                b5_solved_4m[tid].add(seed)

n_1m = len(b5_1m_logs)
n_4m = len(b5_4m_logs)

# unsolved at 1M
unsolved_1m = sorted(tid for tid in stage1_tasks if len(b5_solved_1m[tid]) == 0)
always_1m = sorted(tid for tid, s in b5_solved_1m.items() if len(s) == n_1m)
print(f"\nB5-1M solved always ({len(always_1m)}/{len(stage1_tasks)})")
print(f"B5-1M unsolved ({len(unsolved_1m)}/{len(stage1_tasks)}): {unsolved_1m}")
print()

# unsolved at 4M
unsolved_4m = sorted(tid for tid in stage1_tasks if len(b5_solved_4m[tid]) == 0)
always_4m = sorted(tid for tid, s in b5_solved_4m.items() if len(s) == n_4m)
print(f"B5-4M solved always ({len(always_4m)}/{len(stage1_tasks)})")
print(f"B5-4M unsolved ({len(unsolved_4m)}/{len(stage1_tasks)}): {unsolved_4m}")
print()

# intersection of unsolved at 1M and 4m
unsolved_either = sorted(set(unsolved_1m) | set(unsolved_4m))
print(f"Unsolved at 1M or 4M ({len(unsolved_either)}/{len(stage1_tasks)}): {unsolved_either}")
print()

# Per-task table
print("\nPer-task solve rates (B5-1M, 5 seeds / B5-4M, 15 seeds):")
print(f"{'task_id':12s} {'bucket':6s} {'tags':40s} {'1M':>5s} {'4M':>5s}")
for tid in sorted(stage1_tasks, key=lambda t: (stage1_tasks[t]["bucket"], stage1_tasks[t]["depth"], t)):
    bucket = stage1_tasks[tid]["bucket"]
    tags = ",".join(stage1_tasks[tid]["tags"])
    n1 = len(b5_solved_1m.get(tid, set()))
    n4 = len(b5_solved_4m.get(tid, set()))
    print(f"{tid:12s} {bucket:6s} {tags:40s} {n1:>3d}/{n_1m}  {n4:>3d}/{n_4m}")
