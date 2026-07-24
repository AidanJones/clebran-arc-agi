# 1. Introduction

The Abstraction and Reasoning Corpus (Chollet, 2019) was designed to
measure a property its author calls *skill-acquisition efficiency*: the
ability of a system to acquire new competencies quickly, relative to its
priors, experience, and generalisation difficulty. In *On the Measure of
Intelligence* (Chollet, 2019) the warning is explicit — *unlimited
priors or unlimited training data let you "buy" skill*, masking a
system's actual generalisation power. That framing is what motivates
ARC's small training set, its held-out evaluation split, and the
deliberate absence of internet-scale supervision. It is also what makes
ARC uncomfortable for contemporary systems: a frontier language model
scaled with enough pretraining can solve a substantial fraction of the
public tasks, but the headline number carries no information about how
the model would do if its priors or data were smaller, and therefore
tells us little about the acquisition efficiency we say we care about.

This paper is a deliberate step *away* from chasing the headline
accuracy. We work in a setting small enough that the acquisition cost
is metered rather than guessed: pure-reward evolutionary program
synthesis over a hand-designed DSL, on a 30-task frontier subset of
ARC-AGI-1, with matched candidate-evaluation budgets audited to 0.1%.
The questions we set out to ask concern *whether populations that
communicate* improve on those that do not; the question we ended up
asking concerns *how to measure a learner's acquisition efficiency at
all*.

## 1.1 The clebran hypothesis

