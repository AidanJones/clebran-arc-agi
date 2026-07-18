"""Shared machinery for baseline runners B0–B5.

Compute unit: candidate-evaluations, metered by Evaluator. Every arm gets
`budget` total evaluations; the §8.1-stage-3 audit checks the arms landed
within ±1% of each other.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from ..data.loader import Task, load_task, REPO_ROOT
from ..dsl.solver_parse import parse_all_solvers
from ..subset import load_subset

LOG_DIR = REPO_ROOT / "logs"


def subset_tasks() -> dict[str, Task]:
    return {row["task_id"]: load_task("training", row["task_id"]) for row in load_subset()}


def subset_pool() -> list[str]:
    """Primitive pool for Stage 1: union of primitives used by the subset
    tasks' reference solvers. Guarantees every subset task is solvable
    within the pool; uses training-split info only."""
    progs = parse_all_solvers()
    pool: set[str] = set()
    for row in load_subset():
        pool |= progs[row["task_id"]].primitives_used()
    return sorted(pool)


class RunLog:
    def __init__(self, run_name: str):
        LOG_DIR.mkdir(exist_ok=True)
        self.path = LOG_DIR / f"{run_name}.jsonl"
        self._fh = self.path.open("w")
        self.t0 = time.time()

    def write(self, record: dict) -> None:
        record["t"] = round(time.time() - self.t0, 2)
        self._fh.write(json.dumps(record) + "\n")
        self._fh.flush()

    def close(self) -> None:
        self._fh.close()
