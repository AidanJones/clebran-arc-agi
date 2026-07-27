"""Extract the actual evolved programs for specific B5/B5+planner tasks.

Reads the b5 and b5+planner logs and prints the evolved programs
for the 3 specific tasks of interest (f76d97a5, 0b148d64, f25fbde4).
The output is meant to be pasted into the paper as a side-by-side
comparison.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

LOG_DIR = Path("logs")
TASKS_OF_INTEREST = {"f76d97a5", "0b148d64", "f25fbde4"}


def find_solves(log_path: Path, task_ids: set) -> dict:
    """Return a dict mapping task_id -> (phase, len, program)."""
    out = {}
    for line in log_path.read_text(encoding="utf-8").splitlines():
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if d.get("event") != "solve":
            continue
        task = d.get("task")
        if task not in task_ids or task in out:
            continue
        # The program is stored as a JSON-serialised string in the
        # log; parse it back into a Python list.
        raw = d.get("program", [])
        if isinstance(raw, str):
            try:
                prog = json.loads(raw)
            except json.JSONDecodeError:
                prog = []
        else:
            prog = raw
        out[task] = {
            "phase": d.get("phase"),
            "len": d.get("len"),
            "program": prog,
            "evals": d.get("evals"),
        }
    return out


def fmt_program(prog: list) -> str:
    """Format a clebran program as IR text."""
    if not prog:
        return "(empty)"
    out = []
    for stmt in prog:
        # The stmt is [head, args] where head is [kind, name] and
        # args is [arg, ...] where each arg is [kind, payload].
        if isinstance(stmt, list) and len(stmt) == 2:
            head, args = stmt
            head_str = _fmt_head(head)
            if isinstance(args, list):
                arg_str = ", ".join(_fmt_arg(a) for a in args)
            else:
                arg_str = str(args)
            out.append(f"  {head_str}({arg_str})")
        else:
            out.append(f"  {stmt!r}")
    return "\n".join(out)


def _fmt_head(head) -> str:
    """Format a program head: ['prim', 'replace'] -> 'replace'."""
    if isinstance(head, list) and len(head) >= 2 and head[0] == "prim":
        return head[1]
    return repr(head)


def _fmt_arg(arg) -> str:
    """Format a clebran IR arg."""
    if isinstance(arg, list) and len(arg) >= 1:
        if arg[0] == "in":
            return "I"
        if arg[0] == "reg":
            return f"x{arg[1]}" if len(arg) > 1 else "x?"
        if arg[0] == "const":
            return arg[1] if len(arg) > 1 else "const?"
        if arg[0] == "lit":
            # Literal value
            return repr(arg[1]) if len(arg) > 1 else "lit?"
        if arg[0] == "prim":
            return f"prim:{arg[1]}" if len(arg) > 1 else "prim?"
    return repr(arg)


def main():
    seeds = [1, 2, 3]
    print("=" * 78)
    print("Per-task programs: B5 vs B5+planner on the 3 specific tasks")
    print("=" * 78)
    for task in ["f76d97a5", "0b148d64", "f25fbde4"]:
        print(f"\n### {task}")
        for arm, log_glob in [("B5", "b5_seed*.jsonl"),
                              ("B5P", "b5p_seed*.jsonl")]:
            for log_path in sorted(LOG_DIR.glob(log_glob)):
                seed_match = log_path.stem.split("seed")[-1]
                if not seed_match.isdigit() or int(seed_match) not in seeds:
                    continue
                solves = find_solves(log_path, {task})
                if task in solves:
                    s = solves[task]
                    print(f"\n  {arm} seed={seed_match} ({s['phase']}, "
                          f"len={s['len']}, evals={s.get('evals', '?')}):")
                    print(fmt_program(s["program"]))
                else:
                    print(f"\n  {arm} seed={seed_match}: NOT SOLVED in log")


if __name__ == "__main__":
    main()
