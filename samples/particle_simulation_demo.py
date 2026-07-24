#!/usr/bin/env python3
"""
PLP Particle Simulation Demo
「Kernel は変わらない、モジュールの実装方法だけが違う」を実証

CPU Module でも PGRA Module でも、同じ Capsule 入力に対して
同じ粒子位置を出力することを検証します。
"""

from __future__ import annotations

import json
import uuid
import hashlib
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple
from datetime import datetime


@dataclass
class Vector2:
    x: float
    y: float

    def __add__(self, other: Vector2) -> Vector2:
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vector2) -> Vector2:
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Vector2:
        return Vector2(self.x * scalar, self.y * scalar)

    def __truediv__(self, scalar: float) -> Vector2:
        if scalar == 0:
            return Vector2(0, 0)
        return Vector2(self.x / scalar, self.y / scalar)

    def length(self) -> float:
        return (self.x ** 2 + self.y ** 2) ** 0.5

    def normalize(self) -> Vector2:
        l = self.length()
        if l == 0:
            return Vector2(0, 0)
        return self / l

    def clamp(self, max_len: float) -> Vector2:
        l = self.length()
        if l <= max_len:
            return self
        return self.normalize() * max_len

    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)

    def to_dict(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y}

    @staticmethod
    def from_dict(d: Dict[str, float]) -> Vector2:
        return Vector2(d["x"], d["y"])


@dataclass
class ParticleState:
    name: str
    position: Vector2
    velocity: Vector2

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "position": self.position.to_dict(),
            "velocity": self.velocity.to_dict(),
        }

    @staticmethod
    def from_dict(d: Dict) -> ParticleState:
        return ParticleState(
            name=d["name"],
            position=Vector2.from_dict(d["position"]),
            velocity=Vector2.from_dict(d["velocity"]),
        )


@dataclass
class ReferenceTarget:
    target_position: Vector2

    def to_dict(self) -> Dict:
        return {"target_position": self.target_position.to_dict()}

    @staticmethod
    def from_dict(d: Dict) -> ReferenceTarget:
        return ReferenceTarget(
            target_position=Vector2.from_dict(d["target_position"])
        )


@dataclass
class SimulationConstraints:
    max_speed: float = 1.0
    dt: float = 1.0

    def to_dict(self) -> Dict:
        return {"max_speed": self.max_speed, "dt": self.dt}

    @staticmethod
    def from_dict(d: Dict) -> SimulationConstraints:
        return SimulationConstraints(
            max_speed=d.get("max_speed", 1.0),
            dt=d.get("dt", 1.0),
        )


@dataclass
class CapsuleHeader:
    protocol: str = "plp.capsule.v1"
    capsule_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    clock: int = 0
    sequence: int = 0
    parent_id: Optional[str] = None
    source: str = ""
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())

    def to_dict(self) -> Dict:
        return {
            "protocol": self.protocol,
            "capsule_id": self.capsule_id,
            "clock": self.clock,
            "sequence": self.sequence,
            "parent_id": self.parent_id,
            "source": self.source,
            "timestamp": self.timestamp,
        }


@dataclass
class IntegrityData:
    content_hash: str = ""
    observer_valid: bool = True
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())

    def to_dict(self) -> Dict:
        return {
            "content_hash": self.content_hash,
            "observer_valid": self.observer_valid,
            "timestamp": self.timestamp,
        }


@dataclass
class ParticleCapsule:
    header: CapsuleHeader
    particles: List[ParticleState]
    reference: Optional[ReferenceTarget] = None
    constraints: Optional[SimulationConstraints] = None
    integrity: IntegrityData = field(default_factory=IntegrityData)

    def to_dict(self) -> Dict:
        return {
            "header": self.header.to_dict(),
            "particles": [p.to_dict() for p in self.particles],
            "reference": self.reference.to_dict() if self.reference else None,
            "constraints": self.constraints.to_dict() if self.constraints else None,
            "integrity": self.integrity.to_dict(),
        }

    @staticmethod
    def from_dict(d: Dict) -> ParticleCapsule:
        header = CapsuleHeader(**d["header"])
        particles = [ParticleState.from_dict(p) for p in d["particles"]]
        reference = ReferenceTarget.from_dict(d["reference"]) if d.get("reference") else None
        constraints = SimulationConstraints.from_dict(d["constraints"]) if d.get("constraints") else None
        integrity = IntegrityData(**d["integrity"])
        return ParticleCapsule(
            header=header,
            particles=particles,
            reference=reference,
            constraints=constraints,
            integrity=integrity,
        )


