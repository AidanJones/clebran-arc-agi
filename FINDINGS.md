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
| B2 | fragment channel (given primitives) | 1.60 ± 0.99 |
| B1 | isolated lineages, no channel | 1.45 ± 0.94 |

    B5 (2.65)  >  B0 (2.25)  >  B7 ≈ B6 (1.8)  >  B2 (1.6)  >  B1 (1.45)
    central lib   single pop    multi-agent+channel  fragment   isolated

Only one comparison in the entire study reaches significance: **B6 − B5 = −0.85
(~2.2 se)** — the channel is significantly worse than a central library.

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

- **B5 (the central-library control): significantly best.** One agent that
  reuses its own abstractions beats everything. Two forces explain the whole
  ranking: (1) splitting compute across lineages is a **tax** (B1 ≪ B0);
  (2) communication repays only part of it (B6/B7 < B0); (3) the *same* library
  mechanism run centrally avoids the tax and *adds* to search (B5 > B0). And a
  single agent sees *all* tasks, so its mined vocabulary generalises —
  topographic similarity 0.33 and cross-task reuse 0.15, versus 0.14–0.15 and
  0.05 for the multi-agent arms. **Divergence degrades vocabulary quality:**
  partial views yield task-idiomatic abstractions.

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
- **Communication through exported curricula** (roadmap 7b) — share *problems*,
  not code: a substrate-agnostic payload that sidesteps the "divergence degrades
  the shared vocabulary" failure this study found. The most promising untested
  idea.
- **B5 is not the ceiling either** — it points at centralized library learning
  (DreamCoder/Stitch proper) as the stronger direction for ARC program
  synthesis, with or without the multi-agent framing.
