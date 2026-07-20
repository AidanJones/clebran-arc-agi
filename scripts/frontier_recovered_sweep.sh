#!/bin/sh
# Recovered-primitive frontier sweep (roadmap item 3 payoff).
#
# Runs B0/B1/B2/B6/B7 on the D2/D3 frontier at matched compute, seeds in
# parallel (one process per seed), arms sequentially so parallelism stays
# bounded to the seed count. ~5 arms x N seeds x BUDGET evals — several hours
# at 8 seeds x 3M. Override with env vars:
#
#   SEEDS="1 2 3 4 5 6 7 8" BUDGET=3000000 sh scripts/frontier_recovered_sweep.sh
#
# Then: uv run python -m clebran.baselines.frontier_sweep --analyze
#       uv run python -m clebran.solver_card    # abstraction-using traces
set -e
SEEDS="${SEEDS:-1 2 3 4 5}"
BUDGET="${BUDGET:-3000000}"
export CLEBRAN_SUBSET=frontier_subset

for arm in B0 B1 B2 B6 B7; do
  echo "=== $arm (seeds: $SEEDS, budget: $BUDGET) ==="
  for s in $SEEDS; do
    uv run python -m clebran.baselines.frontier_sweep --run \
        --arm "$arm" --seed "$s" --budget "$BUDGET" &
  done
  wait
done
echo FRONTIER_RECOVERED_SWEEP_DONE
uv run python -m clebran.baselines.frontier_sweep --analyze
