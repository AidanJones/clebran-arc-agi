"""Render the clebran solver card — a single self-contained HTML page.

Reads run logs (logs/*.jsonl) + the Stage-1 subset and produces
logs/report.html: experiment explainer, hypothesis/baseline mapping,
auto-filled results table, and one card per subset task with demo pairs,
the evolved program, and a step-by-step execution trace (every register
rendered as a grid).

Usage:  uv run python scripts/render_report.py
"""
from __future__ import annotations

import html
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from clebran.data.loader import load_task  # noqa: E402
from clebran.dsl.interpreter import run_trace, run_safe, ExecutionError  # noqa: E402
from clebran.dsl.program import Program  # noqa: E402
from clebran.dsl.solver_parse import parse_all_solvers  # noqa: E402
from clebran.subset import load_subset  # noqa: E402

LOGS = ROOT / "logs"
OUT = LOGS / "report.html"

ARC_COLORS = [
    "#000000", "#0074D9", "#FF4136", "#2ECC40", "#FFDC00",
    "#AAAAAA", "#F012BE", "#FF851B", "#7FDBFF", "#870C25",
]


# ---------------- data collection ----------------

def collect() -> tuple[dict, dict]:
    """Return (per-arm summaries, best solve event per task)."""
    summaries: dict[str, dict[int, dict]] = defaultdict(dict)
    solves: dict[str, dict] = {}
    for path in sorted(LOGS.glob("*.jsonl")):
        if path.name == "sweep_results.jsonl":
            continue
        for line in path.read_text().splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            ev = r.get("event")
            if ev == "summary" and "arm" in r:
                summaries[r["arm"]][r["seed"]] = r
            elif ev == "solve" and "program" in r:
                tid = r["task"]
                r["_src"] = path.stem
                cur = solves.get(tid)
                if cur is None or r["len"] < cur["len"]:
                    solves[tid] = r
    return summaries, solves


# ---------------- grid rendering ----------------

