# papers/

Multiple focused papers drawn from the `clebran-arc-agi` work. Each paper is a
**self-contained directory** — its own reproduction instructions, markdown, and
PDF — so the papers can evolve independently and be submitted separately.

| directory | paper | one-line thesis |
|---|---|---|
| [`01-communication-cost/`](01-communication-cost/) | *On the Cost of Communication in Divergent Program Evolution* | at matched compute, a single agent with a central library significantly beats divergent agents communicating over a constrained channel |
| [`02-how-you-learned-it/`](02-how-you-learned-it/) | *Not What You Know, How You Learned It* | teaching content between agents is neutral/harmful, but the *order* of acquisition significantly changes capability |

The two papers are complementary: paper 1 is the falsification (content transfer
does not help), paper 2 is the reorientation it forces (process, not content).
Paper 1 is the natural first read.

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
uv run python papers/build_pdf.py papers/01-communication-cost   # one paper
uv run python papers/build_pdf.py --all                          # every paper
```

## Relationship to `paper/` and the primary artifacts

- `paper/` (singular) is the original **combined** long-form write-up of the
  whole project — one narrative tying every experiment together. These `papers/`
  are *focused splits* of that material, authored self-contained so they do not
  depend on `paper/`'s evolving section files.
- The primary, always-current artifacts remain the per-experiment
  `experiments/<date>_<name>/README.md`, the top-level `FINDINGS.md`, and
  `roadmap.md`. Every number in a paper is traceable to an `experiments/`
  directory via its `REPRODUCE.md`.

## Note

Authored as an additive `papers/` tree without modifying `paper/`, the top-level
`README.md`, or `roadmap.md` (those were under concurrent edit at the time). A
one-line pointer to `papers/` from the top-level README is the natural follow-up
once those files are quiescent.
