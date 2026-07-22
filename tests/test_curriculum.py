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


def test_curriculum_crosses_the_channel_and_is_learnable():
    # a lineage that has solved a task generates a variant, publishes it over
    # the curriculum channel; a receiver adds it as an auxiliary task, evolves,
    # and solves it — learning the concept from a shared *problem*, not code
    from clebran.data.loader import load_task
    from clebran.lineage import Lineage, Individual
    from clebran.channel import make_channel
    from clebran.orchestrator import _publish, _receive

    tid = "6d0aefbc"  # reference solution is exactly MIRROR_APPEND
    task = load_task("training", tid)
    pool = ["vmirror", "hconcat"]
    teacher = Lineage("T", pool, {tid: task}, seed=0, pop_size=30)
    student = Lineage("S", pool, {tid: task}, seed=1, pop_size=30)

    # make the teacher "have learned" the transform
    fit = teacher.evaluator.evaluate(MIRROR_APPEND, task)
    teacher.pops[tid].solved = True
    teacher.pops[tid].solution = Individual(MIRROR_APPEND, fit)

    chan = make_channel("constrained", payload="curriculum",
                        max_fragment_size=6, max_messages=3)
    _publish(teacher, chan, max_frag_size=6)
    _publish(student, chan, max_frag_size=6)
    got = _receive(student, chan)

    assert got == 1                              # a teaching task crossed
    assert len(student.aux_task_ids) == 1
    aux_id = next(iter(student.aux_task_ids))
    assert aux_id in student.pops                # student registered it
    # the student can learn it: evolve the aux task to solution
    for _ in range(400):
        student.step_generation(aux_id)
        if student.pops[aux_id].solved:
            break
    assert student.pops[aux_id].solved           # learned from the shared task
    # ...and solving it never counts toward the real solve rate
    assert aux_id not in student.solved_tasks()


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
