# 02 — Narrative and clarity review

*Reviewer: general-purpose narrative pass. Audience assumed: a NeurIPS/ICML/Evolutionary Computation reader who knows program synthesis, library learning, and emergent communication, but has never seen the clebran project.*

The paper is unusually well-built for a first draft. The headline is sharp, the rig is real, and the falsification framing is consistent. What follows are the places where the *story* still fights the *story-telling* — the structural choices that make a reader's first 60 seconds harder than they need to be, or that cause a careful reader to find the ending three times before the paper has finished setting it up.

---

## Top 3 narrative issues

### 1. The headline is spoiled before §5.6, and then §5.6 is reported again as a "headline" section
**`paper/05-results.md:187-237` (the curriculum channel section) and `paper/05-results.md:239-302` (the central-library control).** The B5 result is reported twice in §5 with the same table and the same headline number. §5.5 ("Curriculum channel") opens with an 8-arm table that already has `B5 (single pop + central library) ... **2.65 ± 1.31**` bolded at the top — a paragraph before §5.6 announces itself as "the decisive experiment" and prints the same table again. The reader has already seen the winning row in §5.5; §5.6 then re-presents the table under the heading "the decisive comparison" and the framing "B5 is a single population that periodically mines its own solutions ... It is a DreamCoder/Stitch wake-sleep learner with no multi-agent divergence and no channel." That is the *introduction* to B5 — the framing that should have appeared *before* the curriculum table — placed after the spoiler.

The §5.9 subsection ("What the headline looks like in one place") is itself a self-diagnosis: the author knows the headline is hard to find, so they wrote a third copy of it.

**Fix.** Two options, in increasing order of disruption. (a) Restructure §5 so B5 is *introduced* in §5.5 with a forward reference ("we report B5 alongside the curriculum channel for context; the central-library control is presented in §5.6 as the decisive comparison") and have §5.5's table *exclude* B5 — or include it but un-bolded. (b) Restructure the section order: §5.1–§5.4 (first test → reachability → dose-response → recovered-primitive) stay; §5.5 becomes the central-library control; §5.6 becomes the curriculum channel framed as "B5 is so good that even the curriculum channel — whose mechanism *does* work — cannot beat it"; §5.7 stays as the teach→test probe. This forces the "B5 was added late" honesty to be visible to the reader, but it gives the headline its due.

Either way, §5.9 should be deleted — its existence is an admission of failure in the section ordering, not a feature.

### 2. The reorientation is previewed in three places before the reader reaches §5
**`paper/00-abstract.md:45-54`, `paper/01-introduction.md:60-114` (§1.2), and `paper/01-introduction.md:116-141` (§1.3).** The abstract already names "the paper's contribution is therefore a falsification plus a reorientation" and lists the capability audit. §1.2 ("What the experiment found") gives the full ranking, the B6 − B5 = −0.85 comparison, the teach→test probe, and the cold-baseline correction — *everything* in §5.7 — in 60 lines, before the reader has seen any data. §1.3 ("The reorientation") states the reorientation as if it were a fact about the data, not a conclusion to be drawn from them.

For a falsification paper, this is a real cost. The dramatic structure of the paper is: "We expected X. We built a rig strong enough to be trusted if X failed. X failed. Here is what that means." The reorientation is the *punchline*. Announcing it in the abstract and then previewing the teach→test and the cold-baseline correction in §1.2 means the reader has heard the punchline before the experiment is run.

**Fix.** Move the full ranking out of §1.2 — leave only the qualitative claim ("the multi-agent arms are not better than the strongest single-agent baseline") and a forward pointer to §5.6. Move §1.3 to a one-paragraph "preview of the reorientation" and reserve the full statement for §6.1, where it is *earned* by §5. The capability audit can still be advertised in §1.4 (it is genuinely a contribution), but the *reason* the audit is needed — the data — should be §5's job to deliver.

### 3. §3 (the technical design, 14k chars) is positioned before §4 (the methods, 8k chars)
**`paper/03-design.md:1-280` and `paper/04-methods.md:1-164`.** The reader is asked to absorb 14k characters of typed-IR, interpreter design, GP operators, fitness, channel payloads, and compression-miner details before they know what the experiment *tests*. The hypotheses, the arm table, the matched-compute protocol, the statistics, and the subsets are all in §4, which comes second. The README itself notes "consult §3 when a specific design choice is in question" — that is a reference-section reading order, not a paper-section reading order.

This matters especially because the paper *uses* §3 in two roles: as a technical reference (which is where it belongs) and as the implicit evidence that the rig is trustworthy (which is what §1, §4, and §6 are supposed to do). Currently the rig's trustworthiness is in §6.3 and §4.3, but the rig's details are in §3, *before* the rig's role is stated.

