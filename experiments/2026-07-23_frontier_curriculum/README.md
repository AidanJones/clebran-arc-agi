# Communication through curricula on the frontier (2026-07-23)

The first empirical test of the curriculum channel (roadmap 7b): lineages
communicate by **exporting synthetic tasks that show what they learned** —
knowledge crosses as *problems*, not code — with the teaching set decomposed
into prerequisite order (sub-abstractions first) and an order-aware learner
that gates deeper tasks until their prerequisites are solved.

## Setup

Frontier subset, matched compute 4M evals/run (audit 0.14%), 20 seeds,
evolution-phase solves. **B8** = constrained curriculum channel, **B9** =
unconstrained, compared against the existing arms at the identical config.
[analysis.txt](analysis.txt), [summaries.jsonl](summaries.jsonl).

## Results (evolution-phase solves, n=20)

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

## The mechanism worked. The transfer didn't.

This is the sharp finding, and it is not the usual "the channel never engaged":

| | messages published | teaching tasks received | **solved** |
|---|---|---|---|
| B8 | 1216 | 30.6 | **23.8 (78%)** |
| B9 | 2238 | 31.2 | **21.9 (70%)** |

Lineages **received ~31 teaching tasks each and solved ~three quarters of
them.** The students demonstrably *learned the concepts their peers taught* —
prerequisite-ordered, fundamentals first, exactly as designed. And it bought
essentially nothing on the real tasks (+0.15 over isolation, ns; below every
other channel payload).

So the bottleneck is **not** acquiring the teacher's concepts — that worked. It
is that **learning a concept from demonstrations does not transfer to new
tasks that need it.** A lineage can solve the synthesised task showing
`vmirror`, and still not deploy `vmirror` where a frontier task requires it.
That is a much more specific and interesting failure than "communication is
noise", and it is the L2T transfer-vs-reconstruction gap (spec §9) appearing at
the level of *whole concepts* rather than single programs.

It also has a cost: the curriculum arms spend real budget solving ~24
auxiliary tasks — compute diverted from the tasks that count — and recover only
+0.15. Under matched compute, teaching is close to a wash.

## Caveat on one number

`reuse` reads 0.00 for B8/B9 because `reuse_rate` measures solutions containing
a received *fragment or abstraction*; a curriculum payload transmits neither, so
the metric is inapplicable rather than zero. The curriculum-specific engagement
metric is the aux_received/aux_solved table above.

## Verdict

**Communication through curricula: mechanism confirmed, benefit null.** The
most substrate-agnostic payload — sharing problems rather than code, which was
meant to sidestep the "divergence degrades the shared vocabulary" failure the
B5 result exposed — engages fully and still does not beat isolation
significantly, does not beat the code-sharing payloads, and does not beat
concentrating compute. The constraint (H3) is null here too, now for the fourth
payload type.

The honest reading across the whole project: on ARC program synthesis at
matched compute, **every form of inter-lineage communication we built is
dominated by simply not dividing the compute** — and the specific reason
curricula fail is newly identified and worth pursuing: concepts are learnable
from demonstrations but do not transfer to novel tasks requiring them.
