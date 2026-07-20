# B3 bandwidth dose-response (2026-07-20)

Roadmap item 2: does solve rate degrade monotonically as the channel widens
from constrained to unconstrained, and does the fragment operator crowd out
mutation as bandwidth grows? The Stage-4 run had flagged unconstrained sharing
(B3) as the worst arm; this tests whether that is a real, mechanistic H3 effect
or noise.

## Setup

- Stage-1 subset (30 tasks), 1M candidate-evaluations/run, 3 seeds, 3 lineages.
- A matched-compute bandwidth ladder (increasing bandwidth ~ K×M):
  `none` (B1) → `K2M1` → `K4M3` (=B2) → `K8M10` → `uncon` (B3).
- `clebran.baselines.dose_response`; raw summaries in [results.jsonl](results.jsonl),
  table in [ladder_table.txt](ladder_table.txt).

## Result: flat — and the hypothesized mechanism is absent

```
config   n    solved/30   evo-solved      reuse  frag-share   frag-succ   mut-succ
none     3   10.33±0.58    2.00±1.00  0.00±0.00   0.03±0.00   0.02±0.00  0.36±0.01
K2M1     3   10.33±0.58    2.00±1.00  0.04±0.04   0.03±0.00   0.02±0.00  0.36±0.01
K4M3     3   10.67±0.58    2.33±0.58  0.05±0.02   0.03±0.00   0.02±0.00  0.36±0.00
K8M10    3   10.33±0.58    2.00±1.00  0.16±0.10   0.03±0.00   0.02±0.00  0.36±0.01
uncon    3   10.00±0.00    1.67±0.58  0.17±0.09   0.03±0.00   0.02±0.00  0.36±0.01
```

- **No dose-response.** Solve rate is flat across the whole ladder (10.0–10.7,
  all overlapping in noise). `uncon` is nominally lowest (10.0, and the only
  config with zero seed variance) but the gap to the rest is within one solve.
  This is consistent with the Stage-4 B3 result never having been significant
  (B2−B3 = +0.60, pooled se 0.32) — the "B3 is worst" observation does not
  survive a controlled bandwidth sweep.
- **The crowding mechanism does not occur.** `frag-share` is pinned at **0.03
  regardless of bandwidth** — identical even for `none`, which has no channel at
  all. Bandwidth changes *which* fragments are used (reuse rises 0.00 → 0.17) but
  not *how much* fragment-splicing happens.

## Why: adaptive operator selection self-regulates the channel

The fragment operator's share is set by **adaptive operator selection** (AOS,
added during Stage 1 to make the channel comparison fair), which weights each
operator by its recent child-≥-parent success. Fragment splicing succeeds only
~2% of the time here versus ~36% for mutation, so AOS holds it near a floor
share (~3%) *independent of how much material the channel supplies*. Dumping a
whole library (unconstrained) cannot crowd out mutation, because the learner
already down-weights a channel that keeps failing.

**This is a substantive result, not just a null.** The naive
information-bottleneck story — "unlimited bandwidth floods the learner with
noise and hurts" — assumes a learner that ingests whatever it is given. An
adaptive learner that regulates intake by success is *robust* to unconstrained
sharing: the constraint stops mattering because the learner self-constrains. It
complicates H3 rather than confirming it.

## What this does and does not settle

- On the Stage-1 substrate, H3 is effectively untestable: reuse tops out at
  ~17% even unconstrained, so the channel barely engages and AOS neutralizes
  what little arrives. The flat curve says "no effect here," not "constraint
  never matters."
- The regime where H3 could still be real is the **frontier** (item 1), where
  reuse ran 0.67–1.00: there received fragments *succeed often* (they are needed
  for composition), so AOS *up-weights* the fragment operator, and the quality
  difference between a curated constrained channel and a flooded unconstrained
  one could finally bite. The dose-response should be rerun on the frontier as
  part of the item-1 sweep, reading `op_mix` down the ladder.
- Reporting caveat for any writeup: the Stage-4 "unconstrained is the worst arm"
  line should be softened — a controlled sweep shows it is within noise and the
  mechanism behind it is suppressed by AOS.
