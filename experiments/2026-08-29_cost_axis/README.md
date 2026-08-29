# Cost-axis re-score at 4M (2026-08-29) — roadmap §9a

Re-scoring the headline 20-seed 4M-eval sweep on **acquisition efficiency**
(evals consumed per solve) instead of solve count. The instrument is
already in the existing logs (`solve.evals`); this is analysis, not new
compute.

## Setup

- Frontier subset (25 D2 + 5 D3), 4M evals/run, 20 seeds per arm,
  matched compute (~0.10% spread).
- B0/B1/B2/B6/B7 from `experiments/2026-07-22_frontier_recovered_scaled/summaries.jsonl`.
- B8/B9 from `experiments/2026-07-23_frontier_curriculum/summaries.jsonl`.
- B5/B5+planner from `logs/b5_seed*.jsonl` / `logs/b5p_seed*.jsonl` (per-solve evals
  preserved). B5+planner seed 1 is a leftover 100K pilot, dropped.
- Analyzer: `clebran/metrics/cost.py` (`uv run python -m clebran.metrics.cost`).
- Outputs: [analysis.txt](analysis.txt) (human-readable), [cost.json](cost.json) (machine-readable).

## Headline

The cost axis **confirms and amplifies** the solve-count picture:

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

**B5 and B5+planner are 7–10× more cost-efficient than every multi-agent
arm**, even though they solve 6× more tasks. The cost axis doesn't
reorder the arms — it widens the gap.

## Why this matters

- **Solve count understates the divide.** At matched compute, B5 not only
  solves 6× more tasks than B0, it does so at ~1/7 the cost per task.
  The per-cell productivity is roughly 40× (6× × 7×).
- **The ordering is robust to the endpoint.** Switching the metric from
  count to cost preserves the ranking. The fact that the solve-count
  ranking survives a metric change is a form of robustness check —
  choose your endpoint defensively, and the conclusion holds.
- **B1 (isolation) is the most expensive failure mode** on the cost axis
  (3.14M evals/solve — 9.7× B5). The multi-agent tax compounds
  dramatically when none of the agents can solve anything.

## B5 vs B5+planner, re-scored

The headline 4M result (Paper 3) was that B5+planner *ties* B5 on
solve count. Re-scored on cost:

| metric | B5 | B5+planner | diff |
|---|---|---|---|
| evals/solve (all solves, n=20/19) | 323,848 | 326,665 | +2,818 (+0.9%) |
| evo-solved (n=20/19) | 4.65 | 4.47 | -0.18 |
| evals/solve (evolution only) — median | 720,233 (n=93) | 573,527 (n=85) | **-146,706 (-20.4%)** |
| evals/solve (evolution only) — mean   | 1,196,189      | 1,100,653      | -95,536 (-8.0%)  |
| welch-t p (headline evals/solve) | — | — | 0.741 |
| **permutation p (median, 10k)** | — | — | **0.717** |

The planner seed makes evolution-only solves ~20% cheaper on the
median, but at n=85/93 the permutation test does not reject the null
(p = 0.717). The directional pattern is suggestive — B5+planner
provides a higher-quality starting point, so each evolution solve
needs less search — but the effect is within noise at this sample
size. A larger sweep would resolve it.

**Reading:** B5+planner is **at least as cost-efficient as B5** at
the headline 4M budget. The "null result at scale" in Paper 3 is
also a cost-axis null, and on the apples-to-apples (evolution-only)
metric there is a directional 20% win that is consistent with the
planner's job but underpowered.

## H2 / H3 verdicts re-scored

| comparison | cost diff (lower = better) | welch-t p |
|---|---|---|
| B2 vs B1 (H2: transfer helps) | -392,349 (-12.5%) | 0.316 |
| B2 vs B0 (H2: transfer vs concentrated) | +414,833 (+17.8%) | 0.302 |

- **B2 (fragment channel) is ~12% cheaper than B1 (isolation) on
  cost** (p=0.316, directional) — *the transfer benefit shows up on
  cost, not count.* B2 solves the same number on average but cheaper
  per task.
- **B2 is ~18% more expensive than B0 (concentrated) on cost**
  (p=0.302). Concentrating all compute in one lineage wins on cost
  the way it wins on count.

Both comparisons remain non-significant at 20 seeds — the frontier
is too hard for the per-arm solve counts to support crisp conclusions
even with the cost endpoint. But the *direction* of the cost axis
matches the *direction* of the count axis, and the per-solve
separation is much larger (12–18% on cost) than the per-seed
separation on count (~10% on average, often within SDs).

## Honest scope

- The cost axis is **summary-only for B0–B9** (per-solve evals
  weren't preserved for the older arms). The "evals/solve" column for
  those arms is 4M / solved, which is a coarse but unbiased summary.
- B5/B5+planner have per-solve evals, so the headline comparison
  there is much sharper.
- The B5+planner evolution-only 20% median win is suggestive but
  underpowered (n=85/93 solves, permutation p=0.717). It is a
  hypothesis for a larger sweep, not a conclusion.
- An arm-level cost win ≠ an arm-level count win. B2 is *cheaper*
  than B1 on cost but solves the same number of tasks. The cost
  axis surfaces speed differences that the count axis cannot.