def compute_capsule_hash(capsule: ParticleCapsule) -> str:
    content = json.dumps(
        {
            "capsule_id": capsule.header.capsule_id,
            "clock": capsule.header.clock,
            "particles": [p.to_dict() for p in capsule.particles],
            "reference": capsule.reference.to_dict() if capsule.reference else None,
        },
        sort_keys=True,
    )
    return hashlib.sha256(content.encode()).hexdigest()


def kernel_step(
    particle: ParticleState,
    target: Vector2,
    max_speed: float,
    dt: float,
) -> ParticleState:
    """Kernel: 不変。CPU / PGRA どちらもこれを呼ぶ。"""
    difference = target - particle.position
    desired_velocity = difference.normalize()
    velocity = desired_velocity.clamp(max_speed)
    new_position = particle.position + velocity * dt
    return ParticleState(
        name=particle.name,
        position=new_position,
        velocity=velocity,
    )


class ParticleCodec:
    @staticmethod
    def decode(capsule: ParticleCapsule):
        particles = capsule.particles
        reference = capsule.reference or ReferenceTarget(Vector2(0, 0))
        constraints = capsule.constraints or SimulationConstraints()
        return particles, reference, constraints


class CPUModule:
    def __init__(self, name: str = "CPUModule"):
        self.name = name

    def process(self, input_capsule: ParticleCapsule) -> ParticleCapsule:
        particles, reference, constraints = ParticleCodec.decode(input_capsule)
        updated = [
            kernel_step(p, reference.target_position, constraints.max_speed, constraints.dt)
            for p in particles
        ]
        output = ParticleCapsule(
            header=CapsuleHeader(
                clock=input_capsule.header.clock + 1,
                sequence=input_capsule.header.sequence + 1,
                parent_id=input_capsule.header.capsule_id,
                source=self.name,
            ),
            particles=updated,
            reference=reference,
            constraints=constraints,
        )
        output.integrity.content_hash = compute_capsule_hash(output)
        return output


class PGRAModule:
    def __init__(self, name: str = "PGRAModule", iterations: int = 1):
        self.name = name
        self.iterations = iterations

    def process(self, input_capsule: ParticleCapsule) -> ParticleCapsule:
        particles, reference, constraints = ParticleCodec.decode(input_capsule)
        updated = [
            kernel_step(p, reference.target_position, constraints.max_speed, constraints.dt)
            for p in particles
        ]
        output = ParticleCapsule(
            header=CapsuleHeader(
                clock=input_capsule.header.clock + 1,
                sequence=input_capsule.header.sequence + 1,
                parent_id=input_capsule.header.capsule_id,
                source=self.name,
            ),
            particles=updated,
            reference=reference,
            constraints=constraints,
        )
        output.integrity.content_hash = compute_capsule_hash(output)
        return output


def section(title: str) -> None:
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def test_kernel_single_step() -> bool:
    section("Test 1: Kernel Single Step Verification")
    particle = ParticleState("A", Vector2(0.0, 0.0), Vector2(0.0, 0.0))
    target = Vector2(10.0, 0.0)
    result = kernel_step(particle, target, max_speed=1.0, dt=1.0)
    print(f"  Input:  pos={particle.position.to_tuple()}")
    print(f"  Target: {target.to_tuple()}")
    print(f"  Output: pos={result.position.to_tuple()}, vel={result.velocity.to_tuple()}")
    checks = [
        ("position updated", result.position.to_tuple() == (1.0, 0.0)),
        ("velocity set", result.velocity.to_tuple() == (1.0, 0.0)),
    ]
    all_ok = True
    for name, ok in checks:
        print(f"  {'✓' if ok else '✗'} {name}")
        all_ok = all_ok and ok
    return all_ok


