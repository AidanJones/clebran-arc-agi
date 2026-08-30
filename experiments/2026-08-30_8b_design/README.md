# 8b design: negative transfer test (skeleton, not yet run)

Roadmap §8b: "Teach concept family A → test on tasks requiring
disjoint family B → compare against an untaught control at matched
compute. All three outcomes are informative (generalises / inert
off-distribution / causes rigidity). If taught < control, that is
the most important scoping result available."

This file is the design — implementation requires the 4M B5D library
from the 4M dreaming pilot (currently running in the background).

## Setup (planned)

The 9b result gives a natural A and B:

- **A** — the 10–11 frontier tasks the B5D dreaming lineage solved
  (its dream-task pool is the variant distribution built from these).
- **B** — the 20–21 frontier tasks the B5D dreaming lineage did *not*
  solve, ideally requiring disjoint primitives (filtered to be
  vocabulary-disjoint from A by the primitives the A-solutions use).
- **Library** — the B5D mining pass at 4M produces ~10–15 abstractions,
  70% used, 5+ reused. This is what we transfer.

### Three arms (matched compute, frontier subset, 4M × ≥5 seeds)

1. **Cold B5** (the existing baseline).
2. **B5 + B5D-library** — fresh B5 with the B5D-mined abstractions
   preloaded as *received* (analogous to B6/B7's `payload="abstraction"`
   channel), `score=0` so the order-aware learner has no prerequisite
   gating.
3. **B5 + B5-library** (sanity check) — fresh B5 with B5's own
   abstractions preloaded. Should be ~inert vs cold (same library,
   just preloaded).

### Endpoint

- B-task solves /30 (the headline).
- B-task evals-to-solve (cost axis, the 9a endpoint).
- Library stats on B: topsim, cross-task reuse, mean body size.
- Cold-vs-taught paired t-test on per-seed B-task solves.

### Three informative outcomes

1. **B5+B5D-library > cold** → dreaming library generalises to
   disjoint tasks. Library is a portable compression of competence.
2. **B5+B5D-library = cold** → library is inert off-distribution. No
   effect, no harm.
3. **B5+B5D-library < cold** → **negative transfer**. The
   task-idiomatic library biases search toward patterns that don't
   fit B. The most informative outcome — it would explain why
   dreaming *didn't* help at 1M and *might still* not help at 4M.

## Why this matters here

The 1M B5D pilot showed the dreaming's library is *task-idiomatic*
(topsim 0.05 vs B5's 0.26 — 5× lower). If that library *also*
*negatively* transfers to disjoint tasks, we have a sharp result:
**dreaming produces a library that is good for the tasks it
generated on, but inert or harmful on tasks it didn't see.** That
would be a *real* scoping result — the dreaming's value is bounded
to its own task distribution, and the broader "dreaming improves
search" claim fails on the disjoint case.

## What the B5+library sanity check is for

Without the B5-library arm, a positive B5+B5D-library vs cold result
could mean:
- (a) B5D's library genuinely helps.
- (b) Any preloaded library helps (the "library as warm start"
  effect).

The B5-library arm is the *transfer-function* control: B5's own
library is structurally similar to B5D's (same miner, same number
of abstractions) but matched to a different search trajectory. If
B5+B5-library > cold too, then (b) is the explanation. If
B5+B5-library ≈ cold but B5+B5D-library > cold, then (a) is the
explanation — B5D's library genuinely helps.

## Implementation plan

1. **Wait for 4M B5D pilot** to finish (10 seeds, ~3.5 hours wall clock).
2. **Extract B5D's mined library** from `abstraction_stats` in the
   summary record (or directly from `lin.abstractions` if we add
   the abstraction bodies to the log).
3. **Build a "B5+B5D-library" arm** that takes a library JSON
   and initializes `Lineage` with those abstractions.
4. **Run** cold B5 / B5+B5D-library / B5+B5-library on 5+ seeds
   × 4M on the B tasks only.
5. **Compare** B-task solves and evals-to-solve.

Total wall clock: ~3 hours for 5 seeds × 3 arms at 4M. Fits in a
half-day session.

## Open design question

**How to define B?** The cleanest is "tasks the B5D lineage never
solved, vocabulary-disjoint from A". A heuristic:
- Take the B5D lineage's 10-11 solved tasks (A).
- Find the primitives used by their solutions.
- Filter the remaining 19-20 tasks to those using disjoint
  primitives.
- If too few (or too many) remain, relax the disjointness
  criterion.

Alternative: use the 4M B5 baseline's solved set as a reference
for "disjoint" — pick B-tasks as those B5@4M solves but B5D@4M
does not (and vice versa). This is empirical rather than
vocabulary-based.

The empirical version is simpler and uses the data we already
have. The vocabulary version is more principled. For a first
8b, empirical is fine.
