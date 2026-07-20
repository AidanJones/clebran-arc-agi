"""Deterministic, exception-guarded interpreter for the linear program IR.

Execution either returns a Grid or raises ExecutionError. Anything else a
buggy candidate can do (type errors inside primitives, unhashable args,
infinite-ish blowups) is converted to ExecutionError so fitness evaluation
can treat all failures uniformly.
"""
from __future__ import annotations

from .program import Program
from .registry import PRIMITIVES, CONSTANTS

Grid = tuple  # tuple of tuples of int


class ExecutionError(Exception):
    pass


# Guard against pathological memory blowups from candidates (e.g. repeated
# upscale). ARC grids are ≤30×30 but reference solvers build intermediate
# grids up to ~10× that (verified: all 400 solvers stay under these caps).
_MAX_GRID_CELLS = 400 * 400
_MAX_COLLECTION = 500_000


def _check_size(value) -> None:
    if isinstance(value, tuple) and value and isinstance(value[0], tuple):
        if len(value) * len(value[0]) > _MAX_GRID_CELLS:
            raise ExecutionError("grid too large")
    elif isinstance(value, (frozenset, tuple)) and len(value) > _MAX_COLLECTION:
        raise ExecutionError("collection too large")


def _invoke(callee, argvals: list, regs: list, abstractions: dict):
    """Call a ("prim"|"abstr"|"reg", ...) callee on already-evaluated args."""
    fkind, fpayload = callee
    if fkind == "prim":
        return PRIMITIVES[fpayload].fn(*argvals)
    if fkind == "abstr":
        if fpayload not in abstractions:
            raise ExecutionError(f"unknown abstraction {fpayload}")
        return _run_body(abstractions[fpayload], argvals, abstractions)
    if fkind == "reg":
        fn = regs[fpayload]
        if not callable(fn):
            raise ExecutionError("callee register not callable")
        return fn(*argvals)
    raise ExecutionError(f"bad callee kind {fkind}")


def _run_body(abstr, params: list, abstractions: dict):
    """Inline-execute an abstraction body. ("param", k) resolves to the
    bound call argument; the abstraction stays a single statement in the
    genome (one mutation/MDL unit) but expands here at run time."""
    regs: list[object] = []
    for st in abstr.body:
        args = []
        for kind, payload in st.args:
            if kind == "param":
                args.append(params[payload])
            elif kind == "reg":
                args.append(regs[payload])
            elif kind == "const":
                args.append(CONSTANTS[payload][0])
            elif kind == "prim":
                args.append(PRIMITIVES[payload].fn)
            elif kind == "lit":
                args.append(payload)
            else:
                raise ExecutionError(f"bad body arg kind {kind}")
        out = _invoke(st.fn, args, regs, abstractions)
        _check_size(out)
        regs.append(out)
    if not regs:
        raise ExecutionError("empty abstraction body")
    return regs[-1]


def run(program: Program, grid: Grid, abstractions: dict | None = None) -> Grid:
    abstractions = abstractions or {}
    regs: list[object] = []
    for st in program.statements:
        try:
            args = []
            for kind, payload in st.args:
                if kind == "in":
                    args.append(grid)
                elif kind == "reg":
                    args.append(regs[payload])
                elif kind == "const":
                    args.append(CONSTANTS[payload][0])
                elif kind == "prim":
                    args.append(PRIMITIVES[payload].fn)
                elif kind == "lit":
                    args.append(payload)
                else:
                    raise ExecutionError(f"bad arg kind {kind}")
            out = _invoke(st.fn, args, regs, abstractions)
            _check_size(out)
            regs.append(out)
        except ExecutionError:
            raise
        except RecursionError:
            raise ExecutionError("recursion")
        except Exception as e:  # noqa: BLE001 — candidate programs fail freely
            raise ExecutionError(f"{st.fn!r}: {type(e).__name__}") from None
    if not regs:
        raise ExecutionError("empty program")
    result = regs[-1]
    if not (
        isinstance(result, tuple)
        and result
        and all(isinstance(row, tuple) and row for row in result)
        and len({len(row) for row in result}) == 1
        and all(isinstance(v, int) for row in result for v in row)
    ):
        raise ExecutionError("result is not a rectangular grid")
    return result


def run_safe(program: Program, grid: Grid, abstractions: dict | None = None) -> Grid | None:
    try:
        return run(program, grid, abstractions)
    except ExecutionError:
        return None


def run_trace(
    program: Program, grid: Grid, abstractions: dict | None = None
) -> list[object]:
    """Execute like run() but return every intermediate register value
    (for visualization). Raises ExecutionError on failure."""
    abstractions = abstractions or {}
    regs: list[object] = []
    for st in program.statements:
        try:
            args = []
            for kind, payload in st.args:
                if kind == "in":
                    args.append(grid)
                elif kind == "reg":
                    args.append(regs[payload])
                elif kind == "const":
                    args.append(CONSTANTS[payload][0])
                elif kind == "prim":
                    args.append(PRIMITIVES[payload].fn)
                else:
                    args.append(payload)
            out = _invoke(st.fn, args, regs, abstractions)
            _check_size(out)
            regs.append(out)
        except ExecutionError:
            raise
        except Exception as e:  # noqa: BLE001
            raise ExecutionError(f"{st.fn!r}: {type(e).__name__}") from None
    return regs