**Fix.** Three options. (a) Move §3 to an appendix, and reduce §3.7 ("what it took to pass the Stage-1 gate") to a paragraph in §4.1 or §6.3. (b) Keep §3 where it is but reduce it to the *specification* of the rig (what each component does, no debugging history), and move the Stage-1 gate fixes to §6.3 as evidence the rig is reliable. (c) Reorder: move §4.1 (hypotheses) and §4.2 (arm table) to the front of §4, with §3 following as a reference. The current ordering is a research-log ordering, not a paper ordering.

---

## Section-by-section notes

### §0 Abstract
The abstract does the right structural work — contribution → falsification → reorientation → rig — but it is dense. The first sentence is a literature hook ("a common hypothesis in emergent communication is that...") where the paper's hook ("a single agent with a central library beats every multi-agent arm") would land harder. "Baselines are strong enough that a null result is trustworthy" (line 13) is one of the paper's best lines, but it appears in the *second* paragraph, after a 12-line description of the setting. The "B5" notation is introduced without the arm-table being in reach; the reader has to take on faith that "B5" is "a single agent that grows a central abstraction library." The "two failures" framing (lines 34-43) packs a 78%, a 56k, a 2×, a "neutral on capability, harmful on mis-target," and a "no amortization configuration that flips the sign" into ten lines. Trim: the per-arm B-numbers, the topographic-similarity and cross-task numbers, and the §11/§7b labels can be deferred. Keep: the B6 − B5 = −0.85 line, the 78% line, and the 56k line.

### §1 Introduction
The strongest section in the paper. §1.1 ("the clebran hypothesis") is a clean 3-paragraph statement of the H1/H2/H3 structure with the right amount of detail. §1.2 ("What the experiment found") is comprehensive — too comprehensive, see issue #2. §1.3 ("The reorientation") is a strong *preview* but loses the chance to be a strong *delivery*. §1.4 ("Contributions") lists six concrete contributions; the abstract advertises two (falsification + reorientation); §1.3 introduces a third (the audit). Mismatch: the contributions should be presented in the same number and shape as the abstract's claim, or the abstract should match the contributions. §1.5 ("Outline") is fine.

Two small wording issues: the H3 description at line 40 says "a *bandwidth-limited* channel preserves better abstractions than an unconstrained library-dump" — but the experiment finds the *opposite* (or rather, a *null*), so the negative result is implicit in the framing. The reader is given a yes/no question and the answer is "no, but for a more interesting reason than the question anticipated"; that nuance is lost if the hypothesis is stated too crisply.

### §2 Related work
The 6-subarea structure is honest but the section is almost as long as §1 (11.5k vs 10.7k). §2.4 (L2T/NEO) is the deepest and does the most work — the four-point summary of L2T ideas is the paper's strongest positioning. §2.6 (curriculum learning) introduces 6 different works (Zhu, Liu, Garcia-Piqueras, Portelas, Narvekar, PAIRED, ACCEL, POET, Sukhbaatar) in a single subsection; a reader who doesn't already know PAIRED/ACCEL is going to skim. §2.3 (emergent communication) introduces the topographic-similarity metric, which is then used in §1.2, §3.6, §5.6, and §5.8 *before* the reader gets back to the definition. Move the metric definition to a forward-reference note in §1.1, or move §2.3 to be §2.1.

### §3 Design
Long, detailed, and reads as a technical reference — which is what it is, but the *paper* wants it to do double duty as evidence the rig is real. §3.5 (channel and four payloads) is the densest part and introduces the "§11" and "§7b" project labels that the reader has to learn. §3.6 (compression miner) is short and good. §3.7 ("What it took to pass the Stage-1 gate") is the most interesting part of the section and is *misplaced* — it is a debugging narrative, not a design specification, and it would land better in §4.1 (as evidence the rig is reliable) or in §6.3 (as evidence the null is trustworthy). The "each fix is identical across arms" closing (line 281) is a great point and belongs somewhere more prominent.

### §4 Methods
Clean. §4.1 states the hypotheses clearly, including the late-arriving B5 control. §4.2's arm table is the right artefact but appears *after* B-numbers have been used in the abstract, §1.2, and §3.5 — a forward reference to "see §4.2 for the arm table" in those earlier sections would help. §4.3's match-compute protocol is detailed enough to be reproducible. §4.4's two-subsets story is well-motivated. §4.5's statistics section is honest about the small-n case (no t-test, standard error is descriptive not a p-value). §4.6 ("What the experiment does *not* test") is a limitations list that duplicates content from §7 — either merge it into §7 or keep it as a *forward* declaration but rename it to avoid the limitation overlap.

### §5 Results
The heart of the paper, and the place with the most structural confusion. The order "research-log order" is honest but fights the headline-first principle. B5 appears in §5.5's table (line 197) before §5.6 is announced. The 20-seed recovered-primitive data appears in §5.4 (line 154-185) and then is partially repeated in §5.5 (which is technically a different table — the curriculum channel table — but uses the same 20-seed B0/B6/B7 numbers). §5.7.1 and §5.7.2 are a "we corrected our own error" pair that requires the reader to track three arms (taught, control, cold) and two metrics (solve rate, evals-to-solve); the payoff is real but the path is dense. §5.7.3 ("in progress") takes half a page for a 67-row pilot — either move to "future work" or cut to two sentences. §5.8's vocabulary table has three rows of em-dashes for B0/B1/B2 because the data isn't collected; a one-line note ("vocabulary metrics are only defined for arms that grow a library") would be cleaner. §5.9 should not exist.

