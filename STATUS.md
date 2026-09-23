# Status — what has been done

The historical record of completed work on the `clebran-arc-agi` rig.
Structured by topic; for the narrative reading see
[FINDINGS.md](FINDINGS.md), for the open work see
[roadmap.md](roadmap.md), for the publishable claims see
[papers/](papers/README.md).

Status as of 2026-09-23. The 12-commit pre-history of the discovery-bottleneck
work (including #1, #2, #3 of the menu) is committed; no branch is in flight.

---

## A. Substrate

The clebran substrate — typed SSA-style linear-IR programs over Hodel's 160
grid primitives, with a deterministic exception-guarded interpreter
(399/400 Hodel reference solvers reproduce exactly), per-task RNG substreams,
audited candidate-evaluation budgets, and three Stage-0 mechanisms — was
built end-to-end in the first wave of work. The closed substrate is what
makes the matching-compute comparisons trustworthy and reproducible.

**Done**

- **Typed primitives + linear IR** (`clebran/dsl/registry.py`, `program.py`):
  union flow-through typing (`vmirror: Piece -> Piece` typed as `Grid -> Grid`),
  so that reference compositions like `vmirror(I)` feeding a Grid slot are
  reachable to typed mutation.
- **Deterministic interpreter** (`clebran/dsl/interpreter.py`): exception-
  guarded, size-capped, `run_trace()` returns every register for visualisation.
  Hodel's 400 solvers reproduce 399/400 (the 1 failure is order-sensitive
  upstream in his `arc-dsl`).
- **Pure-outcome fitness** (`clebran/fitness.py`): fraction of demo pairs
  solved exactly, tie-broken by foreground/background-balanced per-cell
  accuracy (a blank canvas must not outrank content), scaled by NEO's
  `λ_MDL^(-length)` with `λ = 1.05` as default.
- **Adaptive operator selection** (`clebran/genome.py`): mutate/crossover/
  fragment-splice chosen by recent child-vs-parent success with floors.
  Fragment injection self-suppresses where library material is irrelevant
  (it was poisoning 15% of offspring on needle tasks) and self-amplifies
  where it pays.
- **Progress-weighted task scheduling** (`clebran/orchestrator.py`):
  generations allocated by proximity-to-solution, not round-robin; avoids
  starving near-miss tasks in the budget tail.
- **Hall-of-fame restarts + best-per-signature re-injection**: stagnation
  restarts explore fresh space but re-inject the best individual per
  skeleton signature, so a restart can't destroy polishable partial-
  credit stubs.
- **Per-task RNG substreams** (`Random(f"{seed}:{task_id}")`): single-task
  probes *predict* full-run behaviour exactly.
- **Phase-1 systematic closure** (`clebran/lineage.py` seeding): exhaustive
  depth-1 enumeration over typed constants, depth-2 skeleton sweep,
  signature-niched population, then constant-polish (coordinate descent
  + bounded 2-D joint sweeps for two-coordinate needles) on the top stubs
  and compositions around the top families. Closes the depth-≤2 bucket
  deterministically at seeding.
- **Stage-1 subset** (`clebran/subset.py`, `data/stage1_subset.json`):
  10×D1/15×D2/5×D3, tag-stratified, gate-checked; deterministic.
- **Frontier subset** (`data/frontier_subset.json`): 25×D2/5×D3 (D3 was
  re-weighted after the 2M-eval reachability probe showed evolution
  reaches only D2). Stage-1 gate then runs the B0 baseline against this
  frontier subset as a structural test.

**Engine throughput** (commit `f47bdad`-era profiling): ~8.3k evals/s/process,
3× up from ~2.8k. The interpreter's per-cell grid-validation scan
(79.5M `isinstance` calls / 32s in profiling) was replaced with an
O(rows+width) structural + first-row check; reproduction unchanged
(399/400). A length-guarded fitness cache (only deep programs, len ≥ 4)
skips the ~27% duplicate evaluations transparently — every call still
counts as a candidate-evaluation, so budgets/compute-matching are
byte-identical and search is deterministic-identical.

