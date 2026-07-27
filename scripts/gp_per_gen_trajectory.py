"""Generate per-generation GP trajectory data for a few representative
primitives. Shows the fitness curve across 8 generations, useful
for the paper to illustrate the GP's learning dynamics.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from clebran.world_model.l1_gp import GPL1
from clebran.dsl.interpreter import run


def main():
    # Load the trace dataset.
    rows = []
    with open("data/traces.jsonl", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    # 20% test split (same as the main evaluation).
    rng = random.Random(0)
    tasks = sorted(set(r["task_id"] for r in rows))
    rng.shuffle(tasks)
    test_tasks = set(tasks[:80])
    train = [r for r in rows
             if r["task_id"] not in test_tasks
             and r["state"]["kind"] == "grid"
             and r["next_state"]["kind"] == "grid"
             and isinstance(r["action"]["fn"], str)]

    # Run a small GP loop manually so we can capture per-generation fitness.
    from clebran.genome import GenomeOps
    from clebran.world_model.l1_gp import GPL1
    grid_prim_pool = [
        p for p, sig in __import__("clebran.dsl.registry",
                                     fromlist=["PRIMITIVES"]).PRIMITIVES.items()
        if sig.arity == 1 and sig.params == ("Piece",)
    ]
    # Use GPL1._score_program to score each candidate.
    gp = GPL1.__new__(GPL1)  # bypass __init__ since we manage the loop
    score_fn = gp._score_program

    # Pick 4 representative primitives: rot90 (learnable), fill
    # (shape-only lock-in), replace (no progress), hconcat (no progress).
    PRIMITIVES_OF_INTEREST = ["rot90", "fill", "replace", "hconcat"]

    print(f"{'primitive':>10s}  " + "  ".join(f"gen{g:>2d}" for g in range(9)))
    print("-" * 70)
    for prim in PRIMITIVES_OF_INTEREST:
        prim_rows = [r for r in train if r["action"]["fn"] == prim]
        if not prim_rows:
            print(f"{prim:>10s}: no training rows")
            continue
        train_states = [tuple(tuple(row) for row in r["state"]["grid"])
                        for r in prim_rows]
        train_targets = [tuple(tuple(row) for row in r["next_state"]["grid"])
                         for r in prim_rows]
        op_rng = random.Random(0)
        ops = GenomeOps(pool=grid_prim_pool, rng=op_rng, max_len=3)
        population = []
        for _ in range(50):
            length = op_rng.randint(1, 3)
            p = ops.random_program(length=length)
            if p is not None:
                population.append(p)
        scores = []
        for p in population:
            score, ne, ns = score_fn(p, train_states, train_targets)
            scores.append((score, ne, ns, p))
        gen_curve = [max(s[0] for s in scores)]
        for gen in range(8):
            scores.sort(key=lambda x: x[0], reverse=True)
            elite_n = max(1, 50 // 10)
            new_pop = [s[3] for s in scores[:elite_n]]
            while len(new_pop) < 50:
                t1, t2, t3 = (scores[op_rng.randrange(len(scores))][3]
                               for _ in range(3))
                w1 = max(t1, t2, t3, key=lambda p: score_fn(
                    p, train_states[:10], train_targets[:10])[0])
                if op_rng.random() < 0.5 and len(w1.statements) > 0:
                    child = ops.crossover(w1, scores[op_rng.randrange(len(scores))][3])
                else:
                    child = ops.mutate(w1)
                if child is not None:
                    new_pop.append(child)
            population = new_pop
            scores = []
            for p in population:
                score, ne, ns = score_fn(p, train_states, train_targets)
                scores.append((score, ne, ns, p))
            gen_curve.append(max(s[0] for s in scores))
        print(f"{prim:>10s}  " + "  ".join(f"{f:>4.2f}" for f in gen_curve))


if __name__ == "__main__":
    main()
