"""Build a PDF for any paper under `papers/`.

Each paper is a self-contained directory with a `paper.md` and a `meta.json`
(title / subtitle / author / date). This renders `paper.md` to academic-styled
HTML and prints it to PDF via headless Microsoft Edge — the same
dependency-light pipeline as `paper/build_pdf.py` (Python `markdown` + Edge,
no pandoc/LaTeX required), generalised to take a paper directory.

    uv run python papers/build_pdf.py papers/01-communication-cost
    uv run python papers/build_pdf.py --all

Produces `<dir>/paper.pdf` (and `<dir>/paper.html` with --keep-html).
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import markdown
from markdown.extensions.toc import TocExtension

PAPERS = Path(__file__).resolve().parent

CSS = """
@page { size: Letter; margin: 1in 1in 1.1in 1in;
    @bottom-center { content: counter(page); font-family: Arial, sans-serif;
                     font-size: 9pt; color: #888; } }
@page :first { margin: 1.4in 1in 1.1in 1in; @bottom-center { content: ""; } }
html { font-size: 11pt; }
body { font-family: 'Charter','Iowan Old Style','Georgia','Times New Roman',serif;
    line-height: 1.42; color: #1a1a1a; max-width: 6.5in; margin: 0 auto; }
h1,h2,h3,h4 { font-family: 'Helvetica Neue','Arial',sans-serif; color: #111;
    line-height: 1.2; margin-top: 1.4em; margin-bottom: 0.5em; page-break-after: avoid; }
h1 { font-size: 1.55em; margin-top: 1.8em; border-bottom: 1px solid #ccc; padding-bottom: 0.18em; }
h2 { font-size: 1.20em; } h3 { font-size: 1.05em; color: #333; }
h4 { font-size: 0.95em; color: #555; font-style: italic; }
p { margin: 0.55em 0; text-align: justify; hyphens: auto; }
a { color: #1a4d8f; text-decoration: none; }
code { font-family: 'Consolas','Menlo',monospace; font-size: 0.88em; background: #f3f3f3;
    padding: 0.05em 0.30em; border-radius: 2px; color: #2a2a2a; }
pre { font-family: 'Consolas','Menlo',monospace; font-size: 0.85em; background: #f6f6f6;
    padding: 0.7em 0.9em; border-left: 3px solid #ccc; border-radius: 2px;
    overflow-x: auto; line-height: 1.32; page-break-inside: avoid; }
pre code { background: transparent; padding: 0; }
table { border-collapse: collapse; margin: 0.9em 0; width: 100%; font-size: 0.92em;
    page-break-inside: avoid; }
th,td { border: 1px solid #bbb; padding: 0.30em 0.55em; text-align: left; vertical-align: top; }
th { background: #f0f0f0; font-family: 'Helvetica Neue','Arial',sans-serif; color: #222; }
tr:nth-child(even) td { background: #fafafa; }
blockquote { margin: 0.8em 0; padding: 0.4em 0.9em; border-left: 3px solid #999;
    color: #444; background: #f7f7f7; font-style: italic; }
ul,ol { margin: 0.4em 0; padding-left: 1.6em; } li { margin: 0.18em 0; }
hr { border: none; border-top: 1px solid #ccc; margin: 1.6em 0; }
.title-page { text-align: center; page-break-after: always; padding-top: 1.6in; }
.title-page h1 { font-size: 1.9em; border: none; margin-bottom: 0.4em; }
.title-page .subtitle { font-size: 1.05em; color: #444; font-style: italic;
    max-width: 5in; margin: 0 auto 1.6em; }
.title-page .author { font-size: 1.1em; margin-top: 1.2em; }
.title-page .date { color: #666; margin-top: 0.3em; }
.title-page .foot { font-size: 0.8em; color: #888; margin-top: 2.4in; }
"""

EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def _edge() -> str:
    for c in EDGE_CANDIDATES:
        if Path(c).exists():
            return c
    found = shutil.which("msedge") or shutil.which("chrome")
    if found:
        return found
    sys.exit("no Microsoft Edge / Chrome found for headless PDF printing")


def build(paper_dir: Path, keep_html: bool = False) -> None:
    meta = json.loads((paper_dir / "meta.json").read_text(encoding="utf-8"))
    body_md = (paper_dir / "paper.md").read_text(encoding="utf-8")
    html_body = markdown.markdown(
        body_md,
        extensions=["tables", "fenced_code", "sane_lists",
                    TocExtension(toc_depth="2-3")],
    )
    title_page = f"""
    <div class="title-page">
      <h1>{meta['title']}</h1>
      <div class="subtitle">{meta.get('subtitle','')}</div>
      <div class="author">{meta.get('author','')}</div>
      <div class="date">{meta.get('date','')}</div>
      <div class="foot">{meta.get('footnote','')}</div>
    </div>"""
    html = (f"<!doctype html><html><head><meta charset='utf-8'>"
            f"<style>{CSS}</style></head><body>{title_page}{html_body}</body></html>")
    html_out = paper_dir / "paper.html"
    pdf_out = paper_dir / "paper.pdf"
    html_out.write_text(html, encoding="utf-8")
    subprocess.run(
        [_edge(), "--headless", "--disable-gpu", "--no-pdf-header-footer",
         f"--print-to-pdf={pdf_out}", html_out.as_uri()],
        check=True, timeout=120,
    )
    if not keep_html:
        html_out.unlink(missing_ok=True)
    print(f"wrote {pdf_out} ({pdf_out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("paper_dir", nargs="?", help="a papers/<name> directory")
    ap.add_argument("--all", action="store_true", help="build every paper dir")
    ap.add_argument("--keep-html", action="store_true")
    args = ap.parse_args()
    if args.all:
        for d in sorted(PAPERS.iterdir()):
            if (d / "paper.md").exists() and (d / "meta.json").exists():
                build(d, args.keep_html)
    elif args.paper_dir:
        build(Path(args.paper_dir), args.keep_html)
    else:
        ap.error("give a paper directory or --all")
