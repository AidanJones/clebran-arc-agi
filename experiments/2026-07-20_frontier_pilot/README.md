# Frontier pilot — does the channel activate on a contested frontier? (2026-07-20)

A pilot, not a verdict. Follows the Stage-4 null (H2 not supported on the
Stage-1 subset) and its diagnosis: the shallow subset was closed by
deterministic phase-1 search in every arm, leaving no frontier for
communication to move. This pilot rebuilds the subset to be deep enough that
phase-1 is inert, then checks whether the channel does anything there.

## Setup

- **Subset:** [frontier_subset.json](frontier_subset.json) — 25 D2 + 5 D3 tasks
  (reference depth 3–10), no D1. Built with `clebran.subset.build_frontier`.
- **Measure:** evolution-phase solves only (`solved_evolution`) — tasks reached
  by the evolutionary loop, not by deterministic seeding. On this subset
  phase-1 closes ~0 by construction, so this ≈ total solves but is the honest
  treatment-relevant count.
- **Budget:** 3,000,000 candidate-evaluations/run (per-lineage ~1M, where a
  2M-eval B0 probe found single-population evolution solves appear).
- **Arms/seeds:** B1 (isolated) vs B2 (constrained fragment channel), seeds 1–2.
  Summaries in [pilot_summaries.jsonl](pilot_summaries.jsonl).

## Reachability probe (B0, 2M evals, seeds 1–2) — why 25 D2 / 5 D3

Evolution reached **only D2** tasks (3 distinct across 2 seeds, at 390k–1.17M
evals). **Zero** genuine D3 evolution solves — the lone D3 "solve" was a short
accidental depth-2 program, correctly tagged `phase1` by the new accounting.
D3 (depth 6–10) is beyond reach at feasible budgets, so the composition is
D2-heavy with a few D3 as stretch markers.

## Pilot result

| arm | seed 1 | seed 2 | mean evolution solves | reuse rate |
|---|---|---|---|---|
| B1 (isolated) | 1 | 2 | 1.5 | 0 (no channel) |
| B2 (constrained channel) | 1 | 3 | 2.0 | 0.67 – 1.00 |

Two observations, one soft and one hard:

- **(soft) Hint of the H2 direction.** B2 mean 2.0 > B1 1.5. On seed 2, B2
  solved `7468f01a` — a task B1 reached in neither seed — with a
  fragment-carrying program. n=2 and counts of 1–3 make this far too noisy to
  call; it could vanish or grow.
- **(hard) The channel mechanism activated.** Reuse rose from 0.06 on the
  Stage-1 subset to **0.67–1.00** here: on tasks deep enough to require
  composition, received fragments are actually incorporated into solutions.
  This is the mechanism H2 depends on, and it was essentially dormant before.
  The frontier rebuild did what it was meant to.

## Status

Held here by decision (2026-07-20) — the pilot is promising but resolving H2
needs more seeds (≥8) for the low counts. The mechanism-activation result
(reuse 0.06 → 0.67) stands on its own as evidence the frontier is the right
regime. Full B0–B4 × ≥8-seed frontier sweep is the sized, ready next step
(see [roadmap.md](../../roadmap.md) item 1).
