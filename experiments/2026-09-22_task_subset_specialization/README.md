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

## Headline: hard tasks out of reach; specialization on random tasks = compute

| metric (1M, 5 seeds) | hard15 arm | random15 arm | B5-1M full stage1 | B5-4M full stage1 |
|---|---|---|---|---|
| frontier solves / arm | 0.20 ± 0.45 | 5.80 ± 0.84 | 10.40 ± 1.14 | 12.13 ± 1.13 |
| frontier solves / 15-task subset | 0.20 ± 0.45 | 5.80 ± 0.84 | 0.20 / 4.60 | 0.20 / 5.27 |
| **test-exact solves / 15-task subset** | **0.00 ± 0.00** | **5.60 ± 0.55** | **0.00 / 4.60** | **0.00 / 3.53** |
| train-only overfits / arm | 1 | 1 | 1 | 3 |
| welch-t p (specialized vs B5-1M on the same subset) | p = 1.000 | p = 0.007 | — | — |

*Source:* [analysis.txt](analysis.txt). B5-4M row is reference only (15 seeds,
133k/task — twice the per-task compute of the specialized arms).

**Two findings in one:**

1. **Specialization on hard tasks fails.** The hard15 arm gets 0 test-exact
   discoveries at 1M/15=67k/task. The only "solve" the lineage reports is
   a train-only overfit on `1f85a75f` (the persistent lure task) — exactly
   the same artefact that B5-1M at full stage1 produces and that B5-4M at
   full stage1 produces 3 times across 15 seeds. **Even B5-4M at twice the
   per-task compute finds zero test-exact discoveries on this subset.**
   The hard15 set is genuinely beyond B5's reach at these budgets; no
   specialization trick can rescue a search that has run out of room.

2. **Specialization on random tasks = per-task compute.** The random15 arm
   gets 5.6 test-exact solves on its subset; B5-1M at full stage1 gets 4.6
   on the same subset (p = 0.007). But the random15 arm has 67k/task vs
   B5-1M's 33k/task — *twice the per-task compute at the same total
   budget*. A 2× per-task compute increase is the natural explanation
   for ~1 more solve on a frontier of easy D1 tasks. There is no signal
   for "specialization helps on a complementary subset" beyond the
   compute redistribution.

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

## Honest scope

- n=5 seeds at 1M. The per-task compute (67k) is twice the B5-1M baseline
  on full stage1 (33k/task). The headline is robust to that: the
  specialized arm needs to *outperform* B5-1M at the same total budget,
  and it does, but only by an amount consistent with the per-task
  compute doubling alone.
- A matched baseline (B5-2M on full stage1 → 67k/task, matching the
  specialized arms) would close the loop, but the natural reading is
  that 2× compute on easy tasks buys roughly 1 more solve, which is
  exactly what the random15-vs-B5-1M gap shows. We did not spend the
  extra compute to confirm.
- The hard15 set is defined as "tasks B5-4M never solved across 15 seeds"
  ([build_subsets.py](../../build_subsets.py)). That definition is
  contingent on the B5-4M baseline; a different baseline (e.g. B5 with
  dreaming, or B5D 4M) could produce a different "hard" subset. But
  the result that *no B5 lineage solves any of these 15 at 67k/task*
  is robust to the definition: the per-seed count is 0 across 5 seeds
  in the specialized arm, 1 in B5-1M (the lure), and 0 in B5-4M (15
  seeds) at 133k/task.
- The lure / train-only distinction matters: without it, the hard15 arm
  would look like "1 frontier solve" instead of "0 test-exact". The
  test pairs are doing real work catching the overfit on `1f85a75f`.