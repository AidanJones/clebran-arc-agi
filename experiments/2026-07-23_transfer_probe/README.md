# Paired transfer probe — does a taught concept transfer? (2026-07-23)

> **⚠️ CORRECTED by [2026-07-23_amortization](../2026-07-23_amortization/README.md).**
> This probe's headline ("concepts DO transfer, ~2× speedup, p = 0.025") was
> **wrong** — it compared taught vs an *irrelevant-curriculum control* with no
> no-teaching baseline. Adding a **cold** (no-curriculum) baseline shows
> **taught ≈ cold** (−986 evals, p = 0.97): relevant teaching gives *no*
> target-solve speedup. The 2× was **irrelevant teaching harming the control**
> (control − cold = +43k), not relevant teaching helping. Honest verdict:
> relevant teaching is neutral; irrelevant teaching hurts. Read the amortization
> writeup for the corrected three-way result; the analysis below is left intact
> as a record of the confound.


The curriculum frontier run left two explanations confounded: concepts genuinely
don't transfer, or the curricula were aimed at the wrong target. This probe
separates them with a controlled teach → test protocol, and finds a clear,
significant answer that **partly vindicates the curriculum idea while explaining
its null**.

## Setup

- **Phase 1 (teach):** evolve on *only* a curriculum (prerequisite-gated), then
  mine what was learned into named abstractions.
- **Phase 2 (test):** spend the rest of a **shared total budget** (500k) on
  *only* the target, carrying the phase-1 library forward.
- **Taught arm:** curriculum = the target's own prerequisite decomposition —
  i.e. exactly the concepts the target needs (an **oracle**-relevant curriculum,
  so this measures the *upper bound* on transfer).
- **Control arm:** an unrelated program's decomposition, **truncated to the same
  item count**, same seed, same total budget.
- 8 targets (reference depth ≥ 3) × 5 seeds → **34 paired (target, seed) runs**
  per arm. [analysis.txt](analysis.txt), [results.jsonl](results.jsonl).

## Results

| | taught | control |
|---|---|---|
| target solve rate | 38.2% (13/34) | 32.4% (11/34) |
| curriculum learned | 50% | 46% |
| mean teach budget used | 82.6k | 90.2k |
| mean test budget available | 417k | 410k |
| **evals-to-solve, as fraction of available budget** | **0.150** (median 0.115) | **0.318** (median 0.234) |

**Paired outcomes over 34 pairs:** taught-only solves 4 · control-only 2 ·
both 9 · neither 19.

## Two findings, opposite in sign

**1. Solve rate: null.** 4 vs 2 discordant pairs, binomial **p = 0.688**.
Teaching the exactly-right prerequisites did **not** expand *what* is solvable.

**2. Speed: real and significant.** Among runs that solved, the taught arm used
**15.0% of its available budget vs 31.8%** for control — roughly **2× faster** —
permutation test **p = 0.025**.

Crucially this is **not a censoring artifact**: both arms spent almost the same
teaching budget (82.6k vs 90.2k), so both had nearly identical test budget
available (417k vs 410k). The taught arm genuinely finds the target sooner; it
isn't just that it had less budget in which to be observed.

## What this means

**Concept transfer is real — it accelerates search — but acceleration is not the
same as capability.** A relevant curriculum makes the target roughly twice as
cheap to find, and changes almost nothing about which targets are findable at
all.

That precisely explains the curriculum channel's null (B8 − B1 = +0.15, ns): the
channel's benefit is *speed*, but the arm metric is *solve count at fixed
budget*. Speed only converts into solve count for tasks sitting **near** the
budget frontier. Ours mostly aren't — 19 of 34 pairs were solved by *neither*
arm, i.e. far out of reach, and 9 were solved by *both*, i.e. comfortably
reachable. Only a handful were marginal, and that is exactly the population a
2× speedup can flip.

So the curriculum idea was measured with the wrong endpoint on the wrong task
distribution, not falsified.

## Implications

- **The endpoint should include cost, not just count.** Evals-to-solve is where
  teaching shows up; solve-count-at-fixed-budget hides it.
- **Where it would pay off:** a task distribution concentrated near the budget
  frontier (marginal tasks), or a larger budget that turns currently-hopeless
  tasks into marginal ones. Both are testable.
- **Upper-bound caveat:** the taught curriculum here is an oracle decomposition
  of the target's own solver. Real peer-generated curricula are strictly worse
  targeted, so ≈2× is a ceiling on the speed benefit, not a typical value.
- The earlier finding that students *learn* taught concepts (78% of teaching
  tasks solved) plus this one gives the full chain: **concepts are learnable,
  they do transfer, the transfer is worth ~2× search cost, and that is too
  little to move a solve-count metric on a task set with few marginal tasks.**
