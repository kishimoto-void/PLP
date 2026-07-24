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

使用例:
  module = PGRAModule()
  output = module.process(input_capsule)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from plp_capsule import (
    PLPCapsule,
    CapsuleBuilder,
    InputCapsule,
    ObservationBlock,
    Capability,
)
from PGRA.state import PhysicalState, Particle, Geometry, GeometryKind
from PGRA.engine import PGRAPhysicsEngine
from PGRA.reference import DistanceReference, Reference
from .base import CapsuleCodec, CapsuleModule


# ==========================================================
# PGRACodec
# ==========================================================

class PGRACodec:
    """
    Capsule ⇔ PhysicalState の相互変換。

    - decode: Observation から PhysicalState を構築（公理準拠）
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

    # ----------------------------------------------------------
    # decode  (Axiom D1–D6)
    # ----------------------------------------------------------
    def decode(self, capsule: PLPCapsule) -> PhysicalState:
        """
        Capsule の Observation から PhysicalState を復元する。

        優先順位 (D3 Geometric Priority):
          1. 粒子位置の明示的観測 (geometry.particles)
          2. 集約幾何 (n_particles + mean_radius) からの最小再構成
          3. 情報が足りなければ空の PhysicalState を返す (D4)

        捏造は行わない。欠落した速度はゼロ、質量は 1.0 をデフォルトとする。
        """
        state = PhysicalState()

        obs_map = {o.name: o for o in capsule.observations}

        # --- 1. 粒子位置が明示されている場合 (最も忠実) ---
        if "geometry.particles" in obs_map:
            particles = self._decode_particle_positions(obs_map["geometry.particles"])
            for p in particles:
                state.particles[p.id] = p
            return state

        # --- 2. 集約情報からの最小再構成 ---
        n = 0
        mean_radius = 0.0

        if "geometry.radius" in obs_map:
            vals = obs_map["geometry.radius"].values
            n = int(vals.get("n_particles", 0))
            mean_radius = float(vals.get("mean_radius", 0.0))

        if n <= 0:
            # 情報不足 → 空状態を返す (D4 Incomplete Observation Tolerance)
            return state

        # 円周上に等間隔配置する最小再構成（幾何のみ、意味なし）
        for i in range(n):
            theta = 2.0 * np.pi * i / n
            pos = np.array([
                mean_radius * np.cos(theta),
                mean_radius * np.sin(theta),
                0.0,
            ], dtype=np.float64)
            pid = f"p{i}"
            state.particles[pid] = Particle(
                id=pid,
                position=pos,
                velocity=np.zeros(3, dtype=np.float64),
                mass=1.0,
            )

        return state

    def _decode_particle_positions(self, obs: ObservationBlock) -> List[Particle]:
        """
        geometry.particles 観測から粒子リストを復元する。

        期待する values の形式:
          {
            "n": 2.0,
            "ids": "p0,p1",          # カンマ区切り文字列
            "pos": "0,0,0,1.5,0,0",  # flat x0,y0,z0,x1,y1,z1...
            "vel": "0,0,0,0,0,0",    # 同様（省略可）
            "mass": "1.0,1.0",       # 省略可
          }
        """
        vals = obs.values
        n = int(vals.get("n", 0))
        if n <= 0:
            return []

        ids_str = str(vals.get("ids", ""))
        ids = [s.strip() for s in ids_str.split(",") if s.strip()] if ids_str else [f"p{i}" for i in range(n)]

        pos_flat = self._parse_float_list(vals.get("pos", ""))
        vel_flat = self._parse_float_list(vals.get("vel", ""))
        mass_list = self._parse_float_list(vals.get("mass", ""))

        particles: List[Particle] = []
        for i in range(n):
            pid = ids[i] if i < len(ids) else f"p{i}"

            if len(pos_flat) >= (i + 1) * 3:
                pos = np.array(pos_flat[i * 3:(i + 1) * 3], dtype=np.float64)
            else:
                # 位置情報欠落 → この粒子は作らない (D4)
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

        return particles

    @staticmethod
    def _parse_float_list(s: Any) -> List[float]:
        if not s:
            return []
        if isinstance(s, (list, tuple)):
            return [float(x) for x in s]
        try:
            return [float(x) for x in str(s).split(",") if x.strip()]
        except ValueError:
            return []

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
    ):
        self.engine = engine or PGRAPhysicsEngine()
        self.codec = codec or PGRACodec()
        self.epsilon = epsilon
        self.max_iterations = max_iterations

    def process(self, capsule: PLPCapsule) -> PLPCapsule:
        """
        Input Capsule → decode → relax → encode → Output Capsule
        """
        # 1. Decode (Axiom-driven)
        state = self.codec.decode(capsule)

        # decode で粒子が得られなかった場合は、既存 engine.state を維持
        # （実験時の後方互換）
        if state.particles:
            self.engine.state = state

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
