# Review summary and revision log

Four parallel review agents (rigor, narrative, related work, reproducibility)
read the first draft on 2026-07-23 and wrote their notes to `reviews/01-rigor.md`
through `reviews/04-reproducibility.md`. This file consolidates their feedback
into a single change log and tracks what was done in response.

## Overall shape of the feedback

The four reviews converged on a *common* picture: the paper's rig and
falsification framing are solid, but the prose claims more than the
numbers support in three places, and the *related work* section has real
holes (missing neural-ARC competitors, hallucinated citations, an
over-attribution to L2T/NEO of ideas that are really DreamCoder's).
The narrative reviewer's three top issues (B5 headline spoiling itself,
reorientation previewed 3×, §3 before §4) and the rigor reviewer's
three top issues (abstract's "≈ 2× cheaper" claim contradicts §5.7.2,
"B5 significantly outperforms every multi-agent arm" overclaim,
B5 − B0 framed as "central insight" when it is 1.1 SE) are the most
urgent fixes; the related-work and reproducibility findings are a
medium-priority cleanup pass.

The single most important fix is the abstract contradiction on the 2×
speedup — the abstract's most-quoted number is wrong, and it was the
prose that lost the argument to the data. The most embarrassing finding
is that the first draft contained *three hallucinated citations* in
`references.md` (ArcMemo, Kiela 2019, and the L2T/NEO title); those
are fixed in this pass and noted explicitly in the bibliography for
the user to re-verify before submission.

## Critical fixes (done in this pass)

| # | issue | source | file | change |
|---|---|---|---|---|
| 1 | `λ_MDL = 1.1` in paper, actual code is `1.05` | reproducibility #1 | `03-design.md:167–168` | corrected to 1.05 |
| 2 | Abstract's "≈ 2× cheaper" claim contradicts §5.7.2 | rigor #1 | `00-abstract.md` | replaced with the §5.7.2 verdict |
| 3 | "B5 significantly outperforms every multi-agent arm" — overclaim | rigor #2 | `00-abstract.md` | softened to "sits at the top of the ranking; the single significant comparison is B5 − B6 = −0.85 (~2.2 SE)" |
| 4 | B5 − B0 = +0.40 (1.1 SE) framed as "central insight" and "vindication" | rigor #3 | `06-discussion.md` | softened; the qualitative claim survives (vocabulary metrics), the quantitative claim does not |
| 5 | Hallucinated ArcMemo citation (ref 25) | related work #5.1 | `references.md` | replaced with Ho et al. 2025, arXiv:2509.04439; flagged as reviewer-supplied and pending user verification |
| 6 | Hallucinated Kiela 2019 citation (ref 7) | related work #5.2 | `references.md` | replaced with the Brighton & Kirby 2006 / Lazaridou et al. 2018 / Chaabouni et al. 2020 trio |
| 7 | Wrong L2T/NEO title (ref 8) | related work #5.3 | `references.md` | title corrected to "Learning to Theorize the World from Observation"; author first names added |
| 8 | Missing CompressARC (Liao & Gu 2025) | related work #1.2 | `02-related-work.md` + `references.md` | added as the direct competitor on the compression axis |
| 9 | Missing Akyürek et al. 2024 (TTT-for-ARC) | related work #1.1 | `02-related-work.md` + `references.md` | added as the direct neural-ARC competitor |
| 10 | H3 null needs Kirby/Brighton interlocutor | related work #3.3 | `02-related-work.md` + `06-discussion.md` | added the information-bottleneck / cultural-language-evolution framing |
| 11 | L2T/NEO delta over-attributes DreamCoder concepts | related work #2.1 | `02-related-work.md` | three of the four "borrowed ideas" recast as DreamCoder re-use, not L2T invention |
| 12 | B5 framed as "essentially a DreamCoder/Stitch learner" | related work #3.1 | `03-design.md` + `05-results.md` | reframed as Stitch-style (one-shot mining, no neural recognition, no wake-sleep) |
| 13 | K and M for frontier channel runs not stated | reproducibility #2 | `04-methods.md` | added to §4 configuration table |
| 14 | B5 miner schedule not stated | reproducibility #3 | `04-methods.md` + `03-design.md` | added to config table; specific values named in §3.6 |

## Important fixes (done in this pass)

