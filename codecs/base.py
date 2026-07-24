"""
PLP Core Contracts — Stable ABI v1.0
====================================
変更しない契約（Stable ABI）。

Core
├── Capsule          (規格本体は plp_capsule)
├── CapsuleCodec
├── CapsuleModule
├── CapsulePipeline
├── CapsuleSource
└── CapsuleSink

Pipeline は変換のみ。
Runtime は観測・保存・配信（Sink の Fan-out）。

Capsule
   │
   ▼
Source → Pipeline(Modules) → Capsule → FanOut → Sinks
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Protocol, Sequence, TypeVar, Generic

from plp_capsule import PLPCapsule


StateT = TypeVar("StateT")


# ------------------------------------------------------------------
# Codec
# ------------------------------------------------------------------

class CapsuleCodec(Protocol, Generic[StateT]):
    """Capsule ⇔ 内部状態。ロジックを持たない。"""

    def decode(self, capsule: PLPCapsule) -> StateT:
        ...

    def encode(
        self,
        state: StateT,
        *,
        previous: PLPCapsule | None = None,
        clock: int | None = None,
        sequence: int | None = None,
        source: str = "module",
        parent_id: str | None = None,
    ) -> PLPCapsule:
        ...


# ------------------------------------------------------------------
# Module  (transform)
# ------------------------------------------------------------------

class CapsuleModule(Protocol):
    """
    process(capsule) -> capsule

    産む側。意味解釈をしない。
    """

    def process(self, capsule: PLPCapsule) -> PLPCapsule:
        ...


# ------------------------------------------------------------------
# Sink  (consume)
# ------------------------------------------------------------------

class CapsuleSink(Protocol):
    """
    consume(capsule) -> None

    消費側。Capsule を変更しない。Observation を生成しない。
    検索・終了処理などは各 Sink 固有でよい。
    """

    def consume(self, capsule: PLPCapsule) -> None:
        ...


# ------------------------------------------------------------------
# Source  (produce)
# ------------------------------------------------------------------

class CapsuleSource(Protocol):
    """
    produce() -> capsule

    入口。File / Socket / Camera / Replay などを同じ契約で扱う。
    """

    def produce(self) -> PLPCapsule:
        ...


# ------------------------------------------------------------------
# Pipeline  (transform only)
# ------------------------------------------------------------------

class CapsulePipeline:
    """
    直列の Module 合成のみを担当する。

    Capsule → Module → Module → … → Capsule

    Sink や Fan-out は知らない（Runtime の責務）。
    """

    def __init__(self, modules: Sequence[CapsuleModule] = ()) -> None:
        self._modules: List[CapsuleModule] = list(modules)

    def add(self, module: CapsuleModule) -> "CapsulePipeline":
        self._modules.append(module)
        return self

    def run(self, capsule: PLPCapsule) -> PLPCapsule:
        current = capsule
        for mod in self._modules:
            current = mod.process(current)
        return current

    @property
    def modules(self) -> tuple[CapsuleModule, ...]:
        return tuple(self._modules)


# ------------------------------------------------------------------
# Fan-out  (Runtime helper)
# ------------------------------------------------------------------

class FanOutDispatcher:
    """
    Capsule を登録済み Sink へ配るだけ。

    Module は Dispatcher を知らない。
    Dispatcher だけが Sink 一覧を持つ。
    Sink の追加・削除はプラグイン的に行える。
    """

    def __init__(self, sinks: Sequence[CapsuleSink] = ()) -> None:
        self._sinks: List[CapsuleSink] = list(sinks)

    def add(self, sink: CapsuleSink) -> "FanOutDispatcher":
        self._sinks.append(sink)
        return self

    def remove(self, sink: CapsuleSink) -> None:
        self._sinks = [s for s in self._sinks if s is not sink]

    def dispatch(self, capsule: PLPCapsule) -> None:
        for sink in self._sinks:
            sink.consume(capsule)

    @property
    def sinks(self) -> tuple[CapsuleSink, ...]:
        return tuple(self._sinks)


# ------------------------------------------------------------------
# Runtime loop helper (optional, thin)
# ------------------------------------------------------------------

class CapsuleRuntime:
    """
    Source → Pipeline → FanOut の最小ループ。

    これ自体は「便利な配線」であり、Core 契約を増やさない。
    """

    def __init__(
        self,
        *,
        source: Optional[CapsuleSource] = None,
        pipeline: Optional[CapsulePipeline] = None,
        dispatcher: Optional[FanOutDispatcher] = None,
    ) -> None:
        self.source = source
        self.pipeline = pipeline or CapsulePipeline()
        self.dispatcher = dispatcher or FanOutDispatcher()

    def step(self, capsule: Optional[PLPCapsule] = None) -> PLPCapsule:
        """
        1 ステップ:
          (source.produce | 引数 capsule) → pipeline.run → dispatcher.dispatch → 返す
        """
        if capsule is None:
            if self.source is None:
                raise RuntimeError("no capsule and no source")
            capsule = self.source.produce()
        out = self.pipeline.run(capsule)
        self.dispatcher.dispatch(out)
        return out
