"""Quick inspection of the trace dataset."""
import json
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

with open("data/traces.jsonl", "r", encoding="utf-8") as f:
    rows = [json.loads(l) for l in f]

print(f"total rows: {len(rows)}")
print(f"unique tasks: {len(set(r['task_id'] for r in rows))}")
print(f"unique action heads: {len(set(r['action']['fn'] for r in rows))}")
print()
print("top 15 action heads:")
for fn, n in Counter(r['action']['fn'] for r in rows).most_common(15):
    print(f"  {fn:<20} {n}")
print()
print("state kind distribution:")
for k, n in Counter(r['state']['kind'] for r in rows).most_common():
    print(f"  {k:<10} {n}")
print()
print("next_state kind distribution:")
for k, n in Counter(r['next_state']['kind'] for r in rows).most_common():
    print(f"  {k:<10} {n}")
print()
print("=== first row ===")
print(json.dumps(rows[0], indent=2)[:500])
print()
print("=== first non-grid state ===")
for r in rows:
    if r['state']['kind'] != 'grid':
        print(json.dumps(r, indent=2)[:500])
        break
print()
print("=== grid-only rows ===")
grid_rows = [r for r in rows
             if r['state']['kind'] == 'grid' and r['next_state']['kind'] == 'grid']
print(f"  count: {len(grid_rows)} ({100*len(grid_rows)/len(rows):.1f}%)")
print("  top 10 action heads in grid-only rows:")
for fn, n in Counter(r['action']['fn'] for r in grid_rows).most_common(10):
    print(f"    {fn:<20} {n}")
