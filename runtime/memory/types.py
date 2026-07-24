"""
PLP Capsule Memory — Core Types
================================
記憶は意味を保持しない。Capsule Chain を保持する。

Axioms:
  M1 Immutable Memory
  M2 Episode as Capsule Chain
  M3 Difference First
  M4 Replayability
  M5 Semantic Independence
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Mapping, Optional, Sequence
from uuid import uuid4
import time


class MemoryCompliance(Enum):
    MINIMAL = auto()
    STANDARD = auto()
    FULL = auto()


@dataclass(frozen=True)
class Episode:
    episode_id: str
    capsule_ids: tuple[str, ...]
    created_at: float
    tags: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @staticmethod
    def create(
        capsule_ids: Sequence[str],
        *,
        tags: Sequence[str] = (),
        metadata: Optional[Mapping[str, Any]] = None,
        episode_id: Optional[str] = None,
    ) -> "Episode":
        return Episode(
            episode_id=episode_id or str(uuid4()),
            capsule_ids=tuple(str(x) for x in capsule_ids),
            created_at=time.time(),
            tags=tuple(tags),
            metadata=dict(metadata or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "capsule_ids": list(self.capsule_ids),
            "created_at": self.created_at,
            "tags": list(self.tags),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Episode":
        return cls(
            episode_id=str(data["episode_id"]),
            capsule_ids=tuple(data.get("capsule_ids") or ()),
            created_at=float(data.get("created_at", 0.0)),
            tags=tuple(data.get("tags") or ()),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(frozen=True)
class ObservationDifference:
    name: str
    delta: Mapping[str, float]
    norm: float
    changed: bool
    confidence: float
    missing_in_base: bool = False
    missing_in_target: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "delta": dict(self.delta),
            "norm": self.norm,
            "changed": self.changed,
            "confidence": self.confidence,
            "missing_in_base": self.missing_in_base,
            "missing_in_target": self.missing_in_target,
        }


@dataclass(frozen=True)
class CapsuleDifference:
    base_capsule_id: str
    target_capsule_id: str
    observation_differences: tuple[ObservationDifference, ...]
    summary_norm: float
    clock_delta: int = 0
    sequence_delta: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "base_capsule_id": self.base_capsule_id,
            "target_capsule_id": self.target_capsule_id,
            "observation_differences": [o.to_dict() for o in self.observation_differences],
            "summary_norm": self.summary_norm,
            "clock_delta": self.clock_delta,
            "sequence_delta": self.sequence_delta,
        }


@dataclass(frozen=True)
class MemoryDrift:
    episode_id: str
    capsule_id: str
    drift_score: float
    observation_scores: Mapping[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "capsule_id": self.capsule_id,
            "drift_score": self.drift_score,
            "observation_scores": dict(self.observation_scores),
        }


@dataclass(frozen=True)
class DifferenceVelocity:
    base_diff_summary: float
    target_diff_summary: float
    velocity: float
    per_observation: Mapping[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "base_diff_summary": self.base_diff_summary,
            "target_diff_summary": self.target_diff_summary,
            "velocity": self.velocity,
            "per_observation": dict(self.per_observation),
        }
