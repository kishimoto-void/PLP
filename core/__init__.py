"""
PLP Core
========
世界の定義層（記述と不変条件のみ）。

- Particle0  : 存在
- Geometry   : 空間
- Constraint : 制約
- Clock      : 時間

計算・緩和・意味付けは持たない。
"""

from .particle0 import (
    Particle0,
    MutableParticle0,
    FrozenParticle0,
    ParticleID,
    ParticleLike,
    create_particles,
    PARTICLE0_SCHEMA,
    PLP_CORE_VERSION,
)
from .geometry import (
    Geometry,
    GEOMETRY_SCHEMA,
    GEOMETRY_VERSION,
)
from .constraint import (
    Constraint,
    ConstraintID,
    ConstraintKind,
    ConstraintState,
    CONSTRAINT_SCHEMA,
    CONSTRAINT_VERSION,
    boundary_box,
    distance_constraint,
    scalar_limit,
    joint,
)
from .clock import (
    Clock,
    ClockID,
    CLOCK_SCHEMA,
    CLOCK_VERSION,
)

__all__ = [
    # particle0
    "Particle0",
    "MutableParticle0",
    "FrozenParticle0",
    "ParticleID",
    "ParticleLike",
    "create_particles",
    "PARTICLE0_SCHEMA",
    "PLP_CORE_VERSION",
    # geometry
    "Geometry",
    "GEOMETRY_SCHEMA",
    "GEOMETRY_VERSION",
    # constraint
    "Constraint",
    "ConstraintID",
    "ConstraintKind",
    "ConstraintState",
    "CONSTRAINT_SCHEMA",
    "CONSTRAINT_VERSION",
    "boundary_box",
    "distance_constraint",
    "scalar_limit",
    "joint",
    # clock
    "Clock",
    "ClockID",
    "CLOCK_SCHEMA",
    "CLOCK_VERSION",
]
