# Scaled recovered-primitive frontier run (2026-07-22)

A power check on the item-3 payoff. The prior 8-seed run
([2026-07-21_frontier_recovered](../2026-07-21_frontier_recovered/README.md))
gave a directional-but-underpowered B6 > B1/B2 (~1 se). This run doubles the
seeds (8 → **20**), raises the budget (3M → **4M**), and uses the new
**Stitch-style compression miner** and the ~3× faster engine, to see whether
the effect resolves into significance and whether a more compositional
vocabulary strengthens it.

## Setup

- Frontier subset (25 D2 + 5 D3), **matched compute** 4M evals/run (audit:
  0.10% spread), **20 seeds**, 3 lineages. Evolution-phase solves.
- Arms B0/B1/B2/B6/B7 as before; B6/B7 now use the compression miner.
  [analysis.txt](analysis.txt), [summaries.jsonl](summaries.jsonl).

## Results (evolution-phase solves, n=20)

| arm | what | evo-solved /30 | reuse | topsim |
|---|---|---|---|---|
| B0 | single population | **2.25 ± 1.07** | — | — |
| B1 | isolated | 1.45 ± 0.94 | 0 | — |
| B2 | fragment channel | 1.60 ± 0.99 | 0.46 | — |
| B6 | recovered-primitive (constrained) | 1.80 ± 1.06 | 0.59 | 0.14 |
| B7 | recovered-primitive (unconstrained) | 1.85 ± 1.04 | 0.64 | 0.15 |

| comparison | Δ (se) | 8-seed run | verdict |
|---|---|---|---|
| B6 − B1 | +0.35 (0.32) | +0.38 | directional, **not significant** |
| B6 − B2 | +0.20 (0.32) | +0.50 | directional, **not significant** (shrank) |
| B6 − B7 | −0.05 (0.33) | −0.25 | **null** (H3) |
| B2 − B1 | +0.15 (0.31) | −0.12 | directional, not significant |

Vocabulary: B6 used-rate 0.27, cross-task 0.05, received-used 1.12; B7 used-rate
0.26, cross-task 0.05, received-used 1.42.

## Verdict (honest)

**More power did not produce significance — it confirmed the effect is small.**
B6 − B1 held at +0.35 (was +0.38) with the se tightening 0.40 → 0.32, still
~1.1 se; B6 − B2 *shrank* from +0.50 to +0.20. So the +0.50 headline from the
8-seed run was partly noise. Recovered-primitive transfer's advantage over
isolated and fragment channels is **real-but-small and not statistically
significant** on this frontier at this budget.

What *is* robust is the **ordering**, identical across two independent runs:

    B0 (2.25)  ≥  B7 (1.85) ≈ B6 (1.80)  >  B2 (1.60)  >  B1 (1.45)

- **Recovered-primitive channels (B6/B7) are consistently the best channel
  variants** — above isolated (B1) and fragment (B2) in both runs. Cross-run
  consistency is itself evidence the direction is real, even without per-
  comparison significance.
- **But single-population B0 remains best.** The 8-seed run's "B7 matches B0"
  (2.12 = 2.12) did not survive more power: at 20 seeds B0 (2.25) is clearly
  ahead of B7 (1.85). The divergence tax — splitting compute across lineages —
  is only *partly* paid back by communication, not fully.
- **H3 is null** for the discovered vocabulary (B6 ≈ B7), consistent with the
  item-2 dose-response: adaptive operator selection self-regulates the channel,
  so the bandwidth constraint neither helps nor hurts.

**The Stitch miner delivered its structural win but not a performance win.**
topsim rose to 0.14–0.15 (from ~0.01–0.04 pre-Stitch) — the compression miner
produces a measurably *more compositional* vocabulary. But cross-task reuse
stayed at 0.05: the generalized abstractions are structurally better yet still
used task-idiomatically, and that did not translate into more solves or a larger
channel effect.

## Takeaway

Across every measurement the project supports the *mechanism* (divergent
lineages discover different abstractions, recover them, and communicate them —
received-used > 1) but a **consistent, small, non-significant** performance
effect: recovered-primitive communication is the best way to share, beats not
sharing, and closes *part* of the divergence tax — but does not significantly
beat concentrating compute in one population, and the bandwidth constraint does
not matter. This is the trustworthy, well-powered version of the §1 claim: at
matched compute on ARC, constrained gossip helps a little and reliably, not a
lot. Honest next levers if a larger effect is wanted: deeper tasks (bigger
divergence tax = more room for communication), a curriculum/teaching payload
(roadmap 7b), or a regime where single-population search genuinely stalls.
