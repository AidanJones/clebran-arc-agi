# 2. Related work

The clebran design sits at the intersection of four literatures: typed
DSL program synthesis for ARC (§2.1), library learning and the
DreamCoder/Stitch line (§2.2), emergent communication between
divergent agents (§2.3), and the Learning-to-Theorize / Neural
Theorizer (L2T/NEO) framework for primitive recovery under partial
observability (§2.4). A short note on multi-agent program synthesis
(§2.5) and on curriculum / machine-teaching (§2.6) closes the
section. A new subsection (§2.7) scopes the world-modeling
literature and the substrate for the §9f direction.

## 2.1 DSL program synthesis for ARC

The standard reference for typed grid DSLs on ARC is Hodel's `arc-dsl`,
which provides roughly 160 typed primitives covering object extraction,
geometric transformations, recolouring, and composition. We vendor
`dsl.py`, `constants.py`, `arc_types.py`, and (importantly) `solvers.py`
— one hand-written solver per training task — into our interpreter.
`solvers.py` plays two roles in the project: as a *depth oracle* (the
statement count of a solver grades task difficulty and is used to
construct depth-graded subsets) and as a *correctness gate* (every
reference solver must reproduce its task's grids through *our*
interpreter before the task can enter the evolvable subset). 399 of
400 reference solvers reproduce through our interpreter; the one
failure (`e40b9e2f`) is order-sensitive upstream and is excluded from
the subset.

Two recent LLM-based systems are worth contrasting with the clebran
approach because they make the *same* "small system, metered
acquisition cost" bet. *ArcMemo* (Ho et al., 2025) proposes an
LLM-backed reusable-concept memory for ARC, and is the closest
*conceptual* cousin to the central-library (B5) arm — a learner that
*accumulates* named concepts over a run. The differences are
instructive: ArcMemo's concepts are stored in natural language with
LLM-mediated retrieval, ours are recovered executable subroutines in a
typed IR with deterministic execution and zero neural components; the
clebran design is *intentionally* pre-neural so that acquisition cost
is metered, not purchased. The "what to do with a concept" loop is
the same in both systems; the "how to find a concept" loop is
different (LLM-mediated retrieval in ArcMemo, typed GP search in
clebran). The Kaggle ARC Prize 2024–2025 winning entries use ensemble
neural approaches that sit orthogonally to the question this paper
asks.