The original clebran question (Welsh: *clebran*, to chatter, to gossip)
was that multiple populations of DSL programs, each evolving under
pure reward on ARC tasks and therefore diverging into genuinely
different solution strategies, would solve more problems at matched
compute if they were allowed to exchange successful fragments through a
constrained DSL channel. The intuition has three parts: (i) that
independent reward-driven search will diverge into different
abstractions, *because* the search is partial (H1); (ii) that exposing
each lineage to a peer's fragments helps it reach solutions it would
not reach alone (H2); and (iii) that a *bandwidth-limited* channel
preserves better abstractions than an unconstrained library-dump (H3).
A later extension (the *recovered-primitive* variant) asked whether
sharing subroutines a lineage had *discovered for itself* would beat
sharing raw code over a hand-designed vocabulary (the "given versus
recovered" comparison, sometimes called §11 in the project).

The promise of the clebran design is closely related to two active
research literatures. From emergent communication (Lazaridou & Baroni,
2020; Kiela, 2019), it borrows the hypothesis that a bandwidth-limited
channel between divergent agents induces compositional, generalisable
protocols. From library learning and the DreamCoder/Stitch line
(Ellis et al., 2020; Bowers et al., 2023), it borrows the
abstraction-discovery mechanism and the *minimum-description-length*
pressure that makes discovered subroutines cheap to re-use. The
project's specific contribution, in its original framing, was to put
those two ideas together on ARC: divergent lineages that gossip their
*recovered* subroutines, and the bandwidth of the gossip acts as the
abstraction-quality filter.

## 1.2 What the experiment found

It did not work. The clebran question, as posed, is **falsified** by
its own strongest control, and a falsification is the most useful
thing a small, well-instrumented study can produce.

The qualitative headline: across nine arms and twenty seeds at
matched compute on the frontier subset, the multi-agent arms with a
constrained channel are not better than the strongest single-agent
baseline — and the central-library control (the DreamCoder/Stitch
arm) is significantly *better* than the multi-agent channels. The
mechanism the clebran design assumed the channel would provide
(*sharing of recovered abstractions between divergent populations*)
is real but small, and the *cost of splitting compute across
populations* is larger than the benefit the channel can pay back.
H1 (lineages diverge) is supported; H2 (transfer helps) and H3
(the constraint matters) are null. H1 is supported
(lineages do diverge) but, in this substrate, divergence is a
*liability* rather than an asset: the multi-agent arms' mined
vocabularies are less compositional (mean topographic similarity
0.14–0.15 vs 0.33 for B5) and less cross-task-reused (0.05 vs 0.15)
than a single agent's. H2 and H3 are null, in the form that they were
originally posed. The constraint does not help, because adaptive
operator selection already self-regulates a failing channel — a
subtler mechanism than the information-bottleneck story originally
invoked.

The result is striking enough that we asked two follow-up questions to
make sure it was the *channel* that failed rather than the design's
*measurement*. The first is a controlled teach→test probe (§5.7.1): a
lineage is taught a curriculum built from the *target's own*
prerequisite decomposition (an oracle curriculum that maximally targets
the right concepts) and is then asked to solve the target with the rest
of the budget. The naive comparison — taught vs a control taught an
unrelated curriculum — showed an apparent 2× speedup, but adding a
*cold* arm (no curriculum at all) reveals that the apparent benefit was
actually the size of the harm to the mis-targeted control. With the
cold baseline, **taught − cold = −986 evals (permutation p = 0.97)**:
a relevant curriculum gives no target-solve speedup; an irrelevant
one is *slower* than not teaching at all. The honest verdict is that
relevant concept teaching is roughly neutral, irrelevant concept
teaching causes negative transfer, and the per-student condition
L + T < U fails by ≈ 56k evals — a number no amortisation across N
agents can rescue.

The second follow-up concerns the *endpoint* itself. Throughout the
project, every arm was scored on solve count at a fixed budget. The
transfer probe shows that curriculum teaching's benefit lives in
*evals-to-solve*, not in solve count, and only converts to solve count
for tasks *near* the budget frontier. The frontier subset has very few
such tasks. Almost every prior null on the project is therefore a
null on a *solvable-frontier* metric, not a null on acquisition
efficiency. Re-scoring on cost is a cheap fix; it does not undo the
headline ranking, but it does reframe the discussion: the question is
not whether the channel helps, but how to measure what *does* help.

## 1.3 The reorientation

The result forces a reorientation of the project's scientific question.
The clebran design tried to buy acquisition efficiency by adding
*communication* to evolution. The data argue, instead, that the better
purchase is to *concentrate* the compute: one agent that sees every
task and reuses its own mined abstractions strictly dominates several
agents that see task slices and share. Communication has a small,
real, hard-to-detect effect that lives in evals-to-solve, not in solve
count, and that is more than wiped out by the divergence tax — the
cost of splitting a fixed budget across populations.

The more interesting question, then, is not "does communication help?"
but "does the *way a system learns* change how well it can use what
it learned?" That is Chollet's re-statement of intelligence as
acquisition efficiency, applied at the level of an individual learner.
The current paper makes two contributions to that question: it
delivers a falsification of the multi-agent-with-channel hypothesis
that any future work in the area will need to address, and it
proposes a capability audit (core-knowledge priors, abstraction /
compression, communication and teaching, honest measurement,
acquisition efficiency as the objective, self-directed practice,
active learning, continual learning without rigidity, compositional
generalisation, generalisation to genuinely unseen tasks, meta-learning,
reflection) that frames what a *process-aware* learner would need to
have before "how you learned it" can be studied cleanly.

## 1.4 Contributions

Concretely, the paper contributes:

1. **The clebran design** — a typed linear-IR DSL over Hodel's 160
   ARC primitives, with a deterministic interpreter, a typed GP engine
   with phase-1 systematic seeding and adaptive operator selection, a
   Stitch-style compression miner, a blackboard channel with three
   constraint regimes and four payload types, and a measurement rig
   that audits candidate-evaluation budgets to better than 0.3%
   spread. The implementation is open-source, deterministic, and
   reproduces 399/400 of Hodel's reference solvers through our
   interpreter.
2. **A falsified central hypothesis** — the multi-agent-with-channel
   design is dominated by a single agent with a central library at
   matched compute, with the single significant comparison being
   **B6 − B5 = −0.85 (~2.2 se)**. The null is the headline; the
   baselines are strong enough that a null is trustworthy.
3. **A controlled teach→test protocol and a transfer-vs-reconstruction
   decomposition** — students acquire the teacher's concepts (78% of
   teaching tasks solved) but do not transfer them to novel tasks
   needing the same concepts. This is the L2T transfer-versus-
   reconstruction gap appearing at the level of whole concepts.
4. **A re-scoring of every prior arm on cost-to-solve**, exposing that
   the effect of teaching lives in evals-to-solve and is invisible
   under solve count at fixed budget.
5. **A scope claim** — on ARC program synthesis at matched compute,
   communicating learned content does not help, mis-targeted
   communication hurts, and *how* a system learns, not what it
   eventually knows, is the next question the substrate can answer.
6. **A capability audit** for what an "acquisition-efficient" learner
   would need before the reorientation can be made operational.

## 1.5 Outline

Section 2 positions the work against the relevant literatures
(program synthesis for ARC, library learning, emergent communication,
L2T/NEO, multi-agent program synthesis, curriculum learning).
Section 3 describes the clebran design in detail. Section 4 states the
three sub-hypotheses and the arm table, and lays out the match-compute
protocol and statistical convention. Section 5 reports the results
across H1, H2, H3, the recovered-primitive and curriculum channels, the
central-library control, the teach→test probe, and the amortization
result. Section 6 discusses the reorientation, the divergence tax, the
role of measurement, and the scope. Section 7 lays out limitations.
Section 8 concludes.
