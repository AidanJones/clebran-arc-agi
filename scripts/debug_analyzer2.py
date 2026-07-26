"""Debug the analyzer (no string escape issues)."""
import json
from collections import defaultdict
from pathlib import Path

LOGS = Path("logs")
by_k = defaultdict(list)
in_progress = []
for log_path in sorted(LOGS.glob("b5p_*.jsonl")):
    if "_k1_4M_run1" in log_path.name:
        continue
    events = [json.loads(l) for l in log_path.read_text(encoding="utf-8").splitlines()]
    if not events:
        continue
    start = events[0]
    if start.get("event") != "start":
        continue
    K = start.get("planner_top_k", "?")
    summary = events[-1]
    if summary.get("event") != "summary":
        in_progress.append(log_path.name)
        continue
    by_k[K].append(summary)
for K, runs in by_k.items():
    print(f"K={K}: {len(runs)} completed runs")
    for r in runs:
        seed = r.get("seed")
        solved = r.get("n_solved")
        print(f"  seed={seed} solved={solved}")
print(f"in_progress: {in_progress}")
