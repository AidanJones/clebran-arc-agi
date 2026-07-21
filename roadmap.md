# Roadmap

State as of 2026-07-20: Stages 0–4 complete
([experiments/2026-07-20_stage4_b0-b4_matched_compute](experiments/2026-07-20_stage4_b0-b4_matched_compute/)).
H1 supported, H2 null, H3 directional. The null is structural: at 1M evals the
solvable frontier is shallow enough that systematic phase-1 search closes it
without communication, so the channel has nothing to move. Everything below is
ordered by how directly it attacks that.

## 1. Build a contested frontier, rerun B0–B4 (highest priority; IN PROGRESS)

H2 can only show signal on tasks that isolated lineages *fail* but
fragment-equipped lineages might reach.

**Done:**
- **Sharper measure** — evolution-phase solve accounting (`Population.solved_phase`,
  `solved_evolution` in every summary; `report.py` compares on both all-solves and
  evolution-only). This is where any channel effect must live.
- **Frontier subset** — `clebran.subset.build_frontier` → `data/frontier_subset.json`;
  point runs at it with `CLEBRAN_SUBSET=frontier_subset`.

**What the 2M-eval B0 reachability probe (seeds 1-2) showed:**
- Phase tagging validated: the one D3 solve was a short accidental depth-2
  solution, correctly tagged phase1; every genuine evolution solve was D2.
- Evolution reaches **only D2** (depth 3-5): 3 distinct D2 tasks solved across
  2 seeds at 390k–1.17M evals. **Zero** genuine D3 evolution solves — D3
  (depth 6-10) is beyond reach and would just add a floor of zeros. Composition
  reweighted to **25 D2 / 5 D3** accordingly.
- Counts are low (1-2 evolution solves per seed per 2M) → the treatment signal,
  if any, is small; budget and seed count must be sized for it.

**Pilot (B1 vs B2, 3M, seeds 1-2 —
[experiments/2026-07-20_frontier_pilot](experiments/2026-07-20_frontier_pilot/README.md)):**
hint of B2 > B1 on evolution solves (mean 2.0 vs 1.5; B2 solved a task B1
never reached), and — the hard result — channel **reuse jumped from 0.06 to
0.67-1.00**. The mechanism H2 depends on is now active; the frontier rebuild
worked. Held here by decision on 2026-07-20; n=2 is too noisy to call H2.

**Remaining (compute-heavy — sized, ready to launch):**
- **Budget:** ~3M total (per-lineage ~1M, where evolution solves appear).
- **Seeds:** ≥8 for the headline B2-vs-B1 pair given counts of 1-3/seed.
- Full B0–B4 × 8 seeds ≈ several hours; compare on **evolution-phase solves only**.

## 2. Chase the B3 degradation — DONE on stage-1: flat, mechanism absent

Ran the K×M bandwidth ladder (`clebran.baselines.dose_response`:
none→K2M1→K4M3→K8M10→uncon, 1M × 3 seeds) with fragment-crowding
instrumentation ([experiments/2026-07-20_b3_dose_response](experiments/2026-07-20_b3_dose_response/README.md)).

**Finding: no dose-response, and the crowding mechanism does not occur.**
Solve rate is flat across the ladder (10.0–10.7, all overlapping); `frag-share`
is pinned at 0.03 *regardless of bandwidth* — identical even with no channel.
Reuse rises with bandwidth (0→0.17) but fragment *share* does not, so
unconstrained sharing can't crowd out mutation. The reason: **adaptive
operator selection self-regulates** — it weights the fragment op by its ~2%
success (vs ~36% for mutation) and floors it near 3% share no matter how much
material arrives. An adaptive learner is robust to unconstrained sharing
because it self-constrains; the constraint stops mattering. This complicates
H3 rather than confirming it, and softens the Stage-4 "B3 is worst arm" line
(which was never significant anyway: B2−B3 = +0.60, se 0.32).

