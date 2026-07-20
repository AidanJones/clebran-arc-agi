# Roadmap

State as of 2026-07-20: Stages 0–4 complete
([experiments/2026-07-20_stage4_b0-b4_matched_compute](experiments/2026-07-20_stage4_b0-b4_matched_compute/)).
H1 supported, H2 null, H3 directional. The null is structural: at 1M evals the
solvable frontier is shallow enough that systematic phase-1 search closes it
without communication, so the channel has nothing to move. Everything below is
ordered by how directly it attacks that.

## 1. Build a contested frontier, rerun B0–B4 (highest priority)

H2 can only show signal on tasks that isolated lineages *fail* but
fragment-equipped lineages might reach.

- **Frontier subset:** re-run the §4.1 recipe weighted toward D2/D3 (e.g.
  5×D1 / 15×D2 / 10×D3, or drop D1 entirely for the treatment comparison —
  D1 is now deterministic and just burns budget).
- **Budget scaling curve:** B0 at 1M / 3M / 10M evals on the new subset to
  find the knee where GP is still gaining tasks — run the arm comparison at
  that budget, not below it.
- **Sharper measure:** count solves *outside* phase-1 (evolution-phase solves
  only) per arm, so the deterministic layer doesn't dilute the comparison.
- Keep ≥5 seeds; consider 10 for the headline pair (B2 vs B1) since the
  effect size at 5 seeds was ≈0 ± 0.35.

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
