"""Analyze the #3 task-subset specialization experiment.

Compares frontier solve counts (from the *summary* event, which is the
lineage's final state, not the first-solve-event state) across:

  - hard15 arm: B5-1M on the 15 hard tasks
  - random15 arm: B5-1M on 15 random stage1 tasks
  - B5-1M on full stage1 (30 tasks)
  - B5-4M on full stage1 (30 tasks)

Distinguishes:
  - summary.solved: tasks the lineage reports as solved at the end
  - test_exact solves: program passes BOTH train AND test pairs at the
    *first solve event* (some tasks admit spurious train-only solvers
    that are caught by the test pairs; these are "lure" tasks like
    1f85a75f)

Output: per-task solve rates, conditional solve rates, summary table.
"""
from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

LOGS = Path("logs")
DATA = Path("data")


def load_summary_solves(pattern: str) -> tuple[dict[str, set[int]], list[dict]]:
    """Return (test_exact_solves, summaries). test_exact_solves[task] is the
    set of seeds whose FINAL solution passes test_exact (i.e. the last
    time test_exact was logged for the task, it was true)."""
    test_exact_solves: dict[str, set[int]] = defaultdict(set)
    train_only_solves: dict[str, set[int]] = defaultdict(set)
    summaries: list[dict] = []
    logs = sorted(p for p in LOGS.glob(pattern)
                  if "dropped" not in p.name and "partial" not in p.name)
    for log in logs:
        seed = int(log.stem.split("seed")[-1])
        # Per task: collect all test_exact transitions. The *last* transition
        # tells us the final state.
        per_task_final_test_exact: dict[str, bool] = {}
        per_task_first_solve: dict[str, dict] = {}
        for line in log.read_text().splitlines():
            rec = json.loads(line)
            if rec.get("event") == "solve":
                tid = rec["task"]
                if tid not in per_task_first_solve:
                    per_task_first_solve[tid] = rec
                per_task_final_test_exact[tid] = bool(rec.get("test_exact"))
            elif rec.get("event") == "summary":
                summaries.append({
                    "log": log.name,
                    "seed": rec.get("seed"),
                    "solved": rec.get("solved"),
                    "solved_tasks": rec.get("solved_tasks", []),
                    "evals": rec.get("evals"),
                })
        for tid, is_test_exact in per_task_final_test_exact.items():
            if is_test_exact:
                test_exact_solves[tid].add(seed)
            else:
                train_only_solves[tid].add(seed)
    return test_exact_solves, train_only_solves, summaries


# Load stage1 task list and the two subsets
with (DATA / "stage1_subset.json").open() as f:
    stage1 = json.load(f)
stage1_tasks = {t["task_id"]: t for t in stage1["tasks"]}
hard15 = {t["task_id"] for t in json.loads((DATA / "hard15_subset.json").read_text())["tasks"]}
random15 = {t["task_id"] for t in json.loads((DATA / "random15_subset.json").read_text())["tasks"]}
print(f"hard15: {len(hard15)} tasks, random15: {len(random15)} tasks, intersection: {len(hard15 & random15)}")
print(f"  hard15 \\ random15: {sorted(hard15 - random15)}")
print(f"  random15 \\ hard15: {sorted(random15 - hard15)}")
print()

# Load test_exact solves and per-arm summary solves
hard15_te, hard15_to, hard15_summaries = load_summary_solves("hard15_b5_1m_seed*.jsonl")
random15_te, random15_to, random15_summaries = load_summary_solves("random15_b5_1m_seed*.jsonl")
stage1_1m_te, stage1_1m_to, stage1_1m_summaries = load_summary_solves("b5_1m_seed*.jsonl")
stage1_2m_te, stage1_2m_to, stage1_2m_summaries = load_summary_solves("b5_2m_seed*.jsonl")
stage1_4m_te, stage1_4m_to, stage1_4m_summaries = load_summary_solves("b5_4m_seed*.jsonl")

print(f"hard15: {len(hard15_summaries)} seeds, random15: {len(random15_summaries)} seeds, "
      f"stage1-1M: {len(stage1_1m_summaries)} seeds, stage1-2M: {len(stage1_2m_summaries)} seeds, "
      f"stage1-4M: {len(stage1_4m_summaries)} seeds")
print()


def per_seed_summary_solves(summaries: list[dict]) -> list[int]:
    return [s["solved"] for s in summaries]


