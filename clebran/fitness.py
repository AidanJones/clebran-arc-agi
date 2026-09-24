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
    # Novelty-search mode (roadmap #4 / discovery-bottleneck menu):
    # when mode == "novelty", `key` returns (novelty_score, novelty_tiebreak)
    # instead of (solved_frac, tiebreak). accuracy fields are still
    # populated so test-exact / library / reporting machinery is unaffected.
    novelty_score: float = 0.0
    novelty_tiebreak: float = 0.0
    mode: str = "accuracy"

    @property
    def key(self) -> tuple:
        if self.mode == "novelty":
            return (self.novelty_score, self.novelty_tiebreak)
        return (self.solved_frac, self.tiebreak)


class Evaluator:
    """Evaluates candidates and meters candidate-evaluations (the compute
    unit that must be matched across baseline arms, §7)."""

    def __init__(self, lam_mdl: float = 1.05, abstractions: dict | None = None,
                 fitness_mode: str = "accuracy"):
        self.lam_mdl = lam_mdl
        self.evaluations = 0  # candidate-evaluations consumed (the compute unit)
        # shared per-lineage abstraction table (set by the owning Lineage);
        # execution resolves ("abstr", name) heads through it. An abstraction
        # call is one statement, so len(prog) already gives it MDL cost 1 —
        # the compression reward for reusing a discovered subroutine.
        self.abstractions: dict = abstractions if abstractions is not None else {}
        # Fitness mode: "accuracy" (default — pure-outcome + parsimony) or
        # "novelty" (roadmap #4, discovery-bottleneck menu — behavioral
        # diversity instead of task accuracy).
        self.fitness_mode = fitness_mode
        # Fitness cache keyed on (program, task). Transparent: every evaluate
        # still counts as a candidate-evaluation (budget/compute-matching are
        # byte-identical to no-cache), it only skips re-running the interpreter
        # on a repeat — ~27% of evals are duplicates (elites, sweep near-misses,
        # re-derived children). Keyed per-Evaluator so lineage-local abstraction
        # names never collide.
        self._cache: dict = {}
        self._cache_cap = 300_000
        # Per-task archive of programs that pass ALL test pairs (test-exact
        # solvers). Built "for free" — when a candidate program passes all
        # train pairs, we immediately check test pairs in the same interpreter
        # call (no extra candidate-evaluation budget consumed). Used by the
        # novelty-search arm (roadmap #4) where `pop.solution` may be the most
        # novel program rather than the most accurate: counting test-exact
        # solvers at the population level (rather than via the elite) requires
        # this archive.
        self._test_exact_progs: dict[str, set[tuple]] = {}

    def evaluate_for_mode(self, prog: Program, task: Task) -> Fitness:
        """Dispatch to accuracy or novelty scoring based on the
        evaluator's fitness_mode. The lineage calls this single entry
        point so a single code path works for both objectives."""
        if self.fitness_mode == "novelty":
            return self.evaluate_novelty(prog, task)
        return self.evaluate(prog, task)

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
        # Free test-exact check: not counted toward budget; only fires when
        # all train pairs already pass. Records in the per-task archive so
        # the novelty-search arm (roadmap #4) can count test-exact solvers
        # at the population level rather than only via the elite.
        self.record_test_exact_if_solved(prog, task, fit.solved_all)
        return fit

    # ---------- novelty search (roadmap #4, discovery-bottleneck menu) ----------
    # A per-task archive of outputs from previously evaluated programs.
    # The novelty score for a candidate is mean (over train inputs) of
    # the minimum Hamming distance from the candidate's output to any
    # archived output on the same input. This rewards programs whose
    # behavioral signature differs from what we've already seen on the task.
    def _novelty_init(self) -> None:
        if not hasattr(self, "_output_archive"):
            self._output_archive: dict[str, list[tuple]] = {}
        if not hasattr(self, "_novelty_cap"):
            self._novelty_cap = 5000  # FIFO cap per task

    def _hamming_outputs(self, a, b) -> float:
        """Hamming distance between two ARC grid outputs, normalised by
        the larger of the two areas. None on either side -> max (1.0).
        Shapes differ -> distance penalised by overlap."""
        if a is None or b is None:
            return 1.0
        ah, aw = len(a), len(a[0])
        bh, bw = len(b), len(b[0])
        if ah == 0 or aw == 0 or bh == 0 or bw == 0:
            return 1.0
        oh, ow = min(ah, bh), min(aw, bw)
        # count matching cells in overlap
        match = 0
        for r in range(oh):
            for c in range(ow):
                if a[r][c] == b[r][c]:
                    match += 1
        # area of the larger of the two grids
        area = max(ah * aw, bh * bw)
        # dissimilarity in overlap (0 if identical, 1 if no match)
        dissim_overlap = 1.0 - match / (oh * ow)
        # shape mismatch penalty (0 if same shape, 1 if no overlap)
        if (ah, aw) == (bh, bw):
            shape_pen = 0.0
        else:
            shape_pen = 1.0 - (oh * ow) / area
        return 0.7 * dissim_overlap + 0.3 * shape_pen

    def evaluate_novelty(self, prog: Program, task: Task) -> Fitness:
        """Score a candidate by behavioral novelty (mean nearest-neighbor
        Hamming distance on the task's train inputs) instead of accuracy.
        Returns a Fitness with mode="novelty" so the lineage ranks by
        the novelty tuple; accuracy fields are still populated so
        `test_exact` reporting works unchanged at the end of the run."""
        self._novelty_init()
        self.evaluations += 1
        # Run the program on all train inputs.
        outputs: list = []
        for inp, _ in task.train:
            outputs.append(run_safe(prog, inp, self.abstractions))

        # Mean nearest-neighbor Hamming distance over the archive.
        archive = self._output_archive.setdefault(task.task_id, [])
        if not archive:
            # Cold start: full novelty (we're the first on this task).
            novelty = 1.0
        else:
            per_pair: list[float] = []
            for i, got in enumerate(outputs):
                # nearest-neighbor distance to archive on input i
                best = 1.0
                for arch_out in archive:
                    arch_got = arch_out[i]
                    d = self._hamming_outputs(got, arch_got)
                    if d < best:
                        best = d
                per_pair.append(best)
            novelty = sum(per_pair) / len(per_pair) if per_pair else 1.0

        # Append current outputs to the archive (FIFO).
        archive.append(tuple(outputs))
        if len(archive) > self._novelty_cap:
            archive.pop(0)

        # Accuracy fields still populated (for reporting and library mining).
        n = len(task.train)
        solved = 0
        for got, (_, want) in zip(outputs, task.train):
            if got == want:
                solved += 1
        solved_frac = solved / n

        fit = Fitness(
            solved_frac=solved_frac,
            tiebreak=0.0,  # unused in novelty mode
            solved_all=(solved == n),
            length=len(prog),
            novelty_score=novelty,
            novelty_tiebreak=self.lam_mdl ** (-len(prog)),
            mode="novelty",
        )
        # Free test-exact check (see evaluate()).
        self.record_test_exact_if_solved(prog, task, fit.solved_all)
        return fit

    def novelty_archive_size(self, task: Task) -> int:
        """How many programs are archived for this task (used by the
        summary line for the novelty arm)."""
        self._novelty_init()
        return len(self._output_archive.get(task.task_id, []))

    def test_exact(self, prog: Program, task: Task) -> bool:
        """Held-out check: does the program solve the task's test pair(s)?
        Not part of the reward — used only for reporting."""
        return all(run_safe(prog, i, self.abstractions) == o for i, o in task.test)

    def record_test_exact_if_solved(self, prog: Program, task: Task, solved_all: bool) -> bool:
        """If the program solved all train pairs, immediately check test
        pairs (one extra interpreter run, not counted toward budget) and
        record the result in the per-task archive. Returns True iff the
        program passes all test pairs (i.e. is test-exact)."""
        if not solved_all:
            return False
        prog_key = tuple(prog.statements)
        archive = self._test_exact_progs.setdefault(task.task_id, set())
        if prog_key in archive:
            # already known test-exact (cached)
            return True
        is_te = self.test_exact(prog, task)
        if is_te:
            archive.add(prog_key)
        return is_te

    def test_exact_tasks(self) -> set[str]:
        """Task ids for which at least one one test-exact solver has been
        evaluated. Used by the novelty-search arm's summary."""
        return {tid for tid, progs in self._test_exact_progs.items() if progs}

    def test_exact_count(self, task: Task) -> int:
        return len(self._test_exact_progs.get(task.task_id, set()))
