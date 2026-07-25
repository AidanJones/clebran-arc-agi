"""Build the clebran paper PDF.

Concatenates the paper section files in order, converts to HTML with
academic-style CSS, and renders to PDF via headless Microsoft Edge.

Run with:
    uv run python paper/build_pdf.py

Produces:
    paper/clebran_paper.pdf
    paper/clebran_paper.html  (intermediate; removed unless --keep-html)
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import markdown
from markdown.extensions.toc import TocExtension

PAPER = Path(__file__).resolve().parent
HTML_OUT = PAPER / "clebran_paper.html"
PDF_OUT = PAPER / "clebran_paper.pdf"

# Section files in the order they should appear in the PDF.
# (Skips README, review-summary, reviews/, scripts/ — those are meta.)
SECTIONS = [
    "00-abstract.md",
    "01-introduction.md",
    "02-related-work.md",
    "03-design.md",
    "04-methods.md",
    "05-results.md",
    "06-discussion.md",
    "07-limitations.md",
    "08-conclusion.md",
    "references.md",
]

TITLE = "On the Cost of Communication in Divergent Program Evolution"
SUBTITLE = (
    "Matched-compute evidence from ARC-AGI-1 that a single agent with a "
    "central library strictly dominates divergent lineages communicating "
    "over a constrained channel — and a reorientation toward "
    "skill-acquisition efficiency"
)
AUTHOR = "Aidan Jones"
DATE = "23 July 2026"
REPO_FOOTNOTE = (
    "Source: clebran-arc-agi repository. Per-experiment READMEs at "
    "experiments/2026-07-*. The review pass for this draft is in "
    "paper/reviews/, and the consolidated change log in paper/review-summary.md."
)

CSS = """
@page {
    size: Letter;
    margin: 1in 1in 1.1in 1in;
    @bottom-center {
        content: counter(page);
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-size: 9pt;
        color: #888;
    }
}
@page :first {
    margin: 1.4in 1in 1.1in 1in;
    @bottom-center { content: ""; }
}

