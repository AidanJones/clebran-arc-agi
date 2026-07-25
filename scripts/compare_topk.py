"""Compare B5+planner results by top-K value."""
import json
from pathlib import Path

LOGS = Path("logs")
for s in [1, 2, 3]:
    log = LOGS / f"b5p_seed{s}.jsonl"
    if log.exists():
        last_line = log.read_text(encoding="utf-8").splitlines()[-1]
        summary = json.loads(last_line)
        print(f"seed={summary['seed']}  solved={summary['n_solved']}  "
              f"test_exact={summary['n_test_exact']}  "
              f"evo={summary['n_evo_solved']}  "
              f"mean_len={summary['mean_solution_length']:.2f}  "
              f"tasks={summary['solved']}")
