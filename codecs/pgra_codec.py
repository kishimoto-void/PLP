"""
PGRA Codec & Module
===================
PGRA を Capsule 中心のモジュールとして扱う実装。

構成:
  PGRAModule
  ├── PGRACodec          # Capsule ⇔ PhysicalState
  └── RelaxationEngine   # 純粋な幾何緩和ロジック（Capsule を知らない）

Decoder 公理:
  D1 Semantic-Free Reconstruction  — 意味を復元しない
  D2 Snapshot Immutability (≡)     — 破壊的変更をしない
  D3 Geometric Priority            — 位置・距離を最優先
  D4 Incomplete Observation Tolerance — 欠落は捏造しない
  D5 Residue as Global Scalar (≠)  — residue は系全体の数値特徴量
  D6 Round-trip Fidelity as Goal   — 観測の再現性を基準にする
  D7 Confidence                    — 復元結果に信頼度を付与
  D8 Reconstruction Level          — EXACT / PARTIAL / MINIMAL / EMPTY

使用例:
  module = PGRAModule()
  output = module.process(input_capsule)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Protocol, Sequence
import numpy as np

from plp_capsule import (
    PLPCapsule,
    CapsuleBuilder,
    InputCapsule,
    ObservationBlock,
    Capability,
)
from PGRA.state import PhysicalState, Particle
from PGRA.engine import PGRAPhysicsEngine
from PGRA.reference import Reference
from .base import CapsuleCodec, CapsuleModule


# ==========================================================
# D8 Reconstruction Level
# ==========================================================

class ReconstructionLevel(Enum):
    """復元の忠実度レベル (D8)"""
    EXACT = auto()      # geometry.particles など明示的な粒子情報から完全復元
    PARTIAL = auto()    # 一部の粒子のみ復元できた
    MINIMAL = auto()    # 集約情報からの最小再構成
    EMPTY = auto()      # 情報不足で空状態


# ==========================================================
# D7 DecodedState
# ==========================================================

@dataclass(frozen=True)
class DecodedState:
    """
    decode の戻り値。
    状態そのものに加えて、復元の品質情報を持つ。
    """
    state: PhysicalState
    confidence: float                 # 0.0 ~ 1.0
    level: ReconstructionLevel
    source_observations: tuple[str, ...] = ()  # 使った observation 名

    @property
    def is_usable(self) -> bool:
        """Module 側が簡易に判断するためのヘルパー"""
        return self.confidence >= 0.5 and self.level != ReconstructionLevel.EMPTY


# ==========================================================
# ObservationDecoder Protocol (plugin skeleton)
# ==========================================================

class ObservationDecoder(Protocol):
    """
    特定の Observation を PhysicalState の一部に変換するプラグイン。
    将来 GeometryDecoder / EnergyDecoder / ConstraintDecoder を
    独立に登録できるようにするための骨格。
    """

    name: str  # 担当する observation name（例: "geometry.particles"）

    def can_decode(self, obs: ObservationBlock) -> bool:
        ...

    def decode(self, obs: ObservationBlock) -> tuple[List[Particle], float]:
        """
        Returns:
            particles: 復元できた粒子リスト
            confidence: この観測単体の信頼度 0.0~1.0
        """
        ...


# ==========================================================
# Concrete Decoders
# ==========================================================

class GeometryParticlesDecoder:
    """geometry.particles → 粒子リスト (EXACT向け)"""

    name = "geometry.particles"

    def can_decode(self, obs: ObservationBlock) -> bool:
        return obs.name == self.name

    def decode(self, obs: ObservationBlock) -> tuple[List[Particle], float]:
        vals = obs.values
        n = int(vals.get("n", 0))
        if n <= 0:
            return [], 0.0

        ids_str = str(vals.get("ids", ""))
        ids = [s.strip() for s in ids_str.split(",") if s.strip()] if ids_str else [f"p{i}" for i in range(n)]

        pos_flat = _parse_float_list(vals.get("pos", ""))
        vel_flat = _parse_float_list(vals.get("vel", ""))
        mass_list = _parse_float_list(vals.get("mass", ""))

        particles: List[Particle] = []
        for i in range(n):
            pid = ids[i] if i < len(ids) else f"p{i}"

            if len(pos_flat) >= (i + 1) * 3:
                pos = np.array(pos_flat[i * 3:(i + 1) * 3], dtype=np.float64)
            else:
                # 位置欠落 → この粒子は作らない (D4)
                continue

            if len(vel_flat) >= (i + 1) * 3:
                vel = np.array(vel_flat[i * 3:(i + 1) * 3], dtype=np.float64)
            else:
                vel = np.zeros(3, dtype=np.float64)

            mass = mass_list[i] if i < len(mass_list) else 1.0
            if mass <= 0:
                mass = 1.0

            particles.append(Particle(
                id=pid,
                position=pos,
                velocity=vel,
                mass=float(mass),
            ))

        if not particles:
            return [], 0.0

        # 全粒子復元できていれば 1.0、一部なら比例
        confidence = len(particles) / n
        return particles, confidence


class GeometryRadiusDecoder:
    """
    geometry.radius → 最小再構成 (MINIMAL向け)

    配置戦略は実装依存である。
    現在の実装は円周上の等間隔配置を用いるが、
    これは公理ではなく実装戦略である。
    将来、正方格子 / Fibonacci sphere / seeded random 等に
    差し替えても公理を壊さない。
    """

    name = "geometry.radius"

    def can_decode(self, obs: ObservationBlock) -> bool:
        return obs.name == self.name

    def decode(self, obs: ObservationBlock) -> tuple[List[Particle], float]:
        vals = obs.values
        n = int(vals.get("n_particles", 0))
        mean_radius = float(vals.get("mean_radius", 0.0))

        if n <= 0:
            return [], 0.0

        # -------------------------------------------------------
        # Minimal deterministic reconstruction.
        # The placement strategy is implementation-defined.
        # Current strategy: equal spacing on a circle of radius mean_radius.
        # -------------------------------------------------------
        particles: List[Particle] = []
        for i in range(n):
            theta = 2.0 * np.pi * i / n
            pos = np.array([
                mean_radius * np.cos(theta),
                mean_radius * np.sin(theta),
                0.0,
            ], dtype=np.float64)
            particles.append(Particle(
                id=f"p{i}",
                position=pos,
                velocity=np.zeros(3, dtype=np.float64),
                mass=1.0,
            ))

        # 集約情報からの再構成なので信頼度は低め
        confidence = 0.4
        return particles, confidence


def _parse_float_list(s: Any) -> List[float]:
    if not s:
        return []
    if isinstance(s, (list, tuple)):
        return [float(x) for x in s]
    try:
        return [float(x) for x in str(s).split(",") if x.strip()]
    except ValueError:
        return []


# ==========================================================
# PGRACodec
# ==========================================================

class PGRACodec:
    """
    Capsule ⇔ PhysicalState の相互変換。

    - decode: Observation から DecodedState を構築（公理準拠）
    - encode: PhysicalState を観測して Capsule を生成

    ロジック（緩和計算）は一切持たない。
    """

    def __init__(self, source: str = "PGRA"):
        self.source = source
        self._builder = CapsuleBuilder()

        # 観測の登録順: 幾何 → 粒子詳細 → エネルギー
        self._builder.register(_GeometryRadiusObserver(), priority=10)
        self._builder.register(_ParticlePositionsObserver(), priority=15)
        self._builder.register(_EnergyKineticObserver(), priority=20)

        # Decoder プラグイン（優先度順に試行）
        self._decoders: List[ObservationDecoder] = [
            GeometryParticlesDecoder(),  # EXACT
            GeometryRadiusDecoder(),     # MINIMAL
        ]

    def register_decoder(self, decoder: ObservationDecoder) -> None:
        """新しい ObservationDecoder を追加登録する"""
        self._decoders.append(decoder)

    # ----------------------------------------------------------
    # decode  (Axiom D1–D8)
    # ----------------------------------------------------------
    def decode(self, capsule: PLPCapsule) -> DecodedState:
        """
        Capsule の Observation から DecodedState を復元する。

        優先順位 (D3 Geometric Priority):
          1. geometry.particles → EXACT / PARTIAL
          2. geometry.radius    → MINIMAL
          3. 情報不足           → EMPTY

        捏造は行わない (D4)。
        """
        obs_map = {o.name: o for o in capsule.observations}
        used: List[str] = []

        # 登録された Decoder を優先順に試す
        for decoder in self._decoders:
            obs = obs_map.get(decoder.name)
            if obs is None or not decoder.can_decode(obs):
                continue

            particles, conf = decoder.decode(obs)
            if not particles:
                continue

            state = PhysicalState()
            for p in particles:
                state.particles[p.id] = p

            used.append(decoder.name)

            # レベル判定
            if decoder.name == "geometry.particles":
                if conf >= 0.999:
                    level = ReconstructionLevel.EXACT
                else:
                    level = ReconstructionLevel.PARTIAL
            else:
                level = ReconstructionLevel.MINIMAL

            return DecodedState(
                state=state,
                confidence=float(conf),
                level=level,
                source_observations=tuple(used),
            )

        # どの Decoder も成功しなかった
        return DecodedState(
            state=PhysicalState(),
            confidence=0.0,
            level=ReconstructionLevel.EMPTY,
            source_observations=(),
        )

    # ----------------------------------------------------------
    # encode
    # ----------------------------------------------------------
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


class _ParticlePositionsObserver:
    """
    粒子の位置・速度・質量を明示的に載せる観測。
    decode 側がこれを最優先で使う (D3 + D6)。
    """

    def observe(self, world: Any) -> ObservationBlock:
        if not isinstance(world, PhysicalState) or not world.particles:
            return ObservationBlock(
                name="geometry.particles",
                schema="plp.geometry.particles.v1",
                capability=Capability.GEOMETRY.value,
                values={"n": 0.0},
            )

        particles = list(world.particles.values())
        n = len(particles)

        ids = ",".join(p.id for p in particles)
        pos_flat = ",".join(f"{v:.8g}" for p in particles for v in p.position)
        vel_flat = ",".join(f"{v:.8g}" for p in particles for v in p.velocity)
        mass_flat = ",".join(f"{p.mass:.8g}" for p in particles)

        return ObservationBlock(
            name="geometry.particles",
            schema="plp.geometry.particles.v1",
            capability=Capability.GEOMETRY.value,
            values={
                "n": float(n),
                "ids": ids,
                "pos": pos_flat,
                "vel": vel_flat,
                "mass": mass_flat,
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
        min_confidence: float = 0.5,
    ):
        self.engine = engine or PGRAPhysicsEngine()
        self.codec = codec or PGRACodec()
        self.epsilon = epsilon
        self.max_iterations = max_iterations
        self.min_confidence = min_confidence

    def process(self, capsule: PLPCapsule) -> PLPCapsule:
        """
        Input Capsule → decode → relax → encode → Output Capsule
        """
        # 1. Decode (Axiom-driven) → DecodedState
        decoded = self.codec.decode(capsule)

        # confidence が十分で粒子がある場合のみ engine に載せる
        if decoded.is_usable:
            self.engine.state = decoded.state
        # そうでなければ既存の engine.state を維持（後方互換）

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

    def process_state(
        self,
        state: PhysicalState,
        previous: Optional[PLPCapsule] = None,
    ) -> PLPCapsule:
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
