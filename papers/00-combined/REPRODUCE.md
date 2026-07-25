# Reproducing the evidence — Combined paper

This combined paper is a **summary** of three focused papers. Every
quantitative claim is traceable to one of the focused papers below;
each focused paper has its own `REPRODUCE.md` with the exact,
matched-compute commands to regenerate the evidence.

## The three focused papers

| paper | directory | one-line thesis |
|---|---|---|
| **1. Communication cost** | [`../01-communication-cost/`](../01-communication-cost/) | at matched compute, a single agent with a central library significantly beats divergent agents communicating over a constrained channel |
| **2. How you learned it** | [`../02-how-you-learned-it/`](../02-how-you-learned-it/) | teaching content between agents is neutral/harmful, but the *order* of acquisition significantly changes capability |
| **3. World modeling** | [`../03-world-modeling/`](../03-world-modeling/) | the clebran interpreter is a perfect L1; an L2 multi-pair planner + B5 seed ties B5 at matched compute — the first positive integration result on the rig |

To reproduce the evidence behind this combined paper, run each
focused paper's `REPRODUCE.md` in order.

## Long-form archive

The long-form write-up that ties every experiment together
(sections `00-abstract` → `08-conclusion`, with the full related
work, design, methods, and per-experiment results) is archived at
[`paper-source/`](paper-source/). The long-form is the source the
focused papers were extracted from, and is kept for reference.

## Build the PDFs

```sh
uv run python papers/build_pdf.py --all
```

## Frozen data

The exact runs behind the three papers are archived (not regenerated) under:

- `experiments/2026-07-20_b3_dose_response/`
- `experiments/2026-07-20_stage4_b0-b4_matched_compute/`
- `experiments/2026-07-22_b5_central_library/`
- `experiments/2026-07-22_frontier_recovered_scaled/`
- `experiments/2026-07-23_amortization/`
- `experiments/2026-07-23_frontier_curriculum/`
- `experiments/2026-07-23_transfer_probe/`
- `experiments/2026-07-24_order_process/`

Each contains `summaries.jsonl` (one row per arm×seed) and an
`analysis.txt` with the headline numbers. World-modeling pilot
runs are in `logs/b5p_seed*.jsonl` and `logs/b5_seed*.jsonl`.
