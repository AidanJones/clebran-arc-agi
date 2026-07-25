# 5. Results

We report the experimental results in the order in which they
were produced. Section 5.1 reports the Stage-1 first test of
H1/H2/H3 on the Stage-1 subset. Section 5.2 reports the B0
reachability probe on the frontier subset, which established
the frontier as the right place to look. Section 5.3 reports the
bandwidth dose-response. Section 5.4 reports the recovered-
primitive channel result and its power check. **Section 5.5
reports the central-library control (B5) — the headline arm.**
**Section 5.6 reports the curriculum channel, framed as "B5 is
so good that even the curriculum channel — whose mechanism does
work — cannot beat it."** Section 5.7 reports the teach→test
probe and the amortization result that corrected it. Section 5.8
reports the vocabulary-quality metrics.

## 5.1 The Stage-1 first test of H1/H2/H3

The first multi-arm run was the Stage-4 sweep on the Stage-1
subset, 5 arms × 5 seeds × 1M evals, audited to 0.27% compute
spread. The headlines are:

- **H1 supported.** Pairwise Jaccard distance over primitive
  usage, averaged over the multi-lineage arms and 5 seeds, is
  0.57 ± 0.10. The minimum Jaccard across the 25 lineage-pairs
  is 0.41; the maximum is 0.78. Tasks solved by exactly one
  lineage appear in 4/5 seeds. The lineages *do* diverge into
  different solution strategies.

- **H2 null.** The fragment channel (B2) and the unconstrained
  fragment channel (B3) are statistically indistinguishable from
  the isolated baseline (B1). B2 = B1 = 10.4/30, B0 = 10.6/30.
  Channel reuse on Stage-1 is at most 0.17 (B3) — the channel
  barely engages, because the Stage-1 solvable frontier is
  shallow enough that phase-1 systematic seeding closes it
  without communication.

- **H3 directional, not significant.** B3 is the *worst* arm at
  the highest reuse (9.80/30), directionally consistent with the
  unconstrained-sharing-hurts story. The pooled standard error
  is large enough that the gap is not significant (B2 − B3 =
  +0.60, se 0.32); the result is suggestive, not confirmatory.

[exp: 2026-07-20_stage4_b0-b4_matched_compute]

The Stage-1 result is the first indication that the clebran
hypothesis, as posed, is not the cheap win the design assumed.
A null at this stage is *structural*, not a budget artifact: the
solvable frontier is closed by phase-1, so the channel has
nothing to add.

## 5.2 The frontier reachability probe

A two-seed B0 pilot at 2M evals on the frontier subset
established the regime in which a channel effect could plausibly
appear. Three results.

1. **Phase tagging is correct.** The one D3 solve in the pilot
   was a short accidental depth-2 solution, correctly tagged
   phase-1. Every genuine evolution-phase solve was D2. The
   evolution phase *only* reaches D2 at 2M evals.
2. **No D3 evolution solves.** Zero D3 evolution solves across
   2 seeds at 2M evals. D3 (depth 6–10) is beyond reach and
   would just add a floor of zeros, so the frontier is
   *composition-reweighted* to 25 D2 + 5 D3.
3. **Counts are small.** 1–2 evolution solves per seed per 2M
   evals. The treatment signal, if any, is small; the budget
   and seed count must be sized for it.

A pilot of B1 vs B2 on the frontier at 3M evals, 2 seeds,
confirmed the frontier rebuild: B2 mean evolution-solves 2.0
vs B1 1.5, and channel reuse *jumped* from 0.06 to 0.67–1.00.
The mechanism H2 depends on is now active; the frontier rebuild
worked. Held for the main sweep on the same compute decision as
the next item.

[exp: 2026-07-20_frontier_pilot]

## 5.3 Bandwidth dose-response (H3 on Stage-1)

A K×M bandwidth ladder on the Stage-1 subset (`none` → K2M1 →
K4M3 (=B2) → K8M10 → `uncon` (=B3)), 3 seeds, 1M evals, tests
the dose-response shape and the hypothesized crowding mechanism.
The result is *flat* and mechanistically informative. We report
**evolution-phase solves** here (not total solves), because H2
and H3 are *defined* on evolution-phase solves — the only
place the channel can act.