The second comparison is the *test-time training* line. Akyürek et
al. (2024) is the 2024 ARC Prize second-place paper award; the
system performs a small, task-specific network update per task
(semi-private 47.5%, public 53% at 8B parameters, 61.9% when
ensembled with program synthesis). The TTT line is a direct
neural-ARC competitor for the clebran thesis that *test-time
compute* (in clebran's case, evolutionary search) is the right
place to spend a small system's budget. The antecedent of the
TTT-for-ARC line is Sun et al. (2020), which introduced the
test-time training framework in a more general setting. The
clebran paper and the TTT line make complementary bets about
*where* on the curve between pretraining and inference-time
compute a small system should sit; we position clebran as the
*typed-symbolic* end of that curve.

## 2.2 Library learning, compression mining, and MDL

The DreamCoder architecture (Ellis et al., 2020) introduced the
*wake–sleep* loop for library learning: a neural-guided program
synthesiser writes programs from tasks in the wake phase, and a
compression step identifies recurring subroutines, adds them to a
shared library, and rewrites older programs to use the new vocabulary
in the sleep phase. Stitch (Bowers et al., 2023) replaces the
expensive compression step with a fast *anti-unification* miner that
finds recurring subroutines across programs by over-generalising
constants, ranking candidates by the compression ratio they achieve.
The clebran library miner is a Stitch-style compression miner, and
the "central library" (B5) arm is a *Stitch-style* learner (no
neural recognition model; periodic anti-unification mining; no
wake-sleep back-coupling) — pure symbolic search, with library
mining run periodically on the population's best programs. We
emphasise the *Stitch-style* framing in §5.5 because B5 shares the
library mechanism with the multi-agent arms but is *not* a
DreamCoder-style wake-sleep learner, and reviewers from the
DreamCoder community will distinguish the two.

The MDL pressure on program length is a continuation of a longer
lineage: Solomonoff's theory of inductive inference, the
Kolmogorov-complexity tradition (Li & Vitányi, *An Introduction to
Kolmogorov Complexity and Its Applications*), and the
compression-as-cognition line (Schmidhuber, 1997). In the library-
learning setting specifically, the MDL pressure was introduced by
DreamCoder (Ellis et al., 2020) and inherited by L2T/NEO (Baek et
al., 2026). We use the same functional form — `λ_MDL^(-length)` —
as the parsimony term in the fitness function (§3.4), with
`λ_MDL = 1.05` (the value used in every reported run; see §4.7).

The Bayesian-program-learning antecedent of DreamCoder/Stitch is
Tenenbaum (1999) and Goodman et al. (2008), and the broader
program-learning lineage runs through RobustFill and the
sequence-to-sequence program-synthesis work. L2T/NEO and clebran
are both instantiations of this line, but on opposite sides of the
neural/symbolic boundary: NEO is probabilistic, operates over latent
programs decoded back to observations through a state-grounding
constraint, and learns a single codebook by gradient descent on a
variational MDL objective; clebran is deterministic, operates over
symbolic programs in a typed IR, and *mines* its codebook by
anti-unification over best programs. The shared scientific question
is whether the recovered vocabulary transfers; their answers
differ accordingly.

A note on terminology: in the clebran project, "abstraction" refers
specifically to a Stitch-mined subroutine that has been parameterised
by its external inputs, invoked as a single program statement, and
added to a lineage's private or shared vocabulary. "Fragment" refers
to a multi-statement slice of a successful program (the §3.5 channel
payload that operates over Hodel's given primitives). "Library" is the
shared set of abstractions an arm maintains.

**CompressARC (Liao & Gu, 2025)** is the direct competitor on the
"intelligence as compression" axis. CompressARC is a 76K-parameter
neural system with no pretraining and no ARC training-set access
that solves 20% of the public evaluation set by minimising a
variational description length of the target puzzle. The system
took 3rd place at the ARC Prize 2025. Both clebran and CompressARC
deliberately sit on the small-system end of the pretraining-vs-
inference-time trade-off; both inherit from the MDL / Solomonoff
line; the substrate decisions (symbolic program evolution vs
neural variational inference) are different. The clebran paper
should be read as testing the *symbolic-evolution* instantiation
of the compression hypothesis; CompressARC is the *neural-
inference* instantiation. A direct empirical comparison would
require running clebran's central library on the same evaluation
split CompressARC targets, which the clebran paper has not done
(see §7).

## 2.3 Emergent communication between divergent agents

The classical referential-game literature (Lazaridou & Baroni, 2020)
asks whether a discrete, bandwidth-limited channel between two agents
— one producing, one interpreting — induces a compositional protocol.
The standard compositionality metric is *topographic similarity*
(Brighton & Kirby, 2006; Lazaridou, Hermann, Tuyls & Baroni, 2018):
the Spearman rank correlation between message-space and meaning-space
pairwise distances. The clebran project adopts both the protocol (a
discrete, bounded channel between populations under independent
reward) and the metric (Spearman over arity-1 Grid abstractions). A
common finding in the emergent-communication literature is that
bandwidth limits the expressivity of the emergent protocol; an
*adaptive* learner, however, can also *self-constrain* a too-wide
channel by down-weighting operators that rely on the channel. That
adaptive mechanism is what makes our H3 (constraint versus
unconstrained) test null across all four payload types, and it is the
reason the clebran design is at odds with the information-bottleneck
story in its naive form.

Two specific results in the emergent-communication literature are
directly relevant to the clebran findings. **Bouchacourt & Baroni
(2018)** show that successful emergent communication does not entail
compositionality: agents establish successful communication by
inducing visual representations that align with each other but not
with the conceptual properties of the input. This is the same null
the clebran paper reports in H3 — bandwidth-limited channels between
divergent agents do not, in this substrate, induce better
compositionality at matched compute — and the clebran data are a
*typed-symbolic re-instantiation* of the Bouchacourt & Baroni
finding. **Chaabouni et al. (2020)** show that compositional
structure (as measured by various proxies) is decoupled from
generalisation, and **Li & Bowling (2019)** show that topographic
similarity does not perfectly predict task transfer. The clebran H3
null lives in this empirical envelope: successful communication
neither entails compositionality (Bouchacourt & Baroni) nor
guarantees generalisation (Chaabouni et al., Li & Bowling), and
adding a bandwidth constraint does not move either needle in the
clebran substrate.

The clebran H3 null is also in direct conversation with the
*information-bottleneck / cultural-evolution theory of language*
(Kirby, Tamariz, Smith & Cornish, 2015; Brighton & Kirby, 2006),
which argues that compression pressure *does* drive compositional
structure in human languages through iterated cultural transmission.
The clebran data are a clean empirical counter-example in a
typed-symbolic, non-iterated, adaptive-learner substrate: under
adaptive operator selection, the constraint and the unconstrained
channel produce indistinguishable vocabularies. The H3 null does
*not* refute the cultural-evolution account (which involves
iterated transmission rather than a single channel between
populations) but it does argue that the simple
information-bottleneck story is not the whole story even in a
non-neural, deterministic setting.

Our setting differs from the referential-game setting in two
important ways. First, the agents are *populations* under
pure-reward evolution, not neural policies with end-to-end
differentiation; the channel is the only inter-agent pathway. Second,
the channel operates over a *typed* symbolic substrate (Hodel's
primitives or recovered abstractions) rather than over learned
discrete embeddings. The first difference is what makes the project
*measurable* on a small budget; the second is what makes the
channel's "content" inspectable, a property the neural setting does
not have. The clebran EGG-style tooling (Kharitonov, Chaabouni,
Bouchacourt & Baroni, 2019) provides the topographic-similarity and
discrete-channel primitives the project uses; clebran does not use
the EGG framework directly, but borrows the metric and the
discrete-channel framing.

## 2.4 Learning-to-Theorize and the transfer metric

The closest published framework to clebran's actual scientific goal is
*Learning to Theorize* (L2T) and its neural implementation NEO (Baek,
Lee, Baek, Lee & Ahn, 2026), an ICML 2026 oral. L2T formalises the
problem of, given only before→after observation pairs `(x, y)`,
recovering the *hidden program* `τ = (z_{i_1}, …, z_{i_K})` — a
composition of learned, reusable primitive operations — such that
`y = f_τ(x)`. The decisive test in L2T is not reconstruction but
*transfer*: infer `τ̂` from a support pair, then execute `τ̂` on a
fresh input `x′` and check whether the correct `y′` is produced. The
ARC demonstration→test protocol is exactly that transfer test, cast as
theory induction.

The clebran design inherits four ideas from the L2T framework, but
*three of them are really DreamCoder re-use, not L2T inventions*.
We are explicit about this rather than over-attributing, because the
intellectual lineage matters: a system can claim to be an
instantiation of L2T only if its specific contribution to L2T's
hypothesis is identifiable.

- *Theory is an executable program over reusable primitives* — the
  DreamCoder framing (Ellis et al., 2020; 2021). L2T/NEO inherits
  this explicitly: NEO is presented as a "Language of Thought"
  framework, in the same lineage as DreamCoder's wake-sleep Bayesian
  program induction. clebran adopts the same stance.
- *Adaptive MDL-penalised program length* — also DreamCoder's.
  DreamCoder 2020/2021 has the same `λ^len(p)` factor. clebran's
  fitness function uses the same functional form (with `λ_MDL =
  1.05`; see §4.7).
- *Primitive recovery under partial observability* — the L2T
  compositional-OOD claim. NEO recovers primitive-level codes even
  when some primitives never appear in isolation in training. This
  is *loosely* connected to H1/H3 (a system under compositional and
  MDL pressure can disentangle reusable units it never saw alone),
  but clebran does not run the L2T compositional-OOD split (it is
  listed as a limitation in §7). The connection is a "shared
  philosophical root" rather than a "borrowed idea."
- *Transfer, not reconstruction, is the real metric* — *this* is
  the L2T contribution. NEO's specific demonstration is the
  canonical reference, and the clebran teach→test probe (§5.7.1)
  operationalises it at the level of whole concepts. This is the
  L2T idea clebran is genuinely building on, and the clebran
  re-discovery of the transfer/reconstruction gap is a real
  corroboration of the L2T framing.

The deltas that keep clebran novel against L2T are explicit, and the
*substrate delta* is the most important: NEO is *probabilistic* and
uses test-time sampling (the paper gives NEO a compute budget at
inference and samples hundreds of candidate theories); NEO operates
over *latent* programs, decoded back to observations through a
state-grounding constraint; NEO's "single codebook" is *learned* by
gradient descent on a variational MDL objective. clebran is
*deterministic*, operates over *symbolic* programs in a typed IR,
and *mines* its codebook by anti-unification over best programs.
These are three distinct substrate decisions (probabilistic vs
deterministic, latent vs symbolic, learned vs mined) that the
substrate delta distributes across. The clean framing is: *NEO and
clebran are both instantiations of DreamCoder-style library
learning, but on opposite sides of the neural/symbolic boundary;
their shared scientific question is whether the recovered vocabulary
transfers, and their answers differ accordingly.*

On top of the substrate delta, clebran adds four operational axes
that NEO does not have: (a) *multiple deliberately divergent*
populations; (b) *pure evolutionary reward* (no differentiable
executor, no program supervision); (c) *communication* of recovered
abstractions across lineages; (d) a *constrained channel* (the
bandwidth-constrained blackboard). The clebran design asks, in L2T
terms, whether several theorizers that each theorise the world
differently can teach each other their primitives, and whether a
bandwidth-limited channel makes those taught primitives *better*.
The answer the data give is *no* — but the answer is precise: in
this substrate, at matched compute, on this frontier, the taught
primitives are no better than those a single agent would mine on
its own.

**Note on the iterated / single-round axis.** NEO is implicitly
iterated (gradients are taken across many samples and many training
episodes). clebran's reported experiments run *one* round of
communication; the iterated form (curriculum₁ → agents₂ →
curriculum₂ → …) is unaddressed (see §7). The single-round /
iterated distinction is a fifth axis in the substrate delta; we flag
it as a *limitation* of the clebran result, not as part of the
L2T delta.

## 2.5 Multi-agent program synthesis

Multi-agent formulations of program synthesis appear in the
population-based GP literature (Poli et al., 2008), in cooperative
co-evolution (Potter & Jong, 1994), and in island models with
migration (Skolicki & Jong, 2005). clebran's specific framing —
*constrained communication* of *recovered subroutines* between
*deliberately diverged* populations — is a novel combination but
inherits the island-model concern that migration policy matters as
much as migration rate. Our adaptive operator selection (AOS, §3.4)
is the clebran answer to that concern: the channel cannot crowd out
mutation, because AOS down-weights the fragment operator when it is
failing, regardless of how much material the channel supplies. The
*empirical* result is that AOS is so effective at this self-regulation
that the H3 constraint test is null across all four payload types
(§5.3, §5.4, §5.5).

The modern multi-learner / population-based literature has three
threads that are in the clebran intellectual neighbourhood.
*Population-Based Training* (Jaderberg et al., 2017) is the closest
neural-network-native analogue: a population of learners shares
hyperparameters and discovers good schedules through mutation and
exploitation. PBT is in the lineage of island models but operates on
neural-network hyperparameters rather than program fragments, and
its "channel" is a shared parameter store, not a constrained
blackboard. *Quality-Diversity* algorithms (Lehman & Stanley, 2011;
Cully, 2019) maintain a *diverse* set of solutions rather than
converging to the best; clebran's H1 (lineages diverge) is
exactly the QD premise applied to a population-of-populations
setting, and the clebran use of `Random(f"{seed}:{task_id}")` to
guarantee seed-level divergence is the simplest possible QD-style
*novelty* mechanism. *Federated learning* (McMahan et al., 2017) is
the modern distributed-learning analogue of "many learners share a
parameter server"; not a perfect fit (clebran's channel is a
blackboard, not parameter averaging), but the structural parallel is
close enough to deserve a sentence. None of these threads combine
(a) *deliberate divergence* across populations, (b) *constrained*
symbolic communication, and (c) *typed* symbolic payloads — the
clebran combination.

## 2.6 Curriculum learning and machine teaching

The *curriculum channel* arm of clebran (§3.5.4) is a deliberate
synthesis of two threads. *Machine teaching* (Zhu, 2015; Liu et al.,
2017; Garcia-Piqueras & Hernández-Orallo, 2021) inverts the learning
problem: given a target concept, find the smallest teaching set that
induces it. The closest compositional variant — *Optimal Teaching
Curricula with Compositional Simplicity Priors* (Garcia-Piqueras &
Hernández-Orallo, 2021) — uses an MDL-style prior to pick the
teaching set, which is the same prior that clebran's fitness function
uses to pick among programs. *Automatic curriculum learning* in RL
(Portelas et al., 2020; Narvekar et al., 2020) — teacher–student
curricula, learning-progress-driven task selection, regret-based
environment design (PAIRED, ACCEL; Dennis et al., 2020; Parker-Holder
et al., 2022) — provides the curriculum-as-policy framing. POET
(Wang et al., 2019) and the asymmetric self-play line (Sukhbaatar
et al., 2018) are the closest existing examples of *communication
through tasks*: Alice proposes goals, Bob solves them, and competence
compounds. clebran's specific addition is the *bandwidth-constrained
multi-teacher* setting: many divergent teachers, each exporting a
*task sequence* (not a single goal, not a gradient, not code) over a
constrained channel to many divergent students. We are not aware of
prior work combining all four axes (multi-agent divergence,
curriculum-as-payload, constrained channel, program-synthesis
substrate).

The teach→test result of §5.7.1 — students learn taught concepts
(70–78% of synthetic teaching tasks solved) but do not transfer
them to novel tasks needing them — sits inside a larger literature
on negative transfer and continual learning. The findings are
consistent with the catastrophic-forgetting and plasticity-loss
observations in continual learning (Kirkpatrick et al., 2017;
Schwarz et al., 2021): a learned vocabulary can bias later search
in ways that hurt tasks the vocabulary does not cover. The
negative-transfer phenomenon is the broader topic; the
*multitask-learning* line (Caruana, 1997) and the
*task-affinity* line (Standley et al., 2020) provide the formal
machinery. The clebran 8b / "irrelevant teaching hurts" result is
a negative-transfer result in this lineage, and the
*compositional-generalisation* benchmarks — SCAN (Lake & Baroni,
2018), COGS (Kim & Linzen, 2020), gSCAN (Ruis et al., 2020) —
provide the controlled-distribution probe the clebran paper has
not run (see §7).

## 2.7 World models and learned simulators for ARC

The world-modeling literature (Ha & Schmidhuber, 2018; Hafner et al.,
2019, 2020, 2023; Ye et al., 2021) frames an agent as a system
that *predicts* the result of its actions in an internal simulator
and *plans* in that simulator. The *Agentic World Modeling* taxonomy
(Ye et al., 2026, arXiv:2604.22748) organises the field into three
levels: an **L1 Predictor** — a learned `(state, action) → next_state`
function; an **L2 Simulator** — multi-step rollout for planning; an
**L3 Evolver** — revise the model on failed predictions
(self-supervised improvement, the "dreaming" loop). The clebran
interpreter is a perfect L1 for the clebran DSL: `interpreter.run_trace`
returns every register as a grid, and each register-pair with the
k-th statement is a labelled transition. The clebran substrate
therefore sits naturally on the L1/L2/L3 axis, with the B5+planner
arm (§3.7) as the L2 integration test.

Two external resources are the most directly usable substrate for
this direction on ARC. **ARCTraj** (Kim, Choi, Lee & Kim, KDD 2026
Datasets and Benchmarks, arXiv:2511.11079) provides ~10,000 human
step-by-step object-level trajectories across all 400 ARC-AGI-1
training tasks, collected via the O2ARC web interface, MDP-
formatted for PPO / DreamerV3 / GFlowNets / Decision Transformers /
diffusion-augmented RL. The O2ARC actions are object-level (move,
rotate, flip, colour) and need a mapping layer onto Hodel's
primitives; many will not map, which is fine — they are a separate
modality that gives a cross-modality signal. **ARC-AGI-3**
(arXiv:2603.24621) is the new interactive turn-based benchmark.
Four required capabilities: *Exploration, Modeling, Goal-Setting,
Planning and Execution*. The *Modeling* capability is exactly
"the ability to build a world model that represents how the
environment works and can predict the results of unseen actions."
ARC-AGI-3 is the natural long-term testbed for whatever clebran
builds next; the typed-IR substrate and library-mining mechanism
transfer directly.

The closest *learned* baselines on ARC are **CompressARC** (Liao &
Gu, 2025, arXiv:2512.06104, 3rd place ARC Prize 2025, 76K params,
no pretraining) and **Akyürek et al.'s Test-Time Training for
ARC** (arXiv:2411.07279, 2nd place ARC Prize 2024). Both are
purely neural; both treat ARC as a compression problem; neither
exposes the symbolic state representation the clebran planner
relies on. **Grid-JEPA** (arXiv, 2025) is a recent JEPA + RSSM
+ TTT architecture targeted at ARC-AGI-3; the *learned-L1-replaces-
interpreter* design pattern is the same one the clebran §9f build
order targets, but in a fully-neural substrate. The clebran
*contribution* on this axis is the deterministic, perfect-L1
upper bound: a learned L1 can be measured against the interpreter's
predictions, and a planner using the interpreter as L1 establishes
the ceiling any learned L1 has to recover.

The *methodological* pattern is shared with **CATER** (Girdhar &
Ramanan, ICLR 2020) — synthetic 3D scenes with full per-frame state
and atomic / compositional action annotations. The "procedurally
generate, log every intermediate state" workflow is what Hodel's
*re-arc* repository enables for ARC at scale: per-task generators
that produce unlimited synthetic (input, target) pairs, and
`run_trace` to log the full state trajectory. The §9f build-order
item 4 (re-arc-generated trace candidates) is the CATER pattern
applied to ARC.
