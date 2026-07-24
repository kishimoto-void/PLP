"""
PLP Codecs
==========
Capsule ⇔ 内部状態 の相互変換層。

設計原則:
- Codec は変換だけを担当する（ロジックを持たない）
- Logic は Capsule を一切知らない
- Round-trip テストが容易
- Capsule のバージョン変更は Codec のみに影響する
"""

from .base import CapsuleCodec, CapsuleModule
from .pgra_codec import (
    PGRACodec,
    PGRAModule,
    DecodedState,
    ReconstructionLevel,
)

__all__ = [
    "CapsuleCodec",
    "CapsuleModule",
    "PGRACodec",
    "PGRAModule",
    "DecodedState",
    "ReconstructionLevel",
]