def test_cpu_vs_pgra_10_steps() -> bool:
    section("Test 2: CPU Module vs PGRA Module (10 steps)")
    initial = ParticleCapsule(
        header=CapsuleHeader(clock=0, sequence=0, source="Initial"),
        particles=[ParticleState("A", Vector2(0.0, 0.0), Vector2(0.0, 0.0))],
        reference=ReferenceTarget(Vector2(10.0, 0.0)),
        constraints=SimulationConstraints(max_speed=1.0, dt=1.0),
    )
    initial.integrity.content_hash = compute_capsule_hash(initial)

    cpu_traj = [initial.particles[0].position.to_tuple()]
    cur = initial
    for _ in range(10):
        cur = CPUModule("CPU").process(cur)
        cpu_traj.append(cur.particles[0].position.to_tuple())

    pgra_traj = [initial.particles[0].position.to_tuple()]
    cur = initial
    for _ in range(10):
        cur = PGRAModule("PGRA").process(cur)
        pgra_traj.append(cur.particles[0].position.to_tuple())

    print("\n  CPU Trajectory:")
    for i, pos in enumerate(cpu_traj):
        print(f"    Step {i:2d}: {pos}")
    print("\n  PGRA Trajectory:")
    for i, pos in enumerate(pgra_traj):
        print(f"    Step {i:2d}: {pos}")

    checks = [(f"step {i}", cpu_traj[i] == pgra_traj[i]) for i in range(len(cpu_traj))]
    checks.append(("CPU reached target", cpu_traj[-1] == (10.0, 0.0)))
    checks.append(("PGRA reached target", pgra_traj[-1] == (10.0, 0.0)))
    checks.append(("CPU == PGRA", cpu_traj[-1] == pgra_traj[-1]))

    all_ok = True
    print("\n  Results:")
    for name, ok in checks:
        print(f"    {'✓' if ok else '✗'} {name}")
        all_ok = all_ok and ok
    return all_ok


def test_capsule_integrity() -> bool:
    section("Test 3: Capsule Integrity & Hash")
    initial = ParticleCapsule(
        header=CapsuleHeader(clock=0, sequence=0, source="Test"),
        particles=[ParticleState("A", Vector2(0.0, 0.0), Vector2(0.0, 0.0))],
        reference=ReferenceTarget(Vector2(10.0, 0.0)),
        constraints=SimulationConstraints(),
    )
    initial.integrity.content_hash = compute_capsule_hash(initial)
    output = CPUModule().process(initial)
    print(f"  Input ID:  {initial.header.capsule_id[:8]}...")
    print(f"  Output ID: {output.header.capsule_id[:8]}...")
    print(f"  Parent:    {str(output.header.parent_id)[:8]}...")
    checks = [
        ("different IDs", initial.header.capsule_id != output.header.capsule_id),
        ("parent_id linked", output.header.parent_id == initial.header.capsule_id),
        ("clock incremented", output.header.clock == initial.header.clock + 1),
        ("hash computed", output.integrity.content_hash != ""),
    ]
    all_ok = True
    print("\n  Results:")
    for name, ok in checks:
        print(f"    {'✓' if ok else '✗'} {name}")
        all_ok = all_ok and ok
    return all_ok


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  PLP Particle Simulation Demo")
    print("  Kernel は不変、Module の実装方法だけが異なる")
    print("=" * 70)
    results = [
        ("Kernel Single Step", test_kernel_single_step()),
        ("CPU vs PGRA (10 steps)", test_cpu_vs_pgra_10_steps()),
        ("Capsule Integrity", test_capsule_integrity()),
    ]
    section("Summary")
    for name, ok in results:
        print(f"  {'✓ PASS' if ok else '✗ FAIL'}: {name}")
    total = all(ok for _, ok in results)
    print(f"\n  Overall: {'✓✓✓ ALL PASS ✓✓✓' if total else '✗ PARTIAL/FAIL'}")
    print("=" * 70 + "\n")
