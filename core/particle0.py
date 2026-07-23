"""
PLP Core — Particle0 v1.2 (Reference Implementation)
====================================================
意味を持たない最小存在単位。

不変条件 (Invariants):
  I1. position.ndim == 1 and position.size >= 1
  I2. velocity.shape == position.shape
  I3. mass > 0 and isfinite(mass)
  I4. isfinite(position).all() and isfinite(velocity).all()
  I5. isfinite(phase)
  I6. id は非空 ParticleID
  I7. metadata は str キーの辞書（値は opaque、Core は解釈しない）

Core は AI / Emotion / Memory / Relation を持たない。

Metadata 名前空間（仕様上の予約）:
  plp.*           — 公式予約
  vendor.*        — 実装ベンダー用
  experimental.*  — 実験用
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Protocol, runtime_checkable
from uuid import uuid4
import numpy as np


# ==========================================================
# Version / Schema
# ==========================================================

PLP_CORE_VERSION = "1.2"
PARTICLE0_SCHEMA = "plp.core.particle0/1.2"


# ==========================================================
# ParticleID
# ==========================================================

class ParticleID(str):
    """存在識別子。空文字禁止。str として比較・辞書キー利用可能。"""

    __slots__ = ()

    def __new__(cls, value: str) -> "ParticleID":
        if not isinstance(value, str):
            raise TypeError(f"ParticleID requires str, got {type(value).__name__}")
        value = value.strip()
        if not value:
            raise ValueError("ParticleID must be non-empty")
        return super().__new__(cls, value)

    @classmethod
    def new(cls) -> "ParticleID":
        return cls(str(uuid4()))


# ==========================================================
# Protocol（実装非依存の互換面）
# ==========================================================

@runtime_checkable
class ParticleLike(Protocol):
    """
    PLP 互換の最小面。
    NumPy / GPU / JAX / Rust バインディングなどでもこの面を満たせば互換。
    """

    id: ParticleID
    position: np.ndarray
    velocity: np.ndarray
    mass: float
    phase: float

    @property
    def dim(self) -> int: ...

    @property
    def speed(self) -> float: ...

    @property
    def kinetic_energy(self) -> float: ...


# ==========================================================
# Validation helpers
# ==========================================================

def _as_1d_f64(name: str, x: Any) -> np.ndarray:
    arr = np.asarray(x, dtype=np.float64)
    if arr.ndim == 0:
        arr = arr.reshape(1)
    if arr.ndim != 1:
        raise ValueError(f"{name} must be 1-D, got shape {arr.shape}")
    if arr.size < 1:
        raise ValueError(f"{name} must be non-empty")
    if not np.isfinite(arr).all():
        raise ValueError(f"{name} must contain only finite values")
    return arr


def _validate_mass(mass: float) -> float:
    m = float(mass)
    if not np.isfinite(m):
        raise ValueError("mass must be finite")
    if m <= 0.0:
        raise ValueError("mass must be positive")
    return m


def _validate_phase(phase: float) -> float:
    p = float(phase)
    if not np.isfinite(p):
        raise ValueError("phase must be finite")
    return p


def _validate_metadata(md: Any) -> dict[str, Any]:
    if md is None:
        return {}
    if not isinstance(md, Mapping):
        raise TypeError("metadata must be a Mapping[str, Any]")
    out: dict[str, Any] = {}
    for k, v in md.items():
        if not isinstance(k, str):
            raise TypeError(f"metadata keys must be str, got {type(k).__name__}")
        out[k] = v
    return out


def _validate_clock_id(clock_id: Optional[str]) -> Optional[str]:
    if clock_id is None:
        return None
    if not isinstance(clock_id, str) or not clock_id.strip():
        raise ValueError("clock_id must be None or a non-empty str")
    return clock_id.strip()


# ==========================================================
# MutableParticle0
# ==========================================================

@dataclass(slots=True)
class MutableParticle0:
    """
    可変の Particle0。
    物理積分など、状態を更新する経路向け。
    """

    id: ParticleID = field(default_factory=ParticleID.new)
    position: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float64))
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float64))
    mass: float = 1.0
    phase: float = 0.0
    clock_id: Optional[str] = None
    alive: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.id, ParticleID):
            self.id = ParticleID(str(self.id))

        pos = _as_1d_f64("position", self.position)
        vel = _as_1d_f64("velocity", self.velocity)
        if pos.shape != vel.shape:
            raise ValueError(
                f"position and velocity shape mismatch: {pos.shape} vs {vel.shape}"
            )

        self.position = pos
        self.velocity = vel
        self.mass = _validate_mass(self.mass)
        self.phase = _validate_phase(self.phase)
        self.clock_id = _validate_clock_id(self.clock_id)

        if not isinstance(self.alive, bool):
            raise TypeError("alive must be bool")

        self.metadata = _validate_metadata(self.metadata)

    @property
    def schema(self) -> str:
        return PARTICLE0_SCHEMA

    @property
    def dim(self) -> int:
        return int(self.position.shape[0])

    @property
    def speed(self) -> float:
        return float(np.linalg.norm(self.velocity))

    @property
    def kinetic_energy(self) -> float:
        return 0.5 * self.mass * float(np.dot(self.velocity, self.velocity))

    def metadata_view(self) -> Mapping[str, Any]:
        return self.metadata

    def check_invariants(self) -> None:
        _as_1d_f64("position", self.position)
        _as_1d_f64("velocity", self.velocity)
        if self.position.shape != self.velocity.shape:
            raise ValueError("position/velocity shape mismatch")
        _validate_mass(self.mass)
        _validate_phase(self.phase)
        if not isinstance(self.id, ParticleID) or not str(self.id):
            raise ValueError("invalid id")
        _validate_clock_id(self.clock_id)
        if not isinstance(self.alive, bool):
            raise TypeError("alive must be bool")
        _validate_metadata(self.metadata)

    def is_valid(self) -> bool:
        try:
            self.check_invariants()
            return True
        except (TypeError, ValueError):
            return False

    def copy(self) -> "MutableParticle0":
        return MutableParticle0(
            id=ParticleID(str(self.id)),
            position=self.position.copy(),
            velocity=self.velocity.copy(),
            mass=self.mass,
            phase=self.phase,
            clock_id=self.clock_id,
            alive=self.alive,
            metadata=dict(self.metadata),
        )

    def freeze(self) -> "FrozenParticle0":
        return FrozenParticle0.from_mutable(self)

    def with_state(
        self,
        *,
        position: Optional[np.ndarray] = None,
        velocity: Optional[np.ndarray] = None,
        mass: Optional[float] = None,
        phase: Optional[float] = None,
        alive: Optional[bool] = None,
    ) -> "MutableParticle0":
        return MutableParticle0(
            id=ParticleID(str(self.id)),
            position=self.position.copy() if position is None else position,
            velocity=self.velocity.copy() if velocity is None else velocity,
            mass=self.mass if mass is None else mass,
            phase=self.phase if phase is None else phase,
            clock_id=self.clock_id,
            alive=self.alive if alive is None else alive,
            metadata=dict(self.metadata),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": PARTICLE0_SCHEMA,
            "id": str(self.id),
            "position": self.position.tolist(),
            "velocity": self.velocity.tolist(),
            "mass": self.mass,
            "phase": self.phase,
            "clock_id": self.clock_id,
            "alive": self.alive,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MutableParticle0":
        return cls(
            id=ParticleID(str(data["id"])),
            position=np.asarray(data["position"], dtype=np.float64),
            velocity=np.asarray(data["velocity"], dtype=np.float64),
            mass=float(data.get("mass", 1.0)),
            phase=float(data.get("phase", 0.0)),
            clock_id=data.get("clock_id"),
            alive=bool(data.get("alive", True)),
            metadata=dict(data.get("metadata") or {}),
        )


# 互換エイリアス（既定は Mutable）
Particle0 = MutableParticle0


# ==========================================================
# FrozenParticle0
# ==========================================================

@dataclass(frozen=True, slots=True)
class FrozenParticle0:
    """
    不変の Particle0。
    配列は writeable=False に固定する。
    共有・検証・Capsule 載せ向け。
    """

    id: ParticleID
    position: np.ndarray
    velocity: np.ndarray
    mass: float = 1.0
    phase: float = 0.0
    clock_id: Optional[str] = None
    alive: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.id, ParticleID):
            object.__setattr__(self, "id", ParticleID(str(self.id)))

        pos = _as_1d_f64("position", self.position).copy()
        vel = _as_1d_f64("velocity", self.velocity).copy()
        if pos.shape != vel.shape:
            raise ValueError(
                f"position and velocity shape mismatch: {pos.shape} vs {vel.shape}"
            )
        pos.setflags(write=False)
        vel.setflags(write=False)

        object.__setattr__(self, "position", pos)
        object.__setattr__(self, "velocity", vel)
        object.__setattr__(self, "mass", _validate_mass(self.mass))
        object.__setattr__(self, "phase", _validate_phase(self.phase))
        object.__setattr__(self, "clock_id", _validate_clock_id(self.clock_id))

        if not isinstance(self.alive, bool):
            raise TypeError("alive must be bool")

        md = _validate_metadata(self.metadata)
        object.__setattr__(self, "metadata", md)

    @property
    def schema(self) -> str:
        return PARTICLE0_SCHEMA

    @property
    def dim(self) -> int:
        return int(self.position.shape[0])

    @property
    def speed(self) -> float:
        return float(np.linalg.norm(self.velocity))

    @property
    def kinetic_energy(self) -> float:
        return 0.5 * self.mass * float(np.dot(self.velocity, self.velocity))

    def metadata_view(self) -> Mapping[str, Any]:
        return self.metadata

    def check_invariants(self) -> None:
        _as_1d_f64("position", self.position)
        _as_1d_f64("velocity", self.velocity)
        if self.position.shape != self.velocity.shape:
            raise ValueError("position/velocity shape mismatch")
        _validate_mass(self.mass)
        _validate_phase(self.phase)
        if not isinstance(self.id, ParticleID) or not str(self.id):
            raise ValueError("invalid id")
        _validate_clock_id(self.clock_id)
        if not isinstance(self.alive, bool):
            raise TypeError("alive must be bool")
        _validate_metadata(self.metadata)

    def is_valid(self) -> bool:
        try:
            self.check_invariants()
            return True
        except (TypeError, ValueError):
            return False

    def thaw(self) -> MutableParticle0:
        return MutableParticle0(
            id=ParticleID(str(self.id)),
            position=self.position.copy(),
            velocity=self.velocity.copy(),
            mass=self.mass,
            phase=self.phase,
            clock_id=self.clock_id,
            alive=self.alive,
            metadata=dict(self.metadata),
        )

    def copy(self) -> "FrozenParticle0":
        return FrozenParticle0(
            id=ParticleID(str(self.id)),
            position=self.position.copy(),
            velocity=self.velocity.copy(),
            mass=self.mass,
            phase=self.phase,
            clock_id=self.clock_id,
            alive=self.alive,
            metadata=dict(self.metadata),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": PARTICLE0_SCHEMA,
            "id": str(self.id),
            "position": self.position.tolist(),
            "velocity": self.velocity.tolist(),
            "mass": self.mass,
            "phase": self.phase,
            "clock_id": self.clock_id,
            "alive": self.alive,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "FrozenParticle0":
        return cls(
            id=ParticleID(str(data["id"])),
            position=np.asarray(data["position"], dtype=np.float64),
            velocity=np.asarray(data["velocity"], dtype=np.float64),
            mass=float(data.get("mass", 1.0)),
            phase=float(data.get("phase", 0.0)),
            clock_id=data.get("clock_id"),
            alive=bool(data.get("alive", True)),
            metadata=dict(data.get("metadata") or {}),
        )

    @classmethod
    def from_mutable(cls, p: MutableParticle0) -> "FrozenParticle0":
        return cls(
            id=ParticleID(str(p.id)),
            position=p.position.copy(),
            velocity=p.velocity.copy(),
            mass=p.mass,
            phase=p.phase,
            clock_id=p.clock_id,
            alive=p.alive,
            metadata=dict(p.metadata),
        )


# ==========================================================
# Factory
# ==========================================================

def create_particles(
    n: int,
    *,
    dim: int = 3,
    seed: Optional[int] = None,
    mass: float = 1.0,
    clock_id: Optional[str] = None,
    frozen: bool = False,
) -> list[MutableParticle0] | list[FrozenParticle0]:
    """最小集団を生成するだけ。配置・意味は付けない。"""
    if not isinstance(n, int) or n < 0:
        raise ValueError("n must be a non-negative int")
    if not isinstance(dim, int) or dim < 1:
        raise ValueError("dim must be an int >= 1")
    _validate_mass(mass)
    _validate_clock_id(clock_id)

    rng = np.random.default_rng(seed)
    out_m: list[MutableParticle0] = []
    for _ in range(n):
        out_m.append(
            MutableParticle0(
                position=rng.normal(0.0, 1.0, size=dim),
                velocity=rng.normal(0.0, 0.05, size=dim),
                mass=mass,
                phase=float(rng.uniform(0.0, 2.0 * np.pi)),
                clock_id=clock_id,
            )
        )
    if frozen:
        return [p.freeze() for p in out_m]
    return out_m


# ==========================================================
# Self-check
# ==========================================================

if __name__ == "__main__":
    ps = create_particles(3, dim=3, seed=0)
    for p in ps:
        assert isinstance(p, ParticleLike)
        assert p.is_valid()
        print(p.id[:8], f"dim={p.dim}", p.position, f"speed={p.speed:.6f}")

    fp = ps[0].freeze()
    assert not fp.position.flags.writeable
    assert isinstance(fp, ParticleLike)

    d = fp.to_dict()
    assert d["schema"] == PARTICLE0_SCHEMA
    fp2 = FrozenParticle0.from_dict(d)
    assert np.allclose(fp.position, fp2.position)

    try:
        MutableParticle0(position=[1.0, 2.0], velocity=[1.0])
        raise SystemExit("shape mismatch should fail")
    except ValueError:
        pass

    try:
        MutableParticle0(mass=0.0)
        raise SystemExit("mass<=0 should fail")
    except ValueError:
        pass

    print("PLP Core Particle0 v1.2 self-check passed")
    print("schema:", PARTICLE0_SCHEMA)
