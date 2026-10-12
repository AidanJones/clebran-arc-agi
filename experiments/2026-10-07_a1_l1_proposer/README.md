# 2026-10-07 — A1, #5 Learned L1 as proposer (1M × 5 seeds)

Concrete test of the L1-as-proposer hypothesis (roadmap §A1). The
arm is B5 augmented with an L1-proposer that seeds the initial
population of every task with the trace dataset's most common first-
step primitives on grids of the input's shape.

This is the *first concrete test* of the A1 hypothesis. The scoping
pilot at [`experiments/2026-10-07_l1_proposer_scoping/`](../2026-10-07_l1_proposer_scoping/)
showed:

* GPL1 has perfect prediction on pure-geometric primitives (vmirror,
  hmirror) at 100% OOD exact-match on the frontier subset.
* GPL1 ranks Hodel's first-step primitive #1 at 56% on a small
  sample (vs 72% for the interpreter). The 16-pp gap reflects
  GPL1's imperfection on 2/3-arg primitives.
* 126 of 151 primitives in the trace dataset are NOT in the L2
  planner's `_default_candidates` — these are higher-order /
  combinator primitives (`fork`, `compose`, `lbind`, `rbind`,
  `apply`, `mapply`, `ofcolor`, `objects`, ...) that the planner
  cannot reach.

This experiment tests the v1 proposer, restricted to geometric
primitives. v2 (planned if v1 is positive) extends to combinator
primitives and 2-step prefixes.

## Setup

* Trace dataset: `data/traces.jsonl` (16,149 rows, 400 Hodel
  reference solvers).
* Frontier subset: `data/frontier_subset.json` (30 tasks).
* The proposer is trained on **non-frontier** tasks (so the
  frontier is held-out OOD; `--exclude-frontier`).
* v1 candidate primitives: `vmirror`, `hmirror`, `rot90`,
  `rot180`, `rot270`, `cmirror`, `dmirror`, `tophalf`,
  `bottomhalf`, `lefthalf`, `righthalf` (11 primitives).
* `proposer_k = 3` (top-3 candidates per task, capped at
  `pop_size // 4` = 25).
* Each proposal is a 1-statement program evaluated against ALL
  demos of the task; the cost is one candidate-evaluation per
  proposal (counted against the budget).

## Arms

* **B5** (control) — single population, central library, no
  proposer. Same as the B5-1M control in the discovery-bottleneck
  menu pilots. Frozen logs at `logs/b5_1m_seed{1..5}.jsonl`.
* **B5L1** (new) — B5 + `seed_with_l1_proposer` after
  `seed_population` for every task. Logs at
  `logs/b5l1_seed{1..5}.jsonl`.

## Commands

```sh
# B5L1 1M × 5 seeds
for s in 1 2 3 4 5; do
    uv run python -m clebran.baselines.b5_l1_proposer --seed $s --budget 1000000
done

# Aggregation
uv run python -m scripts.aggregate_a1
```

## Frozen data

* Scoping pilot: [`experiments/2026-10-07_l1_proposer_scoping/`](../2026-10-07_l1_proposer_scoping/).
* B5 (control) logs: `logs/b5_1m_seed{1..5}.jsonl` (from the
  discovery-bottleneck menu pilots).
* B5L1 logs: `logs/b5l1_seed{1..5}.jsonl` (this experiment).
* Analysis: `experiments/2026-10-07_a1_l1_proposer/analysis/analysis.txt`.

## Hypothesis

The L1 has seen 400 Hodel reference solvers and learned that certain
geometric transformations are common first steps on grids of
similar shape. Injecting those primitives as high-priority seeds
should give B5 a small advantage on tasks where the first step is
geometric (vmirror, hmirror, rot*, cmirror, dmirror, top/bottom/left/
righthalf).

## Expected result

The scoping pilot predicts a *small* or *null* effect:

* For the 5 frontier tasks where Hodel's first step is geometric
  and in the proposer's set, the proposer is 100% accurate (vmirror
  | hmirror | rot90/180/270) — should help.
* For the other tasks where the first step is `fill`, `paint`,
  `replace`, `ofcolor`, etc., the proposer injects the wrong
  candidate (no signal) — no help, no harm (because the phase-1
  closure already enumerates those primitives).

The net effect: a small positive on geometric tasks, no change on
non-geometric tasks. Frontier solves / 30 expected to be roughly
tied with B5 (10.40 ± 1.14) or slightly above.

If null (B5L1 ≈ B5): the v1 proposer doesn't add value. v2 (with
combinator primitives + 2-step prefixes) is the natural extension.
If v2 is also null, the L1-as-proposer arm closes structurally
and the right next move is A2 (operator self-modification).