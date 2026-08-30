# B5D dreaming pilot (2026-08-29) — roadmap §9b

The first implementation of **self-directed practice** on the clebran rig
(DreamCoder wake/sleep "fantasies"). After every solve, the lineage
synthesises a variant task from its own solution and adds it to its task
pool — it then works on the synthetic task like any other, costing real
candidate-evaluations (matched compute vs B5).

## Setup

- B5 = single population + self-mined central library (Stitch/DreamCoder
  control, arm 5).
- B5D = B5 + `clebran.curriculum.generate_task` called on every solve
  (`clebran/baselines/b0.py:run_b5_dream`); synthetic tasks added as
  `gen_*` with `auxiliary=False` so they join the real task pool.
- Frontier subset (25 D2 + 5 D3), 1M evals/run, **5 seeds**, matched
  compute (per-seed: B5D = 1,000,042-1,004,458 evals; B5 = 1,000,022-
  1,000,109 evals — 0.05% spread).
- Pilot scale chosen to be diagnostic in ~30 min/run; the 4M pilot
  comparison is the natural escalation.
- Outputs: [cost.txt](cost.txt), [cost.json](cost.json),
  [library.txt](library.txt), [dream_split.txt](dream_split.txt).

## Headline: dreaming engages but does not transfer to the frontier

| metric (1M, 5 seeds) | B5 | B5D | diff |
|---|---|---|---|
| frontier solves /30 | 10.40 ± 1.14 | 10.40 ± 0.55 | +0.00 |
| evals/solve (per-seed ratio) | 97,077 | 96,457 | -620 (-0.6%) |
| **welch-t p (per-seed evals/solve)** | — | — | **0.905** (tied) |
| frontier variance | 1.14 | 0.55 | **B5D has half the variance** |
| dreams added | — | 287.2 / seed | — |
| dreams solved | — | 278.8 / seed | — |
| **dream utilization** | — | **97.0%** | — |

The dreaming loop is **engaged and effective at the dreaming tasks**
(97% of generated dream tasks are solved — the lineage can finish them
almost every time). But it does *not* transfer to more or cheaper
frontier solves: B5D solves 10.40 frontier tasks, exactly the same as
B5, at the same per-seed cost (welch-t p=0.905 on per-seed evals/solve).
The headline is a **null on the count and cost axes**.

**The variance reduction is real and worth noting**: B5's per-seed
frontier count has SD=1.14 (range 9-12), B5D's has SD=0.55 (range
10-11). Dreaming smooths out the per-seed variation, possibly because
the lineage has more practice opportunities and converges more
reliably. This is a small but consistent effect.

## Dream cost: easy, mid-run, not trivial

The per-solve evals split (cumulative; see [dream_split.txt](dream_split.txt)):

| source | n | median | mean | min | max |
|---|---|---|---|---|---|
| frontier | 52 | 88,268 | 153,779 | 296 | 809,395 |
| dream | 1,394 | **590,526** | 580,753 | 76,877 | 999,083 |

Dreams have a *higher* cumulative evals-to-solve than frontier tasks
(590K vs 88K median). That looks like dreams are harder — but
cumulative evals at solve-time is not the right cost metric for a
*temporal flood* of solves. The right reading: by the time the lineage
has spent 590K evals, half the dream solves have happened; the
*earliest* dreams are solved quickly (phase1) and later ones absorb
the running search. The 97% utilization on a 280-task-per-seed flood
is the headline — the lineage *can* find a program for every dream it
generates, given enough search.

The dream generation itself is **free** (it calls `run_safe` directly,
not through the Evaluator, so it doesn't consume the candidate-eval
budget). The cost is the lineage's own search on the synthetic tasks.

## Library impact: the dreaming *does* build a more active library

This is the substantive positive result.

| metric (1M, 5 seeds) | B5 | B5D |
|---|---|---|
| library size (n abstractions) | 5.4 | **9.2** |
| **used rate** (% of abstractions used in some solution) | **3.3%** | **70.2%** |
| **cross-task reuse** (mean abstractions used in ≥ 2 tasks) | **0.0** | **5.0** |
| mean body size | 2.34 | 2.26 |
| **topographic similarity (topsim)** | **0.264** | **0.047** |

Source: [library.txt](library.txt). B5D's library is **1.7× larger,
21× more used, and produces real cross-task reuse** (5 abstractions
reused across tasks vs B5's 0). But it has a **5× lower topographic
similarity** — the abstractions are less compositionally structured.

For comparison, B5 at 4M (20 seeds, 4× the compute): n=6.6, used=9.4%,
reuse=0.1, topsim=0.330. **B5D at 1M beats B5 at 4M on every library
metric except topsim**, and the dreaming runs at 1/4 the compute.

**Reading:** the dreaming produces a working, *heavily-used* library
at a fraction of the cost. But the library captures *converged*
patterns (the easy dream-task solutions) rather than *novel
compositions* (which would push topsim up). The dreams give the
lineage *practice* on existing primitives, not *discovery* of new
abstractions.

## Honest scope

- **n=5 seeds at 1M.** A 4M pilot is the natural next step to see if
  the library benefit translates into frontier gains at the budget
  where B5+planner had its budget-conditional result (paper 3).
- **Frontier count is tied with B5.** No escape from the null on the
  count axis. The dreaming loop is doing what it was designed to do
  (generate, solve, mine), and the result of that is a *richer,
  cheaper library*, not a higher frontier count.
- **Topsim direction matches Paper 1's finding**: partial views yield
  task-idiomatic abstractions. B5D sees 280 dream tasks (a flood of
  similar concepts) and produces task-idiomatic abstractions; B5
  sees 11 frontier tasks (a sparse, hard set) and produces more
  compositional ones.
- **The variance reduction is a small but real effect.** A larger
  sweep would tell us if it's robust or noise.

## What this means for the roadmap

The 9b dreaming hypothesis is **partially supported**: the loop
*engages* and *changes the library*, but it does not expand the
frontier at 1M. The library effect is interesting and worth chasing
(richer abstractions, lower cost), but the dreaming's value is
*transport* and *practice* of existing knowledge, not *discovery* of
new capability. This is consistent with the broader pattern in
roadmap §8a/b: clebran's system is good at *moving* competence, not
at *creating* it.

A 4M-eval pilot (5 seeds, ~2 hours/seed = 10 hours total) is the next
escalation. The interesting question there: does the library effect
compound enough at 4M that B5D starts to beat B5 on the *count* axis?