def cond_summary_solve_rate(summaries: list[dict], task_set: set) -> float:
    if not task_set or not summaries:
        return 0.0
    per_seed = [sum(1 for tid in s["solved_tasks"] if tid in task_set) for s in summaries]
    return sum(per_seed) / len(per_seed)


def cond_test_exact_solve_rate(test_exact: dict, task_set: set, n_seeds: int) -> float:
    if not task_set or n_seeds == 0:
        return 0.0
    per_seed = [sum(1 for tid in task_set if s in test_exact.get(tid, set())) for s in range(1, n_seeds + 1)]
    return sum(per_seed) / len(per_seed)


# Summary-based solve rates (lineage's final state)
print("=== Frontier solve rate (lineage's final state, summary event) ===")
print(f"                                hard15     random15   full(30)")
print(f"  hard15  arm  (specialized):  {cond_summary_solve_rate(hard15_summaries, hard15):.2f}     n/a         n/a")
print(f"  random15 arm  (control):     {cond_summary_solve_rate(random15_summaries, hard15):.2f}     {cond_summary_solve_rate(random15_summaries, random15):.2f}     n/a")
print(f"  B5-1M on stage1 (baseline):  {cond_summary_solve_rate(stage1_1m_summaries, hard15):.2f}     {cond_summary_solve_rate(stage1_1m_summaries, random15):.2f}     {cond_summary_solve_rate(stage1_1m_summaries, set(stage1_tasks)):.2f}")
print(f"  B5-2M on stage1 (matched):  {cond_summary_solve_rate(stage1_2m_summaries, hard15):.2f}     {cond_summary_solve_rate(stage1_2m_summaries, random15):.2f}     {cond_summary_solve_rate(stage1_2m_summaries, set(stage1_tasks)):.2f}")
print(f"  B5-4M on stage1 (ref):       {cond_summary_solve_rate(stage1_4m_summaries, hard15):.2f}     {cond_summary_solve_rate(stage1_4m_summaries, random15):.2f}     {cond_summary_solve_rate(stage1_4m_summaries, set(stage1_tasks)):.2f}")
print()

# Test-exact solve rates
print("=== Test-exact solve rate (program passes BOTH train and test pairs) ===")
print(f"                                hard15     random15   full(30)")
print(f"  hard15  arm  (specialized):  {cond_test_exact_solve_rate(hard15_te, hard15, len(hard15_summaries)):.2f}     n/a         n/a")
print(f"  random15 arm  (control):     {cond_test_exact_solve_rate(random15_te, hard15, len(random15_summaries)):.2f}     {cond_test_exact_solve_rate(random15_te, random15, len(random15_summaries)):.2f}     n/a")
print(f"  B5-1M on stage1 (baseline):  {cond_test_exact_solve_rate(stage1_1m_te, hard15, len(stage1_1m_summaries)):.2f}     {cond_test_exact_solve_rate(stage1_1m_te, random15, len(stage1_1m_summaries)):.2f}     {cond_test_exact_solve_rate(stage1_1m_te, set(stage1_tasks), len(stage1_1m_summaries)):.2f}")
print(f"  B5-2M on stage1 (matched):  {cond_test_exact_solve_rate(stage1_2m_te, hard15, len(stage1_2m_summaries)):.2f}     {cond_test_exact_solve_rate(stage1_2m_te, random15, len(stage1_2m_summaries)):.2f}     {cond_test_exact_solve_rate(stage1_2m_te, set(stage1_tasks), len(stage1_2m_summaries)):.2f}")
print(f"  B5-4M on stage1 (ref):       {cond_test_exact_solve_rate(stage1_4m_te, hard15, len(stage1_4m_summaries)):.2f}     {cond_test_exact_solve_rate(stage1_4m_te, random15, len(stage1_4m_summaries)):.2f}     {cond_test_exact_solve_rate(stage1_4m_te, set(stage1_tasks), len(stage1_4m_summaries)):.2f}")
print()

# Per-seed frontier
print("=== Per-seed frontier (lineage's final state) ===")
print(f"  hard15 arm (specialized):  {per_seed_summary_solves(hard15_summaries)}")
print(f"  random15 arm (control):    {per_seed_summary_solves(random15_summaries)}")
print(f"  B5-1M on full stage1:      {per_seed_summary_solves(stage1_1m_summaries)}")
print(f"  B5-2M on full stage1:      {per_seed_summary_solves(stage1_2m_summaries)}")
print(f"  B5-4M on full stage1:      {per_seed_summary_solves(stage1_4m_summaries)}")
print()


