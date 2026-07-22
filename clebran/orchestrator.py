"""Runs N lineages with a channel between them (§6).

One epoch = every lineage steps one generation on each of its unsolved
tasks, then the channel exchange runs (publish → receive). Total
candidate-evaluations across all lineages are capped at `budget` so every
arm (B1–B4) is compute-matched with B0 (§7).
"""
from __future__ import annotations

import random

from .baselines.common import RunLog, run_prefix, subset_pool, subset_tasks
from .channel import Channel, Message
from .fitness import Evaluator
from .lineage import Lineage
from .metrics.divergence import pairwise_jaccard, uniquely_solved
from .metrics.recovery import abstraction_stats
from .curriculum import prerequisite_curriculum

# cap on how many received curriculum tasks a lineage will take on, so
# learning from them can't crowd out its real tasks' budget
_MAX_AUX_TASKS = 12


def make_lineages(
    n: int,
    seed: int,
    tasks,
    pool: list[str],
    pop_size: int,
    drop_frac: float = 0.2,
    lam_mdl: float = 1.05,
) -> list[Lineage]:
    """Divergence levers (§6): distinct seed + distinct primitive sub-pool
    per lineage (each drops a random `drop_frac` of the full pool)."""
    lineages = []
    for i in range(n):
        rng = random.Random(seed * 1000 + i)
        drop = set(rng.sample(pool, int(len(pool) * drop_frac))) if n > 1 else set()
        sub = [p for p in pool if p not in drop]
        lineages.append(
            Lineage(
                lineage_id=f"L{i}",
                pool=sub,
                tasks=tasks,
                seed=seed * 1000 + i,
                pop_size=pop_size,
                evaluator=Evaluator(lam_mdl=lam_mdl),
            )
        )
    return lineages


def _publish(lin: Lineage, chan: Channel, max_frag_size: int) -> None:
    if chan.payload == "signal":
        usage = lin.primitive_usage()
        if usage:
            total = sum(usage.values())
            chan.publish(lin.lineage_id, [
                Message(
                    sender=lin.lineage_id,
                    payload_kind="signal",
                    signal={k: v / total for k, v in usage.items()},
                    score=len(lin.solved_tasks()),
                )
            ])
        return
    if chan.payload == "curriculum":
        # "show what you learned": for each solved program, generate its
        # *ordered* prerequisite curriculum — a task for each sub-abstraction,
        # simplest first — and share it. Score = shallowness, so under the
        # constraint the most fundamental prerequisites cross first (teach the
        # building blocks before the composition).
        msgs = []
        for _task, prog in lin.solved_programs(real_only=True):
            curr = prerequisite_curriculum(
                prog, lin.curriculum_rng, abstractions=lin.abstractions,
                n_pairs=4,
            )
            depth_max = max((d for d, _ in curr), default=1)
            for depth, gt in curr:
                msgs.append(Message(
                    sender=lin.lineage_id, payload_kind="curriculum",
                    task=gt, score=float(depth_max - depth + 1),
                ))
        chan.publish(lin.lineage_id, msgs)
        return
    if chan.payload == "abstraction":
        # grow the lineage's private vocabulary from its own solutions
        # (offer every subroutine that helped), then publish the home-grown
        # ones — the constraint decides what crosses.
        lin.mine_own_abstractions(max_new=8, max_size=max_frag_size)
        home = lin.home_abstractions()
        home.sort(key=lambda t: t[1], reverse=True)
        chan.publish(lin.lineage_id, [
            Message(
                sender=lin.lineage_id,
                payload_kind="abstraction",
                abstraction=a,
                score=score,
            )
            for a, score in home
        ])
        return
    lin.harvest_fragments(max_size=max_frag_size)
    home = [e for e in lin.library if not e.received]
    home.sort(key=lambda e: (e.score, e.uses), reverse=True)
    chan.publish(lin.lineage_id, [
        Message(
            sender=lin.lineage_id,
            payload_kind="fragment",
            fragment=e.frag,
            score=e.score,
        )
        for e in home
    ])


def _receive(lin: Lineage, chan: Channel) -> int:
    msgs = chan.receive(lin.lineage_id)
    n_used = 0
    signals: list[dict] = []
    for m in msgs:
        if m.payload_kind == "fragment" and m.fragment is not None:
            lin.add_fragment(m.fragment, score=m.score, received=True)
            n_used += 1
        elif m.payload_kind == "abstraction" and m.abstraction is not None:
            if lin.install_abstraction(m.abstraction, received=True, score=m.score):
                n_used += 1
        elif m.payload_kind == "curriculum" and m.task is not None:
            # add a received teaching task, capped so it can't swamp the budget;
            # source + score let the order-aware learner gate it in prerequisite
            # order (fundamentals — higher score — unlock first)
            if len(lin.aux_task_ids) < _MAX_AUX_TASKS and lin.add_task(
                m.task, source=m.sender, score=m.score
            ):
                n_used += 1
        elif m.payload_kind == "signal" and m.signal:
            signals.append(m.signal)
            n_used += 1
    if signals:
        blend: dict[str, float] = {}
        for s in signals:
            for k, v in s.items():
                blend[k] = blend.get(k, 0.0) + v / len(signals)
        lin.apply_signal(blend)
    return n_used