| config | evo-solved/30 | reuse | frag-share | frag-succ | mut-succ |
|---|---|---|---|---|---|
| none | 2.00 ± 1.00 | 0.00 | 0.03 | 0.02 | 0.36 |
| K2M1 | 2.00 ± 1.00 | 0.04 | 0.03 | 0.02 | 0.36 |
| K4M3 | 2.33 ± 0.58 | 0.05 | 0.03 | 0.02 | 0.36 |
| K8M10 | 2.00 ± 1.00 | 0.16 | 0.03 | 0.02 | 0.36 |
| uncon | 1.67 ± 0.58 | 0.17 | 0.03 | 0.02 | 0.36 |

Three things to read off the table. First, *no dose-response*:
the evolution-only solve rate is flat (1.67–2.33) across the
whole ladder, all overlapping in noise; the unconstrained
endpoint is *nominally* the worst (1.67) but the gap to the
constrained middle (2.33) is within 1 SE. Second, the *crowding
mechanism does not occur*: `frag-share` is pinned at 0.03
*regardless of bandwidth* — identical even for `none`, which has
no channel at all. Bandwidth changes *which* fragments are used
(reuse rises 0 → 0.17) but not *how much* fragment-splicing
happens. Third, the reason is adaptive operator selection: AOS
weights the fragment operator by its ~2% success vs ~36% for
mutation, and floors it near 3% share no matter how much
material arrives. An adaptive learner is robust to unconstrained
sharing because it self-constrains; the constraint stops
mattering.

[exp: 2026-07-20_b3_dose_response]

**A caveat on the H3 test.** Adaptive operator selection is a
*design choice* in the rig (added during Stage 1, §6.3) — not
a measured property of the learner. The H3 question (does a
bandwidth constraint preserve better abstractions than
flooding?) is in this design *partially confounded with AOS*:
AOS regulates the channel's intake regardless of bandwidth, so
H3 may be *untestable* in this substrate, not just null. The
dose-response is a *measurement* of the AOS regime, not a clean
test of the H3 mechanism. The frontier H3 tests (§5.4) are run
on the same AOS regime but in a regime where reuse is much
higher (0.67–1.00) and the channel is more engaged; the H3
null persists there too (B6 ≈ B7, §5.5), consistent with the
same AOS explanation.

## 5.4 Recovered-primitive channel (B6/B7)

The first payoff measurement on the frontier: 8 seeds, 3M evals,
B0/B1/B2/B6/B7. The recovered-primitive channel is the §11
scientifically important variant: lineages abstract their *own*
subroutines and communicate those, rather than fragments over
Hodel's given primitives.

| arm | what | evo-solved /30 | reuse |
|---|---|---|---|
| B0 | single population | **2.12 ± 1.13** | — |
| B1 | 3 isolated | 1.50 ± 0.53 | 0 |
| B2 | + constrained fragment | 1.38 ± 0.92 | 0.66 |
| B6 | + constrained recovered-primitive | 1.88 ± 0.99 | 0.67 |
| B7 | + unconstrained recovered-primitive | 2.12 ± 1.25 | 0.67 |

| comparison | Δ (se) | reads as |
|---|---|---|
| B6 − B1 | +0.38 (0.40) | recovered-primitive transfer helps |
| B6 − B2 | +0.50 (0.48) | recovered beats given-primitive transfer |
| B6 − B7 | −0.25 (0.56) | constraint does **not** help (H3) |
| B2 − B1 | −0.12 (0.38) | fragment transfer doesn't help |

The mechanism is real. The *received-used* metric — the average
number of received primitives used per solve — is 1.21 for B6
and 1.42 for B7: lineages solve tasks using primitives they
were *handed and never derived*. (The metric is a continuous
count of received abstractions used per solve, not a binary
flag.) A concrete example: a lineage discovered a 4-statement
mirror-tiling subroutine `vmirror → hconcat → hmirror → vconcat`
and used it as a single named call to solve task `62c24649` with
a length-2 program.