**Still open:** H3 is untestable on stage-1 (reuse tops out ~17%; channel
barely engages). Rerun the same ladder on the **frontier** (item 1), where
reuse ran 0.67–1.00 and AOS *up-weights* fragments — there a curated vs
flooded channel could finally differ. Read `op_mix` down the ladder.

## 3. Recovered-primitive channel (§11's scientifically important variant; IN PROGRESS)

The current channel communicates over Hodel's given primitives, which caps the
emergent-language claim. Let lineages abstract their *own* subroutines and
communicate those instead.

**Foundation done** (`clebran/dsl/abstraction.py`, `tests/test_abstraction.py`):
- `Abstraction` — a body parameterised by its external inputs (the task grid I
  and out-of-slice registers become positional `("param", k)` parameters).
  Invoked as a *single* statement `("abstr", name)`, so it costs one unit of
  program length (the MDL/compression lever) but inlines at run time
  (`interpreter._run_body`). Typing threads an `abstractions` table so
  `("abstr", …)` types like a primitive; primitive-only programs unaffected.
- `mine_abstractions` — a duplicated-slice miner over the linear IR: recurring
  dependency-closed subroutines (same primitives/wiring/constants, inputs
  abstracted) across a set of programs. On Hodel's 400 solvers it recovers
  meaningful units unsupervised — `ofcolor(I, leastcolor(I))`,
  `argmax(objects(I,…), size)`, `remove(ZERO, palette(I))`, … Stitch could
  later replace it for optimal compression.
- Interpreter refactor verified behaviour-preserving (399/400 solver
  reproduction unchanged); all tests pass.

**Search integration done** (genome/fitness/lineage; 3 more tests, 11 total):
- `GenomeOps` takes a per-lineage abstraction table (shared dict); random
  generation / `_random_statement` / `_mut_grow` emit `("abstr", …)` heads with
  typed args, and `repair`/`_mut_arg`/typing resolve abstraction signatures via
  `_head_params`. Off by default (empty table) so ordinary search is unchanged
  (verified: B0 pipeline intact).
- `fitness.Evaluator` and every `Lineage` execution path thread the shared
  table; an abstraction call is one statement, so `len(prog)` already gives it
  MDL cost 1 — a test shows an installed subroutine collapses the depth-2 task
  6d0aefbc to a length-1 solving program.
