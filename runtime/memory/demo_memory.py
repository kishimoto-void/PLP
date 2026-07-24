#!/usr/bin/env python3
"""Minimal demo: consume → episode → difference → velocity → replay"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from runtime.memory.sink import MemorySink


@dataclass
class MockHeader:
    capsule_id: str
    clock: int = 0
    sequence: int = 0
    parent_id: str | None = None


@dataclass
class MockObs:
    name: str
    values: Dict[str, float] = field(default_factory=dict)


@dataclass
class MockCapsule:
    header: MockHeader
    observations: List[MockObs] = field(default_factory=list)


def main() -> None:
    print("=" * 60)
    print("PLP Capsule Memory — MemorySink demo")
    print("=" * 60)

    sink = MemorySink()

    c0 = MockCapsule(
        header=MockHeader("cap-0", clock=0, sequence=0),
        observations=[
            MockObs("geometry.radius", {"mean_radius": 1.5, "n_particles": 2.0}),
            MockObs("energy.kinetic", {"kinetic_energy": 0.0}),
        ],
    )
    c1 = MockCapsule(
        header=MockHeader("cap-1", clock=1, sequence=1, parent_id="cap-0"),
        observations=[
            MockObs("geometry.radius", {"mean_radius": 1.2, "n_particles": 2.0}),
            MockObs("energy.kinetic", {"kinetic_energy": 0.01}),
        ],
    )
    c2 = MockCapsule(
        header=MockHeader("cap-2", clock=2, sequence=2, parent_id="cap-1"),
        observations=[
            MockObs("geometry.radius", {"mean_radius": 1.05, "n_particles": 2.0}),
            MockObs("energy.kinetic", {"kinetic_energy": 0.005}),
        ],
    )

    sink.consume(c0)
    sink.consume(c1)
    sink.consume(c2)
    ep = sink.close_episode(tags=["demo", "relaxation"])

    print(f"\nEpisode: {ep.episode_id}")
    print(f"  capsules: {ep.capsule_ids}")
    print(f"  tags: {ep.tags}")

    diffs = sink.differences(ep.episode_id)
    print(f"\nDifferences ({len(diffs)}):")
    for d in diffs:
        print(f"  {d.base_capsule_id} → {d.target_capsule_id}")
        print(f"    summary_norm={d.summary_norm:.6f}  clock_delta={d.clock_delta}")
        for od in d.observation_differences:
            if od.changed:
                print(f"    - {od.name}: norm={od.norm:.6f} delta={dict(od.delta)}")

    vels = sink.velocities(ep.episode_id)
    print(f"\nVelocities ({len(vels)}):")
    for v in vels:
        print(f"  velocity={v.velocity:.6f}  ({v.base_diff_summary:.6f} → {v.target_diff_summary:.6f})")

    replayed = sink.replay.list_episode(ep.episode_id)
    print(f"\nReplay: {len(replayed)} capsules restored")
    for c in replayed:
        print(f"  id={c.header.capsule_id} clock={c.header.clock}")

    print("\nStats:", sink.stats())
    print("\nOK — MemorySink path works.")
    print("=" * 60)


if __name__ == "__main__":
    main()
