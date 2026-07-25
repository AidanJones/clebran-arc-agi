# Abstract

Chollet defines intelligence as *skill-acquisition efficiency* and warns that
unlimited priors or data let a system "buy" skill, masking generalisation. We
take that seriously in a small, fully-instrumented substrate — typed programs
evolved under pure reward on ARC-AGI-1 — and ask not whether communicating
learned *content* between agents raises skill (a companion paper shows it does
not), but whether the *way* a system acquires knowledge changes how well it can
use it. Three matched-compute experiments, all on a teach→test protocol with
cost-to-solve as the primary endpoint, give a sharp and initially
counter-intuitive picture. First, a curriculum channel that shares synthetic
tasks *works mechanically* — peers solve 70–78% of the tasks they are taught —
yet buys nothing on real tasks: learning a concept is not transferring it.
Second, a controlled teach→test probe appeared to show a 2× acquisition speedup
from a relevant curriculum; adding the missing *no-teaching* baseline reverses
the reading — relevant teaching is neutral (−986 evals, p = 0.97) and
*irrelevant* teaching is harmful, so the "2×" was the size of the harm to a
mis-targeted control. No amortization across N students can rescue a per-student
loss. Third, and positively, when *content is held fixed and only the order of
acquisition varies*, order significantly changes capability: a curriculum taught
foundations-first beats the same content taught foundations-last (paired
McNemar p = 0.021), because a dependency-violating order halves how much of the
curriculum is acquired. The effect is asymmetric — *don't teach backwards*
matters more than teaching in exactly the right order — and it is the study's
only significant *process* effect against a wall of null *content* effects. We
argue this reorients the question from what a system knows to how it learned it,
and enumerate the process capabilities a learner needs before that question can
be studied richly.

# 1. Introduction

The companion paper (*On the Cost of Communication in Divergent Program
Evolution*) establishes a falsification: at matched compute on ARC program
synthesis, a single agent with a central abstraction library significantly beats
divergent agents communicating over a constrained channel, across four payload
types. Communicating learned *content* — as code or as curricula — does not help.

This paper asks the next question. Machine Learning Street Talk, and Chollet's
*On the Measure of Intelligence* more formally, press an idea our arm-comparison
was blind to: intelligence is *skill-acquisition efficiency*, not skill, and the
danger of large-prior/large-data systems is that they *buy* skill in a way that
hides generalisation. A small, metered, pre-neural learner is exactly the setting
in which acquisition cost is measured rather than purchased. So we reframe: not
*what* an agent ends up knowing, but *how it learned it*, and whether that
changes what it can do.

We report three experiments, all sharing a **teach → test** protocol. Phase 1
evolves a learner on a curriculum only, then mines the resulting library. Phase 2
spends the rest of a shared total budget on a held-out *target* task, carrying
the phase-1 library forward. The primary endpoint is *evals-to-solve* — the cost
of reaching a capability — because, as we show, the effect of teaching lives in
cost and is invisible under solve count at a fixed budget.

**Contributions.**

1. A transfer-vs-reconstruction result at the level of whole concepts: students
   *acquire* taught concepts (70–78% of teaching tasks solved) but do not
   *deploy* them on novel tasks that need them.
2. A methodological correction that turns on a *cold* baseline: an apparent 2×
   teaching speedup is, against a no-teaching control, the *harm* done by a
   mis-targeted curriculum, not a benefit of a relevant one. Relevant teaching is
   neutral; irrelevant teaching causes negative transfer.
3. An amortization analysis showing the per-student teaching cost exceeds the
   per-student saving, so no number of students rescues it.
4. A first significant *process* effect: with content held fixed, the *order* of
   acquisition significantly changes capability — asymmetrically, don't teach
   backwards.
5. A capability audit of what an acquisition-efficient learner needs before "how
   you learned it" can be studied richly.

# 2. Substrate and protocol

The substrate is described fully in the companion paper: typed programs evolved
under pure outcome reward over Hodel's ARC DSL, with a deterministic interpreter
and matched candidate-evaluation budgets. Three additions matter here.

**Task generation.** A learner can synthesise ARC tasks by running a discovered
program *forward* on structured sampled input grids, keeping the resulting
(input → output) demonstration pairs — a well-formed task the program provably
solves, i.e. a variant of the concept it captured. This is the enabling
capability for a curriculum: knowledge can cross as *problems*, not code.

**Prerequisite decomposition.** A solved program `x0 = f0(…); …; O = fk(…)` has,
at each grid-producing prefix, a self-contained sub-transform — the earlier
abstractions the composition is built from. Generating a task from each prefix
and ordering shortest-first yields a curriculum that teaches each sub-abstraction
before the step that needs it. An order-aware learner *gates* a deeper task until
its prerequisites are solved.

