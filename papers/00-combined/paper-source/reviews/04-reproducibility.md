# Reproducibility and Engineering Review

*Reviewer pass on the clebran paper draft (`paper/00`–`08`, README, FINDINGS, roadmap, `experiments/2026-07-*`). The paper is unusually well-instrumented for a falsification: matched compute, audited budgets, a deterministic interpreter, per-task RNG substreams, and a frozen experiment-folder convention. Most of the gaps below are *paper-text* gaps, not implementation gaps — a competent researcher who cloned the repo and read the code would reproduce the numbers, but someone reading the paper alone would not. The headline concern is a small but real **factual error** (λ_MDL) and several **omitted hyperparameters** that the paper should report in §4 for the result to be auditable from the paper alone.*

---

## Top 3 reproducibility gaps

### 1. The `λ_MDL` value in the paper does not match the code

**Location:** `paper/03-design.md:167–168` and `paper/04-methods.md` (referenced in §3.4) and `paper/06-discussion.md` (referenced throughout).

**Diagnosis.** §3.4 states the fitness tiebreak uses `final(p) = reward(p) * (λ_MDL ** -len(p))` "with `λ_MDL = 1.1`." Every actual implementation site uses `1.05`:

- `clebran/fitness.py:38` — `def __init__(self, lam_mdl: float = 1.05, ...)`
- `clebran/lineage.py:103` — `lam_mdl: float = 1.05` (default)
- `clebran/orchestrator.py:32` — `lam_mdl: float = 1.05` (default)

No code path uses 1.1, and no code branch reads 1.1 from config. Every fitness evaluation across all reported runs — Stage-1, frontier 8-seed, frontier 20-seed, curriculum — has been evaluated with λ_MDL = 1.05.

**Why it matters.** λ_MDL is the most sensitive *fitness-shape* hyperparameter in the system: it directly multiplies the tiebreak that decides among equal solvers. A 0.05 change is not cosmetic — it materially changes the program's MDL-driven convergence on the frontier, where the tiebreak decides many solves. A reader who tries to "reproduce from the paper" with λ_MDL = 1.1 will not match the logged solve counts. This is a factual error, not a typo or stylistic choice, and the paper should not go to publication with it uncorrected.

**Fix.** Either (a) update `03-design.md:167–168` and every other occurrence (the abstract and §1 are silent on the value, so the only fix site is §3.4) to `λ_MDL = 1.05`; or (b) if there is an intent to use 1.1 in a follow-up run, say so explicitly. The paper should also grep-verify that no other prose cites 1.1, 1.05, or related MDL values that could confuse the reader. Add the actual value to the new hyperparameter table suggested in §4 (see below).

### 2. The channel K and M for the frontier runs are never stated in the paper

**Location:** `paper/04-methods.md:61–64` (the arm table footnote about multi-lineage arms), `paper/05-results.md:115–135` (the B6/B7 results section).

**Diagnosis.** §4.2's arm table (lines 48–59) describes the ten arms in terms of payload and constraint regime but never states the constraint values. The footnote on line 61–64 only mentions N=3 and 20% dropout. The K×M dose-response (§5.3, Stage-1) uses K2M1, K4M3, K8M10, uncon — but those are the dose-response *sweep* values, not the values used in the B6/B7/B8/B9 frontier runs. A reader cannot tell from the paper alone what K and M were used for the headline B6 vs B5 comparison.

The default values in code are `K=4` (max fragment size in statements) and `M=3` (max messages per lineage per epoch) in `clebran/channel.py:86–87` (`ChConstrained.max_fragment_size = 4`, `ChConstrained.max_messages = 3`). The Stage-4 README (`experiments/2026-07-20_stage4_b0-b4_matched_compute/README.md:17`) states these explicitly for Stage-4, but the frontier B6/B7/B8/B9 experiment READMEs do not restate them. The reader has to chain the paper → Stage-4 README → source code to recover K and M.

