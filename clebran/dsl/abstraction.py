"""Named abstractions — lineage-discovered reusable subroutines.

The recovered-primitive channel (roadmap item 3, spec §11) has lineages
abstract their *own* subroutines out of successful programs and communicate
those, rather than sharing raw subtrees over Hodel's given primitives. An
Abstraction is a small program body parameterised by its external inputs; a
program invokes it as a *single* statement `("abstr", name)`, so it costs one
unit of program length (the MDL/compression story) yet expands at run time
(see interpreter._run_body).

This module defines the representation, lifts a dependency-closed program
slice into an Abstraction (external inputs — including the task grid I —
become positional parameters), and mines recurring subroutines across a set
of programs.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .program import Program, Statement, Arg, statement_return_type
from .registry import PRIMITIVES


@dataclass(frozen=True)
class Abstraction:
    name: str
    body: tuple[Statement, ...]   # ("reg", local) internally; ("param", k) for inputs
    params: tuple[str, ...]       # parameter type names, positional
    returns: str                  # return type (from the mining context)

    @property
    def arity(self) -> int:
        return len(self.params)

    @property
    def key(self) -> tuple:
        """Structural identity, name-independent — two slices that yield the
        same key are the same abstraction."""
        return (self.body, self.params, self.returns)

    def pretty(self) -> str:
        prog = Program(list(self.body))
        sig = ", ".join(f"p{i}:{t}" for i, t in enumerate(self.params))
        return f"{self.name}({sig}) -> {self.returns}:\n" + prog.pretty()


def _source_type(program: Program, a: Arg) -> str:
    kind, payload = a
    if kind == "in":
        return "Grid"
    if kind == "reg":
        return statement_return_type(program, payload)
    if kind == "hole":
        return payload
    return "Any"


def abstraction_from_slice(
    program: Program, keep: set[int], name: str = "A"
) -> Abstraction | None:
    """Lift a dependency-closed set of statement indices into an Abstraction.

    Internal register refs are renumbered 0..k; every external input — the
    task grid `I`, registers outside the slice, holes — becomes a positional
    parameter (identical sources are shared into one parameter, so a value
    used twice is one input). Returns None for slices this v1 does not
    support (a register-valued callee, i.e. a higher-order call)."""
    order = sorted(keep)
    local = {old: new for new, old in enumerate(order)}
    params: list[Arg] = []       # external source per parameter, in first-use order
    param_types: list[str] = []
    param_of: dict[Arg, int] = {}

    def resolve(a: Arg) -> Arg:
        kind, payload = a
        if kind == "reg" and payload in local:
            return ("reg", local[payload])
        if kind in ("const", "lit", "prim"):
            return a
        # external input -> parameter (shared across identical sources)
        if a not in param_of:
            param_of[a] = len(params)
            params.append(a)
            param_types.append(_source_type(program, a))
        return ("param", param_of[a])

    body: list[Statement] = []
    for old in order:
        st = program.statements[old]
        if st.fn[0] != "prim":
            return None  # v1: primitive-headed statements only (no reg-callees)
        body.append(Statement(st.fn, tuple(resolve(a) for a in st.args)))

    returns = statement_return_type(program, order[-1])
    return Abstraction(name, tuple(body), tuple(param_types), returns)


def _closure(program: Program, root: int) -> set[int]:
    """All statements the value at `root` depends on (inclusive)."""
    keep: set[int] = set()
    stack = [root]
    while stack:
        i = stack.pop()
        if i in keep:
            continue
        keep.add(i)
        st = program.statements[i]
        for kind, payload in (st.fn, *st.args):
            if kind == "reg":
                stack.append(payload)
    return keep


def bounded_slices(program: Program, min_size: int, max_size: int):
    """Every complete dependency-closed subroutine of bounded size — one per
    statement taken as the slice's output."""
    for root in range(len(program.statements)):
        keep = _closure(program, root)
        if min_size <= len(keep) <= max_size:
            yield keep


def mine_abstractions(
    programs: list[Program],
    min_count: int = 2,
    min_size: int = 2,
    max_size: int = 4,
    max_results: int = 20,
) -> list[Abstraction]:
    """Recurring reusable subroutines across `programs`, most-frequent first.

    A subroutine recurs when the *same* structure (same primitives, wiring,
    constants, and parameter shape — external inputs abstracted away) appears
    in ≥ min_count distinct programs. This is the duplicated-slice miner the
    roadmap calls for; Stitch could later replace it for optimal compression."""
    per_program: list[set[tuple]] = []
    rep: dict[tuple, Abstraction] = {}
    for prog in programs:
        keys: set[tuple] = set()
        for keep in bounded_slices(prog, min_size, max_size):
            a = abstraction_from_slice(prog, keep)
            if a is None:
                continue
            keys.add(a.key)
            rep.setdefault(a.key, a)
        per_program.append(keys)

    # count in how many distinct programs each structure appears
    doc_count: Counter = Counter()
    for keys in per_program:
        for k in keys:
            doc_count[k] += 1

    winners = [k for k, c in doc_count.items() if c >= min_count]
    winners.sort(key=lambda k: (doc_count[k], len(rep[k].body)), reverse=True)
    out: list[Abstraction] = []
    for i, k in enumerate(winners[:max_results]):
        a = rep[k]
        out.append(Abstraction(f"A{i}", a.body, a.params, a.returns))
    return out
