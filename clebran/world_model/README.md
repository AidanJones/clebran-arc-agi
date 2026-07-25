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

```
demo pairs evaluated:        1302
(finite-distance pairs:        815)   # pairs where input shape = target shape
identity  mean distance:     26.29
planner   mean distance:     21.62   # 18% reduction
planner improves over identity: 320 / 1302 = 24.6%
Hodel first primitive in candidate set: 188
planner matches Hodel (when in candidate set): 57 / 188 = 30.3%
iterative planner (max 20 steps) solves: 26 / 815 = 3.2%
```

### Reading

* **One-step planner beats identity by ~18%** (26.29 → 21.62) on the
  815 same-shape pairs. The planner picks a primitive that gets it
  closer to the target 24.6% of the time (across *all* pairs,
  including the shape-mismatched ones where the planner correctly
  skips).
* **30.3% one-step match rate** — when the Hodel solver's first
  primitive is in the planner's candidate set (14.4% of pairs), the
  planner picks the same primitive 30% of the time. The remaining
  70% is either the planner's distance heuristic being wrong (the
  Hodel solver's choice isn't the *closest* in Hamming distance)
  or the candidate set missing the right primitive.
* **3.2% iterative solve rate** — the *iterative* planner (apply
  the one-step planner repeatedly until the target is reached or
  `max_steps` is hit) solves 26 out of 815 tasks end-to-end by
  naive one-step greedy planning with a fixed candidate set. This
  is a meaningful baseline: the upper bound on what an L1-trained
  planner could achieve with this candidate set.

### What's needed to improve

* **Larger candidate set.** Most of the 70% Hodel non-match is
  coverage: the Hodel solver uses primitives the planner doesn't
  have (combinators, higher-arity compositions, abstracted
  subroutines). Re-arc-generated traces would massively expand
  the candidate space.
* **Better distance metric.** Hamming distance is a *content*
  metric. Many ARC primitives change a small region (e.g. a
  single object) while leaving the rest of the grid intact;
  Hamming distance scores both as "far" because the whole grid
  is in the metric. A structural / object-aware distance would
  likely score the right primitive higher.
* **Multi-step lookahead.** The greedy planner commits to the
  best next step; a 2-3 step lookahead would catch cases where
  the *first* best move is wrong but a different first move
  leads to a much better second state.
* **Loop avoidance.** The iterative planner can cycle between
  primitives. A visited-states cache or a tabu list would fix
  this.

## B5+planner arm: the L2 direction meets the existing rig

The L2 planner has been integrated into the clebran search engine
as the **B5+planner arm** (`clebran/baselines/b5_planner.py`).
The arm is B5 (single population + central library via the
Stitch-style compression miner) augmented with one planner-
generated individual in the initial population of every task. The
planner uses the clebran interpreter as a perfect L1 (§9f in
`roadmap.md`); the seeded program is the planner's best linear
sequence of primitives. The seed is evaluated by the standard
fitness function (which counts against the budget) and inserted
at the front of the population.

### Pilot result (3 seeds, 500K candidate-evaluations, frontier subset)

```
                   solved  evo-solved  test-exact  mean length
B5 (control)         9.67        2.67          9.67        1.61
B5+planner (L2)      9.33        2.33          9.33        1.73
```

### Reading

The B5+planner arm is a **slight null at 500K-eval budget**:
0.33 fewer solves, 0.33 fewer evo-solves, and slightly longer
mean programs (the planner's seed is longer than what B5's
phase-1 systematic closure finds). At a 1M budget the gap
narrows (seed 1 ties at 10/30).

This is a publishable negative result on the **integration**:
the planner's perfect-L1 seed is not a *better* seed than
B5's phase-1 systematic closure at this budget and candidate
set. The planner is not *broken* — it produces valid programs
(3.2% iterative solve rate, 30% one-step match rate) — but its
seed is a slightly worse starting point for the GP than B5's
own systematic closure.

The next step on this direction is to improve the planner
itself (larger candidate set, better distance, lookahead, loop
avoidance) and re-test the arm. The planner is the right
*substrate* for a learned L1 to be plugged into; the integration
is already built.

## What's next on §9f

1. **Improve the L2 planner** — better candidate set (re-arc
   generated), better distance metric (structural / object-aware),
   2-3 step lookahead, loop avoidance. Re-test the B5+planner arm
   on the 20-seed 4M-eval frontier sweep.
2. **Design a learned L1** that beats the KnnL1 baseline
   (currently 0% exact-match out-of-distribution). The learned
   model is the *substrate* the planner uses; a faster L1 means
   a faster planner.
3. **Integrate ARCTraj** as a cross-modality signal — the 10k
   human step-by-step ARC trajectories are the right training
   data for an ARC-specific world model. The clebran planner can
   use ARCTraj as a heuristic for *what humans do*, complementing
   the clebran interpreter's *what's geometrically possible*.
4. **Target ARC-AGI-3** — the new interactive turn-based benchmark
   that explicitly requires *Modeling* (world-model construction) as
   one of four required capabilities. The L2 direction is exactly
   what ARC-AGI-3 was designed to test.
