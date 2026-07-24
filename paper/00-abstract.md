# 0. Abstract

We test whether bandwidth-limited channels between divergent
agents — the canonical setting of emergent communication — force
compositionality and so improve transfer. The test is on a
deliberately small, fully-instrumented substrate: typed programs
evolved under pure reward on a 30-task frontier subset of
ARC-AGI-1, with matched candidate-evaluation budgets audited to
0.10% spread across 20 seeds. The baselines are strong enough
that a null is trustworthy: a single population with the same
total compute, an isolated-lineage ensemble, an unconstrained
library-dump channel, and — critically — a *single agent that
grows a central abstraction library* (a DreamCoder/Stitch
control).

**The headline.** On this substrate, the central-library control
(B5) sits at the top of the ranking. The single significant
comparison in the entire study is **B5 − B6 = +0.85 (~2.2
standard errors)** — sharing a *discovered* vocabulary between
divergent agents is significantly *worse* than letting one
agent keep the vocabulary. Every other multi-agent arm — across
four payload types (fragment, signal, recovered-primitive,
curriculum) and three constraint regimes (CH-NONE,
CH-CONSTRAINED, CH-UNCONSTRAINED) — lies between the
isolated-lineage floor and the central-library ceiling. The
multi-agent-with-channel hypothesis is falsified by its own
strongest control.

**What the data also show.** H1 (lineages diverge) is supported
— pairwise primitive Jaccard 0.57 ± 0.10 — but divergence in
this substrate is a *liability* for vocabulary quality: the
single agent's mined library is more compositional (topographic
similarity 0.33 vs 0.14–0.15 for the multi-agent arms) and more
cross-task-reused (0.15 vs 0.05). H3 (the constraint matters) is
null across all four payload types, because adaptive operator
selection self-regulates a failing channel regardless of
bandwidth. H2 (transfer helps) is directionally positive but
not significant at 20 seeds; the recovered-primitive channel
beats isolation by +0.35 (se 0.32) and the fragment channel by
+0.20 (se 0.32).

**What the re-scoring shows.** A controlled teach→test probe
with a *cold* (no-curriculum) baseline reveals that the
*probe's* apparent 2× speedup was the size of the harm to a
mis-targeted control; against a cold baseline, a relevant
curriculum is roughly neutral (taught − cold = −986 evals,
permutation p = 0.97), and an irrelevant curriculum is *slower*
than not teaching. The per-student condition L + T < U fails
by ~56k evals, so no amortisation across N agents can rescue
it. *Students learn taught concepts* (70–78% of synthetic
teaching tasks are solved by their peers) but do not transfer
them to novel tasks needing them — the L2T
transfer-vs-reconstruction gap at the level of whole concepts.

**The contribution.** The paper is a falsification plus a
reorientation. The falsification is that, on ARC program
synthesis at matched compute, a single agent with a central
library strictly dominates divergent lineages with a
constrained channel. The reorientation is to the question
Chollet argues is the right one — the *skill-acquisition
efficiency* of a system, not its skill — and to a small set of
process-level capabilities (self-directed practice, active
choice of what to practise, retention without rigidity,
reflection on how something was learned) that must be present
before "how you learned it" can be studied cleanly. The asset
of the work is the matched-compute measurement rig: a
deterministic typed IR, a reproducible per-task RNG substream
scheme, an audited candidate-evaluation budget, and a track
record of reporting nulls.
