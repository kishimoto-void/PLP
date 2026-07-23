"""
PGRA Convergence Engine & Difference Velocity
=============================================
「誤差が減っているか（Difference Velocity）」を観測・評価し、
閉ループ反復（while metric > epsilon）を制御する幾何収束エンジン。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict

from .state import PhysicalState
from .reference import Reference, GeometricMetric
from .strategy import RelaxationStrategy


@dataclass
class ConvergenceMetric:
    reference_id: str
    current_magnitude: float
    difference_velocity: float  # Δ(n+1) - Δ(n) : 負の値であれば正しく減少・収束している


class ConvergenceEngine:
    """
    観測 -> 差異評価 -> 補正 -> 減少速度評価 (閉ループ幾何緩和)
    """

    def __init__(self, strategy: RelaxationStrategy | None = None):
        self.strategy = strategy or RelaxationStrategy()
        self.history: Dict[str, float] = {}  # 過去ステップの magnitude 履歴

    def relax_closed_loop(
        self,
        references: List[Reference],
        state: PhysicalState,
        epsilon: float = 1e-4,
        max_iterations: int = 10,
    ) -> List[ConvergenceMetric]:

        # 優先度順にソート (100: Stability -> 50: Distance etc.)
        sorted_refs = sorted(references, key=lambda r: r.priority, reverse=True)
        convergence_results: List[ConvergenceMetric] = []

        for ref in sorted_refs:
            prev_mag = self.history.get(ref.id, None)

            for iteration in range(max_iterations):
                # 1. 観測 & 評価 (Reference は純粋関数的に Metric を出力)
                metric = ref.evaluate_metric(state)

                if metric.magnitude <= epsilon:
                    break

                # 2. 緩和実行 (RelaxationStrategy が State を補正)
                self.strategy.apply_correction(state, metric, ref.weight)

            # 3. 最終評価と Difference Velocity (誤差の減少速度) の測定
            final_metric = ref.evaluate_metric(state)
            diff_velocity = (
                (final_metric.magnitude - prev_mag) if prev_mag is not None else 0.0
            )
            self.history[ref.id] = final_metric.magnitude

            convergence_results.append(
                ConvergenceMetric(
                    reference_id=ref.id,
                    current_magnitude=final_metric.magnitude,
                    difference_velocity=diff_velocity,
                )
            )

        return convergence_results