def grid_html(g, cap: int = 140, cls: str = "") -> str:
    h, w = len(g), len(g[0])
    cell = max(4, min(18, cap // max(h, w)))
    data = json.dumps([list(r) for r in g], separators=(",", ":"))
    return (
        f'<canvas class="grid {cls}" data-g=\'{data}\' data-c="{cell}" '
        f'width="{w * cell + w + 1}" height="{h * cell + h + 1}" '
        f'title="{h}×{w}"></canvas>'
    )


def value_html(v) -> str:
    """Render an intermediate register: grids as grids, all else compact."""
    if (
        isinstance(v, tuple) and v and all(isinstance(r, tuple) for r in v)
        and all(isinstance(x, int) for r in v for x in r)
        and len({len(r) for r in v}) == 1 and len(v[0]) > 0
    ):
        return grid_html(v, cap=120)
    s = repr(v)
    if callable(v):
        s = f"fn:{getattr(v, '__name__', '?')}"
    if len(s) > 60:
        s = s[:57] + "…"
    return f'<span class="val">{html.escape(s)}</span>'


# ---------------- per-task card ----------------

def task_card(row: dict, solve: dict | None, ref_depth: int) -> str:
    tid = row["task_id"]
    task = load_task("training", tid)
    solved = solve is not None
    status = (
        '<span class="badge ok">solved</span>' if solved
        else '<span class="badge no">unsolved</span>'
    )
    tags = " ".join(f'<span class="chip">{t}</span>' for t in row["tags"])
    pairs = "".join(
        f'<div class="pair">{grid_html(i, 90)}<span class="arr">→</span>'
        f"{grid_html(o, 90)}</div>"
        for i, o in task.train
    )
    body = ""
    if solved:
        prog = Program.from_json(solve["program"])
        pretty = html.escape(prog.pretty())
        meta = (
            f'evolved length {solve["len"]} · reference depth {ref_depth} · '
            f'run {html.escape(solve["_src"])} · '
            f'{"test pair exact ✓" if solve.get("test_exact") else "test pair MISS ✗"}'
        )
        inp = task.train[0][0]
        want = task.train[0][1]
        try:
            regs = run_trace(prog, inp)
            steps = [
                f'<div class="step"><div class="cap">I</div>{grid_html(inp)}</div>'
            ]
            lines = prog.pretty().splitlines()
            for k, v in enumerate(regs):
                cap = html.escape(lines[k])
                steps.append(
                    f'<div class="step"><div class="cap">{cap}</div>'
                    f"{value_html(v)}</div>"
                )
            match = regs[-1] == want
            steps.append(
                f'<div class="step"><div class="cap">expected'
                f'{" · match" if match else ""}</div>{grid_html(want)}</div>'
            )
            trace = (
                '<div class="tracewrap"><div class="trace">'
                + '<span class="arr big">→</span>'.join(steps)
                + "</div></div>"
            )
        except ExecutionError as e:
            trace = f'<p class="mut">trace failed: {html.escape(str(e))}</p>'
        body = (
            f'<div class="meta">{meta}</div>'
            f"<pre>{pretty}</pre>"
            f'<div class="lbl">execution trace · demonstration pair 1</div>{trace}'
        )
    else:
        body = '<p class="mut">No arm has solved this task yet.</p>'
    return (
        f'<article class="card" data-status="{"solved" if solved else "unsolved"}" '
        f'data-bucket="{row["bucket"]}">'
        f'<header><h3>{tid}</h3><span class="chip b">{row["bucket"]}</span>'
        f'<span class="chip">d={ref_depth}</span>{tags}{status}</header>'
        f'<div class="lbl">demonstration pairs</div><div class="pairs">{pairs}</div>'
        f"{body}</article>"
    )


# ---------------- results table ----------------

ARM_DESC = {
    "B0": "single population, all compute",
    "B1": "N isolated lineages, best-of union (CH-NONE)",
    "B2": "N lineages + constrained channel, fragment payload",
    "B3": "N lineages + unconstrained channel",
    "B4": "N lineages + constrained channel, signal payload",
}


def results_table(summaries: dict) -> str:
    if not summaries:
        return '<p class="mut">No completed runs yet.</p>'
    rows = []
    for arm in sorted(summaries):
        per_seed = summaries[arm]
        solved = [
            float(r.get("solved_union", r.get("solved", 0)))
            for r in per_seed.values()
        ]
        evals = [r["evals"] for r in per_seed.values()]
        reuse = [r["reuse_rate"] for r in per_seed.values() if "reuse_rate" in r]
        jac = [
            r["divergence"]["mean"] for r in per_seed.values() if "divergence" in r
        ]
        fmt = (
            f"{st.mean(solved):.1f} ± {st.stdev(solved):.1f}"
            if len(solved) > 1 else f"{solved[0]:.0f}"
        )
        rows.append(
            f"<tr><td><b>{arm}</b></td><td>{ARM_DESC.get(arm, '')}</td>"
            f"<td>{len(per_seed)}</td><td>{fmt}</td>"
            f"<td>{int(st.mean(evals)):,}</td>"
            f"<td>{(f'{st.mean(reuse):.2f}' if reuse else '—')}</td>"
            f"<td>{(f'{st.mean(jac):.2f}' if jac else '—')}</td></tr>"
        )
    return (
        '<div class="tbl"><table><thead><tr><th>arm</th><th>what it is</th>'
        "<th>seeds</th><th>solved /30</th><th>mean evals</th><th>reuse</th>"
        "<th>divergence</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )


# ---------------- page ----------------

def build() -> str:
    subset = load_subset()
    ref = parse_all_solvers()
    summaries, solves = collect()
    n_solved = sum(1 for r in subset if r["task_id"] in solves)
    cards = "".join(
        task_card(row, solves.get(row["task_id"]), len(ref[row["task_id"]]))
        for row in subset
    )
    css = CSS
    return f"""<meta charset="utf-8">
<title>clebran — solver card</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{css}</style>
<div class="wrap">
<header class="top">
  <div class="eyebrow">clebran-arc-agi · solver card</div>
  <h1>Gossip protocols for divergent program evolution</h1>
  <p class="lede">Populations of DSL programs evolve under pure reward on ARC-AGI-1
  tasks, diverge into different strategies, and pass fragments of “what works”
  through a deliberately narrow channel. This card shows what the solver is
  actually doing: every solved task below carries the evolved program and its
  step-by-step execution trace.</p>
</header>

<section>
  <h2>The experiment in one table</h2>
  <p>Three hypotheses, each with a decisive comparison at <em>matched compute</em>
  (same total candidate-evaluations, ≥5 seeds):</p>
  <div class="tbl"><table>
  <thead><tr><th>hypothesis</th><th>claim</th><th>decided by</th></tr></thead>
  <tbody>
  <tr><td><b>H1</b> divergence</td><td>independent lineages find genuinely different abstractions</td><td>low primitive-usage overlap in B1; tasks solved by exactly one lineage</td></tr>
  <tr><td><b>H2</b> transfer helps</td><td>exchanging DSL fragments beats the same compute without communication</td><td>B2 &gt; B1 <em>and</em> B2 &gt; B0</td></tr>
  <tr><td><b>H3</b> constraint matters</td><td>a narrow channel beats dumping whole libraries</td><td>B2 &gt; B3</td></tr>
  </tbody></table></div>
</section>

<section>
  <h2>Results so far</h2>
  {results_table(summaries)}
  <p class="mut">Reuse = fraction of solutions containing channel-received material.
  Divergence = mean pairwise Jaccard distance of primitive usage across lineages.
  Arms appear here automatically as their runs complete.</p>
</section>

<section>
  <h2>Task cards <span class="count">{n_solved}/30 solved by some run</span></h2>
  <div class="filters">
    <button class="f on" data-f="all">all</button>
    <button class="f" data-f="solved">solved</button>
    <button class="f" data-f="unsolved">unsolved</button>
    <span class="sep"></span>
    <button class="f on" data-b="all">D1+D2+D3</button>
    <button class="f" data-b="D1">D1</button>
    <button class="f" data-b="D2">D2</button>
    <button class="f" data-b="D3">D3</button>
  </div>
  {cards}
</section>

<footer>Generated from logs/*.jsonl · grids use the standard ARC palette ·
D-buckets grade tasks by reference-solver depth (d = pipeline steps in
Hodel’s hand-written solution).</footer>
</div>
<script>
const fs = document.querySelectorAll('.f');
let curF = 'all', curB = 'all';
function apply() {{
  document.querySelectorAll('.card').forEach(c => {{
    const okF = curF === 'all' || c.dataset.status === curF;
    const okB = curB === 'all' || c.dataset.bucket === curB;
    c.style.display = okF && okB ? '' : 'none';
  }});
}}
fs.forEach(b => b.addEventListener('click', () => {{
  if (b.dataset.f) {{ curF = b.dataset.f;
    fs.forEach(x => x.dataset.f && x.classList.toggle('on', x === b)); }}
  else {{ curB = b.dataset.b;
    fs.forEach(x => x.dataset.b && x.classList.toggle('on', x === b)); }}
  apply();
}}));
const PAL = {json.dumps(ARC_COLORS)};
document.querySelectorAll('canvas.grid').forEach(cv => {{
  const g = JSON.parse(cv.dataset.g), c = +cv.dataset.c;
  const ctx = cv.getContext('2d');
  ctx.fillStyle = '#2a2e38';
  ctx.fillRect(0, 0, cv.width, cv.height);
  g.forEach((row, y) => row.forEach((v, x) => {{
    ctx.fillStyle = (v >= 0 && v <= 9) ? PAL[v] : '#444';
    ctx.fillRect(1 + x * (c + 1), 1 + y * (c + 1), c, c);
  }}));
}});
</script>
"""


CSS = """
:root{
  --bg:#101216; --panel:#171a20; --panel2:#1d212a; --ink:#e8eaf0;
  --mut:#8b92a3; --line:#262b36; --accent:#d9a441; --ok:#3fb68b; --no:#d25d5d;
  --serif: 'Iowan Old Style','Palatino Linotype',Palatino,Georgia,serif;
  --mono: 'Cascadia Mono','SF Mono',Consolas,'DejaVu Sans Mono',monospace;
}
@media (prefers-color-scheme: light){:root{
  --bg:#f6f7f9; --panel:#ffffff; --panel2:#eef0f4; --ink:#1a1d24;
  --mut:#5b6272; --line:#dde1e8; --accent:#a97b1e;}}
:root[data-theme="dark"]{
  --bg:#101216; --panel:#171a20; --panel2:#1d212a; --ink:#e8eaf0;
  --mut:#8b92a3; --line:#262b36; --accent:#d9a441;}
:root[data-theme="light"]{
  --bg:#f6f7f9; --panel:#ffffff; --panel2:#eef0f4; --ink:#1a1d24;
  --mut:#5b6272; --line:#dde1e8; --accent:#a97b1e;}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font-family:var(--mono);
  font-size:14px;line-height:1.55;margin:0}
.wrap{max-width:1100px;margin:0 auto;padding:40px 20px 80px}
.top .eyebrow{color:var(--accent);letter-spacing:.14em;text-transform:uppercase;
  font-size:11px}
h1{font-family:var(--serif);font-size:clamp(26px,4vw,38px);line-height:1.15;
  margin:.3em 0 .4em;text-wrap:balance;font-weight:600}
.lede{font-family:var(--serif);font-size:17px;max-width:62ch;color:var(--ink)}
h2{font-family:var(--serif);font-size:22px;margin:2.2em 0 .6em;font-weight:600}
h2 .count{font-family:var(--mono);font-size:12px;color:var(--mut);margin-left:10px}
p{max-width:70ch}
.mut{color:var(--mut);font-size:12.5px}
.tbl{overflow-x:auto;border:1px solid var(--line);border-radius:6px}
table{border-collapse:collapse;width:100%;font-size:13px;
  font-variant-numeric:tabular-nums}
th,td{padding:8px 12px;text-align:left;border-bottom:1px solid var(--line)}
th{color:var(--mut);font-weight:500;font-size:11px;text-transform:uppercase;
  letter-spacing:.08em}
tbody tr:last-child td{border-bottom:0}
.filters{display:flex;gap:6px;align-items:center;margin:0 0 18px;flex-wrap:wrap}
.f{background:var(--panel);color:var(--mut);border:1px solid var(--line);
  font:inherit;font-size:12px;padding:4px 12px;border-radius:99px;cursor:pointer}
.f.on{color:var(--ink);border-color:var(--accent)}
.f:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.sep{width:14px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;
  padding:18px 20px;margin:0 0 16px}
.card header{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:0 0 10px}
.card h3{margin:0;font-size:15px;font-weight:600;letter-spacing:.03em}
.chip{background:var(--panel2);color:var(--mut);font-size:11px;padding:2px 8px;
  border-radius:99px}
.chip.b{color:var(--accent)}
.badge{font-size:11px;padding:2px 10px;border-radius:99px;margin-left:auto}
.badge.ok{background:color-mix(in srgb,var(--ok) 18%,transparent);color:var(--ok)}
.badge.no{background:color-mix(in srgb,var(--no) 15%,transparent);color:var(--no)}
.lbl{color:var(--mut);font-size:11px;text-transform:uppercase;
  letter-spacing:.09em;margin:12px 0 6px}
.pairs{display:flex;gap:18px;flex-wrap:wrap;align-items:center}
.pair{display:flex;gap:8px;align-items:center}
canvas.grid{display:block;border-radius:2px;image-rendering:pixelated}
.arr{color:var(--mut)}
.arr.big{align-self:center;font-size:16px;padding:0 2px}
pre{background:var(--panel2);border:1px solid var(--line);border-radius:6px;
  padding:10px 14px;overflow-x:auto;font-size:13px;line-height:1.5;margin:6px 0}
.meta{color:var(--mut);font-size:12px;margin:8px 0 2px}
.tracewrap{overflow-x:auto;padding:6px 0}
.trace{display:flex;gap:6px;align-items:flex-start;width:max-content}
.step{display:flex;flex-direction:column;gap:6px;align-items:flex-start}
.step .cap{color:var(--mut);font-size:11px;max-width:200px;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.val{background:var(--panel2);border:1px solid var(--line);border-radius:4px;
  padding:4px 8px;font-size:11px;color:var(--mut);max-width:220px;
  display:inline-block;overflow-wrap:anywhere}
footer{color:var(--mut);font-size:12px;margin-top:50px;
  border-top:1px solid var(--line);padding-top:14px;max-width:70ch}
@media (prefers-reduced-motion: no-preference){
  .card{transition:border-color .15s}
  .card:hover{border-color:var(--accent)}}
"""


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT}")
