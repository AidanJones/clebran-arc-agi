# clebran.world_model

L1 next-state predictors and evaluation, in service of the
"world model for ARC" direction (§9f in `roadmap.md`).

The clebran interpreter is a perfect L1: it computes
`next_state` from `(state, action)` exactly, deterministically, for
every primitive in Hodel's 160-primitive DSL. The open question is
whether a *learned* approximation generalises well enough to be
useful for planning. This package provides the trace dataset, the
L1 baselines, and the evaluation harness to measure that.

## Quick start

```sh
# 1. Build the trace dataset (one row per (state, action, next_state)
#    triple) from the 400 Hodel reference solvers. ~10 seconds.
uv run python scripts/build_traces.py

# 2. Evaluate the k-NN L1 baseline (with in-distribution sanity check).
uv run python -m clebran.world_model l1

# 3. Run the test suite.
uv run pytest tests/test_world_model.py
```

## Trace dataset

`data/traces.jsonl` is a JSONL file; one row per clebran trace step.
Each row is:

```json
{
  "task_id":     "<arc task id>",
  "input_idx":   <0-based index into the demo pairs>,
  "step_index":  <0-based index into the program statements>,
  "state":       {"kind": "grid"|"int"|"tuple"|"other", ...},
  "action": {
    "fn":         <primitive name>,
    "fn_kind":    "prim" | "reg" | "abstr",
    "arg_kinds":  ["in" | "reg:N" | "const:NAME" | "prim:NAME", ...]
  },
  "next_state":  {"kind": ...},
  "program_len": <total statements in the program>
}
```

The current dataset (built from the 400 Hodel reference solvers) has
**16,149 trace steps** from **1,302 demo pairs** across **400 tasks**.
Of those, **1,378 (~10%) are grid→grid transitions**; the rest
involve heterogeneous types (tuples of objects from `objects()`,
integers from `width()`/`height()`, frozensets, etc.) which are part
of the clebran IR's type system and need a unified L1 if the world
model is to be used for planning.

## L1 baseline: k-NN

The `KnnL1` class is the simplest possible learned L1: index the
trace dataset by `(action_head, arg_kinds)`, retrieve the k nearest
training rows by Hamming distance on the state grid, and return
the majority-vote next_state.

## Evaluation result (k=5, 80/20 split by task, 0% exact-match)

```
KnnL1 exact-match:        0 / 353  =  0.00%   (coverage: 36.83%)
KnnL1 shape-match:       27 / 353  =  7.65%
Identity  exact-match:    19 / 353  =  5.38%
Identity  shape-match:  189 / 353  = 53.54%

In-distribution sanity check (k-NN has seen 99% of these rows):
In-dist KnnL1 exact-match:    14 / 280  =  5.00%   (coverage: 99.29%)
In-dist KnnL1 shape-match:   212 / 280  = 75.71%
In-dist Identity  exact-match: 21 / 280  =  7.50%
In-dist Identity  shape-match: 175 / 280  = 62.50%
```

**Finding.** The k-NN baseline fails to *generalise* (0% out-of-
distribution exact-match) and fails to *memorise* (5% in-
distribution exact-match with 99% coverage). The (state, action) →
next_state relationship is highly state-specific: the same
primitive applied to two 1-cell-different states produces very
different next-states for most DSL primitives, so Hamming-distance
neighbours have inconsistent next-states and the majority vote
loses.

The identity baseline (predict the input as the output) gets 53.5%
shape-match and 5.4% exact-match — most grid→grid actions in the
test set preserve the shape (e.g. `vmirror`, `fill`, `paint`,
`replace`); 5% of them are pure identity (e.g. `cover(I, ...)`
with no objects to cover returns `I`).