- `Lineage.install_abstraction` / `mine_own_abstractions` (dedup by structure,
  shared table → instantly usable). Self-mining finds nothing on shallow
  stage-1 solutions (they don't share substructure) — expected; the vocabulary
  emerges on the frontier.

**Channel payload mode `"abstraction"` done** (channel/lineage/orchestrator/arms;
1 more test, 12 total):
- `Message` carries an `Abstraction`; `ChConstrained` gates it by body size (K)
  and count (M) via a shared `_msg_size`. Lineages track abstraction provenance
  (`abstraction_meta`: received/score/uses); `_publish` mines home-grown
  subroutines (`min_count=1` — offer every subroutine that helped, the
  constraint filters) and publishes them; `_receive` installs received ones as
  named units. `reuse_rate` counts solutions using a *received* abstraction;
  summary logs per-lineage `vocabulary` (total/received).
- Arms **B6** (constrained) and **B7** (unconstrained) abstraction payload —
  the H3 test on a *discovered* vocabulary. (B5 reserved for Stitch.)
- Smoke run: abstractions mine, cross the channel, and install as received
  (vocab received=2/lineage); reuse 0 on shallow stage-1 (received vocabulary
  not *needed* there), as expected — engages on the frontier.

**Metrics done** (`clebran/metrics/recovery.py`, `tests/test_recovery.py`;
6 more tests, 18 total):
- **Topographic similarity** — Spearman rho (scipy-free) between structural
  (message) and behavioural (meaning, over a probe battery) pairwise distances
  across arity-1 Grid abstractions. Validated: 0.53 on the 20 subroutines mined
  from Hodel's solvers — a real compositional signal.
- **Primitive-recovery stats** — `abstraction_stats`: used-rate,
  reused-across-tasks (genuine reusable primitives), received-used (the
  NEO-style "used a primitive it was handed, never derived"), mean body
  size/arity, topsim. Logged per lineage in every summary; `report.py` prints a
  recovered-vocabulary table for B6/B7.

**Replay done:** `Abstraction.to_dict/from_dict`; solve events log the used
abstractions' definitions; `run_trace` takes the table; the solver card renders
a "recovered abstractions used" block and replays abstr solutions. (Also fixed a
latent `Program.from_json` bug that turned literal tuples into lists.)

**Frontier run set up + validated, not launched** (`clebran.baselines.frontier_sweep`,
`scripts/frontier_recovered_sweep.sh`): runs B0/B1/B2/B6/B7 on the frontier at
matched compute, `--analyze` prints the evolution-phase comparisons (B6>B1
recovered-primitive transfer helps; B6 vs B2 recovered vs given; B6>B7 the H3
constraint on a discovered vocabulary) plus the recovery table. Validated
end-to-end at tiny scale.

    SEEDS="1 2 3 4 5 6 7 8" BUDGET=3000000 sh scripts/frontier_recovered_sweep.sh

**Only remaining: launch it** — 5 arms × ≥8 seeds × 3M ≈ several hours; the
item-3 payoff measurement, held for the same compute decision as item 1.

## 4. Metrics debt (needed for any writeup)

- **Transfer–reconstruction gap** (§9): log per solve whether the program
  solves all demo pairs vs the test pair — one seed already showed a
  test-exact miss; track it systematically.
- **Topographic similarity** over channel messages (currently unimplemented).
- **B5 (Stitch central library)**: the strongest "abstraction reuse without
  multi-agent divergence" control; only worth running once a contested
  frontier exists.

## 5. Engine improvements (only as needed by #1)

- Phase-1 currently covers depth ≤ 2; a bounded depth-3 skeleton pass
  (pipeline-fns only, sweep-gated) may be worth its cost on a D2-heavy
  subset — measure, don't assume.
- **Throughput ~8.3k evals/s/process (done, ~3× up from ~2.8k).** The
  interpreter's per-cell grid-validation scan (79.5M isinstance calls / 32s in
  profiling) was replaced with an O(rows+width) structural + first-row check;
  reproduction unchanged (399/400). A length-guarded fitness cache (only deep
  programs, len ≥ 4, where re-running is dearer than the key) skips the ~27%
  duplicate evaluations transparently — every call still counts as a
  candidate-evaluation, so budgets/compute-matching are byte-identical and
  search is deterministic-identical (verified). Further wins if needed: shard
  tasks across processes; the DSL primitives (upscale/replace) now dominate.

## 6. Toward Stage 5 (later)

- Full 400-task training split + eval-split generalization runs (never
  evolve against eval).
- Kaggle-envelope feasibility: wall-clock per task at competition budgets.
- Only then: a learned proposal component (tiny mutation-bias policy), with
  the pure-symbolic system kept as the reproducible baseline.

## 7. Curriculum generation — the inverse-teaching direction (longer horizon)

So far the arrow runs task → program → discovered abstractions (a DSL). This
item runs it **backwards**: given a DSL we have already discovered — a set of
reusable abstractions, ideally the *recovered* subroutines from item 3, not
just Hodel's given primitives — **generate an ordered sequence of tasks that
would lead a fresh learner to build that same DSL.** The analogy is a teacher
handing a student problems in a deliberate order so the student develops, in
the right sequence, the concepts they'll need for problems they haven't seen
yet. It's the symbolic-program-synthesis cousin of automatic **curriculum
learning** in RL (teacher-student curricula, unsupervised environment design,
open-ended generation à la POET) — the teacher proposes tasks at the frontier
of the student's current ability so competence compounds.

