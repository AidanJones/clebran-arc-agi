# clebran-arc-agi — Emergent-DSL Multi-Agent Evolution for ARC-AGI-1

**An implementation specification for a coding agent**

Version 1.1 · Repo: `clebran-arc-agi` · Target: solo researcher, Kaggle-style compute · Benchmark: ARC-AGI-1 (subset first)

> **README blurb (use as the repo description and README opening):**
> *clebran* (Welsh: to chatter, to gossip) — gossip protocols for divergent program evolution. Multiple populations of DSL programs evolve under pure reward on ARC-AGI-1 tasks, diverge into different solution strategies, and pass fragments of "what works" to each other through a deliberately narrow communication channel. The experiment tests whether that constrained gossip preserves better abstractions than isolation, ensembling, or unconstrained sharing — at matched compute, with baselines strong enough that a null result is trustworthy.

**Naming note for the implementing agent:** the top-level Python package is `clebran` (the module layout in §6 reflects this).

---

## 0. Orientation for the implementing agent

You are building a research prototype to test one specific scientific hypothesis. This is **not** a "get the highest ARC score" project. The score is secondary. The primary deliverable is a clean experiment that either supports or falsifies the core claim below, with baselines rigorous enough that the result is believable either way.

Read Sections 1–3 before writing any code. Build in the staged order given in Section 8. Do not skip the baselines (Section 7) — they are the entire point.

---

## 1. The hypothesis

**Core claim:** Multiple independent populations of programs, each evolving under a pure reward signal (no supervised targets) and therefore diverging into *different* solution strategies, can improve overall problem-solving on ARC-AGI-1 by **communicating "what works" to each other through a constrained shared language (a DSL channel)**.

Three sub-claims, each independently testable:

- **H1 (divergence):** Independent reward-driven lineages, seeded differently, discover genuinely different abstractions for the same task distribution. (Measurable: low overlap in which primitives/subprograms each lineage relies on.)
- **H2 (transfer helps):** Allowing lineages to exchange successful DSL fragments improves solve rate versus the same total compute spent without cross-lineage communication.
- **H3 (the constraint matters):** A *constrained* channel (bounded-length DSL messages) preserves better/more reusable abstractions than an unconstrained "dump the whole library" channel. This is the "reward is all you need + a narrow channel forces good compression" intuition, echoing information-bottleneck and MDL arguments.

If H2 fails, that is a real and publishable result. Design so a null result is trustworthy.

---

## 2. Intellectual context (why this is worth doing)

The design borrows four established ideas and combines them in a way that (per prior-art review) has **not** been done together for ARC:

