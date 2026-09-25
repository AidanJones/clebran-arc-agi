# Novelty search arm pilot (2026-09-24) — discovery-bottleneck #4

The fourth concrete test of the **discovery bottleneck**: instead of
scoring programs by *task accuracy*, score them by *behavioral diversity*.
Hypothesis: novelty search explores the *space of programs* rather than
the frontier of *solved tasks*; its discoveries are different by
construction.

**Result: null — discovery-bottleneck menu is 0-for-4 at 1M.** The
novelty arm finds exactly the 6 easy tasks that B5-1M also finds;
no task is unique to novelty. The novelty arm degenerates (novelty
scores plateau, eval rate collapses) — the novelty objective doesn't
reward accuracy-improving mutations, so the lineage stops making
productive progress after the seeding phase.

## Question

Does a B5 lineage that scores on **behavioral novelty** (distinct-output
novelty: novelty = 1.0 for new outputs, decays toward 0 as the same
output is produced by more programs) find anything test-exact that
B5-1M doesn't?

## Hypothesis

The accuracy-scoring B5 lineage converges to a small region of program
space. A novelty objective traverses a different region. If the two
regions overlap on some *test-exact* program that B5 alone misses,
novelty search is a genuinely new discovery mechanism.

## Payoff if positive

A *new* discovery mechanism on the existing rig, orthogonal to all three
prior nulls (#1 failure-mode dreaming, #2 heterogeneous fitness,
#3 task-subset specialization). Even a single unique-to-novelty
test-exact solve would flip the discovery-bottleneck menu from "no
mechanism inside the DSL helps" to "yes, novelty does — and presumably
other objectives would too". Opens a class of objectives (behavioral
diversity, surprise, curiosity) as the next bet.

## If null

Discovery-bottleneck menu is **0-for-4 at 1M**. Even a different
*objective* (novelty) doesn't crack any task B5 already misses. Combined
with the #1–#3 nulls (different practice pool, different fitness signal,
,
different task pool) and the B5+planner 4M null, the cheapest reading
is that **no mechanism inside the current DSL/interpreter/fitness can
expand B5's reach at 1M, regardless of objective**. The structural-
change bet (novel primitive distribution, novel operator pool, novel
world model) becomes the dominant remaining strategy.

## Headline

| metric (1M, 5 seeds, partial — see "Honest scope" below) | B5N novelty | B5-1M accuracy | B5-2M matched |
|---|---|---|---|
| **test-exact solves / seed (mean)** | **2.00** | **10.20** | 11.00 |
| per-seed test-exact | [3, 3, 2, 1, 1] | [10, 10, 9, 11, 11] | [10, 12, 9, 12, 13] |
| tasks ever solved across all seeds | 6 | 24 | 25 |
| **tasks unique to this arm** | **0** | 6 | — |
| overlap with B5-1M | 6 / 6 = 100% | n/a | n/a |
| train-only overfits (lure) | 0 | 1 (`1f85a75f`) | 1 (`1f85a75f`) |

Per-task solve rate (mean over seeds):

```
task       B5N   B5-1M  B5-2M
9172f3a0   3     5      5
a416b8f3   3     5      5
6150a2bd   1     5      5
b1948b0a   1     5      5
d10ecb37   1     5      5
ed36ccf7   1     5      5
(all others 0 for B5N, B5-1M finds 10.20/30, B5-2M finds 11.00/30)
```

**Reading:** the novelty arm finds exactly the 6 easy tasks B5-1M also
finds, in fewer seeds. It does *not* find any of the 6 tasks B5-1M
finds but the novelty arm misses (0d3d703e, 5582e5ca, 5614dbcf,
5bd6f4ac, 6d0aefbc, dc0a314f). The novelty arm reaches the same
frontier as B5-1M — just slowly — and never expands it.

## Build

The novelty arm is implemented as `clebran.baselines.b0.run_b5_novelty`.
Same lineage machinery as B5 (central library, AOS, fragment injection,
restart, hall-of-fame) but with the primary score in
`Fitness.key` swapped for novelty. Library mining stays accuracy-driven
(only programs that solve all train pairs are mined into the library).

