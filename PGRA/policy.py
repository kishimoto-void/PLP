"""
PGRA Correction Policy
======================
状態を書き換える補正ベクトルの配分ポリシー。
"""

from __future__ import annotations

from typing import Dict, Protocol
import numpy as np

from .state import PhysicalState
from .reference import GeometricMetric


class CorrectionPolicy(Protocol):
    def calculate_corrections(
        self, state: PhysicalState, metric: GeometricMetric, weight: float
    ) -> Dict[str, np.ndarray]: ...


class MassWeightedPolicy:
    """逆質量(inv_mass)比率に基づき配分する標準ポリシー"""

    def calculate_corrections(
        self, state: PhysicalState, metric: GeometricMetric, weight: float
    ) -> Dict[str, np.ndarray]:
        particle_ids = metric.affected_particle_ids
        inv_mass_sum = sum(state.particles[pid].inv_mass for pid in particle_ids)
        if inv_mass_sum == 0:
            return {pid: np.zeros(3, dtype=np.float64) for pid in particle_ids}

        scaled_vector = metric.raw_error_vector * weight
        return {
            pid: scaled_vector * (state.particles[pid].inv_mass / inv_mass_sum)
            for pid in particle_ids
        }
