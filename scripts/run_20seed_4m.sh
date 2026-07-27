# 20-seed 4M-eval B5 vs B5+planner headline sweep.
#
# Runs seeds 6-20 (we already have seeds 1-5 from the 5-seed
# pilot in commit f35fccd) of B5 (control) and B5+planner
# (K=1, L=1, hamming) at the headline 4M budget on the
# 30-task frontier subset. Total: 15 seeds x 2 arms = 30 runs,
# ~22 min each = ~11 hours.
#
# Log naming:
#   logs/b5_seed{N}.jsonl         (B5 baseline, control)
#   logs/b5p_seed{N}.jsonl        (B5+planner K=1, hamming, lookahead=1)
#
# Idempotent: skips seeds that already have a complete log
# (i.e. have a "summary" event with arm + budget fields).
#
# Usage (from repo root):
#     bash scripts/run_20seed_4m.sh [START_SEED] [END_SEED]
# Defaults: START=6, END=20
#
# Environment:
#     SEEDS="6 7 8" bash scripts/run_20seed_4m.sh   # override the seed list

set -e

REPO=$(cd "$(dirname "$0")/.." && pwd)
VENV_PY="$REPO/.venv/Scripts/python.exe"
if [ ! -x "$VENV_PY" ]; then
    echo "ERROR: venv python not found at $VENV_PY" >&2
    exit 1
fi
echo "using venv python: $VENV_PY"

START_SEED=${1:-6}
END_SEED=${2:-20}
SEEDS=${SEEDS:-$(seq $START_SEED $END_SEED)}
BUDGET=${BUDGET:-4000000}
POP_SIZE=${POP_SIZE:-100}

# Helper: check if a log has a complete summary event.
is_complete() {
    local log="$1"
    if [ ! -s "$log" ]; then
        return 1
    fi
    grep -q '"event": "summary"' "$log"
}

run_arm() {
    local arm="$1"
    local seed="$2"
    local log="$REPO/logs/${arm}_seed${seed}.jsonl"
    if is_complete "$log"; then
        echo "[$(date +%H:%M:%S)] SKIP ${arm} seed=$seed (already complete: $log)"
        return 0
    fi
    echo "[$(date +%H:%M:%S)] running ${arm} seed=$seed -> $log"
    if [ "$arm" = "b5p" ]; then
        "$VENV_PY" -m clebran.baselines.b5_planner \
            --seed $seed \
            --budget $BUDGET \
            --pop-size $POP_SIZE \
            --planner-lookahead 1
    else
        "$VENV_PY" -m clebran.baselines.frontier_sweep \
            --run --arm B5 --seed $seed --budget $BUDGET
    fi
    echo "[$(date +%H:%M:%S)] done: ${arm} seed=$seed"
}

# Run B5 first (control), then B5+planner — pairs by seed.
for SEED in $SEEDS; do
    run_arm "b5"  "$SEED"
    run_arm "b5p" "$SEED"
done
echo "[$(date +%H:%M:%S)] all done (20-seed 4M sweep complete)"
