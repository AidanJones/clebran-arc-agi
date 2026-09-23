# Reproducing the evidence — Paper 1 (communication cost)

Every quantitative claim in `paper.md` is regenerable from the commands below.
All runs are **matched compute** (candidate-evaluations), audited to ≤0.3%
spread; the primary metric is **evolution-phase solves** (tasks reached by the
evolutionary loop, excluding the deterministic phase-1 seeding that is identical
across arms).

## 0. Environment

```sh
sh scripts/fetch_third_party.sh        # michaelhodel/arc-dsl + fchollet/ARC-AGI
uv sync
uv run pytest -q                       # harness + all experiment unit tests
```

## 1. Subsets

```sh
uv run python -m clebran.subset             # data/stage1_subset.json (10 D1 / 15 D2 / 5 D3)
uv run python -m clebran.subset --frontier  # data/frontier_subset.json (25 D2 / 5 D3)
```

The frontier subset is the substrate for the headline ranking; the Stage-1
subset is used for the H1/H2/H3 first test and the bandwidth dose-response.

## 2. Stage-1 first test of H1/H2/H3 (§ Results)

```sh
uv run python -m clebran.baselines.arms --arms B0 B1 B2 B3 B4 \
    --seeds 1 2 3 4 5 --budget 1000000
uv run python -m clebran.metrics.report      # H1 Jaccard, H2/H3 table, compute audit
```

Claims: H1 supported (pairwise primitive Jaccard 0.57 ± 0.10); H2 null
(B2 = B1 ≈ B0); H3 directional-not-significant on Stage-1.

## 3. Bandwidth dose-response (H3 mechanism)

```sh
uv run python -m clebran.baselines.dose_response --seeds 1 2 3 --budget 1000000
uv run python -m clebran.baselines.dose_response --analyze
```

Claim: flat dose-response; `frag-share` pinned at 0.03 regardless of bandwidth;
adaptive operator selection self-regulates a failing channel.

## 4. The headline frontier ranking (20 seeds × 4M, B0/B1/B2/B5/B6/B7)

The compute-heavy run. B5 is the central-library control; B6/B7 the
recovered-primitive channel; matched to 0.10% spread.

```sh
SEEDS="1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20" BUDGET=4000000 \
    sh scripts/frontier_recovered_sweep.sh
```

(B5 alone, if rerunning just the control:)

```sh
export CLEBRAN_SUBSET=frontier_subset
for s in $(seq 1 20); do
  uv run python -m clebran.baselines.frontier_sweep --run --arm B5 --seed $s --budget 4000000
done
```

Then the curriculum arms that complete the ranking (Paper 2 studies them in
depth; here they are the two lowest channel arms):

```sh
export CLEBRAN_SUBSET=frontier_subset
for arm in B8 B9; do for s in $(seq 1 20); do
  uv run python -m clebran.baselines.frontier_sweep --run --arm $arm --seed $s --budget 4000000
done; done
```

Analyse all arms:

```sh
uv run python -m clebran.baselines.frontier_sweep --analyze
```

Claims: `B5 (2.65) > B0 (2.25) > B7≈B6 (1.8) > B9≈B2≈B8 (1.6) > B1 (1.45)`;
the only significant comparison is **B5 − B6 = +0.85 (~2.2 se)**; H3 null across
payloads (B6 ≈ B7); vocabulary quality favours B5 (topsim 0.33 vs 0.14–0.15;
cross-task reuse 0.15 vs 0.05).

## 5. Frozen data

The exact runs behind the paper are archived (not regenerated) under:

- `experiments/2026-07-22_b5_central_library/` — the headline ranking + B5.
- `experiments/2026-07-22_frontier_recovered_scaled/` — the 20-seed sweep.
- `experiments/2026-07-20_b3_dose_response/` — the dose-response.
- `experiments/2026-07-20_stage4_b0-b4_matched_compute/` — the Stage-1 test.
- `experiments/2026-08-31_b5d_nm_1m/`,
  `experiments/2026-08-31_b5d_nm_aggressive_1m/` — discovery-bottleneck #1 (failure-mode dreaming).
- `experiments/2026-08-31_b5_heterogeneous_1m/` — discovery-bottleneck #2 (heterogeneous fitness / B5-strongmdl).
- `experiments/2026-09-22_task_subset_specialization/` — discovery-bottleneck #3 (task-subset specialization, hard15 vs random15 at 1M).

Each contains `summaries.jsonl` (one row per arm×seed) and an `analysis.txt`.

### 5.1 Discovery-bottleneck menu — reproduction commands

The three discovery-bottleneck pilots (§3.6 of the paper) run via
`scripts/run_b5_subset_1m.ps1` (PowerShell) on the two precomputed subsets
in `data/`:

```sh
# Generate the two subset JSONs (once)
uv run python build_subsets.py
# → data/hard15_subset.json, data/random15_subset.json

# Run all 10 seeds (2 arms × 5 seeds) at 1M evals each
pwsh scripts/run_b5_subset_1m.ps1

# #1 failure-mode dreaming (1M × 5 seeds, conservative + aggressive)
# Handled via clebran.baselines.b0:run_b5_dream with the failure-mode-dream
# flag set. The 1M pilot ran in
# experiments/2026-08-31_b5d_nm_1m/ and
# experiments/2026-08-31_b5d_nm_aggressive_1m/.

# #2 B5-strongmdl (λ = 1.5, 1M × 5 seeds)
# Re-run via the Evaluator's `lam_mdl` knob in
# experiments/2026-08-31_b5_heterogeneous_1m/.

# Analyse all #3 arms (test-exact vs train-only distinction)
uv run python analyze_subset.py
```

Claims: at 1M evals × 5 seeds, the discovery-bottleneck menu returns three
concrete nulls:

- **#1** B5D-NM-aggressive regresses (8.80 vs B5's 10.40, **p = 0.007**); the
  conservative variant regresses mildly (9.80, ns).
- **#2** B5-strongmdl regresses (−0.80 frontier, −0.80 evo, both ~1 SE).
- **#3** hard15 arm gets 0 test-exact discoveries (B5-4M, at 2× per-task
  compute, also fails to crack the subset); random15 arm's apparent gain
  (+1.0 test-exact vs B5-1M on the same subset, p = 0.007) is fully
  consistent with the 2× per-task compute redistribution (67k vs 33k/task).

## Build the PDF

```sh
uv run python papers/build_pdf.py papers/01-communication-cost
```
