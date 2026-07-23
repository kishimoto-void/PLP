"""
PGRA Core Engine
================
PLP Geometric Relaxation Architecture (PGRA) v1.0 Core Engine

Axiom P1:
  物理状態は時間発展した後、シミュレーション時間を進めることなく
  幾何学的基準状態への差異を緩和する。

v1.1:
- RelaxationStrategy のスケールパラメータを外部から設定可能に
"""

from __future__ import annotations

from typing import Dict, List, Optional
import numpy as np

from .state import PhysicalState, Particle, Geometry, GeometryKind
from .reference import Reference
from .convergence import ConvergenceEngine, ConvergenceMetric
from .integrator import TimeIntegrator, EulerIntegrator
from .strategy import RelaxationStrategy
from .policy import CorrectionPolicy


class PGRAPhysicsEngine:
    """
    PLP Geometric Relaxation Architecture (PGRA) v1.0 Core Engine
    """

    def __init__(
        self,
        integrator: TimeIntegrator | None = None,
        convergence_engine: ConvergenceEngine | None = None,
        position_scale: float = 1.0,
        multi_particle_damping: float = 0.15,
        policy: CorrectionPolicy | None = None,
    ):
        self.state = PhysicalState()
        self.references: Dict[str, Reference] = {}
        self.integrator = integrator or EulerIntegrator()

        # 戦略をここで組み立て、スケールを明示的に制御可能にする
        strategy = RelaxationStrategy(
            policy=policy,
            position_scale=position_scale,
            multi_particle_damping=multi_particle_damping,
        )
        self.convergence_engine = convergence_engine or ConvergenceEngine(strategy=strategy)

        self.current_time: float = 0.0
        self.position_scale = position_scale
        self.multi_particle_damping = multi_particle_damping

    def add_particle(
        self, particle_id: str, position: List[float], mass: float = 1.0
    ) -> None:
        self.state.particles[particle_id] = Particle(
            id=particle_id,
            position=np.array(position, dtype=np.float64),
            velocity=np.zeros(3, dtype=np.float64),
            mass=mass,
        )

    def add_geometry(
        self,
        geom_id: str,
        kind: GeometryKind,
        particle_ids: List[str],
    ) -> None:
        self.state.geometries[geom_id] = Geometry(
            id=geom_id, kind=kind, particle_ids=list(particle_ids)
        )

    def add_reference(self, reference: Reference) -> None:
        self.references[reference.id] = reference

    def geometric_relaxation(
        self, epsilon: float = 1e-4, max_iterations: int = 10
    ) -> List[ConvergenceMetric]:
        """時刻 t を変えずに (Static Relaxation Phase)、閉ループで Metric と Convergence を処理"""
        return self.convergence_engine.relax_closed_loop(
            list(self.references.values()),
            self.state,
            epsilon=epsilon,
            max_iterations=max_iterations,
        )

    def step(
        self, dt: float, epsilon: float = 1e-4, max_iterations: int = 10
    ) -> PhysicalState:
        """
        [Step 1] Time Integration (t -> t + dt)
        [Step 2] Static Geometric Relaxation (At t + dt, Closed-loop Convergence)
        """
        # 1. 時間発展
        self.integrator.advance_time(self.state, dt)
        self.current_time += dt

        # 2. 時間固定で幾何学差異を収束
        self.geometric_relaxation(epsilon=epsilon, max_iterations=max_iterations)
        return self.state
