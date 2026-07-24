# Related-work and positioning review

**Reviewer:** 03 (related-work)
**Date:** 2026-07-23
**Files read in full:** `00-abstract.md`, `01-introduction.md`, `02-related-work.md`, `03-design.md`, `04-methods.md`, `05-results.md`, `06-discussion.md`, `07-limitations.md`, `08-conclusion.md`, `references.md`, `README.md`.

The paper's related-work section is competent and well-organised, but has three
real holes: a missing ARC-specific comparison that is its closest neural
neighbour, a missing compression-on-ARC comparison that the "intelligence as
MDL" thesis needs, and a citation in `references.md` that is almost certainly
hallucinated. The L2T/NEO delta is mostly fair but slightly over-attributes
three of its four "borrowed ideas" to NEO, and the clebran-vs-DreamCoder
positioning of B5 is the single biggest framing risk in §2.

---

## 1. Top 3 missing citations

### 1.1. Akyürek et al. (2024) — Test-Time Training for ARC

**Should go in:** §2.1 (DSL program synthesis for ARC), and again briefly in
§6.4 / §7 where the scope claim is made.

**Citation:** Akyürek, E., Damani, M., Zweiger, A., Qiu, L., Guo, H., Pari, J.,
Kim, Y., & Andreas, J. (2024/2025). *The Surprising Effectiveness of Test-Time
Training for Few-Shot Learning.* arXiv:2411.07279. (Second-place paper award
at the ARC Prize 2024; semi-private 47.5%, public 53% at 8B params, 61.9% when
ensembled with program synthesis.)

**Why:** The paper currently treats the Kaggle ARC Prize 2024–2025 winners as
"ensemble neural approaches that sit orthogonally to the question this paper
asks" (§2.1, line 36–38). The Akyürek line is the one that *isn't*
orthogonal: it is also a small-system study, also measures acquisition cost
(test-time training updates per task), also reports a transfer/reconstruction
distinction, and is the second-place paper award. The clebran paper's claim
that it is "deliberately pre-neural so that acquisition cost is metered, not
purchased" (§6.1) is in direct conversation with TTT — both are bets about
*where* on the curve between pretraining and inference-time compute a small
system should sit. The clebran paper should either contrast itself with TTT
or acknowledge that the TTT line is a more recent, better-instrumented
position with the same thesis. As written, the clebran paper writes the
neural ARC community off in a single sentence, which is the kind of
positioning move reviewers penalise.

### 1.2. Liao & Gu (2025) — CompressARC

**Should go in:** §2.2 (library learning / MDL) and §6.4 (scope), as the
direct competitor on the "intelligence as compression" axis.

**Citation:** Liao, I., & Gu, A. (2025). *ARC-AGI Without Pretraining*
(CompressARC). arXiv:2512.06104; 3rd place, ARC Prize 2025. 76K parameters,
no pretraining, no ARC training-set, solves 20% of the public evaluation set
by minimising a variational description length of the target puzzle.

**Why:** CompressARC is the *exact* prior the clebran paper should be
sitting next to. Both projects argue for "compression-driven acquisition",
both are deliberately small, both explicitly inherit from the MDL / Solomonoff
line. CompressARC scores 20% on the *public evaluation split* — a split
clebran has not touched (see §7 "no eval-split generalisation"). Without
citing CompressARC, the clebran paper cannot claim to be testing the
"intelligence as compression" hypothesis; with it, the paper has a clean
third-party benchmark for "is clebran's central library doing something
CompressARC isn't?". The two systems are *not* identical (CompressARC
inference-time-adapts a single neural net; clebran evolves programs
symbolically), but their MDL foundations are the same and the review will
expect the comparison. A single sentence in §2.2 plus a one-line entry in
the scope claim of §6.4 is sufficient.

### 1.3. Bouchacourt & Baroni (2018) — How agents see things

**Should go in:** §2.3 (emergent communication), immediately after the
topographic-similarity paragraph (around line 78).

**Citation:** Bouchacourt, D., & Baroni, M. (2018). *How agents see things:
On visual representations in an emergent language game.* EMNLP 2018, pages
981–985. arXiv:1808.10696.

