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

    def __init__(self, lam_mdl: float = 1.05):
        self.lam_mdl = lam_mdl
        self.evaluations = 0  # candidate-evaluations consumed

    def evaluate(self, prog: Program, task: Task) -> Fitness:
        self.evaluations += 1
        solved = 0
        cell_acc_sum = 0.0
        n = len(task.train)
        for inp, want in task.train:
            got = run_safe(prog, inp)
            if got == want:
                solved += 1
                cell_acc_sum += 1.0
            elif got is not None:
                # Dense gradient: cell accuracy over the overlapping region,
                # scaled by shape similarity so wrong-shape outputs earn
                # strictly less than same-shape ones. Still pure outcome
                # reward — computed only from the grids.
                gh, gw = len(got), len(got[0])
                wh, ww = len(want), len(want[0])
                if (gh, gw) == (wh, ww):
                    hit = sum(
                        g == w
                        for rg, rw in zip(got, want)
                        for g, w in zip(rg, rw)
                    )
                    cell_acc_sum += hit / (wh * ww)
                else:
                    oh, ow = min(gh, wh), min(gw, ww)
                    hit = sum(
                        g == w
                        for rg, rw in zip(got[:oh], want[:oh])
                        for g, w in zip(rg[:ow], rw[:ow])
                    )
                    shape_sim = (oh * ow) / (max(gh, wh) * max(gw, ww))
                    acc = hit / (wh * ww)
                    cell_acc_sum += 0.5 * shape_sim * (0.2 + 0.8 * acc)
            # crash: contributes 0
        solved_frac = solved / n
        tiebreak = (cell_acc_sum / n) * (self.lam_mdl ** (-len(prog)))
        return Fitness(
            solved_frac=solved_frac,
            tiebreak=tiebreak,
            solved_all=(solved == n),
            length=len(prog),
        )

    def test_exact(self, prog: Program, task: Task) -> bool:
        """Held-out check: does the program solve the task's test pair(s)?
        Not part of the reward — used only for reporting."""
        return all(run_safe(prog, i) == o for i, o in task.test)
