# Novelty search arm 1M pilot (2026-09-24) — discovery-bottleneck #4

The fourth concrete test of the **discovery bottleneck**: instead of
scoring programs by *task accuracy*, score them by *behavioral
diversity*. Hypothesis: novelty search explores the *space of programs*
rather than the frontier of *solved tasks*; its discoveries are different
by construction.

If null at 1M, the menu is **0-for-4 at 1M** — strong evidence that no
mechanism *inside* the current DSL/interpreter/fitness can expand B5's
reach, regardless of objective. The structural-change bet becomes
dominant.

## Question

Does a B5 lineage that scores on **behavioral novelty** (mean Hamming
distance from the candidate's output to the existing population's
outputs) find anything test-exact that B5 doesn't?

## Hypothesis

The accuracy-scoring B5 lineage converges to a small region of program
space — wherever the train-solved-frac is high. A different objective
(novelty) traverses a different region. If the two regions overlap on
some *test-exact* program that B5 alone misses, novelty search is a
genuinely new discovery mechanism. If they don't, novelty search is a
different objective that doesn't crack any task B5 doesn't already.

## Payoff if positive

A *new* discovery mechanism on the existing rig, orthogonal to all three
nulls (#1 failure-mode dreaming, #2 heterogeneous fitness, #3 task-subset
specialization). Even a single unique-to-novelty test-exact solve would
flip the discovery-bottleneck menu from "no mechanism inside the
DSL helps" to "yes, novelty does — and presumably other objectives
would too". Opens a class of objectives (behavioral diversity, surprise,
curiosity, etc.) as the next bet.

## If null

Discovery-bottleneck menu is **0-for-4 at 1M**. Even a different
*objective* doesn't crack any task B5 already misses. Combined with the
#1–#3 nulls (different practice pool, different fitness signal,
different task pool) and the B5+planner 4M null, the cheapest reading is
that **no mechanism inside the current DSL/interpreter/fitness can
expand B5's reach at 1M, regardless of objective**. The structural-
change bet (novel primitive distribution, novel operator pool, novel
world model) becomes the dominant remaining strategy.

## Build

The minimum-viable novelty arm has three components:

1. **Novelty score** for a candidate program on a task:
   ```
   novelty(prog, task) = mean over train inputs of
       min over evaluated programs p in pop(task) of
           HammingDistance(p(inp), prog(inp))
   ```
   - Hamming distance treats grids as flat tuples, cells compared
     position-by-position; `None` outputs (crash) get max distance.
   - Mean over train inputs (matches the existing fitness's "fraction of
     pairs solved" denominator).
   - Population = all distinct programs ever evaluated on this task (an
     archive, not just the current top-100).
   - When the archive is empty (cold start), novelty defaults to a
     neutral value (e.g. mean grid size in cells).

2. **Replace the primary score** in `Fitness.key`:
   - Current: `key = (solved_frac, tiebreak)` — solved pairs, then
     length-tied per-cell accuracy.
   - Novelty: `key = (novelty_score, novelty_tiebreak)` — mean
     nearest-neighbor distance, then novelty-derived secondary score.
   - `solved_frac`, `tiebreak`, `solved_all`, `length` fields stay in
     the dataclass so the library / test-exact / reporting machinery is
     unaffected.

3. **The library mechanism still uses accuracy.** The library's purpose
   is to capture *useful* abstractions — programs B5 would re-discover.
   Mining novelty-scored programs into the library would only fill the
   library with novelty-but-incorrect programs. The mining threshold
   stays at "solved-all".

The cost meter, evaluator cache, AOS, fragment injection, restart,
population sort, hall-of-fame, dreaming hook — all unchanged. The only
delta is what goes into `Fitness.key`.

## Arms × seeds × budget

- **B5N (novelty-search arm)** — 5 seeds × 1M evals × full stage1.
  Same lineage, same DSL, same interpreter, same library mechanism;
  primary score swapped for novelty.
- **Baseline**: B5-1M (5 seeds, full stage1) — already on disk.

## Endpoints

- **test-exact solves** (the headline): number of tasks where the
  lineage's final state holds a program that passes both train AND
  test pairs. The novelty arm can find a test-exact solve by chance
  (novel + accurate); we report how many.
- **Frontier solves (lineage's claim)**: number of tasks where
  `solved_frac == 1.0`. Will be near zero (novelty arm doesn't
  optimize for accuracy), but if *some* are test-exact, that's a real
  positive.
- **Library size, used rate, cross-task reuse, topsim**: comparison
  against B5's library at the same budget. A positive result would
  show a *different* library — compositions B5 doesn't reach.
- **Cost axis**: evals/solve (per-solve for whatever novelty arm
  happens to find test-exact for).

## Reproduction

Once the arm is built, the run script is `scripts/run_b5n_1m.ps1`,
modelled on `scripts/run_b5_subset_1m.ps1`. The novelty-score
implementation is in `clebran/fitness.py::Evaluator.evaluate_novelty`
(or a new `clebran/novelty.py` if it gets long).

## Honest scope

- n=5 seeds at 1M evals. The 5-seed count matches the rest of the
  discovery-bottleneck menu; per-seed variance on a novelty objective
  could be higher than on accuracy (novelty doesn't have a saturating
  signal the way solved_frac does at the 1.0 ceiling), so a higher
  seed count might tighten the confidence interval. We follow the
  menu convention.
- The novelty score as defined is a *mean nearest-neighbor Hamming
  distance*. Other novelty metrics are plausible — KNN over behavior
  descriptors, output hash diversity, novelty-within-recent-window
  only. The choice of *Hamming nearest-neighbor* is the simplest that
  gives a meaningful diversity signal in O(archive) per evaluation;
  we don't claim it's optimal.
- We deliberately *do not* blend novelty with accuracy. The point of
  the experiment is to test a different objective, not a weighted
  combination. A "novelty + small accuracy bonus" arm could be tried
  later if pure novelty returns null.
- Library-mining stays accuracy-driven, so even if novelty search
  never finds a test-exact solve on its own, the libraries it builds
  could in principle still be useful as inputs to a downstream
  accuracy-driven pass. That's a follow-up, not this experiment.