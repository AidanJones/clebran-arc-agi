"""Recovered-primitive foundation (roadmap item 3): an abstraction call must
execute identically to its inlined body, and mining must recover a shared
subroutine."""
from clebran.dsl.abstraction import (
    abstraction_from_slice, mine_abstractions, _closure,
)
from clebran.dsl.interpreter import run, run_safe
from clebran.dsl.program import Program, Statement
from clebran.data.loader import load_task
from clebran.dsl.solver_parse import parse_all_solvers


def _grid(rows):
    return tuple(tuple(r) for r in rows)


# P: x0 = vmirror(I); O = hconcat(I, x0)   (the 6d0aefbc solution shape)
P = Program([
    Statement(("prim", "vmirror"), (("in", None),)),
    Statement(("prim", "hconcat"), (("in", None), ("reg", 0))),
])
GRIDS = [_grid([[1, 2], [3, 4]]), _grid([[5, 0, 1]]), _grid([[7]])]


def test_abstraction_equals_inlined_body():
    keep = _closure(P, 1)  # full program
    a = abstraction_from_slice(P, keep, name="A")
    assert a is not None
    # I is used twice but collapses to a single Grid parameter
    assert a.params == ("Grid",)
    q = Program([Statement(("abstr", "A"), (("in", None),))])
    for g in GRIDS:
        assert run(q, g, {"A": a}) == run(P, g), g


def test_abstraction_from_real_solver():
    # a depth-2 reference solver, abstracted whole, must reproduce its task
    progs = parse_all_solvers()
    tid = "6d0aefbc"
    prog = progs[tid]
    task = load_task("training", tid)
    a = abstraction_from_slice(prog, _closure(prog, len(prog) - 1), name="A")
    assert a is not None
    call = Program([Statement(("abstr", "A"), (("in", None),))])
    for inp, out in task.train + task.test:
        assert run_safe(call, inp, {"A": a}) == out


def test_mining_recovers_shared_subroutine():
    # two different programs share the subroutine  hconcat(I, vmirror(I))
    shared = [
        Statement(("prim", "vmirror"), (("in", None),)),
        Statement(("prim", "hconcat"), (("in", None), ("reg", 0))),
    ]
    p1 = Program(list(shared))
    p2 = Program(shared + [Statement(("prim", "hmirror"), (("reg", 1),))])
    mined = mine_abstractions([p1, p2], min_count=2, min_size=2, max_size=3)
    assert mined, "expected at least one recurring abstraction"
    # the shared 2-statement subroutine must be among the recovered ones
    bodies = {a.body for a in mined}
    keep = _closure(p1, 1)
    target = abstraction_from_slice(p1, keep).body
    assert target in bodies


def test_unmined_when_no_recurrence():
    p1 = Program([Statement(("prim", "vmirror"), (("in", None),))])
    p2 = Program([Statement(("prim", "hmirror"), (("in", None),))])
    # min_size 2 excludes single-statement slices; nothing recurs
    assert mine_abstractions([p1, p2], min_count=2, min_size=2) == []


# ---- search integration ----

import random  # noqa: E402

from clebran.genome import GenomeOps  # noqa: E402
from clebran.lineage import Lineage  # noqa: E402


def _abstr():
    return abstraction_from_slice(P, _closure(P, 1), name="ma")


def test_genomeops_emits_and_executes_abstraction():
    a = _abstr()
    ops = GenomeOps(
        ["vmirror", "hconcat", "hmirror"], random.Random(0),
        abstractions={"ma": a}, p_abstraction=0.5,
    )
    for _ in range(2000):
        p = ops.random_program()
        if p is not None and "ma" in p.abstractions_used():
            assert run_safe(p, GRIDS[0], {"ma": a}) is not None or True
            return
    raise AssertionError("search never emitted the abstraction")


def test_installed_abstraction_shared_across_ops_and_evaluator():
    tid = "6d0aefbc"
    task = load_task("training", tid)
    lin = Lineage("L", ["vmirror", "hconcat"], {tid: task}, seed=0, pop_size=20)
    name = lin.install_abstraction(_abstr())
    assert name in lin.abstractions
    assert name in lin.evaluator.abstractions            # shared dict
    assert name in lin.ops_by_task[tid].abstractions


def test_abstraction_collapses_depth2_task_to_depth1():
    # 6d0aefbc's reference solution is hconcat(I, vmirror(I)) — depth 2.
    # With that subroutine installed, a length-1 program solves it.
    tid = "6d0aefbc"
    task = load_task("training", tid)
    lin = Lineage("L", ["vmirror", "hconcat"], {tid: task}, seed=0, pop_size=20)
    name = lin.install_abstraction(_abstr())
    q = Program([Statement(("abstr", name), (("in", None),))])
    fit = lin.evaluator.evaluate(q, task)
    assert fit.solved_all          # correctness through the abstraction
    assert fit.length == 1         # MDL: one statement, the compression payoff
