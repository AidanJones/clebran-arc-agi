"""Parse Hodel's solvers.py into the linear program IR (§4.1 Step A).

Every solver has the rigid shape
    def solve_<taskid>(I):
        x1 = fn(...)
        ...
        O = fn(...)
        return O
with args limited to I, x<k>, constant names, and DSL function names
(verified: solvers.py contains no lambdas, no nested calls, no raw
literals). Parsing therefore recovers each solver *losslessly* into the
IR, giving both the depth proxy d (statement count) and an executable
reference program for the Step-D reproduction gate.
"""
from __future__ import annotations

import ast
from pathlib import Path

from .program import Program, Statement
from .registry import PRIMITIVES, CONSTANTS

SOLVERS_PATH = (
    Path(__file__).resolve().parents[2] / "third_party" / "arc-dsl" / "solvers.py"
)


class SolverParseError(Exception):
    pass


def _parse_arg(node: ast.expr, var_index: dict[str, int]):
    if not isinstance(node, ast.Name):
        raise SolverParseError(f"non-Name arg: {ast.dump(node)}")
    name = node.id
    if name == "I":
        return ("in", None)
    if name in var_index:
        return ("reg", var_index[name])
    if name in CONSTANTS:
        return ("const", name)
    if name in PRIMITIVES:
        return ("prim", name)
    raise SolverParseError(f"unknown name {name}")


def parse_solver(fn_def: ast.FunctionDef) -> Program:
    var_index: dict[str, int] = {}
    statements: list[Statement] = []
    for stmt in fn_def.body:
        if isinstance(stmt, ast.Return):
            if not (isinstance(stmt.value, ast.Name) and stmt.value.id == "O"):
                raise SolverParseError("return is not `return O`")
            continue
        if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
            raise SolverParseError(f"unexpected stmt: {ast.dump(stmt)}")
        target = stmt.targets[0]
        call = stmt.value
        if not isinstance(target, ast.Name) or not isinstance(call, ast.Call):
            raise SolverParseError("assignment is not `name = call(...)`")
        if not isinstance(call.func, ast.Name):
            raise SolverParseError(f"non-Name callee {ast.dump(call.func)}")
        if call.func.id in PRIMITIVES:
            callee = ("prim", call.func.id)
        elif call.func.id in var_index:
            callee = ("reg", var_index[call.func.id])
        else:
            raise SolverParseError(f"unknown fn {call.func.id}")
        args = tuple(_parse_arg(a, var_index) for a in call.args)
        var_index[target.id] = len(statements)
        statements.append(Statement(fn=callee, args=args))
    if "O" not in var_index or var_index["O"] != len(statements) - 1:
        raise SolverParseError("O is not the final assignment")
    return Program(statements)


def parse_all_solvers() -> dict[str, Program]:
    """task_id -> reference Program. Raises if any solver fails to parse."""
    tree = ast.parse(SOLVERS_PATH.read_text())
    out: dict[str, Program] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("solve_"):
            task_id = node.name.removeprefix("solve_")
            out[task_id] = parse_solver(node)
    return out


def solver_depths() -> dict[str, int]:
    """task_id -> depth proxy d (§4.1 Step A): number of call-assignments."""
    return {tid: len(prog) for tid, prog in parse_all_solvers().items()}
