"""Compare all four L1 implementations on the clebran trace dataset.

Compares:
  1. **Identity** — predict the input state as the next state.
  2. **KnnL1** — k-nearest-neighbour over the trace dataset.
  3. **LookupTableL1** — perfect cache over training rows, with
     interpreter fallback on miss.
  4. **GPL1** — GP-evolved per-primitive L1.

Each L1 is measured on the same 20%-of-tasks held-out split on:
  * exact-match rate
  * shape-match rate
  * mean Hamming distance to the trace's next_state
  * predictions per second

Writes a JSON report to ``logs/l1_comparison.json`` and prints
a markdown table to stdout.
"""
from __future__ import annotations

import json
import random
import time
from collections import defaultdict
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from clebran.world_model import (
    KnnL1, LookupTableL1, GPL1,
    perfect_l1_fallback, safe_perfect_l1,
)


TRACE_PATH = Path("data/traces.jsonl")
TEST_FRAC = 0.2
SEED = 0
GP_POP_SIZE = 50
GP_N_GENERATIONS = 8
GP_MAX_PROGRAM_LEN = 3
KNN_K = 5
REPORT_PATH = Path("logs/l1_comparison.json")


def _grid_hamming(a, b) -> int:
    if len(a) != len(b):
        return 10**9
    d = 0
    for ra, rb in zip(a, b):
        if len(ra) != len(rb):
            return 10**9
        for xa, xb in zip(ra, rb):
            if xa != xb:
                d += 1
    return d


def _shape_of(g):
    if not isinstance(g, tuple) or not g or not isinstance(g[0], tuple):
        return None
    return (len(g), len(g[0]))


def load_rows():
    """Load the trace dataset."""
    print(f"loading trace dataset from {TRACE_PATH} ...")
    rows = [json.loads(l) for l in
            TRACE_PATH.read_text(encoding="utf-8").splitlines()]
    print(f"  loaded {len(rows):,} rows")
    return rows


def split_train_test(rows, test_frac=TEST_FRAC, seed=SEED):
    """80/20 split by task."""
    rng = random.Random(seed)
    tasks = sorted(set(r["task_id"] for r in rows))
    rng.shuffle(tasks)
    cutoff = int(round(len(tasks) * test_frac))
    test_tasks = set(tasks[:cutoff])
    train = [r for r in rows if r["task_id"] not in test_tasks]
    test = [r for r in rows if r["task_id"] in test_tasks]
    return train, test


def filter_grid(rows):
    """Restrict to grid→grid rows."""
    return [r for r in rows
            if r["state"]["kind"] == "grid"
            and r["next_state"]["kind"] == "grid"]


def score_predictions(predictions, test_rows):
    """Compute exact-match, shape-match, mean Hamming distance.

    ``mean_hamming`` is the mean of per-cell Hamming distance,
    restricted to predictions whose shape matches the truth
    (a wrong-shape prediction is not directly comparable, so we
    exclude it from the mean rather than give it a +inf penalty).
    The L1's *shape_rate* is the fraction of predictions with
    matching shape — a high shape_rate but low exact_rate means
    the L1 is a shape-correct but value-wrong predictor.
    """
    n = len(test_rows)
    n_exact = 0
    n_shape = 0
    hammings = []  # only for matching-shape predictions
    for r, pred in zip(test_rows, predictions):
        truth_grid = tuple(tuple(row) for row in r["next_state"]["grid"])
        if pred is None:
            continue
        # Coerce pred to tuple-of-tuples if it's a list.
        if isinstance(pred, list) and pred and isinstance(pred[0], list):
            pred_grid = tuple(tuple(row) for row in pred)
        elif isinstance(pred, dict) and pred.get("kind") == "grid":
            pred_grid = tuple(tuple(row) for row in pred["grid"])
        elif isinstance(pred, tuple) and pred and isinstance(pred[0], tuple):
            pred_grid = pred
        else:
            continue
        if pred_grid == truth_grid:
            n_exact += 1
        if _shape_of(pred_grid) == _shape_of(truth_grid):
            n_shape += 1
            h = _grid_hamming(pred_grid, truth_grid)
            hammings.append(h)
    return {
        "n_total": n,
        "n_exact": n_exact,
        "n_shape": n_shape,
        "exact_rate": n_exact / n if n else 0.0,
        "shape_rate": n_shape / n if n else 0.0,
        "mean_hamming_same_shape": (sum(hammings) / len(hammings)
                                    if hammings else float("inf")),
    }


def benchmark_predict_time(predict_fn, test_rows, n_repeats=3):
    """Measure predict-fn's wall time per row (best of n_repeats)."""
    best_us = float("inf")
    for _ in range(n_repeats):
        t0 = time.perf_counter_ns()
        for r in test_rows:
            state = tuple(tuple(row) for row in r["state"]["grid"])
            _ = predict_fn(state, r["action"])
        t1 = time.perf_counter_ns()
        elapsed_us = (t1 - t0) / 1000.0
        if elapsed_us < best_us:
            best_us = elapsed_us
    per_row_us = best_us / max(1, len(test_rows))
    return {
        "predict_time_us": per_row_us,
        "predictions_per_sec": 1e6 / per_row_us if per_row_us else 0.0,
    }