### §6 Discussion
§6.1 re-tells the reorientation rather than discussing it — by the time the reader reaches §6.1, they have the reorientation from the abstract, §1.2, §1.3, and §5.7. §6.1 should *interpret* the reorientation (e.g., "what would the project look like if the reorientation is right?") rather than narrate it. §6.2 (divergence tax) is a strong name and a clean argument. §6.3 (measurement) is the paper's most important meta-claim and is well-delivered, but the "cold baseline is non-negotiable" lesson (lines 146-154) deserves to be lifted to a paper-level methodological contribution in §1.4. §6.4 conflates two things — the scope of the result ("good for / never for") and the capability audit — and would be cleaner as two subsections. §6.5 ("What this means for related literatures") is largely a re-statement of §2 with the data added; cut it to one paragraph in §6.1, or cut §2 to a stub and let §6.5 do the work.

### §7 Limitations
Honest, well-organised, and appropriately scoped. The "no statistical power analysis" admission (line 82) is unusual and welcome. The "honest reporting of nulls" closing (line 109) is the right note to end on. The overlap with §4.6 is the only structural issue — pick one place for the "what the experiment does not test" list.

### §8 Conclusion
Restates the falsification (good), the reorientation (fine, but the third telling), and three open work items (good — but items 1 and 3 are also in §6.4 and §1.4). The "the negative result is the paper's contribution" closing is the right line for a falsification paper. The 6-bullet re-statement of the headline (lines 9-19) is a bit long for a conclusion's opening paragraph; the contribution list in §1.4 already has this material.

---

## Headline and abstract

Three most important changes to the abstract:

1. **Open with the paper's hook, not the literature's.** Replace the first sentence ("A common hypothesis in emergent communication is that bandwidth-limited channels between divergent agents force compositionality and so improve transfer.") with the paper's claim ("We test whether bandwidth-limited channels between divergent agents force compositionality and so improve transfer — and find that, on ARC program synthesis at matched compute, they do not."). The current opening makes the reader wait 12 lines for the headline.
2. **Move "baselines are strong" and the headline number to the first paragraph.** The current abstract's second paragraph has the headline at line 22; the first paragraph can be cut to 3-4 lines (the hypothesis, the setting in one sentence, the headline). Lines 11-16 ("Baselines are strong enough that a null result is trustworthy: a single population with the same total compute, an isolated-lineage ensemble, an unconstrained library-dump channel, and — critically — a *single agent that grows a central abstraction library*") should move up.
3. **Trim the per-arm B-numbering and the secondary numbers.** The abstract currently lists 9 B-numbers, 4 Jaccard/topographic/cross-task numbers, and the §11/§7b labels. A reader at 60 seconds does not need B0/B1/B2; "single population, isolation, fragment channel, recovered-primitive channel, curriculum channel" is enough. The topographic similarity and cross-task numbers can be one line ("the single agent's mined library is more compositional and more cross-task-reused than any multi-agent arm's") without the specific values.

A concrete suggested first paragraph (target: 5-6 lines):

> We test a popular hypothesis from emergent communication — that bandwidth-limited channels between divergent agents force compositionality and so improve transfer — on a deliberately small, fully-instrumented substrate: typed programs evolved under pure reward on a 30-task frontier subset of ARC-AGI-1, with matched candidate-evaluation budgets audited to 0.10% spread across 20 seeds. The baselines are strong enough that a null is trustworthy: a single population with the same total compute, an isolated-lineage ensemble, an unconstrained library-dump channel, and — critically — a single agent that grows a central abstraction library (a DreamCoder/Stitch control). On this substrate, the central-library control significantly outperforms every multi-agent arm: the single significant comparison in the entire study is **B6 − B5 = −0.85 (~2.2 standard errors)** — sharing a discovered vocabulary between divergent agents is not just no better than letting one agent keep the vocabulary, it is *significantly worse*.

Then a second paragraph on the falsification (H1 supported, H2/H3 null, the divergence-is-a-liability finding, the vocabulary metrics in one line), and a third on the reorientation (the teach→test probe, the cold-baseline correction, the 56k gap, and the capability audit as the next open thread).

---

## One-line summary

**The most important change to the story is structural, not verbal: move the B5 (central-library) headline from §5.6 to §5.5, frame §5.6 as "even the curriculum channel — whose mechanism actually works — cannot beat it," and delete §5.9.** The current ordering reports the headline three times, the first time as a spoiler in the curriculum table. A single placement of the headline — at the top of the first subsection where B5 is *introduced* as a control — would let §5.6 do the work of *interpreting* the headline (the divergence tax, the vocabulary-quality mechanism) rather than re-presenting it.
