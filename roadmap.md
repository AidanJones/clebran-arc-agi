# Roadmap — open work, organised by research strand

Open bets for the `clebran-arc-agi` rig, organised by research strand.
Each item has a **hypothesis**, **expected payoff** (what the world
looks like if positive / if null), and **build** (rough scaffold). The
ordering within each strand is by priority for that strand; the
ordering across strands is by which strand has the highest expected
payoff if positive.

**What's been done:** [STATUS.md](STATUS.md). **Narrative:**
[FINDINGS.md](FINDINGS.md). **Publishable claims:** [papers/](papers/README.md).

Status as of 2026-09-24. The discovery-bottleneck menu is **0-for-4 at 1M**;
the four closed pilots (#1 failure-mode dreaming, #2 heterogeneous
fitness, #3 task-subset specialization, #4 novelty search) are
frozen in `experiments/2026-08-31_*` and `experiments/2026-09-22_*`
and `experiments/2026-09-24_novelty_search/`, with the focused paper at
[`papers/04-discovery-bottleneck/`](papers/04-discovery-bottleneck/).

---

## Reading order

1. **[STATUS.md](STATUS.md)** — what's been done, structured by topic.
2. **This file** — what could be done next, organised by strand.
3. **[FINDINGS.md](FINDINGS.md)** — the narrative of how we got here.
4. **[papers/](papers/README.md)** — the publishable claims.

---

## The structural picture (as of 2026-09-24)

- **Transport is solved.** Paper 1: B5 is 7–10× more cost-efficient
  than every multi-agent arm on the cost axis (paper 1 §3.3); the
  recovered-primitive channel beats isolation but never reaches B0;
  dreaming (B5D) at 4M builds a library 2× larger / 13× more used /
  124× more cross-task-reused than B5, but the frontier remains tied.
  **The library mechanism is the asset; the channel/divergence
  framing is not.**
- **Discovery is open.** The discovery-bottleneck menu is **0-for-4 at
  1M × 5 seeds**. Four attacks from four different axes (practice
  pool, fitness signal, task pool, objective) all returned null. *No
  mechanism operating inside the current DSL/interpreter/fitness has
  expanded B5's reach at 1M, regardless of which axis you vary.* The
  remaining bets (#5 L1 proposer, #6 operator self-modification, #7
  L3 evoker) all attack the problem by adding a *new dimension* the
  lineage can search — the **structural-change bet**.
- **Generalisation is un-validated.** All headline numbers are
  training-split. The eval split and compositional-OOD split have
  never been evolved against.
- **Process / plugability is the loose end of the multi-agent
  premise.** Paper 2 showed content sharing is neutral/harmful at
  matched compute; the multi-agent premise has never been tested in
  the regime where it could pay off (amortisation across N students,
  cross-architecture transfer, curriculum-as-payload).

---

## Strand A — Discovery bottleneck (the structural-change bet)

The discovery-bottleneck menu has run #1–#4 (all null at 1M × 5
seeds). Three bets remain; all three *change the substrate*, not the
distribution of budget across the same DSL.

### A1. #5 Learned L1 as proposer (large, ~1 week)

**Question.** Can a learned programmatic `(state, action) → next_state`
predictor over the 16K-row trace dataset propose candidate programs
that B5's search wouldn't otherwise reach?

**Hypothesis.** Two programmatic L1s already exist (`LookupTableL1`,
25.5% exact, memoriser; `GPL1`, 18.7% exact, 52.7% shape) but neither
has been used as a *proposer*. The L1's generalisation — what it has
learned across all 400 reference solvers — is a different *kind* of
discovery from the lineage's own search: the L1 has seen 400
different strategies for combining primitives, while B5's search
starts from random and finds one strategy per task. A successful
proposer would *suggest* plausible program prefixes that B5's search
would take many more evals to find.

**Expected payoff if positive.** A *new* discovery mechanism with a
clear mechanism story — the L1's generalisation, not B5's local
search. The transport layer can carry the new candidates across
lineages as it already does for B5's library.

**Expected payoff if null.** A learned L1, even one with high
in-distribution accuracy, doesn't add what B5 already gets from its
own search. The trace-dataset direction is informative for what an
L1 *cannot* do on this substrate; the question becomes whether the
9f.4 L3 evoker (an L1 that *learns from its own failed predictions*)
can do what a fixed L1 cannot.

**Build (rough).** Train a programmatic L1 (lookup-table or GP),
plug it into the L2 planner's candidate set as an additional
proposer, compare B5 + L1-proposer vs B5 alone at 1M × 5 seeds.

**Pre-conditions met:** trace dataset, KnnL1 / LookupTableL1 /
GPL1 baselines, L2 planner, B5+planner arm at 20 seeds × 4M.

---

### A2. #6 Operator self-modification (large, ~2 weeks)

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

**Expected payoff if positive.** A *new* discovery mechanism on the
same rig that compounds with the existing transport layer.
Modifications that work on one lineage can be ported to others.

