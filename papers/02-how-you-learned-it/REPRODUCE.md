# Reproducing the evidence — Paper 2 (how you learned it)

Every quantitative claim in `paper.md` is regenerable from the commands below.
The three experiments share a **teach → test** protocol: phase 1 evolves on a
curriculum only (then mines the library); phase 2 spends the rest of a *shared
total budget* on the target, carrying the phase-1 library forward. The primary
endpoint is **evals-to-solve** (acquisition efficiency), with solve rate
reported alongside.

## 0. Environment

```sh
sh scripts/fetch_third_party.sh
uv sync
uv run pytest -q tests/test_curriculum.py tests/test_compression_miner.py
```

## 1. The curriculum channel on the frontier (B8/B9)

Context for the process story: the multi-agent curriculum channel, in the full
matched-compute ranking. Requires the frontier subset (see Paper 1 §1).

```sh
uv run python -m clebran.subset --frontier
export CLEBRAN_SUBSET=frontier_subset
for arm in B8 B9; do for s in $(seq 1 20); do
  uv run python -m clebran.baselines.frontier_sweep --run --arm $arm --seed $s --budget 4000000
done; done
uv run python -m clebran.baselines.frontier_sweep --analyze
```

Claim: the channel *engages* — lineages receive ~31 teaching tasks and solve
70–78% of them — but buys nothing on the real tasks (B8 − B1 = +0.15, ns), and
the constraint is null (B8 ≈ B9). Learning a concept ≠ transferring it.
[data: experiments/2026-07-23_frontier_curriculum]

## 2. Teach→test probe (does a taught concept transfer?)

```sh
uv run python -m clebran.transfer_probe --targets 8 --seeds 1 2 3 4 5 \
    --total 500000 --teach-cap 150000
uv run python -m clebran.transfer_probe --analyze
```

Claim (as first reported, and then corrected in §3): taught vs an *irrelevant*
control shows a ~2× speedup — but this comparison lacks a no-teaching baseline.
[data: experiments/2026-07-23_transfer_probe]

## 3. Amortization + cold baseline (the correction)

Adds the missing **cold** (no-curriculum) arm; the three-way merge corrects §2.

```sh
uv run python -m clebran.amortization --targets 8 --seeds 1 2 3 4 5 \
    --total 500000 --teach-cap 150000
uv run python -m clebran.amortization --analyze
```

Claims: **taught ≈ cold** (−986 evals, perm p = 0.97 — relevant teaching is
neutral); **control > cold** (irrelevant teaching is *slower*); the probe's "2×"
was the harm to the mis-targeted control. Per student L + T = 129k > U = 73k, so
the amortization crossover `N > C/(U−L−T)` has no solution.
[data: experiments/2026-07-23_amortization]

## 4. The order/process experiment (the positive result)

Holds content fixed (a target's k prerequisite sub-tasks), varies only the
*order* of acquisition: forward / reverse / shuffled / cold.

```sh
uv run python -m clebran.order_experiment --targets 9 --seeds 1 2 3 4 5 6 \
    --total 500000 --teach-cap 150000
uv run python -m clebran.order_experiment --analyze
```

Claims (216 runs): **forward > reverse (paired McNemar p = 0.021)** and
**forward > cold (p = 0.021)**, but **forward ≈ shuffled (ns)**; reverse halves
curriculum acquisition (23% vs 47%). Order matters at the extreme (don't teach
backwards), not as fine sequencing; the effect is on capability, not the cost
endpoint. [data: experiments/2026-07-24_order_process]

## Reproducibility notes

- The taught curriculum in §2–§4 is an *oracle* decomposition of the target's own
  reference solver — an upper bound on transfer, stated as such in the paper.
- Targets are the depth-≥3 subset tasks with ≥2-step decompositions
  (`pick_targets`); order can only matter when there is more than one step.
- All arms share the total budget, so efficient teaching simply leaves more
  budget for the target — a legitimate advantage, not a confound.

## Build the PDF

```sh
uv run python papers/build_pdf.py papers/02-how-you-learned-it
```
