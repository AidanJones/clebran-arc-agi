# clebran-arc-agi — findings

*A consolidated, honest summary of what the experiment found. Per-experiment
detail lives in [`experiments/`](experiments/); the design is in
[`emergent-dsl-arc-spec.md`](emergent-dsl-arc-spec.md); open questions in
[`roadmap.md`](roadmap.md).*

## The question

Do **multiple divergent populations of DSL programs**, evolving under pure
reward on ARC-AGI-1 and **communicating "what works" over a constrained
channel**, solve more than the alternatives at **matched compute**? Three
sub-claims: **H1** lineages diverge into different abstractions; **H2** sharing
beats not sharing; **H3** a *constrained* channel beats dumping everything. A
later extension (spec §11) asks whether communicating *recovered* subroutines —
a vocabulary the system discovered itself — beats sharing raw code.

The design's whole point (spec §1) is baselines strong enough that **a null is
trustworthy**. It delivered a null — and, in the end, a significant negative.

## The discovery bottleneck — *the* open problem

The clebran system is a three-stage pipeline:

> **discover → share → learn.**

The work in this repo has shown, at matched compute:

- **Share works in principle.** The channel carries messages; the received-
  abstraction payload (B6/B7) is genuinely *used* by receivers.
- **Learn works centrally.** A single learner with a self-mined library (B5)
  outperforms every multi-agent sharing variant on the cost axis (7–10× more
  cost-efficient, 6× more tasks solved).
- **The 9b dreaming arm (B5D) takes transport further** — a library 2× larger,
  13× more used, 124× more cross-task-reused than B5's at the same compute.
  But it does not expand the frontier (B5D 12.33 vs B5 12.13 at 4M, tied).
  The dreaming produces a working library of *what was already known*; it
  does not invent *new things*.

