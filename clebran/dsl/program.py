"""Typed linear program IR — the genome representation.

A Program is an SSA-style sequence of statements
    r0 = callee(args); r1 = callee(args); ...; return r_last
mirroring the shape of Hodel's hand-written solvers, so reference solvers
parse losslessly into this IR. The callee is ("prim", name) or ("reg", i)
— the latter because higher-order primitives (lbind, compose, matcher, …)
store callables in registers that later statements invoke. Each arg is:

    ("in", None)      the task input grid I
    ("reg", i)        the result of statement i (i < current index)
    ("const", name)   a named constant from constants.py
    ("prim", name)    a DSL primitive passed as a value (higher-order arg)
    ("lit", value)    a raw literal (not produced by the solver parser;
                      available to mutation)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from .registry import PRIMITIVES, CONSTANTS

Arg = tuple  # (kind, payload)


@dataclass(frozen=True)
class Statement:
    fn: Arg                 # ("prim", name) | ("reg", i)
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
        return cls(
            [
                Statement(tuple(fn), tuple(tuple(a) for a in args))
                for fn, args in raw
            ]
        )

    def pretty(self) -> str:
        def render(a: Arg) -> str:
            kind, payload = a
            if kind == "in":
                return "I"
            if kind == "reg":
                return f"x{payload}"
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


def statement_return_type(program: Program, i: int) -> str:
    """Static return type of statement i, with union flow-through
    refinement ("Any" for register-called statements)."""
    st = program.statements[i]
    if st.fn[0] != "prim":
        return "Any"
    sig = PRIMITIVES[st.fn[1]]
    ret = sig.returns
    if ret in _FLOW_THROUGH:
        for k, pt in enumerate(sig.params):
            if pt == ret and k < len(st.args):
                refined = arg_type(program, st.args[k])
                if refined != "Any":
                    return refined
                break
    return ret


def arg_type(program: Program, a: Arg) -> str:
    """Static type of an argument, as an arc_types alias name."""
    kind, payload = a
    if kind == "in":
        return "Grid"
    if kind == "reg":
        return statement_return_type(program, payload)
    if kind == "const":
        return CONSTANTS[payload][1]
    if kind == "prim":
        return "Callable"
    if kind == "lit":
        if isinstance(payload, bool):
            return "Boolean"
        if isinstance(payload, int):
            return "Integer"
        if isinstance(payload, tuple):
            return "IntegerTuple"
        return "Any"
    raise ValueError(kind)
