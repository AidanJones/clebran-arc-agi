"""H1 divergence metrics (§9)."""
from __future__ import annotations

from itertools import combinations


def jaccard_distance(a: dict[str, int], b: dict[str, int]) -> float:
    """Generalized (weighted) Jaccard distance between primitive-usage
    count vectors: 1 - Σ min / Σ max. 0 = identical usage, 1 = disjoint."""
    keys = set(a) | set(b)
    if not keys:
        return 0.0
    num = sum(min(a.get(k, 0), b.get(k, 0)) for k in keys)
    den = sum(max(a.get(k, 0), b.get(k, 0)) for k in keys)
    return 1.0 - (num / den if den else 0.0)


def pairwise_jaccard(usages: dict[str, dict[str, int]]) -> dict:
    """lineage_id -> usage counts  =>  mean + per-pair Jaccard distances."""
    pairs = {}
    for x, y in combinations(sorted(usages), 2):
        pairs[f"{x}|{y}"] = round(jaccard_distance(usages[x], usages[y]), 4)
    mean = sum(pairs.values()) / len(pairs) if pairs else 0.0
    return {"mean": round(mean, 4), "pairs": pairs}


def uniquely_solved(solved_sets: dict[str, set[str]]) -> dict:
    """Tasks solved by exactly one lineage — H1's second requirement."""
    all_solved: dict[str, list[str]] = {}
    for lid, s in solved_sets.items():
        for t in s:
            all_solved.setdefault(t, []).append(lid)
    unique = {t: lids[0] for t, lids in all_solved.items() if len(lids) == 1}
    return {
        "union_solved": sorted(all_solved),
        "unique_count": len(unique),
        "unique_tasks": unique,
    }
