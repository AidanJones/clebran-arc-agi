"""Analyze the #4 novelty-search arm (B5N) experiment.

Compares the novelty-search arm against B5-1M (accuracy baseline)
and the B5-2M matched-compute baseline.

Endpoints:
  - test-exact solves per task (any test-exact individual evaluated
    during the run, regardless of which one was the elite)
  - frontier solves (lineage's claim of solved_frac == 1)
  - per-seed novelty-archive size (how many distinct programs were
    evaluated on each task)
  - per-task unique-to-novelty test-exact solves

Output: per-task solve rates, conditional solve rates, summary table,
unique-to-novelty list.
"""
from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

LOGS = Path("logs")
DATA = Path("data")


def load_b5n_solves(pattern: str) -> tuple[dict[str, set[int]], dict[str, set[int]]]:
    """Return (test_exact_solves, train_only_solves). test_exact_solves[task] is
    the set of seeds whose log shows at least one test-exact solver (the
    novelty mode emits a solve event with test_exact=True whenever a new
    test-exact solver is found via the evaluator archive)."""
    test_exact: dict[str, set[int]] = defaultdict(set)
    train_only: dict[str, set[int]] = defaultdict(set)
    for log in sorted(LOGS.glob(pattern)):
        if "dropped" in log.name or "partial" in log.name:
            continue
        seed = int(log.stem.split("seed")[-1])
        for line in log.read_text().splitlines():
            rec = json.loads(line)
            if rec.get("event") == "solve":
                if rec.get("test_exact") is True:
                    test_exact[rec["task"]].add(seed)
                else:
                    train_only[rec["task"]].add(seed)
            elif rec.get("event") == "summary":
                # Summary also reports test_exact (count) and solved_tasks.
                # Use it as a fallback if no per-solve events fired.
                pass
    return test_exact, train_only


def load_b5_solves(pattern: str) -> tuple[dict[str, set[int]], dict[str, set[int]]]:
    """B5 / B5-1M / B5-2M / B5-4M loader: same shape but the train-only
    distinction comes from per-task-final-test-exact."""
    test_exact: dict[str, set[int]] = defaultdict(set)
    train_only: dict[str, set[int]] = defaultdict(set)
    for log in sorted(LOGS.glob(pattern)):
        if "dropped" in log.name or "partial" in log.name:
            continue
        seed = int(log.stem.split("seed")[-1])
        per_task_final_test_exact: dict[str, bool] = {}
        for line in log.read_text().splitlines():
            rec = json.loads(line)
            if rec.get("event") == "solve":
                tid = rec["task"]
                per_task_final_test_exact[tid] = bool(rec.get("test_exact"))
        for tid, is_te in per_task_final_test_exact.items():
            if is_te:
                test_exact[tid].add(seed)
            else:
                train_only[tid].add(seed)
    return test_exact, train_only


def per_seed_count(solves: dict[str, set[int]], task_set: set, n_seeds: int) -> list[int]:
    per_seed = []
    for s in range(1, n_seeds + 1):
        per_seed.append(sum(1 for tid in task_set if s in solves.get(tid, set())))
    return per_seed


# Load stage1 task list
stage1 = json.loads((DATA / "stage1_subset.json").read_text())
stage1_tasks = {t["task_id"] for t in stage1["tasks"]}

# B5N (novelty arm)
b5n_te, b5n_to = load_b5n_solves("b5n_*_seed*.jsonl")
# B5-1M, B5-2M (accuracy baselines)
b5_1m_te, b5_1m_to = load_b5_solves("b5_1m_seed*.jsonl")
b5_2m_te, b5_2m_to = load_b5_solves("b5_2m_seed*.jsonl")

# Count novelty seeds (B5N)
n_b5n = max((max(v) for v in b5n_te.values()), default=0)
n_b5n = max(n_b5n, max((max(v) for v in b5n_to.values()), default=0))
n_b5_1m = max((max(v) for v in b5_1m_te.values()), default=0)
n_b5_2m = max((max(v) for v in b5_2m_te.values()), default=0)

print(f"Loaded: B5N {n_b5n} seeds, B5-1M {n_b5_1m} seeds, B5-2M {n_b5_2m} seeds")
print()

