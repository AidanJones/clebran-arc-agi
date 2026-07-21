# Recovered-primitive channel on the frontier (2026-07-21)

The item-3 payoff measurement: do lineages that gossip their *own discovered
subroutines* (recovered primitives) do better than isolated lineages or ones
sharing raw fragments over Hodel's given primitives? And does the constraint
matter for a discovered vocabulary?

## Setup

- Frontier subset (25 D2 + 5 D3), **matched compute** 3M candidate-evaluations
  /run (audit: 0.27% eval spread), **8 seeds**, 3 lineages.
- Arms: B0 single population · B1 isolated (no channel) · B2 constrained
  fragment channel · **B6 constrained abstraction channel** · **B7
  unconstrained abstraction channel**.
- Measured on **evolution-phase solves** (the only place a channel can act;
  phase-1 is inert on the frontier). [analysis.txt](analysis.txt),
  [summaries.jsonl](summaries.jsonl).

## Results (evolution-phase solves)

| arm | what | evo-solved /30 | reuse |
|---|---|---|---|
| B0 | single population | **2.12 ± 1.13** | — |
| B1 | 3 isolated lineages | 1.50 ± 0.53 | 0 |
| B2 | + constrained **fragment** channel | 1.38 ± 0.92 | 0.66 |
| B6 | + constrained **recovered-primitive** channel | 1.88 ± 0.99 | 0.67 |
| B7 | + unconstrained **recovered-primitive** channel | 2.12 ± 1.25 | 0.67 |

| comparison | Δ (se) | reads as |
|---|---|---|
| B6 − B1 | **+0.38** (0.40) | recovered-primitive transfer helps |
| B6 − B2 | **+0.50** (0.48) | recovered beats given-primitive transfer |
| B6 − B7 | −0.25 (0.56) | constraint does **not** help (H3) |
| B2 − B1 | −0.12 (0.38) | fragment transfer doesn't help |

Recovery/vocabulary: B6 vocab 4.5, used-rate 0.31, received-used 1.21, topsim
0.04; B7 vocab 5.6, used-rate 0.28, received-used 1.42, topsim 0.01.

## Verdict (honest, underpowered)

**The mechanism works, and works better than fragment-sharing — directionally.**

1. **The discovered vocabulary is actually used** (vs used-rate 0 on stage-1):
   used-rate ~0.30, reuse 0.67, and — the NEO-style signal — **received-used
   ≈ 1.2–1.4**: lineages solve tasks using primitives they were *handed and
   never derived*. Concrete example (B6): a lineage discovered a 4-statement
   mirror-tiling subroutine `vmirror→hconcat→hmirror→vconcat` and used it as a
   single named call to solve `62c24649` with a length-2 program.

2. **A divergence tax, and recovered primitives pay it back.** Splitting compute
   across 3 isolated lineages *underperforms* one big lineage (B1 1.50 < B0
   2.12). Fragment-sharing does not recover the deficit (B2 1.38). The
   recovered-primitive channel does: B6 1.88, **B7 2.12 — matching B0**. So
   sharing a *discovered vocabulary* makes divergent multi-lineage evolution
   competitive with concentrated single-population search, where raw-fragment
   sharing cannot. This is the §11 hypothesis (discovered > given) — directional
   (~1 se on both B6−B1 and B6−B2), consistent, mechanistically grounded.

3. **Nothing is significant.** Counts are 1–2 evolution solves/seed; at 8 seeds
   the se's (~0.4–0.5) swamp the ~0.4–0.5 effects. This is a *trustworthy
   directional* result, not a confirmed one. More seeds (or a higher-throughput
   engine to raise per-seed counts) are needed to call it.

4. **No H3 for the discovered vocabulary either** (B6 ≈ B7; unconstrained even
   nominally higher). Same mechanism as the item-2 dose-response: adaptive
   operator selection down-weights a failing channel, so unconstrained sharing
   doesn't crowd out mutation — the constraint stops mattering because the
   learner self-constrains. The constraint neither helps nor hurts here.

5. **The vocabulary is small and task-idiomatic, not yet strongly
   compositional.** topsim ≈ 0 and cross-task reuse ≈ 0.04–0.12: most
   abstractions help one task. A richer, more general vocabulary would need
   deeper tasks and/or a compression step (Stitch) rather than the frequency
   miner.

## Takeaway

On this frontier and budget: recovered-primitive communication is the best of
the channel variants and closes the divergence tax that fragment-sharing can't —
but does not significantly beat single-population B0, and the constraint (H3) is
null for discovered primitives just as it was for fragments. The result is a
clean, mechanistically-grounded *directional* signal for the project's core
§11 claim, held back only by statistical power. Next: more seeds, a Stitch-based
miner for a more compositional vocabulary, and deeper tasks where the divergence
tax (and thus the room for communication to help) is larger.
