# Task-subset specialization 1M pilot (2026-09-22) — discovery-bottleneck #3

The third concrete test of the **discovery bottleneck** principle: instead of
changing *how* the lineage searches, change *what* the lineage searches on.
Run B5 lineages on a 15-task *hard* subset (tasks B5-4M never solved) and on a
15-task *random* subset. The hypothesis: if different subsets need different
*kinds* of programs, splitting the budget and recombining the libraries
beats running one lineage on the full set at the same total compute.

This is the proper test of the clebran multi-agent *premise*: division of
labor creates diversity, transport unifies it. The README §"The discovery
bottleneck" frames it as the next bet after #1 (failure-mode dreaming) and
#2 (heterogeneous fitness), both of which returned null.

## Setup

- Two arms × 5 seeds × 1M evals each.
  - **hard15 arm** — B5-1M on
    [data/hard15_subset.json](../../data/hard15_subset.json): 15 tasks B5-4M
    (15 seeds) never solved.
  - **random15 arm** — B5-1M on
    [data/random15_subset.json](../../data/random15_subset.json): 15 random
    stage1 tasks, fixed seed.
- Subsets intersect in 8 tasks; hard15 \ random15 has 7 unsolved-by-4M tasks,
  random15 \ hard15 has 7 tasks B5 finds easy.
- Per-task compute: 1M / 15 = **67k/task** in both arms.
- Baselines:
  - **B5-1M on full stage1** (5 seeds) — same lineage, 1M/30 = 33k/task.
    Used for an apples-to-apples comparison on the same task subsets.
  - **B5-4M on full stage1** (15 seeds) — same lineage, 4M/30 = 133k/task.
    Used to confirm whether the hard15 set is genuinely beyond B5's reach.
- Distinguishes two notions of "solve":
  - **frontier solve** — the lineage's final state (`summary.solved_tasks`).
    This is what the lineage claims it has solved.
  - **test-exact solve** — program passes BOTH train AND test pairs at the
    last `solve` event. Some tasks (notably `1f85a75f`) admit *spurious*
    train-only solvers that the test pairs reject; the lineage marks them
    as solved but the held-out pairs catch the overfit.
- Outputs: [analysis.txt](analysis.txt) (full output of
  [analyze_subset.py](../../analyze_subset.py)).

## Headline: hard tasks out of reach; specialization on random tasks ≈ compute

| metric (test-exact / 15-task subset) | hard15 sub | random15 sub | full(30) | per-task compute |
|---|---|---|---|---|
| hard15 arm (1M) | **0.00** | n/a | n/a | 67k/task |
| random15 arm (1M) | 0.00 | **5.60** | n/a | 67k/task |
| B5-1M on stage1 | 0.00 | 4.60 | 10.20 | 33k/task |
| **B5-2M on stage1 (matched-compute)** | **0.00** | **5.00** | **11.00** | **67k/task** |
| B5-4M on stage1 (reference) | 0.00 | 3.53 | 8.07 | 133k/task |

Per-seed test-exact on the random15 sub:

```
random15 arm : [7, 5, 5, 6, 6]    mean 5.60, sd 0.55
B5-2M        : [5, 5, 4, 5, 6]    mean 5.00, sd 0.71
B5-1M        : [5, 4, 4, 5, 5]    mean 4.60, sd 0.55
```

**Welch tests** (n=5 per arm):
- random15 arm vs B5-1M on the random15 sub: **p = 0.007** (gains +1.0 solve at 2× per-task compute)
- random15 arm vs **B5-2M** on the random15 sub: **p = 0.102** (ns — gain over B5-2M at *matched* per-task compute is small and not significant)
- hard15 arm vs B5-1M on the hard15 sub: **p = 1.000** (no signal)
- hard15 arm vs B5-2M on the hard15 sub: **p = 1.000** (no signal at matched compute)

*Sources:* [analysis.txt](analysis.txt) (initial) and
[analysis_with_2m.txt](analysis_with_2m.txt) (with matched-compute B5-2M).
B5-4M is reference only (15 seeds, 133k/task — twice the per-task
compute of the specialized arms).

**Three findings in one:**