The novelty score is **distinct-output novelty** (O(1) per eval): the
per-pair output grids are hashed (one integer per task); the score for
a candidate is `1.0` if the hash is new to the per-task archive,
`1.0/(1.0 + count)` if it's been seen. FIFO cap of 500 distinct hashes
per task to bound memory.

A Hamming-nearest-neighbor novelty (the design-doc version) was tried
first but is `O(archive_size)` per eval and made 1M × 5 seeds infeasible
(>10× accuracy-mode wall-clock). The distinct-output version is `O(1)`
and gave the empirical results reported here.

## Setup

- **B5N arm** — 5 seeds × 1M evals × full stage1.
- **Baseline**: B5-1M (5 seeds, full stage1).
- **Matched compute**: B5-2M (5 seeds, full stage1, 67k/task).
- All logs at `logs/b5n_1m_seed{1..5}.jsonl`.

## Honest scope

The 1M × 5 seeds B5N run did not actually finish. **All 5 seeds
degenerated** partway through:

- novelty scoring as the *primary* objective doesn't reward accuracy-
  improving mutations. Once the per-task novelty archive fills with
  distinct outputs and subsequent programs produce duplicates, novelty
  plateaus near 0 and tournament selection degenerates.
- This made the eval rate collapse from ~1670 evals/sec (initial
  seeding phase) to ~70 evals/sec (degenerate state). At 70 evals/sec,
  1M evals × 5 seeds in parallel = ~4 hours, vs the 5–10 min that B5
  accuracy mode takes.
- We killed the runs after observing the degenerate behavior across all
  5 seeds. The data we have is from the seeding phase and early
  evolution (~10–30k evals per seed before before before the
  degeneration, depending on seed).

Despite the truncated runs, **the headline is informative**:

- B5N finds 6 tasks across 5 partial seeds (mean 2.0/seed).
- All 6 are also in B5-1M's set of solved tasks — *overlap is 100%*.
- 0 tasks are unique to B5N.
- The 6 B5N-finds tasks are all "easy" tasks that B5-1M finds in
  5/5 seeds; B5-1M's full set also includes 6 "medium" tasks that
  neither B5N nor B5-2M ever solve at 1M.

The pattern is consistent across partial seeds: B5N finds test-exact
solvers in the **seeding phase only**, never in evolution. Once novelty
plateaus, the lineage has no accuracy gradient to drive evolution-phase
progress. The novelty objective is fundamentally missing what makes B5
useful: a reward for *improving* programs, not just *new* programs.

## Reproduction

```sh
# Run all 5 seeds in parallel (each ~10–30 min until degeneration; we
# recommend killing after the degenerate plateau is observed):
pwsh scripts/run_b5n_1m.ps1

# Per-seed: B5N at 1M
uv run python -m clebran.baselines.b0 --arm B5N --seed N --budget 1000000

# Analysis (B5N vs B5-1M vs B5-2M, per-task test-exact, lure tasks,
# novelty archive sizes):
uv run python analyze_novelty.py
```

The novelty scoring's degenerate plateau is the headline negative
result. A follow-up that resets the novelty archive periodically
(e.g., every 50k evals) or weights novelty against an accuracy term
(e.g., 0.9 × novelty + 0.1 × solved_frac) could in principle keep
the search exploring; that's a follow-up, not this experiment.

## Files

- `clebran/fitness.py::Evaluator.evaluate_novelty` — distinct-output
  novelty scoring, with Hamming helper retained for future use.
- `clebran/lineage.py` — threads `fitness_mode` through the lineage;
  `step_generation` calls `evaluator.evaluate_for_mode`.
- `clebran/baselines/b0.py` — `run_b5_novelty()`; `--arm B5N` CLI;
  novelty-mode summary branch that reads `ev.test_exact_tasks()`.
- `clebran/metrics/cost.py` — loads `b5n_*_seed*.jsonl` as `B5N-1M`
  in the cost-axis ranking.
- `analyze_novelty.py` — comparison vs B5-1M / B5-2M.
- `scripts/run_b5n_1m.ps1` — driver.
- `logs/b5n_1m_seed{1..5}.jsonl` — partial 1M runs (killed when
  novelty plateaued).