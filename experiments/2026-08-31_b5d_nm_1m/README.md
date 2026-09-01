# B5D-NM (failure-mode dreaming) 1M pilot (2026-08-31) — discovery-bottleneck #1

The first concrete test of the **discovery bottleneck** principle: the
lineage dreams from *near-miss* programs (high-fitness but not-fully-
correct) instead of from *solved* programs. The hypothesis: variants
of the near-miss force the lineage to bridge the gap; bridging is
where new primitives are discovered.

A primitive version of the L3 evoker (9f.4): a lineage that
practises on its own failures, not its successes.

## Setup

- B5D-NM = B5 + dreaming from *near-miss* programs.
- After every epoch, for each unsolved task, find the best individual
  with `solved_frac >= 0.4` and not solved; if it has *changed* since
  last epoch, dream from it. (Threshold 0.4 = "we're getting close".)
- Frontier subset (25 D2 + 5 D3), 1M evals/run, **5 seeds** (1-5),
  matched compute (~0.05% spread).
- Compare to B5-1M (5 seeds) and B5D-1M (5 seeds, both from
  `experiments/2026-08-29_dreaming_pilot/`).
- Outputs: [cost.txt](cost.txt), [cost.json](cost.json),
  [library.txt](library.txt).

## Headline: tied on count, different library

| metric (1M, 5 seeds) | B5 | B5D (solved-source) | B5D-NM (near-miss) |
|---|---|---|---|
| frontier solves /30 | 10.40 ± 1.14 | 10.40 ± 0.55 | 10.40 ± 0.55 |
| evals/solve | 97,077 | 96,457 | 96,380 |
| welch-t p (vs B5) | — | 0.905 | 0.893 |
| welch-t p (vs B5D) | — | — | 0.981 |
| dreams added / seed | — | **287.2** | **10.6** |
| dreams solved / seed | — | 278.8 (97.0%) | 8.2 (77.4%) |
| library size (n) | 5.4 | 9.2 | 6.4 |
| used rate | 3.3% | **70.2%** | 21.7% |
| cross-task reuse | 0.0 | **5.0** | 0.8 |
| **topsim** | **0.264** | 0.047 | 0.152 |

*Sources:* [cost.txt](cost.txt), [library.txt](library.txt).

**Three findings in one:**

1. **Frontier: tied.** All three arms solve 10.40 frontier tasks.
   The discovery hypothesis is *not* supported at 1M. Failure-mode
   dreaming doesn't expand the frontier.

2. **Dream count: 27× lower than B5D.** B5D-NM only generates dreams
   when a *near-miss improves* (solved_frac >= 0.4 and program hash
   differs from last epoch). This is the right design — we don't
   want to spam dreams from the same near-miss every epoch — but
   it means the failure-mode library has 27× less material to
   work with.

3. **Library: between B5 and B5D.** Bigger than B5 (6.4 vs 5.4
   abstractions), more used (21.7% vs 3.3%), more reused (0.8 vs
   0.0). But smaller and less used than B5D (9.2 abstractions,
   70.2% used, 5.0 reused). The failure-mode library is *less
   active* than the solved-source library.

4. **Topsim: between B5 and B5D.** Failure-mode dreaming produces
   abstractions with topsim 0.152, more compositional than B5D's
   0.047 but less than B5's 0.264. The near-miss dreams produce
   *more compositional* abstractions than the solved-source
   dreams — a hint that the failure-mode mechanism is producing
   a different *kind* of abstraction, even if it doesn't produce
   more of them.

## What this means

The failure-mode mechanism is *engaged* (10.6 dreams per seed,
77% utilization) but *not amplifying* (the dream count is 27×
lower than B5D, the library is smaller and less used, and the
frontier is unchanged). The threshold 0.4 + "improved since last
epoch" filter is too restrictive to generate enough material for
discovery.

**Hypotheses for the next iteration:**

- **Lower the threshold** to 0.2 or even 0.1 — would find more
  near-misses, more dreams, more material. The risk: dreams from
  very weak near-misses might be uninformative (too distant from
  the original).
- **Drop the "hash differs" check** — dream from each task's best
  near-miss every epoch, regardless of whether it has improved.
  This caps at ~30 dreams per epoch, but in practice the
  near-miss only changes when search actually progresses.
- **Both** — lower threshold AND drop the hash check. Most
  aggressive: dream from every task with solved_frac >= 0.1 every
  epoch.

The natural next escalation is also the **4M test** of the current
mechanism, but the 27× lower dream count means the headline is
likely to be the same null. The most informative next move is to
try the more aggressive version at 1M (cheap, ~25 min) to see
if dream volume is the bottleneck.

## Honest scope

- n=5 seeds at 1M. The B5 and B5D baselines are also 5 seeds, so
  the comparison is matched.
- The dream count is small (2-23 per seed, mean 10.6), so the
  failure-mode library is thin. The mechanism is engaged but
  not amplifying.
- A larger sweep (4M) would tell us if the dream count grows
  with budget; the 1M-4M extrapolation is unclear because near-
  misses are a *frontier* phenomenon, and the frontier is shallow
  at 1M.