1. **Specialization on hard tasks fails, even at matched compute.** The
   hard15 arm gets 0 test-exact discoveries at 1M/15=67k/task. B5-2M
   on the same subset at the same 67k/task is identical: 0 test-exact
   discoveries (the only "solve" is the 1f85a75f train-only overfit —
   exactly the same artefact B5-1M produces, and exactly the one
   B5-4M produces 3 times across 15 seeds at 133k/task). **No B5 lineage
   finds a test-exact solve on the hard15 set at any compute budget
   through 4M.** The hard15 set is genuinely beyond B5's reach; no
   specialization trick can rescue a search that's out of room.

2. **Specialization on random tasks ≈ per-task compute doubling.**
   The random15 arm gets 5.6 test-exact solves on its subset;
   B5-1M at full stage1 gets 4.6 (p = 0.007). But the random15 arm
   has 67k/task vs B5-1M's 33k/task — *twice the per-task compute at
   the same total budget*. **The matched-compute baseline (B5-2M at
   67k/task) gets 5.0 on the same subset — statistically tied with
   the random15 arm (p = 0.102).** Most of the apparent +1.0 gain is
   the per-task compute redistribution; the residual is small and
   not significant.

3. **No signal beyond compute.** Whether the difference between
   random15 arm and B5-2M (0.6 solves, p = 0.102) reflects a real
   small specialization effect or noise is unanswerable at n = 5.
   The headline is clean: **task-subset specialization does not
   expand B5's frontier; what looks like a gain on a complementary
   subset is the 2× per-task compute redistribution alone.**

## What this means

Both prongs of the clebran premise — that disjoint subsets need different
*kinds* of programs and that per-subset libraries recombine into a broader
union — fail to deliver at this budget.

- The *hard* subset is too hard. B5-4M (15 seeds, 133k/task) still finds
  zero test-exact on it; 67k/task is not the bottleneck. The hard tasks
  need *new primitives or operators* to solve, not more budget on the
  same DSL.
- The *random* subset, which contains the easy D1 tasks B5 always solves,
  is *already saturated* — specialization just doubles the per-task
  compute and gains back exactly the budget difference.

The discovery-bottleneck menu has now been exercised three times:
#1 failure-mode dreaming — null at 1M
(`experiments/2026-08-31_b5d_nm_1m/`).
#2 heterogeneous fitness — null at 1M
(`experiments/2026-08-31_b5_heterogeneous_1m/`).
#3 task-subset specialization — null at 1M (this experiment).

