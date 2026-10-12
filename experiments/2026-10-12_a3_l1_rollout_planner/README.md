# 2026-10-12 — A3 (first concrete test), L1-as-rollout-engine pilot (1M × 5 seeds)

The next push from paper 3 §6:

> "The learned L1's job is to be a fast approximation of the
> perfect L1, with a tolerable accuracy loss in exchange for rollout
> speed — and the clebran rig is the right test bed for measuring that
> accuracy / speed trade-off against an L2 planner using the
> perfect L1 as the ground truth."

This experiment is the first concrete test of that next push:
**B5L1P** (B5 + L1-rollout planner) at 1M × 5 seeds on the
30-task frontier subset. The L2 planner uses a hybrid
L1-then-interpreter rollout engine (the GPL1's prediction for
primitives it has learned, the perfect interpreter for primitives
it hasn't) instead of the perfect interpreter on every call.

## Arms

* **B5L1P** (new) — B5 + L2 planner with hybrid L1 rollout.
  GPL1 is trained on non-frontier tasks (so the L1 is OOD
  w.r.t. the test subset). The rollout prefers the GPL1's
  prediction on the primitives it has learned (vmirror, hmirror,
  rot*, cmirror, dmirror, bottomhalf, cellwise, paint, replace,
  plus more) and falls back to the interpreter on miss.
  Logs at `logs/b5l1p_seed{1..5}.jsonl`.
* **B5** (control) — single population, central library, no
  planner. Same as the B5-1M control in the discovery-bottleneck
  menu pilots. Frozen logs at `logs/b5_1m_seed{1..5}.jsonl`.
* **B5P** (control, optional) — B5 + L2 planner with
  perfect-interpreter rollout. Not run at 1M (the B5P 4M
  headline is in paper 3, 20 seeds: B5 12.45 ± 1.15 vs B5P
  12.35 ± 0.99, mean delta −0.10, t = 0.26). If 1M logs are
  available, they are aggregated in `analysis.txt`.

## Setup

* Trace dataset: `data/traces.jsonl` (16,149 rows, 400 Hodel
  reference solvers).
* Frontier subset: `data/frontier_subset.json` (30 tasks).
* GPL1 trained on **non-frontier** tasks (`--exclude-frontier`)
  at pop_size=50, n_generations=8, max_program_len=3.
* The L2 planner uses `--planner-lookahead=1` (greedy one-step)
  and `--planner-distance=hamming` (matches the B5P headline in
  paper 3).
* `planner_top_k=1` (only the planner's best candidate is
  seeded as an individual).

## Commands

```sh
# B5L1P 1M × 5 seeds
for s in 1 2 3 4 5; do
    uv run python -m clebran.baselines.b5_l1_planner --seed $s --budget 1000000
done

# Aggregation
uv run python -m scripts.aggregate_a3
```

## Frozen data

* B5L1P logs: `logs/b5l1p_seed{1..5}.jsonl`.
* B5 (control) logs: `logs/b5_1m_seed{1..5}.jsonl` (frozen
  2026-08-31 to 2026-09-24 from the discovery-bottleneck menu
  pilots).
* Analysis: `experiments/2026-10-12_a3_l1_rollout_planner/analysis/analysis.txt`.

## Hypothesis

The L1 rollout is a *fast approximation* of the perfect
interpreter (paper 3 §6). The arm's accuracy floor is the
interpreter's (the L1 is silent, not wrong, on primitives it
hasn't learned). The arm's speed ceiling is the L1's (look-up
for the 35 primitives GPL1 has learned, ~1 µs/call; the
interpreter is ~10–100 µs/call on grid primitives). At matched
candidate-evaluations, the L1 planner should be **at least as
good as B5P** (the interpreter is not a binding constraint at
1M — B5P is null at 4M because B5 has enough compute to do the
work without the planner's head-start) and **at least as good
as B5** (the L1 rollout planner shouldn't make the arm worse
than no planner at all).

## Expected result

If the L1 rollout is competitive with the interpreter on the
primitives it has learned (vmirror, hmirror, rot*, ...), and
silent on the primitives it hasn't (hconcat, vconcat,
scaling, ...), B5L1P should match B5 at 1M × 5 seeds. Any
positive effect on the planner's head-start (B5P is positive
at 500K-1M, paper 3 §3.3) would also be visible.

If the L1 rollout is *worse* than the interpreter on the
primitives it has learned (e.g. GPL1's wrong predictions
mis-rank candidates), B5L1P will regress. The L1 is 25.6% OOD
exact / 43.0% OOD shape-match (per the scoping pilot at
`experiments/2026-10-07_l1_proposer_scoping/`), so the
predictions are imperfect.

## Decision rule

* **If positive (B5L1P > B5 or B5L1P > B5P):** scale up to 4M
  × 20 seeds (matches paper 3's B5P headline). The
  L1-as-rollout-engine arm becomes the headline arm for the
  world-modeling direction.
* **If null (B5L1P ≈ B5):** the L1's accuracy loss offsets its
  speedup at 1M. The next push is to extend the L1's coverage
  to multi-arg primitives (hconcat, vconcat, scaling) — the
  v1 of the L1-proposer is null on the same frontier, and the
  L1's coverage gap is the most likely cause. This is the
  A3-step-2 (L1 with broader coverage) experiment.
* **If negative (B5L1P < B5):** the L1's wrong predictions
  compound through the planner's ranking, and the L1 isn't
  ready for rollout use. A3 closes structurally; the right next
  move is a different A3 angle (e.g. L3 evoker that refines
  on failed predictions, or a new substrate per paper 4).