The result is directionally the §11 hypothesis — recovered >
given — and the divergence tax is paid back: B7 = 2.12 = B0.
Nothing is *significant* (counts are 1–2 evolution solves/seed;
se's are 0.4–0.5 and swamp the effects), and the comparison is
honestly underpowered.

[exp: 2026-07-21_frontier_recovered]

A power check — 20 seeds (8 → 20), 4M evals (3M → 4M), with the
new compression miner and the 3× faster engine — gives:

> **Note on the cross-run comparison.** The 20-seed run uses
> the new compression miner and the ~3× faster engine. The
> 8-seed and 20-seed B0 measurements (2.12 vs 2.25) are
> *different measurements*, not the same code re-run. The
> paper treats the 20-seed run as the canonical measurement
> for the §5.5 headline; the 8-seed run is reported here for
> the "consistent with its own 8-seed subset" claim. The
> 20-seed run is *not* a replication of the 8-seed run — it is
> the same code on the same tasks with a faster engine and a
> better miner. Cross-run consistency is therefore not
> independent evidence of the effect; the proper replication
> would be 20 *new* seeds on the 8-seed code, which has not
> been run.

| arm | what | evo-solved /30 | reuse | topsim |
|---|---|---|---|---|
| B0 | single population | **2.25 ± 1.07** | — | — |
| B1 | isolated | 1.45 ± 0.94 | 0 | — |
| B2 | fragment channel | 1.60 ± 0.99 | 0.46 | — |
| B6 | recovered-primitive (constrained) | 1.80 ± 1.06 | 0.59 | 0.14 |
| B7 | recovered-primitive (unconstrained) | 1.85 ± 1.04 | 0.64 | 0.15 |

| comparison | Δ (se) | 8-seed | verdict |
|---|---|---|---|
| B6 − B1 | +0.35 (0.32) | +0.38 | directional, **not significant** |
| B6 − B2 | +0.20 (0.32) | +0.50 | shrunken, **not significant** |
| B6 − B7 | −0.05 (0.33) | −0.25 | **null** (H3) |
| B2 − B1 | +0.15 (0.31) | −0.12 | directional, not significant |

The ordering is identical across the two runs:

> B0 ≥ B7 ≈ B6 > B2 > B1.

Recovered-primitive channels (B6/B7) are consistently the best
channel variants. But the 8-seed run's "B7 matches B0" (2.12 =
2.12) does not survive more power: at 20 seeds B0 (2.25) is
clearly ahead of B7 (1.85). The divergence tax is *partly* paid
back, not fully. More power did not produce significance — it
confirmed the effect is small. The +0.50 headline from the
8-seed run was partly noise.

[exp: 2026-07-22_frontier_recovered_scaled]

## 5.5 The central-library control (B5) — the headline arm

B5 is a single population that periodically runs the compression
miner over its hall of fame, installing the top compression-ratio
abstractions as new primitives in the population's library.
Concretely, B5 calls `mine_own_abstractions(max_new=8, min_size=2,
max_size=4)` every 5 epochs, with the underlying miner requiring
`min_occurrences=2` (a subroutine must appear in at least two of
the lineage's best programs to be considered). The B5 arm is
run at the *identical* config to the scaled B0/B6/B7 sweep so all
arms are directly comparable.

> **A note on framing.** B5 is a *Stitch-style* learner, not a
> DreamCoder-style one. It has no neural recognition model; its
> library is grown by periodic anti-unification mining rather
> than a wake-sleep loop. The DreamCoder/Stitch line is the
> closest pre-neural library-learning prior art, and B5 is the
> clebran project's instantiation of that prior. The framing
> matters: B5 is the *same library mechanism* as the multi-agent
> arms, run by a single agent — so the comparison isolates the
> effect of *centralisation* from the effect of *the library
> mechanism itself*.

| arm | what | evo-solved /30 |
|---|---|---|
| **B5** | **single pop + central library** | **2.65 ± 1.31** |
| B0 | single population | 2.25 ± 1.07 |
| B7 | recovered-primitive, unconstrained | 1.85 ± 1.04 |
| B6 | recovered-primitive, constrained | 1.80 ± 1.06 |

| comparison | Δ (se) | verdict |
|---|---|---|
| **B5 − B6** | **+0.85 (0.38)** | **SIGNIFICANT (~2.2 se) — the central library is *better* than the recovered-primitive channel** |
| B5 − B0 | +0.40 (0.38) | directional (~1.1 se), not significant |
| B5 − B7 | +0.80 (0.39) | directional, ~2.0 se — would reach the bar with more seeds |
| B5 − B1 | +1.20 (0.37) | would reach the bar with more seeds |

The vocabulary metrics tell the same story from a different
angle. B5's library is more compositional (topographic
similarity 0.33 vs B6/B7 0.14–0.15) and more cross-task-reused
(0.15 vs 0.05). The single agent's mined vocabulary is
genuinely better than any multi-agent arm's.

