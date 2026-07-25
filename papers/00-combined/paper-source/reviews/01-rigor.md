# 01 — Scientific rigor review

*Reviewer: general-purpose rigor pass. Cross-checked against the
experiment READMEs in `experiments/2026-07-*` and the
project-level `FINDINGS.md`. Audience: a careful reader who
already knows the headline and is checking whether the statistics
support it.*

The paper's headline is a *falsification* — the most defensible
kind of negative result to publish — and most of the rig is real.
The matched-compute audit at 0.10% spread, the deterministic
interpreter, the 399/400 Hodel reproduction gate, and the
self-corrected transfer-probe / amortization sequence are all
strong pieces of scientific hygiene. The problems below are
concentrated in (a) places where the prose claims more than the
numbers support, (b) places where the discussion reads the
multi-agent ranking as if every pairwise contrast had been
tested, and (c) one place where the abstract directly contradicts
the paper's own §5.7.2.

---

## Top 3 issues

### 1. The abstract directly contradicts §5.7.2 on the central "≈ 2× cheaper" claim

`paper/00-abstract.md:39-43` says: "an honest re-scoring on
**cost-to-solve** (evals-to-solution) rather than solve count
reveals that a relevant curriculum makes a target ≈ 2× cheaper
to find but does not expand what is solvable."

`paper/05-results.md:373-376` (§5.7.2) says the opposite: "The
probe's 2× was the size of the harm to the mis-targeted control,
mislabeled as a benefit. The honest verdict is the opposite of
the probe's headline: *relevant teaching is roughly neutral;
irrelevant teaching causes negative transfer*." The
amortization-experiment README
(`experiments/2026-07-23_amortization/analysis.txt`) reports
**taught − cold = −986 evals, p = 0.97** — i.e. no speedup
against a no-curriculum baseline.

The 2× number is *taught vs control (irrelevant curriculum)*, not
*taught vs cold*. Once the cold arm is added, the relevant
curriculum gives ~zero evals benefit and ~6% solve-rate benefit
(13/34 vs 12/34, 38.2% vs 35.3%, ns). The abstract's "≈ 2×
cheaper" reads as taught-vs-cold and is wrong. §1.2 line 99
("a relevant curriculum gives no target-solve speedup") is
correct; the abstract should match §1.2.

**Fix.** Replace lines 39-43 of the abstract with: "An honest
re-scoring on cost-to-solve reveals that the *probe's* apparent
2× speedup was the size of the harm to a mis-targeted control;
against a *cold* (no-curriculum) baseline, a relevant curriculum
is roughly neutral (taught − cold = −986 evals, permutation p =
0.97), while an irrelevant curriculum is *slower* than no
teaching at all. The per-student condition L + T < U fails by
~56k evals, so no amortisation across N agents can rescue it."
The next paragraph of the discussion (§6.3) already makes this
point; the abstract just hasn't been re-aligned with it.

### 2. "B5 significantly outperforms every multi-agent arm" — but only B5 vs B6 is tested

`paper/00-abstract.md:19-20`: "the central-library control (B5)
significantly outperforms every multi-agent arm."

`paper/05-results.md:249-263` reports the B5 vs B6 contrast as the
*only* formal pairwise test against B5 (Δ = −0.85, se 0.38, ~2.2
SE). The other contrasts against B5 — B5 vs B7, B5 vs B2, B5 vs
B8, B5 vs B9, B5 vs B1 — are not computed anywhere in the paper
or the experiment READMEs. From the table at `paper/05-results.md:249-258`,
B5 − B7 = +0.80 and B5 − B1 = +1.20, both clearly large in
absolute terms, but with se's near 0.40 (B5 sd = 1.31, B7 sd = 1.04),
those are ~2.0 SE and ~3.0 SE respectively — so some of them would
presumably be significant and some not, and the reader has no way
to tell from the paper as written.

The abstract's claim is *almost certainly true in fact* — the
B5 row sits a full standard deviation above every other arm —
but the paper's statistics section (paper/04-methods.md:120-145,
§4.5) is explicit that "significant" is reserved for contrasts
that have been reported with an SE. The abstract then makes a
claim that contradicts that convention.

**Fix.** Two options. (a) Compute and report the B5 − B7, B5 − B2,
B5 − B8, B5 − B9, B5 − B1 contrasts with the same pooled-SE
formula (the data is already in the JSONL summaries), and report
which are above the 2 SE bar; tighten the abstract to whatever
is supported. (b) Soften the abstract: "the central-library
control (B5) sits at the top of the ranking, with a single
significant comparison against the recovered-primitive channel
(B6 − B5 = −0.85, ~2.2 SE); the other multi-agent arms are also
below B5 in mean, but only B5 − B6 has been formally tested."
This is the right framing for a paper whose statistics section
deliberately avoids p-values.