def run_multi(
    arm: str,
    channel: Channel,
    seed: int,
    n_lineages: int = 3,
    budget: int = 500_000,
    pop_size: int = 100,
    max_frag_size: int = 4,
    run_name: str | None = None,
) -> dict:
    tasks = subset_tasks()
    pool = subset_pool()
    lineages = make_lineages(n_lineages, seed, tasks, pool, pop_size)
    log = RunLog(run_name or f"{run_prefix()}{arm.lower()}_seed{seed}")
    log.write({
        "event": "start", "arm": arm, "seed": seed, "budget": budget,
        "n_lineages": n_lineages, "pop_size": pop_size,
        "channel": type(channel).__name__, "payload": channel.payload,
        "pools": {l.lineage_id: len(l.ops.pool) for l in lineages},
    })

    def total_evals() -> int:
        return sum(l.evaluator.evaluations for l in lineages)

    sched_rng = random.Random(seed + 777)
    epoch = 0
    while total_evals() < budget:
        all_solved = True
        for lin in lineages:
            # schedule over real tasks + only the *ungated* auxiliary tasks
            # (the order-aware prerequisite frontier); only unsolved real tasks
            # decide termination
            if any(
                t not in lin.aux_task_ids
                for t in lin.tasks if not lin.pops[t].solved
            ):
                all_solved = False
            sched = lin.schedulable_tasks()
            if not sched:
                continue
            w = lin.task_weights()
            picks = sched_rng.choices(
                sched, weights=[w.get(t, 0.15) for t in sched],
                k=len(sched),
            )
            for tid in picks:
                if lin.pops[tid].solved:
                    continue
                if total_evals() >= budget:
                    break
                before = lin.pops[tid].solved
                lin.step_generation(tid)
                if lin.pops[tid].solved and not before and tid not in lin.aux_task_ids:
                    sol = lin.pops[tid].solution
                    used_abs = sol.prog.abstractions_used()
                    log.write({
                        "event": "solve", "lineage": lin.lineage_id,
                        "task": tid, "epoch": epoch,
                        "evals": total_evals(), "len": sol.fit.length,
                        "phase": lin.pops[tid].solved_phase,
                        "from_fragment": sol.from_fragment,
                        "test_exact": lin.evaluator.test_exact(sol.prog, lin.tasks[tid]),
                        "program": sol.prog.to_json(),
                        # definitions needed to replay an abstr-using solution
                        "abstractions": {
                            n: lin.abstractions[n].to_dict() for n in used_abs
                        },
                    })
            if total_evals() >= budget:
                break
        if all_solved or total_evals() >= budget:
            if all_solved:
                break
        # channel exchange
        for lin in lineages:
            _publish(lin, channel, max_frag_size)
        received = {l.lineage_id: _receive(l, channel) for l in lineages}
        epoch += 1
        log.write({
            "event": "epoch", "epoch": epoch, "evals": total_evals(),
            "solved_union": len(set().union(*(l.solved_tasks() for l in lineages))),
            "received": received,
        })

    solved_sets = {l.lineage_id: l.solved_tasks() for l in lineages}
    usages = {l.lineage_id: l.primitive_usage() for l in lineages}
    union = set().union(*solved_sets.values())
    # union-level phase split: a task counts as an evolution solve for the
    # arm only if *no* lineage closed it deterministically at seeding —
    # phase-1 is identical across arms, so only evolution solves can carry
    # a channel effect (§ roadmap "sharper measure").
    phase1_union: set[str] = set()
    for l in lineages:
        phase1_union |= l.solved_by_phase()["phase1"]
    evolution_union = union - phase1_union
    # reuse rate (§9): solutions containing channel-received material — a
    # received fragment (from_fragment) or a received abstraction, depending
    # on payload
    sols = [
        (l, l.pops[t].solution) for l in lineages for t in l.solved_tasks()
    ]
    if channel.payload == "abstraction":
        reused = sum(
            1 for l, s in sols
            if l.solution_uses_received_abstraction(s.prog)
        )
    else:
        reused = sum(1 for _, s in sols if s.from_fragment)
    reuse = reused / len(sols) if sols else 0.0
    test_exact = sum(
        1 for t in union
        if any(
            l.pops[t].solved
            and l.evaluator.test_exact(l.pops[t].solution.prog, tasks[t])
            for l in lineages
        )
    )
    summary = {
        "event": "summary", "arm": arm, "seed": seed,
        "evals": total_evals(), "budget": budget,
        "solved_union": len(union), "solved_tasks": sorted(union),
        "solved_phase1": sorted(phase1_union),
        "solved_evolution": sorted(evolution_union),
        "test_exact": test_exact,
        "per_lineage_solved": {k: sorted(v) for k, v in solved_sets.items()},
        "divergence": pairwise_jaccard(usages),
        "unique": uniquely_solved(solved_sets),
        "reuse_rate": round(reuse, 4),
        "messages_published": channel.published_total,
        "op_mix": {l.lineage_id: l.op_mix() for l in lineages},
        "abstraction_stats": {
            l.lineage_id: abstraction_stats(l) for l in lineages
        },
        "curriculum_stats": {
            l.lineage_id: {
                "aux_received": len(l.aux_task_ids),
                "aux_solved": sum(1 for t in l.aux_task_ids if l.pops[t].solved),
            }
            for l in lineages
        },
        "primitive_usage": usages,
    }
    log.write(summary)
    log.close()
    return summary