1. **Emergent communication / referential games** — multi-agent RL literature where a discrete, bandwidth-limited channel produces compositional "languages." Key intuition we exploit: channel capacity constraints induce compositionality and generalization. See Lazaridou & Baroni's survey (2020), and topographic-similarity as the standard compositionality metric.
   - Survey: *Emergent Multi-Agent Communication in the Deep Learning Era*, Lazaridou & Baroni — https://arxiv.org/abs/2006.02419
   - EGG framework (referential-game tooling, useful for the compositionality metrics even if we don't use it directly): https://github.com/facebookresearch/EGG

2. **Library learning / abstraction discovery** — DreamCoder's wake-sleep loop grows a library of reusable subroutines; this is the closest existing analogue to "keep good abstract representations." Our twist: instead of one library refined centrally, we have *several divergent libraries* that gossip.
   - DreamCoder: Ellis et al. — https://arxiv.org/abs/2006.08381 ; code: https://github.com/ellisk42/ec
   - Stitch (fast library compression, a practical replacement for DreamCoder's expensive compression step): https://github.com/mlb2251/stitch — paper https://arxiv.org/abs/2211.16605
   - ArcMemo (2025, LLM-based reusable-concept memory for ARC — conceptually adjacent, worth reading): search "ArcMemo ARC abstraction memory 2025"

3. **DSL-based program synthesis for ARC** — Michael Hodel's hand-written ARC-DSL is the reference grid-operation DSL and the practical backbone of this project.
   - arc-dsl: https://github.com/michaelhodel/arc-dsl (the file `dsl.py` has ~160 primitives; `solvers.py` has hand-written solutions to training tasks — an invaluable oracle for testing.)

4. **Learning-to-Theorize (L2T) / Neural Theorizer (NEO)** — Baek, Lee, Baek, Lee & Ahn, ICML 2026 (oral). This is the **closest published work to this project's actual goal** and should be treated as the primary theoretical anchor, not a peripheral citation. L2T formalises exactly the thing we care about: inferring, from raw before→after observation pairs `(x, y)` alone, the *hidden program* `τ = (z_{i_1}, …, z_{i_K})` — a composition of **learned, reusable primitive operations** — such that `y = f_τ(x)`. Its decisive test is not reconstruction but **transfer**: infer `τ̂` from a support pair, then execute the *same* `τ̂` on a fresh input `x⁽²⁾` and check whether it yields the correct `y⁽²⁾`. That is precisely the ARC demonstration→test protocol, cast as theory induction.
   - Project page: https://doojinbaek.github.io/publications/learning-to-theorize-the-world/ · Paper: https://arxiv.org/abs/2605.03413 · PDF: https://arxiv.org/pdf/2605.03413
   - Four ideas from L2T we adopt directly:
     - **Theory = executable program over reusable primitives**, and understanding = recovering those primitives — the same stance our DSL genome takes. An ARC task *is* an L2T "phenomenon."
     - **Transfer, not reconstruction, is the real metric.** NEO shows models can reconstruct a support target while failing to transfer. Our fitness must reward programs that solve *all* demonstration pairs (i.e. generalise across the pairs), not merely fit one — see §5.2.
     - **Adaptive, MDL-penalised program length.** NEO picks the *shortest accurate* explanation via a factor `λ_MDL > 1` that penalises longer programs, which stops simple changes being forced into long, entangled codes. This is a concrete, published justification for our parsimony term (§5.2) and gives a specific functional form to copy.
     - **Primitive recovery under partial observability.** NEO recovers primitive-level codes *even when some primitives never appear in isolation* in training — they only ever occur inside composite changes. This is strong evidence for H1/H3: a system under compositional + MDL pressure can disentangle reusable units it never saw alone. Their **compositional-OOD** and **length-OOD** splits (controlled by a parameter α governing how often short programs appear) are a template for how we should stress-test transfer.
   - **How our project differs from L2T (the delta that keeps us novel):** NEO is a *single* neural theorizer learning one codebook by gradient descent with a shared transition model. We replace that with (a) *multiple, deliberately divergent* populations under (b) *pure evolutionary reward* (no differentiable executor, no program supervision) that (c) *communicate* recovered abstractions across lineages through a *constrained channel*. In L2T terms: we are testing whether **several theorizers that each theorise the world differently can teach each other their primitives**, and whether a bandwidth-limited channel makes those taught primitives better. L2T supplies the single-agent theory; we add the multi-agent, communication, and evolutionary axes.

**Novelty to preserve:** the combination of (a) *pure reward* evolutionary populations, (b) *deliberately divergent* lineages, (c) a *constrained DSL channel* as the transfer mechanism, and (d) framing the whole thing as **multi-agent theory induction in the L2T sense** — theorizers sharing recovered primitives. Keep these explicit in the code structure so the contribution stays legible.

---

## 3. Compute budget & ground rules

Target the ARC Prize Kaggle environment so the work stays portable to the real competition later, but do development on whatever local hardware is available.

- **Kaggle competition limits (as of 2026 season — verify current values at submission time):** offline only (no internet at runtime), a fixed GPU allocation (recent seasons: 4×L4-class GPUs, ~96GB RAM), and a hard wall-clock runtime for the full test set (~12 hours). Practical implication: **per-task compute is small** — on the order of seconds-to-a-few-minutes per task, not hours. Budget accordingly.
  - ARC Prize site & competition rules: https://arcprize.org/ and the Kaggle "ARC Prize 2026" competition page (check for current-season specifics before relying on numbers).
- **Design consequence:** favour **CPU-bound symbolic search + tiny models** over large LLM calls. A pure-symbolic evolutionary approach with no neural net at all is a legitimate and strong first version — get that working before adding any learned component.
- **Reproducibility:** fixed seeds per lineage, deterministic DSL interpreter, log everything (Section 9).

---

## 4. Data

- **ARC-AGI-1 dataset** (400 train + 400 eval tasks): https://github.com/fchollet/ARC-AGI
- Use the **training split** for evolving/searching and the **public evaluation split** as held-out. Never let the eval split influence evolution.
- **Start with a subset.** Stage 1 uses a 30-task subset of the training split, generated deterministically by the recipe in §4.1 below (depth-graded via Hodel's `solvers.py`, stratified by reasoning type). Do not hand-pick tasks ad hoc.

**Task representation:** each ARC task is a set of input→output grid pairs (the "train" demonstrations) plus held-out "test" input(s). Grids are 2D arrays of ints 0–9. Fitness is evaluated on the demonstration pairs; a candidate that satisfies all demonstration pairs is then applied to the test input for the actual answer.

### 4.1 Stage-1 subset selection (deterministic recipe — run this, don't hardcode IDs)

Do **not** rely on a fixed list of task IDs from memory — generate the Stage-1 set programmatically from the real files so it is reproducible and verifiable. The subset must be graded by *DSL depth* (how many composed primitives Hodel's reference solution uses), because depth is the axis that controls search difficulty and lets you demonstrate the divergence/communication effects cleanly.

**Step A — get ground-truth depth from `solvers.py`.** Hodel's `arc-dsl` ships one hand-written solver function per training task, named `solve_<taskid>`. Parse each solver's body and count the number of DSL primitive *calls* (equivalently, the number of intermediate assignments `x1, x2, …` before the return). This integer is your **depth proxy** `d` for that task. Bucket the 400 training tasks:

Sketch of the parser (uses Python's `ast` module — Hodel's solvers have a rigid `x1 = fn(...); …; O = fn(...); return O` shape, so assignment-counting is reliable; verify the assumption on a few solvers by eye before trusting the numbers):

```python
import ast
from pathlib import Path

def solver_depths(solvers_path: str) -> dict[str, int]:
    """Map task_id -> depth proxy d (number of DSL-call assignments
    in Hodel's solve_<taskid>, including the final O = ...)."""
    tree = ast.parse(Path(solvers_path).read_text())
    depths: dict[str, int] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("solve_"):
            task_id = node.name.removeprefix("solve_")
            d = sum(
                1
                for stmt in node.body
                if isinstance(stmt, ast.Assign)
                and isinstance(stmt.value, ast.Call)
            )
            depths[task_id] = d
    return depths

# sanity checks worth asserting:
#   len(depths) == 400                       (one solver per training task)
#   all(d >= 1 for d in depths.values())     (no empty solvers)
# then bucket: D1 = {t: d for t, d in depths.items() if d <= 2}, etc.
```

Edge cases to handle when hardening: solvers that assign non-call values (rare; the `ast.Call` guard already skips them), nested calls inside a single assignment (counts as 1, which is fine for a *proxy* — depth here is "pipeline steps," not total primitive invocations), and any future upstream renaming of the `solve_` prefix (assert the 400-count to catch it).

- **D1 (d = 1–2):** near-atomic transforms. These seed Stage 1 — a single lineage should crack them fast, giving you a working reward signal.
- **D2 (d = 3–5):** short compositions. The sweet spot where reuse of a shared fragment plausibly helps — this is where H2/H3 should first show signal.
- **D3 (d = 6–10):** genuine multi-step. Include a few as stretch tasks; mostly for Stage 3+.
- **D4 (d > 10):** exclude from Stage 1.

**Step B — tag by reasoning type.** ARC-AGI-1 has no official category labels, so derive coarse tags cheaply from grid statistics (compute per task, then group):
- *geometry* — output is a rotation/reflection/transpose of input (check by applying the 8 dihedral transforms).
- *recolour* — input and output share the same non-background cell mask but differ in colours.
- *size-change* — output dimensions differ from input (tiling, cropping, scaling).
- *object-count / selection* — output is a small grid or single colour whose value tracks the count/ranking of connected components in the input.
- *symmetry-repair / fill* — output completes or de-noises a partial pattern (output ⊇ input non-background mask).
- *other* — everything the above don't catch.
These are heuristics for *stratification only*, not ground truth; a task may match several. Their purpose is to ensure the subset spans transformation families so divergent lineages have something to diverge *about*.

**Step C — assemble a 30-task Stage-1 set, deterministically.** Sort task IDs lexicographically (stable), then select with a fixed seed:
- 10 × D1, 15 × D2, 5 × D3;
- within each depth bucket, spread across reasoning tags (aim for ≥4 tags represented per bucket, no single tag > 40% of a bucket);
- write the chosen IDs, their depth `d`, and tags to `data/stage1_subset.json` so every run is reproducible and the selection is auditable.

**Step D — sanity gate.** For each selected task, confirm Hodel's `solve_<taskid>` actually reproduces the demonstration outputs through your interpreter (from Stage 0). Drop any task whose reference solver your interpreter can't reproduce — that indicates an interpreter gap to fix before it contaminates fitness. Backfill from the same bucket/tag to keep counts.

**Why depth-graded and not random:** a random subset is mostly deep tasks that a Stage-1 single lineage can't solve at all, so you'd see a floor of zeros and learn nothing about whether communication helps. Grading by depth gives a difficulty ramp: D1 proves the reward loop works, D2 is where cross-lineage fragment transfer should first pay off, D3 stress-tests it. Keep a held-out **eval** subset built by the *same* recipe over the evaluation split for measuring generalisation (never evolve against it).

**Note on provenance:** the concrete task IDs are intentionally not listed here because they must come from the actual dataset files, not from recall — generating them via this recipe guarantees they are real and their depths are ground-truth from Hodel's solvers rather than estimated.

---

## 5. The DSL and the communication channel

### 5.1 The DSL (the "genome" alphabet)

Use **Michael Hodel's arc-dsl** (`dsl.py`) as the primitive set. Reasons: it's typed, purpose-built for ARC grids, MIT-licensed, and comes with worked solutions to validate against.

- A **candidate program** is a typed composition of DSL primitives — represent it as an AST / typed expression tree, not a raw string, so mutation and crossover respect types.
- Start with a **reduced primitive subset** (20–40 primitives) for the Stage-1 task subset to keep the search space tractable; expand later.

### 5.2 The genome & genetic operators

- **Genome:** the AST of a DSL program (plus, optionally, a set of named subroutines the lineage has "abstracted out" — its private library).
- **Mutation:** replace a subtree with a type-compatible random subtree; swap a primitive for a same-signature primitive; insert/delete a unary op; tweak an integer/colour literal.
- **Crossover:** exchange type-compatible subtrees between two parents (standard typed GP crossover).
- **Fitness (reward — no supervision):** reward is computed *only* from grid correctness, nothing else. Suggested shaped reward per candidate on a task:
  - primary: fraction of demonstration pairs solved exactly (0..1) — note this rewards *transfer across pairs*, which is L2T's whole point (a program that fits one pair but not the others has memorised, not theorised);
  - tie-breakers (small weights): per-cell accuracy on unsolved pairs (dense gradient), and an MDL/parsimony penalty proportional to program length (favours short, reusable programs — this is where "good abstractions" pressure enters).
  - This is the "reward is all you need" spine: no target programs, only outcome reward + parsimony.
  - **Adopt NEO's adaptive-length form for the parsimony term.** Rather than a flat length penalty, select the *shortest accurate* program using L2T's rule: among candidate programs of increasing length `k`, prefer the one minimising `λ_MDL^k · ℓ(y, ŷ_k)` with `λ_MDL > 1` (Baek et al., ICML 2026). Concretely: when two candidates solve the same number of demonstration pairs, the shorter one wins by a factor that grows with the length gap. This directly discourages entangled composite operations and pushes each lineage toward genuinely primitive, reusable building blocks — the property we later try to *communicate*. Make `λ_MDL` a config knob.

### 5.3 The constrained channel (the heart of the experiment)

Each lineage periodically emits **messages** and consumes messages from a shared blackboard. A message is a **DSL fragment** (a subtree / candidate subroutine) that scored well in the sender's population — "here is something that works."

Three channel variants to implement (they map directly onto the baselines in Section 7):

- **CH-NONE:** no messages. Populations fully isolated.
- **CH-CONSTRAINED:** messages are capped — bounded max fragment size (e.g. ≤ K nodes) and a bounded number of messages per epoch (e.g. top-M fragments by a reuse/fitness score). Receiving lineages inject these fragments into their gene pool (as new subtrees available for mutation/crossover, and/or as named library entries). This is H3's "narrow channel."
- **CH-UNCONSTRAINED:** the entire best-library of each lineage is shared every epoch (no size/count cap). The control that tests whether the *constraint* — not merely the sharing — is what helps.

Design the channel as a clean interface so variants are swappable via config:

```
class Channel:
    def publish(self, lineage_id, fragments): ...      # sender -> blackboard
    def receive(self, lineage_id) -> list[Fragment]: ...# blackboard -> receiver
# CH-NONE, CH-CONSTRAINED(K, M), CH-UNCONSTRAINED are subclasses/configs
```

**What exactly gets communicated is intentionally a research variable** (the user explicitly wants to experiment here). Support at least two message *payload* modes behind the same interface:
- **payload=fragment:** concrete DSL subtree injected into the receiver's pool (horizontal gene transfer).
- **payload=signal:** abstract "which primitives are paying off" — e.g. a reweighting vector over primitives that biases the receiver's mutation distribution, without handing over concrete code.
Make payload mode a config flag so both can be run.

---

## 6. System architecture

```
+-------------------+     +-------------------+     +-------------------+
|   Lineage A       |     |   Lineage B       |     |   Lineage C       |
|  (pop of ASTs)    |     |  (pop of ASTs)    |     |  (pop of ASTs)    |
|  seed=1, prims=P1 |     |  seed=2, prims=P2 |     |  seed=3, prims=P3 |
+---------+---------+     +---------+---------+     +---------+---------+
          |  publish/receive         |                       |
          +-----------+--------------+-----------+-----------+
                      |                          |
                 +----v--------------------------v----+
                 |            Blackboard/Channel        |
                 |   (CH-NONE | CH-CONSTRAINED | CH-UN) |
                 +--------------------+-----------------+
                                      |
                              +-------v--------+
                              |  DSL Interpreter|  (Hodel arc-dsl, deterministic)
                              |  + Fitness eval |
                              +-----------------+
```

- **Divergence mechanism (for H1):** give each lineage a *different* seed and, optionally, a *different primitive subset* or *different reward shaping* so they are genuinely pushed in different directions ("evolve in completely different directions"). Log which primitives each lineage converges on.
- **Islands analogy:** this is deliberately close to the classic *island model* GA with migration — say so in the writeup; the novelty is the *constrained-DSL* migration payload and the emergent-language framing, not island GAs per se.

Suggested module layout:

```
clebran/
  data/            # ARC-AGI-1 loader, subset definitions
  dsl/             # vendored/wrapped Hodel arc-dsl, typed AST, interpreter
  genome.py        # AST genome, typed mutation & crossover
  fitness.py       # reward: correctness + per-cell + MDL penalty
  lineage.py       # one evolving population
  channel.py       # Channel interface + 3 variants + 2 payload modes
  orchestrator.py  # runs N lineages, epochs, migration schedule
  metrics/         # topographic similarity, reuse rate, MDL, diversity
  baselines/       # B0..B5 runners (Section 7)
  experiments/     # configs (yaml) + run scripts
  logs/            # per-run structured logs
```

---

## 7. Baselines (do not skip — this is the experiment)

To claim "communication helps," you must hold **total compute constant** and vary only the communication. Implement all of these and run them at matched compute (same total candidate-evaluations budget):

- **B0 — single population:** one lineage, all the compute. The honest "just do GP harder" control.
- **B1 — N isolated lineages (CH-NONE), best-of ensemble:** N populations, no communication, take the union of what any solves. Tests whether ensembling alone (not communication) explains any gain.
- **B2 — N lineages + CH-CONSTRAINED (fragment payload):** the main treatment for H2/H3.
- **B3 — N lineages + CH-UNCONSTRAINED:** tests H3 (does the *constraint* matter, or just sharing?).
- **B4 — N lineages + CH-CONSTRAINED (signal payload):** tests the "communicate abstractly, not concrete code" variant.
- **(Optional) B5 — DreamCoder/Stitch-style single growing library:** centralized library learning with no multi-agent divergence, matched compute. The strongest "abstraction reuse without our idea" control. Use Stitch for tractable compression: https://github.com/mlb2251/stitch

**The headline comparisons:**
- H2 supported iff **B2 > B1** and **B2 > B0** at matched compute.
- H3 supported iff **B2 > B3** (constrained beats unconstrained sharing).
- Divergence (H1) shown iff lineages in B1 have low primitive-usage overlap.

Report mean ± variance over ≥5 seeds; ARC solve counts are noisy on small subsets, so seed variance is essential for any claim.

---

## 8. Staged roadmap

**Stage 0 — Harness (no evolution yet).**
Load ARC-AGI-1, vendor Hodel's arc-dsl, build the typed AST + deterministic interpreter, and reproduce a handful of `solvers.py` solutions to confirm the interpreter is correct. Define the 30-task Stage-1 subset **using the deterministic recipe in §4.1** (depth-graded from `solvers.py`, stratified by reasoning tag, written to `data/stage1_subset.json` with the Step-D sanity gate). *Exit criterion:* you can evaluate any AST against any task and get a correct reward, and `stage1_subset.json` exists and passes the §4.1 gate.

**Stage 1 — Single-lineage GP (B0) on the subset.**
Implement genome, mutation, crossover, fitness. Get one population solving a meaningful fraction of the subset. *Exit criterion:* B0 solves a stable, logged number of subset tasks; this is your reference line.

**Stage 2 — Multiple isolated lineages (B1) + divergence metrics.**
Run N=3–5 lineages with different seeds/primitive subsets. Implement the H1 diversity metrics. *Exit criterion:* you can *show* the lineages diverge (low primitive overlap, different solved-task sets).

**Stage 3 — Add the channel (B2, CH-CONSTRAINED, fragment payload).**
Implement the blackboard, migration schedule, fragment injection. *Exit criterion:* B2 runs end-to-end at matched compute and you have the B2-vs-B0/B1 comparison.

**Stage 4 — Ablations (B3, B4, optional B5).**
Swap channel variants and payload modes via config. Run the full matched-compute sweep over ≥5 seeds. *Exit criterion:* the H2/H3 comparison table.

**Stage 5 — Scale & (optional) neural component.**
Expand from the subset toward the full 400 training tasks and the eval split. Only now consider adding a tiny learned component (e.g. a small policy biasing mutation, or an LLM proposing fragments) — and only if it fits the Kaggle compute envelope. Keep the pure-symbolic version as the reproducible baseline.

### 8.1 Definition of done (per stage)

Each stage is complete only when every artifact exists and every logged number below is produced. Treat these as acceptance tests — do not start the next stage with any row unmet.

| Stage | Artifacts that must exist | Numbers that must be logged | Hard gate |
|---|---|---|---|
| 0 | Vendored `arc-dsl`; typed-AST interpreter; `data/stage1_subset.json` (30 IDs + depth + tags); depth-parser (§4.1 Step A) with its two assertions passing | Interpreter reproduces ≥10 hand-picked `solvers.py` solutions exactly; depth histogram over all 400 training tasks | 100% of the 30 subset tasks pass the Step-D solver-reproduction gate |
| 1 | `genome.py`, `fitness.py`, `lineage.py`; B0 runner + config; JSONL run logs | B0 solve count on the 30-task subset, mean±sd over ≥5 seeds; candidate-evaluations per solve; mean solution program length | B0 solves ≥ the D1 bucket (all 10 near-atomic tasks) on every seed — if not, fix the reward loop before proceeding |
| 2 | Multi-lineage orchestrator (CH-NONE); divergence metrics module | Pairwise Jaccard distance of primitive usage across lineages; per-lineage solved-task sets; count of tasks solved by exactly one lineage | Demonstrated divergence: mean pairwise Jaccard distance meaningfully > 0 and ≥1 task solved by exactly one lineage (else H1's premise is empty and the channel test is moot) |
| 3 | `channel.py` with CH-CONSTRAINED (fragment payload); migration schedule in config; matched-compute budgeting verified in logs | B2 vs B0 vs B1 solve rates at matched candidate-evaluations, mean±sd over ≥5 seeds; reuse rate (fraction of B2 solutions containing a received fragment) | Compute-matching audit passes: total candidate-evaluations across arms within ±1%; reuse rate > 0 (the channel is actually being used, whether or not it helps) |
| 4 | CH-UNCONSTRAINED + signal-payload variants; (optional) B5 Stitch runner; full sweep configs | The H2/H3 comparison table: B0–B4(+B5) solve rates, mean±sd, ≥5 seeds; transfer–reconstruction gap; topographic similarity trend | A written verdict on H2 and H3 (supported / refuted / inconclusive) with the table as evidence — a null verdict passes this gate; a missing verdict does not |
| 5 | Full-training-split and eval-split runs; (if attempted) neural-component ablation; reproducibility pack (seeds, configs, env) | Eval-split solve rate (never evolved against); wall-clock and $/task estimate vs the Kaggle envelope (§3) | End-to-end run fits the §3 compute envelope, or a documented gap analysis of why not |


---

## 9. Metrics & logging

Log per epoch, per lineage, to structured files (JSONL):

- **Solve rate** on subset (demonstration-exact) and, separately, held-out eval solve rate.
- **Reuse rate:** fraction of a lineage's successful programs that contain a fragment received via the channel. (Directly measures whether communication is doing anything.)
- **Divergence:** pairwise Jaccard distance of primitive-usage distributions across lineages; count of tasks solved by exactly one lineage.
- **Compositionality:** topographic similarity between message-space and meaning-space (standard emergent-comms metric — borrow the implementation from EGG). Track whether the DSL channel's usage becomes more compositional over time.
- **MDL / parsimony:** mean program length of solutions; total description length of each lineage's library.
- **Transfer–reconstruction gap (from L2T):** a program can satisfy one demonstration pair without capturing the rule. Log, per solved task, whether the winning program solves *all* demonstration pairs (true transfer) versus only the one it was fitted on (reconstruction shortcut). A widening gap is a warning that fitness is rewarding memorisation. This is the L2T "self-explainability ≠ transfer" check applied to ARC.
- **Primitive recovery (from L2T):** how many of the received/abstracted fragments correspond to genuinely primitive, single-purpose operations versus entangled composites. Where a lineage abstracts its own subroutines, check whether it recovers primitives it never used in isolation — NEO's headline evidence, and a direct probe of whether the constrained channel is distilling good units.
- **Cost:** candidate-evaluations and wall-clock per task (for Kaggle-envelope feasibility).

Everything needed to plot "B2 vs B0/B1/B3 solve rate at matched compute, mean±sd over seeds."

---

## 10. Key references (grouped, with links)

**ARC benchmark & DSL**
- ARC-AGI-1 dataset & original paper (Chollet, *On the Measure of Intelligence*): https://github.com/fchollet/ARC-AGI · https://arxiv.org/abs/1911.01547
- Michael Hodel arc-dsl (primary DSL + oracle solvers): https://github.com/michaelhodel/arc-dsl
- ARC Prize (competition, rules, current-season compute): https://arcprize.org/

**Theory induction / primitive recovery (the primary theoretical anchor — see §2.4)**
- Learning-to-Theorize (L2T) / Neural Theorizer (NEO), Baek, Lee, Baek, Lee & Ahn, ICML 2026 (oral): https://doojinbaek.github.io/publications/learning-to-theorize-the-world/ · https://arxiv.org/abs/2605.03413 · PDF https://arxiv.org/pdf/2605.03413
  - Take from it: the phenomenon/theory formalism, the transfer-not-reconstruction test, the `λ_MDL^k · ℓ(y, ŷ_k)` adaptive-length rule, and the OTIB compositional-/length-OOD evaluation design.

**Library learning / abstraction (the "keep good abstractions" leg)**
- DreamCoder (Ellis et al.): https://arxiv.org/abs/2006.08381 · code https://github.com/ellisk42/ec
- Stitch (fast library compression): https://github.com/mlb2251/stitch · https://arxiv.org/abs/2211.16605
- ArcMemo (LLM reusable-concept memory for ARC, 2025) — locate via search; conceptually adjacent.

**Emergent communication (the "constrained channel" leg)**
- Lazaridou & Baroni survey: https://arxiv.org/abs/2006.02419
- EGG framework + topographic-similarity metric: https://github.com/facebookresearch/EGG

**Evolutionary / program-synthesis context**
- Island-model GA with migration (background; standard GP text: Poli, Langdon & McPhee, *A Field Guide to Genetic Programming*, free PDF online).
- Code-evolution-for-ARC precedent (Imbue, 2026) as a sanity check that evolutionary search is competitive on ARC: https://imbue.com/research/2026-02-27-arc-agi-2-evolution/

---

## 11. Explicit non-goals & honest caveats

- **Not** chasing leaderboard SOTA. A modest subset solve rate with a *clean* H2/H3 result is the win.
- The **island-model GA with migration is not itself novel** — be honest about that in any writeup. The novel combination is: pure-reward divergent lineages + constrained-DSL channel + emergent-language framing/metrics.
- A **null result for H2 is a legitimate, reportable outcome** — the baselines exist precisely so that a null is trustworthy. Do not tune the treatment against the eval split to manufacture a positive.
- **Compositionality metrics on a hand-designed DSL** are weaker evidence of "emergent language" than in a from-scratch signaling game — note this limitation; the DSL is a constrained channel, but its primitives are given, not invented. If you later let lineages *name and abstract their own subroutines* (private libraries that get communicated), that is where genuinely emergent vocabulary appears — prioritise that extension if the emergent-language claim matters to you.
  - **L2T sharpens this into a concrete design axis.** NEO learns its primitive codebook *from observations with no program supervision* and still recovers primitive-level codes — so "invented primitives" is demonstrably achievable, not just aspirational. Two honest positions for this project: (i) **given-primitive channel** — communicate over Hodel's DSL; cleaner, faster, but the "emergent language" claim is weak because the alphabet is handed to you. (ii) **recovered-primitive channel** — have each lineage *abstract its own subroutines* out of successful programs (the private-library mechanism in §5.2) and communicate *those*; this is the true L2T-style test, where the shared vocabulary is discovered rather than given, and where topographic-similarity/primitive-recovery metrics become meaningful evidence. Recommendation: build (i) first as the working substrate, but treat (ii) as the scientifically important version, and design the channel so the payload can be either a DSL fragment (given) or a lineage-abstracted subroutine (recovered) without restructuring. NEO's compositional-OOD and length-OOD splits are the right way to prove a recovered vocabulary actually generalises rather than memorises.
- **L2T is a single-agent gradient-based system; ours is multi-agent evolutionary.** Do not assume NEO's positive results transfer automatically — pure evolutionary reward without a differentiable executor may recover primitives less reliably. That gap is itself part of what the experiment tests; report it honestly rather than assuming L2T's guarantees carry over.

---

*End of specification.*
