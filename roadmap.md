# Roadmap — open work

Open bets for the `clebran-arc-agi` rig, in priority order. Each item
has a **hypothesis** (or expected payoff, or question to answer) so the
outcome of running it is sharp. **What's been done is in
[STATUS.md](STATUS.md); the narrative is in [FINDINGS.md](FINDINGS.md);
the publishable claims are in [papers/](papers/README.md).**

Status as of 2026-09-23. The 12-commit pre-history of the discovery-
bottleneck work (including #1, #2, #3 of the menu) is committed; no
branch is in flight.

---

## Reading order

1. **[STATUS.md](STATUS.md)** — what's been done, structured by topic.
2. **This file** — what could be done next, each with a hypothesis.
3. **[FINDINGS.md](FINDINGS.md)** — the narrative of how we got here.
4. **[papers/](papers/README.md)** — the publishable claims.

The structural picture:

- **Transport is solved.** Paper 1: B5 is 7–10× more cost-efficient than
  every multi-agent arm on the cost axis (paper 1 §3.3); Paper 1's
  recovered-primitive channel beats isolation but never reaches B0;
  dreaming (B5D) at 4M builds a library 2×/13×/124× richer than B5 but
  the frontier remains tied. The library mechanism is the asset; the
  channel/divergence framing is not.
- **Discovery is open.** The discovery-bottleneck menu (#1 failure-mode
  dreaming, #2 heterogeneous fitness, #3 task-subset specialization) is
  **0-for-3 at 1M**. No mechanism operating *inside* the current DSL /
  interpreter / fitness on the 30-task frontier has expanded B5's
  reach. The remaining bets all attack the problem by adding a *new
  dimension* the lineage can search — a new objective, a new primitive
  distribution, a new operator pool, a new world model — rather than
  redistributing budget across the same DSL.
- **The structural-change bet is now dominant on this rig.** Items 1–4
  below are the structural-change bets. Items 5–7 are the
  cheaper-but-deferred items (generalisation, process, pluggability).

---

## 1. #4 Novelty search arm (medium, ~3 days) — next discovery-bottleneck bet

**Question.** Does a B5 lineage that scores on **behavioral diversity**
(novel output grids) instead of task accuracy find anything new that the
accuracy-scoring lineage misses?

**Hypothesis.** Novelty search explores the *space of programs* rather
than the frontier of *solved tasks*. Its discoveries are different by
construction. If the existing accuracy-scoring lineage cannot reach a
task because the program space is locally flat, a diversity-scoring
lineage may traverse that flat region and stumble on a program that
*then* retro-fits an unsolved task.

**Payoff if positive.** A *new* discovery mechanism on the same rig.
The transport layer can then carry the new abstractions across lineages
as it already does for B5's library. This is the discovery side of the
clebran premise (the menu README: "novelty search, learned L1 as
proposer, operator self-modification, and the L3 evoker — all attack
the problem by adding a new dimension").

**If null.** The discovery-bottleneck menu becomes **0-for-4 at 1M**.
Strong signal that no mechanism inside the current DSL/interpreter/
fitness can expand B5's reach at 1M, regardless of objective.
**Structural-change bet becomes the only remaining strategy.**

**Build (rough).** Add a B5+novelty arm with `behavioral_novelty =
mean_Hamming_distance(predicted_output_grid, current_population_outputs)`
as the secondary tiebreak, then run 1M × 5 seeds and compare on
frontier solves / test-exact / library metrics.

---

## 2. #5 Learned L1 as proposer (large, ~1 week)

**Question.** Can a learned programmatic `(state, action) → next_state`
predictor over the 16K-row trace dataset propose candidate programs
that B5's search wouldn't otherwise reach?

**Hypothesis.** Two programmatic L1s already exist (`LookupTableL1`,
25.5% exact, memoriser; `GPL1`, 18.7% exact, 52.7% shape) but neither
has been used as a *proposer*. The L1's generalisation — what it has
learned across all 400 reference solvers — is a different *kind* of
discovery from the lineage's own search: the L1 has seen 400 different
strategies for combining primitives, while B5's search starts from
random and finds one strategy per task. A successful proposer would
*suggest* plausible program prefixes that B5's search would take
many more evals to find.

**Payoff if positive.** A *new* discovery mechanism with a clear
mechanism story — the L1's generalisation, not B5's local search.
The trace dataset is in place; the L2 planner is in place; the L1
baselines are in place. The gap is the *integration*: feed L1
proposals into B5's initial population (cf. the B5+planner arm).

**If null.** A learned L1, even one with high in-distribution
accuracy, doesn't add what B5 already gets from its own search. The
trace-dataset direction is informative for what an L1 *cannot* do on
this substrate; the question becomes whether the 9f.4 L3 evoker (an
L1 that *learns from its own failed predictions*) can do what a
fixed L1 cannot.

**Build (rough).** Train a programmatic L1 (lookup-table or GP),
plug it into the L2 planner's candidate set as an additional
proposer, compare B5 + L1-proposer vs B5 alone at 1M × 5 seeds.

---

## 3. #6 Operator self-modification (large, ~2 weeks)

**Question.** Can a B5 lineage modify its own mutation / crossover
operators based on what works, with modifications shareable across
lineages?

**Hypothesis.** Meta-learning on the mutation operator is "learning
to learn": the lineage observes which mutations produce high-fitness
offspring and biases the operator pool accordingly. The clebran
adaptive operator selection (AOS) does a primitive version of this
already — fragment injection self-suppresses / self-amplifies by
recent success. Operator self-modification extends AOS from "weight
operator k by recent success" to "rewrite operator k based on the
patterns in its recent successes". Modifications are shareable
across lineages the same way B5's library is shareable.

**Payoff if positive.** A *new* discovery mechanism on the same rig
that compounds with the existing transport layer. Modifications
that work on one lineage can be ported to others.

**If null.** Even meta-learning on the mutation operator can't
expand B5's reach. Combined with #1–#4, this would close the
discovery-bottleneck menu structurally, not just by failed attack
on this objective or that pool.

**Build (rough).** Add a lineage-level metadata channel (analog of
the per-arm payload modes) for operator modifications; re-implement
two or three primitive operators as parameterised and let the
lineage re-parameterise them by local learning-progress signal.

---

## 4. #7 L3 evoker (9f.4) — large, ~2 weeks

**Question.** Can a learned world model that refines itself on
failed predictions (the L3 step of the Agentic World Modeling
literature, arXiv:2604.22748) improve over the perfect-L1 L2
planner?

**Hypothesis.** The B5+planner arm (paper 3) is *budget-conditional*:
useful at 500K-1M (ties B5 at 10/30, 1 unique task), null at 4M
(20 seeds, B5 12.45 ± 1.15 vs B5+planner 12.35 ± 0.99, mean delta
−0.10, t = 0.26). The 4M null is read as "B5 has enough budget
to do the work without the planner's head-start". An L3 evoker that
*practices inside its own simulator* and refines the model when
reality contradicts it could escape this — the dreaming loop over a
learned world model is what the clebran substrate is missing.

**Pre-conditions now met** (build order 1–3 of roadmap §9f all done):
trace dataset, KnnL1 / LookupTableL1 / GPL1 baselines, L2 planner,
B5+planner arm at 20 seeds × 4M.

**Payoff if positive.** The world-modeling direction's *capstone*:
the substrate for studying ARC-AGI-3 (arXiv:2603.24621) where
*Modeling* is one of four required capabilities.

**If null.** The 4M null is structural, not a small-sample effect;
even a self-refining world model can't beat B5 at matched compute on
this frontier. The world-modeling direction's value stays in its
*substrate* contribution (the trace dataset, the planner-as-substrate),
not in B5 expansion.

**Build (rough).** Pick a learned L1 (the GPL1 baseline is the
natural choice — best OOD coverage), wrap it in an L3 wrapper that
rolls out a candidate program, compares predicted to actual, and
updates the L1's argument table on mismatch; compare B5 + L3-evoker
vs B5 at 4M × 20 seeds.

---

## 5. Stage-5 generalisation runs (roadmap §6, deferred)

**Question.** Do the clebran results — B5 is the cheapest and most
cost-efficient arm at 4M on the 30-task frontier subset — hold on
the **eval split** (the 400 tasks reserved by the spec for the
"genuinely unseen tasks" question)?

**Hypothesis.** All headline numbers are training-split. The eval
split has never been evolved against; the rig has the right hooks
(`CLEBRAN_SUBSET=eval_split` once the subset is built). The
expectation is partial transfer: B5's library mechanism is a
compression operator, not a generalisation operator, so it transfers
less to OOD than to within-distribution tasks.

**Payoff.** A clean answer to "does this generalise?" — the
endpoint Chollet argues is the *only* interesting one for ARC. If
B5's lead shrinks on the eval split, that scopes the claim to
within-distribution synthesis. If it holds, the library mechanism
generalises, which is a stronger result.

**Build (rough).** Build `data/eval_subset.json` (deterministic
recipe mirroring `subset.py`), run B0 / B5 / B5+planner at 4M × 5
seeds against it (smaller budget than the headline because the
eval split is 400 tasks × 5 seeds × 4 arms).

---

## 6. #8b Negative-transfer test on the B5D library (medium, ~3 days)

**Question.** Does B5 with the B5D-library at 4M (17 abstractions,
12.4 cross-task reuse, topsim 0.22) underperform cold B5 on tasks
that need *disjoint* vocabulary? Is the dreaming harmful?

**Hypothesis.** Dreaming builds a richer library than B5 reaches,
but the dreaming's library is dominated by compositions of the
primitives B5 already had. An agent that internalises that library
may search worse than a naive agent on tasks needing disjoint
vocabulary — negative transfer / plasticity loss. The §8b
diagnostic generalises; this experiment is the concrete test on
the B5D 4M artifact.

**Payoff.** Either confirms negative transfer (the most important
scoping result available — the dreaming is harmful, the library
should not be exported), or shows transfer is uniform (the dreaming
is a free win, the library export can be rolled out everywhere).

**If positive.** Mechanism for "dreaming is harmful" — the
library biases the search distribution away from compositions of
the same primitives, and disjoint vocabulary falls outside the
biased distribution.

**If negative (taught ≤ cold).** The dreaming library is uniform
across tasks; safe to export and roll out as the B5 default.

**Build (rough).** Pick 5 tasks disjoint from the dreaming's
seed set; run cold B5 vs B5 seeded with the B5D library at 1M × 5
seeds; compare on frontier / test-exact.

---

## 7. #8a Amortization gap (medium, ~1 week)

**Question.** At what N does a shared curriculum become cheaper
per-student than per-student cold B0?

**Hypothesis.** Per-student taught cost is `L + T` (learn curriculum
+ solve target); per-student untaught cost is `U` (solve target
without curriculum); teacher discovery cost is `C` (paid once).
Amortisation wins when `C + N(L + T) < N·U`, i.e. `N > C / (U −
L − T)`. The probe found ~2× (`L + T` ≈ `U / 2`); crossover is
`N > 2C / U`.

**Payoff if positive.** Validates the "leave a curriculum"
architecture for *many-agent* settings. The clebran rig is
inherently multi-agent; if amortisation kicks in at small N, the
B8/B9 curriculum channel becomes worth revisiting with a real
multi-student harness.

**If null.** The ~2× probe was a per-student artefact that doesn't
amortise. The transport layer (B5's library mechanism) is the only
scalable knowledge-sharing mechanism on the rig.

**Build (rough).** Three arms (cold / shared-curriculum / per-student-
unique-curriculum) at N = 1, 2, 4, 8; compare total compute to
reach a fixed competence bar.

---

## 8. #7b Curriculum as a fourth channel payload (medium, ~1 week)

**Question.** Does sharing *tasks* (curriculum payload) cross the
channel better than sharing *code* (abstraction payload, B6/B7)?

**Hypothesis.** Sharing code assumes a shared substrate and can
transplant a subroutine the receiver can't contextualise. Sharing
*tasks* is substrate-agnostic and lets the receiver integrate the
concept in its own representation — plausibly more robust across
divergent lineages (the whole H1 premise). The constrained
curriculum — few, well-chosen tasks (bounded length = the
bandwidth knob) — is also the most information-bottleneck-pure
payload: a teacher is forced to compress what it knows into a
handful of maximally-instructive tasks.

**Payoff if positive.** A fourth channel payload with a sharp
mechanism story. If constrained-curriculum beats unconstrained-
curriculum, the H3 story (constraint-regime null) re-opens on a
new payload — a real surprise.

**If null.** The H3 null extends to the curriculum payload too;
the constraint story is robust across all four payload types.

**Build (rough).** Build a curriculum-payload mode alongside
fragment/signal/abstraction; add B10 / B11 arms; run at matched
compute on the frontier subset.

---

## 9. #9c Pluggable learners + cross-architecture curriculum transfer (large, ~2 weeks)

**Question.** Does a curriculum built for learner A speed up learner B
when learner A ≠ learner B?

**Hypothesis.** A curriculum is (input, output) grid pairs, with no
shared representation assumed. That makes a sharp test available
that no other payload allows: build a curriculum with learner A as
teacher, measure the acquisition-efficiency gain for learners B
and C. Gain transfers across architectures → curricula encode
*task structure*, and "how you learned it" is a property of the
material, not the student (strong). Gain is architecture-specific
→ teachers overfit their students (caution).

**Payoff if positive.** Curricula become a *reusable artefact* —
the sharpest way the clebran rig can say something that
generalises beyond its own learner.

**Build (rough).** Define a minimal `Learner` interface (`solve(task,
budget) -> program | None` + library/state). Back it with ≥3
genuinely different learners: the existing typed GP, a brute-force
depth-bounded enumerator, a retrieval/nearest-neighbour learner
over seen solutions.

---

## 10. Eval-split compositional-OOD split (medium, ~1 week)

**Question.** Do the clebran results generalise across a
*compositional* OOD split (held-out compositions of known
primitives)?

**Hypothesis.** All headline numbers are training-split. Topsim
and cross-task reuse are the only compositional-generalisation
proxies in the rig. A held-out compositional split — same
primitives, different combinations — would close the
compositional-generalisation capability gap (STATUS §I) and
provide a clean test of whether the library mechanism
*recombines*.

**Payoff.** A measurable compositional-OOD endpoint. If B5
underperforms a no-library control on the OOD split, the library
mechanism hurts generalisation — important negative. If it
holds, the library mechanism is genuinely compositional.

**Build (rough).** Build `data/compositional_ood_subset.json`
(same primitive coverage as the frontier subset, distinct
combinations). Run B5 vs B0 at 4M × 5 seeds on it.

---

## Build order across the open items

**Cheap & immediate** (~weeks): items **1** (novelty search, ~3d),
**6** (negative-transfer test, ~3d), **5** (Stage-5 eval-split
generalisation, ~1wk), **10** (compositional-OOD split, ~1wk).

**Medium-horizon** (~weeks): items **8** (curriculum payload, ~1wk),
**7** (amortization gap, ~1wk).

**Large-horizon** (~weeks-to-months): items **2** (learned L1 as
proposer, ~1wk), **9** (pluggable learners, ~2wk), **3** (operator
self-modification, ~2wk), **4** (L3 evoker, ~2wk).

The discovery-bottleneck menu (#4 novelty search → #5 learned L1
proposer → #6 operator self-modification → #7 L3 evoker) is the
**structural-change bet**: each item tests whether adding a *new
dimension* (a new objective, a new primitive distribution, a new
operator pool, a new world model) can expand B5's reach. If all
four return null, the menu is closed and the project's natural
next move is to bring in a genuinely new substrate (ARCTraj,
ARC-AGI-3) — not to keep attacking the same DSL with new
mechanisms.

The generalisation track (items 5, 10) is independent of the
discovery menu and can be done in parallel — they validate the
existing results on held-out data rather than attempt new
discoveries. The process track (items 7, 8, 9) tests the
clebran's multi-agent premise in the regime where it could
actually pay off (amortisation across N students).