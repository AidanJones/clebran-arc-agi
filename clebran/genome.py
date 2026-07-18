"""Typed genetic operators over the linear program IR (§5.2).

All operators preserve the static-type discipline via registry.compatible:
an argument slot expecting type T only ever receives I/registers/constants
whose static type subsumes into T. A single `repair` pass underlies random
generation, crossover splicing, and (later) channel-fragment injection —
anything that can produce dangling or ill-typed register references.

Fragments (§5.3) are dependency-closed statement slices with internal refs
renumbered from 0 and external refs replaced by ("hole", type_name); repair
fills holes on injection.
"""
from __future__ import annotations

import random

from .dsl.program import Program, Statement, Arg, statement_return_type
from .dsl.registry import PRIMITIVES, CONSTANTS, compatible

Fragment = tuple  # tuple[Statement, ...] with holes


class GenomeOps:
    def __init__(
        self,
        pool: list[str],
        rng: random.Random,
        max_len: int = 12,
        p_higher_order: float = 0.25,
    ):
        self.pool = [p for p in pool if p in PRIMITIVES]
        self.rng = rng
        self.max_len = max_len
        self.p_higher_order = p_higher_order
        self.fn_weights: dict[str, float] | None = None  # signal payload bias
        # constants grouped by type for fast sampling
        self._consts_by_type: dict[str, list[str]] = {}
        for name, (_, t) in CONSTANTS.items():
            self._consts_by_type.setdefault(t, []).append(name)
        for v in self._consts_by_type.values():
            v.sort()

    # ---------- sources: what can fill an argument slot of type T ----------

    def _sources_for(
        self, prog_prefix: list[Statement], expected: str, prog: Program
    ) -> list[Arg]:
        out: list[Arg] = []
        if compatible("Grid", expected):
            out.append(("in", None))
        for i in range(len(prog_prefix)):
            rt = statement_return_type(prog, i) if i < len(prog.statements) else "Any"
            if compatible(rt, expected):
                out.append(("reg", i))
        for t, names in self._consts_by_type.items():
            if compatible(t, expected):
                out.extend(("const", n) for n in names)
        if compatible("Callable", expected):
            out.extend(("prim", n) for n in self.pool)
        return out

    def _random_arg(self, prog: Program, upto: int, expected: str) -> Arg | None:
        """Pick a random source of type `expected` from registers < upto,
        input, constants, or primitives."""
        cands: list[Arg] = []
        if compatible("Grid", expected):
            cands.append(("in", None))
        regs = [
            ("reg", i)
            for i in range(upto)
            if compatible(statement_return_type(prog, i), expected)
        ]
        cands.extend(regs)
        for t, names in self._consts_by_type.items():
            if compatible(t, expected):
                cands.extend(("const", n) for n in names)
        if compatible("Callable", expected):
            cands.extend(("prim", n) for n in self.pool)
        if not cands:
            return None
        # bias toward registers so programs actually compose
        if regs and self.rng.random() < 0.5:
            return self.rng.choice(regs)
        return self.rng.choice(cands)

    def _pick_fn(self) -> str:
        if self.fn_weights:
            return self.rng.choices(
                self.pool,
                weights=[self.fn_weights.get(p, 1.0) for p in self.pool],
                k=1,
            )[0]
        return self.rng.choice(self.pool)

    def _random_statement(self, prog: Program, pos: int) -> Statement | None:
        """A random well-typed statement usable at index pos."""
        for _ in range(30):
            fn = self._pick_fn()
            sig = PRIMITIVES[fn]
            args = []
            ok = True
            for pt in sig.params:
                a = self._random_arg(prog, pos, pt)
                if a is None:
                    ok = False
                    break
                args.append(a)
            if ok:
                return Statement(("prim", fn), tuple(args))
        return None

    # ---------- generation ----------

    def random_program(self, length: int | None = None) -> Program | None:
        n = length or self.rng.randint(1, self.max_len // 2)
        prog = Program([])
        for i in range(n):
            st = self._random_statement(prog, i)
            if st is None:
                return None
            prog.statements.append(st)
        self._force_grid_output(prog)
        return prog if self._returns_grid(prog) else None

    def _returns_grid(self, prog: Program) -> bool:
        if not prog.statements:
            return False
        rt = statement_return_type(prog, len(prog.statements) - 1)
        return compatible(rt, "Grid") or rt in ("Any", "Element", "Piece")

    def _force_grid_output(self, prog: Program) -> None:
        """If the final statement can't produce a grid, append one that can."""
        if self._returns_grid(prog) or len(prog.statements) >= self.max_len:
            return
        grid_prims = [
            p for p in self.pool if compatible(PRIMITIVES[p].returns, "Grid")
        ]
        self.rng.shuffle(grid_prims)
        pos = len(prog.statements)
        for fn in grid_prims:
            sig = PRIMITIVES[fn]
            args = []
            ok = True
            for pt in sig.params:
                a = self._random_arg(prog, pos, pt)
                if a is None:
                    ok = False
                    break
                args.append(a)
            if ok:
                prog.statements.append(Statement(("prim", fn), tuple(args)))
                return

    # ---------- repair (shared by crossover / injection / deletion) ----------

    def repair(self, prog: Program) -> Program | None:
        """Fix dangling ("reg", i>=pos), ill-typed refs, and ("hole", T) args."""
        for pos, st in enumerate(prog.statements):
            new_fn = st.fn
            if st.fn[0] == "hole" or (st.fn[0] == "reg" and st.fn[1] >= pos):
                # callee dangling: re-point to a callable register, or swap in
                # a random primitive of matching arity
                cands = [
                    i for i in range(pos)
                    if statement_return_type(prog, i) in ("Callable", "Any")
                ]
                if cands and self.rng.random() < 0.5:
                    new_fn = ("reg", self.rng.choice(cands))
                else:
                    prims = [
                        p for p in self.pool
                        if PRIMITIVES[p].arity == len(st.args)
                    ]
                    if not prims:
                        return None
                    new_fn = ("prim", self.rng.choice(prims))
            sig = PRIMITIVES[new_fn[1]] if new_fn[0] == "prim" else None
            new_args = []
            for k, a in enumerate(st.args):
                expected = sig.params[k] if sig and k < len(sig.params) else "Any"
                kind, payload = a
                bad = (
                    kind == "hole"
                    or (kind == "reg" and payload >= pos)
                    or (
                        kind == "reg"
                        and not compatible(
                            statement_return_type(prog, payload), expected
                        )
                    )
                )
                if kind == "hole":
                    expected = payload if sig is None else expected
                if bad:
                    repl = self._random_arg(prog, pos, expected)
                    if repl is None:
                        return None
                    new_args.append(repl)
                else:
                    new_args.append(a)
            prog.statements[pos] = Statement(new_fn, tuple(new_args))
        self._force_grid_output(prog)
        return prog if self._returns_grid(prog) else None

    # ---------- mutation ----------

    def mutate(self, parent: Program) -> Program | None:
        prog = Program(list(parent.statements))
        op = self.rng.random()
        if op < 0.25:
            ok = self._mut_swap_fn(prog)
        elif op < 0.50:
            ok = self._mut_arg(prog)
        elif op < 0.70 and len(prog.statements) < self.max_len:
            ok = self._mut_grow(prog)
        elif op < 0.80 and len(prog.statements) < self.max_len:
            ok = self._mut_insert(prog)
        elif op < 0.90 and len(prog.statements) > 1:
            ok = self._mut_delete(prog)
        else:
            ok = self._mut_const(prog)
        if not ok:
            return None
        return self.repair(prog)

    def _mut_swap_fn(self, prog: Program) -> bool:
        pos = self.rng.randrange(len(prog.statements))
        st = prog.statements[pos]
        if st.fn[0] != "prim":
            return False
        old = PRIMITIVES[st.fn[1]]
        cands = [
            p
            for p in self.pool
            if p != st.fn[1]
            and PRIMITIVES[p].arity == old.arity
            and all(
                compatible(a, b)
                for a, b in zip(old.params, PRIMITIVES[p].params)
            )
        ]
        if not cands:
            return False
        prog.statements[pos] = Statement(("prim", self.rng.choice(cands)), st.args)
        return True

    def _mut_arg(self, prog: Program) -> bool:
        pos = self.rng.randrange(len(prog.statements))
        st = prog.statements[pos]
        if not st.args:
            return False
        k = self.rng.randrange(len(st.args))
        expected = (
            PRIMITIVES[st.fn[1]].params[k]
            if st.fn[0] == "prim" and k < PRIMITIVES[st.fn[1]].arity
            else "Any"
        )
        a = self._random_arg(prog, pos, expected)
        if a is None:
            return False
        args = list(st.args)
        args[k] = a
        prog.statements[pos] = Statement(st.fn, tuple(args))
        return True

    def _mut_grow(self, prog: Program) -> bool:
        """Subtree replacement, linear-IR style (§5.2): insert a new random
        statement AND rewire a downstream argument to consume it, in one
        move — so composed structure can appear without surviving a neutral
        intermediate generation."""
        pos = self.rng.randrange(len(prog.statements) + 1)
        st = self._random_statement(prog, pos)
        if st is None:
            return False
        self._shift_refs(prog, pos, +1)
        prog.statements.insert(pos, st)
        new_type = statement_return_type(prog, pos)
        # find downstream arg slots that could consume the new register
        slots = []
        for j in range(pos + 1, len(prog.statements)):
            stj = prog.statements[j]
            sig = PRIMITIVES[stj.fn[1]] if stj.fn[0] == "prim" else None
            for k in range(len(stj.args)):
                expected = sig.params[k] if sig and k < len(sig.params) else "Any"
                if compatible(new_type, expected):
                    slots.append((j, k))
        if not slots:
            return True  # plain insert; repair keeps it well-formed
        j, k = self.rng.choice(slots)
        stj = prog.statements[j]
        args = list(stj.args)
        args[k] = ("reg", pos)
        prog.statements[j] = Statement(stj.fn, tuple(args))
        return True

    def _mut_insert(self, prog: Program) -> bool:
        pos = self.rng.randrange(len(prog.statements) + 1)
        st = self._random_statement(prog, pos)
        if st is None:
            return False
        self._shift_refs(prog, pos, +1)
        prog.statements.insert(pos, st)
        return True

    def _mut_delete(self, prog: Program) -> bool:
        pos = self.rng.randrange(len(prog.statements) - 1)  # never the output
        self._shift_refs(prog, pos + 1, -1, deleted=pos)
        del prog.statements[pos]
        return True

    def _mut_const(self, prog: Program) -> bool:
        spots = [
            (i, k, a)
            for i, st in enumerate(prog.statements)
            for k, a in enumerate(st.args)
            if a[0] == "const"
        ]
        if not spots:
            return False
        i, k, (_, name) = self.rng.choice(spots)
        t = CONSTANTS[name][1]
        options = [c for c in self._consts_by_type.get(t, []) if c != name]
        if not options:
            return False
        st = prog.statements[i]
        args = list(st.args)
        args[k] = ("const", self.rng.choice(options))
        prog.statements[i] = Statement(st.fn, tuple(args))
        return True

    def _shift_refs(
        self, prog: Program, from_pos: int, delta: int, deleted: int | None = None
    ) -> None:
        """Renumber ("reg", i) refs in statements >= from_pos.

        Insert at index p:  call with (from_pos=p, delta=+1) *before*
        inserting — refs i >= p become i+1.
        Delete of index d:  call with (from_pos=d+1, delta=-1, deleted=d)
        *before* deleting — refs i == d become holes, refs i > d become i-1.
        """
        def fix(a: Arg) -> Arg:
            if a[0] != "reg":
                return a
            i = a[1]
            if deleted is not None:
                if i == deleted:
                    return ("hole", "Any")
                return ("reg", i - 1) if i > deleted else a
            return ("reg", i + 1) if i >= from_pos else a

        for j in range(from_pos, len(prog.statements)):
            st = prog.statements[j]
            prog.statements[j] = Statement(
                fix(st.fn) if st.fn[0] == "reg" else st.fn,
                tuple(fix(a) for a in st.args),
            )

    # ---------- crossover ----------

    def crossover(self, a: Program, b: Program) -> Program | None:
        """Linear two-segment crossover: prefix of a + suffix of b, then
        repair dangling refs in the suffix."""
        if not a.statements or not b.statements:
            return None
        ca = self.rng.randint(0, len(a.statements) - 1)
        cb = self.rng.randint(0, len(b.statements) - 1)
        stmts = list(a.statements[:ca]) + list(b.statements[cb:])
        if not stmts or len(stmts) > self.max_len:
            return None
        # suffix refs pointing into b's prefix are dangling relative to the
        # child; offset them into hole-space and let repair re-wire.
        offset = ca - cb
        child = Program([])
        for j, st in enumerate(stmts):
            if j < ca:
                child.statements.append(st)
                continue

            def remap(x: Arg) -> Arg:
                if x[0] == "reg":
                    ni = x[1] + offset
                    if 0 <= ni < j:
                        return ("reg", ni)
                    return ("hole", "Any")
                return x

            child.statements.append(
                Statement(
                    remap(st.fn) if st.fn[0] == "reg" else st.fn,
                    tuple(remap(x) for x in st.args),
                )
            )
        return self.repair(child)

    # ---------- fragments (§5.3) ----------

    def extract_fragment(self, prog: Program, max_size: int) -> Fragment | None:
        """Dependency-closed slice ending at a random register, ≤ max_size
        statements, internal refs renumbered, external refs -> holes."""
        if not prog.statements:
            return None
        end = self.rng.randrange(len(prog.statements))
        keep = {end}
        frontier = [end]
        while frontier and len(keep) < max_size:
            i = frontier.pop()
            st = prog.statements[i]
            for kind, payload in (st.fn, *st.args):
                if kind == "reg" and payload not in keep and len(keep) < max_size:
                    keep.add(payload)
                    frontier.append(payload)
        order = sorted(keep)
        index = {old: new for new, old in enumerate(order)}
        out = []
        for old in order:
            st = prog.statements[old]

            def remap(x: Arg) -> Arg:
                if x[0] == "reg":
                    return ("reg", index[x[1]]) if x[1] in index else ("hole", "Any")
                return x

            out.append(
                Statement(
                    remap(st.fn) if st.fn[0] == "reg" else st.fn,
                    tuple(remap(x) for x in st.args),
                )
            )
        return tuple(out)

    def inject_fragment(self, parent: Program, frag: Fragment) -> Program | None:
        """Splice a fragment at a random position and repair. This is both
        library-reuse mutation and channel-fragment injection."""
        if len(parent.statements) + len(frag) > self.max_len + 4:
            return None
        pos = self.rng.randint(0, len(parent.statements))
        prog = Program(list(parent.statements))
        for _ in range(len(frag)):
            self._shift_refs(prog, pos, +1)
        # renumber fragment-internal refs to absolute positions
        for j, st in enumerate(frag):
            def remap(x: Arg) -> Arg:
                if x[0] == "reg":
                    return ("reg", x[1] + pos)
                return x
            prog.statements.insert(
                pos + j,
                Statement(
                    remap(st.fn) if st.fn[0] == "reg" else st.fn,
                    tuple(remap(x) for x in st.args),
                ),
            )
        return self.repair(prog)
