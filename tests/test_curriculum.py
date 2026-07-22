"""Task generation for communication-through-curricula (roadmap 7b)."""
import random

from clebran.curriculum import generate_task, solves, sample_input, _valid_task
from clebran.dsl.abstraction import abstraction_from_slice, _closure
from clebran.dsl.program import Program, Statement
from clebran.dsl.solver_parse import parse_all_solvers


# a real transform: O = hconcat(I, vmirror(I))  (mirror-and-append)
MIRROR_APPEND = Program([
    Statement(("prim", "vmirror"), (("in", None),)),
    Statement(("prim", "hconcat"), (("in", None), ("reg", 0))),
])


def test_generated_task_is_wellformed_and_solved_by_source():
    rng = random.Random(0)
    task = generate_task(MIRROR_APPEND, rng, n_pairs=4)
    assert task is not None
    assert len(task.train) >= 2 and len(task.test) == 1
    # round-trip: the generating program must solve its own task
    assert solves(MIRROR_APPEND, task)


def test_generated_task_is_nontrivial():
    rng = random.Random(1)
    task = generate_task(MIRROR_APPEND, rng, n_pairs=4)
    pairs = list(task.train) + list(task.test)
    # not identity on every pair, inputs distinct, outputs not all identical
    assert _valid_task(pairs)
    assert any(i != o for i, o in pairs)


def test_variants_differ_across_seeds():
    a = generate_task(MIRROR_APPEND, random.Random(2), n_pairs=4)
    b = generate_task(MIRROR_APPEND, random.Random(3), n_pairs=4)
    assert a.train[0][0] != b.train[0][0]  # different sampled inputs


def test_identity_program_yields_no_task():
    # O = identity(I): every pair is trivial, so no shareable task
    idprog = Program([Statement(("prim", "identity"), (("in", None),))])
    # identity returns non-grid (Any) for a grid input? it returns the grid.
    task = generate_task(idprog, random.Random(0), n_pairs=4)
    assert task is None  # all-identity rejected


def test_generation_from_abstraction_using_program():
    # program that calls a recovered abstraction as its head
    a = abstraction_from_slice(MIRROR_APPEND, _closure(MIRROR_APPEND, 1), name="MA")
    prog = Program([Statement(("abstr", "MA"), (("in", None),))])
    task = generate_task(prog, random.Random(0), abstractions={"MA": a}, n_pairs=4)
    assert task is not None
    assert solves(prog, task, abstractions={"MA": a})


def test_generate_from_real_solvers():
    # generating from a spread of reference solvers should mostly succeed and
    # always round-trip when it does
    progs = parse_all_solvers()
    made = rt = 0
    for tid in sorted(progs)[:40]:
        task = generate_task(progs[tid], random.Random(7), n_pairs=4)
        if task is not None:
            made += 1
            rt += solves(progs[tid], task)
    assert made >= 10          # generation works on a real variety of transforms
    assert rt == made          # every generated task is solved by its source
