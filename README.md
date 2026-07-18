# clebran-arc-agi

*clebran* (Welsh: to chatter, to gossip) — gossip protocols for divergent program evolution. Multiple populations of DSL programs evolve under pure reward on ARC-AGI-1 tasks, diverge into different solution strategies, and pass fragments of "what works" to each other through a deliberately narrow communication channel. The experiment tests whether that constrained gossip preserves better abstractions than isolation, ensembling, or unconstrained sharing — at matched compute, with baselines strong enough that a null result is trustworthy.

See [emergent-dsl-arc-spec.md](emergent-dsl-arc-spec.md) for the full specification.

## Hypotheses → baselines

| | Arm | Purpose |
|---|---|---|
| B0 | single population, all compute | reference line; H2 needs B2 > B0 |
| B1 | N isolated lineages (CH-NONE), union | H1 divergence measured here; ensembling control (H2 needs B2 > B1) |
| B2 | N lineages + CH-CONSTRAINED, fragment payload | main treatment (H2, H3) |
| B3 | N lineages + CH-UNCONSTRAINED | H3 control (constraint vs mere sharing) |
| B4 | N lineages + CH-CONSTRAINED, signal payload | abstract-communication variant |

All arms run at matched candidate-evaluation budgets, ≥5 seeds.

## Setup

```sh
sh scripts/fetch_third_party.sh   # clones michaelhodel/arc-dsl + fchollet/ARC-AGI
uv sync
uv run python -m clebran.subset   # regenerate data/stage1_subset.json (deterministic)
uv run pytest                     # stage acceptance tests
```

## Running

```sh
uv run python -m clebran.baselines.b0 --seed 1 --budget 500000        # single arm
uv run python -m clebran.baselines.arms --arms B0 B1 B2 B3 B4 \
    --seeds 1 2 3 4 5 --budget 500000                                 # full sweep
uv run python -m clebran.metrics.report                               # H2/H3 table
```

Logs are JSONL per run under `logs/`.

## Layout

```
clebran/
  data/loader.py     ARC-AGI-1 tasks
  dsl/               vendored arc-dsl, typed linear IR, deterministic interpreter,
                     solver parser (depth proxy + reproduction gate)
  subset.py          §4.1 deterministic Stage-1 subset recipe
  genome.py          typed mutation / crossover / repair / fragments
  fitness.py         pure outcome reward + NEO adaptive-MDL parsimony
  lineage.py         per-task populations + private fragment library
  channel.py         CH-NONE / CH-CONSTRAINED(K,M) / CH-UNCONSTRAINED,
                     fragment & signal payloads
  orchestrator.py    N lineages, epochs, matched-compute budgeting
  metrics/           divergence (Jaccard), H2/H3 report
  baselines/         B0–B4 runners + sweep driver
```
