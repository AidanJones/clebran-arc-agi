# 4. Hypotheses, baselines, and experimental protocol

The clebran design tests three sub-hypotheses of the central claim
plus one extension. Section 4.1 states them precisely; §4.2 maps
each to one or more arms; §4.3 specifies the match-compute protocol;
§4.4 describes the subsets; §4.5 the statistical convention.

## 4.1 Sub-hypotheses

**H1 (divergence).** Independently-seeded lineages under pure reward
discover genuinely different abstractions for the same task
distribution. *Measurable:* pairwise Jaccard distance over primitive
usage; fraction of tasks solved by exactly one lineage in the
multi-lineage arms.

**H2 (transfer helps).** Sharing successful subprograms between
lineages increases total solve count at matched compute, relative
to not sharing. *Measurable:* the B2 (fragment channel) − B1
(isolated) comparison, and analogous comparisons for B6, B8, B9.

**H3 (the constraint matters).** A bandwidth-limited channel
preserves better or more reusable abstractions than an unconstrained
"dump the whole library" channel. *Measurable:* the B2 − B3
comparison, the B6 − B7 comparison, the B8 − B9 comparison, and the
K×M dose-response ladder.

**§11 (recovered > given).** Sharing subroutines a lineage has
*mined for itself* outperforms sharing raw fragments over Hodel's
given primitives. *Measurable:* the B6 (recovered) − B2 (given)
comparison.

**§7b (curriculum-as-payload).** A teaching set — a sequence of
synthetic tasks that *show* what the sender learned — is a useful
alternative to sharing code. *Measurable:* the B8 (curriculum
constrained) − B1 comparison; the B8 vs B2/B6 comparisons on
identical compute.

A *central* comparison that is not strictly part of the original
hypothesis set but emerged as decisive is the B5 vs B6 comparison:
B5 is a single population that grows a central library by mining
its own solutions — the DreamCoder/Stitch control. If a
multi-agent-with-channel design is to win on this substrate, it
must beat the single agent that has the same library mechanism
without the divergence tax.

## 4.2 Arms

| arm | what it is | tests |
|---|---|---|
| B0 | single population, all compute | reference line |
| B1 | N isolated lineages, no channel (CH-NONE) | H1 baseline |
| B2 | N lineages + CH-CONSTRAINED fragment | H2, H3 (given) |
| B3 | N lineages + CH-UNCONSTRAINED fragment | H3 (given) |
| B4 | N lineages + CH-CONSTRAINED signal | abstract comms variant |
| B5 | single population + central library | *central-library control* |
| B6 | N lineages + CH-CONSTRAINED recovered-primitive | H2, H3 (§11) |
| B7 | N lineages + CH-UNCONSTRAINED recovered-primitive | H3 (§11) |
| B8 | N lineages + CH-CONSTRAINED curriculum | §7b (curriculum) |
| B9 | N lineages + CH-UNCONSTRAINED curriculum | §7b (curriculum) |

Multi-lineage arms use N = 3 lineages and 20% primitive-pool dropout
per lineage, ensuring divergence at the seed level. All arms are
run at matched candidate-evaluation budgets (§4.3) on the same
subset and the same seeds.

## 4.3 Matched-compute protocol

