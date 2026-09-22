"""Find train-only solves (overfit) in all relevant logs."""
import json
from pathlib import Path

for pattern in ['b5_1m_seed*.jsonl', 'b5_4m_seed*.jsonl', 'hard15_b5_1m_seed*.jsonl', 'random15_b5_1m_seed*.jsonl']:
    print(f"=== {pattern} ===")
    for log in sorted(Path("logs").glob(pattern)):
        if "dropped" in log.name or "partial" in log.name:
            continue
        for line in log.read_text().splitlines():
            rec = json.loads(line)
            if rec.get("event") == "solve" and rec.get("test_exact") is not True:
                print(f"  {log.name}: train-only solve of {rec['task']} at epoch {rec['epoch']} evals {rec['evals']}")