html { font-size: 11pt; }
body {
    font-family: 'Charter', 'Iowan Old Style', 'Georgia', 'Times New Roman', serif;
    line-height: 1.42;
    color: #1a1a1a;
    max-width: 6.5in;
    margin: 0 auto;
    padding: 0;
}
h1, h2, h3, h4 {
    font-family: 'Helvetica Neue', 'Helvetica', 'Arial', sans-serif;
    color: #111;
    line-height: 1.2;
    margin-top: 1.4em;
    margin-bottom: 0.5em;
    page-break-after: avoid;
}
h1 {
    font-size: 1.55em;
    margin-top: 1.8em;
    border-bottom: 1px solid #ccc;
    padding-bottom: 0.18em;
}
h2 { font-size: 1.20em; }
h3 { font-size: 1.05em; color: #333; }
h4 { font-size: 0.95em; color: #555; font-style: italic; }

p { margin: 0.55em 0; text-align: justify; hyphens: auto; }

a { color: #1a4d8f; text-decoration: none; }
a:hover { text-decoration: underline; }

em, i { color: #222; }
strong, b { color: #111; }

code {
    font-family: 'Consolas', 'Menlo', 'DejaVu Sans Mono', monospace;
    font-size: 0.88em;
    background: #f3f3f3;
    padding: 0.05em 0.30em;
    border-radius: 2px;
    color: #2a2a2a;
}
pre {
    font-family: 'Consolas', 'Menlo', 'DejaVu Sans Mono', monospace;
    font-size: 0.85em;
    background: #f6f6f6;
    padding: 0.7em 0.9em;
    border-left: 3px solid #ccc;
    border-radius: 2px;
    overflow-x: auto;
    line-height: 1.32;
    page-break-inside: avoid;
}
pre code { background: transparent; padding: 0; }

table {
    border-collapse: collapse;
    margin: 0.9em 0;
    width: 100%;
    font-size: 0.92em;
    page-break-inside: avoid;
}
th, td {
    border: 1px solid #bbb;
    padding: 0.30em 0.55em;
    text-align: left;
    vertical-align: top;
}
th {
    background: #f0f0f0;
    font-family: 'Helvetica Neue', 'Helvetica', 'Arial', sans-serif;
    font-size: 0.92em;
    color: #222;
}
tr:nth-child(even) td { background: #fafafa; }

blockquote {
    margin: 0.8em 0;
    padding: 0.4em 0.9em;
    border-left: 3px solid #999;
    color: #444;
    background: #f7f7f7;
    font-style: italic;
}

ul, ol { margin: 0.4em 0; padding-left: 1.6em; }
li { margin: 0.18em 0; }

hr {
    border: none;
    border-top: 1px solid #ccc;
    margin: 1.6em 0;
}

/* Title page */
.title-page {
    text-align: center;
    page-break-after: always;
    padding-top: 1.6in;
}
.title-page h1 {
    font-size: 2.05em;
    border: none;
    margin: 0 0 0.4em 0;
    padding: 0;
    line-height: 1.18;
}
.title-page .subtitle {
    font-style: italic;
    color: #444;
    font-size: 1.05em;
    max-width: 5.4in;
    margin: 0.6em auto 1.6em auto;
    line-height: 1.4;
}
.title-page .author {
    font-family: 'Helvetica Neue', 'Helvetica', 'Arial', sans-serif;
    font-size: 1em;
    color: #333;
    margin: 0.4em 0;
}
.title-page .date {
    font-family: 'Helvetica Neue', 'Helvetica', 'Arial', sans-serif;
    font-size: 0.95em;
    color: #666;
    margin: 1.4em 0;
}
.title-page .repo {
    font-family: 'Consolas', 'Menlo', 'DejaVu Sans Mono', monospace;
    font-size: 0.78em;
    color: #888;
    margin: 1.0em auto 0.4em auto;
    max-width: 5.0in;
    line-height: 1.5;
}

/* TOC */
.toc-page {
    page-break-after: always;
}
.toc-page h1 {
    font-size: 1.5em;
    border: none;
    margin-bottom: 0.6em;
}
.toc-page ul { list-style: none; padding-left: 0; }
.toc-page li { margin: 0.20em 0; }
.toc-page a { color: #222; }
.toc-page .level-2 { padding-left: 1.4em; }
.toc-page .level-3 { padding-left: 2.8em; font-size: 0.95em; color: #555; }
"""


def load_concatenated_markdown() -> str:
    """Concatenate the section files in order, with the title-page
    metadata prepended and a [TOC] marker after the abstract."""
    parts = []
    for fname in SECTIONS:
        path = PAPER / fname
        if not path.exists():
            print(f"warning: missing {fname}", file=sys.stderr)
            continue
        text = path.read_text(encoding="utf-8")
        parts.append(text.rstrip() + "\n\n")
    return "\n".join(parts)


def build_html() -> str:
    """Build the full HTML document."""
    md_text = load_concatenated_markdown()

    # Insert a [TOC] marker just after the abstract and before the
    # introduction. The [TOC] marker is replaced by the TOC content
    # by the TocExtension.
    abstract_marker = "# 0. Abstract"
    introduction_marker = "# 1. Introduction"
    if abstract_marker in md_text and introduction_marker in md_text:
        idx = md_text.index(introduction_marker, md_text.index(abstract_marker))
        md_text = (
            md_text[:idx]
            + "\n[TOC]\n\n"
            + md_text[idx:]
        )

    md = markdown.Markdown(
        extensions=[
            "extra",        # tables, fenced code, attr_list, def_list
            "smarty",       # smart quotes
            "sane_lists",
            TocExtension(toc_depth="2-3", anchorlink=False, permalink=False),
        ],
        output_format="html5",
    )
    body_html = md.convert(md_text)
    toc_html = md.toc  # populated by TocExtension

    title_page = f"""
<section class="title-page">
  <h1>{TITLE}</h1>
  <p class="subtitle">{SUBTITLE}</p>
  <p class="author">{AUTHOR}</p>
  <p class="date">{DATE}</p>
  <p class="repo">{REPO_FOOTNOTE}</p>
</section>
"""

    toc_page = f"""
<nav class="toc-page">
  <h1>Contents</h1>
  {toc_html}
</nav>
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>{TITLE}</title>
    <style>{CSS}</style>
</head>
<body>
{title_page}
{toc_page}
{body_html}
</body>
</html>
"""


def render_pdf(html_path: Path, pdf_path: Path) -> None:
    """Render the HTML file to PDF via headless Microsoft Edge."""
    edge_paths = [
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    ]
    browser = next((p for p in edge_paths if p.exists()), None)
    if browser is None:
        raise RuntimeError(
            "No headless browser found. Expected Microsoft Edge or Chrome "
            "in the standard Program Files locations."
        )

    url = html_path.resolve().as_uri()
    print(f"using browser: {browser}")
    print(f"rendering: {url}")

    cmd = [
        str(browser),
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        url,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if res.returncode != 0:
        print("Browser stdout:", res.stdout, file=sys.stderr)
        print("Browser stderr:", res.stderr, file=sys.stderr)
        raise RuntimeError(
            f"headless browser returned {res.returncode}; see stderr above"
        )

    if not pdf_path.exists():
        raise RuntimeError(f"PDF was not produced at {pdf_path}")
    size_kb = pdf_path.stat().st_size / 1024
    print(f"PDF written: {pdf_path} ({size_kb:,.1f} KB)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep-html", action="store_true",
                    help="Keep the intermediate HTML file")
    ap.add_argument("--pdf", type=Path, default=PDF_OUT, help="Output PDF path")
    args = ap.parse_args()

    html = build_html()
    HTML_OUT.write_text(html, encoding="utf-8")
    print(f"HTML written: {HTML_OUT} ({len(html):,} bytes)")

    render_pdf(HTML_OUT, args.pdf)

    if not args.keep_html:
        HTML_OUT.unlink(missing_ok=True)
        print(f"removed intermediate HTML: {HTML_OUT}")
    else:
        print(f"kept intermediate HTML: {HTML_OUT}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