The compute unit is the *candidate evaluation*: every call to
`fitness.Evaluator` against a specific program and task, whether
the program is novel, deduped by the length-guarded cache, or
re-evaluated after a mutation, counts as one. The total budget per
run is the per-arm budget (`b` evals); the budget is split equally
between the N lineages of a multi-lineage arm (so the per-lineage
budget is `b/N` and the total is the same as the single-population
arm's).

A run is logged to `logs/<arm>_seed<...>.jsonl` as a `start` record
(the configuration), `solve` records (task, evals consumed, program
JSON, test-exact flag), `epoch` records (lineage state summaries
every K generations), and a final `summary` (solved sets,
per-lineage breakdowns, primitive-usage divergence, reuse rate,
messages published). Compute audits compare the *recorded
evaluations* of the multi-lineage arms to the budget and report
the per-arm spread. Audited spreads are ≤ 0.27% across all
multi-arm runs reported here; for the headline 20-seed frontier
runs the spread is 0.10%. Wall-clock is never used as a
comparator; the compute is metered inside `fitness.Evaluator`.

## 4.4 Subsets

Two subsets are used.

**Stage-1 subset.** 30 tasks generated deterministically by the
recipe in spec §4.1: 10 tasks at depth 1, 15 at depth 2, 5 at
depth 3, stratified by reasoning type (object-extraction,
geometry, recolouring, composition), each gated by successful
reproduction through our interpreter. Committed as
`data/stage1_subset.json`. This is the subset used in the Stage-4
B0–B4 sweep and the K×M dose-response.

**Frontier subset.** 25 D2 + 5 D3 tasks, depth-graded as the
Stage-1 subset, but chosen by the additional criterion that the
task is *not* solved by phase-1 systematic seeding on a B0 pilot
run. This is the subset used in the recovered-primitive and
curriculum channel experiments and the B5 central-library
control. Committed as `data/frontier_subset.json`. The frontier
subset is the one the paper reports, because the Stage-1 subset's
solvable frontier is shallow enough that phase-1 closes it
without communication — a feature that would mask any
channel-driven gain.

The depth proxy is the number of DSL primitive calls in Hodel's
reference solver, computed by `solver_parse.parse_all_solvers`.
D1 is depth ≤ 2 (1–2 statements), D2 is depth 3–5, D3 is depth
6–10. The pilot study that defined the frontier found that
genuine evolution-phase solves occur only in D2 at 2M evals
(seeds 1–2) — D3 is beyond reach and would just add a floor of
zeros, so the frontier is depth-2-dominated.

## 4.5 Statistics

For each arm, we report the mean and standard deviation of
*evolution-phase solves* across seeds. Evolution-phase solves are
the tasks reached by the evolutionary loop *after* the phase-1
seeding is complete, so the number reflects only what search (and
communication) contributed. Phase-1 is identical across arms, so
including it would only add a constant.

The standard error of a mean difference is the pooled standard
error: `sqrt(sd_a^2/n_a + sd_b^2/n_b)` for means of equal-sized
samples. We report a comparison as *significant* if the absolute
difference is at least 2.0 standard errors. We deliberately do
*not* use a t-test or a binomial test on the headline
comparisons because the solve counts are small (1–3 evolution
solves/seed) and the per-seed distributions are not normal. The
standard error is a *descriptive* statistic for the magnitude of
the effect, not a hypothesis-test p-value.

For the cost-to-solve comparisons in §5.7.1, we use a
permutation test (10 000 to 20 000 resamples) on the *paired*
differences between arms, restricted to the (target, seed) pairs
that were solved by both arms under comparison. The permutation
test does not require normality and is the right tool for the
small-n, paired, censored case. The permutation p-values are
reported alongside the observed differences.

## 4.6 What the experiment does *not* test

- **Other substrates.** The clebran design is scoped to ARC
  program synthesis over a hand-designed DSL. It does not test
  the channel hypothesis on language-model agents, robotic
  manipulation, or other multi-agent settings. The transfer of
  the negative result to those substrates is a question for
  future work.
- **The eval split.** All reported results are on the training
  split. The 400-task eval split is reserved for a follow-up
  generalisation test; it has not been touched in the reported
  experiments, and we flag it as a limitation in §7.
- **Compositional OOD.** The L2T compositional-OOD and length-OOD
  splits (Baek et al., 2026) are an interesting generalisation
  probe; we have not run them. They are listed in the
  limitations as an obvious next measurement.
- **The loop.** A single round of sharing has been run; the
  iterated form (curriculum₁ → agents₂ → curriculum₂ → …) has
  not. The loop is the actual open-endedness question, and is
  unaddressed here.

## 4.7 Configuration

A competent reader should be able to reproduce the headline from
the paper alone. The table below names every hyperparameter the
code uses in the reported runs. Sources: `clebran/fitness.py`,
`clebran/lineage.py`, `clebran/channel.py`,
`clebran/orchestrator.py`, `clebran/dsl/abstraction.py`,
`clebran/baselines/b0.py`. Items marked **(stated)** are
reproduced from the paper text; items marked **(not stated)**
were not in the paper before this revision and were added to
make the experiment auditable from the paper alone.

| hyperparameter | value | where in code | paper status |
|---|---|---|---|
| `λ_MDL` (MDL parsimony factor) | **1.05** | `fitness.py:38`, `lineage.py:103`, `orchestrator.py:32` | (was 1.1; corrected) |
| `K` (max fragment size, statements) | 4 | `channel.py:86` | (now stated) |
| `M` (max messages/lineage/epoch) | 3 | `channel.py:87` | (now stated) |
| N (lineages per arm) | 3 | `orchestrator.py:154` | (stated) |
| `drop_frac` (primitive-pool dropout per lineage) | 0.20 | `orchestrator.py:31` | (stated) |
| `pop_size` (population per task) | 100 | `lineage.py:97`, `orchestrator.py:156` | (now stated) |
| `tournament_k` | 3 | `lineage.py:98` | (now stated) |
| `elite` | 5 | `lineage.py:99` | (now stated) |
| `p_crossover` | 0.30 | `lineage.py:100` | (now stated) |
| `p_fragment` (prob. of fragment-splice vs other ops) | 0.15 | `lineage.py:101`, `b0.py:29` | (now stated) |
| `max_library` (per-lineage fragment library) | 50 | `lineage.py:102` | (now stated) |
| AOS decay (op_n/op_w recency) | 0.99 | `lineage.py:84` `op_credit(decay=0.99)` | (now stated) |
| AOS op-weight floor | 0.05 | `lineage.py:81` | (now stated) |
| Hall-of-fame size cap per task | 10 | `lineage.py:76` | (now stated) |
| Fitness cache: threshold length | 4 | `fitness.py:62` | (now stated) |
| Fitness cache: cap (entries) | 300 000 | `fitness.py:53` | (now stated) |
| `mine_every` (B5 compression-miner period, epochs) | 5 | `b0.py:32, 84` | (now stated) |
| `max_new` (B5 abstractions per mine call) | 8 | `lineage.py:673` | (now stated) |
| `min_size` / `max_size` (B5 abstraction body bounds) | 2, 4 | `lineage.py:673–674` | (now stated) |
| `min_occurrences` (compression miner duplicate threshold) | 2 | `abstraction.py:274` | (now stated) |
| Curriculum payload `n_pairs` per sub-abstraction | 4 | `orchestrator.py:78` | (now stated) |
| Curriculum aux-task per-lineage cap | 12 | `orchestrator.py:22` | (now stated) |
| Budget: Stage-4 sweep | 1 000 000 | experiment README | (stated) |
| Budget: frontier 8-seed B0/B1/B2/B6/B7 | 3 000 000 | experiment README | (stated) |
| Budget: frontier 20-seed B0/B1/B2/B5/B6/B7/B8/B9 | 4 000 000 | experiment README | (stated) |
| Seeds: Stage-1 5-arm sweep | 5 (1–5) | experiment README | (stated) |
| Seeds: K×M dose-response | 3 | `dose_response.py` default | (stated) |
| Seeds: frontier 8-seed | 8 | experiment README | (stated) |
| Seeds: frontier 20-seed | 20 | experiment README | (stated) |
| 1-failure case in 399/400 reproduction | `e40b9e2f` | `tests/test_stage0.py:30–31` | (now stated) — order-sensitive in Hodel's solver |

The Stage-4 sweep is committed at `40067c7`; the other
experiments do not currently state their commit hash in the
experiment READMEs, and the consolidated audit table is
deferred to the per-experiment analyses and to `git log
experiments/`.

**Note on the use of "significant".** Throughout the paper,
"significant" is used *colloquially* to mean "above the 2-SE
descriptive bar" (the convention in §4.5), *not* in the formal
hypothesis-testing sense. The paper does not use t-tests, p-values,
or confidence intervals. The 2-SE bar is a *descriptive* heuristic
for effect-magnitude; a comparison that does not meet it is not
*proven null*, only *under-resolved at the current seed count*.
