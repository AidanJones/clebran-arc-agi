# Run B5 4M-eval baseline for seeds 2, 3, 4, 5 in the background.
# Used to compare against the B5+planner top-K sweep at the
# headline configuration.

set -e

REPO=$(cd "$(dirname "$0")/.." && pwd)
VENV_PY="$REPO/.venv/Scripts/python.exe"
if [ ! -x "$VENV_PY" ]; then
    echo "ERROR: venv python not found at $VENV_PY" >&2
    exit 1
fi
echo "using venv python: $VENV_PY"

SEEDS=${SEEDS:-"2 3 4 5"}
BUDGET=${BUDGET:-4000000}

for SEED in $SEEDS; do
    echo "[$(date +%H:%M:%S)] running B5 seed=$SEED ..."
    "$VENV_PY" -m clebran.baselines.frontier_sweep --run --arm B5 \
        --seed $SEED --budget $BUDGET
    echo "[$(date +%H:%M:%S)] done: B5 seed=$SEED"
done
echo "[$(date +%H:%M:%S)] all done"
