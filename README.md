# clebran-arc-agi

*clebran* (Welsh: to chatter, to gossip) — gossip protocols for divergent program evolution. Multiple populations of DSL programs evolve under pure reward on ARC-AGI-1 tasks, diverge into different solution strategies, and pass fragments of "what works" to each other through a deliberately narrow communication channel. The experiment tests whether that constrained gossip preserves better abstractions than isolation, ensembling, or unconstrained sharing — at matched compute, with baselines strong enough that a null result is trustworthy.

The full design is in [emergent-dsl-arc-spec.md](emergent-dsl-arc-spec.md). **What the experiment found: [FINDINGS.md](FINDINGS.md).** Current status and next steps: [roadmap.md](roadmap.md).

> **Headline result.** At matched compute on ARC, a single population that mines its own solutions into a growing abstraction library (a DreamCoder/Stitch-style central learner, arm **B5**) *significantly* outperforms divergent lineages communicating over a constrained channel (B6): `B5 2.65 > B0 2.25 > B7≈B6 1.8 > B2 1.6 > B1 1.45` evolution-phase solves; B6−B5 = −0.85 (~2.2 se, the only significant comparison). The central hypothesis is not supported — the strongest control wins. A trustworthy negative result, which is exactly what the baselines were built to make believable.

## Hypotheses → baselines

| | Arm | Purpose |
|---|---|---|
| B0 | single population, all compute | reference line; H2 needs B2 > B0 |
| B1 | N isolated lineages (CH-NONE), union | H1 divergence measured here; ensembling control (H2 needs B2 > B1) |
| B2 | N lineages + CH-CONSTRAINED, fragment payload | main treatment (H2, H3) |
| B3 | N lineages + CH-UNCONSTRAINED | H3 control (constraint vs mere sharing) |
| B4 | N lineages + CH-CONSTRAINED, signal payload | abstract-communication variant |

All arms run at matched candidate-evaluation budgets (audited to ±1%), ≥5 seeds.

**Results so far** (Stages 0–4 complete, 2026-07-20; full artifacts in
[experiments/2026-07-20_stage4_b0-b4_matched_compute](experiments/2026-07-20_stage4_b0-b4_matched_compute/README.md)):
**H1 supported** — isolated lineages diverge (pairwise Jaccard 0.57 ± 0.10 on primitive
usage, tasks solved by exactly one lineage in 4/5 seeds). **H2 null** at the Stage-1
subset and 1M-eval budget — the channel is active but the solvable frontier is shallow
enough that communication has nothing to add. **H3 directionally supported** —
unconstrained library-dumping was the *worst* arm (9.80/30 vs 10.40) despite the
highest reuse (17%): bandwidth-unlimited gossip measurably hurts.

## External repositories and references

Cloned into `third_party/` by [scripts/fetch_third_party.sh](scripts/fetch_third_party.sh) (not committed):