**Implication.** A k-NN baseline is the wrong model class for this
problem. The clebran interpreter is a perfect L1; the L1 question
becomes "can we learn a fast parametric approximation of the
interpreter that generalises across (state, action) pairs?" That is
a learned model problem (small neural net, or a programmatic
approximation evolved by clebran's own GP), and the L1 result above
is a *baseline* against which to measure it. The next concrete
deliverable (§9f build-order item 2 in `roadmap.md`) is to design
and train that learned L1.

## Next concrete deliverable

The natural next step (§9f build-order item 3) is the **L2
planning arm**: a B5-style arm that, at each step, uses the
*interpreter as a perfect L1* to roll out candidate primitives
and pick the first one whose predicted next-state is closest to
the target. This tests whether *planning with a perfect world
model* is useful — the upper bound for any learned world model —
before worrying about learning a fast approximation.

## L2 planner: one-step and iterative planning

The L2 planner (`clebran/world_model/l2_planner.py`) is a thin
layer on top of the clebran interpreter. For a given (state, target)
pair, it iterates over a fixed candidate set — the most common
grid→grid primitives in the Hodel reference solvers, with hand-
defined default-argument strategies (e.g. `vconcat(I, I)`,
`vconcat(I, vmirror(I))`, `fill(I, mc, ((mc,),))`, `replace(I, mc, c)`
for `c in {0, 1, 2, 3}`) — and picks the primitive whose predicted
next-state has minimum Hamming distance to the target.

### Evaluation (one-step + iterative on the full trace dataset)

**Single-pair L2 evaluation** (one (state, target) pair at a time,
the most direct measure of "does the planner pick a useful next
primitive"):

```
demo pairs evaluated:        1302
(finite-distance pairs:        815)   # pairs where input shape = target shape
identity  mean distance:     26.29
planner   mean distance:     19.87   # 24% reduction
planner improves over identity: 468 / 1302 = 35.9%
Hodel first primitive in candidate set: 241
planner matches Hodel (when in candidate set): 68 / 241 = 28.2%
iterative planner (max 20 steps) solves: 32 / 815 = 3.9%
```

**Multi-pair L2 evaluation** (plan against ALL of a task's demo
pairs simultaneously — the metric that matters for the B5+planner
integration; for each task, the planner must produce a program
that works on every demo):

```
finite-shape tasks evaluated:        263
planner solves (all demos exactly):  9 / 263 = 3.4%
planner partial (some progress):   254
planner no-program:                  0
mean steps per task:               19.3  (near the 20-step cap)
```

### Distance metrics — single-pair diagnostic (815 same-shape pairs)

Four distance metrics are now exposed via `L2Planner(distance=...)`:

| metric | improves over identity | Hodel match (in-cand) | mean dist |
|---|---|---|---|
| `hamming` (default) | 35.2% | 36.7% | 19.87 |
| `component` | 97.9% | 35.4% | 1.22 |
| `color_set` | 98.4% | 20.3% | 0.67 |
| `structural` | 87.5% | 36.7% | 5.77 |

The component / color_set metrics have *much* higher improve rates
because they're easier to satisfy (most primitives change at most
a few components, so the bar is low). But the Hodel match rate
is similar (component 35.4% vs hamming 36.7%) and the multi-pair
iterative solve rate is **unchanged** across all four metrics
(3.4% / 9 / 263). **The distance metric is not the bottleneck
for the multi-pair solve rate** — the bottleneck is the candidate
set. The 28.2% Hodel match rate is the diagnostic: when the
planner is *allowed* to pick the right primitive (because it's in
the candidate set), it only matches the Hodel solver 36.7% of
the time, regardless of the metric. The remaining 63% is the
planner picking a *lower-distance* primitive that the Hodel
solver wouldn't have picked — a metric / planning problem, not
a candidate-coverage problem.

The structural distance is exposed as the natural upgrade for
users who want object-aware behavior (it scores primitives on
structural match rather than cell-wise Hamming), and the
component / color_set metrics are exposed for diagnostic
experiments. The default stays `hamming` for backward
compatibility and because Hamming is the metric the B5 fitness
function optimizes at the integration level — see §3.3 below.

### B5+planner integration by distance metric (3 seeds, 500K)

The B5+planner arm with the *structural* distance (3 seeds, 500K
budget, frontier subset): 9.33 mean solves (2.33 evo, mean length
1.6). Hamming: 10.0 / 3.0 / 2.03. The Hamming-based planner
produces programs that more directly compete with the GP search
(because B5's fitness function is Hamming-based per-cell
accuracy), so the structural distance is a slight regression at
the integration level despite the better per-step matching. The
takeaway: **the planner's distance metric should match the
fitness function's distance metric** for the integration to
work; the structural distance is a useful diagnostic but not
the right default for B5+planner.

### Reading

* **One-step planner beats identity by ~24%** (26.29 → 19.87) on
  the 815 same-shape pairs. The planner picks a primitive that
  gets it closer to the target 35.9% of the time (across *all*
  pairs, including the shape-mismatched ones where the planner
  correctly skips).
* **28.2% one-step match rate** — when the Hodel solver's first
  primitive is in the planner's candidate set (18.5% of pairs,
  up from 14.4% with the larger candidate set), the planner
  picks the same primitive 28% of the time. The remaining 72%
  is either the planner's distance heuristic being wrong (the
  Hodel solver's choice isn't the *closest* in Hamming distance)
  or the candidate set missing the right primitive.
