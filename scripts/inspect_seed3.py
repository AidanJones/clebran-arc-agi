"""Inspect b5p_seed3.jsonl structure."""
import json
from pathlib import Path

log = Path("logs/b5p_seed3.jsonl")
lines = log.read_text(encoding="utf-8").splitlines()
print(f"total lines: {len(lines)}")
print(f"first: {lines[0][:150]}")
print(f"last: {lines[-1][:200]}")
# Find the summary events
summaries = [(i, l[:100]) for i, l in enumerate(lines) if "summary" in l]
print(f"summary events: {len(summaries)}")
for i, s in summaries:
    print(f"  line {i}: {s}")
