"""
PLP Capsule Memory — Replay
============================
M4 Replayability

Replay は Simulation ではない。
保存された Capsule を順番に復元するだけである。
"""

from __future__ import annotations

from typing import Any, Callable, Iterator, List, Optional, Sequence

from .store import MemoryStore
from .types import Episode


class Replay:
    """
    Episode または capsule_id 列を順に返す。
    Codec を通す場合は on_capsule コールバックで decode などを行う（任意）。
    """

    def __init__(
        self,
        store: MemoryStore,
        *,
        on_capsule: Optional[Callable[[Any], Any]] = None,
    ) -> None:
        self.store = store
        self.on_capsule = on_capsule

    def iter_episode(self, episode_id: str) -> Iterator[Any]:
        ep = self.store.get_episode(episode_id)
        for cid in ep.capsule_ids:
            cap = self.store.get_capsule(cid)
            if self.on_capsule is not None:
                yield self.on_capsule(cap)
            else:
                yield cap

    def list_episode(self, episode_id: str) -> List[Any]:
        return list(self.iter_episode(episode_id))

    def iter_ids(self, capsule_ids: Sequence[str]) -> Iterator[Any]:
        for cid in capsule_ids:
            cap = self.store.get_capsule(cid)
            if self.on_capsule is not None:
                yield self.on_capsule(cap)
            else:
                yield cap

    def replay_with_codec(self, episode_id: str, codec: Any) -> List[Any]:
        """
        各 Capsule を codec.decode に通した結果を返す。
        codec は decode(capsule) を持つこと（DecodedState でも state でも可）。
        """
        results: List[Any] = []
        for cap in self.iter_episode(episode_id):
            decoded = codec.decode(cap)
            state = getattr(decoded, "state", decoded)
            results.append(state)
        return results
