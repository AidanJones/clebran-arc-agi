# 2026-10-07 — L1-as-proposer scoping pilot

Pre-experiment check for **A1 — #5 Learned L1 as proposer** (roadmap
strand A, structural-change bet). The pilot was run on
2026-10-07 to answer: *does a learned L1 (GPL1) have enough signal to
re-rank the L2 planner's candidate primitives usefully?* If the L1
ranking is much worse than the perfect interpreter's, the L1-proposer
arm is unlikely to beat B5+planner; if it's comparable, the arm is
worth running at 1M × 5 seeds.

## Setup

* Trace dataset (`data/traces.jsonl`, 16,149 rows from 400 Hodel
  reference solvers).
* Frontier subset (`data/frontier_subset.json`, 30 tasks — held out
  from L1 training).
* Train/test split by task ID (not row).
* Train: 15,689 rows from 370 non-frontier tasks (1,645 grid→grid
  rows).
* Test: 460 rows from 30 frontier tasks (86 grid→grid rows).
* L1: `GPL1` (pop_size=50, n_generations=8, max_program_len=3,
  seed=0) trained on the train split. Evolution time: ~7.5s.

## Per-primitive OOD accuracy on the frontier subset

| primitive | exact | shape |
|---|---|---|
| **vmirror** | 17/17 = **100%** | 17/17 = 100% |
| **hmirror** | 5/5 = **100%** | 5/5 = 100% |
| bottomhalf | 0/3 = 0% | 3/3 = 100% |
| cellwise | 0/5 = 0% | 5/5 = 100% |
| paint | 0/4 = 0% | 4/4 = 100% |
| replace | 0/3 = 0% | 3/3 = 100% |
| hconcat | 0/19 = 0% | 0/19 = 0% |
| hupscale | 0/5 = 0% | 0/5 = 0% |
| lefthalf | 0/2 = 0% | 0/2 = 0% |
| tophalf | 0/5 = 0% | 0/5 = 0% |
| vconcat | 0/13 = 0% | 0/13 = 0% |
| vupscale | 0/5 = 0% | 0/5 = 0% |
| **TOTAL** | **22/86 = 25.6%** | **37/86 = 43.0%** |

**Reading.** GPL1 has perfect prediction on the pure-geometric
primitives (vmirror, hmirror), shape-perfect but value-imperfect
prediction on a handful of simple primitives (bottomhalf, cellwise,
paint, replace), and 0% on the multi-arg primitives (vconcat,
hconcat, scaling). The 25.6% / 43.0% overall numbers match the
18.7% / 52.7% reported in paper 3 (which used a random
train/test split — this pilot uses the frontier subset's specific
held-out tasks).

## Ranking test (Hodel's first-step primitive in `_default_candidates`)

For each frontier demo pair, generate the L2 planner's
`_default_candidates` for the first state, score each candidate by
(a) interpreter distance to target (perfect L1, the planner's
default) and (b) GPL1 distance to target, rank the candidates by each
scoring, and report the rank of Hodel's actual first-step primitive.

| ranking | #1 | ≤3 | ≤5 |
|---|---|---|---|
| **interpreter (perfect)** | 13/18 = **72%** | 13/18 = 72% | 13/18 = 72% |
| **GPL1 (learned)** | 10/18 = **56%** | 10/18 = 56% | 10/18 = 56% |

Only 18 demo first-step pairs across 5 frontier tasks had Hodel's
primitive in the candidate set (most frontier pairs use primitives
outside `_default_candidates` — see next section). The gap of 16
points reflects GPL1's imperfection on multi-arg primitives and the
small training set.

## Combinator gap: 25 of 151 trace primitives are in `_default_candidates`

The L2 planner's candidate set covers only 25 primitives. The 126
primitives NOT in the candidate set include the heavy hitters in the
trace dataset:

| primitive | trace count | in planner? |
|---|---|---|
| **fork** | 903 | ✗ |
| **compose** | 884 | ✗ |
| **lbind** | 757 | ✗ |
| **rbind** | 687 | ✗ |
| **objects** | 739 | ✗ |
| **ofcolor** | 592 | ✗ |
| **mapply** | 552 | ✗ |
| **apply** | 527 | ✗ |
| **chain** | 398 | ✗ |
| **astuple** | 378 | ✗ |
| **branch** | 286 | ✗ |
| **first** | 247 | ✗ |
| **sfilter** | 239 | ✗ |
| **merge** | 234 | ✗ |
| **canvas** | 224 | ✗ |
| **shift** | 193 | ✗ |
| **subgrid** | 184 | ✗ |

These are mostly higher-order / combinator primitives (fork,
compose, apply) and object-extraction primitives (objects, ofcolor).
Hodel solvers do `ofcolor(I, c)` → `fill(I, ...)` → ... very often;
the planner's `_default_candidates` only has `fill` as a primitive
call with default args, not `ofcolor`.

## Implication for A1

A pure "use GPL1 to re-rank `_default_candidates`" L1-proposer is
expected to underperform the L2 planner's interpreter-based
ranking by ~16 pp on geometric tasks and to *fail* to rank 2/3-arg
primitives at all. So a straight re-ranker is unlikely to beat
B5+planner.

The interesting A1 angle is the **combinator gap**. The L1-proposer
arm should:

1. Inject Hodel's heavy-hitter combinator primitives (fork,
   compose, lbind, rbind, apply, mapply, ofcolor, objects, ...) as
   seeds, even though they're not in `_default_candidates`.
2. Inject 2-step program prefixes that combine the combinator with
   the geometric primitive (e.g., `objects((I, x)) → fork(fn, fill, identity)(I)`).
3. Compare B5 vs B5+L1-proposer at 1M × 5 seeds.

This is a more substantial experiment than the scoping pilot — it
expands the candidate set the L1-proposer draws from rather than
just re-ranking the existing one. See
[`scripts/scoping_l1_proposer.py`](../../scripts/scoping_l1_proposer.py)
for the scoping pilot; the A1 arm itself lives at
`clebran/baselines/b5_l1_proposer.py` (forthcoming).