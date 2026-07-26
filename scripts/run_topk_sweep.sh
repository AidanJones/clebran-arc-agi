# Run the 5-seed 4M-eval B5+planner sweep in the background.
# Runs the headline configuration (matching paper 1) for K=1,
# K=3, K=5. Writes JSONL logs to logs/b5p_topk{k}_seed{s}.jsonl.
#
# Usage (from repo root):
#     bash scripts/run_topk_sweep.sh

set -e

# Find the full path to uv (bash on Windows may not have it in PATH).
# The .venv is at $REPO/.venv, so we use Python directly with the venv's
# site-packages to bypass the need for `uv run`.
REPO=$(cd "$(dirname "$0")/.." && pwd)
VENV_PY="$REPO/.venv/Scripts/python.exe"
if [ ! -x "$VENV_PY" ]; then
    echo "ERROR: venv python not found at $VENV_PY" >&2
    exit 1
fi
echo "using venv python: $VENV_PY"

K_VALUES=${K_VALUES:-"1"}
SEEDS=${SEEDS:-"1 2 3 4 5"}
BUDGET=${BUDGET:-4000000}
POP_SIZE=${POP_SIZE:-100}

for K in $K_VALUES; do
    for SEED in $SEEDS; do
        echo "[$(date +%H:%M:%S)] running B5+planner K=$K seed=$SEED ..."
        "$VENV_PY" -m clebran.baselines.b5_planner \
            --seed $SEED \
            --budget $BUDGET \
            --pop-size $POP_SIZE \
            --planner-top-k $K
        echo "[$(date +%H:%M:%S)] done: K=$K seed=$SEED"
    done
done
echo "[$(date +%H:%M:%S)] all done"