- **[michaelhodel/arc-dsl](https://github.com/michaelhodel/arc-dsl)** — the DSL this
  project evolves programs over. We vendor `dsl.py` (160 typed grid primitives),
  `constants.py`, `arc_types.py`, and `solvers.py` into `clebran/dsl/_vendor/` (MIT
  license included). `solvers.py` — one hand-written solver per training task — is
  used two ways: as the **depth oracle** (statement count grades task difficulty, §4.1)
  and as the **correctness gate** (every reference solver must reproduce its task's
  grids through *our* interpreter before that task can enter the subset).
- **[fchollet/ARC-AGI](https://github.com/fchollet/ARC-AGI)** — the ARC-AGI-1 dataset
  (400 training + 400 evaluation tasks as JSON grids). Only the training split is ever
  evolved against.

Intellectual anchors (see spec §2 for how each maps onto the design):
[Learning-to-Theorize / NEO](https://arxiv.org/abs/2605.03413) (transfer-not-reconstruction
fitness, adaptive MDL rule), [DreamCoder](https://arxiv.org/abs/2006.08381) and
[Stitch](https://github.com/mlb2251/stitch) (library learning),
[Lazaridou & Baroni](https://arxiv.org/abs/2006.02419) and
[EGG](https://github.com/facebookresearch/EGG) (constrained-channel emergent communication).

## How the codebase fits together

Programs are **linear SSA-style register programs** (`x0 = fn(...); x1 = fn(x0, ...); return last`)
over Hodel's primitives — the same shape as his hand-written solvers, so reference
solvers parse *losslessly* into our genome representation. Everything else builds on that:

```
clebran/
  data/loader.py       ARC task loading (grids as tuples)
  dsl/
    _vendor/           vendored arc-dsl (dsl.py, constants.py, arc_types.py, solvers.py)
    registry.py        primitive signatures + type-subsumption relation
    program.py         the linear IR; static typing with union flow-through
                       (vmirror: Piece->Piece applied to a Grid returns Grid)
    interpreter.py     deterministic, exception-guarded execution; size caps;
                       run_trace() returns every register for visualization
    solver_parse.py    solvers.py -> IR (depth proxy + Stage-0 reproduction gate:
                       399/400 reproduce exactly; the 1 failure is order-sensitive upstream)
  subset.py            deterministic §4.1 recipe -> data/stage1_subset.json
                       (10×D1/15×D2/5×D3, tag-stratified, gate-checked)
  genome.py            typed operators on the IR: point/arg/const mutation, grow
                       (insert + rewire, the linear-IR "subtree replacement"),
                       two-segment crossover, a shared repair pass, fragment
                       extraction/injection with hole-filling, and systematic
                       depth-1 / depth-2 enumeration
  fitness.py           pure outcome reward: fraction of demo pairs solved exactly,
                       tie-broken by per-cell accuracy (foreground and background
                       scored separately — a blank canvas must not outrank content)
                       scaled by NEO's lambda_MDL^(-length)
  lineage.py           one population per task + the lineage's private fragment
                       library; the search engine (see below)
  channel.py           the blackboard: CH-NONE / CH-CONSTRAINED(K,M) /
                       CH-UNCONSTRAINED, fragment & signal payloads
  orchestrator.py      N lineages, epochs, publish/receive, matched-compute budget
  metrics/
    divergence.py      pairwise Jaccard over primitive usage; uniquely-solved counts
    report.py          terminal H2/H3 table + compute audit + verdict comparisons
  baselines/           b0.py (single population), arms.py (B1–B4 + sweep driver),
                       common.py (subset pool, JSONL run logs)
  solver_card.py       the HTML report generator (see Reports)
tests/test_stage0.py   Stage-0 acceptance tests (§8.1 row 0)
scripts/stage1_gate.py Stage-1 acceptance check over logs/b0_seed*.jsonl
experiments/           one folder per completed experiment (verdicts + frozen data)
data/stage1_subset.json  the 30-task Stage-1 subset (committed, reproducible)
logs/                  JSONL run logs (gitignored)
```

### The search engine (what it took to pass the Stage-1 gate)

The spec's Stage-1 gate — B0 solves all 10 near-atomic tasks on *every* seed — forced
a series of mechanisms, each fixing a diagnosed failure mode. They apply identically
to every arm, so none of them bias the H2/H3 comparison:

- **Union flow-through typing** (`program.py`): Hodel types mirrors as `Piece -> Piece`;
  without refinement, typed mutation could never feed `vmirror(I)` into a `Grid` slot,
  making reference compositions unreachable.
- **Phase-1 systematic closure** (`lineage.py` seeding): exhaustive depth-1 enumeration
  over typed constants, depth-2 skeleton sweep, signature-niched population, then
  constant-polish (coordinate descent + bounded 2-D joint sweeps for two-coordinate
  needles like crop offset+size) on the top stubs *and* compositions around the top
  families. Closes the depth-≤2 bucket deterministically at seeding.
- **Adaptive operator selection**: mutate/crossover/fragment-splice chosen per
  population by recent child-vs-parent success with floors. Fragment injection
  self-suppresses where library material is irrelevant (it was poisoning 15% of
  offspring on needle tasks) and self-amplifies where it pays — the fair setting
  for judging the channel.
- **Progress-weighted task scheduling**: generations allocated by proximity-to-solution
  instead of round-robin, which starved near-miss tasks in the budget tail.
- **Hall-of-fame restarts**: stagnation restarts explore fresh space but re-inject the
  best individual per skeleton signature, so a full restart can't destroy polishable
  partial-credit stubs.
- **Per-task RNG substreams**: each task's trajectory is driven by
  `Random(f"{seed}:{task_id}")`, so a task behaves bit-identically in isolation and
  interleaved with 29 others — isolation probes *predict* full-run behavior.
- **Foreground/background-balanced reward** (`fitness.py`): on mostly-background
  targets, plain per-cell accuracy let `canvas(ZERO, 3x3)` — a blank grid — outrank
  every content-bearing program.

## Setup

```sh
sh scripts/fetch_third_party.sh   # clones michaelhodel/arc-dsl + fchollet/ARC-AGI
uv sync
uv run python -m clebran.subset   # regenerate data/stage1_subset.json (deterministic)
uv run pytest                     # stage acceptance tests
```

## Running experiments

```sh
# single arm, single seed
uv run python -m clebran.baselines.b0 --seed 1 --budget 1000000

# any arm programmatically
uv run python -c "from clebran.baselines.arms import run_arm; run_arm('B2', seed=1, budget=1000000)"

# full sweep driver
uv run python -m clebran.baselines.arms --arms B0 B1 B2 B3 B4 --seeds 1 2 3 4 5 --budget 1000000
```

Every run writes a JSONL log to `logs/<arm>_seed<...>.jsonl`: a `start` record
(config), `solve` records (task, evals consumed, program JSON, test-exact flag),
`epoch` records, and a final `summary` (solved sets, per-lineage breakdowns,
divergence, reuse rate, messages published). The **compute unit is
candidate-evaluations**, metered inside `fitness.Evaluator` — wall-clock never
enters any comparison.

## Reports

Three report surfaces, all reading `logs/`:

```sh
uv run python scripts/stage1_gate.py       # Stage-1 gate: per-seed D1 completeness
uv run python -m clebran.metrics.report    # terminal H2/H3 table, compute audit, verdicts
uv run python -m clebran.solver_card       # writes logs/report.html
```

The **solver card** (`logs/report.html`) is a single self-contained HTML page —
no dependencies, works offline, dark/light themed. It contains the experiment
explainer, the hypothesis→baseline mapping, a results table that auto-fills as
arm summaries appear in `logs/`, and one card per subset task showing the
demonstration pairs, the evolved program, and a **statement-by-statement
execution trace** with every intermediate register rendered as an ARC grid.
Regenerate it after any run; it picks up whatever logs exist. Frozen snapshots
of the card are kept inside each `experiments/` folder.

## Reproducibility

- The subset is generated, never hand-picked: `clebran.subset` is deterministic
  (fixed seed, lexicographic ordering, gate-checked) and its output is committed.
- Lineage seeds are explicit; per-task RNG substreams make single-task probes
  reproduce full-run behavior exactly.
- Completed experiments are frozen under `experiments/<date>_<name>/` with the
  verdict, the raw per-arm-seed summaries, the gate output, and the commit hash.
