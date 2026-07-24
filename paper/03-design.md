# 3. The clebran design

The clebran system has six major components: a typed intermediate
representation for programs (§3.1), a deterministic interpreter with
size caps and a structural grid validator (§3.2), a typed GP engine
with phase-1 systematic seeding and adaptive operator selection
(§3.3), a foreground/background-balanced fitness function with MDL
pressure (§3.4), a per-task lineage model with a private library and a
shared channel (§3.5), and a Stitch-style compression miner that
recovers abstractions from a lineage's best programs (§3.6). The
section is a technical reference; the experimental protocol sits in
§4.

## 3.1 Programs: a linear typed IR

Programs are *linear SSA-style register programs* over Hodel's 160
typed grid primitives:

```
x0 = fn(...); x1 = fn(x0, ...); ...; return x_n
```

The same shape as Hodel's hand-written solvers, which means the
reference solvers parse *losslessly* into our IR — that losslessness
is what allows the depth-graded subset selection (§4.1) and the
correctness gate to work on real data.

Typing is a *nominal* typing of primitives plus a *union* flow-through
rule: when a primitive returns a union type, every downstream use of
the result is typed with the union. The crucial case is the
`vmirror: Piece → Piece` signature, which the union rule allows to be
fed into a `Grid` slot at the next call (because the Grid slot accepts
`Grid | Piece`). Without the union rule, typed mutation could never
build the `vmirror(I)` → crop → paste compositions that several
reference solvers require, and a substantial fraction of the
depth-graded subset would be unreachable by the GP engine. The
union-flow bug was the first diagnosed failure in passing the
Stage-1 acceptance gate (§3.7).

The IR is also used to encode the *abstraction call* — a single
program statement `("abstr", name, *args)` — that invokes a recovered
subroutine at run time, inlines its body through `interpreter._run_body`,
and costs one unit of program length for MDL purposes. The
abstraction's signature is computed from the dependencies of the
duplicated slice and registered in a per-lineage table; the typing
machinery looks up the table when typechecking the call site.

## 3.2 Deterministic interpreter

The interpreter is a small, exception-guarded evaluator with two
size caps (a max-register count, set to keep linear programs from
exploding; a max-statement count) and a structural grid validator
that returns the *first row* of the result and a structural hash
representing the grid's shape, plus a content hash of the cells, in
O(rows + width) time. The validator was the dominant cost in the
interpreter before profiling: a per-cell isinstance check ran ~80M
calls in a 32-second profile window. The O(rows + width) validator
preserves behaviour (the 399/400 reproduction rate is unchanged) and
brings throughput from ~2.8k evals/second/process to ~8.3k.

A *length-guarded fitness cache* dedupes candidate evaluations whose
programs are length ≥ 4 by a hash of the program string. Every
deduped evaluation still counts as a candidate evaluation; the cache
only removes redundant *work*, not redundant *budget*. The
verification protocol (§4.2) checks that budgets and search outcomes
are byte-identical with and without the cache enabled.

The interpreter exposes a `run_trace` function that returns every
register value as an ARC grid, used by the solver-card HTML report to
render a step-by-step execution trace of every evolved program. The
trace is also used internally by the compression miner to identify
subroutines that recur across programs (§3.6).

## 3.3 GP engine

The engine is a typed genetic programming system operating on the
linear IR. The operators are:

- **Point mutation** — flip a head to a compatible primitive, or
  perturb a constant.
- **Argument mutation** — pick a different source register or
  constant for an existing call.
- **Grow mutation** — insert a new statement at a typed position and
  rewire downstream uses to consume its output. On the linear IR,
  this is the analogue of "subtree replacement" in tree-GP.
- **Two-segment crossover** — swap a contiguous slice of statements
  between two programs, with a repair pass that re-types the splice.
- **Fragment splice** — insert a received fragment (from the channel)
  as a contiguous slice, with hole-filling by typed mutation.
- **Depth-1 / depth-2 systematic enumeration** — exhaustively enumerate
  programs of bounded length and a fixed head, used at the *phase-1
  seeding* step.