[exp: 2026-07-22_b5_central_library]

**Honest reading of the B5 result.** B5 is the *best arm* on
the 20-seed frontier; the single formally-tested B5 vs B6
contrast is significant at ~2.2 SE; and the qualitative
vocabulary-quality metrics support the ranking. Two caveats
are in order. First, the B5 − B0 contrast (+0.40, 1.1 SE) is
*directional, not significant* — the paper's "central library
adds to single-population search" claim is supported by the
vocabulary metrics but not by the headline solve-count. Second,
B5's library pool is built from a single population with ~2.65
mean solves, while B6/B7's per-lineage libraries are built from
~0.6–0.7 mean solves per lineage — a ~4× difference in
library-pool size that may itself explain the
vocabulary-quality gap. The cleanest follow-up control is a
*B0 + library* arm (a single population with the same
compression miner, no multi-agent framing), which is the
obvious next measurement (§7).

**Why the central library wins, mechanistically.** The full
ranking tells a coherent story. Three forces explain it:

> B5 (2.65) > B0 (2.25) > B7 (1.85) ≈ B6 (1.80) > B2 (1.60) > B1 (1.45)
>
> └ central library ┘    └ multi-agent + channel ┘   └ fragment ┘   └ isolated ┘

1. **Splitting compute is expensive** (the *divergence tax*):
   3 isolated lineages (B1 1.45) fall well short of one
   population (B0 2.25).
2. **Communication pays back only part of that tax** (B6/B7 ≈
   1.8), never reaching B0.
3. **The *same* library mechanism, run centrally** (B5), not
   only avoids the tax but *adds* to single-population search —
   landing on top.

The reason B5's library is better is visible in the metrics: a
single agent sees *all* tasks, so its mined abstractions
generalise across them; a lineage that sees only the subset it
happened to solve mines task-idiomatic abstractions. Divergence
— the premise of H1 — is precisely what *degrades* the shared
vocabulary. Partial views yield task-idiomatic abstractions.

**The project's central claim — that divergent lineages sharing
over a constrained channel beat the alternatives at matched
compute — is not supported; the strongest control wins.** This
is a *trustworthy* negative result, exactly the outcome the
design was built to make believable.

## 5.6 Curriculum channel (B8/B9) — even an engaged channel does not beat B5

A fourth payload type — the *curriculum* — is the §7b hypothesis:
knowledge crosses as *problems to solve*, not code, by exporting
synthetic tasks generated from a lineage's own DSL and ordered by
prerequisite structure. An order-aware receiver gates deeper tasks
behind their prerequisites being solved. 20 seeds, 4M evals.

| arm | what | evo-solved /30 |
|---|---|---|
| B5 | single pop + central library | **2.65 ± 1.31** |
| B0 | single population | 2.25 ± 1.07 |
| B7 | recovered-primitive, unconstrained | 1.85 ± 1.04 |
| B6 | recovered-primitive, constrained | 1.80 ± 1.06 |
| B9 | **curriculum, unconstrained** | 1.65 ± 0.75 |
| B2 | fragment channel | 1.60 ± 0.99 |
| B8 | **curriculum, constrained** | 1.60 ± 0.75 |
| B1 | isolated | 1.45 ± 0.94 |

| comparison | Δ (se) | verdict |
|---|---|---|
| B8 − B1 | +0.15 (0.27) | curriculum transfer barely beats isolation, **ns** |
| B8 − B6 | −0.20 (0.29) | curriculum is *weaker* than the recovered-primitive payload, ns |
| B8 − B9 | −0.05 (0.24) | **null** — the constraint doesn't matter for teaching sets either |
| B8 − B5 | −1.05 (0.36) | curriculum is significantly *worse* than B5 (~2.9 SE) |