**Still open** (carried into [roadmap §6](roadmap.md)): Stage-5 on the
full 400-task training split and eval-split generalisation runs
(never evolve against eval).

---

## B. The H1 / H2 / H3 falsification (Paper 1)

Paper 1 is the central falsification. The headline result, on a 30-task
frontier subset at 4M candidate-evaluations per run, matched to 0.10%:

> A central learner with a self-mined library (arm **B5**) significantly
> beats every multi-agent sharing variant. The only statistically
> significant comparison in the study is **B5 − B6 = +0.85 evolution-
> phase solves (~2.2 SE)**. Communication is a transport mechanism, not
> a discovery mechanism.

**Arm table** (current; the original H1/H2/H3 framing focused on B0–B4):

| arm | role |
|---|---|
| B0 | single population, all compute |
| B1 | N isolated lineages, union |
| B2 / B3 | constrained / unconstrained **fragment** channel |
| B4 | constrained **signal** channel |
| B5 | single population + **central abstraction library** (Stitch/DreamCoder) |
| B6 / B7 | constrained / unconstrained **recovered-primitive** channel |
| B8 / B9 | constrained / unconstrained **curriculum** channel |
| B5+planner | B5 augmented with a planner-seeded individual (paper 3) |
| B5D | B5 + dreaming (paper 3, self-directed task generation) |

**Frontier ranking, 20 seeds × 4M evals (Paper 1 §3.3):**

| arm | evolution solves /30 |
|---|---|
| **B5** | **2.65 ± 1.31** |
| B0 | 2.25 ± 1.07 |
| B7 | 1.85 ± 1.04 |
| B6 | 1.80 ± 1.06 |
| B9 | 1.65 ± 0.75 |
| B2 | 1.60 ± 0.99 |
| B8 | 1.60 ± 0.75 |
| B1 | 1.45 ± 0.94 |

Plus the cost-axis re-score (roadmap §9a, `experiments/2026-08-29_cost_axis/`):
B5 and B5+planner are 7–10× more cost-efficient than every multi-agent arm,
on top of solving 6× more tasks. B5 (323,848 ± 28,776 evals/solve) is the
cheapest arm in the study.

**Vocabulary metrics** (Paper 1 §3.4): B5's mined library is more
compositional (topographic similarity 0.33 vs 0.14–0.15) and more cross-task
reused (0.15 vs 0.05). Divergence — the premise of H1 — is precisely what
degrades the shared vocabulary.

**Constraint-regime null** (Paper 1 §3.5): adaptive operator selection
self-regulates a failing channel regardless of bandwidth, so the constraint
neither helps nor hurts across all four payload types (fragments, signals,
recovered primitives, curricula).

**Frozen data** (20-seed 4M-eval sweep): `experiments/2026-07-22_b5_central_library/`,
`experiments/2026-07-22_frontier_recovered_scaled/`,
`experiments/2026-07-20_b3_dose_response/`,
`experiments/2026-07-20_stage4_b0-b4_matched_compute/`.

Full paper: [`papers/01-communication-cost/paper.md`](papers/01-communication-cost/paper.md).

---

## C. The "how you learned it" reorientation (Paper 2)

Paper 2 reports three matched-compute experiments on a teach→test protocol
with cost-to-solve as the primary endpoint:

1. **The curriculum channel engages but does not transfer.** Peers solve
   70–78% of the tasks they are taught (in prerequisite order, as designed)
   — the mechanism *works*. But on the real tasks, B8 −B1 = +0.15 (ns).
   *Acquiring* a taught concept is not the same as *transferring* it.
2. **The teach→test probe needed a cold baseline.** A controlled probe
   (taught vs control, 34 paired runs) appeared to show a 2× acquisition
   speedup from a relevant curriculum. Adding a *cold* (no-teaching)
   baseline reversed the reading: relevant teaching is neutral
   (−986 evals, permutation p = 0.97); irrelevant teaching is harmful.
   No amortisation across N students can rescue a per-student loss.
