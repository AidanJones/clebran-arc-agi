"""GP-evolved L1: a learned L1 evolved by clebran's own GP operators.

The GP-evolved L1 is the second programmatic-L1 baseline. For each
of the top grid→grid primitives, evolve a small clebran program
(length 1-3) that, given a state grid, produces the same output
as the primitive would. The clebran ``GenomeOps`` provides the
mutation / crossover / repair operators; the GP loop and the
L1-specific fitness function are here.

**Why per-primitive?** A single program that takes a primitive as
an input would need a conditional dispatch, which the clebran
typed IR doesn't support cleanly. Per-primitive evolution is
simpler and the clebran IR's statics naturally support it: each
program takes a grid (``I``) and produces a grid (the next
register).

**Fitness.** The evolved program is scored on held-out training
rows. The default fitness is *smoothed exact-match*:

* 1.0 if the evolved output equals the trace's next_state exactly
* 0.5 if the output has the same shape (encourages the GP to
  find shape-correct solutions first)
* 0.0 otherwise (the most common case for early generations)

The smoothing lets the GP find progress when exact match is too
sparse; the final reported accuracy uses exact match.

**No neural net.** The evolved L1 is a clebran program — a
sequence of typed statements over Hodel's primitives. It is
executed by the same deterministic, exception-guarded
interpreter the rest of the rig uses; the L1 is a real
program, not a parameter fit.
"""
from __future__ import annotations

import json
import random
import time
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from ..dsl.interpreter import run, run_safe
from ..dsl.program import Program
from ..dsl.registry import PRIMITIVES
from ..genome import GenomeOps


# ----- helpers ------------------------------------------------------------

def _grid_key(grid) -> tuple:
    """Hashable key for a grid."""
    if isinstance(grid, tuple) and grid and isinstance(grid[0], tuple):
        return grid
    return tuple(tuple(row) for row in grid)


def _grid_hamming(a, b) -> int:
    if len(a) != len(b):
        return 10**9
    d = 0
    for ra, rb in zip(a, b):
        if len(ra) != len(rb):
            return 10**9
        for xa, xb in zip(ra, rb):
            if xa != xb:
                d += 1
    return d


def _shape_of(grid) -> tuple | None:
    if not isinstance(grid, tuple) or not grid or not isinstance(grid[0], tuple):
        return None
    return (len(grid), len(grid[0]))


# ----- the L1 -------------------------------------------------------------

class EvolvedL1PerPrimitive:
    """A single evolved program for one primitive. The program
    takes a state grid and returns the evolved L1's prediction.

    Scoring: smoothed exact-match (1.0 exact, 0.5 shape, 0.0 else).
    """

    def __init__(self, program: Program | None, fitness: float,
                 n_train: int, n_exact: int, n_shape: int):
        self.program = program
        self.fitness = fitness
        self.n_train = n_train
        self.n_exact = n_exact
        self.n_shape = n_shape

    def predict(self, state_grid):
        if self.program is None:
            return None
        return run_safe(self.program, state_grid)

    def __repr__(self):
        return (f"EvolvedL1PerPrimitive(fitness={self.fitness:.3f}, "
                f"exact={self.n_exact}/{self.n_train}, "
                f"shape={self.n_shape}/{self.n_train})")