**Why it matters.** K and M are the *treatment* of the H3 test. The paper's claim that the constraint "doesn't matter" is precisely the claim that "B6 (K=4, M=3) ≈ B7 (M=∞)" — the B6 arm's K and M are part of the test, and they must be in the paper. The user-supplied question explicitly says "K=8 M=5" is the user's guess; the actual code default is K=4, M=3. A reader cannot tell from the paper that the user's guess is wrong.

**Fix.** Add to §4.2's table footnote (line 61–64) a line that explicitly states: "The K×M defaults for CH-CONSTRAINED in all frontier runs are K=4 statements, M=3 messages per lineage per epoch (`ChConstrained.max_fragment_size=4`, `max_messages=3` in `clebran/channel.py`); the unconstrained variants set M=∞." The same sentence should appear in §3.5 and in §5.4, §5.5, and §5.6 the first time a constrained arm is named.

### 3. The compression-miner schedule for B5 is not stated

**Location:** `paper/03-design.md:251–254` (the B5 description), `paper/05-results.md:240–248` (B5 is "a single population that periodically mines its own solutions…").

**Diagnosis.** Both §3.6 and §5.6 describe B5 as a "single population that periodically runs the miner over its hall of fame." The word "periodically" is doing all the work — the paper never states the period, the trigger, or the maximum number of abstractions installed per call. In code:

- `clebran/baselines/b0.py:32` — `mine_every: int = 5` (default period in epochs)
- `clebran/baselines/b0.py:84` — `if self_mine and epoch % mine_every == 0: lin.mine_own_abstractions()` (the trigger)
- `clebran/lineage.py:672–678` — `mine_own_abstractions(max_new=8, min_size=2, max_size=4)` (the call, with defaults that control how many abstractions can be added and what size range is allowed)
- `clebran/dsl/abstraction.py:273–278` — `mine_compressing(min_occurrences=2)` (the underlying min-duplicate threshold)

None of `mine_every=5`, `max_new=8`, `min_size=2`, `max_size=4`, `min_occurrences=2` appear in the paper. B5 is the *headline arm* — its schedule is part of the result.

**Why it matters.** A reader who wants to vary the miner schedule (which is the obvious sensitivity check on B5) has no way to know what the paper used. The 5-epoch period is also unusual; many library-learning systems mine on convergence or after a fixed number of solves. The paper should justify the choice, or at least report it.

**Fix.** Add to §3.6 or §5.6: "B5 calls `mine_own_abstractions(max_new=8, min_size=2, max_size=4)` every `mine_every=5` epochs (`clebran/baselines/b0.py`); the underlying `mine_compressing` requires `min_occurrences=2` (a subroutine must appear in at least two of the lineage's best programs to be considered)." This adds three lines of text and removes a real reproducibility gap.

---

## Hyperparameter audit

Below is a list of every hyperparameter the paper should report, where it is used, and what value the code uses. Sources: `clebran/fitness.py`, `clebran/lineage.py`, `clebran/channel.py`, `clebran/orchestrator.py`, `clebran/dsl/abstraction.py`, `clebran/baselines/b0.py`, `clebran/baselines/dose_response.py`.

