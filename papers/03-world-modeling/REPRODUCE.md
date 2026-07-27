# Reproducing the evidence — Paper 3 (world modeling)

Every quantitative claim in `paper.md` is regenerable from the
commands below. The substrate is the clebran rig (typed programs
evolved under pure reward over Hodel's ARC DSL); the world-modeling
additions are the trace dataset, the L1 baseline, the L2 planner,
and the B5+planner arm.

## 0. Environment

```sh
sh scripts/fetch_third_party.sh        # michaelhodel/arc-dsl + fchollet/ARC-AGI
uv sync
uv run pytest -q tests/test_world_model.py tests/test_b5_planner.py
```

## 1. The trace dataset

`data/traces.jsonl` is built by running all 400 Hodel reference
solvers through `interpreter.run_trace` and writing one row per
trace step (state, action, next_state).

```sh
uv run python scripts/build_traces.py
# -> 16,149 rows, 1,302 demo pairs, 6.3 MB
```

Inspect the dataset:

```sh
uv run python scripts/inspect_traces.py            # action head distribution
uv run python scripts/top_grid2grid_primitives.py  # top grid->grid primitives
```

## 2. The L1 baseline (k-NN)

`clebran/world_model/l1_baseline.py::KnnL1` is the wrong-model-class
baseline: index the trace data by `(action_head, arg_kinds)`, k-NN
over state grids, majority-vote next-state.

```sh
uv run python -m clebran.world_model l1
# -> 0% OOD exact-match, 5% in-distribution exact-match (99% coverage)
```

The result is the *floor* any learned L1 has to beat.

**Two programmatic learned L1s** (built and compared head-to-head
with the k-NN baseline in §3.2.5):

```sh
# Lookup-table L1: perfect cache over training rows, with
# interpreter fallback on miss.
uv run python -m clebran.world_model.l1_lookup
# -> 0% OOD hit rate, 25.5% OOD exact-match (via fallback),
#    33.6% in-distribution exact-match (coarse arg_kinds key),
#    0.6-1.2 us/pred lookup, 27-39 us/pred fallback
#    (~31-43x speedup at 0% hit rate)

# GP-evolved L1: clebran's own GP evolves a small program per
# primitive using GenomeOps random_program / mutate / crossover.
uv run python -m clebran.world_model.l1_gp
# -> evolves 33 primitives in ~10s, 18.7% OOD exact-match,
#    52.7% OOD shape-match, 108K pred/s, perfect on rot90 /
#    hmirror / vmirror / dmirror / cmirror (geometric primitives)

# Full head-to-head comparison (writes logs/l1_comparison.json):
uv run python scripts/compare_l1_approaches.py
```

## 3. The L2 planner (multi-pair, lookahead, loop-avoiding)

`clebran/world_model/l2_planner.py::L2Planner` is the perfect-L1
planner. The interpreter is the L1; the planner is a thin layer on
top that picks the candidate primitive whose multi-pair predicted
next-state has the minimum mean Hamming distance to the targets.

**Single-pair evaluation** (one (state, target) pair at a time, the
cleanest read of "does the planner pick a useful next primitive"):

```sh
uv run python -m clebran.world_model l2 --lookahead 1
# -> 35.9% improve over identity, 3.9% iterative solve, 28.2% Hodel match
```

**Multi-pair evaluation** (plan against ALL demo pairs simultaneously,
the metric that matters for the B5+planner integration):

```sh
uv run python scripts/evaluate_planner_multipair.py
# -> 9 / 263 tasks solved end-to-end (3.4%)

uv run python scripts/evaluate_planner_multipair.py --lookahead 2
# -> same ceiling (the iterative planner hits the 20-step cap
#    before lookahead can find longer programs)
```

## 4. The B5+planner arm (the integration test)

`clebran/baselines/b5_planner.py` is B5 (central library) plus a
planner-seeded individual in the initial population of every task.
The planner uses the multi-pair API and all of the task's demo
pairs as the planning target.

**3 seeds, 500K candidate-evaluations, frontier subset, lookahead=1:**

```sh
export CLEBRAN_SUBSET=frontier_subset
for s in 1 2 3; do
  uv run python -m clebran.baselines.b5_planner \
      --seed $s --budget 500000 --pop-size 100 --planner-lookahead 1
done
```

**3 seeds, 500K candidate-evaluations, frontier subset, lookahead=2:**

```sh
for s in 1 2 3; do
  uv run python -m clebran.baselines.b5_planner \
      --seed $s --budget 500000 --pop-size 100 --planner-lookahead 2
done
```

**3 seeds, 1M candidate-evaluations, frontier subset, lookahead=1:**

```sh
for s in 1 2 3; do
  uv run python -m clebran.baselines.b5_planner \
      --seed $s --budget 1000000 --pop-size 100 --planner-lookahead 1
done
```

**5 seeds, 4M candidate-evaluations, frontier subset, lookahead=1 (the
headline configuration):**

```sh
for s in 1 2 3 4 5; do
  uv run python -m clebran.baselines.b5_planner \
      --seed $s --budget 4000000 --pop-size 100 --planner-lookahead 1
done
```

**5 seeds, 4M candidate-evaluations, frontier subset, B5 baseline
(control):**

```sh
for s in 1 2 3 4 5; do
  uv run python -m clebran.baselines.frontier_sweep \
      --run --arm B5 --seed $s --budget 4000000
done
```

Or use `clebran.baselines.arms` for the Stage-1 subset and B5
matched-compute control.

**Claims (500K-1M, starved-GP regime, 3 seeds):**
B5 (control, 500K, 3 seeds): 9.67 solved, 2.67 evo, 1.61 mean length.
B5+planner (L=1, 500K, 3 seeds): 10.00 solved, 3.00 evo, 2.03 mean length.
B5+planner (L=2, 500K, 3 seeds): 10.00 solved, 3.00 evo, 1.70 mean length.
B5+planner (L=1, 1M, 3 seeds): 10.00 solved, 3.00 evo, 2.03 mean length.
B5+planner solves 1 unique task (f76d97a5) that B5 misses in any of the 3 seeds.

**Claims (4M, headline configuration, 5 seeds):**

| seed | B5 solved (evo) | B5+P solved (evo) | delta |
|---|---|---|---|
| 1 | 14 (7) | 13 (6) | -1 |
| 2 | 12 (5) | 13 (6) | +1 |
| 3 | 14 (7) | 12 (5) | -2 |
| 4 | 14 (7) | 12 (5) | -2 |
| 5 | 13 (5) | 12 (4) | -1 |
| **mean** | **13.40 ± 0.89 (6.20 evo)** | **12.40 ± 0.55 (5.20 evo)** | **-1.00** |

B5 union of solved tasks across 5 seeds: 16 unique.
B5+planner union: 14 unique.
B5-only tasks (B5 solves, B5+planner never does): `0b148d64`, `f25fbde4`
(each a single-seed rare-event solve — B5 seed 1 for 0b148d64, B5 seed 3
for f25fbde4).
B5+planner-only tasks: none — the B5+planner's solved set is a *strict
subset* of B5's.

Inspect the per-seed summary with `uv run python scripts/inspect_4m_sweep.py`.

## 5. Frozen data

The exact runs behind the paper are archived (not regenerated) under:

- `clebran/world_model/` — the L1 baseline, L2 planner, and README.
- `clebran/baselines/b5_planner.py` — the integration arm.
- `logs/b5p_seed1.jsonl`, `logs/b5p_seed2.jsonl`, `logs/b5p_seed3.jsonl` —
  the 1M-budget B5+planner logs (start/solve/epoch/summary events).
- `logs/b5_seed1.jsonl`, `logs/b5_seed2.jsonl`, `logs/b5_seed3.jsonl` —
  the 500K-budget B5 baseline logs (from the 2026-07-22 frontier run).

## 6. Tests

```sh
uv run pytest tests/test_world_model.py tests/test_b5_planner.py -v
```

22 tests cover:
- L1 baseline (KnnL1 indexing, voting, unseen-action handling,
  OOD evaluation against the trace dataset).
- L2 planner (single-pair distance, candidate set, multi-pair
  primitive selection, candidate rejection on shape mismatch,
  2-step lookahead, loop avoidance, plan-to-program conversion,
  evaluation against the trace dataset).
- B5+planner (seed_with_planner individual insertion,
  plan-to-program round-trip, full arm end-to-end at 100K budget).

The full clebran test suite (53 tests) passes.

## 7. Build the PDF

```sh
uv run python papers/build_pdf.py papers/03-world-modeling
```

## 8. Next push (open work)

The §9f build order in `roadmap.md` lists the natural follow-ups:
20-seed 4M-eval B5+planner frontier sweep; top-K planner seeds;
re-arc generated trace candidates; object-aware distance metric;
the learned L1; ARCTraj integration; ARC-AGI-3 evaluation.
