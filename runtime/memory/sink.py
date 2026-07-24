"""
PLP Capsule Memory — MemorySink
================================
Memory は Module ではない。Runtime の Sink である。

  consume(capsule) -> None

- Capsule を変更しない
- Observation を生成しない
- 意味を付与しない
"""

from __future__ import annotations

from typing import Any, List, Optional, Sequence

from .store import MemoryStore
from .replay import Replay
from .codec import MemoryCodec
from .types import Episode, CapsuleDifference, DifferenceVelocity, MemoryDrift


class MemorySink:
    """
    Capsule Consumer.

    Pipeline の横に fan-out される想定:

      Capsule Produced
            │
            ├── MemorySink.consume
            ├── LoggerSink.consume
            └── ...
    """

    def __init__(self, store: Optional[MemoryStore] = None) -> None:
        self.store = store or MemoryStore()
        self.codec = MemoryCodec(self.store)
        self.replay = Replay(self.store)
        self._pending_ids: List[str] = []

    def consume(self, capsule: Any) -> None:
        """Capsule を append-only で保存する。戻り値なし。"""
        cid = self.store.append_capsule(capsule)
        self._pending_ids.append(cid)

    def close_episode(
        self,
        *,
        tags: Sequence[str] = (),
        metadata: Optional[dict] = None,
    ) -> Episode:
        if not self._pending_ids:
            raise ValueError("no capsules pending for episode")
        ep = self.store.append_episode(
            list(self._pending_ids),
            tags=tags,
            metadata=metadata,
        )
        self._pending_ids.clear()
        return ep

    def record_chain(
        self,
        capsules: Sequence[Any],
        *,
        tags: Sequence[str] = (),
        metadata: Optional[dict] = None,
    ) -> Episode:
        return self.codec.encode_chain(capsules, tags=tags, metadata=metadata)

    def differences(self, episode_id: str) -> List[CapsuleDifference]:
        return self.store.episode_differences(episode_id)

    def velocities(self, episode_id: str) -> List[DifferenceVelocity]:
        return self.store.velocity_along_episode(episode_id)

    def drift(
        self,
        episode_id: str,
        ref_base: str,
        ref_target: str,
        cur_base: str,
        cur_target: str,
    ) -> MemoryDrift:
        return self.store.drift(episode_id, ref_base, ref_target, cur_base, cur_target)

    def stats(self) -> dict:
        return self.store.stats()


# 後方互換エイリアス
MemoryModule = MemorySink
