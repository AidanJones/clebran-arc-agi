"""Task generation for communication-through-curricula (roadmap 7b).

The enabling capability for the curriculum channel: a lineage "shows what it
learned" by *generating tasks that its discovered programs solve*. Run a
program forward on sampled input grids to synthesize (input → output)
demonstration pairs — a well-formed ARC task the program provably solves, and
a *variant* of the concept it captures (same transform, fresh instances). A
receiver that learns to solve such tasks is pushed toward the same
transformation/abstraction, so knowledge crosses the channel as *problems*,
not code.

This module is the forward generator; the curriculum *payload* (share a small
ordered set of these) and the order-aware learner are later increments.
"""
from __future__ import annotations

import random

from .data.loader import Task
from .dsl.interpreter import run_safe
from .dsl.program import Program

Grid = tuple

_MAX_OUT_CELLS = 900  # keep synthesised tasks ARC-scale (≤ 30×30-ish)


# ---------- structured input-grid samplers ----------
# Uniform-random grids rarely exercise a program meaningfully; ARC inputs have
# structure (a background with objects on it), so we sample that way.

def _blank(h: int, w: int, bg: int) -> list[list[int]]:
    return [[bg] * w for _ in range(h)]


def _sprinkle(rng: random.Random, h: int, w: int) -> Grid:
    bg = rng.choice((0, 0, 0, rng.randint(0, 9)))  # usually black background
    g = _blank(h, w, bg)
    k = rng.randint(1, max(1, h * w // 3))
    for _ in range(k):
        g[rng.randrange(h)][rng.randrange(w)] = rng.randint(0, 9)
    return tuple(tuple(r) for r in g)


def _rects(rng: random.Random, h: int, w: int) -> Grid:
    bg = rng.choice((0, 0, rng.randint(0, 9)))
    g = _blank(h, w, bg)
    for _ in range(rng.randint(1, 3)):
        r0, c0 = rng.randrange(h), rng.randrange(w)
        r1 = min(h, r0 + rng.randint(1, 3))
        c1 = min(w, c0 + rng.randint(1, 3))
        col = rng.randint(0, 9)
        for r in range(r0, r1):
            for c in range(c0, c1):
                g[r][c] = col
    return tuple(tuple(r) for r in g)


def _noise(rng: random.Random, h: int, w: int) -> Grid:
    ncol = rng.randint(2, 5)
    return tuple(tuple(rng.randrange(ncol) for _ in range(w)) for _ in range(h))


_SAMPLERS = (_sprinkle, _sprinkle, _rects, _noise)


def sample_input(rng: random.Random, min_size: int = 2, max_size: int = 8) -> Grid:
    h = rng.randint(min_size, max_size)
    w = rng.randint(min_size, max_size)
    return rng.choice(_SAMPLERS)(rng, h, w)


# ---------- validity / non-triviality filters ----------

def _ok_output(out) -> bool:
    return (
        out is not None
        and len(out) * len(out[0]) <= _MAX_OUT_CELLS
    )


def _valid_task(pairs: list[tuple[Grid, Grid]]) -> bool:
    """A synthesised task is worth sharing only if it is non-degenerate: the
    inputs vary, the transform actually does something on at least one pair,
    and the outputs are not all identical (a constant map is ambiguous)."""
    if len({i for i, _ in pairs}) < len(pairs):
        return False  # duplicate inputs
    if all(i == o for i, o in pairs):
        return False  # identity on every pair — trivial
    if len({o for _, o in pairs}) == 1:
        return False  # constant output — degenerate/ambiguous
    return True


# ---------- generation ----------

def generate_task(
    program: Program,
    rng: random.Random,
    abstractions: dict | None = None,
    n_pairs: int = 4,
    task_id: str | None = None,
    attempts: int = 300,
    min_size: int = 2,
    max_size: int = 8,
) -> Task | None:
    """Synthesise a task the `program` solves, by running it forward on sampled
    inputs. Returns a Task (n_pairs−1 train demos + 1 test) or None if the
    program couldn't yield enough non-degenerate pairs. The returned task is,
    by construction, solved by `program` — a variant that exemplifies what the
    program computes."""
    pairs: list[tuple[Grid, Grid]] = []
    seen: set = set()
    for _ in range(attempts):
        g = sample_input(rng, min_size, max_size)
        if g in seen:
            continue
        seen.add(g)
        out = run_safe(program, g, abstractions)
        if not _ok_output(out):
            continue
        pairs.append((g, out))
        if len(pairs) >= n_pairs:
            break
    if len(pairs) < max(2, n_pairs - 1):
        return None
    if not _valid_task(pairs):
        return None
    if task_id is None:
        task_id = f"gen_{abs(hash((program.to_json(), tuple(pairs)))) & 0xffffff:06x}"
    return Task(task_id=task_id, train=tuple(pairs[:-1]), test=(pairs[-1],))


def solves(program: Program, task: Task, abstractions: dict | None = None) -> bool:
    """Does `program` reproduce every pair of `task` (train + test)?"""
    return all(
        run_safe(program, i, abstractions) == o
        for i, o in task.train + task.test
    )


def prerequisite_curriculum(
    program: Program,
    rng: random.Random,
    abstractions: dict | None = None,
    n_pairs: int = 4,
    max_items: int = 5,
) -> list[tuple[int, Task]]:
    """Decompose a solved program into an *ordered* teaching curriculum.

    A solved program is a chain x0 = f0(…); x1 = f1(x0, …); …; O = fk(…). Each
    grid-producing **prefix** is a self-contained sub-transform — the earlier,
    simpler abstractions the final composition is built from. Generating a task
    from each prefix and ordering shortest-first gives a curriculum that
    *teaches each abstraction before the step that needs it*: to teach
    hconcat(I, vmirror(I)) you first show tasks that are just vmirror, then the
    composition. Returns [(depth, Task)] shortest-first; the full program's task
    is the final target. Prefixes whose intermediate value isn't a grid are
    skipped (nothing to demonstrate)."""
    items: list[tuple[int, Task]] = []
    seen_trains: set = set()
    n = len(program.statements)
    for i in range(n):
        prefix = Program(list(program.statements[: i + 1]))
        gt = generate_task(prefix, rng, abstractions=abstractions, n_pairs=n_pairs)
        if gt is None:
            continue
        if gt.train in seen_trains:      # same sub-transform as a shallower prefix
            continue
        seen_trains.add(gt.train)
        items.append((i + 1, gt))
    items.sort(key=lambda t: t[0])
    if len(items) > max_items:           # keep the shallowest prerequisites + the target
        items = items[: max_items - 1] + [items[-1]]
    return items
