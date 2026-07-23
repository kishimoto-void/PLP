"""
PGRA Relaxation Strategy
========================
Metric を元に State の位置を補正・更新する戦略実行クラス。
"""

from __future__ import annotations

import numpy as np

from .state import PhysicalState
from .reference import GeometricMetric
from .policy import CorrectionPolicy, MassWeightedPolicy


class RelaxationStrategy:
    """Metric を元に State の位置を補正・更新する戦略実行クラス"""

    def __init__(self, policy: CorrectionPolicy | None = None):
        self.policy = policy or MassWeightedPolicy()

    def apply_correction(
        self, state: PhysicalState, metric: GeometricMetric, weight: float
    ) -> None:
        if metric.magnitude == 0.0 or np.all(metric.raw_error_vector == 0):
            return

        corrections = self.policy.calculate_corrections(state, metric, weight)

        if len(metric.affected_particle_ids) == 2:
            # 2粒子間の引き寄せ/離反補正
            p1_id, p2_id = metric.affected_particle_ids
            state.particles[p1_id].position -= corrections[p1_id]
            state.particles[p2_id].position += corrections[p2_id]
        else:
            # 複数粒子の同一方向シフト補正 (重心等)
            # 0.1 は現時点の減衰係数（後でパラメータ化可能）
            for pid, corr in corrections.items():
                state.particles[pid].position += corr * 0.1
