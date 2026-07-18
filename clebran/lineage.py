"""One evolving population per (lineage × task), plus the lineage's private
fragment library (§5.2 "private library", the unit of communication in §5.3).

A Lineage owns:
  - a GenomeOps (its primitive pool + rng — divergence levers, §6)
  - one Population per task, persisted across epochs
  - a library of scored fragments extracted from its best programs

Evolution is generational with elitism + tournament selection. Every
candidate evaluation goes through the shared Evaluator so compute is
metered for the matched-budget audit (§8.1 stage 3).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from .data.loader import Task
from .dsl.program import Program
from .fitness import Evaluator, Fitness
from .genome import GenomeOps, Fragment


@dataclass
class Individual:
    prog: Program
    fit: Fitness
    from_fragment: bool = False  # contains channel-received material


@dataclass
class LibraryEntry:
    frag: Fragment
    score: float          # fitness of the source program when extracted
    uses: int = 0         # times spliced into an accepted offspring
    received: bool = False  # arrived via the channel (vs home-grown)


@dataclass
class Population:
    task_id: str
    individuals: list[Individual] = field(default_factory=list)
    solved: bool = False
    solution: Individual | None = None


class Lineage:
    def __init__(
        self,
        lineage_id: str,
        pool: list[str],
        tasks: dict[str, Task],
        seed: int,
        pop_size: int = 100,
        tournament_k: int = 3,
        elite: int = 5,
        p_crossover: float = 0.3,
        p_fragment: float = 0.15,
        max_library: int = 50,
        lam_mdl: float = 1.05,
        evaluator: Evaluator | None = None,
    ):
        self.lineage_id = lineage_id
        self.rng = random.Random(seed)
        self.ops = GenomeOps(pool, self.rng)
        self.tasks = tasks
        self.pop_size = pop_size
        self.tournament_k = tournament_k
        self.elite = elite
        self.p_crossover = p_crossover
        self.p_fragment = p_fragment
        self.max_library = max_library
        self.evaluator = evaluator or Evaluator(lam_mdl=lam_mdl)
        self.library: list[LibraryEntry] = []
        self.pops: dict[str, Population] = {
            tid: Population(task_id=tid) for tid in tasks
        }

    # ---------- init ----------

    def seed_population(self, tid: str) -> None:
        pop = self.pops[tid]
        task = self.tasks[tid]
        while len(pop.individuals) < self.pop_size:
            prog = self.ops.random_program()
            if prog is None:
                continue
            fit = self.evaluator.evaluate(prog, task)
            pop.individuals.append(Individual(prog, fit))
        self._sort(pop)

    # ---------- one generation on one task ----------

    def step_generation(self, tid: str) -> None:
        pop = self.pops[tid]
        if pop.solved:
            return
        if not pop.individuals:
            self.seed_population(tid)
        task = self.tasks[tid]
        inds = pop.individuals
        next_gen: list[Individual] = inds[: self.elite]
        n_immigrants = max(1, self.pop_size // 10)
        while len(next_gen) < self.pop_size:
            if len(next_gen) >= self.pop_size - n_immigrants:
                # random immigrants: keep exploration alive when the
                # population has no fitness gradient to follow
                child, used_frag = self.ops.random_program(), False
            else:
                child, used_frag = self._make_child(inds)
            if child is None:
                continue
            fit = self.evaluator.evaluate(child, task)
            next_gen.append(Individual(child, fit, from_fragment=used_frag))
        pop.individuals = next_gen
        self._sort(pop)
        best = pop.individuals[0]
        if best.fit.solved_all:
            pop.solved = True
            pop.solution = best
            self._absorb_solution(best)

    def _make_child(self, inds: list[Individual]) -> tuple[Program | None, bool]:
        r = self.rng.random()
        used_frag = False
        if r < self.p_fragment and self.library:
            entry = self._pick_fragment()
            parent = self._tournament(inds)
            child = self.ops.inject_fragment(parent.prog, entry.frag)
            if child is not None:
                entry.uses += 1
                used_frag = entry.received or parent.from_fragment
            return child, used_frag
        if r < self.p_fragment + self.p_crossover and len(inds) >= 2:
            a, b = self._tournament(inds), self._tournament(inds)
            child = self.ops.crossover(a.prog, b.prog)
            return child, a.from_fragment or b.from_fragment
        parent = self._tournament(inds)
        child = self.ops.mutate(parent.prog)
        return child, parent.from_fragment

    def _tournament(self, inds: list[Individual]) -> Individual:
        pick = max(
            self.rng.sample(inds, min(self.tournament_k, len(inds))),
            key=lambda i: i.fit.key,
        )
        return pick

    def _sort(self, pop: Population) -> None:
        pop.individuals.sort(key=lambda i: i.fit.key, reverse=True)

    # ---------- library ----------

    def _absorb_solution(self, ind: Individual) -> None:
        """Extract fragments from a solving program into the private library."""
        for _ in range(3):
            frag = self.ops.extract_fragment(ind.prog, max_size=4)
            if frag:
                self.add_fragment(frag, score=1.0, received=False)

    def harvest_fragments(self, max_size: int) -> None:
        """Absorb fragments from current high-scoring programs (not only
        full solutions) so there is something to gossip early on: any task
        best with solved_frac ≥ 0.5 contributes."""
        for pop in self.pops.values():
            best = pop.solution or (
                pop.individuals[0] if pop.individuals else None
            )
            if best is None or best.fit.solved_frac < 0.5:
                continue
            frag = self.ops.extract_fragment(best.prog, max_size=max_size)
            if frag:
                self.add_fragment(
                    frag, score=best.fit.solved_frac, received=False
                )

    def apply_signal(self, weights: dict[str, float]) -> None:
        """Signal payload (§5.3): bias mutation's primitive distribution
        toward what other lineages report is paying off. Blend keeps 1.0
        as the floor so local primitives never vanish."""
        scale = max(weights.values()) if weights else 1.0
        self.ops.fn_weights = {
            p: 1.0 + 2.0 * weights.get(p, 0.0) / scale for p in self.ops.pool
        }

    def add_fragment(self, frag: Fragment, score: float, received: bool) -> None:
        key = repr(frag)
        for e in self.library:
            if repr(e.frag) == key:
                e.score = max(e.score, score)
                return
        self.library.append(LibraryEntry(frag=frag, score=score, received=received))
        if len(self.library) > self.max_library:
            self.library.sort(key=lambda e: (e.uses, e.score), reverse=True)
            del self.library[self.max_library :]

    def _pick_fragment(self) -> LibraryEntry:
        weights = [max(e.score, 0.01) + 0.1 * e.uses for e in self.library]
        return self.rng.choices(self.library, weights=weights, k=1)[0]

    # ---------- reporting ----------

    def solved_tasks(self) -> set[str]:
        return {tid for tid, p in self.pops.items() if p.solved}

    def primitive_usage(self) -> dict[str, int]:
        """Primitive counts over current best programs (for H1 divergence)."""
        counts: dict[str, int] = {}
        for pop in self.pops.values():
            best = pop.solution or (
                pop.individuals[0] if pop.individuals else None
            )
            if best is None:
                continue
            for p in best.prog.primitives_used():
                counts[p] = counts.get(p, 0) + 1
        return counts
