"""
PLP Geometric Relaxation Architecture (PGRA) v1.0
================================================

PLP の物理層：時間発展後にシミュレーション時間を進めず、
幾何学的基準（Reference）との差異を閉ループで緩和する。

Axiom P1:
  物理状態は時間発展した後、シミュレーション時間を進めることなく
  幾何学的基準状態への差異を緩和する。

主要公開:
  - PGRAPhysicsEngine
  - PhysicalState / Particle / Geometry
  - Reference 系 (DistanceReference, StabilityReference)
  - ConvergenceEngine / ConvergenceMetric
"""

from .state import Particle, Geometry, GeometryKind, PhysicalState
from .reference import GeometricMetric, Reference, DistanceReference, StabilityReference
from .policy import CorrectionPolicy, MassWeightedPolicy
from .strategy import RelaxationStrategy
from .convergence import ConvergenceMetric, ConvergenceEngine
from .integrator import TimeIntegrator, EulerIntegrator
from .engine import PGRAPhysicsEngine

__all__ = [
    "Particle",
    "Geometry",
    "GeometryKind",
    "PhysicalState",
    "GeometricMetric",
    "Reference",
    "DistanceReference",
    "StabilityReference",
    "CorrectionPolicy",
    "MassWeightedPolicy",
    "RelaxationStrategy",
    "ConvergenceMetric",
    "ConvergenceEngine",
    "TimeIntegrator",
    "EulerIntegrator",
    "PGRAPhysicsEngine",
]

__version__ = "1.0.0"