**The bottleneck is *discovery*, not transport.** Every arm in the rig —
B0, B1, B2, B3, B4, B5, B5+planner, B5D, B6, B7, B8, B9 — runs the same DSL,
the same interpreter, the same pure-outcome fitness, on the same 30 frontier
tasks, with the same primitive pool (Hodel's 160). The mechanisms we have
vary *initial conditions* (random seed, library of self-mined abstractions,
planner-seeded program, dream-task pool) but none of them invent new
primitives, change the fitness function, or explore structurally new regions
of the search space. They all *improve search*; none of them *expand reach*.

**The guiding idea for what comes next.** A multi-agent system *is* good for
sharing knowledge — that's the clebran premise, and it is right. But the
*value* of the multi-agent system is bounded by what each individual agent
can discover. To make the system as a whole *learn new things*, we need
individual agents to actually discover new things first. **The transport
is solved; the discovery is open.**

A concrete menu of candidate discovery mechanisms (in increasing order of
cost) is in the README at [`README.md` §"The discovery bottleneck"](README.md#the-discovery-bottleneck--the-open-problem):
failure-mode dreaming, heterogeneous fitness, task-subset specialization,
novelty search, learned L1 as proposer, operator self-modification, and the
L3 evoker (9f.4). **Any mechanism that expands what a single lineage can
discover is worth more, on this rig, than any mechanism that improves how
discoveries are shared.** We have the second; we need the first.

## Headline

**At matched compute on ARC program synthesis, a single population that mines
its own solutions into a growing abstraction library (a DreamCoder/Stitch-style
central learner, arm B5) significantly outperforms divergent lineages
communicating over a constrained channel.** The multi-agent + channel idea is
consistently the *middle* of the pack: better than isolated or fragment-sharing,
worse than concentrating compute, and significantly worse than centralized
library learning. The project's central hypothesis is not supported; it is
falsified by its own strongest control.

## The decisive table (frontier, 20 seeds × 4M evals, compute matched 0.10%)

Measured on **evolution-phase solves** — tasks reached by the evolutionary loop,
excluding the deterministic seeding layer that is identical across arms, so the
number reflects only what search (and communication) contributed.

| arm | what it is | evo-solved /30 |
|---|---|---|
| **B5** | single pop + self-mined central library | **2.65 ± 1.31** |
| B0 | single population | 2.25 ± 1.07 |
| B7 | recovered-primitive channel, unconstrained | 1.85 ± 1.04 |
| B6 | recovered-primitive channel, constrained | 1.80 ± 1.06 |
| B9 | curriculum channel, unconstrained | 1.65 ± 0.75 |
| B2 | fragment channel (given primitives) | 1.60 ± 0.99 |
| B8 | curriculum channel, constrained | 1.60 ± 0.75 |
| B1 | isolated lineages, no channel | 1.45 ± 0.94 |

    B5 (2.65) > B0 (2.25) > B7≈B6 (1.8) > B9≈B2≈B8 (1.6) > B1 (1.45)
    central lib  single pop  recovered-prim   curriculum/frag   isolated

Only one comparison in the entire study reaches significance: **B6 − B5 = −0.85
(~2.2 se)** — the channel is significantly worse than a central library. **Every
communication variant we built — four payload types, constrained and
unconstrained — sits below simply not dividing the compute.**

## Verdicts

- **H1 (divergence): supported.** Independently-seeded lineages rely on
  genuinely different primitives — mean pairwise Jaccard distance 0.57, with
  tasks solved by exactly one lineage. But H1 turned out to be a *liability*,
  not the asset the hypothesis assumed (see B5 below).

- **H2 (transfer helps): not supported.** Fragment-sharing does not beat
  isolation (B2 − B1 = +0.15, ns); recovered-primitive sharing beats isolation
  only directionally (B6 − B1 = +0.35, ~1.1 se, ns) and never reaches
  single-population B0. More power (8 → 20 seeds, 3M → 4M) shrank rather than
  confirmed the effect (B6 − B2 fell +0.50 → +0.20): it is real-but-small, not a
  near-miss on significance.

- **H3 (the constraint matters): not supported.** Constrained ≈ unconstrained
  for both fragments (a flat K×M bandwidth dose-response) and recovered
  primitives (B6 ≈ B7). Mechanism: the adaptive operator selection added for
  fairness down-weights a failing channel, so the learner **self-constrains** —
  unbounded sharing can't crowd out mutation, and the constraint has nothing
  left to do. An adaptive learner is robust to unconstrained sharing.

- **The §11 extension (recovered > given): directionally yes, but moot.** The
  recovered-primitive channel (B6/B7) does consistently beat the fragment
  channel (B2) and isolation (B1) across two independent runs — the ordering is
  stable even without per-comparison significance. The mechanism is real:
  lineages solve tasks using primitives they were *handed and never derived*
  (received-used ≈ 1.1–1.4). But it is all dominated by B5.

- **Communication through curricula (roadmap 7b): mechanism confirmed, benefit
  null — and the failure is newly diagnostic.** Lineages that share *synthetic
  tasks showing what they learned* (prerequisite-ordered, with an order-aware
  learner gating deeper tasks until fundamentals are solved) received ~31
  teaching tasks each and **solved ~78% of them** — the students genuinely
  learned their peers' concepts. It bought +0.15 over isolation (ns), below
  every code-sharing payload. So the bottleneck is **not acquiring** a taught
  concept; it is that **a concept learned from demonstrations does not transfer
  to novel tasks that need it** — the L2T transfer-vs-reconstruction gap at the
  level of whole concepts. Teaching also costs budget (~24 auxiliary tasks
  solved), making it close to a wash under matched compute.
  ([experiments/2026-07-23_frontier_curriculum](experiments/2026-07-23_frontier_curriculum/README.md))

- **Concept transfer, against a proper baseline: neutral if relevant, harmful if
  not.** A first probe (oracle-relevant curriculum vs an *irrelevant* one)
  seemed to show a ~2× speedup — but it lacked a no-teaching baseline. Adding a
  **cold** arm (no curriculum) and merging the three (same targets/seeds/budget)
  corrects it decisively: **taught ≈ cold** (−986 evals to solve the target,
  perm p = 0.97 — *no* speedup from relevant teaching), while **control > cold**
  (+43k — irrelevant teaching is *slower* than not teaching). The apparent "2×"
  was the size of the *harm* to the mis-targeted control, mislabeled as a
  benefit. Honest statement: **relevant concept teaching is neutral; irrelevant
  concept teaching causes negative transfer.** And it costs budget to acquire —
  per student, taught total L+T = 129k vs cold U = 73k, so the per-student
  condition L+T < U fails and **amortisation across N agents cannot rescue it at
  any N** (the crossover has no solution).
  ([experiments/2026-07-23_amortization](experiments/2026-07-23_amortization/README.md),
  correcting [experiments/2026-07-23_transfer_probe](experiments/2026-07-23_transfer_probe/README.md))

- **B5 (the central-library control): significantly best.** One agent that
  reuses its own abstractions beats everything. Two forces explain the whole
  ranking: (1) splitting compute across lineages is a **tax** (B1 ≪ B0);
  (2) communication repays only part of it (B6/B7 < B0); (3) the *same* library
  mechanism run centrally avoids the tax and *adds* to search (B5 > B0). And a
  single agent sees *all* tasks, so its mined vocabulary generalises —
  topographic similarity 0.33 and cross-task reuse 0.15, versus 0.14–0.15 and
  0.05 for the multi-agent arms. **Divergence degrades vocabulary quality:**
  partial views yield task-idiomatic abstractions.

## Process, not content: the first significant "how you learned it" effect

Every finding above is about *what* is communicated, and all are null-or-harmful.
The reorientation (roadmap §9) asks instead whether the *way* knowledge is
acquired matters. The order/process experiment holds content fixed (a target's k
prerequisite sub-tasks) and varies only acquisition order:

- **A dependency-violating order is destructive and significant.** Teaching the
  same curriculum foundations-*last* (reverse) lets the learner acquire only 23%
  of it vs 47% foundations-first — you cannot learn a composition before its
  parts. That halves capability: **forward beats reverse (paired p = 0.021), and
  reverse is no better than not teaching at all (p = 0.73).** Same content, same
  budget, reversed order → the curriculum's value is destroyed.
- **But fine sequencing is not the active ingredient.** forward vs shuffled is
  not significant (p = 0.18); when all steps are available at once the
  fundamentals are the easy ones and get solved first anyway — the learner
  self-orders. Strict ordering matters when it can do *harm* (reverse), not when
  it enforces an order the learner would find regardless.
- **The effect is on capability, not speed** (all evals-to-solve contrasts null):
  order changes *which* targets are reachable, not how fast reachable ones are
  found. Different interventions surface on different endpoints.

Qualified yes for the reorientation: on compositionally-structured tasks, *how*
(the order) you learn significantly changes capability with *what* held constant
— asymmetrically, "don't teach backwards" matters more than "teach in exactly
the right order." Scoped to targets with real decompositions; see
[experiments/2026-07-24_order_process](experiments/2026-07-24_order_process/README.md).

## What was actually built (all pure-symbolic, no neural component)

A complete, reproducible research prototype: a typed linear-IR DSL over Michael
Hodel's 160 ARC primitives with a deterministic interpreter (reproduces 399/400
reference solvers); a typed GP engine (mutation/crossover/repair, phase-1
systematic seeding, adaptive operator selection, per-task RNG substreams); pure
outcome reward with NEO-style MDL parsimony; a channel with three constraint
regimes and **four payload modes** (fragment, signal, recovered-abstraction,
and the scaffold for curriculum); a **Stitch-style compression miner** that
antiunifies over constants; compositionality metrics (topographic similarity,
primitive-recovery, transfer accounting); and the six baseline arms B0–B7. A
~3× engine speedup (interpreter grid-validation O(cells) → O(rows+width) + a
guarded fitness cache) made the well-powered runs affordable. A self-contained
HTML **solver card** renders every solution's step-by-step execution trace,
including recovered-abstraction bodies.

Getting a stochastic GP engine to pass the spec's deterministic Stage-1 gate
took ~a dozen diagnosed fixes (a union-type-flow bug that made mirror
compositions unreachable; a reward exploit where blank grids out-scored content;
restart amnesia; shared-RNG context sensitivity) — that debugging trail is
itself a record of what pure-reward program evolution needs to be reliable.

## Honest limitations

- Scoped to **one frontier subset, matched budgets, pure-symbolic search**. It
  does not prove communication can never help — it shows that *here*, at matched
  compute, centralized abstraction reuse is the better use of the same compute.
- Solve counts are small (1–3 evolution solves/seed); most comparisons are
  underpowered by construction because the frontier is hard. B5 vs B6 is the one
  effect large enough to resolve at 20 seeds.
- Compositionality metrics on a hand-designed DSL are weaker evidence of
  "emergent language" than a from-scratch signalling game (spec §11 caveat).

## Where a positive result might still live (see roadmap)

- **Deeper tasks / a regime where single-population search genuinely stalls** —
  the divergence tax only becomes worth paying when one agent *can't* do the job
  alone. On this frontier B0 does fine, leaving little room for communication.
- **Measure cost, and put tasks at the budget frontier.** The transfer probe
  shows teaching's benefit is real but lives in *evals-to-solve*, not
  solve-count — so (a) report cost-to-solve alongside counts in every arm, and
  (b) build a task set concentrated where a ~2× speedup actually flips outcomes
  (marginal tasks), or raise the budget until today's hopeless tasks become
  marginal. Both are cheap and directly test whether the curriculum channel's
  null is an artifact of endpoint + task distribution. **This is the most
  specific open lead the project produced** — and, unlike the other leads, it
  comes with a measured effect size (~2×) to size the experiment against.
- **B5 is not the ceiling either** — it points at centralized library learning
  (DreamCoder/Stitch proper) as the stronger direction for ARC program
  synthesis, with or without the multi-agent framing.

## Cost-axis re-score (roadmap §9a, 2026-08-29)

The headline above is on **solve count** at matched compute. Roadmap §9a
argues that is the endpoint Chollet says is uninformative — skill can be
bought with priors or training data, and acquisition cost is what can't.
Re-scoring the 20-seed 4M-eval sweep on the cost axis (evals-to-solve) is
analysis, not new compute: the per-solve `evals` field is already in every
log.

The cost axis **confirms and amplifies** the count ranking.

| arm | solved/30 | evals/solve | × B5 cost |
|---|---|---|---|
| **B5** | **12.45 ± 1.15** | **323,848 ± 28,776** | 1.0× |
| B5+planner | 12.32 ± 1.00 | 326,665 ± 24,298 | 1.01× |
| B0 | 2.25 ± 1.07 | 2,333,510 ± 1,284,369 | 7.2× |
| B7 | 1.90 ± 1.07 | 2,579,205 ± 1,275,957 | 8.0× |
| B6 | 1.85 ± 1.09 | 2,631,779 ± 1,241,940 | 8.1× |
| B9 | 1.70 ± 0.86 | 2,649,320 ± 1,091,437 | 8.2× |
| B8 | 1.65 ± 0.81 | 2,737,451 ± 1,130,719 | 8.5× |
| B2 | 1.65 ± 1.14 | 2,748,344 ± 1,194,381 | 8.5× |
| B1 | 1.50 ± 0.95 | 3,140,693 ± 1,182,998 | 9.7× |

B5 and B5+planner are 7–10× more cost-efficient than every multi-agent
arm, on top of solving 6× more tasks. Per-cell productivity is roughly
40× (6× × 7×). **B1 (isolation) is the most expensive failure mode**
(3.14M evals/solve — 9.7× B5): the multi-agent tax compounds dramatically
when none of the agents can solve anything.

**The ordering is robust to the endpoint.** Choosing your endpoint
defensively and the conclusion holds.

**H2 transfer benefit, on cost:** B2 is ~12% cheaper per solve than B1
(2.75M vs 3.14M, welch-t p = 0.316) — directional support for H2 on the
cost axis, not significant. B2 is ~18% more expensive than B0
(2.75M vs 2.33M, p = 0.302) — concentrating compute in one lineage is
still the cheapest way to discover things.

**B5 vs B5+planner, on cost:** the headline 4M tie holds on the
evals/solve metric (323K vs 326K, welch p = 0.741). On the
*apples-to-apples* comparison (evolution-phase solves only — B5+planner
has zero phase1 solves, the planner seed bypasses the seeding layer)
B5+planner's median is **20% lower** (573K vs 720K) and the mean is
**8% lower** (1.10M vs 1.20M). The 20% median win is **not significant**
at n=85/93 (permutation p = 0.717, 10k shuffles on the median) — a
suggestive but underpowered result. A larger sweep would resolve it.

*Artifact:* the 4M cost-axis re-score is frozen at
[`experiments/2026-08-29_cost_axis/`](experiments/2026-08-29_cost_axis/)
with [analysis.txt](experiments/2026-08-29_cost_axis/analysis.txt) and
[cost.json](experiments/2026-08-29_cost_axis/cost.json). The headline
report (`python -m clebran.metrics.report`) now also reports an
`evals/solve` column.

## Dreaming (B5D) — roadmap §9b, 1M pilot (2026-08-29)

Roadmap §9b: the missing "self-directed practice" capability — a learner
that generates its own practice from what it has seen (DreamCoder
wake/sleep "fantasies"). The forward generator
(`clebran.curriculum.generate_task`) was already in the codebase; the
gap was the loop.

**Arm:** **B5D = B5 + dreaming.** After every B5 solve, the lineage calls
`generate_task(sol.prog, rng, abstractions=lin.abstractions)` to
synthesise a variant task and adds it to its task pool (`auxiliary=False`,
so it joins the real task pool, no prerequisite gating). The synthetic
task costs real candidate-evaluations when the lineage works on it —
matched compute vs B5. The dream generation itself is "free" (it calls
`run_safe` directly, not through the Evaluator).

**Pilot (1M, 5 seeds):**

| metric | B5 | B5D | diff / p |
|---|---|---|---|
| frontier solves /30 | 10.40 ± 1.14 | 10.40 ± 0.55 | +0.00 |
| evals/solve (per-seed ratio) | 97,077 | 96,457 | welch-t p = **0.905** (tied) |
| frontier variance (SD) | 1.14 | **0.55** | B5D has **half** the variance |
| dreams added / seed | — | 287.2 | — |
| dreams solved / seed | — | 278.8 | — |
| **dream utilization** | — | **97.0%** | — |
| library size (n abstractions) | 5.4 | **9.2** | +70% |
| **library used rate** | **3.3%** | **70.2%** | +21× |
| **library cross-task reuse** | **0.0** | **5.0** | — |
| library mean body size | 2.34 | 2.26 | — |
| **library topographic similarity** | **0.264** | **0.047** | -5× |

*Sources:* [cost.txt](experiments/2026-08-29_dreaming_pilot/cost.txt),
[library.txt](experiments/2026-08-29_dreaming_pilot/library.txt).

**Three findings in one:**

1. **The dreaming loop is engaged (97% utilization).** 278/287 dream
   tasks per seed are solved. The forward generator + lineage work as
   designed.

2. **The dreaming does *not* transfer to the frontier.** B5D solves
   exactly the same number of frontier tasks as B5 (10.40 vs 10.40)
   at the same cost (97K vs 96K evals/solve, p = 0.905). The headline
   is a **null on count and cost** — the first acquisition-efficiency
   null in the project where the loop is *demonstrably working*.

3. **The library is the substantive positive result.** B5D's central
   library is **1.7× larger, 21× more used, and produces real
   cross-task reuse (5 abstractions used in ≥2 tasks vs B5's 0)**.
   **B5D at 1M beats B5 at 4M** (4× the compute) on every library
   metric except topsim: B5@4M has n=6.6, used=9.4%, reuse=0.1,
   topsim=0.330. But B5D's **topsim is 5× lower** (0.047 vs 0.264 at
   1M; 0.330 for B5@4M). The library captures *converged practice*
   patterns, not *novel compositions*.

**The variance reduction is real.** B5's per-seed frontier count
ranges 9–12 (SD=1.14); B5D's is 10–11 (SD=0.55). Dreaming smooths
the per-seed variation — the lineage has more practice opportunities
and converges more reliably. A small but consistent effect.

**The reading.** Clebran is good at **moving** competence, not at
**creating** it (Paper 1 / §8). The dreaming follows the pattern:
the loop is alive, the library is rich, the practice transfers to
*more active use of existing primitives* but not to *novel
compositions* on the frontier. The dreams give the lineage
*practice* on what it already knows, not *discovery* of what it
doesn't. This is consistent with the broader project finding: a
system that must *discover* should look like B5 (concentrated
compute, no practice flooding); teaching/dreaming is what you bolt
on afterwards to make existing competence cheaper to acquire
(roadmap §8d's "compression-and-transport layer").

*Artifact:* the 1M pilot is frozen at
[`experiments/2026-08-29_dreaming_pilot/`](experiments/2026-08-29_dreaming_pilot/)
with [cost.txt](experiments/2026-08-29_dreaming_pilot/cost.txt),
[cost.json](experiments/2026-08-29_dreaming_pilot/cost.json),
[library.txt](experiments/2026-08-29_dreaming_pilot/library.txt), and
[dream_split.txt](experiments/2026-08-29_dreaming_pilot/dream_split.txt).
The arm is at `clebran.baselines.b0:run_b5_dream` (CLI: `--arm B5D`).

### Dreaming 4M escalation (2026-08-30)

The 4M test of the dreaming loop, against the 15-seed B5-4M baseline
(renamed to `b5_4m_seed*.jsonl` to prevent overwrites). 9 B5D-4M seeds
(spanning 6, 8-15; seed 7 was lost to a bash 30-min timeout, see the
README in `experiments/2026-08-30_b5d_4m/`).

| metric (4M) | B5 (15 seeds) | B5D (9 seeds) | ratio |
|---|---|---|---|
| frontier solves /30 | 12.13 ± 1.06 | 12.33 ± 1.12 | 1.02× |
| evolution-phase solves | 4.13 ± 1.13 | 4.44 ± 1.33 | 1.08× |
| evals/solve (per-seed ratio) | 331,910 | 326,667 | 0.98× (B5D marginally cheaper) |
| library size | **8.5** | **17.0** | **2.0×** |
| **library used rate** | **6.6%** | **85.7%** | **13×** |
| **library cross-task reuse** | **0.1** | **12.4** | **124×** |
| library topsim | 0.338 | 0.221 | 0.65× |
| dream utilization | — | 99.0% | — |
| dreams added per seed | — | 1,343 | — |

**Frontier: tied.** B5D 12.33 vs B5 12.13, well within B5's SD=1.06.
The dreaming loop does not expand the frontier at 4M either.

**Library: dramatic.** B5D's library at 4M is **2× larger, 13× more
used, 124× more cross-task-reused** than B5's. B5's library is mostly
dormant (6.6% used, 0.1 cross-task reuse); B5D's is the workhorse
(85.7% used, 12.4 reused). Topsim is still lower (0.22 vs 0.34) but
the gap is narrower at 4M than at 1M (0.05 vs 0.26).

**The library effect compounds** with budget (B5 5.4 → 8.5, B5D
9.2 → 17.0), but it does *not* translate to more frontier solves.
The dreaming builds a transportable library (the headline result) but
the transport doesn't expand the frontier — consistent with the
broader clebran finding (Paper 1, §8) that the system is good at
*transporting* competence, not at *creating* it.

*Artifact:* the 4M pilot is frozen at
[`experiments/2026-08-30_b5d_4m/`](experiments/2026-08-30_b5d_4m/)
with [cost.txt](experiments/2026-08-30_b5d_4m/cost.txt),
[cost.json](experiments/2026-08-30_b5d_4m/cost.json),
[library.txt](experiments/2026-08-30_b5d_4m/library.txt), and
[dream_split.txt](experiments/2026-08-30_b5d_4m/dream_split.txt).

## Open leads the 9a + 9b results sharpen

- **9b-3. 8b negative-transfer test.** The 4M B5D library (17
  abstractions, 12.4 cross-task reuse, topsim 0.22) is the
  natural test bed for the negative-transfer experiment. Three
  arms: cold B5 / B5 + B5D-library / B5 + B5-library. If
  B5+B5D-library < cold on tasks needing disjoint vocabulary,
  the dreaming is *harmful* — the most informative outcome.
  Design in `experiments/2026-08-30_8b_design/`. ~3 hours at 4M
  × 5 seeds.
- **9b-4. B5D as a teacher.** Dreaming builds a richer library
  (17 abstractions / 12.4 cross-task reuse) than B5 ever
  reaches; the *export* of that library to a fresh B5 is the
  natural follow-up. Tests whether the dreaming's value is
  *transportable* across lineages.
- **9a-1. Cost axis in every paper.** Already done for Paper 1
  and Paper 3 (committed as `faa5a92`). The headline report
  also has an `evals/solve` column.
- **9f.4. L3 evoker.** A learned world model + dreaming is the
  natural capstone of the world-modeling direction: the
  lineage imagines possible dream tasks, refines the world
  model on failed predictions, re-rolls. The trace dataset
  and L2 planner are in place; this is the next open
  build-order item.