**Why:** This is the canonical demonstration that *successful emergent
communication does not entail compositionality*: Bouchacourt & Baroni show
that agents establish successful communication by inducing visual
representations that align with each other but not with the conceptual
properties of the input. This is *exactly* the same null the clebran paper
is reporting in §2.3 (bandwidth-limited channels between divergent agents
do not, in this substrate, induce better compositionality at matched
compute) and the H3 null in §5.3. The clebran paper should cite the
Bouchacourt & Baroni result as the original demonstration of the
"successful communication ≠ compositional communication" gap; the current
related work only cites the topographic-similarity metric and its
Lazaridou/Baroni operationalisation, not the result. The clebran data are
a *typed symbolic re-instantiation* of the Bouchacourt & Baroni finding;
the paper should say so explicitly.

**Two runner-ups** that are also worth flagging in this slot:

- **Li & Bowling (2019)**, *Ease-of-Teaching and Language Structure from
  Emergent Communication*, NeurIPS 2019 (arXiv:1906.02403). Canonical
  reference for the topsim–generalisation decoupling: shows that topsim
  rises in the "reset" regime, but also that topsim does not perfectly
  predict task transfer. Pairs naturally with the §2.3 topsim paragraph.
- **Chaabouni et al. (2020)**, *Compositionality and Generalization In
  Emergent Languages*, ACL 2020. The clearest empirical demonstration
  that compositional structure (as measured by various proxies) is
  decoupled from generalisation. The clebran paper's H3 null lives in
  this paper's empirical envelope.

---

## 2. L2T/NEO delta critique

The §2.4 framing is the single most important positioning move in the
related-work section, and the delta is *mostly* fair, but has three real
defects.

### 2.1. Three of the four "borrowed ideas" are not L2T's

The paper presents four L2T ideas that "inform the clebran design directly":
*theory is an executable program*, *transfer not reconstruction*,
*adaptive MDL-penalised length*, and *primitive recovery under partial
observability*. Of these:

- **"Theory is an executable program over reusable primitives"** is the
  *DreamCoder* framing (Ellis et al., 2020; 2021). L2T/NEO inherits it
  explicitly: the NEO paper's "Language of Thought" is in the same
  lineage as DreamCoder's wake-sleep Bayesian program induction.
  Attributing the framing to L2T over-attributes.
- **"Adaptive MDL-penalised program length"** is also DreamCoder's.
  DreamCoder 2020/2021 has the same `λ^len(p)` factor. The clebran
  paper should say "the L2T/NEO MDL factor is the same `λ^len(p)` factor
  DreamCoder introduced; the clebran fitness function inherits the same
  functional form".
- **"Transfer, not reconstruction, is the real metric"** *is* the L2T
  contribution and is correctly attributed. NEO's specific demonstration
  is the canonical reference and the clebran teach→test probe (§5.7.1)
  operationalises it at the level of whole concepts. This attribution
  is fair.
- **"Primitive recovery under partial observability"** is the L2T
  compositional-OOD claim. The clebran paper's H1 and H3 are about
  *communication* between populations, not about *primitive recovery
  under partial observability*, and the clebran experiment does not run
  the L2T compositional-OOD split (it is listed as a limitation in §7).
  The connection is loose and is more "shared philosophical root" than
  "borrowed idea".

**Concrete fix.** Re-cast the four "L2T ideas" as: (a) the L2T framework
*re-states* the DreamCoder/Stitch theory-as-program framing in a neural
setting, and clebran inherits the same framing; (b) L2T's *specific*
contribution is the transfer-vs-reconstruction decomposition, which
clebran operationalises directly; (c) the MDL factor and primitive
recovery are L2T's *re-use* of DreamCoder concepts, not L2T inventions.
This avoids the appearance of over-attribution and is more honest
intellectually.

### 2.2. The "shared transition model" attribute is correct, but the substrate change deserves more weight

The paper says NEO is a "single neural theorizer learning one codebook by
gradient descent with a shared transition model". The "shared transition
model" line is right (NEO uses a shared neural transition model to execute
candidate programs and provide a decode-encode ground-truth signal). But
the clebran design's substrate change is *bigger* than the delta suggests:

