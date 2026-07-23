"""
PGRA Pure Reference & Metric
============================
Reference は「現在の State を評価して Metric を返すだけ」の純粋関数的インターフェース。
状態変更ロジックを一切排除。
"""

from __future__ import annotations

from typing import Protocol, List
from dataclasses import dataclass
import numpy as np

from .state import PhysicalState, Geometry


@dataclass
class GeometricMetric:
    """純粋な偏差評価結果データ"""
    reference_id: str
    magnitude: float              # 誤差のスカラー絶対量
    raw_error_vector: np.ndarray  # 生の3D誤差ベクトル Δ
    affected_particle_ids: List[str]


class Reference(Protocol):
    id: str
    priority: int  # 優先度 (100: Stability, 80: Collision, 60: Joint, etc.)
    weight: float

    def evaluate_metric(self, state: PhysicalState) -> GeometricMetric:
        """時間を進めず、Stateを変更することなく、純粋に Metric のみを計算して返す"""
        ...


class DistanceReference:
    """距離基準"""

    def __init__(
        self,
        ref_id: str,
        p1_id: str,
        p2_id: str,
        distance: float,
        priority: int = 50,
        weight: float = 1.0,
    ):
        self.id = ref_id
        self.p1_id = p1_id
        self.p2_id = p2_id
        self.target_distance = distance
        self.priority = priority
        self.weight = weight

    def evaluate_metric(self, state: PhysicalState) -> GeometricMetric:
        p1 = state.particles[self.p1_id].position
        p2 = state.particles[self.p2_id].position
        delta_vec = p1 - p2
        dist = float(np.linalg.norm(delta_vec))

        if dist == 0.0:
            return GeometricMetric(
                self.id, 0.0, np.zeros(3, dtype=np.float64), [self.p1_id, self.p2_id]
            )

        mag = dist - self.target_distance
        raw_vec = (mag / dist) * delta_vec
        return GeometricMetric(
            self.id, abs(mag), raw_vec.astype(np.float64), [self.p1_id, self.p2_id]
        )


class StabilityReference:
    """重心・支持領域の安定度基準"""

    def __init__(
        self,
        ref_id: str,
        particle_ids: List[str],
        support_geom_id: str,
        min_margin: float = 0.80,
        priority: int = 100,
        weight: float = 1.0,
    ):
        self.id = ref_id
        self.particle_ids = particle_ids
        self.support_geom_id = support_geom_id
        self.min_margin = min_margin
        self.priority = priority
        self.weight = weight

    def evaluate_metric(self, state: PhysicalState) -> GeometricMetric:
        total_mass = sum(state.particles[pid].mass for pid in self.particle_ids)
        if total_mass <= 0:
            return GeometricMetric(
                self.id, 0.0, np.zeros(3, dtype=np.float64), self.particle_ids
            )

        com_2d = (
            sum(
                state.particles[pid].position[:2] * state.particles[pid].mass
                for pid in self.particle_ids
            )
            / total_mass
        )

        geom = state.geometries[self.support_geom_id]
        poly_pts = np.array(
            [state.particles[pid].position[:2] for pid in geom.particle_ids],
            dtype=np.float64,
        )
        poly_center_2d = np.mean(poly_pts, axis=0)

        max_radius = float(np.max(np.linalg.norm(poly_pts - poly_center_2d, axis=1)))
        if max_radius == 0.0:
            return GeometricMetric(
                self.id, 0.0, np.zeros(3, dtype=np.float64), self.particle_ids
            )

        current_margin = max(
            0.0, 1.0 - (float(np.linalg.norm(com_2d - poly_center_2d)) / max_radius)
        )
        if current_margin >= self.min_margin:
            return GeometricMetric(
                self.id, 0.0, np.zeros(3, dtype=np.float64), self.particle_ids
            )

        mag = self.min_margin - current_margin
        diff_2d = poly_center_2d - com_2d
        raw_vec_3d = np.array([diff_2d[0], diff_2d[1], 0.0], dtype=np.float64)

        return GeometricMetric(self.id, float(mag), raw_vec_3d, self.particle_ids)