class GPL1:
    """A GP-evolved L1: a dict of primitive_name → evolved program.

    Parameters
    ----------
    rows : list of dict
        Training rows from the trace dataset. Each row must have
        ``state.kind == "grid"`` and ``next_state.kind == "grid"``.
    primitives : list of str, optional
        The primitive names to evolve an L1 for. If None, uses
        every primitive that has at least ``min_rows_per_primitive``
        training rows.
    pop_size : int, default 50
        Population size per primitive.
    n_generations : int, default 8
        Number of GP generations per primitive.
    max_program_len : int, default 3
        Maximum length of the evolved program. The clebran
        interpreter is fast (microseconds per statement), so 1-3
        statements is the right budget for a fast L1.
    min_rows_per_primitive : int, default 5
        Skip primitives with fewer training rows (the GP has
        nothing to learn from).
    seed : int, default 0
        Random seed for the GP.
    """

    def __init__(self, rows: list[dict], primitives: list[str] | None = None,
                 pop_size: int = 50, n_generations: int = 8,
                 max_program_len: int = 3, min_rows_per_primitive: int = 5,
                 seed: int = 0, verbose: bool = True):
        # Group rows by primitive name.
        by_prim: dict[str, list[dict]] = defaultdict(list)
        for r in rows:
            if (r["state"]["kind"] != "grid"
                    or r["next_state"]["kind"] != "grid"):
                continue
            prim = r["action"]["fn"]
            # The trace dataset's `action.fn` is sometimes an int
            # (a constant like 0, 1, 2 used as an action head) and
            # sometimes a string (a primitive name). The L1 GP
            # only handles primitive heads (str), so we filter.
            if not isinstance(prim, str):
                continue
            by_prim[prim].append(r)
        # Decide which primitives to evolve.
        if primitives is None:
            primitives = sorted([
                p for p, rs in by_prim.items()
                if len(rs) >= min_rows_per_primitive
            ])
        # The grid→grid primitive pool for the GP. We restrict to
        # primitives whose arity is compatible with taking a grid
        # as the only input.
        grid_prim_pool = [
            p for p, sig in PRIMITIVES.items()
            if sig.arity == 1 and sig.params == ("Piece",)
        ]
        # Evolve one program per primitive.
        self.evolved: dict[str, EvolvedL1PerPrimitive] = {}
        rng = random.Random(seed)
        for prim in primitives:
            prim_rows = by_prim[prim]
            if verbose:
                print(f"  evolving L1 for primitive {prim!r} "
                      f"({len(prim_rows)} training rows) ...")
            evo = self._evolve_primitive(prim, prim_rows, grid_prim_pool,
                                         pop_size=pop_size,
                                         n_generations=n_generations,
                                         max_program_len=max_program_len,
                                         seed=rng.randint(0, 2**32),
                                         verbose=verbose)
            self.evolved[prim] = evo
        self.pop_size = pop_size
        self.n_generations = n_generations
        self.max_program_len = max_program_len
        self.seed = seed
        self.timing = {}  # populated by benchmark()

    def _score_program(self, program: Program, train_states: list,
                        train_targets: list) -> tuple[float, int, int]:
        """Score a program on the (state, next_state) pairs. Returns
        (mean_fitness, n_exact, n_shape)."""
        if not train_states:
            return 0.0, 0, 0
        n_exact = 0
        n_shape = 0
        total = 0.0
        for s, t in zip(train_states, train_targets):
            try:
                pred = run(program, s)
            except Exception:
                pred = None
            if pred is None:
                total += 0.0
                continue
            if pred == t:
                n_exact += 1
                total += 1.0
            elif _shape_of(pred) == _shape_of(t):
                n_shape += 1
                total += 0.5
        return total / len(train_states), n_exact, n_shape

    def _evolve_primitive(self, prim: str, prim_rows: list[dict],
                           grid_prim_pool: list[str], pop_size: int,
                           n_generations: int, max_program_len: int,
                           seed: int, verbose: bool) -> EvolvedL1PerPrimitive:
        """Run a small GP loop for one primitive. Returns the best
        evolved program (or None if no progress was made)."""
        rng = random.Random(seed)
        # Pre-extract (state, target) tuples for fast fitness eval.
        train_states = [tuple(tuple(row) for row in r["state"]["grid"])
                        for r in prim_rows]
        train_targets = [tuple(tuple(row) for row in r["next_state"]["grid"])
                         for r in prim_rows]
        # Initialise the GP operators.
        ops = GenomeOps(pool=grid_prim_pool, rng=rng,
                         max_len=max_program_len)
        # Initialise the population with random programs of length
        # 1 to max_program_len. We bias toward shorter programs
        # for speed.
        population: list[Program] = []
        for _ in range(pop_size):
            length = rng.randint(1, max_program_len)
            p = ops.random_program(length=length)
            if p is not None:
                population.append(p)
        if not population:
            return EvolvedL1PerPrimitive(None, 0.0, len(train_states), 0, 0)
        # Score the initial population.
        scores: list[tuple[float, int, int, Program]] = []
        for p in population:
            score, ne, ns = self._score_program(p, train_states, train_targets)
            scores.append((score, ne, ns, p))
        # GP loop. Tournament selection + mutation + crossover.
        for gen in range(n_generations):
            # Sort by score (descending). Elitism: keep the top 10%.
            scores.sort(key=lambda x: x[0], reverse=True)
            elite_n = max(1, pop_size // 10)
            new_population: list[Program] = [s[3] for s in scores[:elite_n]]
            # Fill the rest with offspring via tournament selection
            # and mutation / crossover.
            while len(new_population) < pop_size:
                # Tournament of size 3.
                t1, t2, t3 = (scores[rng.randrange(len(scores))][3]
                               for _ in range(3))
                winner1 = max(t1, t2, key=lambda p: self._score_program(
                    p, train_states[:10], train_targets[:10])[0])
                t1, t2, t3 = (scores[rng.randrange(len(scores))][3]
                               for _ in range(3))
                winner2 = max(t1, t2, t3, key=lambda p: self._score_program(
                    p, train_states[:10], train_targets[:10])[0])
                # Crossover (50%) or mutation (50%).
                if rng.random() < 0.5 and len(winner1.statements) > 0 and len(winner2.statements) > 0:
                    child = ops.crossover(winner1, winner2)
                else:
                    child = ops.mutate(winner1)
                if child is not None:
                    new_population.append(child)
            # Re-score the new population.
            population = new_population
            scores = []
            for p in population:
                score, ne, ns = self._score_program(p, train_states, train_targets)
                scores.append((score, ne, ns, p))
            if verbose and (gen + 1) % max(1, n_generations // 4) == 0:
                best = scores[0]
                print(f"    gen {gen+1:>2}/{n_generations}: "
                      f"best fitness={best[0]:.3f}, "
                      f"exact={best[1]}/{len(train_states)}, "
                      f"shape={best[2]}/{len(train_states)}")
        # Final scoring on the full training set.
        scores.sort(key=lambda x: x[0], reverse=True)
        best_score, best_exact, best_shape, best_program = scores[0]
        return EvolvedL1PerPrimitive(
            program=best_program,
            fitness=best_score,
            n_train=len(train_states),
            n_exact=best_exact,
            n_shape=best_shape,
        )

    def predict(self, state_grid, action: dict):
        """Return the evolved L1's prediction for the (state, action)
        pair, or None if no evolved program is available for the
        primitive.
        """
        prim = action["fn"]
        evo = self.evolved.get(prim)
        if evo is None or evo.program is None:
            return None
        return evo.predict(state_grid)

    def benchmark(self, test_rows: list[dict], n_repeats: int = 3) -> dict:
        """Measure predict-time speed on ``test_rows``."""
        test = [r for r in test_rows
                if r["state"]["kind"] == "grid"
                and r["next_state"]["kind"] == "grid"]
        queries = []
        for r in test:
            state = tuple(tuple(row) for row in r["state"]["grid"])
            queries.append((state, r["action"]["fn"]))
        best_us = float("inf")
        for _ in range(n_repeats):
            t0 = time.perf_counter_ns()
            for state, prim in queries:
                evo = self.evolved.get(prim)
                if evo is not None and evo.program is not None:
                    _ = run_safe(evo.program, state)
            t1 = time.perf_counter_ns()
            elapsed_us = (t1 - t0) / 1000.0
            if elapsed_us < best_us:
                best_us = elapsed_us
        per_row_us = best_us / max(1, len(queries))
        return {
            "n_test_rows": len(test),
            "predict_time_us": per_row_us,
            "predictions_per_sec": 1e6 / per_row_us if per_row_us else 0.0,
        }


# ----- CLI entry point ----------------------------------------------------

def main(trace_path: Path = Path("data/traces.jsonl"),
         test_frac: float = 0.2, seed: int = 0,
         pop_size: int = 50, n_generations: int = 8,
         max_program_len: int = 3) -> int:
    """Evolve an L1 for each of the top grid→grid primitives and
    report accuracy + speed on the held-out test rows.
    """
    print(f"loading trace dataset from {trace_path} ...")
    rows = [json.loads(l) for l in trace_path.read_text(encoding="utf-8").splitlines()]
    print(f"  loaded {len(rows):,} rows")
    # Train/test split by task.
    rng = random.Random(seed)
    tasks = sorted(set(r["task_id"] for r in rows))
    rng.shuffle(tasks)
    cutoff = int(round(len(tasks) * test_frac))
    test_tasks = set(tasks[:cutoff])
    train = [r for r in rows if r["task_id"] not in test_tasks]
    test = [r for r in rows if r["task_id"] in test_tasks]
    print(f"  train rows: {len(train):,}, test rows: {len(test):,}")
    train_grid = [r for r in train
                  if r["state"]["kind"] == "grid"
                  and r["next_state"]["kind"] == "grid"]
    test_grid = [r for r in test
                 if r["state"]["kind"] == "grid"
                 and r["next_state"]["kind"] == "grid"]
    print(f"  train grid rows: {len(train_grid):,}, "
          f"test grid rows: {len(test_grid):,}")
    # Evolve.
    print()
    print(f"evolving GP-L1 (pop_size={pop_size}, "
          f"n_generations={n_generations}, max_program_len={max_program_len}) ...")
    t0 = time.time()
    gp = GPL1(train_grid, pop_size=pop_size, n_generations=n_generations,
              max_program_len=max_program_len, seed=seed, verbose=True)
    t1 = time.time()
    print(f"\nevolution took {t1 - t0:.1f}s")
    # Per-primitive training accuracy.
    print()
    print("training accuracy per primitive (top 10 by rows):")
    by_prim_count: dict[str, int] = defaultdict(int)
    for r in train_grid:
        by_prim_count[r["action"]["fn"]] += 1
    top_prims = sorted(by_prim_count.items(), key=lambda x: -x[1])[:10]
    for prim, count in top_prims:
        evo = gp.evolved.get(prim)
        if evo is None:
            print(f"  {prim:>20s}: not evolved (only {count} rows)")
            continue
        print(f"  {prim:>20s}: fitness={evo.fitness:.3f}, "
              f"exact={evo.n_exact}/{evo.n_train}, "
              f"shape={evo.n_shape}/{evo.n_train}")
    # Benchmark.
    print()
    print("benchmarking on test rows ...")
    bench = gp.benchmark(test_grid, n_repeats=3)
    for k, v in bench.items():
        if isinstance(v, float):
            print(f"  {k:>22s} = {v:.4f}")
        else:
            print(f"  {k:>22s} = {v}")
    # Test accuracy.
    print()
    print("test-set accuracy per primitive:")
    by_prim_test: dict[str, list[dict]] = defaultdict(list)
    for r in test_grid:
        prim = r["action"]["fn"]
        if not isinstance(prim, str):
            continue
        by_prim_test[prim].append(r)
    total_exact = 0
    total_shape = 0
    total = 0
    n_evolved_used = 0
    n_fallback = 0
    for prim, prim_test in by_prim_test.items():
        evo = gp.evolved.get(prim)
        n_e = 0
        n_s = 0
        n_total = len(prim_test)
        for r in prim_test:
            state = tuple(tuple(row) for row in r["state"]["grid"])
            truth = r["next_state"]
            if evo is None or evo.program is None:
                n_fallback += 1
                continue
            n_evolved_used += 1
            try:
                pred_grid = run(evo.program, state)
            except Exception:
                continue
            truth_grid = tuple(tuple(row) for row in truth["grid"])
            if pred_grid == truth_grid:
                n_e += 1
            if _shape_of(pred_grid) == _shape_of(truth_grid):
                n_s += 1
        total_exact += n_e
        total_shape += n_s
        total += n_total
        if n_total:
            print(f"  {prim:>20s}: exact={n_e}/{n_total} = {n_e/n_total:.1%}, "
                  f"shape={n_s}/{n_total} = {n_s/n_total:.1%}, "
                  f"evolved={evo is not None and evo.program is not None}")
    if total:
        print()
        print(f"  TOTAL exact-match: {total_exact} / {total} = "
              f"{total_exact/total:.2%}")
        print(f"  TOTAL shape-match: {total_shape} / {total} = "
              f"{total_shape/total:.2%}")
        print(f"  (evolved L1 used on {n_evolved_used} / {total} = "
              f"{n_evolved_used/total:.1%} of test rows; "
              f"{n_fallback} / {total} = {n_fallback/total:.1%} had no "
              f"evolved program)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
