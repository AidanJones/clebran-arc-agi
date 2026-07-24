# 7. Limitations

The clebran experiment is small by design, and the smallness is
both a strength and a limitation. We list the limitations in
order of how much they bound the result's claim.

**Substrate.** The experiment is scoped to ARC-AGI-1 program
synthesis over Hodel's 160 typed primitives, with a pure
evolutionary search and no neural component. The negative
result — that divergent multi-agent populations with a
constrained channel are dominated by a single agent with a
central library — is established on this substrate only. The
transfer of the result to other program-synthesis settings
(e.g. string transformation benchmarks), to other multi-agent
settings (e.g. emergent communication referential games with
non-adaptive learners), and to language-model agents is an
empirical question for each. The result is most relevant where
the substrate is a small, fully-instrumented one and the
learner is adaptive.

**Frontier.** The frontier subset is 25 D2 + 5 D3 tasks
(depth 2-dominated, because D3 is beyond reach at 4M evals).
The solvable frontier is therefore narrow, and the headline
effects are 1–3 evolution solves/seed. Most comparisons are
underpowered by construction. The single significant
comparison is B6 − B5 = −0.85 (~2.2 se); the rest of the
ranking is *consistent* across runs but not per-comparison
significant.

**Solve count vs cost-to-solve.** The headline endpoint is
*evolution-phase solves* (count) at a fixed candidate-
evaluation budget. Cost-to-solve is a *secondary* endpoint
that has been re-scored for the teach→test probe and the
amortization result; the multi-agent headline ranking has
not been re-scored on cost. A cost-axis re-scoring of the
B0–B9 frontier ranking is a small, cheap follow-up that
should be done before publication; it may not change the
ranking, but it would change the discussion of how the
ranking was *measured*.

**Single round of sharing.** The experiment runs *one* round
of communication. The iterated form (curriculum₁ → agents₂ →
curriculum₂ → …) — the actual open-endedness question — is
unaddressed. The single round is what the *channel* baseline
in the emergent-communication literature typically uses, and
it is the right unit for a falsification experiment; it is
not the right unit for a *positive* result on competence
compounding.

**No compositional OOD split.** The L2T compositional-OOD
and length-OOD splits (Baek et al., 2026) — controlled
distributions over the compositional depth and length of the
target program — are an interesting generalisation probe.
The clebran experiment does not run them; the headroom for
positive transfer effects is therefore unknown.

**No eval-split generalisation.** All reported results are on
the training split. The 400-task eval split is reserved for
the "does this generalise to genuinely unseen tasks" question
and has not been touched. The clebran design's library-
mining mechanism is the part of the project most likely to
show *or fail to show* generalisation; the eval split is
the obvious next test.

**Noisy underpowered comparisons.** Several headline
comparisons (B6 − B1, B6 − B2, B8 − B6) are at 1.0–1.4
standard errors — directionally consistent across runs but
not per-comparison significant. The cleanest interpretation
is the *ordering* of the arms, not any single pairwise
contrast.

**Compression miner is not optimal.** The compression miner
is Stitch-style anti-unification, which is fast but
sub-optimal compared to a full search-based compression
algorithm. A more compressive miner might produce a better
library for B5 (raising the bar further for any multi-agent
arm). The clebran result therefore *understates* the
advantage of the central library; the falsification is
robust to this concern.

**Missing B0+library control.** The B5 win is confounded
between three factors: (a) centralisation (one agent vs
three lineages), (b) library-pool size (B5's pool is built
from ~2.65 mean solves, ~4× the per-lineage pool of B6/B7),
and (c) the library mechanism itself. The cleanest
isolation of the library mechanism is a *B0 + library* arm
(a single population with the same compression miner, no
multi-agent framing), which is the obvious follow-up that
would isolate the contribution of the library mechanism
from the contribution of centralisation. This arm is listed
in the project's roadmap but has not been run; the B5
headline should be read as "centralisation plus the library
mechanism dominates divergence plus any channel," not as
"the library mechanism alone is what wins." Until the
B0+library control is run, the clebran paper's
library-learning framing (§6.2, §6.5) is supported by the
vocabulary-quality metrics but not by a clean solve-count
contrast.

**No statistical power analysis.** The standard errors are
*descriptive*, not a power analysis. A power analysis would
let us say "X more seeds are needed to detect effect size d
at α = 0.05, β = 0.2" — useful for sizing follow-up
experiments, not done here. The current seed counts (5 on
Stage-1, 20 on the frontier) are *large enough* to detect
the B6 − B5 effect, but not large enough to detect smaller
channel-driven effects even if they exist.

**Cross-task reuse metric is conservative.** Cross-task
reuse is the fraction of pairs (task, abstraction) where the
abstraction is used on a task *other than* the one it was
mined from. The metric does not count an abstraction that
is *available* in the lineage's library but unused on a
later task; the right metric for "is the library useful" may
also include the *availability* rate. The reported numbers
are therefore a *lower bound* on cross-task utility.

**The order experiment is small and narrowly scoped.** The
completed run is 216 rows — 9 targets (depth ≥ 3, ≥ 2
prerequisite steps) × 6 seeds × four order arms
(forward / reverse / shuffled / cold, §5.7.3). Two paired
comparisons are significant (forward − reverse and
forward − cold, both McNemar p = 0.021), but the discordant
counts are small (9–17 pairs), the significant effects are on
*capability* (solve rate) rather than the pre-registered
cost-to-solve endpoint (all order-vs-order evals contrasts are
null), and the significant "well-ordered teaching helps" result
(forward − cold) is scoped to targets with ≥ 2-step
decompositions — it does not generalise to tasks without
compositional structure, where amortization found teaching
neutral. A preliminary partial-data read had shown a larger
forward-vs-shuffled gap that regressed to non-significance at
full n, a caution against reading early cells. The result is
reported as the first *process* effect, honestly bounded, not as
a general claim that curriculum ordering optimises learning.

**Honest reporting of nulls.** The project has a track
record of correcting its own nulls: the transfer probe
showed a 2× speedup, the amortization experiment showed
the speedup was an artifact of a missing cold baseline, and
the FINDINGS and README were updated. The clebran design's
*measurement rig* (matched compute, audited budgets, strong
baselines, paired designs, permutation tests) is the part
of the project that makes the nulls trustworthy; it is
also the part that future work should reuse.