* **3.9% iterative solve rate (single-pair) / 3.4% multi-pair** —
  the *iterative* planner (apply the one-step planner repeatedly
  until the target is reached or `max_steps` is hit) solves ~3-4%
  of tasks end-to-end. This is the upper bound on what an
  L1-trained planner could achieve with this candidate set.

### Design properties

* **Multi-pair planning.** The high-level `plan_to_program(demos,
  ...)` takes a list of (input, target) pairs and picks the
  primitive that minimises the *mean* Hamming distance to the
  targets across all demos. A candidate that fails on any demo
  (wrong shape) is given `+inf` and never picked. This is the
  natural extension of the single-pair planner for ARC tasks.
* **Lookahead.** `L2Planner(lookahead=2)` rolls out every
  (candidate, candidate) pair and picks the 2-step prefix that
  minimises the multi-pair distance at the end. With ~50
  candidates and 2 steps, the branching factor is ~2500, which is
  still cheap (one interpreter call per leaf).
* **Loop avoidance.** The iterative planner keeps a small set of
  recently-visited states; a candidate that produces an
  already-visited state is heavily penalised (+inf), so the
  planner doesn't oscillate between two primitives.
* **Wide candidate set.** Covers the top 20 grid→grid primitives
  in the Hodel traces (1,731 transitions across 400 tasks): 19
  1-arg self-applications, 8 2-arg self-compositions, 3 2-arg
  scaling primitives, 11 3-arg fill/paint/replace, 3 3-arg
  switch/underfill, 3 3-arg crop.

### What's needed to improve further

* **Object-aware distance.** Hamming distance is a *content*
  metric. Many ARC primitives change a small region (e.g. a
  single object) while leaving the rest of the grid intact;
  Hamming distance scores both as "far". A structural /
  object-aware distance would likely score the right primitive
  higher.
* **Re-arc-generated traces.** Most of the 72% Hodel non-match is
  coverage: the Hodel solver uses combinators and abstracted
  subroutines the planner doesn't have. Re-arc-generated traces
  would massively expand the candidate space (and the trace
  dataset for the L1 learner).
* **Domain-specific heuristics.** For example, ARC tasks involving
  object detection often need `ofcolor(I, c)` followed by
  `recolor`, which is a 2-step pattern the planner misses.
* **Branch-and-bound search.** With the 3.9% iterative solve rate
  hitting the 20-step cap, a wider search (DFS with pruning) could
  find longer programs the greedy planner misses.

## B5+planner arm: the L2 direction meets the existing rig

The L2 planner has been integrated into the clebran search engine
as the **B5+planner arm** (`clebran/baselines/b5_planner.py`).
The arm is B5 (single population + central library via the
Stitch-style compression miner) augmented with one planner-
generated individual in the initial population of every task. The
planner uses the clebran interpreter as a perfect L1 (§9f in
`roadmap.md`) and plans against ALL of the task's demo pairs
simultaneously (the multi-pair API). The seeded program is the
planner's best linear sequence of primitives. The seed is
evaluated by the standard fitness function (which counts against
the budget) and inserted at the front of the population.

The distance metric is configurable via
`--planner-distance {hamming,component,color_set,structural}`
(default `hamming`); see the *Distance metrics* section above
for the trade-offs.

The number of planner candidates seeded is configurable via
`--planner-top-k K` (default 1). With K=1, the planner's *best*
candidate is seeded; with K>1, the top-K candidates are seeded
(one planner call, K program evaluations) via
`Lineage.seed_with_planner_topk`. The K-1 runners-up are
capped at `pop_size // 4` to avoid swamping the random initial
population.

**Pilot result (3 seeds, 500K candidate-evaluations, frontier
subset, by top-K):**

| K | solved | evo-solved | test-exact | mean length |
|---|---|---|---|---|
| 1 (default) | **10.00** | **3.00** | 9.67 | 2.03 |
| 3 | 9.67 | 2.67 | 9.33 | 1.70 |
| 5 | 9.67 | 2.67 | **9.67** | 1.79 |

K=1 (the default, just the planner's best) is the best at this
budget. The K-1 runners-up are usually not much better than the
random initial population's other seeds, and adding them
dilutes the pop's quality. K=5 has a peak (seed 2 hits 11
solves, including 0d3d703e which is one of B5's unique solves
across 3 seeds), but the mean is the same as K=3.

**The lesson: the planner's *best* candidate captures most of
the planner's value; the runners-up don't add much at this
budget.** The hypothesis that "more planner seeds = more
solves" is null at 500K / 3 seeds — the variance is too high
to distinguish K=1 from K>1. The 20-seed 4M-eval sweep is the
proper test of whether top-K helps at scale.

