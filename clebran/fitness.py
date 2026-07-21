"""Reward (§5.2): pure outcome reward + parsimony. No supervision.

Fitness is a lexicographic tuple:
  primary   solved_frac — fraction of demonstration pairs solved exactly
            (rewards transfer across pairs, the L2T point)
  secondary tiebreak — mean per-cell accuracy on unsolved pairs (dense
            gradient), scaled by NEO's adaptive-length factor
            λ_MDL^(-len): among equal solvers the shorter wins by a factor
            growing with the length gap.

Python tuple comparison gives the lexicographic order for free.
"""
from __future__ import annotations

from dataclasses import dataclass

from .data.loader import Task
from .dsl.interpreter import run_safe
from .dsl.program import Program


@dataclass(frozen=True)
class Fitness:
    solved_frac: float
    tiebreak: float
    solved_all: bool
    length: int

    @property
    def key(self) -> tuple:
        return (self.solved_frac, self.tiebreak)


class Evaluator:
    """Evaluates candidates and meters candidate-evaluations (the compute
    unit that must be matched across baseline arms, §7)."""

    def __init__(self, lam_mdl: float = 1.05, abstractions: dict | None = None):
        self.lam_mdl = lam_mdl
        self.evaluations = 0  # candidate-evaluations consumed (the compute unit)
        # shared per-lineage abstraction table (set by the owning Lineage);
        # execution resolves ("abstr", name) heads through it. An abstraction
        # call is one statement, so len(prog) already gives it MDL cost 1 —
        # the compression reward for reusing a discovered subroutine.
        self.abstractions: dict = abstractions if abstractions is not None else {}
        # Fitness cache keyed on (program, task). Transparent: every evaluate
        # still counts as a candidate-evaluation (budget/compute-matching are
        # byte-identical to no-cache), it only skips re-running the interpreter
        # on a repeat — ~27% of evals are duplicates (elites, sweep near-misses,
        # re-derived children). Keyed per-Evaluator so lineage-local abstraction
        # names never collide.
        self._cache: dict = {}
        self._cache_cap = 300_000

    def evaluate(self, prog: Program, task: Task) -> Fitness:
        self.evaluations += 1
        # Cache only deep programs: for short ones (stage-1, len ≤ 3) the key
        # construction costs as much as re-running the cheap interpreter, so
        # caching there is a net loss (measured). Frontier programs (len 8-12)
        # are expensive to run, so the ~27% duplicate rate pays off.
        key = None
        if len(prog) >= 4:
            key = (tuple(prog.statements), task.task_id)
            hit = self._cache.get(key)
            if hit is not None:
                return hit
        solved = 0
        cell_acc_sum = 0.0
        n = len(task.train)
        for inp, want in task.train:
            got = run_safe(prog, inp, self.abstractions)
            if got == want:
                solved += 1
                cell_acc_sum += 1.0
            elif got is not None:
                # Dense gradient, still pure outcome reward. Background and
                # foreground cells are scored separately and averaged: on
                # mostly-background targets a blank canvas otherwise gets
                # ~half the cells "right" and deceptively dominates every
                # content-bearing program (observed: canvas(ZERO, 3x3)
                # out-ranking all crop stubs on block-selection tasks).
                gh, gw = len(got), len(got[0])
                wh, ww = len(want), len(want[0])
                oh, ow = min(gh, wh), min(gw, ww)
                counts: dict[int, int] = {}
                for rw_ in want:
                    for w in rw_:
                        counts[w] = counts.get(w, 0) + 1
                bg = max(counts, key=counts.get)
                bg_hit = bg_tot = fg_hit = fg_tot = 0
                for r in range(oh):
                    rg, rw_ = got[r], want[r]
                    for c in range(ow):
                        if rw_[c] == bg:
                            bg_tot += 1
                            bg_hit += rg[c] == rw_[c]
                        else:
                            fg_tot += 1
                            fg_hit += rg[c] == rw_[c]
                # cells of `want` outside the overlap are misses
                for r in range(oh, wh):
                    for c in range(ww):
                        if want[r][c] == bg:
                            bg_tot += 1
                        else:
                            fg_tot += 1
                for r in range(oh):
                    for c in range(ow, ww):
                        if want[r][c] == bg:
                            bg_tot += 1
                        else:
                            fg_tot += 1
                parts = []
                if bg_tot:
                    parts.append(bg_hit / bg_tot)
                if fg_tot:
                    parts.append(fg_hit / fg_tot)
                acc = sum(parts) / len(parts) if parts else 0.0
                if (gh, gw) == (wh, ww):
                    cell_acc_sum += acc
                else:
                    shape_sim = (oh * ow) / (max(gh, wh) * max(gw, ww))
                    cell_acc_sum += 0.5 * shape_sim * (0.2 + 0.8 * acc)
            # crash: contributes 0
        solved_frac = solved / n
        tiebreak = (cell_acc_sum / n) * (self.lam_mdl ** (-len(prog)))
        fit = Fitness(
            solved_frac=solved_frac,
            tiebreak=tiebreak,
            solved_all=(solved == n),
            length=len(prog),
        )
        if key is not None and len(self._cache) < self._cache_cap:
            self._cache[key] = fit
        return fit

    def test_exact(self, prog: Program, task: Task) -> bool:
        """Held-out check: does the program solve the task's test pair(s)?
        Not part of the reward — used only for reporting."""
        return all(run_safe(prog, i, self.abstractions) == o for i, o in task.test)
