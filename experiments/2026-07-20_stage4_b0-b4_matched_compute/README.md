# Stage-4 experiment — B0–B4 at matched compute (2026-07-20)

First full run of the H1/H2/H3 comparison on the Stage-1 subset.

| file | what it is |
|---|---|
| [verdict.md](verdict.md) | the written H1/H2/H3 verdicts with the headline table (§8.1 Stage-4 gate artifact) |
| [report_table.txt](report_table.txt) | raw output of `clebran.metrics.report` — per-arm mean±sd, compute audit, verdict comparisons |
| [stage1_gate.txt](stage1_gate.txt) | Stage-1 gate check on the B0 runs feeding this table (all 5 seeds PASS) |
| [sweep_results.jsonl](sweep_results.jsonl) | one summary record per arm×seed (25 rows): solved sets, per-lineage breakdowns, primitive usage, divergence, reuse |
| [solver_card_snapshot.html](solver_card_snapshot.html) | frozen solver card at the time of the verdict (open in a browser) |

## Configuration

- 5 arms × 5 seeds (1–5), 1,000,000 candidate-evaluations per run
- multi-lineage arms: N=3 lineages, 20% primitive-pool dropout per lineage
- CH-CONSTRAINED: fragments ≤ 4 statements, ≤ 3 messages/lineage/epoch
- code at commit `40067c7`

## Reproduce

```sh
uv run python -m clebran.baselines.b0 --seed 1 --budget 1000000       # B0, one seed
uv run python -c "from clebran.baselines.arms import run_arm; run_arm('B2', seed=1, budget=1000000)"
uv run python -m clebran.metrics.report                                # after collecting summaries
```

Headline: H1 supported (Jaccard 0.57 ± 0.10); H2 null (B2 = B1 = 10.4 ≈ B0 = 10.6);
H3 directional (B3 = 9.80, worst arm at highest reuse — unconstrained sharing hurts).
