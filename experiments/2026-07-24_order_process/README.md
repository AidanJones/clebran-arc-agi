# Order / process experiment — "how you learned it" (2026-07-24)

The purest test of the roadmap-9 reorientation: hold the **content** fixed (a
target's k prerequisite sub-tasks) and vary only the **order** of acquisition.
Result: **order matters — but at the extreme, not the margin.** Teaching the same
content in the *wrong* order (foundations last) is significantly worse than the
right order and no better than not teaching at all; fine-grained ordering beyond
"fundamentals available" does not significantly help.

## Setup

9 targets (depth ≥ 3, ≥ 2 grid prerequisite steps) × 6 seeds × 4 arms, matched
total budget 500k, teach cap 150k, **evals-to-solve as the primary endpoint**.
All three teaching arms share the *identical* curriculum; only the prerequisite
`score` (hence the unlock order) differs.
[analysis.txt](analysis.txt), [results.jsonl](results.jsonl).

- **cold** — no curriculum · **forward** — foundations first · **reverse** —
  hardest first · **shuffled** — all at once, ungated.

## Results (n = 54 per arm)

| order | teach budget | curriculum acquired | target solve rate |
|---|---|---|---|
| cold | 0 | — | 29.6% |
| **forward** | 109k | **47%** | **48.1%** |
| shuffled | 113k | 45% | 38.9% |
| reverse | 111k | **23%** | 33.3% |

**Paired (McNemar, by target × seed):**

| comparison | wins | p | reads as |
|---|---|---|---|
| **forward − reverse** | 9 vs 1 | **0.021** | right order ≫ wrong order (same content) |
| **forward − cold** | 13 vs 3 | **0.021** | well-ordered teaching beats none |
| forward − shuffled | 7 vs 2 | 0.180 | ordering vs merely-available: **ns** |
| shuffled − cold | 11 vs 6 | 0.332 | unordered teaching vs none: ns |
| reverse − cold | 5 vs 3 | 0.727 | **wrong-order teaching ≈ no teaching** |

Acquisition efficiency (paired evals-to-solve, tasks both arms solved): all
order-vs-order contrasts **null** (forward − shuffled +16k, p = 0.41).

## What it means

**The significant, mechanistically-explained finding is about the *wrong* order.**
Teaching foundations-last (reverse) lets the learner acquire only **23%** of the
same curriculum — half of forward's 47% — because you cannot learn a composition
before its parts, and a gate that demands the hard step first stalls. That
halved acquisition shows up as a significantly lower solve rate: **forward beats
reverse (p = 0.021), and reverse is no better than not teaching at all
(p = 0.73).** Same content, same budget, reversed order → the curriculum's value
is destroyed.

**But fine-grained ordering is not the active ingredient.** forward vs shuffled
is not significant (p = 0.18), and shuffled acquires 45% ≈ forward's 47% —
because when all steps are available at once, the *fundamentals are the easy
ones and get solved first anyway*. The learner self-orders. Strict prerequisite
gating only matters when it can do *harm* (reverse), not when it enforces an
order the learner would have found regardless.

**The effect is on capability, not speed.** Every evals-to-solve contrast is
null: ordering does not make an already-reachable target cheaper to find; it
changes *which* targets are reachable at all (via how much of the curriculum is
acquired). Different interventions surface on different endpoints — teaching-vs-
not showed up on speed earlier; order shows up on capability.

## Honest scope and a tension

- **forward > cold is significant here (p = 0.021)** where the amortization
  experiment found taught ≈ cold. The difference is target selection: this
  experiment filters to targets with ≥ 2-step decompositions (where order can
  matter); amortization did not. So "well-ordered teaching helps" is scoped to
  targets with real compositional structure, not tasks in general — an honest
  qualification, not a contradiction.
- Small discordant counts (9–17 pairs); the two significant results are the
  paired forward-vs-reverse and forward-vs-cold, both p = 0.021.
- Preliminary partial data had shown a larger forward-vs-shuffled gap that
  regressed to non-significance at full n — recorded as a caution against
  reading early cells.

## Verdict for the reorientation

A **qualified yes** for "how you learned it": on tasks with compositional
structure, the *order* of acquisition significantly changes capability with
content held constant — specifically, a dependency-violating order is
destructive and wastes the curriculum. What the data does **not** support is
that fine curriculum sequencing beats simply making the material available to a
learner that self-orders. The actionable takeaway is asymmetric: **don't teach
backwards** matters more than **teach in exactly the right order**. This is the
project's first significant *process* effect, and it points the next work
(9b dreaming, 9c cross-architecture) at learners rich enough that self-ordering
is not already this easy.
