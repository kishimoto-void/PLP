"""
PLP Capsule Memory — Store
===========================
M1 Immutable Memory — append-only
M5 Semantic Independence

Capsule 本体は変更しない。削除もしない。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence
from copy import deepcopy

from .types import Episode, CapsuleDifference, DifferenceVelocity, MemoryDrift
from .difference import compare_capsules, difference_velocity, compute_drift


class MemoryStore:
    """In-memory append-only store."""

    def __init__(self) -> None:
        self._capsules: Dict[str, Any] = {}
        self._episodes: Dict[str, Episode] = {}
        self._order: List[str] = []
        self._diff_cache: Dict[tuple[str, str], CapsuleDifference] = {}

    def append_capsule(self, capsule: Any) -> str:
        header = getattr(capsule, "header", None)
        cid = str(getattr(header, "capsule_id", "") or "")
        if not cid:
            raise ValueError("capsule.header.capsule_id is required")
        if cid in self._capsules:
            raise ValueError(f"capsule already stored (immutable): {cid}")
        self._capsules[cid] = deepcopy(capsule)
        self._order.append(cid)
        return cid

    def append_episode(
        self,
        capsule_ids: Sequence[str],
        *,
        tags: Sequence[str] = (),
        metadata: Optional[dict] = None,
        episode_id: Optional[str] = None,
    ) -> Episode:
        for cid in capsule_ids:
            if cid not in self._capsules:
                raise KeyError(f"capsule not in store: {cid}")
        ep = Episode.create(
            capsule_ids, tags=tags, metadata=metadata, episode_id=episode_id,
        )
        if ep.episode_id in self._episodes:
            raise ValueError(f"episode already exists: {ep.episode_id}")
        self._episodes[ep.episode_id] = ep
        return ep

    def record_chain(
        self,
        capsules: Sequence[Any],
        *,
        tags: Sequence[str] = (),
        metadata: Optional[dict] = None,
    ) -> Episode:
        ids: List[str] = []
        for c in capsules:
            ids.append(self.append_capsule(c))
        return self.append_episode(ids, tags=tags, metadata=metadata)

    def get_capsule(self, capsule_id: str) -> Any:
        if capsule_id not in self._capsules:
            raise KeyError(f"capsule not found: {capsule_id}")
        return self._capsules[capsule_id]

    def get_episode(self, episode_id: str) -> Episode:
        if episode_id not in self._episodes:
            raise KeyError(f"episode not found: {episode_id}")
        return self._episodes[episode_id]

    def list_capsule_ids(self) -> List[str]:
        return list(self._order)

    def list_episode_ids(self) -> List[str]:
        return list(self._episodes.keys())

    def episode_capsules(self, episode_id: str) -> List[Any]:
        ep = self.get_episode(episode_id)
        return [self.get_capsule(cid) for cid in ep.capsule_ids]

    def difference(self, base_id: str, target_id: str) -> CapsuleDifference:
        key = (base_id, target_id)
        if key in self._diff_cache:
            return self._diff_cache[key]
        base = self.get_capsule(base_id)
        target = self.get_capsule(target_id)
        diff = compare_capsules(base, target)
        self._diff_cache[key] = diff
        return diff

    def episode_differences(self, episode_id: str) -> List[CapsuleDifference]:
        ep = self.get_episode(episode_id)
        ids = list(ep.capsule_ids)
        out: List[CapsuleDifference] = []
        for i in range(len(ids) - 1):
            out.append(self.difference(ids[i], ids[i + 1]))
        return out

    def velocity_along_episode(self, episode_id: str) -> List[DifferenceVelocity]:
        diffs = self.episode_differences(episode_id)
        out: List[DifferenceVelocity] = []
        for i in range(len(diffs) - 1):
            out.append(difference_velocity(diffs[i], diffs[i + 1]))
        return out

    def drift(
        self,
        episode_id: str,
        reference_base_id: str,
        reference_target_id: str,
        current_base_id: str,
        current_target_id: str,
    ) -> MemoryDrift:
        ref = self.difference(reference_base_id, reference_target_id)
        cur = self.difference(current_base_id, current_target_id)
        return compute_drift(episode_id, current_target_id, ref, cur)

    def stats(self) -> dict:
        return {
            "n_capsules": len(self._capsules),
            "n_episodes": len(self._episodes),
            "n_diff_cache": len(self._diff_cache),
        }