# Per-task test-exact solve rates (mean over seeds)
def rate(solves, task_set, n_seeds):
    if not task_set or n_seeds == 0:
        return 0.0
    return sum(per_seed_count(solves, task_set, n_seeds)) / n_seeds


b5n_rate = rate(b5n_te, stage1_tasks, n_b5n)
b5_1m_rate = rate(b5_1m_te, stage1_tasks, n_b5_1m)
b5_2m_rate = rate(b5_2m_te, stage1_tasks, n_b5_2m)
print("=== Test-exact solve rate (mean over seeds) on full stage1 (30 tasks) ===")
print(f"  B5N (novelty, 1M):  {b5n_rate:.2f} ({len([t for t in stage1_tasks if b5n_te.get(t)])}/{len(stage1_tasks)} tasks ever solved)")
print(f"  B5-1M (accuracy):   {b5_1m_rate:.2f}")
print(f"  B5-2M (accuracy):   {b5_2m_rate:.2f}")
print()

# Per-seed on full stage1
b5n_per_seed = per_seed_count(b5n_te, stage1_tasks, n_b5n)
b5_1m_per_seed = per_seed_count(b5_1m_te, stage1_tasks, n_b5_1m)
print("=== Per-seed test-exact solves on full stage1 (lineage's full run) ===")
print(f"  B5N : {b5n_per_seed}    mean {sum(b5n_per_seed)/max(n_b5n,1):.2f}")
print(f"  B5-1M: {b5_1m_per_seed}    mean {sum(b5_1m_per_seed)/max(n_b5_1m,1):.2f}")
print()

# Unique-to-novelty
unique_to_novelty = sorted(
    t for t in stage1_tasks
    if b5n_te.get(t) and not b5_1m_te.get(t)
)
unique_to_b5 = sorted(
    t for t in stage1_tasks
    if b5_1m_te.get(t) and not b5n_te.get(t)
)
overlap = sorted(
    t for t in stage1_tasks
    if b5n_te.get(t) and b5_1m_te.get(t)
)
print(f"=== Overlap on test-exact (any seed) ===")
print(f"  unique to B5N:       {unique_to_novelty}")
print(f"  unique to B5-1M:     {unique_to_b5}")
print(f"  overlap:             {overlap}")
print()

# Lure tasks (train-only)
print(f"=== Lure tasks (solved train-only, rejected by test pairs) ===")
for label, d in [("B5N", b5n_to), ("B5-1M", b5_1m_to), ("B5-2M", b5_2m_to)]:
    items = sorted(d.items(), key=lambda kv: -len(kv[1]))
    n_unique = len(items)
    n_events = sum(len(v) for v in d.values())
    s = ", ".join(f"{tid}({len(v)})" for tid, v in items[:5]) if items else "-"
    print(f"  {label}: {n_events} events, {n_unique} unique tasks  [{s}]")
print()

# Per-task novelty archive (from summary)
print("=== Per-task novelty-archive sizes (mean over B5N seeds) ===")
archive_sizes: dict[str, list[int]] = defaultdict(list)
for log in sorted(LOGS.glob("b5n_*_seed*.jsonl")):
    if "dropped" in log.name or "partial" in log.name:
        continue
    seed = int(log.stem.split("seed")[-1])
    for line in log.read_text().splitlines():
        rec = json.loads(line)
        if rec.get("event") == "summary":
            for tid, size in rec.get("novelty_archive_per_task", {}).items():
                archive_sizes[tid].append(size)
for tid in sorted(stage1_tasks):
    sizes = archive_sizes.get(tid, [])
    if sizes:
        mean = sum(sizes) / len(sizes)
        print(f"  {tid}: mean archive size {mean:.0f} (n={len(sizes)})")
print()

# Per-seed frontier / test-exact per task
print("=== Test-exact task-by-task (mean over seeds) ===")
print(f"  {'task':<10} {'B5N':<6} {'B5-1M':<6} {'B5-2M':<6}")
for tid in sorted(stage1_tasks):
    n_b5n_t = len(b5n_te.get(tid, set()))
    n_b5_1m_t = len(b5_1m_te.get(tid, set()))
    n_b5_2m_t = len(b5_2m_te.get(tid, set()))
    print(f"  {tid:<10} {n_b5n_t:<6} {n_b5_1m_t:<6} {n_b5_2m_t:<6}")