"""Inspect the b5p logs."""
import json
from pathlib import Path

LOGS = Path("logs")
for f in sorted(LOGS.glob("b5p_seed*.jsonl")):
    if "_k1_4M_run1" in f.name:
        continue
    text = f.read_text(encoding="utf-8").splitlines()
    first = json.loads(text[0])
    last = json.loads(text[-1])
    seed = first.get("seed")
    K = first.get("planner_top_k")
    budget = first.get("budget")
    solved = last.get("n_solved")
    evo = last.get("n_evo_solved")
    summary_event = last.get("event")
    print(f"{f.name}: seed={seed} K={K} budget={budget} "
          f"solved={solved} evo={evo} (last_event={summary_event})")
