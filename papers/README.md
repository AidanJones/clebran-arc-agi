# papers/

Multiple focused papers drawn from the `clebran-arc-agi` work, plus a
combined summary that ties them together. Each paper is a
**self-contained directory** — its own reproduction instructions,
markdown, and PDF — so the papers can evolve independently and be
submitted separately.

| directory | paper | one-line thesis |
|---|---|---|
| [`00-combined/`](00-combined/) | *clebran: Communication, Process, and World Models for ARC Program Synthesis* | the combined summary — substrate + the four focused papers + the synthesis |
| [`01-communication-cost/`](01-communication-cost/) | *On the Cost of Communication in Divergent Program Evolution* | at matched compute, a single agent with a central library significantly beats divergent agents communicating over a constrained channel |
| [`02-how-you-learned-it/`](02-how-you-learned-it/) | *Not What You Know, How You Learned It* | teaching content between agents is neutral/harmful, but the *order* of acquisition significantly changes capability |
| [`03-world-modeling/`](03-world-modeling/) | *A World-Model Substrate for ARC Program Synthesis* | the clebran interpreter is a perfect L1; an L2 multi-pair planner + B5 seed ties B5 at matched compute — the first positive integration result on the rig |
| [`04-discovery-bottleneck/`](04-discovery-bottleneck/) | *A Trustworthy Negative: Four Discovery Mechanisms, Four Nulls at 1M in ARC Program Synthesis* | four pre-registered attacks on the central library's reach (practice pool, fitness signal, task pool, objective) all return null at 1M × 5 seeds — closes the "more mechanism on the same DSL" menu |

The four focused papers are complementary. Paper 1 is the
**falsification** (content transfer does not help), paper 2 is the
**reorientation** it forces (process, not content), paper 3 is the
**first positive integration result** on the rig (a world-model seed
that ties B5 at matched compute), and paper 4 is the
**discovery-side falsification** (no mechanism *inside* the current
DSL/interpreter/fitness expands B5's reach at 1M, regardless of which
axis you vary). Paper 1 is the natural first read; the combined
paper at `00-combined/` is the natural second read if you want the
synthesis.

The long-form write-up that ties every experiment together (sections
`00-abstract` → `08-conclusion`, with the full related work, design,
methods, and per-experiment results) is archived at
[`00-combined/paper-source/`](00-combined/paper-source/). The
long-form is the source the focused papers were extracted from, and
is kept for reference.

## Each paper directory contains

- **`REPRODUCE.md`** — the exact, matched-compute commands to regenerate every
  quantitative claim in the paper, plus pointers to the frozen `experiments/`
  data the paper actually cites.
- **`paper.md`** — the paper, single-file, self-contained.
- **`meta.json`** — title / subtitle / author / date for the PDF title page.
- **`paper.pdf`** — the rendered PDF (produced by the builder below).

## Building the PDFs

The builder renders `paper.md` to academic-styled HTML and prints it to PDF via
headless Microsoft Edge — no pandoc or LaTeX required (Python `markdown` + Edge).

```sh
uv run python papers/build_pdf.py --all                          # every paper
uv run python papers/build_pdf.py papers/01-communication-cost   # one paper
```

## Relationship to `paper/`, the focused papers, and the primary artifacts

- `papers/00-combined/` is the **combined summary** — the one paper that
  ties the four focused papers together. The long-form write-up that
  contains every section in full is archived at
  `papers/00-combined/paper-source/`, kept for reference but not the
  primary artifact.
- `papers/01-.../`, `papers/02-.../`, `papers/03-.../`,
  `papers/04-.../` are the four *focused* papers — one per set of
  experiments, self-contained so they can be submitted independently.
- The primary, always-current artifacts remain the per-experiment
  `experiments/<date>_<name>/README.md`, the top-level `FINDINGS.md`, and
  `roadmap.md`. Every number in a paper is traceable to an `experiments/`
  directory via its `REPRODUCE.md`.

## Note

Authored as an additive `papers/` tree. The original `paper/` directory was
moved to `papers/00-combined/paper-source/` so the long-form write-up is
preserved as the source archive; the active combined paper is
`papers/00-combined/paper.md` (a summary that ties the four focused papers
together). The top-level `README.md` and `roadmap.md` were under
concurrent edit at the time of the move.