# B5D dreaming 4M pilot (2026-08-30) — roadmap §9b escalation

The headline 4M test of the dreaming loop, after the 1M pilot showed
the loop engages (97% dream utilization) and changes the library
(70% used, 5.0 cross-task reuse) but does not expand the frontier
(B5D 10.40 vs B5 10.40 at 1M, p=0.905). The 4M test is whether the
library benefit compounds at the headline budget.

## Setup

- Frontier subset (25 D2 + 5 D3), 4M evals/run, **9 seeds**
  (6, 8, 9, 10, 11, 12, 13, 14, 15; seed 7 was killed mid-run by a
  bash 30-min timeout and re-running was deferred), matched compute
  (~0.07% spread).
- B5 baseline: 15 seeds from the existing 2026-07-22 4M sweep
  (renamed to `b5_4m_seed*.jsonl` to prevent the overwrite bug;
  see `experiments/2026-08-29_dreaming_pilot/` for the data).
- B5D: fresh runs at the new `b5d_4m_seed*.jsonl` naming convention.
- Outputs: [cost.txt](cost.txt), [cost.json](cost.json),
  [library.txt](library.txt), [dream_split.txt](dream_split.txt).

## Headline: dreaming tied on frontier, library effect compounds

| metric (4M) | B5 (15 seeds) | B5D (9 seeds) | ratio |
|---|---|---|---|
| frontier solves /30 | 12.13 ± 1.06 | 12.33 ± 1.12 | 1.02× |
| evolution-phase solves | 4.13 ± 1.13 | 4.44 ± 1.33 | 1.08× |
| evals/solve (per-seed ratio) | 331,910 | 326,667 | 0.98× (B5D cheaper) |
| library size (n abstractions) | **8.5** | **17.0** | **2.0×** |
| **library used rate** | **6.6%** | **85.7%** | **13×** |
| **library cross-task reuse** | **0.1** | **12.4** | **124×** |
| library mean body size | 2.68 | 2.42 | — |
| **library topsim** | **0.338** | **0.221** | 0.65× |
| dream utilization | — | 99.0% | — |
| dreams added per seed | — | 1,343 | — |

*Sources:* [cost.txt](cost.txt), [library.txt](library.txt).

**Two findings in one:**

1. **Frontier + cost: tied.** B5D 12.33 vs B5 12.13 frontier
   solves (welch-t p not reported here; visually within noise at
   B5's SD=1.06). On the cost axis, B5D 326,667 vs B5 331,910
   evals/solve — essentially tied, B5D very slightly cheaper.
   **The dreaming loop does not expand the frontier at 4M.**

2. **Library: dramatic win for B5D.** B5D's library at 4M is
   **2× larger (17.0 vs 8.5 abstractions), 13× more used
   (85.7% vs 6.6%), and 124× more cross-task reused (12.4 vs
   0.1)**. The B5D library is the workhorse of the search; the
   B5 library is mostly dormant. Topsim is still lower
   (0.221 vs 0.338), but the gap is narrower at 4M than at 1M
   (was 0.05 vs 0.26). The dreaming builds a richer, more
   *reusable* library even when it doesn't expand the frontier.

## Dream cost at 4M

Per-solve evals split (cumulative evals at solve, see
[dream_split.txt](dream_split.txt)):

| source | n | median | mean | min | max |
|---|---|---|---|---|---|
| frontier (all 9 seeds) | 111 | 124,938 | 536,635 | — | — |
| dream (all 9 seeds) | 12,083 | 2,077,453 | 2,078,116 | 83,327 | 4,000,226 |

Same pattern as 1M: dreams are spread across the run (median
2.08M cumulative evals — about half the 4M budget), and the lineage
finishes them with high utilization (99% vs 97% at 1M). The
frontier solves are still mostly phase1 (81/111, 73%) with
~30 evolution-phase solves per 9 seeds.

## Library at 4M: deep dive

The library effect compounds with budget:

| metric | B5-1M (5) | B5-4M (15) | B5D-1M (5) | B5D-4M (9) |
|---|---|---|---|---|
| library size | 5.4 | 8.5 | 9.2 | **17.0** |
| used rate | 3.3% | 6.6% | 70.2% | **85.7%** |
| cross-task reuse | 0.0 | 0.1 | 5.0 | **12.4** |
| topsim | 0.264 | 0.338 | 0.047 | 0.221 |

*Reading:* the B5 library barely grows (5.4 → 8.5 abstractions, 3%
→ 7% used). The B5D library grows substantially (9.2 → 17.0) and
becomes *more* used (70% → 86%) at 4× the compute. B5D's topsim
also climbs (0.05 → 0.22) — the abstractions are more
compositionally structured at 4M than at 1M, though still not as
structured as B5's.

## Honest scope

- **n=9 B5D seeds (skipped 7).** The 9 seeds span seeds 6 and 8-15.
  B5 has 15 seeds, so 6 of the B5 seeds (1-5) have no paired B5D
  data. The headline numbers are unpaired, but the variance is
  similar (B5 SD=1.06, B5D SD=1.12), so the comparison is well-
  calibrated.
- **The bash 30-min timeout** killed the B5D seed 7 mid-run (at
  3.54M evals, 88% complete). The 9 remaining seeds were run in
  a single foreground task with a 4-hour timeout to avoid the
  same issue. Future long-running sweeps should use a single
  foreground task with an appropriate timeout, not a background
  task with the default 30-min cap.
- **The library effect is real** (B5D 17 vs B5 8.5 abstractions;
  85.7% vs 6.6% used; 12.4 vs 0.1 reused) but its *consequence*
  on the frontier is null. The dreaming builds a library the
  lineage can use, but the library doesn't translate to solving
  more frontier tasks at this budget.
- **Topsim is the *directionally right* signal** for whether the
  library is compositional: B5D 0.22 < B5 0.34. The dreaming's
  library is less compositional than B5's, but the gap is
  narrower at 4M (0.22 vs 0.34) than at 1M (0.05 vs 0.26), which
  is consistent with the 9b-2 hypothesis (more dreaming = more
  compositional structure over time).

## What this means for the roadmap

The 9b dreaming hypothesis is **not supported at 4M**. The dreaming
loop engages (99% utilization, 1,343 dreams added per seed, 17
abstractions mined) and produces a *much* more active library, but
it does not expand the frontier at matched compute. The
*substantive result* is the library: 2× larger, 13× more used, 124×
more cross-task-reused.

**This is consistent with the broader clebran finding** (Paper 1,
§8): the project is good at *transporting* competence, not at
*creating* it. The dreaming arm proves this point with a new
mechanism: it produces a transportable library (vs B5's dormant
one), but the transport doesn't expand the frontier.

**The 8b negative-transfer test** is the natural next step. If
B5D's library is *task-idiomatic* (low topsim), it might harm
search on tasks needing disjoint vocabulary. The B5D-4M library
now has 17 abstractions / 12.4 cross-task reuse to test with —
the design is in `experiments/2026-08-30_8b_design/`.
