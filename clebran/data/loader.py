"""ARC-AGI-1 task loading."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ARC_DATA = REPO_ROOT / "third_party" / "ARC-AGI" / "data"

Grid = tuple


def _to_grid(rows: list[list[int]]) -> Grid:
    return tuple(tuple(r) for r in rows)


@dataclass(frozen=True)
class Task:
    task_id: str
    train: tuple[tuple[Grid, Grid], ...]  # demonstration (input, output) pairs
    test: tuple[tuple[Grid, Grid], ...]   # held-out pairs (output known in dataset)


def load_task(split: str, task_id: str) -> Task:
    path = ARC_DATA / split / f"{task_id}.json"
    raw = json.loads(path.read_text())
    return Task(
        task_id=task_id,
        train=tuple(
            (_to_grid(p["input"]), _to_grid(p["output"])) for p in raw["train"]
        ),
        test=tuple(
            (_to_grid(p["input"]), _to_grid(p["output"])) for p in raw["test"]
        ),
    )


def load_split(split: str) -> dict[str, Task]:
    tasks = {}
    for path in sorted((ARC_DATA / split).glob("*.json")):
        tasks[path.stem] = load_task(split, path.stem)
    return tasks
