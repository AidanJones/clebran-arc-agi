# A3 (first concrete test) — B5 + L1-rollout planner (analysis)

**Question.** Does using a learned L1 (GPL1) as the L2 planner's
rollout engine, instead of the perfect clebran interpreter, let
B5 reach more frontier tasks at 1M × 5 seeds? (paper 3 §6
"next push": the learned L1's job is to be a *fast approximation
of the perfect L1*, with a tolerable accuracy loss in exchange
for rollout speed.)

**Answer (v1, hybrid L1-then-interpreter).** **No — null with
noise.** B5L1P = 10.20 ± 0.20 frontier solves (5 seeds:
10, 10, 10, 11, 10) vs B5 = 10.40 ± 0.51 (delta = -0.20, well
within the B5 SE of 0.51). Evo-solved: B5L1P = 3.00 ± 0.32 vs
B5 = 3.20 ± 0.37 (delta = -0.20). Test-exact: B5L1P = 10.00 ±
0.32 vs B5 = 10.20 ± 0.37 (delta = -0.20). **The L1 rollout is
competitive on average, but does not expand B5's reach.**

## Headline numbers (5 seeds, 1M eval budget, 30-task frontier subset)

| metric (1M, 5 seeds) | B5L1P (B5 + L1-rollout planner) | B5 (control) | delta |
|---|---|---|---|
| frontier solves / 30 | 10.20 ± 0.20 | 10.40 ± 0.51 | -0.20 |
| evo-solved / 30 | 3.00 ± 0.32 | 3.20 ± 0.37 | -0.20 |
| test-exact / 30 | 10.00 ± 0.32 | 10.20 ± 0.37 | -0.20 |

## Per-seed frontier solves

| seed | B5L1P | B5 | delta |
|---|---|---|---|
| 1 | 10 | 10 | 0 |
| 2 | 10 | 10 | 0 |
| 3 | 10 | 9 | +1 |
| 4 | 11 | 11 | 0 |
| 5 | 10 | 12 | -2 |

## Per-task overlap (any seed)

* Tasks solved by any B5L1P seed: **12** (`5582e5ca`, `5614dbcf`,
  `5bd6f4ac`, `6150a2bd`, `6d0aefbc`, `9172f3a0`, `a416b8f3`,
  `b1948b0a`, `d10ecb37`, `dc0a314f`, `ed36ccf7`, `f76d97a5`).
* Tasks solved by any B5 seed: **13** (`0d3d703e`, `1f85a75f`,
  `5582e5ca`, `5614dbcf`, `5bd6f4ac`, `6150a2bd`, `6d0aefbc`,
  `9172f3a0`, `a416b8f3`, `b1948b0a`, `d10ecb37`, `dc0a314f`,
  `ed36ccf7`).
* **Overlap: 11 / 13** (84.6%).
* **Unique to B5L1P: 1** (`f76d97a5`).
* **Unique to B5: 2** (`0d3d703e`, `1f85a75f`).

## Comparison to A1 v1 (L1-as-proposer)

| arm | frontier solves / 30 | evo-solved / 30 | unique tasks |
|---|---|---|---|
| B5 (control) | 10.40 ± 0.51 | 3.20 ± 0.37 | 2 |
| A1 B5L1 (L1-proposer, geometric) | 10.00 ± 0.32 | 2.80 ± 0.37 | 1 |
| A3 B5L1P (L1-rollout planner) | 10.20 ± 0.20 | 3.00 ± 0.32 | 1 |

The L1-rollout-planner (A3) is slightly *better* than the
L1-proposer (A1) on the same 1M × 5 seeds, but both are within
noise of B5. The L1-as-rollout-engine hypothesis (paper 3 §6
"next push") is **not** supported at 1M × 5 seeds.

## Reading

* The L1 rollout is *fast but imperfect*. The GPL1 has 35
  learned programs (vmirror, hmirror, rot*, cmirror, dmirror,
  bottomhalf, cellwise, paint, replace, plus 2/3-arg primitives
  with shape-perfect but value-imperfect predictions), but
  overall OOD accuracy is only 25.6% exact / 43.0% shape-match
  (per the scoping pilot at
  [`experiments/2026-10-07_l1_proposer_scoping/`](../../2026-10-07_l1_proposer_scoping/)).
  For the L2 planner's candidate set, the L1 is *correct* on
  the geometric primitives but *value-imperfect* on the
  compositional primitives (fill, paint, replace, hconcat,
  vconcat, scaling) — so the planner's ranking is
  shape-correct but value-imperfect, which is enough to keep
  B5L1P from regressing but not enough to beat B5P or B5.
