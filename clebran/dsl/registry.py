"""Primitive registry: every Hodel arc-dsl function with its type signature.

Signatures are kept as *strings* (the annotation names from arc_types), with a
subsumption relation `compatible(produced, expected)` used by typed mutation
and crossover. This is deliberately coarse — runtime execution is still
exception-guarded — but it prunes the vast majority of ill-typed programs
before they are ever run.
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Callable

from . import _vendor
from ._vendor import dsl as _dsl
from ._vendor import constants as _constants


@dataclass(frozen=True)
class Signature:
    name: str
    params: tuple[str, ...]   # annotation names, in order
    returns: str
    fn: Callable

    @property
    def arity(self) -> int:
        return len(self.params)


def _annotation_name(ann) -> str:
    """Render an annotation object back to its arc_types alias name."""
    if ann is inspect.Parameter.empty:
        return "Any"
    if isinstance(ann, str):
        return ann
    # arc_types aliases are typing constructs; match by identity against the
    # alias table so we recover the *alias name* rather than its expansion.
    from ._vendor import arc_types
    for alias in _ALIAS_NAMES:
        if ann is getattr(arc_types, alias, None):
            return alias
    if ann is bool:
        return "Boolean"
    if ann is int:
        return "Integer"
    return getattr(ann, "__name__", str(ann))


_ALIAS_NAMES = [
    "Boolean", "Integer", "IntegerTuple", "Numerical", "IntegerSet", "Grid",
    "Cell", "Object", "Objects", "Indices", "IndicesSet", "Patch", "Element",
    "Piece", "TupleTuple", "ContainerContainer", "Container", "Callable",
    "Tuple", "FrozenSet", "Iterable", "Any",
]

# Subsumption: value of type K can feed a parameter expecting type V.
# Derived from the alias definitions in arc_types.py.
_SUBSUMES: dict[str, set[str]] = {
    "Any": set(_ALIAS_NAMES),
    "Numerical": {"Integer", "IntegerTuple", "Numerical"},
    "Patch": {"Object", "Indices", "Patch"},
    "Element": {"Object", "Grid", "Element"},
    "Piece": {"Grid", "Object", "Indices", "Patch", "Piece"},
    "Container": {
        "Container", "ContainerContainer", "Tuple", "TupleTuple", "FrozenSet",
        "IntegerSet", "Grid", "Object", "Objects", "Indices", "IndicesSet",
        "Cell", "IntegerTuple", "Patch", "Element", "Piece",
    },
    "ContainerContainer": {
        "ContainerContainer", "Grid", "Objects", "IndicesSet", "TupleTuple",
    },
    "Iterable": {
        "Iterable", "Tuple", "TupleTuple", "FrozenSet", "IntegerSet", "Grid",
        "Object", "Objects", "Indices", "IndicesSet", "Cell", "IntegerTuple",
        "Patch", "Element", "Piece", "Container", "ContainerContainer",
    },
    "Tuple": {"Tuple", "TupleTuple", "Grid", "IntegerTuple", "Cell"},
    "TupleTuple": {"TupleTuple", "Grid"},
    "FrozenSet": {
        "FrozenSet", "IntegerSet", "Object", "Objects", "Indices",
        "IndicesSet",
    },
    "Callable": {"Callable"},
    "Boolean": {"Boolean"},
    "Integer": {"Integer", "Boolean"},
    "IntegerTuple": {"IntegerTuple"},
    "IntegerSet": {"IntegerSet"},
    "Grid": {"Grid"},
    "Cell": {"Cell"},
    "Object": {"Object"},
    "Objects": {"Objects"},
    "Indices": {"Indices"},
    "IndicesSet": {"IndicesSet"},
}


def compatible(produced: str, expected: str) -> bool:
    """Can a value of type `produced` be passed where `expected` is wanted?"""
    if produced == expected or expected == "Any" or produced == "Any":
        return True
    return produced in _SUBSUMES.get(expected, set())


def _build_registry() -> dict[str, Signature]:
    reg: dict[str, Signature] = {}
    for name, fn in inspect.getmembers(_dsl, inspect.isfunction):
        if name.startswith("_"):
            continue
        sig = inspect.signature(fn)
        params = tuple(
            _annotation_name(p.annotation) for p in sig.parameters.values()
        )
        returns = _annotation_name(sig.return_annotation)
        reg[name] = Signature(name=name, params=params, returns=returns, fn=fn)
    return reg


PRIMITIVES: dict[str, Signature] = _build_registry()

# Constants from Hodel's constants.py, typed.
CONSTANTS: dict[str, tuple[object, str]] = {}
for _name in dir(_constants):
    if _name.startswith("_"):
        continue
    _val = getattr(_constants, _name)
    if isinstance(_val, bool):
        _t = "Boolean"
    elif isinstance(_val, int):
        _t = "Integer"
    elif isinstance(_val, tuple):
        _t = "IntegerTuple"
    else:
        continue
    CONSTANTS[_name] = (_val, _t)
