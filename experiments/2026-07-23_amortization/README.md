# Amortization + the honest baseline (2026-07-23)

This experiment added the baseline the transfer probe was missing — a **cold**
agent with *no* curriculum — and in doing so **overturns the transfer probe's
headline**. It also settles the amortization question (roadmap 8a).

## Setup

Paired **cold** (empty curriculum, full budget on the target) vs **taught**
(target's own oracle prerequisite curriculum) on the same (target, seed);
8 targets (depth ≥ 3) × 5 seeds, total budget 500k, teach cap 150k. Merged with
the transfer probe's **control** arm (unrelated curriculum) — same targets,
seeds, budget and code — for a clean three-way. [analysis.txt](analysis.txt),
[results.jsonl](results.jsonl).

## The three-way result (target-solve cost, 9 pairs solved by all three arms)

| arm | curriculum | target-solve evals (T) | solve rate |
|---|---|---|---|
| cold | none | 73,152 (median 61,866) | 35.3% |
| taught | target's own (relevant) | 72,166 (median 72,082) | 38.2% |
| control | unrelated (irrelevant) | 116,067 (median 83,221) | 32.4% |

| paired difference | Δ | perm p | reads as |
|---|---|---|---|
| **taught − cold** | **−986** | **0.967** | relevant teaching ≈ **no teaching** |
| control − cold | +42,915 | 0.269 | irrelevant teaching is **slower** than no teaching |
| control − taught | +43,901 | — | *this is what the transfer probe measured* |

## This corrects the transfer probe

The probe ([2026-07-23_transfer_probe](../2026-07-23_transfer_probe/README.md))
reported "concepts DO transfer, ~2× speedup (p = 0.025)". That comparison was
**taught vs control** — and it lacked a no-teaching baseline. With the cold
baseline added:

- **taught ≈ cold** (−986, p = 0.97): a relevant curriculum gives **no** target-
  solve speedup over not teaching at all.
- **control > cold** (+43k): the probe's effect was **irrelevant teaching
  *harming*** the control, not relevant teaching helping.

So the honest statement is the opposite of the probe's headline: **relevant
teaching is roughly neutral; irrelevant teaching hurts (negative transfer).**
The probe's `2×` measured the size of the harm to the control, mislabeled as a
benefit. This is exactly the confound the cold arm was built to catch, and the
reason the probe writeup and FINDINGS have been corrected rather than extended.

## Amortization (roadmap 8a): fails, and not for lack of N

Even ignoring the neutral T, the taught agent must *acquire* the curriculum
first (cost **L**). Per student, taught total is **L + T = 128,942** vs cold
**U = 73,152** — the per-student condition **L + T < U is violated by ~56k**.
Amortization only spreads the *teacher's* one-time cost across N students; if
each student is individually worse off, no N rescues it. **The crossover formula
has no solution.** Sharing a curriculum among many agents cannot pay off here,
because the thing being shared does not make an individual agent cheaper.

## Honest caveats

- **Protocol wastes teaching budget.** L median is only 7,561 but the mean is
  56,775 — a few runs burn the full 150k teach cap without finishing. A fair
  "teach efficiently" test needs an early-stopped teach phase (stop when the
  curriculum is solved *or* clearly stalling). That would lower L, but since
  T ≈ cold already, it cannot turn the per-student condition positive — it only
  reduces how badly it loses.
- **Oracle upper bound.** The taught curriculum is the target's own solver
  decomposition — the best possible targeting. Real peer curricula are worse.
- **Small n** (9 all-solved pairs); the −986 is a tight null, the +43k control
  penalty is noisier (p = 0.27) but directionally consistent with the probe's
  significant taught-vs-control gap.

## Verdict

Relevant concept teaching, at the oracle upper bound, is **neutral on capability
and neutral on target-solve cost**, while costing budget to acquire; irrelevant
teaching is **harmful**. Amortization cannot save it. Combined with B5 (a single
concentrated learner is best) and the divergence-degrades-vocabulary finding,
the project's picture is now consistent and blunt: **in this substrate,
communicating learned content — as code or as curricula — does not help, and
mis-targeted communication hurts.** The remaining live thread is not *content*
transfer but *process* (roadmap 9): whether the *way* a system learns can be
improved and measured on the acquisition-efficiency axis, where — unlike here —
the instrument shows real structure.
