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

from collections import Counter, defaultdict
from dataclasses import dataclass

from .program import (
    Program, Statement, Arg, statement_return_type, _stmt_from_json,
)
from .registry import PRIMITIVES, CONSTANTS


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

    # ---- serialization (for logging + solver-card replay) ----
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "body": [[list(st.fn), [list(a) for a in st.args]] for st in self.body],
            "params": list(self.params),
            "returns": self.returns,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Abstraction":
        body = tuple(_stmt_from_json(fn, args) for fn, args in d["body"])
        return cls(d["name"], body, tuple(d["params"]), d["returns"])


def _source_type(program: Program, a: Arg) -> str:
    kind, payload = a
    if kind == "in":
        return "Grid"
    if kind == "reg":
        return statement_return_type(program, payload)
    if kind == "const":
        return CONSTANTS[payload][1]
    if kind == "lit":
        if isinstance(payload, bool):
            return "Boolean"
        if isinstance(payload, int):
            return "Integer"
        if isinstance(payload, tuple):
            return "IntegerTuple"
        return "Any"
    if kind == "hole":
        return payload
    return "Any"


def abstraction_from_slice(
    program: Program, keep: set[int], name: str = "A",
    generalize_consts: bool = False,
) -> Abstraction | None:
    """Lift a dependency-closed set of statement indices into an Abstraction.

    Internal register refs are renumbered 0..k; every external input — the
    task grid `I`, registers outside the slice, holes — becomes a positional
    parameter (identical sources are shared into one parameter, so a value
    used twice is one input). With `generalize_consts`, named constants and
    literals also become parameters — Stitch-style antiunification, so
    `replace(I, 5, 0)` and `replace(I, 3, 0)` share one abstraction
    `replace(p0, p1, 0)`. Returns None for slices this v1 does not support (a
    register-valued callee, i.e. a higher-order call)."""
    order = sorted(keep)
    local = {old: new for new, old in enumerate(order)}
    params: list[Arg] = []       # external source per parameter, in first-use order
    param_types: list[str] = []
    param_of: dict[Arg, int] = {}

    def resolve(a: Arg) -> Arg:
        kind, payload = a
        if kind == "reg" and payload in local:
            return ("reg", local[payload])
        if kind == "prim":
            return a
        if kind in ("const", "lit") and not generalize_consts:
            return a
        # external input (or a generalized constant) -> parameter, shared
        # across identical sources
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


def _utility(occ: int, body_size: int, arity: int, arity_penalty: float) -> float:
    """Compression utility of an abstraction (DreamCoder/Stitch form):
    replacing each of `occ` occurrences (each `body_size` statements) with one
    call saves occ·(body_size−1) statements; defining it costs body_size once.
    A mild arity penalty prefers low-arity units (fewer typed slots for search
    to fill)."""
    return occ * (body_size - 1) - body_size - arity_penalty * arity


def _skeleton(program: Program, order: list[int], local: dict[int, int]):
    """Structural key: primitive heads + register wiring, with every const/
    lit/external-input arg collapsed to a fillable slot. Slices sharing a
    skeleton are antiunification candidates."""
    sk = []
    for old in order:
        st = program.statements[old]
        if st.fn[0] != "prim":
            return None
        toks = []
        for kind, payload in st.args:
            if kind == "reg" and payload in local:
                toks.append(("reg", local[payload]))
            elif kind == "prim":
                toks.append(("prim", payload))
            else:
                toks.append(("slot",))
        sk.append((st.fn, tuple(toks)))
    return tuple(sk)


def _antiunify(reps: list[tuple]) -> Abstraction | None:
    """Antiunify a group of slices sharing a skeleton: a slot stays an inline
    constant iff it holds the *same* const/lit across every member, else it
    becomes a parameter (external inputs always do). Slots that co-vary
    identically share one parameter — so a grid used twice stays one input.
    This yields the minimal-arity generalization (Stitch behaviour)."""
    p0, order0, local0 = reps[0]

    def arg_at(rep, si, ai):
        p, order, _ = rep
        return p.statements[order[si]].args[ai]

    param_of: dict[tuple, int] = {}
    param_types: list[str] = []
    body: list[Statement] = []
    for si, old0 in enumerate(order0):
        st0 = p0.statements[old0]
        new_args = []
        for ai, a0 in enumerate(st0.args):
            kind, payload = a0
            if kind == "reg" and payload in local0:
                new_args.append(("reg", local0[payload]))
                continue
            if kind == "prim":
                new_args.append(a0)
                continue
            sig = tuple(arg_at(r, si, ai) for r in reps)
            if len(set(sig)) == 1 and kind in ("const", "lit"):
                new_args.append(a0)  # invariant constant → inline
                continue
            if sig not in param_of:
                param_of[sig] = len(param_types)
                param_types.append(_source_type(p0, a0))
            new_args.append(("param", param_of[sig]))
        body.append(Statement(st0.fn, tuple(new_args)))
    returns = statement_return_type(p0, order0[-1])
    return Abstraction("A", tuple(body), tuple(param_types), returns)


def mine_compressing(
    programs: list[Program],
    min_size: int = 2,
    max_size: int = 4,
    max_results: int = 20,
    max_arity: int = 4,
    arity_penalty: float = 0.5,
    min_utility: float = 0.0,
    min_occurrences: int = 2,
) -> list[Abstraction]:
    """Stitch-style compression miner. Groups bounded dependency-closed slices
    by structural skeleton, antiunifies each group (lifting only the constants
    that *vary*, so `replace(I, 5, 0)` and `replace(I, 3, 0)` collapse to one
    minimal-arity `replace(p0, p1, 0)`), and returns the highest-compression-
    utility abstractions. This is the key advance over `mine_abstractions`,
    which can only find exact-constant recurrences. Native to the linear IR;
    real Stitch (lambda s-exprs) could replace it for globally-optimal,
    nesting-aware compression."""
    groups: dict[tuple, list[tuple]] = defaultdict(list)
    for prog in programs:
        for keep in bounded_slices(prog, min_size, max_size):
            order = sorted(keep)
            local = {old: i for i, old in enumerate(order)}
            sk = _skeleton(prog, order, local)
            if sk is not None:
                groups[sk].append((prog, order, local))

    scored: list[tuple] = []
    for reps in groups.values():
        occ = len(reps)
        if occ < min_occurrences:
            continue
        a = _antiunify(reps)
        if a is None or a.arity > max_arity:
            continue
        u = _utility(occ, len(a.body), a.arity, arity_penalty)
        if u >= min_utility:
            scored.append((u, a))
    scored.sort(key=lambda t: (t[0], len(t[1].body)), reverse=True)
    return [
        Abstraction(f"A{i}", a.body, a.params, a.returns)
        for i, (_, a) in enumerate(scored[:max_results])
    ]