| # | Hyperparameter | Where it lives in code | Value(s) in code | Where it should appear in paper |
|---|---|---|---|---|
| 1 | `λ_MDL` (MDL parsimony factor) | `fitness.py:38`, `lineage.py:103`, `orchestrator.py:32` | **1.05** (paper says **1.1** — discrepancy) | §3.4 (one-line), §4 (table) |
| 2 | `K` (max fragment size, statements) | `channel.py:86` `ChConstrained.max_fragment_size` | 4 (default); Stage-4 README states 4 | §4.2 footnote, §5.4, §5.5, §5.6 |
| 3 | `M` (max messages/lineage/epoch) | `channel.py:87` `ChConstrained.max_messages` | 3 (default); Stage-4 README states 3 | §4.2 footnote, §5.4, §5.5, §5.6 |
| 4 | N (lineages per arm) | `orchestrator.py:154` | 3 | §4.2 footnote (stated) |
| 5 | `drop_frac` (primitive-pool dropout per lineage) | `orchestrator.py:31` | 0.20 | §4.2 footnote (stated) |
| 6 | `pop_size` (population per task) | `lineage.py:97`, `orchestrator.py:156` | 100 | §4 (table) — **not stated** |
| 7 | `tournament_k` | `lineage.py:98` | 3 | §4 (table) — **not stated** |
| 8 | `elite` | `lineage.py:99` | 5 | §4 (table) — **not stated** |
| 9 | `p_crossover` | `lineage.py:100` | 0.30 | §4 (table) — **not stated** |
| 10 | `p_fragment` (prob. of fragment-splice vs other ops) | `lineage.py:101`, `b0.py:29` | 0.15 | §4 (table) — **not stated** |
| 11 | `max_library` (per-lineage fragment library size) | `lineage.py:102` | 50 | §4 (table) — **not stated** |
| 12 | AOS decay (op_n/op_w exponential recency) | `lineage.py:84` `op_credit(decay=0.99)` | 0.99 | §3.3 (mentioned qualitatively; value not stated) |
| 13 | AOS op-weight floor | `lineage.py:81` `op_weight` `max(0.05, ...)` | 0.05 | §3.3 — **not stated** |
| 14 | AOS init credit (op_n, op_w) | `lineage.py:56–57` | 2.0, 1.0 | §3.3 — **not stated** |
| 15 | Hall-of-fame size cap per task | `lineage.py:76` `if len(self.hof) > 10` | 10 | §3.3 — **not stated** |
| 16 | Fitness cache: threshold length, cap | `fitness.py:62` (`len(prog) >= 4`), `fitness.py:53` (`_cache_cap = 300_000`) | 4, 300,000 | §3.2 — **not stated** (mentioned in §3.2 as "length ≥ 4" but cache cap is not) |
| 17 | Budget: Stage-4 sweep | B0–B4 README line 16 | 1,000,000 | §5.1 (stated) |
| 18 | Budget: frontier 8-seed B0/B1/B2/B6/B7 | `experiments/2026-07-21_frontier_recovered/README.md` | 3,000,000 | §5.4 (stated) |
| 19 | Budget: frontier 20-seed B0/B1/B2/B5/B6/B7/B8/B9 | `experiments/2026-07-22_*/README.md`, `2026-07-23_*/README.md` | 4,000,000 | §5.4–§5.6 (stated) |
| 20 | Seeds: Stage-1 5-arm sweep | Stage-4 README | 5 (seeds 1–5) | §5.1 (stated) |
| 21 | Seeds: K×M dose-response | `dose_response.py` (default) | 3 | §5.3 (stated) |
| 22 | Seeds: frontier 8-seed | experiment README | 8 | §5.4 (stated) |
| 23 | Seeds: frontier 20-seed (B0/B1/B2/B5/B6/B7/B8/B9) | experiment README | 20 | §5.4–§5.6 (stated) |
| 24 | `mine_every` (B5 compression-miner period, epochs) | `b0.py:32, 84` | 5 | §3.6, §5.6 — **not stated** |
| 25 | `max_new` (B5 abstractions per mine call) | `lineage.py:672` | 8 | §3.6, §5.6 — **not stated** |
| 26 | `min_size` / `max_size` (B5 abstraction body bounds) | `lineage.py:673–674` | 2, 4 | §3.6, §5.6 — **not stated** |
| 27 | `min_occurrences` (compression miner duplicate threshold) | `dsl/abstraction.py:274` | 2 | §3.6, §5.6 — **not stated** |
| 28 | Curriculum payload `n_pairs` per sub-abstraction | `orchestrator.py:78` | 4 | §3.5, §5.5 — **not stated** |
| 29 | Curriculum aux-task per-lineage cap | `orchestrator.py:22` `_MAX_AUX_TASKS` | 12 | §3.5, §5.5 — **not stated** |
| 30 | 1-failure case in 399/400 reproduction | `tests/test_stage0.py:30–31` | `e40b9e2f` (frozenset-order-sensitive in Hodel's solver) | §3.2 — **not stated** (mentioned in §2 but not §3.2) |

The paper should add a "Configuration" table to §4 (between §4.2 and §4.3, or as an appendix) listing items 1, 2, 3, 4, 5, 6–11, 12–15, 24–27 at minimum. The single most consequential omissions are items 1, 2, and 24 — these are the values a reader would type into a config file to reproduce the headline result.

---

## Artifact mapping

The paper currently cites experiments by inline tag: `[exp: 2026-07-22_b5_central_library]`. This is a *pointer* to an experiment folder but not a *map* from a paper number to an artifact row. For a reproducibility reviewer, the right primitive is: for every number in the paper, name the experiment folder, name the JSONL row that produced it, and (ideally) name the git commit that produced that JSONL.

Below is a suggested template. The current paper has all the components but does not assemble them; the table below is what the paper should add as an appendix (or, minimally, a footnote under the headline tables in §5.6 and §5.9).

| Paper claim | Value | Experiment | Run log | Commit hash | Notes |
|---|---|---|---|---|---|
| §5.6 B5 evo-solved (20-seed) | 2.65 ± 1.31 | `experiments/2026-07-22_b5_central_library/` | `b5_summaries.jsonl` (20 rows) | (paper does not state) | per-arm README `analysis.txt` reproduces the mean/sd |
| §5.6 B0 evo-solved (20-seed) | 2.25 ± 1.07 | `experiments/2026-07-22_b5_central_library/` (B0 rows in same `b5_summaries.jsonl`) and `experiments/2026-07-22_frontier_recovered_scaled/` | both | (paper does not state) | B0 rows were generated in two places; the 20-seed file in `2026-07-22_b5_central_library/` is the canonical for the §5.6 table |
| §5.6 B6 evo-solved (20-seed) | 1.80 ± 1.06 | `experiments/2026-07-22_frontier_recovered_scaled/` | `summaries.jsonl` (B6 rows) | (paper does not state) | |
| §5.5 B8 evo-solved (20-seed) | 1.60 ± 0.75 | `experiments/2026-07-23_frontier_curriculum/` | `summaries.jsonl` (B8 rows) | (paper does not state) | also reports `aux_received` ≈ 12, `aux_solved` ≈ 7.8 mean |
| §5.1 Stage-1 B2−B1 | 0.0 (B2 = B1 = 10.4) | `experiments/2026-07-20_stage4_b0-b4_matched_compute/` | `sweep_results.jsonl` | `40067c7` (stated in README) | only experiment that states the commit hash |
| §5.3 K×M ladder | 5 configs × 3 seeds | `experiments/2026-07-20_b3_dose_response/` | `results.jsonl` | (paper does not state) | |

**Concretely the paper should add:**

1. The git commit hash for every experiment, in the format `<short-hash> <experiment-date>`. The Stage-4 README is the only one that does this. The other 8 experiment READMEs do not. A single `git log --pretty=format:"%h %ai %s" experiments/` would fill the table.

2. A standard file-naming convention across experiments. The Stage-4 run uses `sweep_results.jsonl`; the 8-seed and 20-seed frontier runs use `summaries.jsonl`; the B5 run uses `b5_summaries.jsonl`. The paper should pick one (probably `summaries.jsonl` as the de-facto standard) and rename the Stage-4 file or note the inconsistency in §4.3.

3. For each result-table row in §5.4 and §5.6, an inline `(run log: <file>, n=<N>)` annotation. The current paper has `[exp: ...]` tags but these point to a folder, not a row, and the row format (per-arm summary) is not visible without opening the JSONL.

4. A single "all-run audit" table for §4.3's compute-spread claim. The paper says "0.10% spread on the headline 20-seed frontier runs" — but the audit value is per-experiment and lives in each `analysis.txt`. A consolidated table with one row per experiment (experiment, n_arms, n_seeds, budget, audit spread, wall-clock mean ± sd) would close this gap. Wall-clock is in the JSONL `"t"` field (e.g. `t: 5742.34` for B5 seed 1 = ~96 min) and is currently dropped from the paper entirely.

---

## One-line summary

**Fix the λ_MDL error in §3.4 and add a §4 configuration table that names K, M, mine_every, and the AOS/init/hall-of-fame/cap hyperparameters — the rest of the gaps are paper-text polish, but these are the two changes a reviewer would demand before accepting the paper as reproducible.**
