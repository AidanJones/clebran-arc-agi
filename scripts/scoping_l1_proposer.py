"""Scoping pilot for A1 — L1 (GPL1) as proposer.

Question: for the frontier subset's tasks (held out from GPL1 training),
how does GPL1's re-ranking of the L2 planner's candidate primitives
compare to the interpreter's re-ranking?

If GPL1's re-ranking matches Hodel's first-step primitive at the same
rate as the interpreter's re-ranking, the L1-proposer is worth
implementing (the L1's generalisation is at least as good as the
interpreter's local view).

If GPL1's re-ranking is significantly worse, the L1-as-proposer arm
is unlikely to beat B5+planner, and the A1 hypothesis is closed
structurally (the learned L1 is too lossy to be useful for this task).

Run::

    uv run python -m scripts.scoping_l1_proposer
"""
from __future__ import annotations

import json
from pathlib import Path

from clebran.world_model.l1_gp import GPL1
from clebran.world_model.l2_planner import _default_candidates


def _hamming_distance(a_grid, b_grid) -> int | float:
    """Cell-wise Hamming distance between two same-shape grids, or +inf
    if shapes differ. The grid is a tuple-of-tuples."""
    if a_grid is None or b_grid is None:
        return float("inf")
    if len(a_grid) != len(b_grid):
        return float("inf")
    d = 0
    for ra, rb in zip(a_grid, b_grid):
        if len(ra) != len(rb):
            return float("inf")
        for xa, xb in zip(ra, rb):
            if xa != xb:
                d += 1
    return d


