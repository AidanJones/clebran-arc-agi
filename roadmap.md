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
