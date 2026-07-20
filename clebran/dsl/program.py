"""Typed linear program IR — the genome representation.

A Program is an SSA-style sequence of statements
    r0 = callee(args); r1 = callee(args); ...; return r_last
mirroring the shape of Hodel's hand-written solvers, so reference solvers
parse losslessly into this IR. The callee is ("prim", name), ("reg", i)
— the latter because higher-order primitives (lbind, compose, matcher, …)
store callables in registers that later statements invoke — or
("abstr", name), a call to a lineage-discovered named abstraction
(§ recovered-primitive channel). Each arg is:

    ("in", None)      the task input grid I
    ("reg", i)        the result of statement i (i < current index)
    ("const", name)   a named constant from constants.py
    ("prim", name)    a DSL primitive passed as a value (higher-order arg)
    ("lit", value)    a raw literal (not produced by the solver parser;
                      available to mutation)
    ("param", k)      the k-th argument of the enclosing abstraction; only
                      ever appears inside an Abstraction body, never at the
                      top level
    ("hole", type)    an unbound slot to be filled by repair/injection

An `abstractions` argument (a mapping name -> Abstraction, anything exposing
`.params`/`.returns`) threads through the typing helpers so ("abstr", name)
statements type like primitives; it defaults to empty, so ordinary
primitive-only programs are unaffected.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from .registry import PRIMITIVES, CONSTANTS

Arg = tuple  # (kind, payload)


def _arg_from_json(a) -> Arg:
    """Rebuild an arg tuple from JSON, restoring literal tuples (JSON turns
    a ("lit", (0, 2)) payload into a list — convert it back so IntegerTuple
    literals stay tuples)."""
    kind, payload = a[0], a[1]
    if kind in ("lit", "hole") and isinstance(payload, list):
        payload = tuple(payload)
    return (kind, payload)


def _stmt_from_json(fn, args) -> "Statement":
    return Statement(tuple(fn), tuple(_arg_from_json(a) for a in args))


@dataclass(frozen=True)
class Statement:
    fn: Arg                 # ("prim", name) | ("reg", i) | ("abstr", name)
    args: tuple[Arg, ...]


@dataclass
class Program:
    statements: list[Statement] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.statements)

    def primitives_used(self) -> set[str]:
        used: set[str] = set()
        for st in self.statements:
            for kind, payload in (st.fn, *st.args):
                if kind == "prim":
                    used.add(payload)
        return used

    def abstractions_used(self) -> set[str]:
        return {
            st.fn[1] for st in self.statements if st.fn[0] == "abstr"
        }

    # ---- serialization ----
    def to_json(self) -> str:
        return json.dumps(
            [
                [list(st.fn), [list(a) for a in st.args]]
                for st in self.statements
            ]
        )

    @classmethod
    def from_json(cls, s: str) -> "Program":
        raw = json.loads(s)
        return cls([_stmt_from_json(fn, args) for fn, args in raw])

    def pretty(self) -> str:
        def render(a: Arg) -> str:
            kind, payload = a
            if kind == "in":
                return "I"
            if kind == "reg":
                return f"x{payload}"
            if kind == "param":
                return f"p{payload}"
            if kind == "lit":
                return repr(payload)
            return str(payload)

        lines = []
        for i, st in enumerate(self.statements):
            args = ", ".join(render(a) for a in st.args)
            lines.append(f"x{i} = {render(st.fn)}({args})")
        if lines:
            lines[-1] = lines[-1].replace(f"x{len(self.statements)-1} = ", "O = ", 1)
        return "\n".join(lines)


# Union aliases whose concrete type flows through polymorphic primitives:
# e.g. vmirror(x: Piece) -> Piece applied to a Grid returns a Grid.
_FLOW_THROUGH = {"Piece", "Element", "Patch", "Numerical"}


def _callee_sig(callee: Arg, abstractions) -> tuple[tuple, str] | None:
    """(params, returns) for a ("prim"|"abstr", name) callee, else None."""
    kind, name = callee
    if kind == "prim":
        sig = PRIMITIVES[name]
        return sig.params, sig.returns
    if kind == "abstr" and abstractions and name in abstractions:
        a = abstractions[name]
        return a.params, a.returns
    return None


def statement_return_type(program: Program, i: int, abstractions=None) -> str:
    """Static return type of statement i, with union flow-through
    refinement ("Any" for register-called or unknown-abstraction calls)."""
    st = program.statements[i]
    sig = _callee_sig(st.fn, abstractions)
    if sig is None:
        return "Any"
    params, ret = sig
    if ret in _FLOW_THROUGH:
        for k, pt in enumerate(params):
            if pt == ret and k < len(st.args):
                refined = arg_type(program, st.args[k], abstractions)
                if refined != "Any":
                    return refined
                break
    return ret


def arg_type(program: Program, a: Arg, abstractions=None) -> str:
    """Static type of an argument, as an arc_types alias name."""
    kind, payload = a
    if kind == "in":
        return "Grid"
    if kind == "reg":
        return statement_return_type(program, payload, abstractions)
    if kind == "const":
        return CONSTANTS[payload][1]
    if kind == "prim":
        return "Callable"
    if kind == "param":
        return "Any"  # only inside abstraction bodies; not typed here
    if kind == "hole":
        return payload
    if kind == "lit":
        if isinstance(payload, bool):
            return "Boolean"
        if isinstance(payload, int):
            return "Integer"
        if isinstance(payload, tuple):
            return "IntegerTuple"
        return "Any"
    raise ValueError(kind)
