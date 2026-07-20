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

## 2. Chase the B3 degradation (cheapest publishable finding)

Unconstrained sharing was the worst arm (9.80) at the highest reuse (17%) —
preliminary evidence that bandwidth-unlimited gossip is actively harmful.

- Sweep the constraint knobs: K (fragment size) × M (messages/epoch) grid,
  e.g. K ∈ {2, 4, 8, ∞}, M ∈ {1, 3, 10, ∞} — is there a dose-response curve
  from CH-CONSTRAINED to CH-UNCONSTRAINED? A monotone degradation with
  bandwidth would make H3 significant and mechanistic.
- Instrument *where* the harm lands: are B3's lost solves tasks where
  fragment-op children crowded out mutation (AOS credit logs already record
  this per population)?

## 3. Recovered-primitive channel (§11's scientifically important variant)

The current channel communicates over Hodel's given primitives, which caps the
emergent-language claim. Let lineages abstract their *own* subroutines:

- Compress each lineage's solutions into named subroutines (Stitch, or a
  simple duplicated-slice miner over the linear IR — extraction machinery
  already exists in `genome.extract_fragment`).
- Channel payload becomes the lineage's abstracted subroutines; receivers
  add them as callable named units, not raw splices.
- Then the H3 metrics that matter: topographic similarity (EGG-style),
  primitive-recovery rate, compositional-OOD splits per L2T.

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
- Evaluation throughput is ~2.5–3k evals/s/process; if 10M-eval runs are
  needed, profile the interpreter (grid ops dominate) or shard tasks across
  processes.
- Fitness cache keyed on (program, task) would cut re-evaluation of elites
  and duplicated children — but it changes the meaning of "candidate-
  evaluations", so if added it must be identical across arms and the budget
  metric must switch to *unique* evaluations.

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
