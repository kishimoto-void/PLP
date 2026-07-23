"""
PLP Core — Geometry v1.1 (strict)
=================================
空間定義のみ。意味・物理法則・AI は持たない。

共通 Core インターフェース:
  schema / version
  check_invariants() / is_valid()
  copy() / to_dict() / from_dict()

不変条件:
  G1. dim >= 1
  G2. origin.shape == (dim,)
  G3. axes.shape == (dim, dim)
  G4. origin / axes は finite
  G5. scale > 0 and finite
  G6. axes は正規直交 (axes.T @ axes ≈ I)  ※ Core 仕様として保証
  G7. |det(axes)| ≈ 1
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional
import numpy as np


GEOMETRY_VERSION = "1.1"
GEOMETRY_SCHEMA = "plp.core.geometry/1.1"

_ORTH_ATOL = 1e-8


def _as_1d_f64(name: str, x: Any, *, dim: Optional[int] = None) -> np.ndarray:
    arr = np.asarray(x, dtype=np.float64).reshape(-1)
    if arr.size < 1:
        raise ValueError(f"{name} must be non-empty")
    if not np.isfinite(arr).all():
        raise ValueError(f"{name} must be finite")
    if dim is not None and arr.size != dim:
        raise ValueError(f"{name} expected dim={dim}, got {arr.size}")
    return arr


def _as_square_f64(name: str, x: Any, *, dim: int) -> np.ndarray:
    arr = np.asarray(x, dtype=np.float64)
    if arr.shape != (dim, dim):
        raise ValueError(f"{name} must have shape ({dim}, {dim}), got {arr.shape}")
    if not np.isfinite(arr).all():
        raise ValueError(f"{name} must be finite")
    return arr


def _validate_orthonormal(axes: np.ndarray, *, atol: float = _ORTH_ATOL) -> None:
    dim = axes.shape[0]
    gram = axes.T @ axes
    if not np.allclose(gram, np.eye(dim), atol=atol):
        raise ValueError("axes must be orthonormal (axes.T @ axes ≈ I)")
    det = float(np.linalg.det(axes))
    if not np.isfinite(det) or abs(abs(det) - 1.0) > atol:
        raise ValueError(f"axes determinant must satisfy |det|≈1, got {det}")


@dataclass(slots=True)
class Geometry:
    """
    空間の最小記述（正規直交座標系 + 等方スケール）。

    - dim     : 空間次元
    - origin  : 原点
    - axes    : 正規直交基底（列が軸）
    - scale   : 等方スケール（正）
                ※ 将来 anisotropic scale (ndarray) への拡張余地を仕様上残す
    """

    dim: int = 3
    origin: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float64))
    axes: np.ndarray = field(default_factory=lambda: np.eye(3, dtype=np.float64))
    scale: float = 1.0

    def __post_init__(self) -> None:
        if not isinstance(self.dim, int) or self.dim < 1:
            raise ValueError("dim must be int >= 1")

        origin = _as_1d_f64("origin", self.origin, dim=self.dim)
        axes = _as_square_f64("axes", self.axes, dim=self.dim)
        _validate_orthonormal(axes)

        s = float(self.scale)
        if not np.isfinite(s) or s <= 0.0:
            raise ValueError("scale must be finite and positive")

        self.origin = origin
        self.axes = axes
        self.scale = s

    # ------------------------------------------------------------------
    # 共通インターフェース
    # ------------------------------------------------------------------

    @property
    def schema(self) -> str:
        return GEOMETRY_SCHEMA

    @property
    def version(self) -> str:
        return GEOMETRY_VERSION

    def check_invariants(self) -> None:
        if not isinstance(self.dim, int) or self.dim < 1:
            raise ValueError("dim must be int >= 1")
        _as_1d_f64("origin", self.origin, dim=self.dim)
        axes = _as_square_f64("axes", self.axes, dim=self.dim)
        _validate_orthonormal(axes)
        if not np.isfinite(self.scale) or self.scale <= 0.0:
            raise ValueError("scale must be finite and positive")

    def is_valid(self) -> bool:
        try:
            self.check_invariants()
            return True
        except (TypeError, ValueError):
            return False

    def copy(self) -> "Geometry":
        return Geometry(
            dim=self.dim,
            origin=self.origin.copy(),
            axes=self.axes.copy(),
            scale=self.scale,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": GEOMETRY_SCHEMA,
            "version": GEOMETRY_VERSION,
            "dim": self.dim,
            "origin": self.origin.tolist(),
            "axes": self.axes.tolist(),
            "scale": self.scale,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Geometry":
        return cls(
            dim=int(data["dim"]),
            origin=np.asarray(data["origin"], dtype=np.float64),
            axes=np.asarray(data["axes"], dtype=np.float64),
            scale=float(data.get("scale", 1.0)),
        )

    # ------------------------------------------------------------------
    # 幾何量
    # ------------------------------------------------------------------

    @property
    def determinant(self) -> float:
        """基底の行列式。右手系なら +1 付近、左手系なら -1 付近。"""
        return float(np.linalg.det(self.axes))

    @property
    def is_right_handed(self) -> bool:
        return self.determinant > 0.0

    def distance(self, a: np.ndarray, b: np.ndarray) -> float:
        aa = _as_1d_f64("a", a, dim=self.dim)
        bb = _as_1d_f64("b", b, dim=self.dim)
        return float(np.linalg.norm(aa - bb))

    def to_local(self, world_point: np.ndarray) -> np.ndarray:
        p = _as_1d_f64("world_point", world_point, dim=self.dim)
        return (self.axes.T @ (p - self.origin)) / self.scale

    def to_world(self, local_point: np.ndarray) -> np.ndarray:
        p = _as_1d_f64("local_point", local_point, dim=self.dim)
        return self.origin + self.scale * (self.axes @ p)

    # ------------------------------------------------------------------
    # 変換合成
    # ------------------------------------------------------------------

    def inverse(self) -> "Geometry":
        """
        この Geometry が表す変換の逆。
        world = origin + scale * axes @ local
        より inverse を構成する。
        """
        inv_scale = 1.0 / self.scale
        inv_axes = self.axes.T  # orthonormal => inverse is transpose
        inv_origin = -inv_scale * (inv_axes @ self.origin)
        return Geometry(
            dim=self.dim,
            origin=inv_origin,
            axes=inv_axes,
            scale=inv_scale,
        )

    def compose(self, other: "Geometry") -> "Geometry":
        """
        変換合成: self ∘ other
        先に other、次に self を適用するイメージ。
        次元は一致必須。
        """
        if self.dim != other.dim:
            raise ValueError(f"dim mismatch: {self.dim} vs {other.dim}")

        new_axes = self.axes @ other.axes
        new_scale = self.scale * other.scale
        new_origin = self.origin + self.scale * (self.axes @ other.origin)
        return Geometry(
            dim=self.dim,
            origin=new_origin,
            axes=new_axes,
            scale=new_scale,
        )

    def translate(self, delta: np.ndarray) -> "Geometry":
        d = _as_1d_f64("delta", delta, dim=self.dim)
        return Geometry(
            dim=self.dim,
            origin=self.origin + d,
            axes=self.axes.copy(),
            scale=self.scale,
        )

    def with_scale(self, scale: float) -> "Geometry":
        return Geometry(
            dim=self.dim,
            origin=self.origin.copy(),
            axes=self.axes.copy(),
            scale=scale,
        )

    @classmethod
    def identity(cls, dim: int = 3) -> "Geometry":
        return cls(
            dim=dim,
            origin=np.zeros(dim, dtype=np.float64),
            axes=np.eye(dim, dtype=np.float64),
            scale=1.0,
        )


if __name__ == "__main__":
    g = Geometry.identity(3)
    assert g.is_valid()
    assert abs(g.determinant - 1.0) < 1e-10

    p = np.array([1.0, 2.0, 3.0])
    assert np.allclose(g.to_world(g.to_local(p)), p)

    g2 = g.translate([1.0, 0.0, 0.0]).with_scale(2.0)
    inv = g2.inverse()
    composed = inv.compose(g2)
    assert composed.is_valid()
    assert np.allclose(
        composed.to_world(np.array([1.0, 0.0, 0.0])),
        np.array([1.0, 0.0, 0.0]),
        atol=1e-8,
    )

    d = g2.to_dict()
    g3 = Geometry.from_dict(d)
    assert g3.is_valid()
    print("schema:", g.schema, "version:", g.version)
    print("Geometry v1.1 ok")
