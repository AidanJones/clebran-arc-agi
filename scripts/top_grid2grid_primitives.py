"""Top grid->grid primitives in the trace dataset."""
import json
from collections import Counter
from pathlib import Path

rows = [json.loads(l) for l in Path("data/traces.jsonl").read_text(encoding="utf-8").splitlines()]
g2g = [r for r in rows if r["state"]["kind"] == "grid" and r["next_state"]["kind"] == "grid"]
heads = Counter(r["action"]["fn"] for r in g2g)
print(f"grid->grid transitions: {len(g2g)} / {len(rows)}")
print()
print("Top 35 grid->grid primitives:")
for h, c in heads.most_common(35):
    h_str = str(h) if h is not None else "<None>"
    print(f"  {h_str:20s} {c}")