**The teach→test protocol.** Phase 1 (teach): evolve on the curriculum only,
under a teaching cap, then mine the library. Phase 2 (test): the remaining shared
budget on the target only, carrying fragments and abstractions forward. Because
the two phases draw on one total budget, teaching efficiently simply leaves more
budget for the target — a legitimate advantage, not a confound. Unless stated,
the taught curriculum is an *oracle* decomposition of the target's own reference
solver — the best possible targeting, an upper bound on transfer.

# 3. Results

## 3.1 The curriculum channel engages but does not transfer

In the full matched-compute ranking (20 seeds × 4M on the frontier), the
curriculum channel arms B8 (constrained) and B9 (unconstrained) sit near the
bottom (1.60 and 1.65 evolution-solves), with B8 − B1 = +0.15 (ns) and the
constraint null (B8 ≈ B9). Yet the mechanism *works*: lineages received ~31
teaching tasks each and **solved 70–78% of them**, in prerequisite order, as
designed. The students demonstrably learned the concepts their peers taught, and
it bought essentially nothing on the real tasks. The bottleneck is not acquiring
a taught concept — that worked — but that *a concept learned from demonstrations
does not transfer to a new task that needs it*. A lineage can solve the
synthesised task showing `vmirror` and still not deploy `vmirror` where a
frontier task requires it. This is the L2T transfer-vs-reconstruction gap
appearing at the level of whole concepts.

## 3.2 A teach→test probe, and why it needed a cold baseline

A controlled probe compared a *taught* arm (oracle-relevant curriculum) against a
*control* arm (an unrelated program's decomposition, matched item-count, seed and
budget), 34 paired runs. It appeared decisive: target solve rate was null (4 vs 2
discordant pairs, p = 0.69), but among solves the taught arm used 15% of its
available budget versus 32% for control — a ~2× speedup, permutation p = 0.025,
and not a censoring artifact (both arms had near-equal test budget). Read alone,
this says concepts transfer and buy speed.

It is wrong, and the reason is instructive: the probe had no *no-teaching*
baseline. It compared taught against a control that was itself *harmed* by being
taught the wrong curriculum.

## 3.3 The correction: relevant teaching is neutral, irrelevant teaching harms

Adding a **cold** arm (no curriculum, full budget on the target) and merging the
three on the same targets/seeds/budget corrects the verdict. On the 9 targets all
three arms solved:

| arm | curriculum | target-solve evals |
|---|---|---|
| cold | none | 73,152 |
| taught | relevant (oracle) | 72,166 |
| control | irrelevant | 116,067 |

| paired difference | Δ | perm p | reads as |
|---|---|---|---|
| **taught − cold** | **−986** | **0.97** | relevant teaching ≈ no teaching |
| control − cold | +42,915 | 0.27 | irrelevant teaching is *slower* |
| control − taught | +43,901 | — | *what the probe measured* |

The probe's 2× was the size of the harm to the mis-targeted control, mislabeled
as a benefit. **Relevant concept teaching is neutral; irrelevant concept teaching
causes negative transfer** — a taught vocabulary biases later search, so an agent
that internalised the wrong abstractions searches *worse* than a naive one. This
is the sharpest scoping result available, and it generalises a rule: in any
"intervention helps" experiment, a do-nothing arm is the only way to distinguish
a real benefit from a harm to a mis-targeted control masquerading as one.

**Amortization cannot rescue it.** Teaching cost is paid once and could be reaped
by N students — but the economics require each student to be individually better
off. Per student, taught total L + T = 129k exceeds cold U = 73k, so the crossover
`N > C/(U − L − T)` has no solution. Sharing a curriculum among many agents cannot
pay off when the thing shared does not make an individual agent cheaper.

## 3.4 The positive result: order matters, at the extreme

The content experiments say *what* you teach is neutral-or-harmful. The order
experiment isolates *how*. It holds the curriculum content fixed — a target's k
prerequisite sub-tasks — and varies only the acquisition order, with the identical
task set and identical budget across arms; the arms differ only in the
prerequisite score handed to the order-aware gate. 9 targets (depth ≥ 3, ≥ 2
prerequisite steps) × 6 seeds → 216 runs.

| order | curriculum acquired | target solve rate |
|---|---|---|
| **forward** (foundations first) | **47%** | **48.1%** |
| shuffled (unordered) | 45% | 38.9% |
| reverse (hardest first) | **23%** | 33.3% |
| cold (no curriculum) | — | 29.6% |

| comparison (paired McNemar) | wins | p |
|---|---|---|
| **forward − reverse** | 9 vs 1 | **0.021** |
| **forward − cold** | 13 vs 3 | **0.021** |
| forward − shuffled | 7 vs 2 | 0.180 |
| reverse − cold | 5 vs 3 | 0.727 |

