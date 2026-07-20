"""The communication channel (§5.3) — the heart of the experiment.

A blackboard that lineages publish to and receive from once per epoch.

Variants (map 1:1 onto baseline arms, §7):
  ChNone          — CH-NONE: no communication (B1)
  ChConstrained   — CH-CONSTRAINED(K, M): fragments capped at ≤K statements,
                    ≤M messages per lineage per epoch (B2 fragment payload,
                    B4 signal payload)
  ChUnconstrained — CH-UNCONSTRAINED: whole library dumped every epoch (B3)

Payload modes (config flag, §5.3):
  "fragment"    — concrete DSL subtrees, injected into the receiver's library
                  (horizontal gene transfer over Hodel's given primitives)
  "signal"      — a primitive-reweighting vector biasing the receiver's
                  mutation distribution; no concrete code crosses the channel
  "abstraction" — a lineage-*recovered* subroutine (the emergent-vocabulary
                  variant, spec §11); receivers install it as a named callable
                  unit. This is the scientifically important payload: the
                  shared alphabet is discovered, not given.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .genome import Fragment
from .dsl.abstraction import Abstraction


@dataclass(frozen=True)
class Message:
    sender: str
    payload_kind: str            # "fragment" | "signal" | "abstraction"
    fragment: Fragment | None = None
    score: float = 0.0
    signal: dict | None = None       # primitive name -> weight
    abstraction: Abstraction | None = None


def _msg_size(m: Message) -> int:
    """Statement count a message would inject — the quantity the bandwidth
    constraint (K) caps. Signals carry no code, so size 0."""
    if m.fragment is not None:
        return len(m.fragment)
    if m.abstraction is not None:
        return len(m.abstraction.body)
    return 0


@dataclass
class Channel:
    payload: str = "fragment"
    board: dict[str, list[Message]] = field(default_factory=dict)  # sender -> msgs
    published_total: int = 0

    def publish(self, lineage_id: str, messages: list[Message]) -> None:
        accepted = self._admit(messages)
        self.board[lineage_id] = accepted
        self.published_total += len(accepted)

    def receive(self, lineage_id: str) -> list[Message]:
        out: list[Message] = []
        for sender, msgs in sorted(self.board.items()):
            if sender != lineage_id:
                out.extend(msgs)
        return out

    def _admit(self, messages: list[Message]) -> list[Message]:
        raise NotImplementedError


class ChNone(Channel):
    def _admit(self, messages: list[Message]) -> list[Message]:
        return []


@dataclass
class ChConstrained(Channel):
    max_fragment_size: int = 4   # K: statements per fragment
    max_messages: int = 3        # M: messages per lineage per epoch

    def _admit(self, messages: list[Message]) -> list[Message]:
        # bounded fragment/abstraction size (K) and bounded count (M); signals
        # are uncapped in size (they carry no code) but still count-limited
        ok = [
            m
            for m in messages
            if m.payload_kind == "signal"
            or _msg_size(m) <= self.max_fragment_size
        ]
        ok.sort(key=lambda m: m.score, reverse=True)
        return ok[: self.max_messages]


class ChUnconstrained(Channel):
    def _admit(self, messages: list[Message]) -> list[Message]:
        return list(messages)


def make_channel(kind: str, payload: str = "fragment", **kw) -> Channel:
    if kind == "none":
        return ChNone(payload=payload)
    if kind == "constrained":
        return ChConstrained(payload=payload, **kw)
    if kind == "unconstrained":
        return ChUnconstrained(payload=payload)
    raise ValueError(kind)