**Phase-1 systematic seeding.** The first ~5% of the budget is spent
on a deterministic closure of the depth-≤2 bucket: depth-1
enumeration over typed constants; depth-2 skeleton sweep; a
signature-niched population; and constant-polish (coordinate descent
plus bounded 2-D joint sweeps for two-coordinate needles like
crop offset + size) on the top stubs *and* compositions around the
top families. The seeding is identical across arms, so any
channel-driven gain must come from the evolutionary phase, not from
the seeding phase. We report *evolution-phase solves* separately
from seeding solves for exactly this reason.

**Adaptive operator selection.** Each operator's share of the
offspring production is set by its recent child-≥-parent success
rate, with floors. The fragment splice is the operator that adaptive
selection most often down-weights: in the K×M dose-response
(§5.3), fragment splice succeeds ~2% of the time vs ~36% for
mutation, so AOS holds it near a 3% share *regardless of how much
material the channel supplies*. AOS is the mechanism that makes
the H3 constraint test null: an adaptive learner self-constrains a
failing channel.

**Per-task RNG substreams.** Each task's trajectory is driven by
`Random(f"{seed}:{task_id}")`, so a task behaves bit-identically in
isolation and interleaved with the other 29. The isolation
*predicts* the full-run behaviour, which is the property that
makes the per-task debugging loop tractable.

**Progress-weighted task scheduling.** Generations are allocated by
proximity-to-solution instead of round-robin. Without this, near-miss
tasks were starved in the budget tail: a task that is 1 cell from
solving would not get the generations that would let a polish
mutation hit it, because the schedule moved on to a task further
from its own solution.

**Hall-of-fame restarts.** Stagnation restarts explore fresh space
but re-inject the best individual per skeleton signature, so a
restart cannot destroy polishable partial-credit stubs. Without the
hall-of-fame injection, the B0 Stage-1 gate fails (several tasks
have a unique 2-cell fragment that only appears in a single
mutation's neighbourhood; a clean restart loses the search
neighbourhood entirely).

## 3.4 Fitness

The fitness function is *pure outcome reward*: the fraction of demo
pairs a candidate program solves exactly, *tie-broken by per-cell
accuracy on the foreground and on the background separately*. The
background/foreground split is critical: on mostly-background
targets, plain per-cell accuracy lets a `canvas(ZERO, 3×3)` — a
blank grid of the right size — outscore every content-bearing
program. The split is implemented by counting, per target, the
*background colour* (the most common cell value, or the cell value
at the corners for framed tasks) and scoring the foreground and
background cell accuracies separately. The reward is then:

```
reward(p) =
  foreground_acc(p) * foreground_weight
  + background_acc(p) * background_weight
  - foreground_penalty * (1 - foreground_present(p))
```

with weights chosen so that a fully-foreground program with
background accuracy 0 still loses to a fully-correct program, and
a fully-background "all-blank" program loses to any program that
produces a non-trivial foreground.

The reward is then scaled by NEO's MDL factor:

```
final(p) = reward(p) * (λ_MDL ** -len(p))
```

with `λ_MDL = 1.05` (the value used in every reported run; see
the configuration table in §4.7 for the code default). The
factor penalises long programs; combined with the
foreground/background split, it is what makes the population
converge to the *shortest correct* program rather than the
longest-fitting one.

The fitness function is *test-exact-aware*: a candidate that solves
all demonstration pairs is then applied to the test input(s) and
the resulting grids are recorded as a `test_exact` flag. The
transfer-vs-reconstruction gap (§5.7.1) is the difference between
solving all demos (reconstruction) and reproducing the test grid
exactly (transfer). Both flags are logged for every candidate.

## 3.5 The channel and the four payloads

The channel is a blackboard shared by all lineages of a single arm.
A lineage publishes messages to the blackboard at a periodic
publish cadence (every K epochs), and reads messages that other
lineages have published since its last read. The constraint regime
imposes a *bandwidth* (K, the maximum message size in statements
or in body length) and a *rate* (M, the maximum number of messages
per lineage per epoch). Three constraint regimes are supported:
**CH-NONE** (no channel at all; the B1 control), **CH-CONSTRAINED**,
and **CH-UNCONSTRAINED** (effectively M = ∞). Four payload types
are supported.

**Fragment payload.** A *fragment* is a multi-statement slice of a
successful program, parameterised by the external inputs it reads.
A lineage publishes its best-performing fragments; receivers
splice them in as a contiguous block with hole-filling by typed
mutation. This is the original §3 payload, used by B2/B3/B4.

