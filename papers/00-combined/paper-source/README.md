# Paper source — `clebran-arc-agi`

This directory contains the markdown source of an academic paper written
from the experiments in this repository. It is a **paper-shaped write-up** of
the work, not a substitute for the per-experiment READMEs, the
`FINDINGS.md` summary, or the `roadmap.md`. Those are the primary artifacts;
this is a single-narrative paper that ties them together.

## Files

| file | contents |
|---|---|
| `00-abstract.md` | abstract |
| `01-introduction.md` | motivation, question, headline, contributions |
| `02-related-work.md` | ARC, library learning, emergent communication, L2T/NEO, multi-agent program synthesis, curriculum learning |
| `03-design.md` | the clebran design: IR, interpreter, GP engine, lineage, channel, payloads, library miner |
| `04-methods.md` | the three sub-hypotheses, the arm table, the match-compute protocol, statistics |
| `05-results.md` | H1, H2, H3, the frontier ranking, the central-library control, the curriculum channel, the transfer probe, amortization |
| `06-discussion.md` | the reorientation: not what you know, how you learned it |
| `07-limitations.md` | substrate, frontier, sample size, eval split, compositional OOD, single round |
| `08-conclusion.md` | what was falsified, what the project now proposes, open work |
| `references.md` | bibliography |
| `reviews/` | per-reviewer notes after the parallel review pass |
| `review-summary.md` | consolidated review feedback and the change log |

## Source conventions

- Each numbered file is one paper section. Section headings are H1; subsections H2.
- Tables use GFM pipe tables.
- Equations are inline `$...$`; no rendered math yet — a follow-up pass
  can port to LaTeX if the paper is to be submitted.
- Cross-references between files use `[§N](../05-results.md)` style.
- All claims about numbers are sourced from the per-experiment READMEs in
  `experiments/<date>_<name>/`; every quantitative claim should be traceable
  there. Inline citations of the form `[exp: 2026-07-22_b5_central_library]`
  refer to those directories.
- Tone is academic but readable; this is a falsification paper and is
  written that way — the negative result is the headline, not the conclusion.

## How to read in order

If you want the story end-to-end, read `00` → `01` → `02` → `04` (skim
hypotheses) → `05` (the heart of the paper) → `06` (the reorientation) →
`07` → `08`. `03` is the long technical reference; consult it when a
specific design choice is in question.

## Status

First draft, with one full pass of four parallel reviewer agents
(rigor, narrative, related work, reproducibility) incorporated.
Their notes are in `reviews/` and the consolidated log of edits in
`review-summary.md`. The `scripts/` subdirectory contains a
small Python helper that was used during the editing process; it
can be deleted once the paper is finalised.

**Update (2026-07-24):** incorporated the completed order/process
experiment [exp: 2026-07-24_order_process] — the paper's first
significant *process* result (foundations-first vs foundations-last,
paired McNemar p = 0.021). Touched: `00-abstract`, `01-introduction`
(contributions), `05-results` §5.7.3 (rewritten from "in progress" to
the full 216-run result), `06-discussion` §6.1, `08-conclusion`. The
transfer-probe/amortization correction (relevant teaching ≈ neutral,
irrelevant teaching harmful) was already in the draft (§5.7.2) and is
unchanged. Known defect not yet fixed: `01-introduction.md` contains
mojibake (`â€"`, `âˆ'`, `â†'` for —, −, →) from an encoding slip in an
earlier edit; the other section files are clean.
