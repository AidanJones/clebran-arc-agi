# clebran-arc-agi

*clebran* (Welsh: to chatter, to gossip) — gossip protocols for divergent program evolution. Multiple populations of DSL programs evolve under pure reward on ARC-AGI-1 tasks, diverge into different solution strategies, and pass fragments of "what works" to each other through a deliberately narrow communication channel. The experiment tests whether that constrained gossip preserves better abstractions than isolation, ensembling, or unconstrained sharing — at matched compute, with baselines strong enough that a null result is trustworthy.

The full design is in [emergent-dsl-arc-spec.md](emergent-dsl-arc-spec.md). **What the experiment found: [FINDINGS.md](FINDINGS.md).** What has been done, structured by topic: [STATUS.md](STATUS.md). Open work with hypothesis / expected payoff: [roadmap.md](roadmap.md). **The papers: [papers/](papers/README.md)** — one focused paper per set of experiments (paper 1: communication cost; paper 2: how you learned it; paper 3: world modeling; paper 4: discovery-bottleneck 0-for-4) plus a combined summary at `papers/00-combined/`.

> **Headline result.** At matched compute on ARC, a single population that mines its own solutions into a growing abstraction library (a DreamCoder/Stitch-style central learner, arm **B5**) *significantly* outperforms divergent lineages communicating over a constrained channel (B6): `B5 2.65 > B0 2.25 > B7≈B6 1.8 > B2 1.6 > B1 1.45` evolution-phase solves; B6−B5 = −0.85 (~2.2 se, the only significant comparison). The central hypothesis is not supported — the strongest control wins. A trustworthy negative result, which is exactly what the baselines were built to make believable.

## Project at a glance

