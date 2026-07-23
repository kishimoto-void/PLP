"""
PGRA Relaxation Strategy
========================
Metric を元に State の位置を補正・更新する戦略実行クラス。

v1.1:
- position_scale / multi_particle_damping をパラメータ化
- 2粒子と複数粒子で一貫したスケール適用
"""

from __future__ import annotations

import numpy as np

from .state import PhysicalState
from .reference import GeometricMetric
from .policy import CorrectionPolicy, MassWeightedPolicy


class RelaxationStrategy:
    """Metric を元に State の位置を補正・更新する戦略実行クラス"""

    def __init__(
        self,
        policy: CorrectionPolicy | None = None,
        position_scale: float = 1.0,
        multi_particle_damping: float = 0.15,
    ):
        """
        Args:
            policy: 補正ベクトル配分ポリシー
            position_scale: 全体の位置補正スケール（通常 1.0）
            multi_particle_damping: 複数粒子補正時の追加減衰（重心シフト等で振動を抑える）
        """
        self.policy = policy or MassWeightedPolicy()
        self.position_scale = float(position_scale)
        self.multi_particle_damping = float(multi_particle_damping)

        if self.position_scale <= 0.0:
            raise ValueError("position_scale must be positive")
        if self.multi_particle_damping <= 0.0:
            raise ValueError("multi_particle_damping must be positive")

    def apply_correction(
        self, state: PhysicalState, metric: GeometricMetric, weight: float
    ) -> None:
        if metric.magnitude == 0.0 or np.all(metric.raw_error_vector == 0):
            return

        corrections = self.policy.calculate_corrections(state, metric, weight)

        if len(metric.affected_particle_ids) == 2:
            # 2粒子間の引き寄せ/離反補正（距離制約など）
            p1_id, p2_id = metric.affected_particle_ids
            scale = self.position_scale
            state.particles[p1_id].position -= corrections[p1_id] * scale
            state.particles[p2_id].position += corrections[p2_id] * scale
        else:
            # 複数粒子の同一方向シフト補正（重心・安定性など）
            # multi_particle_damping でステップを小さくし、過補正を防ぐ
            scale = self.position_scale * self.multi_particle_damping
            for pid, corr in corrections.items():
                state.particles[pid].position += corr * scale
