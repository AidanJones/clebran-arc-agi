# B5 — the central-library control (2026-07-22)

The strongest "abstraction reuse without our idea" control (spec §7, §11), and
the **first statistically significant comparison in the project**. B5 is a
single population — like B0, all compute concentrated — that periodically mines
its own solutions into a growing abstraction library (the Stitch compression
miner) and reuses it: a DreamCoder/Stitch wake-sleep learner with **no
multi-agent divergence and no channel**. It asks the decisive question: does the
divergence + constrained-communication structure add anything over centralized
abstraction reuse?

## Setup

Frontier subset, matched compute 4M evals/run (audit 0.10%), 20 seeds,
evolution-phase solves. B5 run at the identical config to the scaled sweep so
all six arms are directly comparable. [analysis.txt](analysis.txt),
[b5_summaries.jsonl](b5_summaries.jsonl).

## Results (evolution-phase solves, n=20)

| arm | what | evo-solved /30 |
|---|---|---|
| **B5** | **single population + central library** | **2.65 ± 1.31** |
| B0 | single population | 2.25 ± 1.07 |
| B7 | recovered-primitive channel (unconstrained) | 1.85 ± 1.04 |
| B6 | recovered-primitive channel (constrained) | 1.80 ± 1.06 |
| B2 | fragment channel | 1.60 ± 0.99 |
| B1 | isolated lineages | 1.45 ± 0.94 |

| comparison | Δ (se) | verdict |
|---|---|---|
| **B6 − B5** | **−0.85 (0.38)** | **SIGNIFICANT (~2.2 se) — the channel is *worse* than a central library** |
| B5 − B0 | +0.40 (0.38) | directional (~1.1 se), not significant |

Vocabulary: B5 topsim **0.33** (vs B6/B7 0.14–0.15) and cross-task reuse **0.15**
(vs 0.05) — the single agent builds a *more compositional, more cross-task-
reused* library than the multi-agent arms.

## Verdict — the core hypothesis is falsified, rigorously

**B5 is the best arm, and it beats the recovered-primitive channel (B6)
significantly** (−0.85, ~2.2 se — the only significant comparison in the whole
study). The project's central claim — that *divergent lineages sharing over a
constrained channel* beat the alternatives at matched compute — is **not
supported; the strongest control wins.** Concentrating compute in one agent that
reuses its own abstractions dominates splitting it across divergent,
communicating lineages.

Why, mechanistically — the full ranking tells a coherent story:

    B5 (2.65)  >  B0 (2.25)  >  B7 (1.85) ≈ B6 (1.80)  >  B2 (1.60)  >  B1 (1.45)
    └ central library ┘        └ multi-agent + channel ┘   └ fragment ┘  └ isolated ┘

1. **Splitting compute is expensive** (the "divergence tax"): 3 isolated
   lineages (B1 1.45) fall well short of one population (B0 2.25).
2. **Communication pays back only part** of that tax (B6/B7 ≈ 1.8), never
   reaching B0.
3. **Meanwhile the *same* library mechanism, run centrally** (B5), not only
   avoids the tax but *adds* to single-population search — landing on top.

The reason B5's library is better is visible in the metrics: a single agent
sees *all* tasks, so its mined abstractions generalise across them (topsim 0.33,
cross-task 0.15) far better than a lineage that sees only the subset it happened
to solve. Divergence — the premise of H1 — is precisely what *degrades* the
shared vocabulary: partial views yield task-idiomatic abstractions (B6/B7
cross-task 0.05).

## What this does and doesn't say

- It is a **trustworthy, significant negative result**, exactly the outcome the
  spec's §1 designed the baselines to make believable: "If H2 fails, that is a
  real and publishable result." Here the failure is sharp — not just "no gain"
  but "the honest control significantly wins."
- It is scoped to **this frontier, this budget, pure-symbolic evolutionary
  search**. It does not say communication can never help — it says that on ARC
  program synthesis at matched compute, centralized abstraction reuse is the
  better use of the same compute than divergence + a constrained channel.
- The divergence that H1 confirmed is real, but it is a **liability** for
  vocabulary quality here, not the asset the hypothesis assumed.

## Implication for the write-up

The headline flips from "constrained gossip helps a little" to the stronger,
cleaner: **at matched compute on ARC, a single agent with a growing abstraction
library (DreamCoder/Stitch-style) significantly outperforms divergent lineages
communicating over a constrained channel.** The multi-agent machinery is a
well-instrumented, honestly-tested idea that the strongest baseline beats.