- **Substrate.** Typed evolutionary program synthesis over
  [michaelhodel/arc-dsl](https://github.com/michaelhodel/arc-dsl) on the
  ARC-AGI-1 training split; 30-task frontier subset (25 D2 + 5 D3) for
  the headline numbers. Programs are linear SSA-style register
  programs (the shape Hodel's hand-written solvers already take), so
  reference solvers parse *losslessly* into our genome.
- **Rig.** Matched-compute evaluation with ≤ 0.27% audit spread; the
  compute unit is candidate-evaluations (wall-clock never enters a
  comparison). Each headline arm runs ≥ 5 seeds; the B5 vs multi-agent
  frontier sweep is 20 seeds.
- **Transport.** B5 (single learner with a growing central abstraction
  library) sits at the top of every matched-compute ranking; the
  multi-agent sharing arms are 7–10× less cost-efficient on top of
  solving fewer tasks. The dreaming arm B5D builds a library 2× larger
  and 124× more cross-task-reused than B5 at 4M — the library mechanism
  is real and reusable. Communication is **a transport mechanism, not
  a discovery mechanism**, and in this substrate transport does not
  pay back the cost of dividing the compute. (Paper 1.)
- **Process.** Teaching content between agents is neutral or harmful
  at matched compute, but *order* matters: a foundations-first curriculum
  significantly outperforms the same curriculum taught
  foundations-last (paired McNemar p = 0.021), because a
  dependency-violating order halves how much of the same content
  transfers. (Paper 2.)
- **World-modeling substrate.** The trace dataset (16,149 rows from
  Hodel's 400 reference solvers) and the L2 multi-pair planner are
  built; the L1 baseline shows k-NN is the wrong model class (0% OOD
  exact-match); programmatic learned L1s are characterised (lookup-table
  L1 = 25.5% OOD exact-match but 0% OOD hit-rate; GP-evolved L1 = 18.7%
  OOD exact-match, 52.7% shape-match, perfect on pure-geometric
  primitives). The B5+planner integration is **budget-conditional**:
  positive on starved GP (500K-1M, ties B5 with 1 unique task) and
  *null at scale* (4M, 20 seeds: 12.45 ± 1.15 vs 12.35 ± 0.99,
  mean delta −0.10, t = 0.26). (Paper 3.)
- **Discovery bottleneck — the open problem.** Four pre-registered
  attacks on the central library's reach (failure-mode dreaming,
  heterogeneous fitness, task-subset specialization, novelty search)
  return null at 1M × 5 seeds. The discovery-bottleneck menu is
  **0-for-4**: *no mechanism operating inside the current
  DSL/interpreter/fitness on this frontier will expand B5's reach at
  1M, regardless of which axis you vary*. The remaining bets (learned
  L1 as proposer #5, operator self-modification #6, L3 evoker #7) all
  change the *substrate* — they are the structural-change bet. (Paper 4.)
- **What's next.** See [roadmap.md](roadmap.md) for the open work,
  organised by research strand with hypothesis and expected payoff for
  each.

## Research direction: *not what you know, but how you learned it*

The project is pivoting from "does communication raise skill?" to **"does the
*way* a system acquires knowledge change how well it can use it?"** This is not
a soft reframe — it is what the benchmark's own author says intelligence *is*:

> "The intelligence of a system is a measure of its **skill-acquisition
> efficiency** over a scope of tasks, with respect to priors, experience, and
> generalization difficulty." — Chollet, *On the Measure of Intelligence*

Chollet's companion warning is that **unlimited priors or unlimited training
data let you "buy" skill**, masking a system's actual generalization power. That
is the precise sense in which internet-scale pretraining plus task RL sidesteps
the question rather than answering it — and it is why this repo deliberately
studies a small, fully-instrumented learner where *acquisition cost* is
measurable rather than a large one where it is not.

**Our own results independently point the same way.** The transfer probe found
that a relevant curriculum changes **evals-to-solve** (acquisition cost) while
leaving **solve count** (skill) unmoved. We had been scoring every arm on skill,
which is exactly the endpoint Chollet argues is uninformative. The instrument
was already in the repo; it was not the primary metric. Section 9 of the
[roadmap](roadmap.md) makes it one, and lays out the capability gaps —
self-directed practice ("dreaming"), active choice of what to practise,
retention without rigidity, and reflection on *how* something was learned — that
a learner needs before "how you learned it" can be studied properly.

## The discovery bottleneck — *the* open problem

The clebran system is a three-stage pipeline:

> **discover → share → learn.**

What we have shown on this rig, at matched compute:

- **Share works in principle.** The channel carries messages; the received-
  abstraction payload (B6/B7) is genuinely *used* by receivers (`received_used ≈ 1.1–1.4`).
- **Learn works centrally.** A single learner that mines its own solutions
  into a growing library (B5) outperforms every multi-agent sharing variant
  on the cost axis (7–10× more cost-efficient than B0–B9) while solving 6× more
  tasks. The library is the *transport* layer, and it works.
- **The 9b dreaming arm (B5D) takes the next step on transport**: it produces
  a library 2× larger, 13× more used, and 124× more cross-task-reused than B5's
  at the same compute — at 4M evals, 17.0 abstractions, 85.7% used, 12.4
  cross-task-reuse. The library is *real and reusable*. But it still does
  not expand the frontier (B5D 12.33 vs B5 12.13, tied). The dreaming
  produces a working library of *what was already known*; it does not invent
  *new things*.

**The bottleneck is *discovery*, not transport.** No mechanism in the
rig actually expands what an individual lineage can solve. Every arm —
B0, B1, B2, B3, B4, B5, B5+planner, B5D, B6, B7, B8, B9 — runs the same
DSL, the same interpreter, the same pure-outcome fitness, on the same
30 frontier tasks, with the same primitive pool (Hodel's 160). The
mechanisms we have vary *initial conditions* (random seed, library of
self-mined abstractions, planner-seeded program, dream-task pool) but
none of them invent new primitives, change the fitness function, or
explore structurally new regions of the search space. They all *improve
search*; none of them *expand reach*.

This is consistent with the broader clebran finding (Paper 1, §8,
[`FINDINGS.md`](FINDINGS.md)): **the system is good at *transporting*
competence, not at *creating* it.** The central library is the
compression-and-transport layer for what an agent has already learned.
The channel is a second transport layer. Neither is the discovery
mechanism we need.

**The guiding idea for what comes next.** A multi-agent system *is*
good for sharing knowledge — that's the clebran premise, and it is
right. But the *value* of the multi-agent system is bounded by what
each individual agent can discover. To make the system as a whole
*learn new things*, we need individual agents to actually discover
new things first. The transport is solved; the discovery is open.

### Concrete discovery mechanisms (in increasing order of cost)

Each is a mechanism for an *individual* lineage to find something
genuinely new, distinct from its prior. After discovery, the existing
transport machinery can carry it.

**Menu status (2026-09-24):** #1, #2, #3, #4 have been run at 1M × 5
seeds and all returned **null** — **0-for-4 at 1M**, across four
different axes (practice pool, fitness signal, task pool, objective).
See [STATUS.md §F](STATUS.md) for the four pilots' results, the
discovery-bottleneck pattern, and frozen data pointers; the focused
paper is at [`papers/04-discovery-bottleneck/`](papers/04-discovery-bottleneck/).
**#5 onward are un-started.** The discovery-bottleneck menu is now
the structural-change bet — each remaining item tests whether
adding a *new dimension* (a new primitive distribution, a new operator
pool, a new world model) can expand B5's reach.

1. ~~**Failure-mode dreaming**~~ — **DONE 2026-09, NULL.** B5D-NM-aggr
   regresses (8.80 vs B5 10.40, **p = 0.007**); B5D-NM-cons 9.80 (ns).
   See [`experiments/2026-08-31_b5d_nm_1m/`](experiments/2026-08-31_b5d_nm_1m/),
   [`experiments/2026-08-31_b5d_nm_aggressive_1m/`](experiments/2026-08-31_b5d_nm_aggressive_1m/).
   Aggressive failure-mode targeting is harmful; the conservative
   variant regresses mildly. ([STATUS §F #1](STATUS.md).)

2. ~~**Heterogeneous fitness**~~ — **DONE 2026-09, NULL.** B5-strongmdl
   (λ = 1.5) regresses (−0.80 frontier, −0.80 evo, both ~1 SE); is more
   expensive (105K vs 97K evals/solve). Stronger MDL pressure produces
   *shorter*, not *more compositional*, programs.
   [`experiments/2026-08-31_b5_heterogeneous_1m/`](experiments/2026-08-31_b5_heterogeneous_1m/). ([STATUS §F #2](STATUS.md).)

3. ~~**Task-subset specialization**~~ — **DONE 2026-09, NULL.** hard15
   arm: 0 test-exact (B5-4M, 2× per-task compute, also 0); random15 arm:
   +1.0 test-exact vs B5-1M on the same subset (p = 0.007), fully
   consistent with the 2× per-task compute redistribution (67k vs
   33k/task). No signal beyond compute.
   [`experiments/2026-09-22_task_subset_specialization/`](experiments/2026-09-22_task_subset_specialization/). ([STATUS §F #3](STATUS.md).)

4. ~~**Novelty search arm**~~ — **DONE 2026-09-24, NULL.** B5N
   (objective: distinct output grids) finds exactly the 6 easy tasks
   B5-1M also finds (100% overlap, 0 unique-to-novelty tasks); all
   5 seeds degenerated partway through evolution (novelty plateau
   near 0 once the per-task archive filled). Mean solves: B5N 2.00
   vs B5-1M 10.20 (degeneration). The novelty arm's reading is that
   *novelty-as-objective can't drive B5's evolution* — it doesn't
   reward improvement. See
   [`experiments/2026-09-24_novelty_search/`](experiments/2026-09-24_novelty_search/).
   The discovery-bottleneck menu is **0-for-4 at 1M × 5 seeds**.
   ([STATUS §F #4](STATUS.md); focused paper at
   [`papers/04-discovery-bottleneck/`](papers/04-discovery-bottleneck/).)

5. **Learned L1 as proposer** (large, ~1 week) — **next
   discovery-bottleneck bet, on the [roadmap](roadmap.md) as item 1.**
   Train a small programmatic L1 on the trace dataset
   ([`data/traces.jsonl`](data/traces.jsonl), 16,149 rows from
   Hodel's 400 solvers). Use the L1 to *propose* candidate
   programs for unsolved frontier tasks. The L1's generalization
   is what it has learned across all 400 reference solvers —
   a different *kind* of discovery from the lineage's own search.
   If null at 1M, the menu is 0-for-5 and the structural-change bet
   continues with #6.

6. **Operator self-modification** (large, ~2 weeks). The lineage
   modifies its own mutation/crossover operators based on what
   works. Modifications are shareable across lineages. Closer to
   "learning to learn", and a real direction in the world-modeling
   direction's spirit. ([roadmap](roadmap.md) item 3.)

7. **L3 evoker (9f.4)** (large, ~2 weeks). The world model that
   improves on failed predictions. The trace dataset and L2
   planner are in place; this is the next open build-order item
   in the world-modeling direction (Paper 3). The L3 evoker
   refines its world model when reality contradicts it, then
   re-rolls — the natural capstone of the world-modeling
   direction. ([roadmap](roadmap.md) item 4.)

**The principle.** Any mechanism that expands what a *single*
lineage can discover is worth more, on this rig, than any
mechanism that improves how discoveries are shared. We have the
second; we need the first.

## Hypotheses → baselines

The arm table covers the original H1/H2/H3 framing (B0–B4) and the
extension arms (B5–B9) that close the central-library control.

| arm | description | role |
|---|---|---|
| B0 | single population, all compute | reference line; H2 needs B2 > B0 |
| B1 | N isolated lineages (CH-NONE), union | H1 divergence measured here; ensembling control |
| B2 / B3 | N lineages + CH-CONSTRAINED / UNCONSTRAINED, **fragment** payload | main treatment (H2, H3) |
| B4 | N lineages + CH-CONSTRAINED, **signal** payload | abstract-communication variant |
| **B5** | **single population + central abstraction library** | the central-library control; the strongest "abstraction reuse without divergence" baseline (Paper 1) |
| B6 / B7 | N lineages + CH-CONSTRAINED / UNCONSTRAINED, **recovered-primitive** payload | H3 on a *discovered* vocabulary |
| B8 / B9 | N lineages + CH-CONSTRAINED / UNCONSTRAINED, **curriculum** payload | teaching-as-communication (Paper 2) |
| **B5+planner** | **B5 + planner-seeded individual (paper 3)** | world-model integration; budget-conditional result |
| B5D | B5 + dreaming (paper 3) | self-directed practice; transport-side enrichment |

All arms run at matched candidate-evaluation budgets (audited to ≤ 0.27%
spread across multi-arm runs, 0.10% for the headline 20-seed frontier
sweep). The compute unit is candidate-evaluations; wall-clock never
enters a comparison.

**Headline result on the frontier** (20 seeds × 4M evals; full data in
[`experiments/2026-07-22_frontier_recovered_scaled`](experiments/2026-07-22_frontier_recovered_scaled/),
[`experiments/2026-07-22_b5_central_library`](experiments/2026-07-22_b5_central_library/),
and Paper 1 §3.3):

| arm | evolution-phase solves /30 |
|---|---|
| **B5** | **2.65 ± 1.31** |
| B0 | 2.25 ± 1.07 |
| B7 | 1.85 ± 1.04 |
| B6 | 1.80 ± 1.06 |
| B9 | 1.65 ± 0.75 |
| B2 | 1.60 ± 0.99 |
| B8 | 1.60 ± 0.75 |
| B1 | 1.45 ± 0.94 |

**H1 supported** — isolated lineages diverge (pairwise Jaccard 0.57 ± 0.10
on primitive usage, tasks solved by exactly one lineage in 4/5 seeds).
**H2 null** — at the Stage-1 subset and 1M-eval budget, communication
has nothing to add; at the 20-seed 4M frontier sweep, the central-library
control (B5) *significantly* beats every multi-agent arm, with the only
significant comparison being **B5 − B6 = +0.85 (~2.2 SE)**. **H3 null**
across all four payload types — adaptive operator selection self-regulates
a failing channel regardless of bandwidth. On the cost axis
([`experiments/2026-08-29_cost_axis/`](experiments/2026-08-29_cost_axis/)),
B5 and B5+planner are 7–10× more cost-efficient than every multi-agent
arm, on top of solving 6× more tasks.

**Discovery side** (the open problem; STATUS §F and FINDINGS §Discovery-
bottleneck menu): four concrete attacks on the discovery-bottleneck
menu (failure-mode dreaming, heterogeneous fitness, task-subset
specialization, novelty search) return null at 1M × 5 seeds. The menu
is **0-for-4** — no mechanism operating *inside* the current
DSL/interpreter/fitness has expanded B5's reach, regardless of which
axis is varied. The remaining bets (learned L1 as proposer, operator
self-modification, L3 evoker) all attack the problem by adding a *new
dimension* the lineage can search — the **structural-change bet**.
Focused paper at
[`papers/04-discovery-bottleneck/`](papers/04-discovery-bottleneck/).

## External repositories and references

Cloned into `third_party/` by [scripts/fetch_third_party.sh](scripts/fetch_third_party.sh) (not committed):

- **[michaelhodel/arc-dsl](https://github.com/michaelhodel/arc-dsl)** — the DSL this
  project evolves programs over. We vendor `dsl.py` (160 typed grid primitives),
  `constants.py`, `arc_types.py`, and `solvers.py` into `clebran/dsl/_vendor/` (MIT
  license included). `solvers.py` — one hand-written solver per training task — is
  used two ways: as the **depth oracle** (statement count grades task difficulty, §4.1)
  and as the **correctness gate** (every reference solver must reproduce its task's
  grids through *our* interpreter before that task can enter the subset).
- **[fchollet/ARC-AGI](https://github.com/fchollet/ARC-AGI)** — the ARC-AGI-1 dataset
  (400 training + 400 evaluation tasks as JSON grids). Only the training split is ever
  evolved against.

Intellectual anchors (see spec §2 for how each maps onto the design):
[Learning-to-Theorize / NEO](https://arxiv.org/abs/2605.03413) (transfer-not-reconstruction
fitness, adaptive MDL rule), [DreamCoder](https://arxiv.org/abs/2006.08381) and
[Stitch](https://github.com/mlb2251/stitch) (library learning),
[Lazaridou & Baroni](https://arxiv.org/abs/2006.02419) and
[EGG](https://github.com/facebookresearch/EGG) (constrained-channel emergent communication),
[DreamerV2/V3 (Hafner et al.)](https://arxiv.org/abs/2010.02193) and
[*Agentic World Modeling* (Ye et al., arXiv:2604.22748)](https://arxiv.org/abs/2604.22748)
(L1/L2/L3 framing for the world-modeling direction).

**The world-modeling direction (roadmap §9f) brought in no new external
data or code.** The trace dataset (`data/traces.jsonl`, 16,149 rows) is
built from the **400 Hodel reference solvers already vendored** from
[michaelhodel/arc-dsl](https://github.com/michaelhodel/arc-dsl); the L1
baseline, L2 planner, and B5+planner arm are built on the existing
clebran APIs (no new dependencies). The closest external resources the
direction *should* engage with next (ARCTraj, ARC-AGI-3, Hodel's
*re-arc*, CATER) are listed in the *World modeling direction* section
below.

## How the codebase fits together

Programs are **linear SSA-style register programs** (`x0 = fn(...); x1 = fn(x0, ...); return last`)
over Hodel's primitives — the same shape as his hand-written solvers, so reference
solvers parse *losslessly* into our genome representation. Everything else builds on that:

```
clebran/
  data/loader.py       ARC task loading (grids as tuples)
  dsl/
    _vendor/           vendored arc-dsl (dsl.py, constants.py, arc_types.py, solvers.py)
    registry.py        primitive signatures + type-subsumption relation
    program.py         the linear IR; static typing with union flow-through
                       (vmirror: Piece->Piece applied to a Grid returns Grid)
    interpreter.py     deterministic, exception-guarded execution; size caps;
                       run_trace() returns every register for visualization
    solver_parse.py    solvers.py -> IR (depth proxy + Stage-0 reproduction gate:
                       399/400 reproduce exactly; the 1 failure is order-sensitive upstream)
  subset.py            deterministic §4.1 recipe -> data/stage1_subset.json
                       (10×D1/15×D2/5×D3, tag-stratified, gate-checked)
  genome.py            typed operators on the IR: point/arg/const mutation, grow
                       (insert + rewire, the linear-IR "subtree replacement"),
                       two-segment crossover, a shared repair pass, fragment
                       extraction/injection with hole-filling, and systematic
                       depth-1 / depth-2 enumeration
  fitness.py           pure outcome reward: fraction of demo pairs solved exactly,
                       tie-broken by per-cell accuracy (foreground and background
                       scored separately — a blank canvas must not outrank content)
                       scaled by NEO's lambda_MDL^(-length)
  lineage.py           one population per task + the lineage's private fragment
                       library; the search engine (see below)
  channel.py           the blackboard: CH-NONE / CH-CONSTRAINED(K,M) /
                       CH-UNCONSTRAINED, fragment & signal payloads
  orchestrator.py      N lineages, epochs, publish/receive, matched-compute budget
  metrics/
    divergence.py      pairwise Jaccard over primitive usage; uniquely-solved counts
    report.py          terminal H2/H3 table + compute audit + verdict comparisons
  baselines/           b0.py (single population), arms.py (B1–B4 + sweep driver),
                       b5_planner.py (B5+planner arm — paper 3),
                       common.py (subset pool, JSONL run logs)
  world_model/         roadmap §9f: L1/L2 world-model substrate
    __init__.py        package marker
    __main__.py        CLI: `python -m clebran.world_model {l1,l2}`
    l1_baseline.py     KnnL1 — k-NN predictor over data/traces.jsonl
    l2_planner.py      L2Planner — multi-pair, lookahead, loop-avoiding
    README.md          developer-facing README (trace dataset, L1, L2, B5+planner)
  solver_card.py       the HTML report generator (see Reports)
tests/
  test_stage0.py       Stage-0 acceptance tests (§8.1 row 0)
  test_world_model.py  L1/L2 world-model tests (12 unit + 2 slow end-to-end)
  test_b5_planner.py   B5+planner arm tests (2 unit + 1 slow end-to-end)
scripts/
  stage1_gate.py       Stage-1 acceptance check over logs/b0_seed*.jsonl
  build_traces.py      build data/traces.jsonl from the 400 Hodel solvers
  inspect_traces.py    debug: action-head distribution, state-kind counts
  evaluate_planner_multipair.py
                       multi-pair L2 evaluation against data/traces.jsonl
experiments/           one folder per completed experiment (verdicts + frozen data)
data/
  stage1_subset.json   the 30-task Stage-1 subset (committed, reproducible)
  frontier_subset.json the 30-task frontier subset (committed, reproducible)
  traces.jsonl         16,149 (state, action, next_state) rows from
                       the 400 Hodel solvers — the world-modeling
                       trace dataset (built, committed, 6.3 MB)
logs/                  JSONL run logs (gitignored)
papers/                one paper per set of experiments (see Papers below)
```

### The search engine (what it took to pass the Stage-1 gate)

The spec's Stage-1 gate — B0 solves all 10 near-atomic tasks on *every* seed — forced
a series of mechanisms, each fixing a diagnosed failure mode. They apply identically
to every arm, so none of them bias the H2/H3 comparison:

- **Union flow-through typing** (`program.py`): Hodel types mirrors as `Piece -> Piece`;
  without refinement, typed mutation could never feed `vmirror(I)` into a `Grid` slot,
  making reference compositions unreachable.
- **Phase-1 systematic closure** (`lineage.py` seeding): exhaustive depth-1 enumeration
  over typed constants, depth-2 skeleton sweep, signature-niched population, then
  constant-polish (coordinate descent + bounded 2-D joint sweeps for two-coordinate
  needles like crop offset+size) on the top stubs *and* compositions around the top
  families. Closes the depth-≤2 bucket deterministically at seeding.
- **Adaptive operator selection**: mutate/crossover/fragment-splice chosen per
  population by recent child-vs-parent success with floors. Fragment injection
  self-suppresses where library material is irrelevant (it was poisoning 15% of
  offspring on needle tasks) and self-amplifies where it pays — the fair setting
  for judging the channel.
- **Progress-weighted task scheduling**: generations allocated by proximity-to-solution
  instead of round-robin, which starved near-miss tasks in the budget tail.
- **Hall-of-fame restarts**: stagnation restarts explore fresh space but re-inject the
  best individual per skeleton signature, so a full restart can't destroy polishable
  partial-credit stubs.
- **Per-task RNG substreams**: each task's trajectory is driven by
  `Random(f"{seed}:{task_id}")`, so a task behaves bit-identically in isolation and
  interleaved with 29 others — isolation probes *predict* full-run behavior.
- **Foreground/background-balanced reward** (`fitness.py`): on mostly-background
  targets, plain per-cell accuracy let `canvas(ZERO, 3x3)` — a blank grid — outrank
  every content-bearing program.

## World modeling direction — built (budget-conditional integration result)

The falsification (Paper 1: H1 supported, H2/H3 null, central library wins)
closed the original clebran question. The "how you learned it"
reorientation (Paper 2) opened a new one. The next concrete capability on
the list was a **learned world model** — an internal simulator the agent
uses to *imagine* the result of an action before it commits to it. **The
first three layers of this direction are now built** (roadmap §9f build
order, items 1–3 complete), and the integration result is
**budget-conditional** — *positive at starved-GP budgets, null at the
headline 4M budget*. Read it as the rig's first *partial-positive* result:
the substrate is in place and a small-budget win is real, but the 4M
sweep is a clean null.

> **Headline (paper 3).** A B5+planner arm — B5 (central library) augmented
> with a planner-seeded individual in the initial population of every task —
> ties B5 at the 10/30 frontier-subset ceiling (3 seeds, 500K and 1M
> candidate-evaluations, matched compute). 10.00 vs 9.67 mean solves, +0.33
> evolution-phase solves, 1 unique task (f76d97a5) that B5 misses in any of
> the 3 seeds. **At the headline 4M budget (20 seeds), B5 and B5+planner are
> tied** (12.45 ± 1.15 vs 12.35 ± 0.99, mean delta −0.10, t = 0.26, well
> below 2 SE); B5 has 1 unique-to-it task (f25ffba3), B5+planner has zero
> unique-to-it. The 5-seed pilot's "B5 alone wins by 1.0" was a small-
> sample effect. Full paper:
> [`papers/03-world-modeling/`](papers/03-world-modeling/).

### What was built (and what was *not* brought in from elsewhere)

- **No external data or code was added.** The trace dataset is built from
  the **400 Hodel reference solvers already vendored in `third_party/`**;
  the planner, the L1 baseline, and the B5+planner arm are built on
  existing clebran APIs (`interpreter.run_trace`, `dsl.registry.PRIMITIVES`,
  `fitness.Evaluator`, `lineage.Lineage`). **No new external dependencies.**
- **L1 baseline (KnnL1)** — `clebran/world_model/l1_baseline.py`. A k-NN
  predictor over the trace dataset: 0% out-of-distribution exact-match,
  5% in-distribution exact-match (99% coverage). The k-NN is the *wrong
  model class* for this problem — `(state, action) → next_state` is too
  state-specific for Hamming-distance neighbours — and establishes the
  floor for any learned L1.
- **L2 planner (L2Planner)** — `clebran/world_model/l2_planner.py`. A
  multi-pair, lookahead, loop-avoiding greedy planner over the clebran
  interpreter (which is a *perfect* L1). 35.9% one-step improve over
  identity on the trace dataset; 3.4% multi-pair iterative solve rate.
  The 3.4% is the *ceiling* any learned L1 has to recover, with the
  perfect L1 as the ground truth.
- **B5+planner arm** — `clebran/baselines/b5_planner.py`. B5 (central
  library) augmented with a planner-seeded individual in the initial
  population of every task. CLI: `python -m clebran.baselines.b5_planner
  --seed N --budget K --planner-lookahead L`.

**L1/L2/L3 framing** (per the Agentic World Modeling literature,
arXiv:2604.22748):

- **L1 Predictor** — built (the clebran interpreter is a perfect L1; the
  KnnL1 baseline establishes the floor; the learned L1 is open work).
- **L2 Simulator** — built (the multi-pair planner; the B5+planner arm
  is the integration test).
- **L3 Evolver** — open work; the "self-directed practice / dreaming"
  row in the §9d capability audit (roadmap §9b).

**Trace dataset** — `data/traces.jsonl`, 16,149 `(state, action,
next_state)` rows from the 400 Hodel solvers, recorded by
`interpreter.run_trace`. **1,302 demo pairs, 6.3 MB, all from existing
substrate — no new external data.** Build with
`uv run python scripts/build_traces.py`.

### Reading order for the world-modeling direction

1. `clebran/world_model/README.md` — the developer-facing README with the
   trace dataset, the L1 baseline, the L2 planner, and the B5+planner
   arm results, in that order.
2. [`papers/03-world-modeling/`](papers/03-world-modeling/) — the
   self-contained focused paper. Abstract, methods, results, discussion,
   and the headline (B5+planner ties B5 at 10.00 vs 9.67 mean solves).
3. [`papers/00-combined/`](papers/00-combined/) — the combined summary
   that ties the world-modeling paper to paper 1 (the falsification) and
   paper 2 (the reorientation), with the synthesis and the four
   methodological lessons that recur across all three.

### Closest external resources the project should engage with next

- **ARCTraj** (Kim, Choi, Lee & Kim, KDD 2026, arXiv:2511.11079,
  [HuggingFace `SejinKimm/ARCTraj`](https://huggingface.co/datasets/SejinKimm/ARCTraj))
  — ~10,000 human step-by-step object-level trajectories across all 400
  ARC-AGI-1 training tasks, MDP-formatted, designed for PPO / DreamerV3 /
  GFlowNets / Decision Transformers. This is the most directly usable
  *external* dataset for what comes next; it has not been integrated yet.
- **ARC-AGI-3** (arXiv:2603.24621) — the new interactive turn-based ARC
  benchmark. "Modeling" is one of four required capabilities; the
  world-model direction is exactly what ARC-AGI-3 is designed to test.
- **CATER** (Girdhar & Ramanan, ICLR 2020) — synthetic 3D scenes with full
  per-frame state; the design pattern (procedurally generate, log every
  intermediate state) is what re-arc + `run_trace` can do for ARC at scale.
- **Hodel's re-arc** — already provides task generators that, combined with
  `run_trace`, can produce unlimited additional trace data beyond the 400
  Hodel solvers. The §9f build-order item 4 (re-arc-generated trace
  candidates) would expand the planner's candidate set with primitives
  inferred from per-task generators, not just Hodel's reference solvers.

## Setup

```sh
sh scripts/fetch_third_party.sh   # clones michaelhodel/arc-dsl + fchollet/ARC-AGI
uv sync
uv run python -m clebran.subset   # regenerate data/stage1_subset.json (deterministic)
uv run pytest                     # stage acceptance tests
```

## Running experiments

```sh
# single arm, single seed
uv run python -m clebran.baselines.b0 --seed 1 --budget 1000000

# any arm programmatically
uv run python -c "from clebran.baselines.arms import run_arm; run_arm('B2', seed=1, budget=1000000)"

# full sweep driver
uv run python -m clebran.baselines.arms --arms B0 B1 B2 B3 B4 --seeds 1 2 3 4 5 --budget 1000000

# B5+planner arm (paper 3, world-modeling direction)
uv run python -m clebran.baselines.b5_planner --seed 1 --budget 500000 --planner-lookahead 1

# build the world-modeling trace dataset
uv run python scripts/build_traces.py
# -> data/traces.jsonl, 16,149 (state, action, next_state) rows

# evaluate the L2 planner (single-pair, on the trace dataset)
uv run python -m clebran.world_model l2 --lookahead 1
```

Every run writes a JSONL log to `logs/<arm>_seed<...>.jsonl`: a `start` record
(config), `solve` records (task, evals consumed, program JSON, test-exact flag),
`epoch` records, and a final `summary` (solved sets, per-lineage breakdowns,
divergence, reuse rate, messages published). The **compute unit is
candidate-evaluations**, metered inside `fitness.Evaluator` — wall-clock never
enters any comparison.

## Reports

Three report surfaces, all reading `logs/`:

```sh
uv run python scripts/stage1_gate.py       # Stage-1 gate: per-seed D1 completeness
uv run python -m clebran.metrics.report    # terminal H2/H3 table, compute audit, verdicts
uv run python -m clebran.solver_card       # writes logs/report.html
```

The **solver card** (`logs/report.html`) is a single self-contained HTML page —
no dependencies, works offline, dark/light themed. It contains the experiment
explainer, the hypothesis→baseline mapping, a results table that auto-fills as
arm summaries appear in `logs/`, and one card per subset task showing the
demonstration pairs, the evolved program, and a **statement-by-statement
execution trace** with every intermediate register rendered as an ARC grid.
Regenerate it after any run; it picks up whatever logs exist. Frozen snapshots
of the card are kept inside each `experiments/` folder.

## Reproducibility

- The subset is generated, never hand-picked: `clebran.subset` is deterministic
  (fixed seed, lexicographic ordering, gate-checked) and its output is committed.
- Lineage seeds are explicit; per-task RNG substreams make single-task probes
  reproduce full-run behavior exactly.
- Completed experiments are frozen under `experiments/<date>_<name>/` with the
  verdict, the raw per-arm-seed summaries, the gate output, and the commit hash.