- NEO is *probabilistic* and uses test-time sampling (the paper gives
  NEO a compute budget at inference and samples hundreds of candidate
  theories).
- NEO operates over *latent* programs, decoded back to observations
  through a state-grounding constraint.
- NEO's "single codebook" is *learned* by gradient descent on a
  variational MDL objective; clebran's codebook is *mined* by
  anti-unification over best programs.

These are not just "evolution vs gradient" — they are three distinct
substrate decisions (probabilistic vs deterministic, latent vs symbolic,
learned vs mined) that the paper could call out as a single "substrate
delta" rather than distributing across the four borrowed ideas. The
cleaner framing is: *NEO and clebran are both instantiations of
DreamCoder-style library learning, but on opposite sides of the
neural/symbolic boundary; their shared scientific question is whether
the recovered vocabulary transfers, and their answers differ
accordingly.*

### 2.3. The delta is fair; the framing could be sharper

The actual delta — multiple populations, pure evolutionary reward,
communication, constrained channel — is fair and well-stated. Two
improvements:

- Add a fifth axis: *iterated vs single-round*. The clebran design runs
  one round of communication; the L2T/NEO framework is implicitly
  iterated (gradients are taken across many samples and many training
  episodes). The clebran paper's §7 lists the single-round as a
  limitation; the related-work could call this out as a fifth delta.
- The "constrained channel" delta is the genuinely novel one and
  deserves the most ink. The §2.4 paragraph spends most of its
  paragraphs on the *borrowed* ideas; the constrained channel is
  one sentence. Move it up.

### 2.4. Transfer-metric attribution: correct, but the broader lineage deserves one sentence

The paper correctly attributes "transfer, not reconstruction" to L2T/NEO
(§2.4, line 116–125). But the principle that *test-exact* (i.e. transfer)
is the right metric is older: DreamCoder reports test-exact transfer on
held-out tasks in the same setting, and the continual-learning literature
has long argued that reconstruction is the wrong endpoint. The clebran
paper should acknowledge that L2T is *the paper* that operationalised the
distinction in a primitive-recovery setting, but is not its inventor. One
sentence in §2.4 is enough.

---

## 3. Positioning problems

### 3.1. B5 vs DreamCoder is the single biggest framing risk

§2.2 (line 51–54) and §5.6 (line 245–248) repeatedly call B5 "essentially a
DreamCoder/Stitch learner" and "the DreamCoder/Stitch control". The
comparison is *not* fair as stated:

- **DreamCoder** uses a *neural recognition model* (a "wake-sleep" trained
  recognition network) to guide search. B5 has no neural component.
- **Stitch** uses an *anti-unification miner* plus a *type-directed
  rewriter*; B5's compression miner is Stitch-style (the paper says this
  explicitly in §3.6), but the IR is linear-SSA not lambda-calculus and
  the abstractions are not as compositionally structured.
- The "wake-sleep loop" is a DreamCoder-specific mechanism (iterating
  between wake, sleep-G, sleep-R phases). B5 runs the miner
  *periodically* on the hall of fame, which is closer to a one-shot
  Stitch-style re-write than a wake-sleep loop.

The framing should be: *"B5 is a Stitch-style learner, not a DreamCoder-
style learner: it has no neural recognition model, its library is
grown by periodic anti-unification mining, and the wake-sleep
back-coupling is absent. The DreamCoder/Stitch line is the closest
pre-neural library-learning prior art; B5 is the clebran project's
instantiation of that prior."* The current "essentially a
DreamCoder/Stitch learner" overclaims what B5 is and could draw a
challenge from a DreamCoder reviewer.

### 3.2. The ArcMemo comparison is honest but under-leverages the analogy

The §2.1 ArcMemo paragraph is fair: it acknowledges ArcMemo is
LLM-mediated, retrieval-based, and that clebran is "intentionally
pre-neural so that acquisition cost is metered, not purchased." But the
analogy is *closer* than the paper makes it, and the paper should make
this productive rather than dismissive:

- ArcMemo's "Program Synthesis" (PS) memory format is the *typed,
  modular, reusable abstraction* that clebran's library also is. The
  shapes are the same; the substrate is different.