### 3. The discussion treats "central library" as a vindication, but B5 − B0 is itself not significant

`paper/06-discussion.md:83-85` (§6.2): "A central library
*avoids* the tax and *adds* to single-population search. B5
(2.65) > B0 (2.25) is the central insight of the experiment."

`paper/06-discussion.md:256-263` (§6.5): "For *library learning*,
the result is a clean vindication of the central library
mechanism."

`paper/05-results.md:263`: B5 − B0 = +0.40 (0.38), explicitly
flagged as "directional (~1.1 se), not significant." The "central
insight" and "clean vindication" framings are not warranted by
the only statistic the paper actually reports. The mechanism
claim in §6.2 ("B5's library is more compositional, more
cross-task-reused") is independently supported by the vocabulary
metrics, so the *qualitative* claim can survive, but the
quantitative ranking claim cannot.

This matters because the cleanest experimental isolation would
have been a "B0 + library" arm — a single population with the
*same* compression miner and library mechanism as B5, but no
multi-agent framing. That arm does not exist in the paper. As a
result, the B5 result is confounded between (a) centralization
(one agent vs three), (b) library pool size (B5 has more solved
programs to mine from than any single lineage), and (c) the
library mechanism itself. The paper cannot, with the arms it has,
say which of (a), (b), (c) drives the win.

**Fix.** Three coordinated changes. (a) Soften §6.2 line 84 and
§6.5 line 257: "B5 (2.65) > B0 (2.25) is a directional result
(1.1 SE, not significant) consistent with the library mechanism
adding to single-population search; the *qualitative* claim is
supported by the vocabulary metrics, but the *quantitative*
contribution of the library mechanism over plain single-pop
search is not statistically resolved at n = 20." (b) Add a
missing-control note in §7 or §4.6: a "B0 + library (no
divergence)" arm is the obvious follow-up that would isolate
the library mechanism from the centralization confound. (c) Note
that B5's library pool is built from a single population with
~2.65 mean solves, while B6/B7's per-lineage libraries are built
from ~0.6–0.7 mean solves per lineage — a ~4× difference in
library-pool size that may itself explain the vocabulary-quality
gap.

---

## Medium-priority issues

### 4. "Cross-run consistency is itself evidence" is not independent evidence
**`paper/05-results.md:177-178`**: "cross-run consistency is
itself evidence the direction is real even without per-comparison
significance." The two runs cited are the 8-seed run
(`2026-07-21_frontier_recovered`) and the 20-seed run
(`2026-07-22_frontier_recovered_scaled`). The 8-seed run is a
*subset* of the 20-seed run (same seeds 1–8, same code on the
same tasks, same config except engine and miner version) — the
runs are not independent. This is a "consistency with the
subsample" claim, not a "replication" claim. **Fix:** either rerun
on independent seeds, or soften the wording to "consistent with
its own 8-seed subset" and stop using "cross-run."

### 5. The §5.3 dose-response table reports total solves, not evolution-phase solves
**`paper/05-results.md:84-91`**: the dose-response table reports
"solved/30" (the README's analysis.txt confirms these are total
solves, not evolution-only). H2 and H3 are *defined* on
evolution-phase solves (the place where the channel can act);
the discussion in lines 92-103 reads as if those numbers are
evolution-only. The README's analysis shows evo-solved
`none 2.00 ± 1.00 → K2M1 2.00 ± 1.00 → K4M3 2.33 ± 0.58 →
K8M10 2.00 ± 1.00 → uncon 1.67 ± 0.58` — the *evolution*-only
ladder has a *larger* gap between the constrained middle and the
unconstrained tail (1.67 vs 2.33) than the total ladder shows
(10.00 vs 10.67). **Fix:** report evo-solved/30 in the table and
flag the larger unconstrained-evo-solved drop.

### 6. The §5.7.2 amortization analysis is on n=9, not n=34 — unflagged
**`paper/05-results.md:357-388`**: the three-way table reports
"target-solve evals (T)" and the per-student cost (L+T vs U).
The experiment's `analysis.txt` says "34 paired (target, seed)
runs; both arms solved in 9" — i.e. the L+T and U numbers are
*means over the 9 pairs that all three arms solved*. The
paper presents the means as if they were the primary endpoint
without flagging that the n=9 conditioning changes the estimand
from ITT (intention-to-treat) to "conditional on solving." For
the −986 taught-vs-cold number, this conditioning is what makes
the variance tight enough to give p=0.97; on the ITT sample the
comparison is more variable. **Fix:** add a row in the table
"n=9 (all-solved-by-all-three)" and an explanatory footnote.