**Signal payload.** A *signal* is a discrete identifier that names
a target difficulty bucket, used as a routing hint rather than a
code fragment. Signal payloads are the B4 arm; they test the
*abstract-communication* hypothesis (H3 variant) — that a *less*
informative channel might nonetheless be useful as a routing signal
— and have been used in the Stage-4 B0–B4 sweep.

**Recovered-primitive payload.** A *recovered abstraction* is a
subroutine that the publishing lineage has mined from its own
solved programs using the compression miner (§3.6), parameterised
by its external inputs, and registered in the shared abstraction
table. A *received* abstraction is installed into the receiving
lineage's local library as a new primitive with the mined
signature. The reuse rate is the fraction of solves that contain
at least one received abstraction; the *received-used* metric is
the average number of received abstractions used per solve (the
NEO-style "used a primitive it was handed and never derived"
signal). This is the B6/B7 arm and is the §11 scientifically
important variant.

**Curriculum payload.** A *curriculum* is an ordered sequence of
synthetic tasks generated by the publishing lineage from its own
DSL: a program that uses a target abstraction is sampled, run on
random input grids through the interpreter, and the resulting
(input → output) demonstration pairs form a teaching task. The
teaching tasks are ordered by the prerequisite structure of the
abstractions they were synthesised from (a `score` field in the
task record). A *curriculum-aware* receiver carries a
library-persistent state and gates deeper tasks behind their
prerequisites being solved. The reuse rate is not applicable to
curriculum payloads (no fragment or abstraction is transmitted);
the engagement metric is *aux_received* (teaching tasks received
per lineage) and *aux_solved* (of those, how many the student
solved). This is the B8/B9 arm, the §7b hypothesis.

## 3.6 Compression miner

The compression miner is a Stitch-style duplicated-slice miner. Given
a set of programs (typically, the top-k by fitness from a lineage's
hall of fame), it finds dependency-closed subroutines that recur
across at least two programs, with the same primitives, the same
wiring, and the same constants up to a substitution. The candidate
subroutines are parameterised by the inputs they read that come
from outside the slice; the resulting `Abstraction` is registered in
the lineage's library as a new primitive with a typed signature. The
rank order is by *compression ratio*: the number of statements
removed from the rewritten programs, minus a body-length penalty.

**Configuration.** B5 (the central-library control, §5.5) calls
`mine_own_abstractions(max_new=8, min_size=2, max_size=4)` every
`mine_every=5` epochs (`clebran/baselines/b0.py`). The underlying
`mine_compressing` requires `min_occurrences=2` — a subroutine must
appear in at least two of the lineage's best programs to be
considered. The 5-epoch period is unusually frequent for a library-
learning system; it is the choice that makes B5 grow its library
aggressively. A sensitivity check (varying `mine_every` from 1 to
20) is a natural follow-up; the paper uses `mine_every=5` because
the comparison with the multi-agent arms requires the central-
library mechanism to have a comparable number of mine calls per
run.

On Hodel's 400 reference solvers, the miner recovers meaningful
subroutines unsupervised: `ofcolor(I, leastcolor(I))`, `argmax(
objects(I, …), size)`, `remove(ZERO, palette(I))`, and so on. The
topographic similarity of the resulting vocabulary is 0.53 over
arity-1 Grid abstractions — a real compositional signal. The miner
is also the component that B5 uses: B5 is essentially a single
population that periodically runs the miner over its hall of fame
and adds the top compression-ratio abstractions to its library. The
fact that B5 dominates the multi-agent arms is the headline result
of §5.5.

## 3.7 A note on rig-evidence

The spec's Stage-1 acceptance gate — B0 solves all 10 near-atomic
tasks on *every* seed — forced a series of mechanisms (union-type
flow-through, foreground/background-balanced reward, hall-of-fame
restarts, per-task RNG substreams, progress-weighted scheduling,
adaptive operator selection) that are now part of the rig
described in §3.1–§3.6. The Stage-1 debugging trail is documented
in detail in §6.3, where the "what it took to make the rig
reliable" story belongs. Every fix is identical across arms, so
the H2/H3 comparison is not biased by which fix landed first.
