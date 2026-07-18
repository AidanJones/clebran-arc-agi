"""Stage-1 subset selection — the deterministic recipe of §4.1.

Step A: depth proxy d from Hodel's solvers (solver_parse.solver_depths).
Step B: coarse reasoning-type tags from grid statistics.
Step C: 30 tasks (10×D1, 15×D2, 5×D3), tag-stratified, fixed seed.
Step D: sanity gate — reference solver must reproduce all demonstration
        pairs through our interpreter; failures are dropped and backfilled.

Output: data/stage1_subset.json
"""
from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path

from .data.loader import Task, load_split, REPO_ROOT
from .dsl.interpreter import run_safe
from .dsl.solver_parse import parse_all_solvers

SUBSET_PATH = REPO_ROOT / "data" / "stage1_subset.json"
SEED = 20260718  # fixed: date the subset was frozen

Grid = tuple


# ---------- Step B: reasoning-type tags (heuristics for stratification) ----

def _dims(g: Grid) -> tuple[int, int]:
    return len(g), len(g[0])


def _dihedral(g: Grid):
    def vm(x):  # vertical mirror
        return tuple(row[::-1] for row in x)

    def hm(x):
        return x[::-1]

    def tr(x):
        return tuple(zip(*x))

    yield vm(g); yield hm(g); yield tr(g)
    yield hm(vm(g))                # rot180
    yield tuple(zip(*g[::-1]))     # rot90
    yield tuple(zip(*g))[::-1]     # rot270
    yield vm(tr(g))                # anti-transpose-ish
    yield hm(tr(g))


def _bg(g: Grid) -> int:
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _mask(g: Grid, bg: int) -> frozenset:
    return frozenset(
        (i, j) for i, row in enumerate(g) for j, v in enumerate(row) if v != bg
    )


def tag_task(task: Task) -> list[str]:
    tags: set[str] = set()
    pairs = task.train
    if all(_dims(i) != _dims(o) for i, o in pairs):
        tags.add("size-change")
    if all(_dims(i) == _dims(o) for i, o in pairs):
        if all(i != o and any(t == o for t in _dihedral(i)) for i, o in pairs):
            tags.add("geometry")
        bgs = [_bg(i) for i, _ in pairs]
        if all(
            _mask(i, b) == _mask(o, b) and i != o
            for (i, o), b in zip(pairs, bgs)
        ):
            tags.add("recolour")
        if all(
            _mask(i, b) < _mask(o, b)
            for (i, o), b in zip(pairs, bgs)
        ):
            tags.add("symmetry-repair")
    if all(
        _dims(o)[0] * _dims(o)[1] <= 9 or len({v for r in o for v in r}) == 1
        for _, o in pairs
    ):
        tags.add("object-count")
    if not tags:
        tags.add("other")
    return sorted(tags)


# ---------- Steps C + D: selection with sanity gate ----------

def _bucket(d: int) -> str | None:
    if d <= 2:
        return "D1"
    if d <= 5:
        return "D2"
    if d <= 10:
        return "D3"
    return None  # D4 excluded


def _passes_gate(task: Task, prog) -> bool:
    return all(run_safe(prog, i) == o for i, o in task.train) and all(
        run_safe(prog, i) == o for i, o in task.test
    )


def build_subset(write: bool = True) -> dict:
    progs = parse_all_solvers()
    assert len(progs) == 400, "expected one solver per training task"
    assert all(len(p) >= 1 for p in progs.values()), "empty solver"
    tasks = load_split("training")
    depths = {tid: len(p) for tid, p in progs.items()}

    buckets: dict[str, list[str]] = {"D1": [], "D2": [], "D3": []}
    for tid in sorted(tasks):  # lexicographic — stable
        b = _bucket(depths[tid])
        if b is not None:
            buckets[b].append(tid)

    tags = {tid: tag_task(tasks[tid]) for tid in tasks}
    rng = random.Random(SEED)
    want = {"D1": 10, "D2": 15, "D3": 5}
    chosen: dict[str, list[str]] = {}

    for b, n in want.items():
        pool = [t for t in buckets[b]]
        rng.shuffle(pool)
        picked: list[str] = []
        tag_count: Counter = Counter()
        max_per_tag = max(2, int(n * 0.4))
        # greedy: prefer tasks whose tags are underrepresented; enforce gate
        for round_relax in (False, True):
            for tid in pool:
                if len(picked) == n:
                    break
                if tid in picked:
                    continue
                primary = tags[tid][0]
                if not round_relax and tag_count[primary] >= max_per_tag:
                    continue
                if not _passes_gate(tasks[tid], progs[tid]):
                    continue  # Step-D gate: drop, backfill from same bucket
                picked.append(tid)
                tag_count[primary] += 1
        assert len(picked) == n, f"bucket {b}: only {len(picked)}/{n} pass gate"
        chosen[b] = picked

    subset = {
        "seed": SEED,
        "recipe": "spec §4.1 v1.1",
        "tasks": [
            {
                "task_id": tid,
                "depth": depths[tid],
                "bucket": b,
                "tags": tags[tid],
            }
            for b in ("D1", "D2", "D3")
            for tid in sorted(chosen[b])
        ],
    }
    if write:
        SUBSET_PATH.parent.mkdir(exist_ok=True)
        SUBSET_PATH.write_text(json.dumps(subset, indent=2))
    return subset


def load_subset() -> list[dict]:
    return json.loads(SUBSET_PATH.read_text())["tasks"]


if __name__ == "__main__":
    s = build_subset()
    from collections import Counter as C

    print(f"wrote {SUBSET_PATH} with {len(s['tasks'])} tasks")
    for b in ("D1", "D2", "D3"):
        rows = [t for t in s["tasks"] if t["bucket"] == b]
        tag_hist = C(tag for t in rows for tag in t["tags"])
        print(b, len(rows), dict(tag_hist))