3. **Order significantly changes capability, with content held fixed.**
   Forward (foundations-first) beats reverse (foundations-last) on
   paired McNemar p = 0.021 — a dependency-violating order halves how
   much of the same curriculum is acquired (23% vs 47%). Forward also
   beats *cold* (p = 0.021). Fine-grained ordering is not the active
   ingredient (forward vs shuffled is ns, p = 0.18) — the learner
   self-orders when the material is merely available. Strict gating
   matters mainly when it can do *harm* (reverse). The effect is on
   *capability* (which targets solve at all), not on the cost endpoint
   (all order-vs-order evals-to-solve contrasts are null).

The capability audit (roadmap §9d) is the substantive deliverable:
self-directed practice / dreaming, active choice of what to practise,
retention without rigidity, compositional generalisation to genuinely
unseen tasks, meta-learning, and reflection on how something was learned
are *all* missing on the clebran rig — and the order experiment is the
proof of concept that the *axis* is measurable.

**Frozen data**: `experiments/2026-07-24_order_process/`. Full paper:
[`papers/02-how-you-learned-it/paper.md`](papers/02-how-you-learned-it/paper.md).

---

## D. The world-model direction (Paper 3, partial)

Build order (Paper 3 / roadmap §9f, items 1–3 of 6):

1. **Trace dataset** ✅ `data/traces.jsonl` — 16,149 `(state, action,
   next_state)` triples from the 400 Hodel solvers, recorded by
   `interpreter.run_trace`. 1,302 demo pairs, 6.3 MB, all from the
   existing substrate (no new external data). Build with
   `uv run python scripts/build_traces.py`.
