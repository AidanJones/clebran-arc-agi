# 6. Discussion

The headline is sharp. The discussion asks what the headline
*means* — for the clebran design, for the clebran hypothesis, and
for the broader question the experiment was supposed to be
about. We organise the discussion around four claims: the
*reorientation* (§6.1), the *divergence tax* (§6.2), the role of
*measurement* (§6.3), and the *scope* of the result (§6.4). A
short note on what the result implies for related literatures
(§6.5) closes.

## 6.1 The reorientation: not what you know, how you learned it

The clebran hypothesis was that communication, in the form of a
bandwidth-limited channel between divergent populations, would
improve the *skill* of a system at matched compute. The data
argue that the better purchase is *concentration* — one agent
that sees every task and reuses its own mined abstractions
strictly dominates several agents that see task slices and share.
Communication has a small, real, hard-to-detect effect that lives
in evals-to-solve rather than in solve count, and is more than
wiped out by the divergence tax.

The reorientation of the question is forced by two facts. The
first is the *transfer probe's corrected verdict* (§5.7.2):
relevant concept teaching is neutral on cost, irrelevant
teaching is harmful, and the per-student condition L + T < U
fails by ~56k. The thing that was supposed to be the central
mechanism of clebran (a curriculum that *teaches* what the
sender learned) does not, in this substrate, at matched compute,
make an individual agent cheaper to reach a target capability.

The second is the *endpoint*. The transfer probe's apparent 2×
speedup was real but lived in evals-to-solve, not in solve
count. Re-scoring on cost exposes that curriculum teaching's
benefit is invisible under solve count at fixed budget, and only
converts to solve count for tasks *near* the budget frontier —
of which the frontier subset has very few. Almost every prior
null in the project is therefore a null on a *solvable-frontier*
metric, not a null on *acquisition efficiency*. The instrument
for cost-to-solve was already in the logs; it was not the
metric.

Chollet's *On the Measure of Intelligence* warns that *unlimited
priors or unlimited training data let you "buy" skill*, masking a
system's actual generalisation power. The clebran design was
deliberately small, fully instrumented, and pre-neural so that
acquisition cost is metered, not purchased. The honest reading of
the headline is that even on this small substrate, the
multi-agent-with-channel framing is dominated by the central-
library framing. The next question is therefore the one
*On the Measure of Intelligence* is really about: how
*acquisition-efficient* is the system, and what design choices
move that number?

The reorientation is not only a proposal: the order experiment
(§5.7.3) is a first empirical purchase on it, and it comes back
*positive*. Holding the taught *content* fixed and varying only
the *order* of acquisition produces a significant capability
difference — teaching a curriculum foundations-*last* (reverse)
halves how much of it is acquired (23% vs 47%) and is no better
than not teaching at all, while foundations-first (forward) is
significantly better (paired p = 0.021). This is the cleanest
statement the substrate can make of "how you learned it": the
*same* knowledge, acquired in a dependency-violating order, is
worth significantly less. The effect is asymmetric — *don't teach
backwards* matters, but fine sequencing beyond "make the
fundamentals available" does not (forward ≈ shuffled, ns), because
an adaptive learner self-orders when all steps are on offer. So
the process axis is real but, in this substrate, shows up mainly
as a *failure mode to avoid* rather than a lever to optimise. That
it appears at all — as the project's only significant *process*
effect, against a wall of null *content* effects — is what marks
the axis as the one worth pursuing.

A capability audit (§6.4) frames the rest of the answer. The
process-level capabilities that an "acquisition-efficient" learner
would need — self-directed practice, active choice of what to
practise, retention without rigidity, reflection on *how*
something was learned — are the gaps. None of them is fully
present in the clebran design; together they describe the
substrate the reorientation would actually need. The order result
is a proof of concept that the *axis* is measurable here; the
capability audit is why measuring it *richly* needs a more capable
learner than pure GP, for which order this cheaply self-corrects.

## 6.2 The divergence tax

The single clearest mechanism in the data is the *divergence
tax*: splitting a fixed compute budget across N populations
yields fewer solves than spending the whole budget on one
population. B1 (3 isolated lineages, 1.45) is *worse* than B0
(single pop, 2.25). The mechanism is straightforward: each
lineage sees a third of the population generations, and the
small populations are more vulnerable to premature convergence
on local optima.

