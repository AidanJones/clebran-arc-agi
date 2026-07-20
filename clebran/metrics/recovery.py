"""Compositionality / primitive-recovery metrics for the recovered-primitive
channel (roadmap item 3; spec §9, §11).

Two families:

- **Topographic similarity** (the standard emergent-comms compositionality
  metric, EGG-style): the rank correlation between distance in *message*
  space (the abstraction's structure) and distance in *meaning* space (what
  it computes on a probe battery). High topsim ⇒ structurally similar
  abstractions behave similarly ⇒ a compositional vocabulary.

- **Primitive-recovery stats** (NEO-style): are the recovered subroutines
  genuine single-purpose units that get *reused across contexts*, or
  entangled composites that are never used? Reuse across ≥2 tasks is the
  strong signal; using a *received* abstraction is the multi-agent version.

topsim is restricted to arity-1 Grid→X abstractions — the ones with a clean
"apply to a grid" meaning; that covers the common recovered units.
"""
from __future__ import annotations

from ..dsl.interpreter import _run_body
from ..dsl.program import Program
from ..dsl.registry import compatible

# deterministic probe battery — small, varied grids
PROBES = [
    ((1,),),
    ((1, 2), (3, 4)),
    ((0, 1, 0), (1, 0, 1), (0, 1, 0)),
    ((5, 5), (5, 0)),
    ((1, 2, 3),),
    ((2,), (2,), (2,)),
    ((0, 0), (0, 0)),
    ((3, 1), (1, 3)),
    ((4, 0, 4), (0, 4, 0)),
    ((7, 8), (9, 1)),
]


# ---------- small stats helpers (no scipy dependency) ----------

def _ranks(xs: list[float]) -> list[float]:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(xs):
        j = i
        while j + 1 < len(xs) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def _pearson(a: list[float], b: list[float]) -> float:
    n = len(a)
    if n == 0:
        return 0.0
    ma, mb = sum(a) / n, sum(b) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = sum((x - ma) ** 2 for x in a) ** 0.5
    db = sum((y - mb) ** 2 for y in b) ** 0.5
    return num / (da * db) if da > 0 and db > 0 else 0.0


def spearman(a: list[float], b: list[float]) -> float:
    return _pearson(_ranks(a), _ranks(b))


def _levenshtein(s: str, t: str) -> int:
    if s == t:
        return 0
    m, n = len(s), len(t)
    prev = list(range(n + 1))
    for i in range(1, m + 1):
        cur = [i] + [0] * n
        for j in range(1, n + 1):
            cost = 0 if s[i - 1] == t[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
        prev = cur
    return prev[n]


def _norm_lev(s: str, t: str) -> float:
    m = max(len(s), len(t))
    return _levenshtein(s, t) / m if m else 0.0


# ---------- topographic similarity ----------

def _canon(v) -> object:
    if v is None or isinstance(v, (int, bool, tuple, frozenset)):
        return v
    return repr(v)


def _meaning_signature(abstr, abstractions: dict) -> tuple:
    sig = []
    for g in PROBES:
        try:
            sig.append(_canon(_run_body(abstr, [g], abstractions)))
        except Exception:  # noqa: BLE001 — any primitive error = undefined here
            sig.append(None)
    return tuple(sig)


def topographic_similarity(abstractions: dict) -> float | None:
    """Spearman rho between structural and behavioural pairwise distances
    over arity-1 Grid→X abstractions. None if fewer than 3 qualify (too few
    pairs to be meaningful)."""
    items = [
        a for a in abstractions.values()
        if a.arity == 1 and compatible("Grid", a.params[0])
    ]
    # keep only abstractions that actually run on some probe
    scored = []
    for a in items:
        sig = _meaning_signature(a, abstractions)
        if any(v is not None for v in sig):
            scored.append((a, sig, Program(list(a.body)).pretty()))
    if len(scored) < 3:
        return None
    msg_d, mean_d = [], []
    for i in range(len(scored)):
        for j in range(i + 1, len(scored)):
            (_, sa, ta), (_, sb, tb) = scored[i], scored[j]
            msg_d.append(_norm_lev(ta, tb))
            mean_d.append(
                sum(1 for x, y in zip(sa, sb) if x != y) / len(sa)
            )
    return round(spearman(msg_d, mean_d), 4)


# ---------- primitive-recovery stats ----------

def abstraction_stats(lineage) -> dict:
    """Recovery/usage stats for a lineage's vocabulary (spec §9)."""
    abstrs = lineage.abstractions
    if not abstrs:
        return {"n": 0}
    used_in: dict[str, set] = {name: set() for name in abstrs}
    for tid, pop in lineage.pops.items():
        if pop.solved and pop.solution is not None:
            for name in pop.solution.prog.abstractions_used():
                if name in used_in:
                    used_in[name].add(tid)
    used = [n for n, ts in used_in.items() if ts]
    cross = [n for n, ts in used_in.items() if len(ts) >= 2]
    received = lineage.received_abstraction_names()
    bodies = [len(a.body) for a in abstrs.values()]
    arities = [a.arity for a in abstrs.values()]
    return {
        "n": len(abstrs),
        "used": len(used),
        "used_rate": round(len(used) / len(abstrs), 3),
        "reused_across_tasks": len(cross),   # genuine reusable primitives
        "received": len(received),
        "received_used": sum(1 for n in used if n in received),  # NEO-style
        "mean_body_size": round(sum(bodies) / len(bodies), 2),
        "mean_arity": round(sum(arities) / len(arities), 2),
        "topsim": topographic_similarity(abstrs),
    }