* The B5+planner arm (B5P, perfect interpreter rollout) is
  null at 4M (paper 3, 20 seeds: B5 12.45 ± 1.15 vs B5P 12.35 ±
  0.99, mean delta −0.10, t = 0.26). The B5+planner arm is
  positive at starved-GP budgets (500K-1M) and null at the
  headline 4M budget. At 1M × 5 seeds, B5P ≈ B5 (within noise),
  and B5L1P ≈ B5P ≈ B5 — the L1 rollout's accuracy loss
  doesn't break the null.
* The L1 rollout's speedup (GPL1 lookup vs interpreter call)
  is real but small. The planner is called once per task per
  seed, so the per-task speedup is at most a few seconds. The
  L1 build is 15-30s (vs ~0s for the interpreter), which
  *costs* more than it saves at this scale. The arm is slightly
  slower than B5L1 (the proposer arm, which doesn't call the
  planner at all) but competitive in frontier solves.

## Why A3 v1 is null

* The L1's value-perfection is the bottleneck. The planner's
  ranking is computed by Hamming distance from the L1's
  predicted `next_state` to the target. If the L1's prediction
  is shape-correct but value-imperfect (e.g. predicts a
  `vmirror` of an input but with the wrong colors), the
  Hamming distance is high even when the right primitive is
  chosen. The planner then can't pick the right primitive.
* The L1's coverage is also limited. The 35 primitives the
  L1 has learned include the geometric primitives (which the
  L1 gets 100% on) and some 2/3-arg primitives (which the L1
  gets shape-perfect but value-imperfect on). The
  compositional primitives that the L2 planner's
  `_default_candidates` uses most heavily (fill, paint,
  replace, hconcat, vconcat, scaling) are *not* in the L1's
  coverage — so the L1 rollout silently falls through to the
  interpreter on those calls, giving no speedup.
* The B5+planner arm is already null at 4M. The L1 rollout
  is a *fast* approximation of the planner, not a different
  mechanism. If the planner is null, the L1-rollout planner
  is null too.

## What v1 leaves open

A3 v1 is a fast L1 rollout that *trades accuracy for speed*
within the existing planner architecture. The hypothesis in
the README said "if null, extend the L1's coverage to
multi-arg primitives". That extension is a multi-week R&D
effort: a new L1 (e.g. a small neural net or a more
sophisticated programmatic L1) that handles the 2/3-arg
primitives the L2 planner uses.

A simpler interpretation is that A3 (the L1-as-rollout-engine
direction) is *not* the unlock for the discovery bottleneck.
The discovery-bottleneck menu is now 0-for-4 (A1 null) plus
0-for-1 (A3 v1 null) = 0-for-5 at 1M. The structural-change bet
is closing.

## Frozen data

* B5L1P logs: `logs/b5l1p_seed{1..5}.jsonl`.
* B5 (control) logs: `logs/b5_1m_seed{1..5}.jsonl` (frozen
  2026-08-31 to 2026-09-24 from the discovery-bottleneck
  menu pilots).
* A1 v1 logs: `logs/b5l1_seed{1..5}.jsonl` (the geometric-only
  L1-proposer, null at 1M × 5 seeds, see
  [`experiments/2026-10-07_a1_l1_proposer/`](../../2026-10-07_a1_l1_proposer/)).
* Scoping pilot: [`experiments/2026-10-07_l1_proposer_scoping/`](../../2026-10-07_l1_proposer_scoping/).
* Source: `clebran/baselines/b5_l1_planner.py`,
  `clebran/world_model/l1_rollout.py`,
  `clebran/world_model/l2_planner.py` (added `rollout_fn`),
  `clebran/lineage.py` (added `planner` parameter to
  `seed_with_planner` and `seed_with_planner_topk`),
  `clebran/baselines/arms.py` (registered B5L1P).

## Implication for the menu

A3 v1 (L1-as-rollout-engine) is null. Combined with A1 v1
(L1-as-proposer, also null), the L1-related bets are 0-for-2.
Paper 4's roadmap says: *"If #5–#7 also return null, the menu
closes and the right next move is to bring in a genuinely
new substrate (ARCTraj, ARC-AGI-3) — not to keep attacking the
same DSL with new mechanisms."*

The next bet is **A2 — #6 Operator self-modification**
(roadmap §A2, ~2 weeks). A2 lets the lineage modify its own
mutation / crossover operators — a structural change to the
rig. If A2 is also null, the menu closes and the right move
is a new substrate.

Alternatively, a **3rd pilot of the L1 direction**: extend
the L1 to multi-arg primitives (hconcat, vconcat, scaling,
fill, paint, replace with default args) via a more
sophisticated programmatic L1 or a small neural L1. This is
the A3 v2 experiment — multi-week R&D effort, with the
specific scope to be designed.