# Hypothesis tests (Welch, normal approximation)
def welch_p(mean1, var1, n1, mean2, var2, n2):
    se = math.sqrt(var1 / n1 + var2 / n2)
    if se == 0:
        return 1.0
    t = (mean1 - mean2) / se
    return 2 * (1 - 0.5 * (1 + math.erf(abs(t) / math.sqrt(2))))


def variance(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = sum(values) / len(values)
    return sum((x - m) ** 2 for x in values) / (len(values) - 1)


# Per-seed within hard15 task set
def per_seed_in_subset(summaries: list[dict], task_set: set) -> list[int]:
    return [sum(1 for tid in s["solved_tasks"] if tid in task_set) for s in summaries]


hard_hard = per_seed_in_subset(hard15_summaries, hard15)
random_hard = per_seed_in_subset(random15_summaries, hard15)
stage1_1m_hard = per_seed_in_subset(stage1_1m_summaries, hard15)
stage1_1m_random = per_seed_in_subset(stage1_1m_summaries, random15)
stage1_2m_hard = per_seed_in_subset(stage1_2m_summaries, hard15)
stage1_2m_random = per_seed_in_subset(stage1_2m_summaries, random15)
random_random = per_seed_in_subset(random15_summaries, random15)

print("=== Per-seed within task set (lineage's final state) ===")
print(f"  hard15 arm on hard15 sub:    {hard_hard}")
print(f"  random15 arm on hard15 sub:  {random_hard}")
print(f"  random15 arm on random15 sub:{random_random}")
print(f"  B5-1M on hard15 sub:         {stage1_1m_hard}")
print(f"  B5-1M on random15 sub:       {stage1_1m_random}")
print(f"  B5-2M on hard15 sub:         {stage1_2m_hard}    (matched-compute baseline: 67k/task)")
print(f"  B5-2M on random15 sub:       {stage1_2m_random}    (matched-compute baseline: 67k/task)")
print()

print("=== Hypothesis tests (Welch, normal approximation) ===")
p_hard_specialized = welch_p(
    sum(hard_hard) / len(hard_hard), variance([float(x) for x in hard_hard]), len(hard_hard),
    sum(stage1_1m_hard) / len(stage1_1m_hard), variance([float(x) for x in stage1_1m_hard]), len(stage1_1m_hard),
)
p_random_specialized = welch_p(
    sum(random_random) / len(random_random), variance([float(x) for x in random_random]), len(random_random),
    sum(stage1_1m_random) / len(stage1_1m_random), variance([float(x) for x in stage1_1m_random]), len(stage1_1m_random),
)
# Matched-compute test: does B5-2M-on-random15 (67k/task) match the
# random15-arm-on-random15 (67k/task)? If yes, the random15 arm's gain
# is fully explained by 2x per-task compute.
p_matched_random = welch_p(
    sum(random_random) / len(random_random), variance([float(x) for x in random_random]), len(random_random),
    sum(stage1_2m_random) / len(stage1_2m_random), variance([float(x) for x in stage1_2m_random]), len(stage1_2m_random),
)
print(f"  hard15-specialized vs B5-1M-on-hard15:    p = {p_hard_specialized:.3f}  (H: specialized helps)")
print(f"  random15-specialized vs B5-1M-on-rand:    p = {p_random_specialized:.3f}  (H: specialization on any subset helps)")
print(f"  random15-arm vs B5-2M-on-rand (matched):  p = {p_matched_random:.3f}  (H: specialization on top of 2x compute)")
print()

# Train-only (overfit) analysis
print("=== Lure tasks (solved train-only, rejected by test pairs) ===")
for label, d in [("hard15", hard15_to), ("random15", random15_to),
                 ("b5_1m", stage1_1m_to), ("b5_2m", stage1_2m_to),
                 ("b5_4m", stage1_4m_to)]:
    items = sorted(d.items(), key=lambda kv: -len(kv[1]))
    n_unique = len(items)
    n_events = sum(len(v) for v in d.values())
    s = ", ".join(f"{tid}({len(v)})" for tid, v in items[:5]) if items else "-"
    print(f"  {label}: {n_events} events, {n_unique} unique tasks  [{s}]")