### 7. The "78% solve rate on synthetic teaching tasks" abstract number is B8 only
**`paper/00-abstract.md:35-36`**: "students *learn* taught
concepts (78% solve rate on synthetic demonstrations of the
teacher's concepts)". B8 = 23.8/30.6 = 78%; B9 = 21.9/31.2 =
70% (`paper/05-results.md:212-214` and the curriculum README).
The abstract cites only B8's number. **Fix:** say "70–78% of
synthetic teaching tasks" or cite the constrained/unconstrained
split.

### 8. The §5.7.1 "2× speedup" is on a self-selecting subset, not ITT
**`paper/05-results.md:333-341`**: the evals-to-solve comparison
is reported "among runs that solved" — i.e. on the n=9
all-solved-by-both subset. The paper does say "Among runs that
solved" but does not discuss the selection bias: the *control*'s
solvers may be its easier wins (the 9 of 11 solves that the
control arm produced, minus 2 that the taught arm didn't solve)
while the *taught*'s solvers include its 4 that the control
didn't. The asymmetry of the 4-vs-2 discordant pairs means the
conditioning set is not symmetric. **Fix:** add a one-paragraph
caveat in §5.7.1 noting that the conditional comparison can
overstate or understate the ITT effect, and that the §5.7.2 cold
baseline is the more reliable verdict.

### 9. H3 is confounded with AOS, not just null
**`paper/05-results.md:99-103`** attributes the H3 null to AOS
self-regulation. But AOS was added during Stage 1 (§3.7 item 6:
"phase-1 fragment splice that poisoned 15% of offspring on needle
tasks: fixed by the AOS self-suppression of fragment splice") —
i.e. AOS is a *design choice* in the rig, not a measured
property of the learner. H3 (the information-bottleneck
hypothesis) is null in this design *because AOS was tuned to
neutralize the mechanism H3 would test*. The paper acknowledges
this in passing but does not flag it as a confound on H3. The
dose-response README
(`experiments/2026-07-20_b3_dose_response/`) is more direct: H3
is "effectively untestable" in this substrate because of AOS.
**Fix:** in §5.3 or §7, state that H3 may be untestable in this
design, not just null — i.e. the H3 question ("does a bandwidth
constraint preserve better abstractions than flooding") is not
asked cleanly because the channel's intake is already regulated
by AOS regardless of bandwidth.

### 10. "The library mechanism, run centrally, is genuinely useful" — but B5 − B0 = +0.40 (1.1 SE)
See issue #3 above. The §6.2 "central insight" framing and the
§6.5 "clean vindication" framing are both quantitatively
unwarranted. The library mechanism *may* be useful, but the paper
has not shown that with the arms it has. The cleanest follow-up
control is B0 + library, which is listed in `roadmap.md` but not
in the paper.

### 11. "Significant" is used both formally and informally in the same paper
**`paper/04-methods.md:131-137`** is careful: SE is descriptive,
the 2-SE bar is a heuristic, the paper does not use t-tests.
**`paper/00-abstract.md:22`** then says "the single *significant*
comparison ... is **B6 − B5 = −0.85 (~2.2 se)**" — using
"significant" in a way that suggests formal hypothesis testing
while §4.5 just disclaimed it. This is the same paper using
"significant" in two incompatible senses. **Fix:** either use
"the single comparison above the 2-SE bar" in the abstract, or
add a sentence in §4.5 saying "we use 'significant' colloquially
to mean 'above the 2-SE descriptive bar,' not in the formal
hypothesis-testing sense."

---

## Minor / nits

- **Line numbering inconsistency, §5.4 vs §5.8.** `paper/05-results.md:140-144` reports B6 received-used = 1.21, B7 = 1.42 (these are the 8-seed run numbers). The §5.8 table at `paper/05-results.md:425-426` reports B6 = 1.12, B7 = 1.42 (the 20-seed run). The 1.21 vs 1.12 difference for B6 is real (different miner, different seed count), but the paper doesn't flag that §5.4 is using 8-seed vocabulary metrics while §5.8 is using 20-seed. **Fix:** annotate which run each row is from.

- **Vocabulary size mismatch, §5.8 vs `analysis.txt`.** §5.8 table has B6 vocab = 4.5, B7 = 5.6; `experiments/2026-07-22_b5_central_library/analysis.txt` reports B6 = 4.77, B7 = 6.05. Minor — likely a rounding choice — but worth flagging.

- **B0 total solve discrepancy across runs.** §5.4 reports B0 = 2.12 ± 1.13 (8-seed run) and B0 = 2.25 ± 1.07 (20-seed run). The 0.13 difference between two B0 measurements is a *code-change* artifact (the 20-seed run uses the faster engine and the Stitch miner), not a random-seed effect. The paper does not flag this. **Fix:** add a one-line note in §5.4 that the 20-seed B0 is a different measurement (different engine), so the 8-seed and 20-seed columns are not directly comparable for absolute values.

- **The §5.4 "received-used" definition.** §5.4 line 138 calls it the "NEO-style 'used a primitive it was handed, never derived' signal." The metric is actually the *count* of received primitives used per solve (averaged), not a binary flag — so "the lineage used a primitive it was handed and never derived" describes a binary event, while the metric is a continuous count of such events per solve. **Fix:** clarify "average number of received primitives used per solve" on first use.

- **§5.7.1 "curriculum learned" undefined.** Line 330 reports "curriculum learned 50% (taught), 46% (control)" without defining the metric. The probe README says it is the fraction of curriculum items solved during phase 1; the paper should say so. **Fix:** one-sentence definition.

- **§3.5 conflation of CH-NONE with B1.** §3.5 line 188 says "CH-NONE (no channel at all; the B1 control)" — but B1 is *N isolated lineages with no channel*, which is related to CH-NONE but not identical. **Fix:** "CH-NONE: no messages are exchanged (the B1 condition with N lineages)."

- **§3.6 topsim 0.53 vs §5.6 0.33.** §3.6 line 249 reports the *miner*'s topographic similarity is 0.53 over arity-1 Grid abstractions (i.e. the output of running the compression miner over all 400 reference solvers). §5.6 reports B5's *actual run* has topsim 0.33. These are different (0.53 is a miner-quality number; 0.33 is a run-quality number on 20 seeds × 1.3 mean solves) but the paper doesn't flag the distinction. **Fix:** state the distinction once.

- **"3× faster engine" referenced but not isolated.** §3.2 line 59 reports the validator brought throughput "from ~2.8k evals/second/process to ~8.3k" — a real 3× speedup. But the 8-seed recovered run (engine ~2.8k/s, frequency miner) vs the 20-seed run (engine ~8.3k/s, Stitch miner) is a two-variable change. The paper attributes the cross-run effect to power ("more power did not produce significance — it confirmed the effect is small") but does not flag that *engine* and *miner* changed between the two runs. **Fix:** add one sentence in §5.4.

- **§4.4's "D3 is beyond reach" is a result, not a definition.** §4.4 line 117-118: "the pilot study that defined the frontier found that genuine evolution-phase solves occur only in D2 at 2M evals (seeds 1–2) — D3 is beyond reach and would just add a floor of zeros, so the frontier is depth-2-dominated." This is a *measurement* used to *define* the subset, and then the frontier subset is reported on as if it generalises. The reader is asked to accept that D3 is irrelevant because the pilot said so. **Fix:** in §4.4 or §7, note that "depth-2-dominated" is a *scope* statement, not a property of the design, and that the result may not generalise to deeper tasks where the divergence tax is larger (the FINDINGS.md already notes this).

- **B2 = 1.60 vs B2 = 1.65.** The §5.6 table at line 256 reports B2 = 1.60 ± 0.99; the B5 analysis.txt reports B2 = 1.65 ± 1.14 (a different *sample*? or rounding?). The 0.05 difference is small but if it's a sample difference it should be flagged. **Fix:** confirm whether the §5.6 B2 and the analysis.txt B2 are the same 20 seeds, and if not, which is canonical.

- **"B3 (10.4 = B1)" stage-1 verdict ignores evolution-phase.** §5.1 line 30: "B2 = B1 = 10.4/30, B0 = 10.6/30" — these are *total* solves, including phase-1. The H2 null on total solves doesn't tell the reader whether H2 is null on evolution-phase solves (the only place the channel can act). The README's verdict at line 26-32 of `2026-07-20_stage4_b0-b4_matched_compute/verdict.md` is careful to note the *test-exact* column shows 10.40 ± 0.55 for both B1 and B2 (so test-exact — which is evolution + post-evolution — is also null). The paper could be clearer. **Fix:** in §5.1, note that the total-solve null is corroborated by the test-exact column.

- **§6.4 "Good for / Never for" reads as overconfident.** The list at §6.4 lines 161-213 makes strong claims about what the result is good for and never for (e.g. "Amortising known competence ... what it lacks is the right distribution and the right setup"). For a falsification paper with a narrow substrate, this section overreaches. **Fix:** tighten the "Good for" list to one or two paragraphs and acknowledge that "good for" is currently a *prediction* from the data, not a measured property.

- **§6.5 "vindication" / "partial vindication" / "clean refutation" rhetoric.** The discussion in §6.5 uses "vindication," "clean refutation," and "partial vindication" as if these words were neutral. For a falsification paper whose central claim is "I falsified a hypothesis," the language of "vindication" in adjacent paragraphs reads as advocacy. **Fix:** rephrase "vindication" to "the result is consistent with" or "the data support."

---

## One-line summary

**The most important change is to fix the abstract's "≈ 2× cheaper" claim — it directly contradicts §5.7.2's "relevant teaching is roughly neutral" verdict and is the abstract's most-quoted number; the rest of the rigor issues follow from it.**
