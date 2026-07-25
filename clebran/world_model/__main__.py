"""CLI entry point for clebran.world_model.

Run with:
    uv run python -m clebran.world_model --trace-path data/traces.jsonl
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .l1_baseline import main as run_l1_baseline
from .l2_planner import main as run_l2_planner


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_l1 = sub.add_parser("l1", help="Evaluate the L1 baseline on the trace dataset")
    p_l1.add_argument("--trace-path", type=Path, default=Path("data/traces.jsonl"))
    p_l1.add_argument("--k", type=int, default=5)
    p_l1.add_argument("--test-frac", type=float, default=0.2)
    p_l1.add_argument("--seed", type=int, default=0)

    p_l2 = sub.add_parser("l2", help="Evaluate the L2 planner on the trace dataset")
    p_l2.add_argument("--trace-path", type=Path, default=Path("data/traces.jsonl"))

    args = ap.parse_args()
    if args.cmd == "l1":
        return run_l1_baseline(
            trace_path=args.trace_path,
            k=args.k,
            test_frac=args.test_frac,
            seed=args.seed,
        )
    if args.cmd == "l2":
        return run_l2_planner(trace_path=args.trace_path)
    return 1


if __name__ == "__main__":
    sys.exit(main())