- ArcMemo's "concept-level memory" with selective retrieval is the
  functional analogue of clebran's per-lineage library + AOS
  down-weighting of failing fragment splice. Both are
  "selective-retrieval with adaptive gating" mechanisms.
- The honest contrast is: *ArcMemo's memory is text and is retrieved by
  LLM-mediated inference; clebran's memory is symbolic and is
  retrieved by typed GP search. The "what to do with a concept" loop
  is the same; the "how to find a concept" loop is different.*

One paragraph is enough. As written, the ArcMemo paragraph reads as a
defensive dismissal, which is a positioning risk in a paper that
explicitly positions itself as "the closest conceptual cousin" to
ArcMemo (line 30).

### 3.3. The "constraint doesn't help" finding has a missing interlocutor

The §2.3 paragraph and §5.3 dose-response make a strong empirical claim:
bandwidth-limited channels between divergent agents do not, in this
substrate, induce better compositionality. The claim is in direct
contradiction with the *information-bottleneck theory of language*
(Kirby, Tamariz, Smith, & Cornish 2015; Brighton & Kirby 2006), which
argues compression pressure *does* drive compositional structure in
human languages. The clebran paper's H3 null is in fact a *clean
empirical refutation* of the Kirby et al. cultural-evolution story in
a typed-symbolic substrate, and the paper should say so. The current
text frames the null as a refutation of the "naive information-
bottleneck story" but does not name Kirby, Brighton, or the cultural
language-evolution literature. This is a real gap: a reader who knows
the information-bottleneck literature will want to know that the
authors know it too.

### 3.4. The §2.5 "multi-agent program synthesis" paragraph is thin

§2.5 cites Poli et al. (2008) on GP, Potter & De Jong (1994) on
cooperative coevolution, and Skolicki & De Jong (2005) on island
models. These are the *correct* ancestor references but the paragraph
does not engage with the modern multi-agent / population-based
literature:

- **Population-Based Training (PBT)** (Jaderberg et al., 2017) — the
  closest modern analogue: hyperparameter-sharing across a population
  of learners. PBT is in the lineage of island models but is
  neural-network-native.
- **Quality-Diversity (QD) algorithms** (MAP-Elites; Cully 2019;
  Lehman & Stanley 2011) — the modern evolutionary-computation
  literature on generating *diverse* rather than *best* solutions.
  Clebran's H1 (lineages diverge) is exactly the QD premise; the
  paper should cite the QD literature when it says so.
- **Federated learning** (McMahan et al., 2017) — the modern
  distributed-learning analogue of "many learners share a parameter
  server". Not a perfect fit (clebran's channel is a blackboard, not
  parameter averaging), but the structural parallel is close enough to
  deserve a sentence.

None of these are blocking, but a one-sentence acknowledgement in §2.5
would make the multi-agent framing sharper and would let the paper
place its AOS mechanism in the right lineage.

---

## 4. Missing framings

The paper would benefit from at least a one-sentence acknowledgement of
each of the following literatures:

1. **Information-bottleneck / cultural-evolution theory of language**
   (Kirby et al. 2015; Brighton & Kirby 2006). The clebran H3 null is
   in this literature and should engage with it (see §3.3 above).
2. **Compression-as-cognition / MDL / Kolmogorov complexity**
   (Schmidhuber 1997; Li & Vitányi *An Introduction to Kolmogorov
   Complexity and Its Applications*, any edition). The paper uses
   `λ_MDL` in the fitness function and "compression" in the
   library-mining section without ever citing the prior. One sentence
   suffices.
3. **Test-time training / adaptation** (Sun et al. 2020;
   Akyürek et al. 2024). The dominant post-2024 paradigm for ARC; see
   §1.1 above.
4. **Quality-Diversity evolutionary algorithms** (Cully 2019; Lehman
   & Stanley 2011). Clebran's H1 is the QD premise.
