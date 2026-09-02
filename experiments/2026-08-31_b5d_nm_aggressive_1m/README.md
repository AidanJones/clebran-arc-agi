# B5D-NM aggressive 1M pilot (2026-08-31) — discovery-bottleneck #1, the null

The follow-up to the conservative B5D-NM 1M pilot
(`experiments/2026-08-31_b5d_nm_1m/`). The conservative B5D-NM
(threshold 0.4, "hash-differs" check) was tied with B5/B5D-1M at
10.4 frontier solves — a null. The natural hypothesis: the
mechanism is *correct* but the dream volume is too low (only
5-10 dreams/seed). The aggressive variant lowers the threshold
to 0.2 and drops the hash-differs check (dream from every task's
best near-miss every epoch), so it generates 30× more dreams.

**The result: the aggressive variant is significantly *worse* than
B5 baseline (p=0.007).** Failure-mode dreaming at higher dream
volume is *subtractive* — the lineage wastes budget on harder
near-miss dreams that don't transfer to the frontier.

## Setup

Same as the conservative pilot, but two changes:
- `near_miss_min`: 0.4 → **0.2** (lower threshold, more dreams).
- `dream_near_miss_aggressive`: True (drop the hash-differs check).

Frontier subset, 1M evals/run, **5 seeds** (1-5), matched compute.
Saved to `b5d-nm-aggr_1m_seed*.jsonl` to avoid overwriting the
conservative data.

## Headline: aggressive failure-mode dreaming is *worse*

| arm | frontier | evo-solved | evals/solve | dreams/seed |
|---|---|---|---|---|
| **B5** (baseline) | 10.40 ± 1.14 | 3.20 ± 0.84 | 97,077 | — |
| B5D (solved-source) | 10.40 ± 0.55 | 3.20 ± 0.84 | 96,457 | 287.2 |
| B5D-NM-cons (threshold 0.4) | 9.80 ± 0.45 | 2.60 ± 0.55 | 102,230 | 5.2 |
| **B5D-NM-aggr** (threshold 0.2) | **8.80 ± 0.84** | **1.60 ± 0.55** | **115,183** | **311.0** |

*Sources:* [cost.txt](cost.txt).

**The regression is significant:**
- welch-t p (B5D-NM-aggr vs B5, evals/solve): **0.007** — *significant*
- welch-t p (B5D-NM-cons vs B5, evals/solve): 0.321 — not significant
- The aggressive variant solves 1.6 fewer frontier tasks on average
  (-15% from baseline), with 60× more dreams than the conservative.

**Two findings in one:**

1. **Failure-mode dreaming is *subtractive* at high volume.** The
   lineage produces 311 dreams/seed (matching B5D's 287), but
   the dreams are *harder* (lower utilization, presumably because
   the near-misses are at lower fitness) and the budget spent on
   them is *not* offset by frontier discoveries. The mechanism
   doesn't transfer; it just consumes budget on uninformative
   practice.

2. **The lower threshold (0.2) produces more dreams but not
   *better* dreams.** The dreams are still generated from
   *near-miss programs that haven't yet solved the task*. At
   0.2, those programs are *very far* from solving — the
   lineage has barely started to find the right primitives.
   Variants of those programs are easy to generate but hard
   to solve, and don't teach the lineage anything new.

## Why this is the discovery-bottleneck null

The roadmap §9b #1 hypothesis was: "dreams from near-miss programs
force the lineage to bridge the gap; bridging is where new
primitives are discovered." The data says no:

- The mechanism *engages* (dreams are generated and added to
  the pool).
- The dreams are *not* trivially easy (utilization is moderate,
  not 97% like B5D's solved-source dreams).
- The lineage spends budget on the dreams.
- But the *frontier does not expand* — in fact, it *contracts*
  (8.80 vs 10.40, p=0.007).

The pattern is consistent with the broader clebran finding
(Paper 1, §8; roadmap §8d): **the system is good at *transporting*
competence, not at *creating* it.** Failure-mode dreaming is a
new transport mechanism (the library it produces is *different*
from B5D's — more compositional topsim, more used-rate than B5 but
less than B5D), but the transport doesn't expand the frontier.

## What this means for the other discovery mechanisms

The failure-mode result is *especially* informative because:

- It uses a *new* source of programs (near-miss, not solved).
- The dreams are *substantively different* from solved-source
  dreams (variants of "we're close" vs variants of "we got it").
- The mechanism is engaged (dreams added, lineage works on them).
- The mechanism *transports* something (the library is different).
- But the mechanism doesn't *create* anything (the frontier is
  the same or worse).

This is a strong null. The remaining 6 candidates (#2-#7 in
README) are the *next* bets, but the bar is now high: the
candidate needs to expand the frontier, not just change the
library. **Discovery is harder than practice.**

## Honest scope

- n=5 seeds at 1M. The conservative pilot at 1M had a similar
  trend (9.80 frontier, slightly worse than baseline) but
  smaller effect. The aggressive variant amplifies the
  regression.
- The 4M test of either B5D-NM variant is not run; the 1M
  null is informative enough to call the mechanism a null
  on this rig. A 4M test would just take more budget for the
  same null.
- The cost axis (per-seed evals/solve) tells the same story:
  B5D-NM-aggr is the *worst* of the dreaming arms (115,183
  evals/solve vs B5D's 96,457). The mechanism is more
  expensive on the cost axis too.

## What would actually find new things

The failure-mode result narrows the search. The remaining
candidates are listed in `README.md` §"The discovery bottleneck".
The most promising:

- **#2 (heterogeneous fitness)** — change *what* the lineage
  values. The failure-mode result says dreaming on what
  the lineage has *almost found* doesn't help. Maybe
  optimizing for a different objective (length, diversity,
  novelty) would.
- **#4 (novelty search)** — explore the *space of programs*
  rather than the *frontier of solved tasks*. A program that
  produces a unique output grid (different from any other
  program) is *novel* by definition, and novelty search has
  historically found *new* solutions on hard problems.
- **#5 (learned L1 as proposer)** — use the 16K-row trace
  dataset to learn a *generative model* of programs. A
  learned L1 can propose programs the GP has never seen.
- **#7 (L3 evoker)** — the world model that improves on
  failed predictions. The capstone of the world-modeling
  direction.

The discovery bottleneck principle still holds: **we need
mechanisms that expand what a single lineage can discover, not
mechanisms that improve how discoveries are shared.** The
failure-mode pilot is a clean null on the most natural next
candidate. The remaining bets are harder.
