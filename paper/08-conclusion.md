# 8. Conclusion

We set out to test whether divergent populations of DSL programs
on ARC-AGI-1, exchanging successful subroutines through a
constrained channel, would beat the alternatives at matched
compute. The experiment delivered a falsification. On a 30-task
frontier subset at 4M candidate-evaluations per run, with audited
compute spread of 0.10%, the single significant comparison in the
entire study is **B6 − B5 = −0.85 (~2.2 se)**: a single
population that grows a central abstraction library from its own
solutions (a DreamCoder/Stitch-style learner) is significantly
better than the recovered-primitive channel between divergent
populations. Every multi-agent arm lies between isolation (worst)
and the central library (best). The constraint-versus-unconstrained
comparison is null across all four payload types, because adaptive
operator selection self-regulates a failing channel. H1 is
supported — lineages do diverge — but divergence in this substrate
is a *liability* for vocabulary quality, not the asset the
hypothesis assumed.

The result is meaningful only because the baselines are strong.
The match-compute protocol audits each arm's recorded candidate-
evaluations to the per-arm budget; the per-task RNG substream
scheme makes single-task probes predict full-run behaviour; the
deterministic interpreter and the 399/400 reference-solver
reproduction gate make every evolved program auditable. The
power check (8 → 20 seeds, 3M → 4M evals) confirmed the effect is
small rather than a near-miss on significance.

A controlled teach→test probe then forced a reorientation of the
question. A relevant curriculum makes a target ≈ 2× cheaper to
find, but does not expand what is solvable; an irrelevant
curriculum causes negative transfer. With a *cold* baseline
(no curriculum) added, the honest verdict is the opposite of the
probe's headline: relevant teaching is roughly neutral, irrelevant
teaching hurts, and the per-student condition L + T < U fails
by ~56k — a number no amortisation across N agents can rescue.
The teaching's benefit lives in *evals-to-solve*, not in solve
count, and is invisible under the standard endpoint at a budget
frontier with few marginal tasks.

The reorientation is therefore from "does communication raise
skill?" to "does the *way* a system learns change how well it can
use what it learned?" That is the question Chollet's *On the
Measure of Intelligence* argues is the right one. The clebran
substrate has *measurement* as its asset, and the reorientation
requires capabilities it does not yet have: self-directed
practice, active choice of what to practise, retention without
rigidity, compositional generalisation, generalisation to
genuinely unseen tasks, meta-learning, and reflection on *how*
something was learned. The capability audit is a "what would
have to be true?" list; the substrate is currently missing most
of the rows.

Three open work items are the most directly productive.

1. **The order experiment (§5.7.3).** A pristine test of
   "how you learned it" varies only the *order* of acquisition
   with content held constant. A 67-row pilot on 3 targets
   shows forward > reverse > shuffled > cold on solve rate;
   finishing the seed count and writing it up is the cheapest,
   most directly publishable unit of work on the table.

2. **9a: make cost the primary endpoint everywhere.** Re-score
   every existing log on evals-to-solve + evals-per-solve. The
   data is already in the JSONL; it is an analysis pass, not
   new compute. Expect several prior nulls to wake up. Add the
   column to `metrics/report.py` and the frontier analyser.

3. **9b: point `clebran.curriculum` inward (dreaming).** The
   task generator already exists and is only ever pointed
   outward. After solving, a lineage could generate variants
   of its own solutions, train on them, and measure (a)
   vocabulary quality (topsim, cross-task reuse) and (b)
   whether later solves get cheaper. This is the single most
   implementable big missing capability.

The negative result is the paper's contribution. It is what the
clebran design's baselines were built to make believable, and it
is the result that any future work in the area has to address.
The "how you learned it" reorientation is the project's open
thread: the metric exists, the experiment is writable, and the
question is sharper than the one we set out to ask. The clebran
substrate — its measurement rig, its compression miner, its
linear IR, its deterministic interpreter, its track record of
reporting nulls — is the asset that lets the reorientation be
made operational.
