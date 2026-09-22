"""Build the two subset files for the #3 task-subset specialization experiment.

hard15_subset.json: 15 tasks from stage1 that B5-4M (15 seeds) never solved.
random15_subset.json: 15 random tasks from stage1, fixed seed.

Output files follow the same schema as data/stage1_subset.json so the
existing subset loader picks them up via the CLEBRAN_SUBSET env var.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

DATA = Path("data")

with (DATA / "stage1_subset.json").open() as f:
    stage1 = json.load(f)
stage1_tasks = stage1["tasks"]
print(f"stage1 tasks: {len(stage1_tasks)}")

# 15 hard tasks: unsolved at B5-4M (computed from logs/b5_4m_seed*.jsonl)
HARD_15 = [
    "007bbfb7", "0b148d64", "1190e5a7", "178fcbfb", "1f85a75f",
    "2dc579da", "32597951", "41e4d17e", "46f33fce", "6f8cd79b",
    "a79310a0", "ae4f1146", "ba97ae07", "be94b721", "ce22a75a",
]
hard_records = [t for t in stage1_tasks if t["task_id"] in HARD_15]
assert len(hard_records) == 15, f"got {len(hard_records)} hard records"
print(f"hard15 tasks: {len(hard_records)}")

hard_subset = {
    "seed": stage1["seed"],
    "recipe": "subset-spec #3: 15 stage1 tasks unsolved by B5-4M (15 seeds)",
    "composition": {"hard15": 15},
    "tasks": sorted(hard_records, key=lambda t: t["task_id"]),
}

with (DATA / "hard15_subset.json").open("w") as f:
    json.dump(hard_subset, f, indent=2)
print(f"wrote data/hard15_subset.json ({len(hard_records)} tasks)")

# 15 random tasks: 15 stage1 tasks, fixed seed
rng = random.Random(20260831)
random_15_ids = sorted(rng.sample([t["task_id"] for t in stage1_tasks], 15))
random_records = [t for t in stage1_tasks if t["task_id"] in random_15_ids]
assert len(random_records) == 15
print(f"random15 tasks: {random_15_ids}")

random_subset = {
    "seed": 20260831,
    "recipe": "subset-spec #3: 15 stage1 tasks, deterministic random sample",
    "composition": {"random15": 15},
    "tasks": sorted(random_records, key=lambda t: t["task_id"]),
}

with (DATA / "random15_subset.json").open("w") as f:
    json.dump(random_subset, f, indent=2)
print(f"wrote data/random15_subset.json ({len(random_records)} tasks)")