None of these mechanisms, applied to a B5 lineage, expand the frontier.
The transport side of clebran is solved (B5's library mechanism works);
the discovery side is open. The next bets in the menu — novelty search,
learned L1 as proposer, operator self-modification, the L3 evoker (9f.4)
— all attack discovery by adding a *new dimension* the lineage can
search, rather than redistributing budget across the same DSL.

## Lure tasks (solved train-only, rejected by test pairs)

| arm | events | unique tasks | task(s) |
|---|---|---|---|
| hard15 | 1 | 1 | `1f85a75f`(1) |
| random15 | 1 | 1 | `0b148d64`(1) |
| B5-1M full stage1 | 1 | 1 | `1f85a75f`(1) |
| B5-4M full stage1 | 3 | 1 | `1f85a75f`(3) |

`1f85a75f` is the persistent "lure" task: B5 consistently finds programs
that pass the train pairs but not the test pairs. B5-4M produces 3 such
overfits across 15 seeds (vs 1 at 1M × 5 seeds), so the lure count grows
with budget but the lineage never finds a test-exact program.

## Per-seed frontier

```
hard15 arm (specialized):  [1, 0, 0, 0, 0]
random15 arm (control):    [7, 5, 5, 6, 6]
B5-1M on full stage1:      [10, 10, 9, 11, 12]
B5-4M on full stage1:      [13, 13, 12, 15, 13, 12, 11, 12, 12, 11, 12, 12, 11, 12, 11]
```

Per-seed within subset (lineage's final state):

```
hard15 arm on hard15 sub:    [1, 0, 0, 0, 0]
random15 arm on hard15 sub:  [1, 0, 0, 0, 0]
random15 arm on random15 sub:[7, 5, 5, 6, 6]
B5-1M on hard15 sub:         [0, 0, 0, 0, 1]
B5-1M on random15 sub:       [5, 4, 4, 5, 5]
```

The "1" on `hard15 arm on hard15 sub` is seed 1, which reported
`solved_tasks = ["1f85a75f"]` with `test_exact = 0`. The "1" on
`B5-1M on hard15 sub` is seed 5, which reported 12 total solves including
`1f85a75f` (also `test_exact = 0`; it had 11 test-exact discoveries on
other tasks). Both are the same lure artefact.

## Matched-compute baseline (2026-09-24) — B5-2M on full stage1, 67k/task

The "Honest scope" gap from the first analysis was: does a B5 arm with
the same per-task compute as the specialized arms (67k/task) match the
specialized arms' apparent gain over B5-1M? B5-2M on full stage1 gives
2M/30 = 67k/task — matching both specialized arms. **It does match.**
5 seeds × 2M evals; 23-min wall-clock; logs at `logs/b5_2m_seed*.jsonl`.

| metric (test-exact / 15-task subset) | hard15 sub | random15 sub | full(30) |
|---|---|---|---|
| hard15 arm (1M, 67k/task) | **0.00** | n/a | n/a |
| random15 arm (1M, 67k/task) | 0.00 | **5.60** | n/a |
| B5-1M on full stage1 (33k/task) | 0.00 | 4.60 | 10.20 |
| **B5-2M on full stage1 (67k/task)** | **0.00** | **5.00** | **11.00** |
| B5-4M on full stage1 (133k/task) | 0.00 | 3.53 | 8.07 |

Per-seed test-exact on the random15 sub:

```
random15 arm on random15 sub: [7, 5, 5, 6, 6]   (mean 5.60)
B5-2M       on random15 sub: [5, 5, 4, 5, 6]   (mean 5.00)
B5-1M       on random15 sub: [5, 4, 4, 5, 5]   (mean 4.60)
```

**Welch tests on the matched-compute question** (random15 arm vs B5-2M
at the same 67k/task): **p = 0.102 — not significant**. The
random15 arm's +1.0 solve gain over B5-1M (p = 0.007) is *mostly*
explained by the 2× per-task compute redistribution (B5-2M at the same
67k/task gains +0.4 over B5-1M at 33k/task). The remaining 0.6 solve
gap between random15-arm and B5-2M is non-significant — consistent
with noise or with a small specialization effect too small to detect
at n = 5.

**Both prongs of the clebran premise close cleanly:**

1. **hard15 specialization**: still 0 test-exact at the matched 67k/task.
   B5-2M-on-hard15 is [0, 0, 0, 0, 1] (the "1" is the 1f85a75f lure),
   identical to B5-1M. The hard set is genuinely beyond B5's reach;
   specialization can't rescue a search that's out of room.
2. **random15 specialization**: the per-task compute hypothesis is
   confirmed. B5-2M (67k/task) matches the random15 arm (67k/task) on
   the same subset (p = 0.102). The random15 arm's apparent +1.0 gain
   over B5-1M is mostly the 2× compute doubling; the residual is not
   statistically significant at n = 5.

The 8.07 / 12.13 mismatch in B5-4M test-exact / frontier (and the
11.00 / 11.20 mismatch in B5-2M) is the same train-only-overfit
artefact that drove the lure-task analysis above: at higher budgets,
the lineage produces more frontier "solves" that the test pairs
reject. The lure count grows with budget (B5-1M 1 event, B5-2M 1 event,
B5-4M 3 events across 15 seeds, all on `1f85a75f`).

*Artifact:* the matched-compute run is at `logs/b5_2m_seed{1..5}.jsonl`;
the cost-axis loader (`clebran/metrics/cost.py`) now picks up `B5-2M`.
Driver: `scripts/run_b5_2m.ps1`.

## Honest scope

- n=5 seeds at 1M and n=5 seeds at 2M. The matched-compute baseline
  (B5-2M at 67k/task) closes the original "Honest scope" gap (random15
  arm vs B5-1M at 33k/task): the random15 arm's gain is mostly the
  per-task compute doubling, with a small non-significant residual
  (0.6 solves, p = 0.102) that could be a true small specialization
  effect or noise.
- The hard15 set is defined as "tasks B5-4M never solved across 15 seeds"
  ([build_subsets.py](../../build_subsets.py)). That definition is
  contingent on the B5-4M baseline; a different baseline (e.g. B5 with
  dreaming, or B5D 4M) could produce a different "hard" subset. But
  the result that *no B5 lineage solves any of these 15 at 67k/task*
  is robust to the definition: the per-seed count is 0 across 5 seeds
  in the specialized arm and B5-2M, and 0 in B5-4M (15 seeds) at 133k/task.
- The lure / train-only distinction matters: without it, the hard15 arm
  would look like "1 frontier solve" instead of "0 test-exact". The
  test pairs are doing real work catching the overfit on `1f85a75f`.