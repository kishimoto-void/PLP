"""
PGRA Time Integrator
====================
時間発展（t → t+dt）の最小実装。
現時点は Euler のみ。将来 RK4 等を追加可能。
"""

from __future__ import annotations

from typing import Protocol
import numpy as np

from .state import PhysicalState


class TimeIntegrator(Protocol):
    def advance_time(self, state: PhysicalState, dt: float) -> None: ...


class EulerIntegrator:
    """単純 Euler 積分（位置 = 位置 + 速度 * dt）"""

    def advance_time(self, state: PhysicalState, dt: float) -> None:
        for p in state.particles.values():
            p.position = p.position + p.velocity * dt
