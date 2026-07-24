"""
PLP Capsule Memory (Runtime Sink)
=================================
記憶は意味を保持しない。Capsule Chain を保持する。

位置づけ: runtime/memory  — Module ではなく Sink

Axioms: M1 Immutable / M2 Episode Chain / M3 Difference First /
        M4 Replayability / M5 Semantic Independence

Usage:
  from runtime.memory import MemorySink, MemoryStore, Replay

  sink = MemorySink()
  sink.consume(capsule_a)
  sink.consume(capsule_b)
  episode = sink.close_episode(tags=["exp-1"])
  diffs = sink.differences(episode.episode_id)
"""

from .types import (
    Episode,
    ObservationDifference,
    CapsuleDifference,
    MemoryDrift,
    DifferenceVelocity,
    MemoryCompliance,
)
from .difference import (
    compare_observations,
    compare_capsules,
    difference_velocity,
    compute_drift,
)
from .store import MemoryStore
from .replay import Replay
from .codec import MemoryCodec
from .sink import MemorySink, MemoryModule

__all__ = [
    "Episode",
    "ObservationDifference",
    "CapsuleDifference",
    "MemoryDrift",
    "DifferenceVelocity",
    "MemoryCompliance",
    "compare_observations",
    "compare_capsules",
    "difference_velocity",
    "compute_drift",
    "MemoryStore",
    "Replay",
    "MemoryCodec",
    "MemorySink",
    "MemoryModule",
]

__version__ = "0.1.0"