**Expected payoff if null.** Even meta-learning on the mutation
operator can't expand B5's reach. Combined with #1–#5, this would
close the discovery-bottleneck menu structurally, not just by failed
attack on this objective or that pool. The natural next move becomes
a genuinely new substrate (ARCTraj, ARC-AGI-3).

**Build (rough).** Add a lineage-level metadata channel (analog of
the per-arm payload modes) for operator modifications; re-implement
two or three primitive operators as parameterised and let the
lineage re-parameterise them by local learning-progress signal.

---

### A3. #7 L3 evoker (9f.4, large, ~2 weeks)

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

**Expected payoff if positive.** The world-modeling direction's
*capstone*: the substrate for studying ARC-AGI-3 (arXiv:2603.24621)
where *Modeling* is one of four required capabilities. Would also
upgrade B5+planner from a budget-conditional result (parity at
starved GP, null at 4M) to a positive integration at all budgets.

**Expected payoff if null.** The 4M null is structural, not a
small-sample effect; even a self-refining world model can't beat B5
at matched compute on this frontier. The world-modeling direction's
value stays in its *substrate* contribution (the trace dataset, the
planner-as-substrate), not in B5 expansion.

**Build (rough).** Pick a learned L1 (the GPL1 baseline is the
natural choice — best OOD coverage), wrap it in an L3 wrapper that
rolls out a candidate program, compares predicted to actual, and
updates the L1's argument table on mismatch; compare B5 + L3-evoker
vs B5 at 4M × 20 seeds.

**Pre-conditions met:** trace dataset, KnnL1 / LookupTableL1 /
GPL1 baselines, L2 planner, B5+planner arm at 20 seeds × 4M.

---

## Strand B — Generalisation (validating existing results on held-out data)

Independent of the discovery menu. Closes the "does this generalise?"
endpoint that Chollet argues is the *only* interesting one for ARC.

### B1. Stage-5 eval-split generalisation (medium, ~1 week)

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

**Expected payoff if positive.** Confirms the existing B5 result
generalises — the library mechanism is genuinely a generalisation
operator, not just an in-distribution compression operator.

**Expected payoff if negative.** B5's lead shrinks on the eval
split — scopes the claim to within-distribution synthesis. The most
useful scoping result available.

**Build (rough).** Build `data/eval_subset.json` (deterministic
recipe mirroring `subset.py`), run B0 / B5 / B5+planner at 4M × 5
seeds against it (smaller budget than the headline because the
eval split is 400 tasks × 5 seeds × 4 arms).

---

### B2. Compositional-OOD split (medium, ~1 week)

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

**Expected payoff if positive.** The library mechanism is
genuinely compositional — abstractions transfer across
compositions, not just across the same compositions seen in
training.

**Expected payoff if negative.** B5 underperforms a no-library
control on the OOD split — the library mechanism hurts
generalisation. Important scoping result.

**Build (rough).** Build `data/compositional_ood_subset.json`
(same primitive coverage as the frontier subset, distinct
combinations). Run B5 vs B0 at 4M × 5 seeds on it.

---

## Strand C — Process / plugability (the multi-agent premise's loose end)

Paper 2 showed content sharing is neutral/harmful at matched compute;
the multi-agent premise has never been tested in the regime where it
could pay off.

### C1. #8b Negative-transfer test on the B5D library (medium, ~3 days)

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

**Expected payoff if positive (negative transfer found).** The
dreaming is harmful, the library should not be exported. Mechanism
story: the library biases the search distribution away from
compositions of the same primitives, and disjoint vocabulary falls
outside the biased distribution.

**Expected payoff if negative (taught ≤ cold).** The dreaming
library is uniform across tasks; safe to export and roll out as the
B5 default.

**Build (rough).** Pick 5 tasks disjoint from the dreaming's
seed set; run cold B5 vs B5 seeded with the B5D library at 1M × 5
seeds; compare on frontier / test-exact.

---

### C2. #8a Amortization gap (medium, ~1 week)

**Question.** At what N does a shared curriculum become cheaper
per-student than per-student cold B0?

**Hypothesis.** Per-student taught cost is `L + T` (learn curriculum
+ solve target); per-student untaught cost is `U` (solve target
without curriculum); teacher discovery cost is `C` (paid once).
Amortisation wins when `C + N(L + T) < N·U`, i.e. `N > C / (U −
L − T)`. The probe found ~2× (`L + T` ≈ `U / 2`); crossover is
`N > 2C / U`.

**Expected payoff if positive.** Validates the "leave a curriculum"
architecture for *many-agent* settings. The clebran rig is
inherently multi-agent; if amortisation kicks in at small N, the
B8/B9 curriculum channel becomes worth revisiting with a real
multi-student harness.

**Expected payoff if null.** The ~2× probe was a per-student
artefact that doesn't amortise. The transport layer (B5's library
mechanism) is the only scalable knowledge-sharing mechanism on the
rig.