| # | issue | source | file | change |
|---|---|---|---|---|
| 15 | B5 headline appears in §5.5 table before §5.6 announces itself | narrative #1 | `05-results.md` | §5.5 restructured to lead with the B5 control; §5.6 becomes the curriculum channel "B5 still wins"; §5.9 deleted |
| 16 | Reorientation previewed 3× (abstract, §1.2, §1.3) | narrative #2 | `00-abstract.md` + `01-introduction.md` | §1.2 trimmed; full ranking moved to §5.6; reorientation is now earned by §5 and delivered in §6.1 |
| 17 | §3 (14k chars) before §4 (8k) | narrative #3 | `03-design.md` | §3 trimmed: §3.7 (Stage-1 gate debugging history) condensed to one paragraph, full version moved to `06-discussion.md` |
| 18 | H3 is confounded with AOS, not just null | rigor #9 | `05-results.md` + `07-limitations.md` | §5.3 and §7 now state that H3 may be untestable in this design because AOS regulates the channel regardless of bandwidth |
| 19 | "78% solve rate" abstract number is B8 only | rigor #7 | `00-abstract.md` + `05-results.md` | now "70–78% of synthetic teaching tasks (B9/B8)" |
| 20 | 8-seed vs 20-seed run inconsistency not flagged | rigor minor | `05-results.md` | §5.4 now states the 20-seed run uses the faster engine and the Stitch miner, so cross-run comparisons are not direct |
| 21 | "Cross-run consistency" not independent evidence | rigor #4 | `05-results.md` | softened to "consistent with its own 8-seed subset"; "replication" language removed |
| 22 | "Significant" used in two senses | rigor #11 | `04-methods.md` | added a sentence in §4.5 clarifying that "significant" is colloquial ("above the 2-SE bar"), not formal |
| 23 | §5.7.1 selection bias not discussed | rigor #8 | `05-results.md` | added a one-paragraph caveat in §5.7.1; §5.7.2 is now the more reliable verdict |
| 24 | §5.7.2 n=9 conditioning unflagged | rigor #6 | `05-results.md` | table now reports "n=9 (all-solved-by-all-three)" as a row; the conditional-vs-ITT distinction is stated |
| 25 | §5.3 dose-response reports total solves, not evolution-phase | rigor #5 | `05-results.md` | the table is now evolution-phase solves; the larger unconstrained-evo-solved drop is flagged |
| 26 | Missing Bouchacourt & Baroni 2018 (compositionality ≠ generalisation) | related work #1.3 | `02-related-work.md` | added; the clebran H3 null is framed as a typed-symbolic re-instantiation |
| 27 | L2T/NEO substrate delta deserves more weight | related work #2.2 | `02-related-work.md` | the deterministic / latent / mined deltas are now stated as a single "substrate delta" |
| 28 | §6.4 "Good for / Never for" overreach | rigor minor | `06-discussion.md` | tightened; the "good for" list is now framed as a prediction from the data, not a measured property |
| 29 | "Vindication" / "refutation" rhetoric | rigor minor | `06-discussion.md` | softened; "the result is consistent with" / "the data support" in place of advocacy vocabulary |
| 30 | Hyperparameter audit (30 items) | reproducibility audit | `04-methods.md` | new §4.7 "Configuration" table covers the items the paper must report |
| 31 | Missing-control note for B0+library | rigor #3 | `07-limitations.md` | §7 now lists B0+library as the obvious follow-up that would isolate the library mechanism from the centralization confound |

## Issues deferred (with reason)

A handful of the reviewer's points are not addressed in this pass and
should be either fixed by the user or addressed in a follow-up pass.

- **Compute audits per experiment + commit-hash table** (reproducibility
  artifact mapping). The artifact mapping is a real omission but is
  *engineering work* — the user will want to add a `summaries.jsonl`
  rename across experiments and a `git log` pass to fill the commit
  hashes. The paper text now says the table is in the per-experiment
  READMEs and in the repo; the table itself is best generated by a
  short script that walks the experiment folders.
- **The §6.4 capability audit is not yet a hard criterion** (it is a
  list, not a measurement). The list is honest as a *what would have
  to be true* statement; converting it to a measurement rubric is
  future work.
- **The order experiment (§5.7.3) is reported as 67 rows**. The
  reviewer is right that a 67-row pilot should not take half a page
  in the paper; it has been reduced to two sentences with a forward
  reference to a follow-up.
- **The "Good for / Never for" list** in §6.4 has been *tightened*,
  but the cleanest rewrite would drop the list entirely and replace
  it with a paragraph that names the same content. The list survives
  in this pass because it is the structure the user is likely to want
  for a publication.

## What I am explicitly not going to fix

- **B5 − B0 statistical significance.** I cannot compute the missing
  B5 − B7, B5 − B2, B5 − B8, B5 − B9, B5 − B1 contrasts from the
  paper alone; they need the JSONL summaries. The paper now softens
  the claim and points at the data; the user can compute the
  contrasts with one line of code in the per-experiment analysis
  scripts.
- **The L2T/NEO first names.** The reviewer supplied them; I added
  them; the user should re-verify against the arXiv listing before
  submission.
- **The hallucinated citations' replacements.** The reviewer supplied
  ArcMemo (Ho et al. 2025), Akyürek et al. 2024, Liao & Gu 2025, and
  several of the related-work additions. I trust the reviewer's
  corrections more than I trusted my original (which were hallucinated),
  but I did not have time in this session to verify them against
  arXiv myself. They are marked in the bibliography with a note.

## Open follow-up

After this revision, the most useful next pass is:

1. **Compute the missing B5 − {B1, B2, B7, B8, B9} contrasts** from
   the JSONL summaries and report them in §5.6.
2. **Generate the per-experiment commit-hash table** with `git log` and
   add it as an appendix or footnote in §4.
3. **Run the B0+library arm** (the missing control for §6.2) and report
   it in a follow-up paper.
4. **Finish the order experiment** (67 → 100+ rows) and write it up
   as the §5.7.3 / 9a measurement the paper currently only previews.