5. **Compositional generalisation benchmarks** (SCAN, Lake & Baroni
   2018; COGS, Kim & Linzen 2020; gSCAN, Ruis et al. 2020). The
   clebran paper's negative-transfer result in §5.7.1 is in this
   literature and the §6.4 capability audit ("compositional
   generalisation to novel combinations: missing") sits next to it.
6. **Bayesian program learning lineage** (Tenenbaum 1999; Goodman et
   al. 2008). L2T/NEO and DreamCoder are in this lineage; clebran's
   compression miner is too. One sentence in §2.4 acknowledges the
   shared ancestor.
7. **Negative transfer** (Caruana 1997; Standley et al. 2020). The
   clebran 8b / "irrelevant teaching hurts" result is a negative-
   transfer result and should be cited as such. The §6.4 discussion
   would benefit from this anchor.

---

## 5. Citation accuracy

I verified the arXiv IDs and titles of every reference where possible.
Four real issues:

### 5.1. Reference 25 (ArcMemo) — wrong on every field

**Citation as written:** "Wang, A., Bowman, S., & Pavlick, E. (2025).
*ArcMemo: Abstract Reasoning with Compositional Memory.*"

**What it actually is:** Ho, M., Si, C., Feng, Z., Yu, F., Yang, Y.,
Liu, Z., Hu, Z., & Qin, L. (2025). *ArcMemo: Abstract Reasoning
Composition with Lifelong LLM Memory.* arXiv:2509.04439. Published
Sep 2025; the second-listed author of the paper is Chen Si and
Lianhui Qin is the last author. The arXiv:2509.04439 ID and the
"Abstract Reasoning Composition" / "Lifelong LLM Memory" title are
both confirmed against the arXiv listing and against the
emgentmind.com summary.

**Diagnosis:** The "Wang, Bowman, Pavlick" author list is the
author list of a *different* paper — possibly the 2019 ERASER
benchmark paper, or the Linzen/Talbar et al. compositional
generalisation line. It is not the ArcMemo author list. This is a
**hallucinated citation** and the most urgent fix in the
bibliography. The bibliography entry should be replaced with the
Ho et al. citation, the arXiv ID, and the correct title.

### 5.2. Reference 7 (Kiela, 2019) — title doesn't match any real paper

**Citation as written:** "Kiela, D. (2019). *Lazaridou & Baroni, and
the compositionality challenge in emergent communication.*"

**What it actually is:** No paper with this exact title exists in
the EC literature. The closest papers are:

- Brighton & Kirby (2006), "Systems generating compositional
  language", which introduces topographic similarity.
- Lazaridou, Hermann, Tuyls, & Baroni (2018), "Emergence of
  Linguistic Communication from Referential Games with
  Symbolic and Pixel Input", which operationalises topsim for
  EC.
- Chaabouni, Kharitonov, Bouchacourt, Dupoux, & Baroni (2020),
  "Compositionality and Generalization In Emergent Languages",
  ACL 2020, which is the closest to the cited title but is by
  Chaabouni et al. (not Kiela) and is from 2020 (not 2019).

**Diagnosis:** This looks like a hallucinated or wrongly-attributed
citation. The paper has "(Citation of the topographic-similarity
discussion.)" as its one-line description, which is a hint that
the author did not have a specific paper in mind. Replace with
the Brighton & Kirby 2006 / Lazaridou et al. 2018 / Chaabouni et
al. 2020 trio. The clebran paper's argument does not need a
Kiela-cited reference; it needs the canonical topographic-
similarity references.

### 5.3. Reference 8 (Baek et al., L2T/NEO) — title is wrong

**Citation as written:** "Baek, D., Lee, S., Baek, J., Lee, M., & Ahn,
S. (2026). *Learning to Theorize: Improving Generalization and
Compositionality via Neural Theorizer (NEO).* ICML 2026 oral.
arXiv:2605.03413."

**What it actually is:** Baek, D., Lee, G., Baek, J., Lee, H., &
Ahn, S. (2026). *Learning to Theorize the World from Observation.*
ICML 2026 oral, Jul 9 2026. arXiv:2605.03413 (submitted 5 May
2026). The author surnames are correct but the first names
("Gyubin" and "Hosung", not "S." and "M.") are omitted, and the
arXiv ID and ICML oral status are correct. The title is
**wrong**: the actual title is "Learning to Theorize the World
from Observation" (not "Learning to Theorize: Improving
Generalization and Compositionality via Neural Theorizer (NEO)").