**Build (rough).** Three arms (cold / shared-curriculum /
per-student-unique-curriculum) at N = 1, 2, 4, 8; compare total
compute to reach a fixed competence bar.

---

### C3. #7b Curriculum as a fourth channel payload (medium, ~1 week)

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

**Expected payoff if positive.** A fourth channel payload with a
sharp mechanism story. If constrained-curriculum beats
unconstrained-curriculum, the H3 story (constraint-regime null)
re-opens on a new payload — a real surprise.

**Expected payoff if null.** The H3 null extends to the curriculum
payload too; the constraint story is robust across all four
payload types.

**Build (rough).** Build a curriculum-payload mode alongside
fragment/signal/abstraction; add B10 / B11 arms; run at matched
compute on the frontier subset.

---

## Strand D — Pluggability (cross-architecture transfer)

### D1. #9c Pluggable learners + cross-architecture curriculum transfer (large, ~2 weeks)

**Question.** Does a curriculum built for learner A speed up learner
B when learner A ≠ learner B?

**Hypothesis.** A curriculum is (input, output) grid pairs, with no
shared representation assumed. That makes a sharp test available
that no other payload allows: build a curriculum with learner A as
teacher, measure the acquisition-efficiency gain for learners B
and C. Gain transfers across architectures → curricula encode
*task structure*, and "how you learned it" is a property of the
material, not the student (strong). Gain is architecture-specific
→ teachers overfit their students (caution).

**Expected payoff if positive.** Curricula become a *reusable
artefact* — the sharpest way the clebran rig can say something
that generalises beyond its own learner.

**Build (rough).** Define a minimal `Learner` interface
(`solve(task, budget) -> program | None` + library/state). Back it
with ≥3 genuinely different learners: the existing typed GP, a
brute-force depth-bounded enumerator, a retrieval/nearest-neighbour
learner over seen solutions.

---

## Completed items (the discovery-bottleneck menu, 0-for-4 at 1M × 5 seeds)

| # | pilot | kind of attack | result | frozen data |
|---|---|---|---|---|
| 1 | failure-mode dreaming (B5D-NM-cons, B5D-NM-aggr) | change the *practice pool* (targeted) | **null**; B5D-NM-aggr regresses (−1.6, p = 0.007) | [`experiments/2026-08-31_b5d_nm_1m/`](experiments/2026-08-31_b5d_nm_1m/), [`experiments/2026-08-31_b5d_nm_aggressive_1m/`](experiments/2026-08-31_b5d_nm_aggressive_1m/) |
| 2 | heterogeneous fitness (B5-strongmdl, λ = 1.5) | change the *fitness signal* (parsimony pressure) | **null**; produces *shorter*, not *more compositional*, programs | [`experiments/2026-08-31_b5_heterogeneous_1m/`](experiments/2026-08-31_b5_heterogeneous_1m/) |
| 3 | task-subset specialization (B5-hard15, B5-random15) | change *what the lineage searches on* (subset) | **null**; hard subset out of reach at 1M, also at 4M | [`experiments/2026-09-22_task_subset_specialization/`](experiments/2026-09-22_task_subset_specialization/) |
| 4 | novelty search (B5N) | change the *objective* (behavioral diversity) | **null**; finds the same 6 easy tasks B5-1M also finds (100% overlap); novelty-as-objective degenerates | [`experiments/2026-09-24_novelty_search/`](experiments/2026-09-24_novelty_search/) |

Reading the four together, the cheapest is: **no mechanism operating
*inside* the current DSL/interpreter/fitness on the 30-task frontier
will expand B5's reach at 1M, regardless of which axis you vary.**
The remaining bets (A1–A3) all change the *substrate* — they are the
structural-change bet. Focused paper:
[`papers/04-discovery-bottleneck/`](papers/04-discovery-bottleneck/).

---

## Build order across strands

**Discovery-bottleneck strand** (the structural-change bet):
A1 (L1 proposer, ~1wk), A2 (operator self-mod, ~2wk), A3 (L3
evoker, ~2wk). If all three return null, the discovery menu is
*structurally* closed and the right next move is a new substrate.

**Generalisation strand** (independent of the menu, can run in
parallel): B1 (eval split, ~1wk), B2 (compositional OOD, ~1wk).
These validate the existing results on held-out data rather than
attempt new discoveries.

**Process / plugability strand** (the multi-agent premise's loose
end): C1 (B5D negative transfer, ~3d), C2 (amortization gap,
~1wk), C3 (curriculum payload, ~1wk), D1 (pluggable learners,
~2wk). These test the clebran's multi-agent premise in the regime
where it could actually pay off (amortisation across N students,
cross-architecture transfer, curriculum-as-payload).

**Cheapest first sweep:** C1 (3d) → A1 (1wk) → B1 (1wk) → C2 (1wk)
→ B2 (1wk) → C3 (1wk) → D1 (2wk) → A2 (2wk) → A3 (2wk).