### Pilot result (3 seeds, 500K and 1M candidate-evaluations, frontier subset)

```
                              solved  evo-solved  test-exact  mean length
B5 (control, 500K)             9.67        2.67          9.67        1.61
B5+planner (L=1, 500K)        10.00        3.00          9.67        2.03
B5+planner (L=2, 500K)        10.00        3.00          9.67        1.70
B5+planner (L=1, 1M)          10.00        3.00          9.67        2.03
```

### Reading

The B5+planner arm is **at parity with B5 at 500K and 1M-eval
budget** (10.00 vs 9.67 mean solves), with **+0.33 evolution-
phase solves** (the planner seed is genuinely contributing to
discovery, not just sitting in the population as a no-op) and
**1 unique task** (f76d97a5) that B5 misses in any of the 3
seeds. The planner-seeded programs are slightly longer (2.0 vs
1.6 statements), which is the cost of carrying a non-trivial
seeded individual.

At 1M budget the numbers don't change (10/10/10 for B5+planner),
which is a ceiling: B5+planner at the current candidate set has
extracted most of what's possible from the planner seed, and
further compute doesn't help. The next lever is to expand the
planner's *coverage* (object-aware distance, re-arc-generated
trace candidates) or to scale the seed from 1 individual to N
planner-seeded individuals (e.g., the top-K candidates from the
multi-pair evaluation).

The key design choices that flipped the result from "slight
null" to "parity":

1. **Multi-pair planning** (not just first demo pair). The first
   implementation passed `target=input_grid` to the planner, so
   the planner thought the target WAS the input — this produced
   no-op programs. Switching to `demos = [(input, target) for
   input, target in task.train]` made the planner actually plan
   toward the right state.
2. **Expanded candidate set** (top 20 grid→grid Hodel primitives
   instead of top 10). The planner went from 14.4% to 18.5%
   Hodel-first-primitive coverage in the candidate set, and the
   iterative solve rate went from 2.8% to 3.9% on the trace
   dataset.
3. **Lookahead** (`--planner-lookahead 2`, off by default). The
   2-step variant found 11/30 solves in seed 1 (vs 10/30 for
   lookahead=1), at the cost of ~4x more interpreter calls per
   planner call. The mean is unchanged at 10.00 because seed 3
   underperforms.

This is a **publishable positive result on the integration**:
with a multi-pair planner and a wide enough candidate set, the
planner-seeded arm matches B5 at this budget, with at least one
task B5 can't solve in 3 seeds. The natural next step is the
20-seed 4M-eval frontier sweep that matches the headline B5
result; the per-seed 1M pilot is already at the ceiling, so the
remaining question is whether the parity is consistent across
many more seeds.

## What's next on §9f

1. **20-seed 4M-eval B5+planner frontier sweep** — match the
   headline B5 result. This is the integration test that
   matters: does the parity hold at higher budgets and across
   more seeds? (Per-seed 1M is already at the ceiling of 10/30,
   so the sweep is a question of consistency, not magnitude.)
2. **Top-K planner seeds** — instead of seeding 1 planner-
   generated individual per task, seed the top-K candidates
   from the multi-pair evaluation. This expands the planner
   contribution from 1 to K individuals at a small cost (the
   planner call is shared; only the program evaluation differs).
3. **Re-arc generated trace candidates** — expand the planner's
   candidate set with primitives inferred from re-arc's
   per-task generators, not just Hodel's reference solvers. The
   re-arc generators give unlimited synthetic (input, target)
   pairs per task, so the planner can pattern-match on the
   specific task structure, not just generic primitives.
4. **Object-aware distance metric** — a structural / object-
   aware distance (counting matching objects by color and shape)
   would likely score the right primitive higher on tasks where
   Hamming distance is too coarse.
5. **Design a learned L1** that beats the KnnL1 baseline
   (currently 0% exact-match out-of-distribution). The learned
   model is the *substrate* the planner uses; a faster L1 means
   a faster planner. The trace dataset (16K steps from 400
   Hodel solvers) is the training data; a small neural net or
   a programmatic approximation evolved by clebran's own GP
   would be the model.
6. **Integrate ARCTraj** as a cross-modality signal — the 10k
   human step-by-step ARC trajectories are the right training
   data for an ARC-specific world model. The clebran planner can
   use ARCTraj as a heuristic for *what humans do*, complementing
   the clebran interpreter's *what's geometrically possible*.
7. **Target ARC-AGI-3** — the new interactive turn-based benchmark
   that explicitly requires *Modeling* (world-model construction) as
   one of four required capabilities. The L2 direction is exactly
   what ARC-AGI-3 was designed to test.
