"""
PLP Capsule Codec & Module Protocols
====================================
Capsule を唯一の境界とする実行基盤の最小契約。

Capsule
   │
   ▼
Codec.decode()
   │
   ▼
Internal State
   │
   ▼
Logic (pure)
   │
   ▼
Internal State
   │
   ▼
Codec.encode()
   │
   ▼
Capsule
"""

from __future__ import annotations

from typing import Any, Protocol, TypeVar, Generic
from plp_capsule import PLPCapsule


StateT = TypeVar("StateT")


class CapsuleCodec(Protocol, Generic[StateT]):
    """
    Capsule ⇔ 内部状態 の相互変換。

    - decode: Capsule から内部状態を復元
    - encode: 内部状態から Capsule を生成

    Codec はロジックを持たない。純粋な変換のみ。
    """

    def decode(self, capsule: PLPCapsule) -> StateT:
        """Capsule を内部状態に展開する"""
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
        """内部状態を観測し、Capsule に載せる"""
        ...


class CapsuleModule(Protocol):
    """
    PLP 上のすべての処理単位が実装する唯一の契約。

    Input Capsule を受け取り、Output Capsule を返す。
    内部では Codec + Logic の二層で処理する。
    """

    def process(self, capsule: PLPCapsule) -> PLPCapsule:
        """
        Input Capsule → (decode) → Logic → (encode) → Output Capsule

        意味解釈は一切行わない。
        """
        ...
