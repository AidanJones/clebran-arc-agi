# Stage-4 verdict — H2/H3 at matched compute (Stage-1 subset)

**Date:** 2026-07-20 · **Budget:** 1,000,000 candidate-evaluations per arm ·
**Seeds:** 5 (1–5) · **Subset:** 30 tasks (10×D1, 15×D2, 5×D3), `data/stage1_subset.json` ·
**Compute audit:** mean-evals spread across arms 0.12% (PASS ±1%)

## The table

| arm | configuration | solved /30 | test-exact | reuse | divergence (Jaccard) |
|---|---|---|---|---|---|
| B0 | single population, all compute | **10.60 ± 0.55** | 10.40 ± 0.89 | — | — |
| B1 | 3 isolated lineages, union | 10.40 ± 0.55 | 10.40 ± 0.55 | 0.00 | 0.57 ± 0.10 |
| B2 | + CH-CONSTRAINED (K=4, M=3), fragments | 10.40 ± 0.55 | 10.40 ± 0.55 | 0.06 ± 0.06 | 0.57 ± 0.06 |
| B3 | + CH-UNCONSTRAINED, fragments | **9.80 ± 0.45** | 9.80 ± 0.45 | 0.17 ± 0.07 | 0.51 ± 0.09 |
| B4 | + CH-CONSTRAINED, signal payload | 10.40 ± 0.55 | 10.40 ± 0.55 | 0.00 | 0.59 ± 0.11 |

## Verdicts

**H1 (divergence): SUPPORTED.** Isolated lineages (B1) show mean pairwise
Jaccard distance 0.57 ± 0.10 over primitive usage — far from zero — and 4/5
seeds contain at least one task solved by exactly one lineage (up to 5 in a
seed). Divergent seeds/pools genuinely produce different strategies. The
premise of the channel experiment holds.

**H2 (transfer helps): NOT SUPPORTED at this subset and budget.**
B2−B1 = +0.00, B2−B0 = −0.20 (pooled se 0.35; both null). The channel is
demonstrably *active* (≈500 messages/run; 6% ± 6% of B2 solutions contain
received fragments) and compute is matched, so this is a trustworthy null,
not a broken experiment. Structural reading: at 1M evaluations the solvable
frontier is the D1 bucket plus 1–3 shallow D2 tasks, which the deterministic
phase-1 (depth-≤2 enumeration + constant sweeps) closes without needing
cross-lineage material; the deep D2/D3 tasks where fragment reuse should pay
are beyond *every* arm. There is no contested frontier for communication to
move.

**H3 (constraint matters): DIRECTIONALLY SUPPORTED, NOT SIGNIFICANT.**
B2−B3 = +0.60 (≈1.9 pooled se, just under the 2-se bar). Notably,
unconstrained sharing was the *worst* arm overall (9.80, below even B0) while
having the *highest* reuse (17%): dumped whole libraries get spliced into
offspring three times as often as constrained gossip and act as noise,
displacing productive mutation. The constraint at minimum prevents harm —
the stronger claim (that it *improves* transfer) needs a regime where H2 has
signal at all.

## What this means for the project

1. A null H2 on a frontier-free subset is the expected outcome of a healthy
   harness, per §1's own falsifiability framing. The next experiment must
   create a contested frontier: raise per-arm budget and/or rebuild the
   subset D2/D3-heavy (the §4.1 recipe supports re-stratifying), so tasks
   exist that single lineages fail but fragment-equipped lineages might reach.
2. B3's degradation is the most interesting single number: sharing *without*
   a bandwidth constraint measurably hurts at matched compute. This is
   direct, if preliminary, evidence for the information-bottleneck intuition
   behind H3.
3. Follow-ups in order: (a) frontier-building rerun of B0–B4; (b) the
   recovered-primitive channel (§11) once lineages abstract their own
   subroutines; (c) transfer–reconstruction gap tracking on deeper tasks.
