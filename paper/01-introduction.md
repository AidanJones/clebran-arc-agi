# 1. Introduction

The Abstraction and Reasoning Corpus (Chollet, 2019) was designed to
measure a property its author calls *skill-acquisition efficiency*: the
ability of a system to acquire new competencies quickly, relative to its
priors, experience, and generalisation difficulty. In *On the Measure of
Intelligence* (Chollet, 2019) the warning is explicit â€” *unlimited
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
recovered" comparison, sometimes called Â§11 in the project).

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
baseline â€” and the central-library control (the DreamCoder/Stitch
arm) is significantly *better* than the multi-agent channels. The
mechanism the clebran design assumed the channel would provide
(*sharing of recovered abstractions between divergent populations*)
is real but small, and the *cost of splitting compute across
populations* is larger than the benefit the channel can pay back.
H1 (lineages diverge) is supported; H2 (transfer helps) and H3
(the constraint matters) are null.

The rest of the paper is the data and the consequences. The
headline ranking is reported in §5.5; the multi-agent-channel
results are in §5.4 (recovered-primitive) and §5.6 (curriculum);
the dose-response and the mechanism behind the H3 null are in
§5.3; the teach→test probe and the cold-baseline correction that
exposed a hidden confound in the project’s first attempt at the
probe are in §5.7. The reorientation to acquisition efficiency —
which is *why* the headline was hard to see with solve-count as
the endpoint — is delivered in §6.1, where the data have earned
it.
(the constraint matters) are null.

The rest of the paper is the data and the consequences. The
headline ranking is reported in §5.5; the multi-agent-channel
results are in §5.4 (recovered-primitive) and §5.6 (curriculum);
the dose-response and the mechanism behind the H3 null are in
§5.3; the teach->test probe and the cold-baseline correction that
exposed a hidden confound in the project's first attempt at the
probe are in §5.7. The reorientation to acquisition efficiency --
which is *why* the headline was hard to see with solve-count as
the endpoint -- is delivered in §6.1, where the data have earned
it.


## 1.3 The reorientation (preview)

The headline is striking enough to demand a re-reading of the question. The clebran design tried to buy acquisition efficiency by adding *communication* to evolution; the data argue, instead, that the better purchase is to *concentrate* the compute — one agent that sees every task and reuses its own mined abstractions strictly dominates several agents that see task slices and share. The more interesting question, then, is not "does communication help?" but "does the *way a system learns* change how well it can use what it learned?" That is Chollet’s re-statement of intelligence as acquisition efficiency, applied at the level of an individual learner. The full argument is delivered in §6.1, where the data have earned it; the contribution list (§1.4) names the two deliverable pieces (the falsification, and a capability audit for what an “acquisition-efficient” learner would need before “how you learned it” can be studied cleanly).

## 1.4 Contributions

Concretely, the paper contributes:

1. **The clebran design** â€” a typed linear-IR DSL over Hodel's 160
   ARC primitives, with a deterministic interpreter, a typed GP engine
   with phase-1 systematic seeding and adaptive operator selection, a
   Stitch-style compression miner, a blackboard channel with three
   constraint regimes and four payload types, and a measurement rig
   that audits candidate-evaluation budgets to better than 0.3%
   spread. The implementation is open-source, deterministic, and
   reproduces 399/400 of Hodel's reference solvers through our
   interpreter.
2. **A falsified central hypothesis** â€” the multi-agent-with-channel
   design is dominated by a single agent with a central library at
   matched compute, with the single significant comparison being
   **B6 âˆ’ B5 = âˆ’0.85 (~2.2 se)**. The null is the headline; the
   baselines are strong enough that a null is trustworthy.
3. **A controlled teachâ†’test protocol and a transfer-vs-reconstruction
   decomposition** â€” students acquire the teacher's concepts (78% of
   teaching tasks solved) but do not transfer them to novel tasks
   needing the same concepts. This is the L2T transfer-versus-
   reconstruction gap appearing at the level of whole concepts.
4. **A cost-to-solve (acquisition-efficiency) endpoint for the teaching
   experiments**, exposing that the effect of teaching lives in
   evals-to-solve and is invisible under solve count at fixed budget.
   (Re-scoring the content arms B0–B9 on the same endpoint is a cheap
   analysis pass left as follow-up.)
5. **A first significant process result** — holding taught *content*
   fixed and varying only the *order* of acquisition, a curriculum
   taught foundations-first significantly beats the same content taught
   foundations-last (paired McNemar p = 0.021), because a dependency-
   violating order halves how much is acquired. It is the study's only
   significant *process* effect, and it is asymmetric: *don't teach
   backwards* matters more than teaching in exactly the right order.
6. **A scope claim** — on ARC program synthesis at matched compute,
   communicating learned *content* does not help and mis-targeted
   communication hurts, while *how* a system learns — the *process* —
   is where the substrate shows real structure and is the next question
   to pursue.
7. **A capability audit** for what an "acquisition-efficient" learner
   would need before the reorientation can be studied richly.

## 1.5 Outline

Section 2 positions the work against the relevant literatures
(program synthesis for ARC, library learning, emergent communication,
L2T/NEO, multi-agent program synthesis, curriculum learning).
Section 3 describes the clebran design in detail. Section 4 states the
three sub-hypotheses and the arm table, and lays out the match-compute
protocol and statistical convention. Section 5 reports the results
across H1, H2, H3, the recovered-primitive and curriculum channels, the
central-library control, the teachâ†’test probe, and the amortization
result. Section 6 discusses the reorientation, the divergence tax, the
role of measurement, and the scope. Section 7 lays out limitations.
Section 8 concludes.