Two significant results, both about the *wrong* order. Teaching foundations-last
(reverse) lets the learner acquire only 23% of the same curriculum — half of
forward's 47% — because a gate that demands the composition before its parts
stalls, and one cannot learn a composition before the pieces it is built from.
That halved acquisition significantly lowers capability: forward beats reverse
(p = 0.021), and reverse is *no better than not teaching at all* (p = 0.73). Same
content, same budget, reversed order → the curriculum's value is destroyed.

But *fine-grained ordering is not the active ingredient*: forward vs shuffled is
not significant (p = 0.18), and shuffled acquires 45% ≈ forward's 47% — because
when all steps are available at once, the fundamentals are the *easy* ones and
get solved first anyway. The learner self-orders; strict gating matters only when
it can do *harm* (reverse). As with teaching-vs-not, the effect is on *capability*
(which targets solve at all), not the cost endpoint (all order-vs-order
evals-to-solve contrasts are null).

This is the study's first significant *process* effect and its first empirical
purchase on the reorientation. It is a *qualified* yes for "how you learned it":
on compositionally-structured tasks, the order of acquisition significantly
changes capability with content held constant — asymmetrically, don't teach
backwards.

# 4. Discussion

**Content is bought; process is earned.** Across the content experiments,
communicating what an agent learned is neutral (relevant) or harmful (irrelevant)
at matched compute, and no amortization rescues it. The one axis that moves
capability with content held fixed is *process* — and in this substrate it moves
mainly as a *failure mode to avoid* (a dependency-violating order is destructive)
rather than a lever to finely optimise, because an adaptive learner self-orders
when the material is merely available. That the process effect appears at all,
against a wall of null content effects, is what marks the axis as the one worth
pursuing.

**Different interventions surface on different endpoints.** Teaching-vs-not lives
in cost (the transfer probe's speed effect, before correction) or in nothing (the
corrected cold comparison); order lives in capability. A recurring methodological
lesson: report cost-to-solve *and* solve count, and include a do-nothing control —
the transfer-probe correction is the dramatic case of both.

**A capability audit.** Studying process *richly* requires capabilities the
substrate does not yet have. Chollet's core-knowledge priors are present (Hodel's
DSL encodes objectness, geometry/topology, number); abstraction, teaching, and
honest measurement are present; but the process capabilities are the gaps.

| capability | status |
|---|---|
| core-knowledge priors | have (via the DSL) |
| abstraction / compression | have |
| communication & teaching | have (4 payloads, ordered curricula) |
| honest matched-compute measurement | have — the rig |
| acquisition efficiency as the objective | instrument exists, not yet the metric everywhere |
| self-directed practice ("dreaming") | missing |
| active choice of what to practise | missing |
| retention without rigidity (plasticity) | missing, and possibly already violated (§3.3) |
| compositional generalisation to novel combinations | missing (no OOD split) |
| generalisation to genuinely unseen tasks | missing (eval split untouched) |
| meta-learning — adapting the learning algorithm | missing |
| reflection — credit assignment over *how* it learned | missing, least-explored anywhere |

The last row is the sharpest form of the thesis: a system that models its own
acquisition process and improves it. Everything above it is prerequisite
scaffolding. The order result is a proof of concept that the *axis* is measurable
here; it also shows why measuring it richly needs a learner for which order does
not self-correct as cheaply as pure GP's does.

# 5. Limitations

The teaching curricula are *oracle* decompositions of the targets' own solvers —
an upper bound on transfer; real peer curricula are worse-targeted, so the neutral
result is a ceiling, not a typical value. The teach→test and amortization
estimands are "conditional on solving" (n = 9 all-solved pairs), not
intention-to-treat; the conditional set is what makes the p = 0.97 tight. The
order result is small (9–17 discordant pairs), its significant effects are on
capability rather than the pre-registered cost endpoint, and "well-ordered
teaching helps" (forward − cold) is scoped to targets with real compositional
structure — it does not generalise to tasks without it, where amortization found
teaching neutral. The amortization teach phase uses a fixed budget that some runs
exhaust without finishing the curriculum, inflating L; an early-stopped phase
would lower L but, since T ≈ cold, cannot make the per-student condition positive.

# 6. Conclusion

Teaching an agent *what* another agent learned, at matched compute on this
substrate, is neutral when the content is relevant and harmful when it is not,
and no amortization across students rescues it — the benefit that a first probe
seemed to show was, against a cold baseline, the harm done to a mis-targeted
control. The one axis that moves capability with content held fixed is *process*:
the order in which knowledge is acquired significantly changes what a learner can
do, asymmetrically — don't teach backwards matters more than teaching in exactly
the right order. This reorients the question from what a system knows to how it
learned it, which is the question Chollet argues is the right one, and it names
the process capabilities — self-directed practice, active choice of what to
practise, retention without rigidity, reflection on one's own acquisition — that
a learner must have before "how you learned it" can be studied richly. The
substrate's asset is that, on the process axis, the instrument shows real
structure where the content axis showed only nulls.
