"""Smoke test for L2 planner → clebran Program conversion."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")

from clebran.world_model.l2_planner import L2Planner

state = ((1, 0, 1),
         (0, 1, 0),
         (1, 0, 1))
target = ((0, 1, 0),
          (1, 0, 1),
          (0, 1, 0))

planner = L2Planner()
result = planner.plan_to_program(state, target, max_steps=5)
print("solved:", result["solved"])
print("program statements:")
for st in result["program"].statements:
    print("  ", st)
print()
print("trace steps:")
for t in result["trace"]:
    print(f"  step {t['step']}: {t.get('primitive')} dist={t.get('distance')}")
