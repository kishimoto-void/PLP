"""
PLP Codecs & Core Contracts
===========================
Stable ABI v1.0 + リファレンス Codec 実装。
"""

from .base import (
    CapsuleCodec,
    CapsuleModule,
    CapsuleSink,
    CapsuleSource,
    CapsulePipeline,
    FanOutDispatcher,
    CapsuleRuntime,
)
from .pgra_codec import (
    PGRACodec,
    PGRAModule,
    DecodedState,
    ReconstructionLevel,
)

__all__ = [
    # Stable ABI
    "CapsuleCodec",
    "CapsuleModule",
    "CapsuleSink",
    "CapsuleSource",
    "CapsulePipeline",
    "FanOutDispatcher",
    "CapsuleRuntime",
    # Reference implementation
    "PGRACodec",
    "PGRAModule",
    "DecodedState",
    "ReconstructionLevel",
]
