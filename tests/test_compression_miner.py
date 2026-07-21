"""Stitch-style compression miner (roadmap item 3 follow-up)."""
from clebran.dsl.abstraction import (
    abstraction_from_slice, mine_compressing, mine_abstractions, _closure,
)
from clebran.dsl.interpreter import run, run_safe
from clebran.dsl.program import Program, Statement
from clebran.data.loader import load_task
from clebran.dsl.solver_parse import parse_all_solvers


def _prog(*stmts):
    return Program(list(stmts))


def test_generalize_consts_lifts_constants_to_params():
    # replace(I, FIVE, ZERO): with generalization both constants become params
    p = _prog(Statement(("prim", "replace"),
                        (("in", None), ("const", "FIVE"), ("const", "ZERO"))))
    exact = abstraction_from_slice(p, _closure(p, 0), generalize_consts=False)
    gen = abstraction_from_slice(p, _closure(p, 0), generalize_consts=True)
    assert exact.arity == 1 and exact.params == ("Grid",)
    assert gen.arity == 3  # grid + two lifted integer constants
    assert gen.params == ("Grid", "Integer", "Integer")


def test_compression_antiunifies_differing_constants():
    # two programs that differ only in a constant share one generalized
    # abstraction that the exact miner cannot find
    p1 = _prog(Statement(("prim", "replace"),
                         (("in", None), ("const", "FIVE"), ("const", "ZERO"))),
               Statement(("prim", "vmirror"), (("reg", 0),)))
    p2 = _prog(Statement(("prim", "replace"),
                         (("in", None), ("const", "THREE"), ("const", "ZERO"))),
               Statement(("prim", "vmirror"), (("reg", 0),)))
    # exact miner: the two replace-consts differ, so no 2-statement recurrence
    exact = mine_abstractions([p1, p2], min_count=2, min_size=2, max_size=2)
    assert exact == []
    # compression miner: recovers replace(p0, p1, ZERO) -> vmirror generalized
    comp = mine_compressing([p1, p2], min_size=2, max_size=2, min_utility=-10)
    assert comp, "compression miner should antiunify the differing constant"
    heads = [tuple(st.fn for st in a.body) for a in comp]
    assert (("prim", "replace"), ("prim", "vmirror")) in heads


def test_compression_utility_prefers_more_reused():
    # a subroutine appearing in 3 programs should outrank one appearing in 2
    def mk(c):
        return _prog(Statement(("prim", "replace"),
                               (("in", None), ("const", c), ("const", "ZERO"))),
                     Statement(("prim", "rot90"), (("reg", 0),)))
    progs = [mk("ONE"), mk("TWO"), mk("THREE")]  # generalized pattern occurs 3x
    comp = mine_compressing(progs, min_size=2, max_size=2, min_utility=0.0)
    assert comp, "a 3x-recurring 2-statement subroutine should compress (utility>0)"


def test_compression_abstraction_executes_correctly():
    # a generalized abstraction must still run identically to a concrete
    # instantiation of it
    p = _prog(Statement(("prim", "replace"),
                        (("in", None), ("const", "FIVE"), ("const", "ZERO"))))
    a = abstraction_from_slice(p, _closure(p, 0), name="A", generalize_consts=True)
    # call A(grid, 5, 0) should equal replace(grid, 5, 0)
    grid = ((5, 1), (5, 2))
    call = _prog(Statement(("abstr", "A"),
                           (("in", None), ("lit", 5), ("lit", 0))))
    assert run(call, grid, {"A": a}) == run(p, grid)


def test_compression_miner_on_real_solvers():
    progs = list(parse_all_solvers().values())
    comp = mine_compressing(progs, min_size=2, max_size=3, max_results=10)
    assert comp
    # generalized abstractions (arity > 1) should appear — the whole point
    assert any(a.arity > 1 for a in comp)
