"""Inspect fill args in the trace dataset."""
import json
from pathlib import Path
from collections import Counter

rows = [json.loads(l) for l in Path("data/traces.jsonl").read_text(encoding="utf-8").splitlines()]
# Find fill rows and look at the arg_kinds
fill_rows = [r for r in rows if r.get("action", {}).get("fn") == "fill"][:5]
for r in fill_rows:
    print(r.get("action"))
