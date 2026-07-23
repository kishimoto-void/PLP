"""
PGRA State definitions
======================
PhysicalState / Particle / Geometry

Core の Particle0 とは独立した、緩和エンジン用の軽量実行時状態。
将来 Adapter で Core と接続する。
"""

from __future__ import annotations

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Any
import numpy as np


class GeometryKind(Enum):
    POINT = auto()
    EDGE = auto()
    TRIANGLE = auto()
    QUAD = auto()
    POLYGON = auto()


@dataclass
class Particle:
    id: str
    position: np.ndarray  # 3D [x, y, z]
    velocity: np.ndarray  # 3D [vx, vy, vz]
    mass: float
    inv_mass: float = field(init=False)

    def __post_init__(self):
        self.position = np.asarray(self.position, dtype=np.float64)
        self.velocity = np.asarray(self.velocity, dtype=np.float64)
        if self.position.shape != (3,) or self.velocity.shape != (3,):
            raise ValueError("position and velocity must be shape (3,)")
        self.inv_mass = 1.0 / self.mass if self.mass > 0 else 0.0


@dataclass
class Geometry:
    """支持多角形などの幾何形状"""
    id: str
    kind: GeometryKind
    particle_ids: List[str]


@dataclass
class PhysicalState:
    particles: Dict[str, Particle] = field(default_factory=dict)
    geometries: Dict[str, Geometry] = field(default_factory=dict)
