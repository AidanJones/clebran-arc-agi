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
from dataclasses import dataclass, field, replace

from .data.loader import Task
from .dsl.program import Program, Statement
from .dsl.registry import CONSTANTS, PRIMITIVES
from .fitness import Evaluator, Fitness
from .genome import GenomeOps, Fragment
from .dsl.abstraction import mine_compressing


# ---- helpers -------------------------------------------------------------

# Build a reverse map: int value -> constant name. Used by
# ``_classify_arg_for_seed`` to identify whether an arg value is
# a known arc-dsl constant.
_CONST_BY_VALUE: dict = {}
for _name, (_val, _t) in CONSTANTS.items():
    if isinstance(_val, int) and not isinstance(_val, bool):
        _CONST_BY_VALUE.setdefault(_val, []).append(_name)


def _classify_arg_for_seed(value, input_grid) -> tuple:
    """Classify an evaluated argument value into an IR arg tuple
    for a planner-seeded 1-statement program.

    ``input_grid`` is the task's input grid (the IR's `I`
    reference). Returns the appropriate ``(kind, payload)`` tuple:

      1. The input grid -> ``("in", None)``
      2. A constant int value in arc-dsl -> ``("const", name)``
      3. A primitive function (callable from PRIMITIVES) -> ``("prim", name)``
      4. Anything else (a tuple / grid / frozenset / etc.) -> ``("lit", value)``
    """
    if value is input_grid:
        return ("in", None)
    if isinstance(value, int) and not isinstance(value, bool):
        names = _CONST_BY_VALUE.get(value)
        if names:
            return ("const", names[0])
    if callable(value):
        for name, sig in PRIMITIVES.items():
            if sig.fn is value:
                return ("prim", name)
    return ("lit", value)


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
    # which phase solved it: "phase1" = deterministic initial seeding
    # (identical across arms — channel and library are empty there), or
    # "evolution" = the evolutionary loop, where fragments/signals can act.
    # The H2/H3 treatment effect can only live in evolution-phase solves.
    solved_phase: str | None = None
    stall: int = 0
    best_key: tuple = (-1.0, -1.0)
    restarts: int = 0
    # adaptive operator selection: exponential-recency credit per operator
    op_n: dict = field(default_factory=lambda: {"mutate": 2.0, "crossover": 2.0, "fragment": 2.0})
    op_w: dict = field(default_factory=lambda: {"mutate": 1.0, "crossover": 1.0, "fragment": 1.0})
    # cumulative counters for the crowding metric: how often each operator
    # was chosen and how often its child at least matched the parent. The
    # H3 hypothesis is that unconstrained sharing raises the fragment op's
    # *share* (more material to splice) while lowering its *success* (it is
    # noise), displacing productive mutation.
    op_selected: dict = field(default_factory=lambda: {"mutate": 0, "crossover": 0, "fragment": 0})
    op_wins: dict = field(default_factory=lambda: {"mutate": 0, "crossover": 0, "fragment": 0})
    # hall of fame: best individual per skeleton signature, survives
    # restarts so full restarts explore fresh space without destroying
    # polishable partial-credit stubs
    hof: dict = field(default_factory=dict)
    swept: set = field(default_factory=set)  # programs already const-swept

    def hof_update(self, ind) -> None:
        sig = tuple(st.fn for st in ind.prog.statements)
        cur = self.hof.get(sig)
        if cur is None or ind.fit.key > cur.fit.key:
            self.hof[sig] = ind
        if len(self.hof) > 10:
            drop = min(self.hof, key=lambda s: self.hof[s].fit.key)
            del self.hof[drop]

    def op_weight(self, op: str) -> float:
        return max(0.05, self.op_w[op] / self.op_n[op])

    def op_credit(self, op: str, win: bool, decay: float = 0.99) -> None:
        self.op_n[op] = self.op_n[op] * decay + 1.0
        self.op_w[op] = self.op_w[op] * decay + (1.0 if win else 0.0)
        self.op_selected[op] += 1
        self.op_wins[op] += 1 if win else 0


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
        fitness_mode: str = "accuracy",
    ):
        self.lineage_id = lineage_id
        self.rng = random.Random(seed)  # lineage-level (library picks)
        # the lineage's recovered vocabulary: one dict shared (by reference)
        # with every per-task GenomeOps and the evaluator, so installing an
        # abstraction makes it immediately usable in search and execution.
        self.abstractions: dict = {}
        self.abstraction_meta: dict[str, dict] = {}  # name -> {received, score, uses}
        self._abstr_counter = 0
        # auxiliary tasks received over a curriculum channel (roadmap 7b):
        # the lineage also evolves on these, and solving them enriches its
        # library, but they never count toward the real solve rate.
        self.aux_task_ids: set[str] = set()
        # per received curriculum task: {source, score}. score = shallowness
        # (a fundamental prerequisite scores higher). Used by the order-aware
        # learner to gate a deeper task until its prerequisites are solved.
        self.aux_meta: dict[str, dict] = {}
        self.curriculum_rng = random.Random(f"{seed}:curriculum")
        # per-task rng substreams: a task's search trajectory is identical
        # whether it runs in isolation or interleaved with other tasks —
        # isolation probes then predict full-run behavior exactly
        self.rngs = {tid: random.Random(f"{seed}:{tid}") for tid in tasks}
        self.ops_by_task = {
            tid: GenomeOps(pool, self.rngs[tid], abstractions=self.abstractions)
            for tid in tasks
        }
        self.ops = GenomeOps(pool, self.rng, abstractions=self.abstractions)
        # own copy: add_task (received curriculum tasks) mutates this, and the
        # same dict is shared across lineages by the orchestrator
        self.tasks = dict(tasks)
        self.pop_size = pop_size
        self.tournament_k = tournament_k
        self.elite = elite
        self.p_crossover = p_crossover
        self.p_fragment = p_fragment
        self.max_library = max_library
        self.evaluator = evaluator or Evaluator(lam_mdl=lam_mdl, fitness_mode=fitness_mode)
        self.evaluator.abstractions = self.abstractions
        self.library: list[LibraryEntry] = []
        self.pops: dict[str, Population] = {
            tid: Population(task_id=tid) for tid in tasks
        }

    # ---------- init ----------

    def seed_population(self, tid: str, keep: int = 0) -> None:
        """First seeding: exhaustive depth-1 sweep (typed constants), keep
        the best half-population. Reseeding (restarts): ramped init — half
        systematic single statements, half random."""
        pop = self.pops[tid]
        task = self.tasks[tid]
        ops = self.ops_by_task[tid]
        first_time = not pop.individuals and keep == 0
        pop.individuals = pop.individuals[:keep]
        if first_time:
            scored = []
            for prog in ops.enumerate_depth1():
                fit = self.evaluator.evaluate_for_mode(prog, task)
                scored.append(Individual(prog, fit))
                if fit.solved_all:
                    break
            if not (scored and scored[-1].fit.solved_all):
                for prog in ops.enumerate_depth2():
                    fit = self.evaluator.evaluate_for_mode(prog, task)
                    scored.append(Individual(prog, fit))
                    if fit.solved_all:
                        break
            # niche by skeleton signature: keep only the best program per
            # function-sequence so one lucky family can't crowd out the
            # right skeleton with unlucky constants
            by_sig: dict[tuple, Individual] = {}
            for ind in scored:
                sig = tuple(st.fn for st in ind.prog.statements)
                cur = by_sig.get(sig)
                if cur is None or ind.fit.key > cur.fit.key:
                    by_sig[sig] = ind
            nichebest = sorted(
                by_sig.values(), key=lambda i: i.fit.key, reverse=True
            )
            pop.individuals = nichebest[: self.pop_size // 2]
            while len(pop.individuals) < self.pop_size:
                prog = ops.random_program()
                if prog is None:
                    continue
                pop.individuals.append(
                    Individual(prog, self.evaluator.evaluate_for_mode(prog, task))
                )
            self._sort(pop)
            if not pop.individuals[0].fit.solved_all:
                # phase-1 polish, once per task: sweep the best few short
                # stubs to completion so the depth-<=2 bucket is closed
                # systematically rather than left to stall-timing luck
                shorts: list[tuple[tuple, Individual]] = []
                seen: set[tuple] = set()
                for ind in list(pop.individuals):
                    sig = tuple(st.fn for st in ind.prog.statements)
                    if len(ind.prog) > 2 or sig in seen:
                        continue
                    seen.add(sig)
                    shorts.append((sig, ind))
                targets = [ind for _, ind in shorts[:6]]
                # also sweep compositions built around the top families:
                # the right skeleton often contains the top-ranked primitive
                # but scores no better than it until its constants are swept
                # (e.g. replace>downscale vs plain downscale)
                top_fns = {
                    p for sig, _ in shorts[:3] for k, p in sig if k == "prim"
                }
                extra = [
                    ind for sig, ind in shorts[6:]
                    if any(k == "prim" and p in top_fns for k, p in sig)
                ]
                targets += extra[:6]
                for ind in targets:
                    self._sweep_one(pop, task, ind)
                    if pop.individuals[0].fit.solved_all:
                        break
            best = pop.individuals[0]
            if best.fit.solved_all:
                pop.solved = True
                pop.solved_phase = "phase1"
                pop.solution = best
                self._absorb_solution(best)
            return
        fns = list(ops.pool)
        self.rngs[tid].shuffle(fns)
        for fn in fns[: self.pop_size // 2 - keep]:
            prog = ops.single_statement_program(fn)
            if prog is None:
                continue
            fit = self.evaluator.evaluate_for_mode(prog, task)
            pop.individuals.append(Individual(prog, fit))
        while len(pop.individuals) < self.pop_size:
            prog = ops.random_program()
            if prog is None:
                continue
            fit = self.evaluator.evaluate_for_mode(prog, task)
            pop.individuals.append(Individual(prog, fit))
        self._sort(pop)

    def seed_with_planner(self, tid: str, max_steps: int = 20,
                          lookahead: int = 1,
                          distance: str = "hamming") -> bool:
        """Run the L2 planner on *all* of the task's demo pairs and
        add the resulting program to the population as a
        high-priority seed. Returns True if the planner produced a
        non-empty program; False otherwise (e.g. the planner
        couldn't find any improving candidate at the first step).

        The planner uses the clebran interpreter as a perfect L1
        world model (§9f in `roadmap.md`); the seeded program is
        the planner's best linear sequence of primitives. It is
        evaluated by the standard fitness function (which counts
        against the budget) and inserted at the front of the
        population so it survives the next ``_sort``.

        Parameters
        ----------
        tid : str
            The task ID to seed.
        max_steps : int, default 20
            Maximum number of planning steps (i.e. the maximum
            length of the seeded program).
        lookahead : int, default 1
            Planning depth passed to ``L2Planner``. ``1`` = greedy
            one-step (default). ``2`` = two-step lookahead.
        distance : str, default "hamming"
            Distance metric passed to ``L2Planner``. One of
            ``"hamming"``, ``"component"``, ``"color_set"``,
            ``"structural"``. The structural / component metrics
            are *object-aware* — they score primitives on structural
            match (number of disconnected disagreement regions)
            rather than cell-wise Hamming, which is the right
            metric for tasks that change a small region of the grid.
        """
        from .world_model.l2_planner import L2Planner
        task = self.tasks[tid]
        pop = self.pops[tid]
        if not task.train:
            return False
        # Build a list of (input, target) demo pairs from the task.
        demos: list[tuple] = []
        for input_grid, target_grid in task.train:
            demos.append((
                tuple(tuple(r) for r in input_grid),
                tuple(tuple(r) for r in target_grid),
            ))
        # All demos must be grid→grid (the planner only handles
        # grid→grid transitions).
        for st, tg in demos:
            if not (isinstance(st, tuple) and st and isinstance(st[0], tuple)):
                return False
            if not (isinstance(tg, tuple) and tg and isinstance(tg[0], tuple)):
                return False
        planner = L2Planner(lookahead=lookahead, distance=distance)
        result = planner.plan_to_program(demos, max_steps=max_steps)
        prog = result["program"]
        if not prog.statements:
            return False
        fit = self.evaluator.evaluate_for_mode(prog, task)
        # Insert at the front; the next _sort will keep it if it's
        # competitive.
        pop.individuals.insert(0, Individual(prog, fit))
        self._sort(pop)
        return True

    def seed_with_planner_topk(self, tid: str, k: int = 3,
                                lookahead: int = 1,
                                distance: str = "hamming") -> int:
        """Top-K variant of ``seed_with_planner``: seed the top-K
        planner candidates as K individuals in the population. The
        planner call is shared (one rollout); only the program
        evaluation differs across the K seeds, so the cost is K
        candidate-evaluations (counted against the budget) rather
        than K planner calls.

        Each seed is a single-statement program (the candidate
        primitive applied to the first demo's input). The K
        candidates are sorted by ascending mean distance, so the
        best is at the front of the population after the next
        ``_sort``.

        Returns the number of seeds actually added (0 if no valid
        candidates were found, up to ``k`` if all K were valid).
        The maximum is bounded by the population size; we cap at
        ``pop_size // 4`` to avoid swamping the random initial
        population with planner seeds.

        Parameters
        ----------
        tid : str
            The task ID to seed.
        k : int, default 3
            Number of top candidates to seed.
        lookahead, distance
            Forwarded to ``L2Planner``.
        """
        from .world_model.l2_planner import L2Planner
        task = self.tasks[tid]
        pop = self.pops[tid]
        if not task.train:
            return 0
        # Build a list of (input, target) demo pairs from the task.
        demos: list[tuple] = []
        for input_grid, target_grid in task.train:
            demos.append((
                tuple(tuple(r) for r in input_grid),
                tuple(tuple(r) for r in target_grid),
            ))
        for st, tg in demos:
            if not (isinstance(st, tuple) and st and isinstance(st[0], tuple)):
                return 0
            if not (isinstance(tg, tuple) and tg and isinstance(tg[0], tuple)):
                return 0
        # Cap at a quarter of the pop size — too many seeds would
        # crowd out the random initial population.
        max_seeds = max(1, self.pop_size // 4)
        k_eff = min(k, max_seeds)
        planner = L2Planner(lookahead=lookahead, distance=distance)
        top_k = planner.top_k_candidates(demos, k=k_eff)
        if not top_k:
            return 0
        # Build a 1-statement program for each candidate and
        # evaluate it. The first-state (from the first demo) is
        # the IR's `I` reference; subsequent positions are
        # auto-classified by _classify_arg.
        from .dsl.interpreter import _invoke, _check_size
        added = 0
        first_state = demos[0][0]
        for cand in top_k:
            name = cand["primitive"]
            args = cand["args"]
            try:
                classified = tuple(
                    _classify_arg_for_seed(a, first_state)
                    for a in args
                )
                statement = Statement(
                    fn=("prim", name), args=classified
                )
                prog = Program(statements=[statement])
                fit = self.evaluator.evaluate_for_mode(prog, task)
            except Exception:
                continue
            # Insert at the front (sorted by fitness descending,
            # so the best is at index 0).
            pop.individuals.insert(0, Individual(prog, fit))
            added += 1
        self._sort(pop)
        return added

    # ---------- one generation on one task ----------

    def step_generation(self, tid: str) -> None:
        pop = self.pops[tid]
        if pop.solved:
            return
        if not pop.individuals:
            self.seed_population(tid)
            if pop.solved:
                return
        task = self.tasks[tid]
        inds = pop.individuals
        next_gen: list[Individual] = inds[: self.elite]
        n_immigrants = max(1, self.pop_size // 10)
        while len(next_gen) < self.pop_size:
            if len(next_gen) >= self.pop_size - n_immigrants:
                # random immigrants: keep exploration alive when the
                # population has no fitness gradient to follow
                child, used_frag, op, parent_key = (
                    self.ops_by_task[tid].random_program(), False, None, None
                )
            else:
                child, used_frag, op, parent_key = self._make_child(pop, inds)
            if child is None:
                continue
            fit = self.evaluator.evaluate_for_mode(child, task)
            next_gen.append(Individual(child, fit, from_fragment=used_frag))
            if op is not None:
                pop.op_credit(op, fit.key >= parent_key)
        pop.individuals = next_gen
        self._sort(pop)
        for ind in pop.individuals[:5]:
            pop.hof_update(ind)
        best = pop.individuals[0]
        if best.fit.key > pop.best_key:
            pop.best_key = best.fit.key
            pop.stall = 0
        else:
            pop.stall += 1
            if pop.stall == 20:
                # memetic step: coordinate-descent sweep over the elite's
                # constant/literal slots before giving up on this basin
                improved = self._local_const_search(pop, task)
                if improved:
                    pop.stall = 0
                    best = pop.individuals[0]
            if pop.stall >= 40:
                # stagnation restart; alternate keeping the top-2 with a
                # full restart so a deceptive elite can't re-trap every
                # restart in its own basin
                pop.restarts += 1
                keep = 2 if pop.restarts % 2 == 1 else 0
                self.seed_population(tid, keep=keep)
                # re-inject the hall of fame: restarts explore fresh space
                # but never lose the best stub of each known skeleton
                if pop.hof:
                    pop.individuals[-len(pop.hof):] = list(pop.hof.values())
                    self._sort(pop)
                pop.stall = 0
                best = pop.individuals[0]
        if best.fit.solved_all:
            pop.solved = True
            pop.solved_phase = "evolution"
            pop.solution = best
            self._absorb_solution(best)

    def _make_child(
        self, pop: Population, inds: list[Individual]
    ) -> tuple[Program | None, bool, str, tuple]:
        """Pick an operator by adaptive credit (recent fraction of children
        at least matching their parent), floored so no operator dies out.
        Fragment splicing thus self-suppresses on tasks where library
        material is irrelevant and self-amplifies where it pays — the fair
        setting for judging the channel. Returns
        (child, carries_received_material, op, parent_fitness_key)."""
        gops = self.ops_by_task[pop.task_id]
        rng = self.rngs[pop.task_id]
        ops = ["mutate"]
        base = {"mutate": 1.0}
        if len(inds) >= 2:
            ops.append("crossover")
            base["crossover"] = self.p_crossover / 0.55
        if self.library:
            ops.append("fragment")
            base["fragment"] = self.p_fragment / 0.55
        weights = [base[o] * pop.op_weight(o) for o in ops]
        op = rng.choices(ops, weights=weights, k=1)[0]
        if op == "fragment":
            entry = self._pick_fragment()
            parent = self._tournament(inds, rng)
            child = gops.inject_fragment(parent.prog, entry.frag)
            used_frag = False
            if child is not None:
                entry.uses += 1
                used_frag = entry.received or parent.from_fragment
            return child, used_frag, op, parent.fit.key
        if op == "crossover":
            a, b = self._tournament(inds, rng), self._tournament(inds, rng)
            child = gops.crossover(a.prog, b.prog)
            return (
                child, a.from_fragment or b.from_fragment, op,
                max(a.fit.key, b.fit.key),
            )
        parent = self._tournament(inds, rng)
        child = gops.mutate(parent.prog)
        return child, parent.from_fragment, op, parent.fit.key

    def _local_const_search(self, pop: Population, task: Task) -> bool:
        """Coordinate descent on the elite's const/lit arg slots: try all
        same-type constants plus small literals, keep strict improvements.
        All evaluations are metered. Returns True if the elite improved."""

        improved_all = False
        seen_sigs: set[tuple] = set()
        targets: list[Individual] = []
        for ind in pop.individuals:
            sig = tuple(st.fn for st in ind.prog.statements)
            if sig in seen_sigs:
                continue
            seen_sigs.add(sig)
            targets.append(ind)
            if len(targets) == 5:
                break
        for ind in targets:
            if self._sweep_one(pop, task, ind):
                improved_all = True
                if pop.individuals[0].fit.solved_all:
                    break
        return improved_all

    def _sweep_one(self, pop: Population, task: Task, best: Individual) -> bool:
        key = best.prog.to_json()
        if key in pop.swept:
            return False
        pop.swept.add(key)
        prog, fit = best.prog, best.fit
        improved_any = False
        for _round in range(3):
            improved = False
            for i, st in enumerate(prog.statements):
                for k, a in enumerate(st.args):
                    if a[0] not in ("const", "lit"):
                        continue
                    value = CONSTANTS[a[1]][0] if a[0] == "const" else a[1]
                    if isinstance(value, bool):
                        cands = [("lit", not value)]
                    elif isinstance(value, int):
                        cands = [("lit", v) for v in range(10) if v != value]
                    elif isinstance(value, tuple) and len(value) == 2:
                        cands = [
                            ("lit", (x, y))
                            for x in range(10)
                            for y in range(10)
                            if (x, y) != value
                        ]
                        # short programs are needle candidates — sweep the
                        # full tuple space; sample it for longer ones
                        if len(prog) > 3 and len(cands) > 40:
                            cands = self.rngs[pop.task_id].sample(cands, 40)
                    else:
                        continue
                    for cand in cands:
                        args = list(st.args)
                        args[k] = cand
                        trial = Program(list(prog.statements))
                        trial.statements[i] = Statement(st.fn, tuple(args))
                        tfit = self.evaluator.evaluate_for_mode(trial, task)
                        if tfit.key > fit.key:
                            prog, fit = trial, tfit
                            st = trial.statements[i]
                            improved = improved_any = True
                            if tfit.solved_all:
                                break
                    if fit.solved_all:
                        break
                if fit.solved_all:
                    break
            if not improved or fit.solved_all:
                break
        if not fit.solved_all and len(prog) <= 2:
            prog, fit, hit2d = self._joint_tuple_sweep(prog, fit, task)
            improved_any = improved_any or hit2d
        if improved_any:
            try:
                idx = next(
                    i for i, x in enumerate(pop.individuals) if x is best
                )
            except StopIteration:
                idx = len(pop.individuals) - 1
            pop.individuals[idx] = Individual(
                prog, fit, from_fragment=best.from_fragment
            )
            self._sort(pop)
        return improved_any

    def _joint_tuple_sweep(
        self, prog: Program, fit: Fitness, task: Task
    ) -> tuple[Program, Fitness, bool]:
        """2-D sweep for two-coordinate needles (e.g. crop offset+size):
        jointly try lit tuples 0..9² in one tuple slot × tuple constants in
        another. Coordinate descent cannot cross these when neither
        coordinate improves alone; a bounded joint sweep (~2.6k evals on a
        short elite) can."""
        def _val(a):
            return CONSTANTS[a[1]][0] if a[0] == "const" else a[1]

        tup_slots, int_slots = [], []
        for i, st in enumerate(prog.statements):
            for k, a in enumerate(st.args):
                if a[0] not in ("const", "lit"):
                    continue
                v = _val(a)
                if isinstance(v, tuple):
                    tup_slots.append((i, k))
                elif isinstance(v, int) and not isinstance(v, bool):
                    int_slots.append((i, k))
        tuple_consts = [
            ("const", n) for n, (v, _) in sorted(CONSTANTS.items())
            if isinstance(v, tuple)
        ]
        tup_lits = [("lit", (x, y)) for x in range(10) for y in range(10)]
        int_lits = [("lit", v) for v in range(10)]
        pairs: list[tuple] = []
        if len(tup_slots) >= 2:
            pairs += [
                (tup_slots[0], tup_slots[1], tup_lits, tuple_consts),
                (tup_slots[1], tup_slots[0], tup_lits, tuple_consts),
            ]
        if len(int_slots) >= 2:
            # all int-slot pairs on a short program (colour pairs etc.)
            for x in range(len(int_slots)):
                for y in range(len(int_slots)):
                    if x != y:
                        pairs.append(
                            (int_slots[x], int_slots[y], int_lits, int_lits)
                        )
        improved = False
        for (ia, ka), (ib, kb), cands_a, cands_b in pairs:
            for va in cands_a:
                for vb in cands_b:
                    trial = Program(list(prog.statements))
                    sa = trial.statements[ia]
                    args = list(sa.args)
                    args[ka] = va
                    trial.statements[ia] = Statement(sa.fn, tuple(args))
                    sb = trial.statements[ib]
                    args = list(sb.args)
                    args[kb] = vb
                    trial.statements[ib] = Statement(sb.fn, tuple(args))
                    tfit = self.evaluator.evaluate_for_mode(trial, task)
                    if tfit.key > fit.key:
                        prog, fit = trial, tfit
                        improved = True
                        if fit.solved_all:
                            return prog, fit, True
        return prog, fit, improved

    def _tournament(
        self, inds: list[Individual], rng: random.Random | None = None
    ) -> Individual:
        rng = rng or self.rng
        pick = max(
            rng.sample(inds, min(self.tournament_k, len(inds))),
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
        fw = {
            p: 1.0 + 2.0 * weights.get(p, 0.0) / scale for p in self.ops.pool
        }
        self.ops.fn_weights = fw
        for gops in self.ops_by_task.values():
            gops.fn_weights = fw

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

    # ---------- scheduling ----------

    def task_weights(self) -> dict[str, float]:
        """Budget-allocation weights over unsolved tasks: proximity to a
        solution (partial credit) plus a boost while improvement is live.
        Round-robin starves near-miss tasks in the tail — most budget goes
        to deep tasks that cannot crack at this stage; this skews
        generations toward tasks the engine is actually making progress on.
        Every unsolved task keeps a floor weight so none starves entirely."""
        weights: dict[str, float] = {}
        for tid, pop in self.pops.items():
            if pop.solved:
                continue
            solved_frac, tiebreak = (
                pop.best_key if pop.best_key > (0.0, 0.0) else (0.0, 0.0)
            )
            w = 0.15 + solved_frac + min(tiebreak, 1.0)
            if pop.stall < 10:
                w *= 1.5  # improvement is live
            weights[tid] = w
        return weights

    def solved_tasks(self) -> set[str]:
        # real (non-auxiliary) solved tasks — the solve-rate metric
        return {
            tid for tid, p in self.pops.items()
            if p.solved and tid not in self.aux_task_ids
        }

    def add_task(self, task, auxiliary: bool = True, source: str | None = None,
                 score: float = 0.0) -> bool:
        """Register a task dynamically (a received curriculum task). Creates
        its population, per-task ops and rng. Returns False if already known."""
        if task.task_id in self.pops:
            return False
        self.tasks[task.task_id] = task
        self.rngs[task.task_id] = random.Random(f"{self.lineage_id}:{task.task_id}")
        self.ops_by_task[task.task_id] = GenomeOps(
            self.ops.pool, self.rngs[task.task_id], abstractions=self.abstractions
        )
        self.pops[task.task_id] = Population(task_id=task.task_id)
        if auxiliary:
            self.aux_task_ids.add(task.task_id)
            self.aux_meta[task.task_id] = {"source": source, "score": score}
        return True

    def is_aux_gated(self, tid: str) -> bool:
        """Order-aware learner (roadmap 7a): a received task is gated — no
        search budget yet — while a *more fundamental* prerequisite from the
        same curriculum (same source, higher shallowness score) is still
        unsolved. So the lineage masters building blocks before the
        compositions that need them, and each solved prerequisite enriches the
        library the next step draws on."""
        meta = self.aux_meta.get(tid)
        if meta is None:
            return False
        return any(
            m["source"] == meta["source"]
            and m["score"] > meta["score"]
            and not self.pops[other].solved
            for other, m in self.aux_meta.items()
        )

    def schedulable_tasks(self) -> list[str]:
        """Unsolved tasks eligible for search: all real tasks plus only the
        *ungated* auxiliary tasks (the current prerequisite frontier)."""
        return [
            t for t in self.tasks
            if not self.pops[t].solved and not self.is_aux_gated(t)
        ]

    def solved_programs(self, real_only: bool = True) -> list:
        """(task, program) for solved tasks — the transforms this lineage has
        learned, i.e. what it can generate curriculum variants from."""
        out = []
        for tid, p in self.pops.items():
            if not (p.solved and p.solution is not None):
                continue
            if real_only and tid in self.aux_task_ids:
                continue
            out.append((self.tasks[tid], p.solution.prog))
        return out

    # ---------- recovered vocabulary (roadmap item 3) ----------

    def install_abstraction(
        self, abstr, received: bool = False, score: float = 1.0
    ) -> str | None:
        """Register a mined/received abstraction under a stable lineage-local
        name (dedup by structure). Shared table → immediately usable in
        search and execution. Returns the assigned name, or None if it was
        already known (its score is bumped)."""
        for name, existing in self.abstractions.items():
            if existing.key == abstr.key:
                meta = self.abstraction_meta[name]
                meta["score"] = max(meta["score"], score)
                return None
        name = f"{self.lineage_id}_a{self._abstr_counter}"
        self._abstr_counter += 1
        self.abstractions[name] = replace(abstr, name=name)
        self.abstraction_meta[name] = {
            "received": received, "score": score, "uses": 0,
        }
        return name

    def mine_own_abstractions(
        self, max_new: int = 8, min_size: int = 2, max_size: int = 4,
    ) -> int:
        """Mine subroutines from this lineage's own solved programs with the
        Stitch-style compression miner and install the top `max_new`
        (best-compressing first, constant-antiunified). The channel offers
        these; its constraint does the final filtering. Returns count added."""
        solved = [
            p.solution.prog
            for p in self.pops.values()
            if p.solved and p.solution is not None
        ]
        if not solved:
            return 0
        mined = mine_compressing(
            solved, min_size=min_size, max_size=max_size, max_results=max_new,
            min_occurrences=1, min_utility=-1e9,  # offer all; constraint filters
        )
        return sum(
            1 for a in mined
            if self.install_abstraction(a, received=False) is not None
        )

    def home_abstractions(self) -> list[tuple]:
        """(Abstraction, score) for home-grown (non-received) entries — what
        this lineage offers to the channel."""
        return [
            (self.abstractions[n], m["score"])
            for n, m in self.abstraction_meta.items()
            if not m["received"]
        ]

    def received_abstraction_names(self) -> set[str]:
        return {n for n, m in self.abstraction_meta.items() if m["received"]}

    def solution_uses_received_abstraction(self, prog) -> bool:
        return bool(prog.abstractions_used() & self.received_abstraction_names())

    def op_mix(self) -> dict[str, float]:
        """Aggregate operator usage across this lineage's populations, for
        the H3 crowding metric. fragment_share = fraction of offspring made
        by fragment splicing; fragment_success = fraction of those at least
        matching their parent (mutate/crossover_success given for contrast)."""
        sel = {k: 0 for k in ("mutate", "crossover", "fragment")}
        win = dict(sel)
        for p in self.pops.values():
            for op in sel:
                sel[op] += p.op_selected[op]
                win[op] += p.op_wins[op]
        total = sum(sel.values())
        out = {"fragment_share": (sel["fragment"] / total) if total else 0.0}
        for op in sel:
            out[f"{op}_success"] = (win[op] / sel[op]) if sel[op] else 0.0
        return out

    def solved_by_phase(self) -> dict[str, set[str]]:
        """{"phase1": {...}, "evolution": {...}} — the split that isolates
        where communication could have acted (§ roadmap "sharper measure")."""
        out = {"phase1": set(), "evolution": set()}
        for tid, p in self.pops.items():
            if p.solved and p.solved_phase in out:
                out[p.solved_phase].add(tid)
        return out

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