Why this fits clebran specifically:
- **The forward generator already exists in principle.** A task that *requires*
  abstraction A is cheap to synthesize: sample programs that use A, run them on
  random input grids through our deterministic interpreter, and keep the
  resulting (input → output) demonstration pairs. "Make a task needing A" is
  just running the DSL forward. (Hodel's `re-arc` generators are prior art for
  the grid-synthesis half.)
- **We already ship a crude, *static* curriculum.** The §4.1 depth-graded
  subset (D1 → D2 → D3) is a hand-built ordering by pipeline depth. This item
  generalizes that from a fixed hand-ordering to an ordering *derived from a
  target DSL*: order abstractions by their prerequisite structure (which
  subroutines compose out of which), then emit tasks bottom-up so each new
  abstraction is learnable from ones already acquired.
- **It closes an open-ended loop.** Divergent lineages discover abstractions
  (H1); the constrained channel shares them (H2/H3); a curriculum generator
  could then synthesize task distributions that make those abstractions *easier
  to rediscover and compose* — feeding new populations that reach deeper than
  the original run could. Teacher and student co-evolve.

Concrete first experiments:
- **Inversion test.** Take a DSL discovered by a lineage. Generate a curriculum
  from it. Train a fresh B0 lineage on the curriculum (in order) and check
  whether it rediscovers the target abstractions *faster / at lower compute*
  than the same lineage on a random task order or on the flat depth-graded
  subset. Faster rediscovery = the curriculum encodes real prerequisite
  structure.
- **DSL-quality probe.** A *good* DSL should admit a *short, learnable*
  curriculum; an entangled one should not. Curriculum length / learnability
  becomes an intrinsic quality metric for a discovered DSL — complementary to
  the MDL and topographic-similarity measures already planned (items 3–4).
- **Teacher as a policy.** Later, make the teacher adaptive: pick the next task
  to maximize the student's learning progress (measured as reduction in evals
  to solve held-out tasks needing the target abstractions), the standard
  learning-progress signal from automatic-curriculum RL.

Depends on item 3 (recovered-primitive channel) for the interesting version —
generating a curriculum for Hodel's *given* primitives is possible but far less
meaningful than for a vocabulary the system discovered itself. Also relates to
the L2T anchor (§2.4): a curriculum is a controlled distribution over
phenomena, and NEO's compositional-/length-OOD splits are essentially a
hand-designed curriculum for probing primitive recovery.

### 7a. Two halves: curriculum *generators* and curriculum *learners*

The item above conflates two capabilities that should be built and evaluated
separately, then paired:

- **Generators (teachers).** Given a target (a DSL / a set of held-out tasks),
  produce an ordered task sequence. Candidate mechanisms to implement and
  compare on our IR: (i) **prerequisite-ordered forward generation** — sample
  programs over the target vocabulary by increasing depth, render demo pairs
  through the interpreter, order by which abstractions compose out of which
  (cheap, deterministic, no learner in the loop); (ii) **regret/learning-
  progress-driven** — pick the next task to maximize the student's improvement,
  the automatic-curriculum-learning objective; (iii) **adversarial/co-evolved** —
  a teacher population evolves tasks that the current student population fails
  but a slightly-better one solves (regret), directly in our evolutionary
  substrate.
- **Learners (students).** Given a task sequence, actually *use the order* — our
  B0 lineage already learns from tasks, but ignores ordering (progress-weighted
  scheduling aside). A curriculum-aware learner carries its private library/
  vocabulary forward from earlier tasks to later ones, so a curriculum that puts
  prerequisites first pays off. This is mostly a scheduling + library-persistence
  change to `lineage.py`, and it is the thing that makes a *good* ordering
  measurably beat a shuffled one.