def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    traces_path = repo / "data" / "traces.jsonl"
    frontier_path = repo / "data" / "frontier_subset.json"

    print(f"loading trace dataset from {traces_path} ...")
    rows = [json.loads(l) for l in traces_path.read_text(encoding="utf-8").splitlines()]
    print(f"  loaded {len(rows):,} rows")

    frontier = json.loads(frontier_path.read_text(encoding="utf-8"))
    frontier_tasks = {t["task_id"] for t in frontier["tasks"]}
    print(f"  frontier tasks (held-out): {len(frontier_tasks)}")

    # Train/test split: train on non-frontier tasks, test on frontier.
    train = [r for r in rows if r["task_id"] not in frontier_tasks]
    test = [r for r in rows if r["task_id"] in frontier_tasks]
    train_grid = [r for r in train
                  if r["state"]["kind"] == "grid"
                  and r["next_state"]["kind"] == "grid"]
    test_grid = [r for r in test
                 if r["state"]["kind"] == "grid"
                 and r["next_state"]["kind"] == "grid"]
    print(f"  train grid rows: {len(train_grid):,}, test grid rows: {len(test_grid):,}")

    print()
    print("training GPL1 on non-frontier tasks (this takes ~30s) ...")
    import time
    t0 = time.time()
    gp = GPL1(train_grid, pop_size=50, n_generations=8,
              max_program_len=3, seed=0, verbose=True)
    t1 = time.time()
    print(f"\nGPL1 evolution took {t1 - t0:.1f}s")

    # Per-primitive OOD accuracy on the frontier subset.
    print()
    print("per-primitive OOD accuracy on frontier tasks:")
    n_exact_total = 0
    n_shape_total = 0
    n_total_total = 0
    for prim, evo in gp.evolved.items():
        if evo.program is None:
            continue
        prim_test = [r for r in test_grid if r["action"]["fn"] == prim]
        if not prim_test:
            continue
        n_e, n_s = 0, 0
        for r in prim_test:
            state = tuple(tuple(row) for row in r["state"]["grid"])
            truth_grid = tuple(tuple(row) for row in r["next_state"]["grid"])
            try:
                pred_grid = evo.predict(state)
            except Exception:
                continue
            if pred_grid is None:
                continue
            if pred_grid == truth_grid:
                n_e += 1
            if (pred_grid is not None and truth_grid is not None
                    and len(pred_grid) == len(truth_grid)
                    and (not pred_grid or len(pred_grid[0]) == len(truth_grid[0]))):
                n_s += 1
        n_exact_total += n_e
        n_shape_total += n_s
        n_total_total += len(prim_test)
        if len(prim_test):
            print(f"  {prim:>20s}: exact={n_e}/{len(prim_test)} = "
                  f"{n_e/len(prim_test):.1%}, shape={n_s}/{len(prim_test)} = "
                  f"{n_s/len(prim_test):.1%}")
    if n_total_total:
        print(f"  {'TOTAL':>20s}: exact={n_exact_total}/{n_total_total} = "
              f"{n_exact_total/n_total_total:.1%}, "
              f"shape={n_shape_total}/{n_total_total} = "
              f"{n_shape_total/n_total_total:.1%}")

    # Now the actual ranking test: for each frontier demo pair's first
    # state, generate the L2 planner's candidates, score each by
    # (a) the interpreter (perfect L1), (b) the GPL1 prediction. Rank
    # candidates by each ranking. Where does Hodel's actual primitive
    # fall in each ranking?
    print()
    print("ranking test: rank Hodel's first-step primitive by "
          "interpreter distance vs GPL1 distance ...")
    rows_by_task = {}
    for r in test_grid:
        if r["step_index"] != 0:
            continue  # only first-step
        rows_by_task.setdefault(r["task_id"], []).append(r)
    per_task = {}
    for tid, trows in rows_by_task.items():
        # For each demo pair, find Hodel's first primitive and rank
        # it among the L2 planner's candidates under each scoring.
        n_pairs = 0
        n_hodel_in_cands = 0
        rk_int_1, rk_int_3, rk_int_5 = 0, 0, 0
        rk_gpl1_1, rk_gpl1_3, rk_gpl1_5 = 0, 0, 0
        n_gpl1_unknown = 0  # GPL1 doesn't have a learned program
        for r in trows:
            state = tuple(tuple(row) for row in r["state"]["grid"])
            target = r["next_state"]
            if target["kind"] != "grid":
                continue
            target_t = tuple(tuple(row) for row in target["grid"])
            hodel_action = r["action"]
            # Build the L2 planner's candidate set.
            candidates = _default_candidates(state, target_t)
            if not candidates:
                continue
            # Compute interpreter-based distance (perfect L1).
            from clebran.dsl.registry import PRIMITIVES
            interp_scored = []
            for fn_name, args in candidates:
                sig = PRIMITIVES[fn_name]
                try:
                    pred = sig.fn(*args)
                except Exception:
                    pred = None
                if pred is None or not (isinstance(pred, tuple) and pred
                                          and isinstance(pred[0], tuple)):
                    interp_scored.append((float("inf"), fn_name))
                    continue
                interp_scored.append((_hamming_distance(pred, target_t), fn_name))
            interp_scored.sort(key=lambda x: x[0])
            # Compute GPL1-based distance.
            gpl1_scored = []
            for fn_name, args in candidates:
                evo = gp.evolved.get(fn_name)
                if evo is None or evo.program is None:
                    gpl1_scored.append((float("inf"), fn_name))
                    continue
                # GPL1 only learns 1-arg grid→grid primitives. Skip
                # if not a candidate.
                sig = PRIMITIVES[fn_name]
                if sig.arity != 1:
                    gpl1_scored.append((float("inf"), fn_name))
                    continue
                try:
                    pred = evo.predict(state)
                except Exception:
                    pred = None
                if pred is None or not (isinstance(pred, tuple) and pred
                                          and isinstance(pred[0], tuple)):
                    gpl1_scored.append((float("inf"), fn_name))
                    continue
                gpl1_scored.append((_hamming_distance(pred, target_t), fn_name))
            gpl1_scored.sort(key=lambda x: x[0])
            # Find Hodel's rank.
            hodel_prim = hodel_action["fn"]
            # In interp ranking:
            for rank, (d, p) in enumerate(interp_scored, start=1):
                if p == hodel_prim:
                    n_pairs += 1
                    if rank == 1:
                        rk_int_1 += 1
                    if rank <= 3:
                        rk_int_3 += 1
                    if rank <= 5:
                        rk_int_5 += 1
                    break
            # In GPL1 ranking:
            ranked_under_gpl1 = False
            for rank, (d, p) in enumerate(gpl1_scored, start=1):
                if p == hodel_prim:
                    n_gpl1_unknown += 0
                    if rank == 1:
                        rk_gpl1_1 += 1
                    if rank <= 3:
                        rk_gpl1_3 += 1
                    if rank <= 5:
                        rk_gpl1_5 += 1
                    ranked_under_gpl1 = True
                    break
            if not ranked_under_gpl1:
                # GPL1 had no learned program for Hodel's primitive
                # (it's a 2-arg / 3-arg primitive not in GPL1's set).
                n_gpl1_unknown += 1
        per_task[tid] = (n_pairs, rk_int_1, rk_int_3, rk_int_5,
                         rk_gpl1_1, rk_gpl1_3, rk_gpl1_5, n_gpl1_unknown)
    # Aggregate.
    n_total = sum(p[0] for p in per_task.values())
    rk_int_1 = sum(p[1] for p in per_task.values())
    rk_int_3 = sum(p[2] for p in per_task.values())
    rk_int_5 = sum(p[3] for p in per_task.values())
    rk_gpl1_1 = sum(p[4] for p in per_task.values())
    rk_gpl1_3 = sum(p[5] for p in per_task.values())
    rk_gpl1_5 = sum(p[6] for p in per_task.values())
    n_unknown = sum(p[7] for p in per_task.values())
    print()
    print(f"scoped over {n_total} demo first-step pairs across "
          f"{len(per_task)} frontier tasks")
    print(f"  pairs where GPL1 had no program for Hodel's primitive: {n_unknown}")
    print()
    print(f"  {'ranking':<22s} {'#1':>8s} {'<=3':>8s} {'<=5':>8s}")
    if n_total:
        print(f"  {'interpreter (perfect)':<22s} "
              f"{rk_int_1:>4d}/{n_total:>3d} ({rk_int_1/n_total:>4.0%})  "
              f"{rk_int_3:>4d}/{n_total:>3d} ({rk_int_3/n_total:>4.0%})  "
              f"{rk_int_5:>4d}/{n_total:>3d} ({rk_int_5/n_total:>4.0%})")
        print(f"  {'GPL1 (learned)':<22s} "
              f"{rk_gpl1_1:>4d}/{n_total:>3d} ({rk_gpl1_1/n_total:>4.0%})  "
              f"{rk_gpl1_3:>4d}/{n_total:>3d} ({rk_gpl1_3/n_total:>4.0%})  "
              f"{rk_gpl1_5:>4d}/{n_total:>3d} ({rk_gpl1_5/n_total:>4.0%})")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())