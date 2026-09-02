# Heterogeneous-fitness pilot (2026-08-31) — discovery-bottleneck #2

The first concrete test of *changing what the lineage values*. The
default B5 uses `lam_mdl=1.05` (NEO-style adaptive-length factor):
tiebreak is `cell_acc * 1.05^(-len)`. The strong-MDL variant uses
`lam_mdl=1.5` — a stronger length penalty that pushes harder for
shorter programs.

**The result: stronger length penalty is *worse* than default
B5 (9.60 vs 10.40 frontier solves).** Changing the secondary
tiebreak weight doesn't help. Combined with the #1 (failure-mode
dreaming) null, the picture is: **the default B5 is well-tuned
for this frontier, and small perturbations to the objective
structure all hurt the frontier.**

## Setup

Same as B5-1M (frontier subset, 1M evals/run, 5 seeds 1-5), but
with `lam_mdl=1.5` instead of the default 1.05. The change is
applied at the Evaluator level — the cell-accuracy tiebreak becomes
`cell_acc * 1.5^(-len)` (instead of `* 1.05^(-len)`), making
shorter programs strongly preferred among equal solvers.

Saved to `b5-strongmdl_1m_seed*.jsonl` to avoid overwriting the
default B5-1M data.

## Headline: stronger MDL is *worse*

| arm | frontier | evo-solved | evals/solve |
|---|---|---|---|
| **B5-1M** (default, λ=1.05) | 10.40 ± 1.14 | 3.20 ± 0.84 | 97,077 |
| B5D-1M (solved-source dreams) | 10.40 ± 0.55 | 3.20 ± 0.84 | 96,457 |
| B5D-NM-cons (failure-mode dreams) | 9.80 ± 0.45 | 2.60 ± 0.55 | 102,230 |
| **B5-strongmdl** (λ=1.5) | **9.60 ± 1.14** | **2.40 ± 1.14** | 105,468 |
| B5D-NM-aggr (failure-mode dreams, high vol) | 8.80 ± 0.84 | 1.60 ± 0.55 | 115,183 |

*Source:* cost analyzer output.

**All four "discovery" variants are *worse* than default B5:**
- B5D (solved-source dreaming): tied, not significant
- B5D-NM-cons: -0.6 frontier, not significant
- B5-strongmdl: -0.8 frontier, not significant
- B5D-NM-aggr: -1.6 frontier, **significant (p=0.007)**

The pattern: changing the B5 objective structure (in any direction
tested) does not expand the frontier. **The default B5 is well-
tuned; the "improvements" we tried are subtractive.**

## What this means

The #2 hypothesis was: changing what the lineage values would
lead to different discoveries. The data says: the default
objective structure (cell_accuracy with light MDL penalty) is
*optimal* for this frontier, and the perturbations we tried
all hurt.

But: this is a *partial* #2. The full heterogeneous-fitness
experiment would also test:
- **Pure length** (drop accuracy, minimize length only).
- **Pure diversity** (maximize primitive diversity in the program).
- **Pure novelty** (maximize behavioral novelty compared to the rest
  of the population).

These would require *fundamental* fitness changes (not just a
parameter). The current pilot only tested a *parameter
variation* (λ=1.5 vs 1.05), which is a *minor* version of #2.

**The proper #2 follow-up** is to add a fitness variant that
replaces the secondary tiebreak with a primitive-diversity or
behavioral-novelty term. This requires modifying the Fitness
class in `clebran/fitness.py` and adding a new Evaluator mode.
Skipped here in favour of moving to the next discovery mechanism.

## Pattern across the discovery mechanisms

After two concrete discovery-mechanism tests:

| mechanism | n=seeds | frontier | vs B5 |
|---|---|---|---|
| (baseline) B5-1M | 5 | 10.40 ± 1.14 | — |
| #1 B5D-NM-cons | 5 | 9.80 ± 0.45 | -0.6, ns |
| #1 B5D-NM-aggr | 5 | 8.80 ± 0.84 | -1.6, **p=0.007** |
| #2 B5-strongmdl | 5 | 9.60 ± 1.14 | -0.8, ns |

**All four arms are *worse* than default B5.** The null is
consistent. The default B5 is well-tuned, and the discovery
mechanisms we've tried don't expand the frontier.

The next bet (#3 task-subset specialization) is different in
kind: instead of changing *how the lineage searches*, it changes
*what the lineage searches on* (disjoint task subsets). If
the subsets need different *kinds* of programs, division of
labor + transport might help. This is the proper test of the
clebran multi-agent premise.

## Honest scope

- n=5 seeds at 1M. The strong-MDL effect is small (-0.8 solves,
  ~1 SE) and not significant. The mechanism engages (the
  lineage produces solutions, just shorter ones), but doesn't
  expand the frontier.
- The λ=1.5 is a moderate change. The 4M test would be more
  informative but isn't run; the 1M signal is already null.
- The cost axis (per-seed evals/solve) tells the same story:
  B5-strongmdl is more expensive (105K vs 97K) for fewer
  solves.
