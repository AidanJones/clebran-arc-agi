"""Compare L2 planner performance across the 4 distance metrics.

Runs the single-pair L2 evaluation on data/traces.jsonl with each
of hamming / component / color_set / structural, and reports the
key metrics side by side.

Usage:
    uv run python scripts/compare_distance_metrics.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from clebran.world_model.l2_planner import L2Planner, _grid_hamming


def main():
    trace_path = REPO_ROOT / "data" / "traces.jsonl"
    rows = [json.loads(l) for l in trace_path.read_text(encoding="utf-8").splitlines()]
    print(f"loaded {len(rows):,} rows from {trace_path}")
    print()

    # Group rows by (task_id, input_idx).
    pairs = {}
    for r in rows:
        pairs.setdefault((r["task_id"], r["input_idx"]), []).append(r)

    for distance_name in ("hamming", "component", "color_set", "structural"):
        planner = L2Planner(distance=distance_name)
        n_pairs = 0
        n_finite = 0
        n_improves = 0
        total_d = 0.0
        n_match_hodel = 0
        n_hodel_in_cands = 0
        for (tid, iidx), pair_rows in pairs.items():
            state = None
            for r in pair_rows:
                if r["step_index"] == 0 and r["state"]["kind"] == "grid":
                    state = tuple(tuple(row) for row in r["state"]["grid"])
                    break
            if state is None:
                continue
            target = None
            for r in pair_rows:
                if r["next_state"]["kind"] == "grid":
                    target = tuple(tuple(row) for row in r["next_state"]["grid"])
            if target is None:
                continue
            id_d = _grid_hamming(state, target)
            if id_d == float("inf"):
                continue
            n_pairs += 1
            best = planner.plan(state, target)
            d = best["distance"] if best["distance"] != float("inf") else id_d
            if best["distance"] != float("inf"):
                n_finite += 1
                total_d += best["distance"]
            if best["distance"] < id_d:
                n_improves += 1
            # Hodel match
            hodel = None
            for r in pair_rows:
                if r["step_index"] == 0:
                    hodel = r["action"]
                    break
            if hodel is not None:
                from clebran.world_model.l2_planner import _default_candidates
                cands = _default_candidates(state, target)
                hodel_in = any(name == hodel["fn"] for name, _ in cands)
                if hodel_in:
                    n_hodel_in_cands += 1
                    if best["primitive"] == hodel["fn"]:
                        n_match_hodel += 1
        mean_d = total_d / max(1, n_finite)
        print(f"== distance={distance_name} ==")
        print(f"  pairs evaluated:        {n_pairs}")
        print(f"  finite-distance pairs:  {n_finite}")
        print(f"  mean planner distance:  {mean_d:.2f}")
        print(f"  planner improves:       {n_improves} / {n_pairs} = {n_improves/n_pairs:.1%}")
        print(f"  Hodel in cands:         {n_hodel_in_cands}")
        match_str = (f"{n_match_hodel}/{n_hodel_in_cands} = {n_match_hodel/n_hodel_in_cands:.1%}"
                     if n_hodel_in_cands else "n/a")
        print(f"  planner matches Hodel:  {match_str}")
        print()


if __name__ == "__main__":
    main()
