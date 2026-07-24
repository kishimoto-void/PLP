"""
PLP Capsule Memory — Memory Codec
=================================
Capsule Chain ⇔ Episode

意味を付与しない。構造の相互変換のみ。
"""

from __future__ import annotations

from typing import Any, List, Optional, Sequence

from .types import Episode
from .store import MemoryStore


class MemoryCodec:
    """
    Capsule Chain ↔ Episode の変換。

    encode_chain: capsules → Episode（Store に載せる）
    decode_episode: Episode → capsule list（Store から読む）
    """

    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def encode_chain(
        self,
        capsules: Sequence[Any],
        *,
        tags: Sequence[str] = (),
        metadata: Optional[dict] = None,
    ) -> Episode:
        return self.store.record_chain(capsules, tags=tags, metadata=metadata)

    def decode_episode(self, episode_id: str) -> List[Any]:
        return self.store.episode_capsules(episode_id)

    def encode_existing_ids(
        self,
        capsule_ids: Sequence[str],
        *,
        tags: Sequence[str] = (),
        metadata: Optional[dict] = None,
    ) -> Episode:
        return self.store.append_episode(
            capsule_ids, tags=tags, metadata=metadata
        )
