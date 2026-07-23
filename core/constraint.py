"""
PLP Core — Constraint v1.1 (strict)
===================================
制約の定義のみ。ソルバ・更新・意味解釈は持たない。

共通 Core インターフェース:
  schema / version
  check_invariants() / is_valid()
  copy() / to_dict() / from_dict()

不変条件:
  C1. id は非空 ConstraintID
  C2. kind は ConstraintKind
  C3. state は ConstraintState
  C4. dim >= 0
  C5. particle_ids は非空文字列のタプル
  C6. params の値は finite float
  C7. priority は int
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Optional, Protocol, Sequence, runtime_checkable
from uuid import uuid4
import numpy as np


CONSTRAINT_VERSION = "1.1"
CONSTRAINT_SCHEMA = "plp.core.constraint/1.1"


class ConstraintID(str):
    """制約識別子。空文字禁止。"""

    __slots__ = ()

    def __new__(cls, value: str) -> "ConstraintID":
        if not isinstance(value, str):
            raise TypeError(f"ConstraintID requires str, got {type(value).__name__}")
        value = value.strip()
        if not value:
            raise ValueError("ConstraintID must be non-empty")
        return super().__new__(cls, value)

    @classmethod
    def new(cls) -> "ConstraintID":
        return cls(str(uuid4()))


class ConstraintKind(str, Enum):
    BOUNDARY = "boundary"
    DISTANCE = "distance"
    LIMIT = "limit"
    JOINT = "joint"
    COLLISION = "collision"
    PROJECTION = "projection"
    CUSTOM = "custom"


class ConstraintState(str, Enum):
    """Core は意味を解釈しない。状態値のみ保持する。"""
    ACTIVE = "active"
    DISABLED = "disabled"
    BROKEN = "broken"


@runtime_checkable
class ConstraintParameters(Protocol):
    """params の互換面。実装は dict[str, float] で十分。"""

    def keys(self): ...
    def __getitem__(self, key: str) -> float: ...


def _as_1d_f64(name: str, x: Any, *, dim: Optional[int] = None) -> np.ndarray:
    arr = np.asarray(x, dtype=np.float64).reshape(-1)
    if arr.size < 1:
        raise ValueError(f"{name} must be non-empty")
    if not np.isfinite(arr).all():
        raise ValueError(f"{name} must be finite")
    if dim is not None and arr.size != dim:
        raise ValueError(f"{name} expected dim={dim}, got {arr.size}")
    return arr


def _validate_params(params: Any) -> dict[str, float]:
    if params is None:
        return {}
    if not isinstance(params, Mapping):
        raise TypeError("params must be a Mapping[str, float]")
    out: dict[str, float] = {}
    for k, v in params.items():
        if not isinstance(k, str):
            raise TypeError("params keys must be str")
        fv = float(v)
        if not np.isfinite(fv):
            raise ValueError(f"params[{k}] must be finite")
        out[k] = fv
    return out


@dataclass(slots=True)
class Constraint:
    """
    制約の最小単位。

    - id           : ConstraintID
    - kind         : 制約種別
    - state        : ACTIVE / DISABLED / BROKEN
    - priority     : Solver 順序ヒント（Core は解釈しない）
    - dim          : 関連空間次元（0 なら未指定）
    - particle_ids : 関与する ParticleID 文字列
    - params       : 数値パラメータ
    - metadata     : opaque（Core は解釈しない）
    """

    id: ConstraintID = field(default_factory=ConstraintID.new)
    kind: ConstraintKind = ConstraintKind.CUSTOM
    state: ConstraintState = ConstraintState.ACTIVE
    priority: int = 0
    dim: int = 0
    particle_ids: tuple[str, ...] = ()
    params: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.id, ConstraintID):
            self.id = ConstraintID(str(self.id))

        if not isinstance(self.kind, ConstraintKind):
            self.kind = ConstraintKind(str(self.kind))

        if not isinstance(self.state, ConstraintState):
            self.state = ConstraintState(str(self.state))

        if not isinstance(self.priority, int):
            raise TypeError("priority must be int")

        if not isinstance(self.dim, int) or self.dim < 0:
            raise ValueError("dim must be int >= 0")

        ids = tuple(str(x) for x in self.particle_ids)
        for x in ids:
            if not x:
                raise ValueError("particle_ids must be non-empty strings")
        self.particle_ids = ids

        self.params = _validate_params(self.params)

        md: dict[str, Any] = {}
        for k, v in dict(self.metadata).items():
            if not isinstance(k, str):
                raise TypeError("metadata keys must be str")
            md[k] = v
        self.metadata = md

    @property
    def schema(self) -> str:
        return CONSTRAINT_SCHEMA

    @property
    def version(self) -> str:
        return CONSTRAINT_VERSION

    @property
    def enabled(self) -> bool:
        """互換用。ACTIVE のみ True。"""
        return self.state is ConstraintState.ACTIVE

    def check_invariants(self) -> None:
        if not isinstance(self.id, ConstraintID) or not str(self.id):
            raise ValueError("invalid id")
        if not isinstance(self.kind, ConstraintKind):
            raise TypeError("kind must be ConstraintKind")
        if not isinstance(self.state, ConstraintState):
            raise TypeError("state must be ConstraintState")
        if not isinstance(self.priority, int):
            raise TypeError("priority must be int")
        if not isinstance(self.dim, int) or self.dim < 0:
            raise ValueError("dim must be int >= 0")
        for x in self.particle_ids:
            if not isinstance(x, str) or not x:
                raise ValueError("invalid particle_id")
        _validate_params(self.params)

    def is_valid(self) -> bool:
        try:
            self.check_invariants()
            return True
        except (TypeError, ValueError):
            return False

    def copy(self) -> "Constraint":
        return Constraint(
            id=ConstraintID(str(self.id)),
            kind=self.kind,
            state=self.state,
            priority=self.priority,
            dim=self.dim,
            particle_ids=self.particle_ids,
            params=dict(self.params),
            metadata=dict(self.metadata),
        )

    def with_state(self, state: ConstraintState) -> "Constraint":
        c = self.copy()
        c.state = state
        return c

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": CONSTRAINT_SCHEMA,
            "version": CONSTRAINT_VERSION,
            "id": str(self.id),
            "kind": self.kind.value,
            "state": self.state.value,
            "priority": self.priority,
            "dim": self.dim,
            "particle_ids": list(self.particle_ids),
            "params": dict(self.params),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Constraint":
        return cls(
            id=ConstraintID(str(data["id"])) if "id" in data else ConstraintID.new(),
            kind=ConstraintKind(str(data.get("kind", "custom"))),
            state=ConstraintState(str(data.get("state", "active"))),
            priority=int(data.get("priority", 0)),
            dim=int(data.get("dim", 0)),
            particle_ids=tuple(data.get("particle_ids") or ()),
            params=dict(data.get("params") or {}),
            metadata=dict(data.get("metadata") or {}),
        )


def boundary_box(
    *,
    dim: int,
    low: Sequence[float],
    high: Sequence[float],
    particle_ids: Sequence[str] = (),
    priority: int = 0,
) -> Constraint:
    lo = _as_1d_f64("low", low, dim=dim)
    hi = _as_1d_f64("high", high, dim=dim)
    if not np.all(lo <= hi):
        raise ValueError("low must be <= high elementwise")
    params = {f"low_{i}": float(lo[i]) for i in range(dim)}
    params.update({f"high_{i}": float(hi[i]) for i in range(dim)})
    return Constraint(
        kind=ConstraintKind.BOUNDARY,
        dim=dim,
        particle_ids=tuple(particle_ids),
        params=params,
        priority=priority,
    )


def distance_constraint(
    particle_a: str,
    particle_b: str,
    *,
    rest_length: float,
    dim: int = 0,
    priority: int = 0,
) -> Constraint:
    rl = float(rest_length)
    if not np.isfinite(rl) or rl <= 0.0:
        raise ValueError("rest_length must be finite and positive")
    if not particle_a or not particle_b:
        raise ValueError("particle ids must be non-empty")
    return Constraint(
        kind=ConstraintKind.DISTANCE,
        dim=dim,
        particle_ids=(str(particle_a), str(particle_b)),
        params={"rest_length": rl},
        priority=priority,
    )


def scalar_limit(
    *,
    name: str,
    low: float,
    high: float,
    particle_ids: Sequence[str] = (),
    priority: int = 0,
) -> Constraint:
    lo, hi = float(low), float(high)
    if not np.isfinite(lo) or not np.isfinite(hi):
        raise ValueError("low/high must be finite")
    if lo > hi:
        raise ValueError("low must be <= high")
    if not name:
        raise ValueError("name must be non-empty")
    return Constraint(
        kind=ConstraintKind.LIMIT,
        particle_ids=tuple(particle_ids),
        params={"low": lo, "high": hi},
        priority=priority,
        metadata={"target": name},
    )


def joint(
    particle_a: str,
    particle_b: str,
    *,
    dim: int = 0,
    priority: int = 0,
    metadata: Optional[Mapping[str, Any]] = None,
) -> Constraint:
    if not particle_a or not particle_b:
        raise ValueError("particle ids must be non-empty")
    return Constraint(
        kind=ConstraintKind.JOINT,
        dim=dim,
        particle_ids=(str(particle_a), str(particle_b)),
        priority=priority,
        metadata=dict(metadata or {}),
    )


if __name__ == "__main__":
    c1 = boundary_box(dim=3, low=[-1, -1, -1], high=[1, 1, 1], priority=10)
    assert c1.is_valid() and c1.enabled
    c2 = distance_constraint("a", "b", rest_length=1.7, dim=3)
    c2b = c2.with_state(ConstraintState.DISABLED)
    assert not c2b.enabled
    d = c2.to_dict()
    c3 = Constraint.from_dict(d)
    assert c3.params["rest_length"] == 1.7
    print("schema:", c1.schema, "version:", c1.version)
    print("Constraint v1.1 ok")
