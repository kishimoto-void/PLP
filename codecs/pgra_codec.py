"""
PGRA Codec & Module
===================
PGRA を Capsule 中心のモジュールとして扱う実装。

構成:
  PGRAModule
  ├── PGRACodec          # Capsule ⇔ PhysicalState
  └── RelaxationEngine   # 純粋な幾何緩和ロジック（Capsule を知らない）

使用例:
  module = PGRAModule()
  output = module.process(input_capsule)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np

from plp_capsule import (
    PLPCapsule,
    CapsuleBuilder,
    CapsuleHeader,
    CapsuleFlags,
    InputCapsule,
    InputReference,
    ObservationBlock,
    Capability,
    DeltaBlock,
    CapsuleIntegrity,
    compute_content_hash,
)
from PGRA.state import PhysicalState, Particle, Geometry, GeometryKind
from PGRA.engine import PGRAPhysicsEngine
from PGRA.reference import DistanceReference, StabilityReference, Reference
from .base import CapsuleCodec, CapsuleModule


# ==========================================================
# PGRACodec
# ==========================================================

class PGRACodec:
    """
    Capsule ⇔ PhysicalState の相互変換。

    - decode: Observation や必要情報から PhysicalState を構築
    - encode: PhysicalState を観測して Capsule を生成

    ロジック（緩和計算）は一切持たない。
    """

    def __init__(self, source: str = "PGRA"):
        self.source = source
        self._builder = CapsuleBuilder()

        # デフォルトの観測を登録
        self._builder.register(_GeometryRadiusObserver(), priority=10)
        self._builder.register(_EnergyKineticObserver(), priority=20)

    def decode(self, capsule: PLPCapsule) -> PhysicalState:
        """
        Capsule から PhysicalState を復元する。

        現時点では簡易実装：
        - observations に粒子情報が含まれている場合はそれを使う
        - なければ空の PhysicalState を返す（実験用）

        将来は ObservationBlock の schema に従って厳密に復元する。
        """
        state = PhysicalState()

        # 簡易: metadata や特定の observation から復元する余地を残す
        # 現時点では呼び出し側で state を直接渡すケースも想定
        return state

    def encode(
        self,
        state: PhysicalState,
        *,
        previous: Optional[PLPCapsule] = None,
        clock: Optional[int] = None,
        sequence: Optional[int] = None,
        source: Optional[str] = None,
        parent_id: Optional[str] = None,
        input_packet: Optional[InputCapsule] = None,
        references: Optional[List[Reference]] = None,
    ) -> PLPCapsule:
        """PhysicalState を観測し Capsule に載せる"""
        if clock is None:
            clock = (previous.header.clock + 1) if previous else 0
        if sequence is None:
            sequence = (previous.header.sequence + 1) if previous else 0
        if parent_id is None and previous is not None:
            parent_id = previous.header.capsule_id
        if input_packet is None:
            input_packet = (
                previous.input if previous is not None
                else InputCapsule()
            )

        return self._builder.build(
            world=state,
            input_packet=input_packet,
            clock=clock,
            sequence=sequence,
            previous=previous,
            source=source or self.source,
            parent_id=parent_id,
        )


# ==========================================================
# Internal Observers（Codec が使う純粋観測）
# ==========================================================

class _GeometryRadiusObserver:
    def observe(self, world: Any) -> ObservationBlock:
        if not isinstance(world, PhysicalState) or not world.particles:
            return ObservationBlock(
                name="geometry.radius",
                schema="plp.geometry.v1",
                capability=Capability.GEOMETRY.value,
                values={
                    "mean_radius": 0.0,
                    "std_radius": 0.0,
                    "max_radius": 0.0,
                    "n_particles": 0.0,
                },
            )

        positions = np.array([p.position for p in world.particles.values()])
        radii = np.linalg.norm(positions, axis=1)

        return ObservationBlock(
            name="geometry.radius",
            schema="plp.geometry.v1",
            capability=Capability.GEOMETRY.value,
            values={
                "mean_radius": float(np.mean(radii)),
                "std_radius": float(np.std(radii)),
                "max_radius": float(np.max(radii)),
                "n_particles": float(len(radii)),
            },
        )


class _EnergyKineticObserver:
    def observe(self, world: Any) -> ObservationBlock:
        if not isinstance(world, PhysicalState) or not world.particles:
            return ObservationBlock(
                name="energy.kinetic",
                schema="plp.energy.v1",
                capability=Capability.ENERGY.value,
                values={"kinetic_energy": 0.0},
            )

        ke = 0.0
        for p in world.particles.values():
            ke += 0.5 * p.mass * float(np.dot(p.velocity, p.velocity))

        return ObservationBlock(
            name="energy.kinetic",
            schema="plp.energy.v1",
            capability=Capability.ENERGY.value,
            values={"kinetic_energy": float(ke)},
        )


# ==========================================================
# PGRAModule（Codec + Logic）
# ==========================================================

class PGRAModule:
    """
    Capsule を入出力とする PGRA モジュール。

    内部構造:
      decode (Codec) → geometric_relaxation (Logic) → encode (Codec)

    Logic（PGRAPhysicsEngine）は Capsule を一切知らない。
    """

    def __init__(
        self,
        engine: Optional[PGRAPhysicsEngine] = None,
        codec: Optional[PGRACodec] = None,
        epsilon: float = 1e-4,
        max_iterations: int = 10,
    ):
        self.engine = engine or PGRAPhysicsEngine()
        self.codec = codec or PGRACodec()
        self.epsilon = epsilon
        self.max_iterations = max_iterations

    def process(self, capsule: PLPCapsule) -> PLPCapsule:
        """
        Input Capsule → decode → relax → encode → Output Capsule
        """
        # 1. Decode（現時点では呼び出し側で state を用意するケースも多いため、
        #    エンジンが既に state を持っている場合はそのまま使う）
        # 将来 decode を本格実装したときにここで上書きする
        state = self.engine.state

        # 2. Logic（純粋な幾何緩和。Capsule を知らない）
        self.engine.geometric_relaxation(
            epsilon=self.epsilon,
            max_iterations=self.max_iterations,
        )

        # 3. Encode
        return self.codec.encode(
            state=self.engine.state,
            previous=capsule,
            source="PGRAModule",
        )

    # 実験・デバッグ用の便利メソッド
    def process_state(self, state: PhysicalState, previous: Optional[PLPCapsule] = None) -> PLPCapsule:
        """内部状態を直接渡して処理したい場合（実験用）"""
        self.engine.state = state
        self.engine.geometric_relaxation(
            epsilon=self.epsilon,
            max_iterations=self.max_iterations,
        )
        return self.codec.encode(
            state=self.engine.state,
            previous=previous,
            source="PGRAModule",
        )