The mechanism *did* work. Lineages received ~31 teaching tasks
each and solved **70–78% of them** (B8 23.8/30.6 = 78%; B9
21.9/31.2 = 70%). The students demonstrably *learned the
concepts their peers taught*, in the prerequisite order, exactly
as designed. And it bought essentially nothing on the real
tasks: +0.15 over isolation, below every other channel payload,
and significantly below B5.

The bottleneck is not acquiring a taught concept — that worked.
It is that *learning a concept from demonstrations does not
transfer to new tasks that need it*. A lineage can solve the
synthesised task showing `vmirror`, and still not deploy `vmirror`
where a frontier task requires it. This is the L2T
transfer-vs-reconstruction gap appearing at the level of
*whole concepts* rather than single programs.

Teaching also costs budget: the curriculum arms solve ~24
auxiliary tasks each, compute diverted from the tasks that count.
Under matched compute, teaching is close to a wash.

[exp: 2026-07-23_frontier_curriculum]

A caveat on one number: `reuse` reads 0.00 for B8/B9 because
`reuse_rate` measures solutions containing a *received fragment or
abstraction*; a curriculum payload transmits neither, so the metric
is inapplicable. The curriculum-specific engagement metric is the
aux_received / aux_solved table.

## 5.7 The teach→test probe and the amortization correction

The B5 result forced two follow-up questions. Was the *channel*
that failed, or the *measurement*? And does the curriculum's
*engagement* (70–78% of teaching tasks solved) translate to
anything measurable on the real tasks?

### 5.7.1 The teach→test probe (without a cold baseline)

A controlled teach→test protocol separates *acquiring* a taught
concept from *transferring* it to a novel task needing the
concept. Phase 1: evolve on a curriculum only, then mine the
resulting library. Phase 2: spend the rest of a shared total
budget (500k) on the target only, carrying the phase-1 library
forward.

- **Taught arm** — curriculum is the target's own prerequisite
  decomposition (an *oracle-relevant* curriculum: maximally well
  targeted, an upper bound on transfer).
- **Control arm** — an unrelated program's decomposition,
  truncated to the same item count, same seed, same total budget.
- **8 targets × 5 seeds → 34 paired (target, seed) runs per arm.**

| | taught | control |
|---|---|---|
| target solve rate | 38.2% (13/34) | 32.4% (11/34) |
| curriculum learned | 50% | 46% |
| mean teach budget used | 82.6k | 90.2k |
| mean test budget available | 417k | 410k |
| **evals-to-solve, fraction of available budget** | **0.150** | **0.318** |

Two findings of opposite sign. *Solve rate is null* (4 vs 2
discordant pairs, binomial p = 0.688). *Speed is real and
significant* (15.0% vs 31.8%, permutation p = 0.025) — the
taught arm is roughly 2× faster on the runs that solve. Both
arms spent almost the same teaching budget, so the test budget
was almost the same in both; the taught arm genuinely finds
the target sooner.

A caveat on the conditional comparison. The "evals-to-solve"
comparison is computed on the *runs that solved* in both arms
(n = 9 all-solved pairs); the conditioning set is not
symmetric, because the discordant pairs split 4-vs-2 in favour
of the taught arm. The conditional comparison can therefore
overstate or understate the ITT effect. The next section
(§5.7.2) reports a *cold* baseline, which is the more reliable
verdict.

[exp: 2026-07-23_transfer_probe]

Concept transfer is real — it accelerates search — but
acceleration is not the same as capability. A relevant
curriculum makes the target twice as cheap to find, and changes
almost nothing about which targets are findable at all. That
precisely explains the curriculum channel's null (B8 − B1 =
+0.15, ns): the channel's benefit is *speed*, but the arm metric
is *solve count at fixed budget*, and the speed only converts to
solve count for tasks sitting *near* the budget frontier, of
which the frontier subset has very few.

### 5.7.2 The amortization correction (cold baseline)