**Diagnosis:** The title appears to be a confabulation that
inferred "Improving Generalization and Compositionality via
Neural Theorizer (NEO)" from the paper's substantive claims
(NEO is presented as a "Neural Theorizer" that "induces latent
programs ... enabling explanation-driven generalization"). The
actual paper's title and abstract are on arXiv and the ICML
2026 oral listing; both confirm "Learning to Theorize the
World from Observation". Fix the title and add the first
names.

### 5.4. Reference 21 (Garcia-Piqueras & Hernández-Orallo, 2021) — venue is right; consider also citing the 2023 ML-journal follow-up

**Citation as written:** "Garcia-Piqueras, M., & Hernández-Orallo,
J. (2021). *Optimal Teaching Curricula with Compositional
Simplicity Priors.* ECML-PKDD 2021."

**What it actually is:** The title and venue are correct. The
authors also have a 2023 *Machine Learning* journal paper
(*Heuristic search of optimal machine teaching curricula*,
Mach Learn 112:4049–4080, 2023) which is the longer, heuristic-
search version of the same framework. The 2023 paper is the
more comprehensive citation for the "MDL-style prior picks the
teaching set" claim that §2.6 makes.

**Diagnosis:** The 2021 ECML-PKDD citation is fine. For
completeness, also cite the 2023 ML journal follow-up.

### 5.5. Reference 9 (EGG framework) — software citation is fine; consider also citing the Kharitonov et al. paper

**Citation as written:** EGG framework. (2020).
https://github.com/facebookresearch/EGG.

**What it actually is:** A software citation. The EGG framework
was introduced in Kharitonov, Chaabouni, Bouchacourt, & Baroni
(2020), "EGG: a toolkit for research in Emergence of lanGuage in
Games", arXiv:1907.00852. The clebran project does adopt the
*topographic-similarity* and *discrete-channel* framing from
EGG, so a primary citation of the EGG paper is appropriate
alongside the software link.

**Diagnosis:** Not wrong, but under-cited. Add the Kharitonov et
al. paper.

### 5.6. References 4 (DreamCoder), 5 (Stitch), 6 (Lazaridou & Baroni), 15 (Dennis et al. PAIRED), 16 (Parker-Holder ACCEL), 18 (Narvekar), 19 (Zhu), 20 (Liu et al.), 22 (Kirkpatrick), 23 (Schwarz), 24 (Wang et al. Dataset Distillation), 26 (ARC Prize)

Verified: titles, authors, years, and arXiv IDs are correct. No
issues.

---

## 6. Self-citation and project documentation

The paper uses `[exp: YYYY-MM-DD_arm_name]` to cite experiment
READMEs (e.g. `[exp: 2026-07-22_b5_central_library]` in §5.6,
line 271). This is workable for a project-release format but is
unusual for an academic paper, and three improvements would make
it more reviewer-friendly:

1. **Add a single project URL footnote at the first occurrence** (e.g.
   in §1.4 or §3.7). A paper that cites its own experiment
   directories without a URL makes the reader hunt for the repo.
2. **Promote the experiment directory references to a per-experiment
   appendix (Appendix B)**, or a single "Experiment Manifest" table
   that lists each `[exp: ...]` tag with one line of description
   (arm, seeds, budget, link). This is the cleanest way to handle
   self-citation in a release-style paper.
3. **The `FINDINGS.md`, `roadmap.md`, and `README.md` references** in
   the paper's `README.md` are not currently cited in the paper body
   itself. If the paper is going to be released alongside the repo,
   add one footnote at the abstract that says "all data, logs, and
   experiment READMEs are at `<repo URL>`" and remove the inline
   `[exp: ...]` tags in favour of the Appendix B table.

The current style works for a release format and is honestly a
reasonable convention. The above are quality-of-life improvements
that a reviewer is likely to ask for, not correctness issues.

---

## 7. One-line summary

**The single most important related-work change is to fix the
hallucinated ArcMemo citation and add CompressARC (Liao & Gu 2025)
and Akyürek et al. 2024 as the two missing ARC-specific neural
references; the clebran paper's "intelligence as compression" and
"small-system acquisition cost" theses are both in direct
conversation with these two systems, and the paper cannot
credibly position itself without them.**