Evaluate the pair by the **inversion test** (7's first experiment) and by
*teacher–learner transfer*: a curriculum built for learner L should also speed
up a *different* learner L′ (different seed/pool) — otherwise the teacher has
overfit to one student.

### 7b. Communication *through exported curricula* (a fourth channel payload)

The sharp new idea: make the channel payload a **curriculum**, not a fragment,
signal, or abstraction. A lineage that has discovered vocabulary V exports a
*small synthetic task sequence* — generated by running its DSL forward (7's
generator) — chosen so that a receiver who trains on it will be induced to
**rediscover V for itself**. Knowledge crosses the channel as *problems to
solve*, not as code. This slots straight into the existing machinery as
`payload="curriculum"` alongside fragment/signal/abstraction, with the same
B-arm comparisons: does curriculum-transfer help (H2), and does a *constrained*
curriculum — few, well-chosen tasks (bounded length = the bandwidth knob) —
teach better than dumping many (H3)? It is the most information-bottleneck-
pure payload: a teacher is *forced* to compress what it knows into a handful of
maximally-instructive tasks.

Why it is worth trying over sharing abstractions directly: sharing code assumes
a shared substrate and can transplant a subroutine the receiver can't
contextualize; sharing *tasks* is substrate-agnostic and lets the receiver
integrate the concept in its own representation — plausibly more robust across
divergent lineages (the whole H1 premise). It also unifies the project's two
themes: communication *is* teaching, and the constrained channel *is* a
teaching-set-size budget.

### 7c. Prior art (this sits on an active literature — cite, don't reinvent)

- **Machine teaching** — the inverse of learning: find the optimal (often
  smallest) teaching set for a target concept. Directly relevant, incl. a
  compositional-simplicity-prior variant that mirrors our MDL/DSL stance:
  Zhu's machine-teaching program; *Iterative Machine Teaching* (Liu et al.,
  ICML 2017, https://arxiv.org/abs/1705.10470); *Optimal Teaching Curricula
  with Compositional Simplicity Priors* (Garcia-Piqueras & Hernández-Orallo,
  ECML-PKDD 2021).
- **Learning to teach** — a teacher *model* learns which data/tasks to give a
  student: Fan et al., ICLR 2018 (https://openreview.net/pdf?id=HJewuJWCZ);
  *Teacher–Student Curriculum Learning* (Matiisen et al., 2019).
- **Dataset distillation** — the ML analogue of "export a tiny curriculum that
  teaches": compress a corpus into a few synthetic examples that train a model
  to near-full performance (Wang et al., 2018,
  https://openreview.net/pdf?id=Sy4lojC9tm). Our exported curriculum is its
  symbolic, task-level cousin.
- **Asymmetric self-play** — the closest existing "communicate through tasks":
  Alice proposes goals/tasks, Bob solves them, yielding an automatic curriculum
  (Sukhbaatar et al., 2018, https://tesatory.github.io/selfplay_umass.pdf;
  OpenAI robotic-manipulation goal discovery). Our twist: *many divergent*
  teachers, exporting *task sequences* over a *constrained* channel.
- **Unsupervised environment design / evolving curricula** — teachers generate
  environments at the regret frontier: PAIRED (Dennis et al., NeurIPS 2020,
  minimax regret), POET (Wang et al.), and — closest to our evolutionary
  substrate — ACCEL / *Evolving Curricula with Regret-Based Environment Design*
  (Parker-Holder et al., 2022, https://arxiv.org/abs/2203.01302).
- **Automatic curriculum learning survey** for the landscape: Portelas et al.,
  2020; Narvekar et al., *Curriculum Learning for RL* (JMLR 2020).

**Novelty to preserve:** none of the above combines (a) *multiple divergent*
teachers, (b) exporting *curricula* (not gradients, code, or single goals) as
the (c) *bandwidth-constrained* communication channel between (d) *program-
synthesising* learners. That intersection is what clebran would add.

Build order when this item is picked up: 7a-generators (prerequisite-ordered
forward generation) → 7a-learners (library-persistent, order-aware scheduling)
→ inversion test → 7b `payload="curriculum"` arm → the H2/H3 comparison on
curriculum transfer.
