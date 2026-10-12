# A1 — #5 Learned L1 as proposer (analysis)

**Question.** Does injecting trace-dataset-derived first-step
primitives into B5's initial population expand B5's reach on the
30-task frontier subset at 1M × 5 seeds?

**Answer (v1, geometric-only).** **No.** B5L1 = 10.00 ± 0.32
frontier solves (5 seeds: 9, 10, 11, 10, 10) vs B5 = 10.40 ± 0.51
(delta = -0.40, within noise). Evo-solved: B5L1 = 2.80 ± 0.37 vs
B5 = 3.20 ± 0.37 (delta = -0.40). Test-exact: B5L1 = 10.00 vs
B5 = 10.20. **v1 is null.**

## Headline numbers (5 seeds, 1M eval budget, 30-task frontier subset)

| metric (1M, 5 seeds) | B5L1 (L1 proposer + B5) | B5 (control) | delta |
|---|---|---|---|
| frontier solves / 30 | 10.00 ± 0.32 | 10.40 ± 0.51 | -0.40 |
| evo-solved / 30 | 2.80 ± 0.37 | 3.20 ± 0.37 | -0.40 |
| test-exact / 30 | 10.00 ± 0.32 | 10.20 ± 0.37 | -0.20 |

## Per-seed frontier solves

| seed | B5L1 | B5 | delta |
|---|---|---|---|
| 1 | 9 | 10 | -1 |
| 2 | 10 | 10 | 0 |
| 3 | 11 | 9 | +2 |
| 4 | 10 | 11 | -1 |
| 5 | 10 | 12 | -2 |

## Per-task overlap (any seed)

* Tasks solved by any B5L1 seed: **12** (`5582e5ca`, `5614dbcf`,
  `5bd6f4ac`, `6150a2bd`, `6d0aefbc`, `9172f3a0`, `a416b8f3`,
  `b1948b0a`, `d10ecb37`, `dc0a314f`, `ed36ccf7`, `f76d97a5`).
* Tasks solved by any B5 seed: **13** (`0d3d703e`, `1f85a75f`,
  `5582e5ca`, `5614dbcf`, `5bd6f4ac`, `6150a2bd`, `6d0aefbc`,
  `9172f3a0`, `a416b8f3`, `b1948b0a`, `d10ecb37`, `dc0a314f`,
  `ed36ccf7`).
* **Overlap: 11 / 13** (84.6%).
* **Unique to B5L1: 1** (`f76d97a5`).
* **Unique to B5: 2** (`0d3d703e`, `1f85a75f`).

## Reading

* The proposer is contributing — there is one task (`f76d97a5`)
  that B5L1 solves and B5 does not.
* But it's also *cannibalising* the random initial population's
  exploration: B5L1 misses `0d3d703e` and `1f85a75f` that B5 finds.
  The L1-proposer seeds (3 per task, 30 tasks = 90 candidates) are
  displacing ~30 random initial programs from each task's phase-1
  closure, costing exploration diversity.
* The net effect at 1M × 5 seeds is a *small* negative (-0.40
  frontier solves), well within the B5 SE of 0.51.

## Why v1 is null

The v1 proposer is restricted to **geometric** primitives
(`vmirror`, `hmirror`, `rot90/180/270`, `cmirror`, `dmirror`,
`top/bottom/left/righthalf` — 11 primitives). These are *also*
already enumerated by B5's phase-1 closure
(`seed_population → enumerate_depth1 → enumerate_depth2`), so the
proposer is adding primitives that the random search would have
found anyway, just *earlier* in the budget.

For the geometric case, the v1 proposer's only effect is to
*shorten* the time-to-first-solve on those tasks; it doesn't
expand the set of tasks B5 can solve at the 1M horizon.

## What v1 *would* need to look like to be positive

A meaningful L1-as-proposer arm needs to inject programs that
B5's phase-1 closure **cannot** reach. There are two such
classes:

1. **Combinator / higher-order primitives** (`fork`, `compose`,
   `lbind`, `rbind`, `apply`, `mapply`, `pipe`, `chain`,
   `branch`, `sfilter`, `merge`, ...) — 126 of the 151 primitives
   in the trace dataset are NOT in the L2 planner's
   `_default_candidates` (per the scoping pilot at
   [`experiments/2026-10-07_l1_proposer_scoping/`](../../2026-10-07_l1_proposer_scoping/)).
   These require functional arg inference (which function to pass
   to `fork`, etc.) and their default args are task-specific.
2. **Multi-step program prefixes** (2-3 statement programs) that
   the L1 has seen across 400 reference solvers. The L1's
   generalisation is "after `vmirror`, often comes `fill(I, mc)`",
   not just "first step is `vmirror`". v1 only injects
   1-statement programs, so it never sees the
   `vmirror → fill(mc)` pattern.

The natural v2 experiment would (a) extend the proposer to
combinator primitives, (b) inject 2-3 step program prefixes, and
(c) re-run at 1M × 5 seeds.

## Implication for A1

v1 of the L1-as-proposer is **null** at 1M × 5 seeds. The result
is *consistent* with the discovery-bottleneck menu's pattern
(0-for-4 at 1M): no mechanism operating inside the current
DSL/interpreter/fitness has expanded B5's reach.

**However:** v1 is a deliberately narrow experiment (geometric
primitives only, 1-statement programs only). A v2 extending to
combinator primitives + multi-step prefixes is a *different
mechanism* and worth a separate pilot before declaring A1
closed. If v2 is also null, the L1-as-proposer arm closes
structurally and the right next move is A2 (operator
self-modification).

## Frozen data

* B5L1 logs: `logs/b5l1_seed{1..5}.jsonl`.
* B5 (control) logs: `logs/b5_1m_seed{1..5}.jsonl` (from the
  discovery-bottleneck menu pilots, frozen 2026-08-31 to
  2026-09-24).
* Scoping pilot: [`experiments/2026-10-07_l1_proposer_scoping/`](../../2026-10-07_l1_proposer_scoping/).
* Source: `clebran/baselines/b5_l1_proposer.py`,
  `clebran/world_model/l1_proposer.py`.