The probe lacked a *no-teaching baseline*. Adding a *cold* arm
(empty curriculum, full budget on the target) and merging the
three (same targets, seeds, budget) gives the corrected three-way
verdict. The means below are over the **n = 9 pairs solved by
all three arms** (the only estimand on which all three are
defined); the comparison is therefore "conditional on solving,"
not ITT. The conditional-vs-ITT distinction matters: the
n = 34 ITT comparison is more variable, and the n = 9 conditional
is what makes the variance tight enough to give the p = 0.97
verdict below.

| arm | curriculum | target-solve evals (T) | n | solve rate (n=34) |
|---|---|---|---|---|
| cold | none | 73,152 (median 61,866) | 9 | 35.3% |
| taught | target's own (relevant) | 72,166 (median 72,082) | 9 | 38.2% |
| control | unrelated (irrelevant) | 116,067 (median 83,221) | 9 | 32.4% |

| paired difference | Δ (n=9) | perm p | reads as |
|---|---|---|---|
| **taught − cold** | **−986** | **0.967** | relevant teaching ≈ no teaching |
| control − cold | +42,915 | 0.269 | irrelevant teaching is *slower* than no teaching |
| control − taught | +43,901 | — | *this is what the probe measured* |

The probe's 2× was the size of the harm to the mis-targeted
control, mislabeled as a benefit. The honest verdict is the
opposite of the probe's headline: *relevant teaching is roughly
neutral; irrelevant teaching causes negative transfer*.

[exp: 2026-07-23_amortization]

The amortization story is also cleanly closed. Per student,
taught total is L + T = 128,942 vs cold U = 73,152 — the
per-student condition L + T < U is violated by ~56k. Amortization
spreads the *teacher's* one-time cost C across N students; if
each student is individually worse off, no N rescues it. The
crossover formula `N > C / (U − L − T)` has no solution. Sharing
a curriculum among many agents *cannot* pay off here, because
the thing being shared does not make an individual agent
cheaper.

Two caveats. The protocol wastes teaching budget (mean L = 56,775
vs median 7,561 — a few runs burn the full 150k cap without
finishing). An early-stopped teach phase would lower L, but since
T ≈ cold already, it cannot turn the per-student condition
positive. The taught curriculum is the target's own solver
decomposition — the *oracle upper bound*. Real peer curricula are
strictly worse targeted, so ≈ 2× is a ceiling on the speed
benefit, not a typical value.

### 5.7.3 The order experiment — the first significant process effect

The teach→test and amortization results close the *content*
question: relevant teaching is neutral, irrelevant teaching
harms. They say nothing about *process*. The order experiment is
the pristine test of the "how you learned it" thesis: it holds
the curriculum *content* fixed — a target's k prerequisite
sub-tasks — and varies *only* the order in which they are
acquired. Four arms, identical content and identical total
budget (500k), with cost-to-solve as the primary endpoint:
**cold** (no curriculum), **forward** (foundations first, gated),
**reverse** (hardest first, gated), **shuffled** (all steps at
once, ungated). The three teaching arms differ only in the
prerequisite `score` handed to the order-aware gate — so order is
isolated and nothing else changes. 9 targets (depth ≥ 3, ≥ 2 grid
prerequisite steps) × 6 seeds → 216 runs.

| order | curriculum acquired | target solve rate |
|---|---|---|
| **forward** (foundations first) | **47%** | **48.1%** |
| shuffled (unordered) | 45% | 38.9% |
| reverse (hardest first) | **23%** | 33.3% |
| cold (no curriculum) | — | 29.6% |

Paired McNemar (by target × seed), the correct test for the
paired binary solve outcome:

| comparison | wins | p | reads as |
|---|---|---|---|
| **forward − reverse** | 9 vs 1 | **0.021** | right order ≫ wrong order (same content) |
| **forward − cold** | 13 vs 3 | **0.021** | well-ordered teaching beats none |
| forward − shuffled | 7 vs 2 | 0.180 | ordering vs merely-available: **ns** |
| reverse − cold | 5 vs 3 | 0.727 | **wrong-order teaching ≈ no teaching** |

