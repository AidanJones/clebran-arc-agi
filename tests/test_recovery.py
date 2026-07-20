"""Compositionality / recovery metrics (roadmap item 3)."""
import pytest

from clebran.dsl.abstraction import abstraction_from_slice, _closure
from clebran.dsl.program import Program, Statement
from clebran.metrics.recovery import (
    spearman, topographic_similarity, abstraction_stats, _norm_lev,
)


def _abstr(body, name):
    p = Program(body)
    return abstraction_from_slice(p, _closure(p, len(p) - 1), name=name)


def test_spearman_monotone():
    assert spearman([1, 2, 3, 4], [1, 2, 3, 4]) == pytest.approx(1.0)
    assert spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)


def test_norm_lev_bounds():
    assert _norm_lev("abc", "abc") == 0.0
    assert _norm_lev("abc", "xyz") == 1.0
    assert 0 < _norm_lev("abc", "abd") < 1


def test_topsim_none_when_too_few():
    a = _abstr([Statement(("prim", "vmirror"), (("in", None),))], "a0")
    assert topographic_similarity({"a0": a}) is None


def test_topsim_defined_for_several_grid_abstractions():
    # four distinct grid->grid abstractions -> topsim is a real number in [-1,1]
    defs = {
        "a0": [Statement(("prim", "vmirror"), (("in", None),))],
        "a1": [Statement(("prim", "hmirror"), (("in", None),))],
        "a2": [Statement(("prim", "rot90"), (("in", None),))],
        "a3": [Statement(("prim", "vmirror"), (("in", None),)),
               Statement(("prim", "hmirror"), (("reg", 0),))],
    }
    abstractions = {k: _abstr(v, k) for k, v in defs.items()}
    ts = topographic_similarity(abstractions)
    assert ts is not None and -1.0 <= ts <= 1.0


def test_abstraction_stats_empty():
    class _L:
        abstractions = {}
    assert abstraction_stats(_L()) == {"n": 0}


def test_abstraction_stats_counts_usage():
    from clebran.data.loader import load_task
    from clebran.lineage import Lineage

    tid = "6d0aefbc"
    task = load_task("training", tid)
    lin = Lineage("L", ["vmirror", "hconcat"], {tid: task}, seed=0, pop_size=20)
    P = Program([Statement(("prim", "vmirror"), (("in", None),)),
                 Statement(("prim", "hconcat"), (("in", None), ("reg", 0)))])
    name = lin.install_abstraction(
        abstraction_from_slice(P, _closure(P, 1), name="ma"), received=True)
    # make the abstraction the recorded solution for the task
    from clebran.lineage import Individual
    q = Program([Statement(("abstr", name), (("in", None),))])
    fit = lin.evaluator.evaluate(q, task)
    lin.pops[tid].solved = True
    lin.pops[tid].solution = Individual(q, fit)

    stats = abstraction_stats(lin)
    assert stats["n"] == 1
    assert stats["used"] == 1
    assert stats["received"] == 1
    assert stats["received_used"] == 1  # NEO-style: used a received primitive