Communication pays back part of the tax. B6/B7 (≈ 1.8) are
better than B1 (1.45), but never reach B0. The
*received-primitive* signal is real (received-used ≈ 1.1–1.4,
NEO-style), and the recovered-primitive channel does help
isolated lineages solve more — but the gain is small (0.35
mean solves over B1 at 20 seeds) and the gap to B0 is
unchanged.

A central library *avoids* the tax and is *consistent with*
adding to single-population search. B5 (2.65) > B0 (2.25) is
directional (+0.40, 1.1 SE) — not formally significant — but
the qualitative claim survives: B5's library is more
compositional (topsim 0.33 vs 0.14–0.15) and more cross-task-
reused (0.15 vs 0.05). The reason is in the metrics: a single
agent sees every task, so its mined abstractions generalise
across tasks; a lineage that sees only the subset it solved
mines task-idiomatic abstractions. Divergence is precisely
what *degrades* the shared vocabulary — partial views yield
task-idiomatic abstractions, even when the partial views are
communicated and combined.

**Caveat on the B5 − B0 attribution.** B5's win over B0 is
*not* isolated to the library mechanism: B5 also has a
~4× larger library pool (built from a single population with
~2.65 mean solves, vs B6/B7's ~0.6–0.7 per lineage) and is run
on a single agent rather than three. The cleanest experimental
isolation of the library mechanism is a B0 + library arm
(single population, same compression miner, no multi-agent
framing), which is the obvious follow-up (§7). Until that
control is run, the paper's claim is that *centralisation
plus the library mechanism* dominates *divergence plus any
channel*, not that the library mechanism alone is what wins.

The negative result has a positive corollary: the design of the
*library* (the compression miner, the MDL pressure, the
Stitch-style library growing mechanism) is the part of clebran
worth keeping. The multi-agent framing, the channel, the
constraint regime, and the curriculum payload are the parts
worth re-thinking. B5 is the strongest "abstraction reuse
without divergence" result, and it is consistent with the
broader library-learning literature: a Stitch-style learner
on a hard synthesis problem is a strong baseline, and any
multi-agent framing has to *beat* it, not just match it.

## 6.3 The role of measurement

The clebran design's most important asset is its measurement
rig, and the headline is the rig's most important output.

The match-compute protocol audits each arm's recorded
candidate-evaluations to the per-arm budget and reports the
spread. Audited spreads are ≤ 0.27% across all reported
multi-arm runs; for the headline 20-seed frontier runs the
spread is 0.10%. The per-task RNG substream scheme
(`Random(f"{seed}:{task_id}")`) makes a single-task probe
predict full-run behaviour exactly, so a unit of debugging work
on a single task is a unit of debugging work on the run. The
deterministic interpreter and the `Program.from_json` round-trip
let every experiment be re-run from a frozen commit and
reproduce the same summaries.

The rig is what makes the null trustworthy. A cheap critique of
a null result in evolutionary program synthesis is "you just
didn't give the channel enough of a chance" — more seeds, more
budget, more bandwidth. The power check (§5.4) doubled the
seeds (8 → 20) and raised the budget (3M → 4M); the effect
*shrank* (B6 − B2 fell +0.50 → +0.20) and the standard error
narrowed (0.48 → 0.32), so the result is real-but-small rather
than a near-miss on significance. The dose-response (§5.3)
tested the constraint versus unconstrained range from `none`
to `uncon` and found the channel's *crowding mechanism is
absent* because AOS self-constrains a failing channel.

Two methodological lessons are worth stating explicitly. First,
*report cost-to-solve alongside solve count*. The transfer probe
is the dramatic example: a 2× speedup in evals-to-solve is
invisible under solve count at fixed budget if the budget
frontier has no tasks near it. Adding the cost endpoint is a
cheap fix; it does not undo the headline ranking (B5 still
wins), but it changes the discussion from "no effect" to "an
effect that is invisible to the standard endpoint."

Second, *the cold baseline is non-negotiable*. The transfer
probe's headline was wrong because it compared taught to a
control arm that was *mis-targeted* and therefore *harmed by
the channel*. Adding the cold arm revealed the confound and
corrected the verdict. The rule generalises: in any
"intervention helps" experiment, a *do-nothing* arm is the
only way to distinguish a real benefit from a *harm to a
mis-targeted control* masquerading as a benefit. The clebran
project's later arms (B5, B8/B9) explicitly include a cold
reference for exactly this reason.

**What it took to make the rig reliable.** The spec's Stage-1
gate — B0 solves all 10 near-atomic tasks on *every* seed —
forced a series of mechanisms, each fixing a diagnosed failure
mode. The full debugging trail is itself a record of what
pure-reward program evolution needs to be reliable. In the
order the fixes were discovered:

1. A union-type-flow bug that made `vmirror(I)` compositions
   unreachable: fixed by the union flow-through rule (§3.1).
2. A reward exploit where blank grids out-scored content: fixed
   by the foreground/background-balanced reward (§3.4).
3. Restart amnesia: fixed by the hall-of-fame restarts (§3.3).
4. A shared-RNG context sensitivity: fixed by the per-task RNG
   substreams (§3.3).
5. A round-robin scheduling starvation on near-miss tasks:
   fixed by the progress-weighted scheduler (§3.3).
6. A phase-1 fragment splice that poisoned 15% of offspring on
   needle tasks: fixed by the AOS self-suppression of fragment
   splice where library material is irrelevant (§3.3).
7. A literal-tuple → list `Program.from_json` bug introduced by
   the abstraction replay support: fixed by an explicit tuple
   coerce.

Each fix is identical across arms, so the H2/H3 comparison is
not biased by which fix landed first. The Stage-1 debugging
trail is the most direct evidence the rig is reliable: a
non-trivial set of mechanisms had to be added to make a
stochastic GP engine pass a deterministic gate, and every
mechanism is now part of every arm.

## 6.4 Scope: what the result is for, and what it is never for

The scope of the result is narrower than its surface. We state
both halves explicitly.

**Good for**

- *Amortising known competence* — making the 2nd…Nth agent
  acquire a capability ≈ 2× cheaper, when the curriculum is
  oracle-relevant and the budget frontier has marginal tasks.
  The clebran data do not show this on the current frontier,
  but the teach→test probe shows the *effect exists*; what it
  lacks is the right distribution and the right setup.
- *Distributing competence cheaply and substrate-agnostically* —
  curricula are compact and, unlike code, assume no shared
  representation. The clebran *curriculum* channel is the
  payload type most likely to generalise across learner
  architectures.
- *Bootstrapping a starting vocabulary* — so that new agents do
  not begin at zero. A small, recovered abstraction library
  installed at the start of a run is a clean experimental
  manipulation, and the clebran data suggest it would be
  cheaper than a curriculum.
- *Interpretability / audit* — a curriculum is a human-readable
  statement of what an agent knows. The clebran solver card
  already renders every evolved program's step-by-step
  execution trace; a curriculum extends that audit to the
  *inter*-agent layer.

**Never for**

- *Discovering abstractions nobody has found* — neither clebran
  mechanism, taken alone, can create information not present
  in the teacher or in the population. The library-mining
  component is the *only* mechanism that can discover
  abstractions; the channel and the curriculum are
  *transport* mechanisms. The headline falsification is
  precisely that, in this substrate, transport does not help
  even when discovery is shared.
- *Raising the ceiling on what is solvable at all* — the
  teach→test probe shows that a relevant curriculum makes a
  target cheaper, not more reachable. Speed, not capability.
- *Beating concentrated compute at discovery* — the B5 control
  is the single best arm. Splitting compute is a tax, and
  communication does not pay it back fully.
- *Tasks outside the curriculum's vocabulary coverage* — the
  amortization result shows that mis-targeted teaching causes
  *negative transfer* (irrelevant teaching is slower than no
  teaching). This is the most important scoping result
  available: a taught vocabulary biases later search, so an
  agent that internalised vocabulary A may search *worse* than
  a naive agent on a task needing disjoint vocabulary B.

**One-line scope.** *This is a compression-and-transport layer
for competence, not an engine of novelty.* A system that must
*discover* should look like B5 — one learner, maximum compute,
maximum task exposure. Teaching is what you bolt on afterwards
to make that expensive competence cheap to replicate.

A *capability audit* for what a process-aware learner would
need before "how you learned it" can be studied cleanly. The
audit is a "what would have to be true for the reorientation
to be operational?" list; the clebran substrate is missing
several of the rows.

| capability | status in clebran |
|---|---|
| core-knowledge priors (objectness, geometry, number, agentness) | **have** — encoded in Hodel's DSL |
| abstraction / compression (MDL, library learning) | **have** — compression miner, MDL pressure |
| communication & teaching | **have** — 4 payloads, prerequisite-ordered curricula |
| honest measurement (matched compute, baselines, seeds) | **have** — the repo's real asset |
| acquisition efficiency as the objective | instrument exists, **not the metric** |
| self-directed practice / dreaming | **missing** |
| active learning — *choosing* what to practise next | **missing** |
| continual learning without rigidity (plasticity) | **missing, and possibly already violated** |
| compositional generalisation to novel combinations | **missing** (no OOD split) |
| generalisation to genuinely unseen tasks | **missing** (eval split untouched) |
| meta-learning — adapting the *learning algorithm* itself | **missing** |
| reflection — credit assignment over *how* it learned | **missing**, and the least-explored anywhere |

The last row is the sharpest form of the thesis and is largely
open in the literature: systems that model *their own
acquisition process* and improve it. Everything above it is
prerequisite scaffolding.

## 6.5 What this means for related literatures

Three implications for the literatures the clebran design draws
on.

For *emergent communication*, the result is a clean refutation
of the naive information-bottleneck story in a typed symbolic
setting. Bandwidth-limited channels between divergent agents do
not, in this substrate, induce better compositionality at
matched compute. The reason is *adaptive operator selection*:
an adaptive learner self-constrains a failing channel, so the
information-bottleneck argument does not bite. The composi-
tionality question is *still open* for non-adaptive learners
and for the right evaluation setup; the clebran data close
only the *adaptive* variant. The result is in direct
conversation with the cultural-evolution theory of language
(Kirby, Tamariz, Smith & Cornish, 2015; Brighton & Kirby, 2006),
which argues that compression pressure *does* drive
compositional structure in human languages. The clebran H3
null is a clean empirical counter-example in a typed-symbolic
substrate: under adaptive selection, the constraint and the
unconstrained channel produce indistinguishable
vocabularies. The H3 null does not refute the cultural-
evolution account (which involves iterated cultural
transmission rather than a single channel between
populations) but it does argue that the simple
information-bottleneck story is not the whole story even
in a non-neural, deterministic setting. The closely-related
result by Bouchacourt & Baroni (2018) — that successful
emergent communication does not entail compositionality in
neural referential games — provides a non-clebran
counter-example to the same simple story, and the clebran
H3 null is a typed-symbolic re-instantiation of the same
gap.

For *library learning*, the result is consistent with the
central library mechanism being a strong baseline. B5 is the
single best arm and beats every multi-agent arm; the
vocabulary metrics support the ranking; the only formally-
tested contrast (B5 − B6 = +0.85, ~2.2 SE) is significant.
The clebran design's compression miner and MDL pressure are
not novel in themselves (both inherit from Stitch and
DreamCoder), but the match-compute comparison against
divergent multi-agent baselines is, and the win is
significant.

For *L2T/NEO*, the result is *consistent with* the transfer
metric framing. NEO's headline test (transfer, not
reconstruction) reappears in the teach→test probe: students
*learn* the taught concept (reconstruction) but do not deploy
it on novel tasks (no transfer). The clebran data add a sharp
*empirical* example to the L2T claim that reconstruction is
not the right endpoint. They also add a sharp *negative*
example: the *received-used* signal in the recovered-primitive
channel is real (lineages use received primitives, on average,
more than once per solve) but the *transfer* signal is not —
those used primitives do not improve solve count at matched
compute in the multi-agent setting, and a single agent that
mines its own primitives (B5) builds a strictly better library.

The combined picture is consistent and blunt. In this substrate,
on this frontier, at matched compute, *communicating learned
content — as code or as curricula — does not help, and
mis-targeted communication hurts*. The remaining live thread
is not *content* transfer but *process* (the reorientation):
whether the *way* a system learns can be improved and
measured on the acquisition-efficiency axis, where — unlike
in the multi-agent comparison — the instrument shows real
structure.