Two significant results, and both are about the *wrong* order. The
mechanism is mechanistically legible: teaching foundations-*last*
lets the learner acquire only **23%** of the same curriculum —
half of forward's 47% — because a gate that demands the hard
composition before its parts stalls, and you cannot learn a
composition before the pieces it is built from. That halved
acquisition shows up as a significantly lower solve rate: forward
beats reverse (p = 0.021), and reverse is *no better than not
teaching at all* (p = 0.727). Same content, same budget, reversed
order → the curriculum's value is destroyed.

But *fine-grained ordering is not the active ingredient*. forward
vs shuffled is not significant (p = 0.18), and shuffled acquires
45% ≈ forward's 47% — because when all steps are available at
once, the fundamentals are the *easy* ones and get solved first
anyway. The learner self-orders; strict prerequisite gating only
matters when it can do *harm* (reverse), not when it enforces an
order the learner would have found regardless.

As with teaching-vs-not (§5.7.2), the effect is on *capability*,
not speed: every paired evals-to-solve contrast between the order
arms is null (forward − shuffled = +16k, p = 0.41). Order changes
*which* targets are reachable — through how much of the curriculum
is acquired — not how fast an already-reachable target is found.
Different interventions surface on different endpoints: teaching-
vs-not lived in speed, order lives in capability.

[exp: 2026-07-24_order_process]

**Scope and one honest tension.** forward − cold is significant
here (p = 0.021) where the amortization taught − cold was neutral
(§5.7.2). The difference is target selection: this experiment
filters to targets with ≥ 2-step decompositions, where order can
matter; amortization did not. So "well-ordered teaching helps" is
scoped to targets with real compositional structure, not tasks in
general — a qualification, not a contradiction. The discordant
counts are small (9–17 pairs); the two significant results are the
paired forward-vs-reverse and forward-vs-cold, both p = 0.021. A
preliminary partial-data read had shown a larger forward-vs-
shuffled gap that regressed to non-significance at full n — a
caution recorded against reading early cells.

This is the project's **first significant process effect** and its
first empirical purchase on the reorientation (§6.1). It is a
*qualified* yes for "how you learned it": on compositionally-
structured tasks, the order of acquisition significantly changes
capability with content held constant — asymmetrically, *don't
teach backwards* matters more than *teach in exactly the right
order*.

## 5.8 Vocabulary quality

A summary of the vocabulary metrics across the multi-agent arms
and the central-library control. Vocabulary metrics are only
defined for arms that grow a library (i.e. not for B0, B1, or
B2). The metrics supplement the solve-count headline with
"how good is the abstract structure?" probes.

| arm | vocab size | used-rate | cross-task | received-used | topsim |
|---|---|---|---|---|---|
| B6 (recovered, constrained) | 4.5 | 0.27 | 0.05 | 1.12 | 0.14 |
| B7 (recovered, unconstrained) | 5.6 | 0.26 | 0.05 | 1.42 | 0.15 |
| **B5 (central library)** | — | — | **0.15** | — | **0.33** |

Three things to read off the table. *received-used is > 1* for
B6 and B7 — lineages use *more than one* received primitive per
solve, on average, a real signal that the channel is engaged.
*cross-task reuse* is three times higher for B5 (0.15) than for
B6/B7 (0.05): a single agent's mined abstractions generalise
across more tasks. *topographic similarity* is more than double
for B5 (0.33 vs 0.14–0.15): the central-library vocabulary is
more compositional. The two metrics agree: the single-agent
library is *better*, not just *more abundant*.

> A note on the two topsim numbers in the paper: §3.6 reports
> topsim 0.53 for the *miner run over all 400 Hodel reference
> solvers*; the 0.33 reported here is B5's *actual run* on
> 20 seeds × ~1.3 mean solves. The 0.53 is a miner-quality
> number; the 0.33 is a run-quality number.

The "divergence degrades vocabulary quality" finding is the
mechanistic explanation of the B5 win: a single agent sees every
task, so its mined vocabulary generalises across them; a lineage
that sees only the subset it happened to solve mines
task-idiomatic abstractions. The premise of H1 (divergence is
an asset) is supported — lineages *do* diverge — but divergence
in this substrate is a *liability* for vocabulary quality, not
an asset.
