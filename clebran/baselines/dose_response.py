"""H3 bandwidth dose-response (roadmap item 2).

Runs a ladder of channel configurations from no-channel (B1) through
increasingly loose constrained channels to fully unconstrained (B3), all at
matched compute. The question: does solve rate degrade *monotonically* with
channel bandwidth? A monotone curve — plus the crowding metric showing the
fragment operator taking a larger share at lower success as bandwidth grows
— turns the Stage-4 "B3 is the worst arm" observation into a mechanistic,
significant H3 result.

Bandwidth is ~ K x M (max nodes a lineage can inject per epoch). The ladder:

    none      no channel (B1)                       bandwidth 0
    K2M1      fragments <=2 nodes, 1 msg/epoch       ~2
    K4M3      fragments <=4 nodes, 3 msgs  (= B2)    ~12
    K8M10     fragments <=8 nodes, 10 msgs           ~80
    uncon     whole library every epoch (B3)         inf

Usage:
    uv run python -m clebran.baselines.dose_response --seeds 1 2 3 4 5 --budget 1000000
    uv run python -m clebran.baselines.dose_response --analyze
"""
from __future__ import annotations

import argparse
import json
import statistics as st

from ..channel import make_channel
from ..orchestrator import run_multi
from .common import LOG_DIR, run_prefix

# (label, channel-kind, kwargs) in increasing-bandwidth order.
LADDER = [
    ("none", "none", {}),
    ("K2M1", "constrained", {"max_fragment_size": 2, "max_messages": 1}),
    ("K4M3", "constrained", {"max_fragment_size": 4, "max_messages": 3}),
    ("K8M10", "constrained", {"max_fragment_size": 8, "max_messages": 10}),
    ("uncon", "unconstrained", {}),
]

RESULTS = LOG_DIR / "dose_response_results.jsonl"


def run(seeds: list[int], budget: int, n_lineages: int = 3,
        pop_size: int = 100) -> None:
    for label, kind, kw in LADDER:
        for seed in seeds:
            chan = make_channel(kind, payload="fragment", **kw)
            frag_k = kw.get("max_fragment_size", 4)
            summary = run_multi(
                arm=f"DR-{label}", channel=chan, seed=seed, budget=budget,
                n_lineages=n_lineages, pop_size=pop_size, max_frag_size=frag_k,
                run_name=f"{run_prefix()}dr_{label}_seed{seed}",
            )
            summary["dr_label"] = label
            with RESULTS.open("a") as fh:
                fh.write(json.dumps(summary) + "\n")
            evo = len(summary.get("solved_evolution", []))
            print(f"{label:6} seed={seed}: solved {summary['solved_union']}/30 "
                  f"(evo {evo}) reuse={summary['reuse_rate']}")


def _agg(rows: list[dict], key) -> str:
    vals = [key(r) for r in rows if key(r) is not None]
    if not vals:
        return "-"
    if len(vals) == 1:
        return f"{vals[0]:.2f}"
    return f"{st.mean(vals):.2f}±{st.stdev(vals):.2f}"


def analyze() -> None:
    by_label: dict[str, list[dict]] = {}
    for line in RESULTS.read_text().splitlines():
        r = json.loads(line)
        by_label.setdefault(r["dr_label"], []).append(r)

    def frag_share(r):
        m = r.get("op_mix")
        if not m:
            return None
        return st.mean(v["fragment_share"] for v in m.values())

    def frag_success(r):
        m = r.get("op_mix")
        if not m:
            return None
        return st.mean(v["fragment_success"] for v in m.values())

    def mut_success(r):
        m = r.get("op_mix")
        if not m:
            return None
        return st.mean(v["mutate_success"] for v in m.values())

    print(f"{'config':7} {'n':>2} {'solved/30':>12} {'evo-solved':>12} "
          f"{'reuse':>10} {'frag-share':>11} {'frag-succ':>11} {'mut-succ':>10}")
    order = [lbl for lbl, _, _ in LADDER]
    for label in order:
        rs = by_label.get(label)
        if not rs:
            continue
        solved = _agg(rs, lambda r: float(r["solved_union"]))
        evo = _agg(rs, lambda r: float(len(r.get("solved_evolution", [])))
                   if "solved_evolution" in r else None)
        reuse = _agg(rs, lambda r: r.get("reuse_rate"))
        print(f"{label:7} {len(rs):>2} {solved:>12} {evo:>12} {reuse:>10} "
              f"{_agg(rs, frag_share):>11} {_agg(rs, frag_success):>11} "
              f"{_agg(rs, mut_success):>10}")
    print("\nH3 dose-response: read down the ladder (bandwidth 0 -> inf).")
    print("A monotone fall in solved with a rising frag-share / falling")
    print("frag-success is the mechanistic signature of bandwidth harm.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", nargs="+", type=int, default=[1, 2, 3, 4, 5])
    ap.add_argument("--budget", type=int, default=1_000_000)
    ap.add_argument("--pop", type=int, default=100)
    ap.add_argument("--analyze", action="store_true")
    args = ap.parse_args()
    if args.analyze:
        analyze()
    else:
        run(args.seeds, args.budget, pop_size=args.pop)
        analyze()