2. **L1 baseline** ✅ `clebran/world_model/l1_baseline.py::KnnL1` — k-NN
   over the trace dataset: 0% out-of-distribution exact-match, 5% in-
   distribution (99% coverage). The k-NN is the *wrong model class* — `(state,
   action) → next_state` is too state-specific for Hamming-distance
   neighbours — and establishes the floor for any learned L1. **Two
   programmatic learned L1s** also done: `LookupTableL1` (25.5% exact,
   memoriser not learner, 0% OOD hit) and `GPL1` (18.7% exact, 52.7%
   shape, clebran's own GP evolves a small program per primitive).
3. **L2 planning arm** ✅ `clebran/world_model/l2_planner.py::L2Planner`
   — multi-pair, lookahead, loop-avoiding greedy planner over the
   clebran interpreter (a perfect L1). 35.9% one-step improve rate;
   3.4% multi-pair iterative solve rate — the *ceiling* any learned L1
   has to recover. `clebran/baselines/b5_planner.py` integrates the
   planner as a seed for B5's central-library search.
4. **L3 evoker** ❌ pending (roadmap §9f.4).
5. **ARCTraj integration** ❌ pending (roadmap §9f.5).
6. **ARC-AGI-3 evaluation** ❌ pending (roadmap §9f.6).

**B5+planner arm headline** (Paper 3 abstract): **budget-conditional**,
not a clean win. At 500K and 1M evals (3 seeds, frontier subset),
B5+planner *ties* B5 at 10.00 vs 9.67 mean solves with +0.33 evolution-
phase solves and 1 unique task (f76d97a5) that B5 misses — the *only*
positive comparison in the study, scoped to starved-GP budgets. At the
headline 4M budget (20 seeds), B5 and B5+planner are **tied** (12.45 ±
1.15 vs 12.35 ± 0.99, mean delta −0.10, t = 0.26, well below 2 SE).
B5 has 1 unique-to-it task (f25ffba3), B5+planner has zero unique-to-it
tasks. The 5-seed pilot's "B5 alone wins by 1.0" was a small-sample
effect.

**Reading**: the world-model direction is *useful at starved-GP budgets*
and *null at the headline 4M budget*. The planner seed is *exactly what
ARC-AGI-3 was designed to test* (arXiv:2603.24621: *Modeling* is one of
four required capabilities), and the clebran typed-IR substrate and library-
mining mechanism transfer directly.

**Frozen data**: `experiments/2026-08-29_cost_axis/` (cost-axis rescore
that includes B5+planner at 20 seeds × 4M); earlier pilots in
`clebran/world_model/`. Full paper:
[`papers/03-world-modeling/paper.md`](papers/03-world-modeling/paper.md).

---

## E. Dreaming and B5D (paper 3, supplementary)

**B5D arm**: B5 + dreaming. After every B5 solve, the lineage calls
`generate_task(sol.prog, rng, abstractions=lin.abstractions)` to
synthesise a variant task and adds it to its task pool (`auxiliary=False`,
no prerequisite gating). The dream generation itself is free (it calls
`run_safe` directly); the synthetic task costs real candidate-evaluations
when the lineage works on it — matched compute vs B5.

**1M pilot** (`experiments/2026-08-29_dreaming_pilot/`):

| metric (1M, 5 seeds) | B5 | B5D |
|---|---|---|
| frontier solves /30 | 10.40 ± 1.14 | 10.40 ± 0.55 |
| evals/solve | 97,077 | 96,457 (welch p = 0.905) |
| library size | 5.4 | 9.2 (+70%) |
| library used rate | 3.3% | 70.2% (+21×) |
| library cross-task reuse | 0.0 | 5.0 |
| library topsim | 0.264 | 0.047 (−5×) |

**4M escalation** (`experiments/2026-08-30_b5d_4m/`): 9 B5D-4M seeds vs
the 15-seed B5-4M baseline. B5D 12.33 vs B5 12.13, well within B5's
SD = 1.06. Library: B5D 2× larger, 13× more used, 124× more cross-task
reused. **Topsim is still lower** (0.22 vs 0.34) but the gap is
narrower at 4M than at 1M (0.05 vs 0.26). **Frontier remains tied.**

**Reading**: dreaming builds a *working library of what was already
known*; it does not invent new things. The dreaming builds a transportable
library (the headline result) but the transport doesn't expand the
frontier — consistent with the broader clebran finding (Paper 1) that
the system is good at *transporting* competence, not at *creating* it.

**B5D as a teacher / export-the-library** (roadmap §9b-4): design done
in the dreaming-pilot README, not built. Would test whether the
dreaming's library is *transportable* across lineages.

---

## F. Discovery-bottleneck menu — three concrete nulls at 1M

The transport side of clebran is solved (Paper 1: B5 is 7–10× more
cost-efficient than every multi-agent arm, +0.85 SE-significant vs the
recovered-primitive channel; dreaming builds libraries 2×/13×/124×
richer than B5 at 4M). The discovery side is the open problem: every
arm in the rig runs the same DSL, the same interpreter, the same pure-
outcome fitness, on the same 30 frontier tasks. **Three concrete
attacks on the discovery-bottleneck menu returned null at 1M pilots.**

| # | mechanism | kind of attack | result |
|---|---|---|---|
| 1 | failure-mode dreaming (B5D-NM-cons, B5D-NM-aggr) | change the *practice pool* (targeted) | **null** — aggressive variant 8.80 vs 10.40, **p = 0.007**; conservative 9.80, ns |
| 2 | heterogeneous fitness (B5-strongmdl, λ = 1.5) | change the *fitness signal* (parsimony pressure) | **null** — 9.60, ns; produces *shorter*, not *more compositional*, programs |
| 3 | task-subset specialization (hard15, random15) | change *what the lineage searches on* (subset) | **null** — hard subset: 0 test-exact (B5-4M also 0 at 2× per-task compute); random subset: gain = 2× per-task compute |

**Reading**: the three attack the same search space from three different
angles (practice pool, fitness signal, task pool); all three return null
at 1M. **No mechanism operating inside the current DSL/interpreter/
fitness on this frontier will expand B5's reach at 1M.** The remaining
bets — novelty search (#4), learned L1 as proposer (#5), operator
self-modification (#6), L3 evoker (#7) — all attack the problem by
adding a *new dimension* the lineage can search, rather than
redistributing budget across the same DSL. The **structural-change bet
is now the dominant remaining strategy on this rig.**

**Frozen data**:
- `#1`: `experiments/2026-08-31_b5d_nm_1m/`,
  `experiments/2026-08-31_b5d_nm_aggressive_1m/`.
- `#2`: `experiments/2026-08-31_b5_heterogeneous_1m/`.
- `#3`: `experiments/2026-09-22_task_subset_specialization/`
  (cost-axis loader at `clebran/metrics/cost.py` now picks up the
  B5-hard15 / B5-random15 arms so the menu pilots roll into the cost
  ranking).

---

## G. Curriculum generation (paper 2, deferred direction)

A planned direction scoped in the original roadmap (§7) for generating
*ordered task sequences* that would lead a fresh learner to build a
target DSL — the symbolic cousin of automatic curriculum learning in
RL.

**Done (in support of paper 2)**: the curriculum channel payload (B8/B9)
is built and frozen; the teach→test probe is built and frozen; the
order-vs-order probe is built and frozen; the teach→test cold baseline
is built and frozen. All three are reported in Paper 2.

**Not done (still on the roadmap)**:
- **Generators/learners split** (§7a): prerequisite-ordered forward
  generation vs regret/learning-progress-driven vs adversarial/co-evolved
  teacher policies — comparison is unrun.
- **Curriculum as a payload** (§7b): the fourth channel payload
  (alongside fragment/signal/abstraction) where knowledge crosses the
  channel as *problems to solve*, not as code. Not built.
- **Amortization gap** (§8a): total compute to bring N agents to a
  competence bar, with vs without a shared curriculum, sweeping N.
  Predicted crossover ≈ 2–4 agents if the probe's ~2× holds. Not run.
- **Negative transfer / novelty gap** (§8b): teach concept family A →
  test on tasks needing disjoint family B → compare against untaught
  control. Design done; not run.
- **8b-3** (specific to dreaming): B5 + B5D-library on tasks needing
  disjoint vocabulary. Not run.
- **Pluggable learners** (§9c): `Learner` interface + cross-
  architecture curriculum transfer. Not built.

---

## H. Generalisation and held-out evaluation

**Done**: the eval split has never been touched. All headline numbers
(frontier subset, 20 seeds × 4M evals) are training-split. The 400-task
eval split is reserved for exactly the "does this generalise to genuinely
unseen tasks" question.

**Not done** (all on the roadmap):
- Eval-split generalisation runs (roadmap §6).
- Compositional-OOD splits (no held-out split exists yet; topsim and
  cross-task reuse are the proxies).
- The teaching/transfer loop never iterated (`curriculum₁ → agents₂ →
  curriculum₂ → …`); competence-compounding across generations is the
  actual open-endedness question.

---

## I. Capability audit (roadmap §9d, status snapshot)

The honest assessment of what the clebran rig has vs. what it would need
to study "how you learned it" richly. (Verified against the published
papers and the experiments directory.)

| capability | status here |
|---|---|
| core-knowledge priors (objectness, geometry, number, agentness) | **have** (via the DSL; agentness weakest) |
| abstraction / compression (MDL, library learning) | **have** (miner, Stitch-style antiunification) |
| communication & teaching | **have** (4 payloads: fragment, signal, recovered-abstraction, curriculum) |
| honest measurement (matched compute, baselines, seeds) | **have** — the repo's real asset |
| acquisition efficiency as the objective | **have** — `clebran/metrics/cost.py`, `evals/solve` column in every arm summary |
| self-directed practice / dreaming | **have the loop, not the agent-driven version** — B5D dreams from solved programs; L3 evoker (paper 3 §9f.4) is open |
| active learning — *choosing* what to practise next | **missing** (learning-progress teacher; on roadmap as part of curriculum §7a) |
| continual learning without rigidity (plasticity) | **missing**, and possibly already violated (the §8b negative-transfer test is the diagnostic) |
| compositional generalisation to novel combinations | **partial** — topsim and cross-task reuse exist; held-out compositional split does not |
| generalisation to genuinely unseen tasks | **missing** — eval split untouched |
| meta-learning — adapting the *learning algorithm* itself | **missing** — `Operator self-modification` is #6 in the discovery-bottleneck menu |
| reflection — credit assignment over *how* it learned | **missing**, and the least-explored anywhere |

The last row is the sharpest form of the thesis and is largely open in
the literature: systems that model *their own acquisition process* and
improve it.

---

## J. Build-order decisions resolved

**One repo or several** (roadmap §9e): *one repo, pluggable interfaces* —
factor along capability boundaries inside the repo
(`core`: tasks/curricula, the protocol, metrics, baselines, honest
reporting; `plugins`: learners, teachers/curriculum generators, payload
types, world models). Splitting is justified only when a direction needs a
genuinely different substrate *and* has already shown a result worth
porting. Prove it here first behind the `Learner` interface; split later
if and only if the interface stops fitting.

**Substrate-only world-modeling** (roadmap §9f): the world-modeling
direction brought in **no new external data or code**. The trace dataset
is built from the 400 Hodel reference solvers already vendored from
[michaelhodel/arc-dsl](https://github.com/michaelhodel/arc-dsl); the L1
baseline, L2 planner, and B5+planner arm are built on existing clebran
APIs. The closest external resources the direction *should* engage with
next — ARCTraj, ARC-AGI-3, Hodel's *re-arc*, CATER — are listed in the
[roadmap §9f.5–6](roadmap.md) and the README's *World modeling direction*
section.

---

## K. Frozen experiment index

All experiments are frozen under `experiments/<date>_<name>/` with the
verdict, raw per-arm-seed summaries, gate output, and commit hash. The
ones relevant to the published claims:

| experiment | paper | verdict |
|---|---|---|
| `2026-07-20_stage4_b0-b4_matched_compute` | paper 1 | Stages 0–4 complete; H1 supported, H2 null, H3 directionally supported |
| `2026-07-20_b3_dose_response` | paper 1 | B3 degradation absent (AOS self-regulates); H3 null on stage-1 |
| `2026-07-22_b5_central_library` | paper 1 | B5 baseline; the central-library control |
| `2026-07-22_frontier_recovered_scaled` | paper 1 | 20-seed 4M-eval frontier ranking; B5 > B6/B7 |
| `2026-07-24_order_process` | paper 2 | Order significantly changes capability (p = 0.021) |
| `2026-08-29_cost_axis` | paper 1 / paper 3 | Cost-axis rescore; B5 cheapest, B5+planner tied at 4M |
| `2026-08-29_dreaming_pilot` | paper 3 (supp.) | B5D 1M pilot; frontier tied, library 1.7× larger |
| `2026-08-30_b5d_4m` | paper 3 (supp.) | B5D 4M; frontier tied, library 124× more reused |
| `2026-08-31_b5d_nm_1m` | STATUS §F #1 | B5D-NM-cons 9.80 vs B5 10.40, ns |
| `2026-08-31_b5d_nm_aggressive_1m` | STATUS §F #1 | B5D-NM-aggressive 8.80 vs B5 10.40, **p = 0.007** |
| `2026-08-31_b5_heterogeneous_1m` | STATUS §F #2 | B5-strongmdl 9.60 vs B5 10.40, ns |
| `2026-09-22_task_subset_specialization` | STATUS §F #3 | hard15 arm: 0 test-exact (B5-4M also 0); random15: gain = 2× per-task compute |