def run_identity(train, test):
    """Identity L1: predict the input state as the next state."""
    print()
    print("Identity L1 ...")
    predict_fn = lambda state, action: state
    t0 = time.time()
    preds = []
    for r in test:
        state = tuple(tuple(row) for row in r["state"]["grid"])
        preds.append(state)
    t_predict = time.time() - t0
    score = score_predictions(preds, test)
    timing = benchmark_predict_time(predict_fn, test)
    return {"name": "Identity", "score": score, "timing": timing,
            "train_time_s": 0.0}


def run_knn(train, test):
    """KnnL1 baseline."""
    print()
    print("KnnL1 baseline ...")
    t0 = time.time()
    knn = KnnL1(train, k=KNN_K)
    t_train = time.time() - t0
    print(f"  trained in {t_train:.1f}s ({knn.n_rows} grid rows)")
    def predict_fn(state, action):
        return knn.predict(state, action)
    preds = []
    for r in test:
        state = tuple(tuple(row) for row in r["state"]["grid"])
        preds.append(predict_fn(state, r["action"]))
    score = score_predictions(preds, test)
    timing = benchmark_predict_time(predict_fn, test)
    return {"name": "KnnL1", "score": score, "timing": timing,
            "train_time_s": t_train}


def run_lookup(train, test):
    """LookupTableL1 with interpreter fallback."""
    print()
    print("LookupTableL1 ...")
    t0 = time.time()
    l1 = LookupTableL1(train, fallback=safe_perfect_l1)
    t_train = time.time() - t0
    print(f"  trained in {t_train:.1f}s ({l1.n_rows} entries, "
          f"{l1.n_collisions} collisions)")
    def predict_fn(state, action):
        return l1.predict(state, action)
    preds = []
    for r in test:
        state = tuple(tuple(row) for row in r["state"]["grid"])
        preds.append(predict_fn(state, r["action"]))
    score = score_predictions(preds, test)
    timing = benchmark_predict_time(predict_fn, test)
    # Also measure the lookup-only path (no fallback) for the
    # in-distribution timing.
    return {"name": "LookupTableL1",
            "score": score, "timing": timing,
            "train_time_s": t_train,
            "n_entries": l1.n_rows, "n_collisions": l1.n_collisions}


def run_gp(train, test):
    """GP-evolved L1."""
    print()
    print("GPL1 (GP-evolved) ...")
    t0 = time.time()
    gp = GPL1(train, pop_size=GP_POP_SIZE, n_generations=GP_N_GENERATIONS,
              max_program_len=GP_MAX_PROGRAM_LEN, seed=SEED, verbose=False)
    t_train = time.time() - t0
    print(f"  evolved {len(gp.evolved)} primitives in {t_train:.1f}s")
    def predict_fn(state, action):
        return gp.predict(state, action)
    preds = []
    for r in test:
        state = tuple(tuple(row) for row in r["state"]["grid"])
        preds.append(predict_fn(state, r["action"]))
    score = score_predictions(preds, test)
    timing = benchmark_predict_time(predict_fn, test)
    # Per-primitive evolved-program lengths.
    lens = {p: (len(evo.program.statements) if evo.program else 0)
            for p, evo in gp.evolved.items()}
    return {"name": "GPL1", "score": score, "timing": timing,
            "train_time_s": t_train,
            "n_evolved": len(gp.evolved),
            "evolved_program_lengths": lens}


def main():
    rows = load_rows()
    train, test = split_train_test(rows)
    print(f"  train rows: {len(train):,}, test rows: {len(test):,}")
    train_grid = filter_grid(train)
    test_grid = filter_grid(test)
    print(f"  train grid rows: {len(train_grid):,}, "
          f"test grid rows: {len(test_grid):,}")
    results = []
    results.append(run_identity(train_grid, test_grid))
    results.append(run_knn(train_grid, test_grid))
    results.append(run_lookup(train_grid, test_grid))
    results.append(run_gp(train_grid, test_grid))
    # Print the comparison table.
    print()
    print("=" * 78)
    print("L1 COMPARISON (held-out tasks, 20% split)")
    print("=" * 78)
    print()
    header = (f"{'L1':>16s}  {'exact%':>7s}  {'shape%':>7s}  "
              f"{'mean_h*':>8s}  {'µs/pred':>8s}  {'pred/s':>9s}  "
              f"{'train_s':>8s}")
    print(header)
    print("-" * 78)
    for r in results:
        s = r["score"]
        t = r["timing"]
        # Print the mean Hamming as "—" if no shape-matching predictions.
        mh = s["mean_hamming_same_shape"]
        mh_str = f"{mh:>8.2f}" if mh != float("inf") else f"{'—':>8s}"
        print(f"{r['name']:>16s}  "
              f"{s['exact_rate']*100:>6.2f}%  "
              f"{s['shape_rate']*100:>6.2f}%  "
              f"{mh_str:>8s}  "
              f"{t['predict_time_us']:>8.2f}  "
              f"{t['predictions_per_sec']:>9.0f}  "
              f"{r['train_time_s']:>8.2f}")
    print()
    print("* mean per-cell Hamming, restricted to shape-matching "
          "predictions (no +inf penalty).")
    # Write JSON report.
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(results, indent=2,
                                       default=str), encoding="utf-8")
    print()
    print(f"JSON report written to {REPORT_PATH}")


if __name__ == "__main__":
    main()
