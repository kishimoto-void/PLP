"""
PLP Capsule v1.2
================
通信規格として固めた版。

主な改善:
- Schema に plp. 名前空間を推奨
- Capability を公式 Enum + 拡張可能に
- CapabilityRegistry を追加
- content_hash の対象を仕様として明確化
- Observer に priority を付けられるように
- from_dict / 空ケースの堅牢性向上

設計目標 (CAPSULE.md 準拠):
1. Interpretation Stability
2. State Transition Reduction
3. Semantic Delay
4. Unified Physical Representation
5. Common Interface
6. Temporal Consistency
7. Observer Isolation
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Sequence
from uuid import uuid4
import hashlib
import json
import time


# ==========================================================
# Capability（公式 + 拡張）
# ==========================================================

class Capability(str, Enum):
    """公式 Capability。外部拡張は文字列でも可。"""
    GEOMETRY = "geometry"
    ENERGY = "energy"
    PHASE = "phase"
    CONSTRAINT = "constraint"
    TOPOLOGY = "topology"
    VECTOR = "vector"
    CLOCK = "clock"
    CUSTOM = "custom"


# ==========================================================
# Capability Registry
# ==========================================================

class CapabilityRegistry:
    """
    capability → 推奨 schema の対応表。
    Observer が schema を省略したときに使える。
    """
    _registry: Dict[str, str] = {
        Capability.GEOMETRY.value: "plp.geometry.v1",
        Capability.ENERGY.value: "plp.energy.v1",
        Capability.PHASE.value: "plp.phase.v1",
        Capability.CONSTRAINT.value: "plp.constraint.v1",
        Capability.TOPOLOGY.value: "plp.topology.v1",
        Capability.VECTOR.value: "plp.vector.v1",
        Capability.CLOCK.value: "plp.clock.v1",
    }

    @classmethod
    def register(cls, capability: str, schema: str) -> None:
        cls._registry[capability] = schema

    @classmethod
    def get_schema(cls, capability: str) -> Optional[str]:
        return cls._registry.get(capability)

    @classmethod
    def list_all(cls) -> Dict[str, str]:
        return dict(cls._registry)


# ==========================================================
# Flags
# ==========================================================

@dataclass(frozen=True)
class CapsuleFlags:
    compressed: bool = False
    encrypted: bool = False
    partial: bool = False
    realtime: bool = True


# ==========================================================
# Header
# ==========================================================

@dataclass(frozen=True)
class CapsuleHeader:
    protocol: str = "PLP/1.0"
    capsule_schema: str = "capsule.v1"
    version: str = "1.2"

    capsule_id: str = field(default_factory=lambda: str(uuid4()))
    parent_id: Optional[str] = None

    clock: int = 0
    sequence: int = 0
    timestamp: float = 0.0
    source: str = "ParticleKernel"

    flags: CapsuleFlags = field(default_factory=CapsuleFlags)


# ==========================================================
# Input
# ==========================================================

@dataclass(frozen=True)
class InputReference:
    """本番向け。生データを持たない。"""
    input_id: str
    input_type: str = "opaque"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class InputCapsule:
    """開発用に raw_input を残しつつ、本番は reference を推奨。"""
    raw_input: Any = None
    input_type: str = "opaque"
    metadata: Dict[str, Any] = field(default_factory=dict)
    reference: Optional[InputReference] = None


# ==========================================================
# Observation
# ==========================================================

@dataclass(frozen=True)
class ObservationBlock:
    name: str
    schema: str
    capability: str = Capability.CUSTOM.value
    values: Dict[str, float] = field(default_factory=dict)
    clock: Optional[int] = None

    def __post_init__(self):
        # schema が空なら Registry から補完を試みる
        if not self.schema and self.capability:
            suggested = CapabilityRegistry.get_schema(self.capability)
            if suggested:
                object.__setattr__(self, "schema", suggested)


# ==========================================================
# Delta / Integrity
# ==========================================================

@dataclass(frozen=True)
class DeltaBlock:
    changes: Dict[str, Dict[str, float]] = field(default_factory=dict)


@dataclass(frozen=True)
class CapsuleIntegrity:
    content_hash: Optional[str] = None
    valid: bool = True
    error: Optional[str] = None


# ==========================================================
# Capsule
# ==========================================================

@dataclass(frozen=True)
class PLPCapsule:
    header: CapsuleHeader
    input: InputCapsule
    observations: List[ObservationBlock]
    delta: DeltaBlock
    integrity: CapsuleIntegrity

    def to_dict(self) -> Dict[str, Any]:
        return {
            "header": {
                **{k: v for k, v in asdict(self.header).items() if k != "flags"},
                "flags": asdict(self.header.flags),
            },
            "input": {
                "raw_input": self.input.raw_input,
                "input_type": self.input.input_type,
                "metadata": dict(self.input.metadata),
                "reference": asdict(self.input.reference) if self.input.reference else None,
            },
            "observations": [
                {
                    "name": o.name,
                    "schema": o.schema,
                    "capability": o.capability,
                    "values": dict(o.values),
                    "clock": o.clock,
                }
                for o in self.observations
            ],
            "delta": {"changes": self.delta.changes},
            "integrity": asdict(self.integrity),
        }


# ==========================================================
# Interfaces
# ==========================================================

class IObserver(Protocol):
    def observe(self, world: Any) -> ObservationBlock: ...


class ICapsuleTransport(Protocol):
    def send(self, capsule: PLPCapsule) -> None: ...
    def receive(self) -> Optional[PLPCapsule]: ...


# ==========================================================
# Builder
# ==========================================================

class CapsuleBuilder:
    def __init__(self) -> None:
        # (priority, observer) のリスト。小さい priority が先。
        self._observers: List[tuple[int, IObserver]] = []

    def register(self, observer: IObserver, priority: int = 100) -> "CapsuleBuilder":
        self._observers.append((priority, observer))
        self._observers.sort(key=lambda x: x[0])
        return self

    def clear(self) -> "CapsuleBuilder":
        self._observers.clear()
        return self

    def _compute_delta(
        self,
        current: Sequence[ObservationBlock],
        previous: Optional[PLPCapsule],
    ) -> DeltaBlock:
        if previous is None:
            return DeltaBlock()

        prev_map = {f"{o.name}.{o.schema}": o for o in previous.observations}
        changes: Dict[str, Dict[str, float]] = {}

        for obs in current:
            key = f"{obs.name}.{obs.schema}"
            prev = prev_map.get(key)
            if prev is None:
                continue

            diff: Dict[str, float] = {}
            for k, v in obs.values.items():
                if k in prev.values:
                    d = float(v) - float(prev.values[k])
                    if abs(d) > 1e-12:
                        diff[k] = d
            if diff:
                changes[key] = diff

        return DeltaBlock(changes=changes)

    def _compute_content_hash(
        self,
        header: CapsuleHeader,
        observations: Sequence[ObservationBlock],
        delta: DeltaBlock,
    ) -> str:
        """
        仕様:
        - capsule_id / clock / sequence を含める（時間一貫性の検証用）
        - observations と delta を含める
        - flags や timestamp は含めない（再計算で変わりうるため）
        """
        payload = {
            "capsule_id": header.capsule_id,
            "clock": header.clock,
            "sequence": header.sequence,
            "observations": [
                {
                    "name": o.name,
                    "schema": o.schema,
                    "capability": o.capability,
                    "values": o.values,
                }
                for o in observations
            ],
            "delta": delta.changes,
        }
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:16]

    def build(
        self,
        world: Any,
        input_packet: InputCapsule,
        clock: int,
        sequence: int,
        previous: Optional[PLPCapsule] = None,
        source: str = "ParticleKernel",
        parent_id: Optional[str] = None,
        flags: Optional[CapsuleFlags] = None,
    ) -> PLPCapsule:
        observations: List[ObservationBlock] = []
        errors: List[str] = []

        for _, observer in self._observers:
            try:
                block = observer.observe(world)
                if not isinstance(block, ObservationBlock):
                    errors.append(f"non-ObservationBlock from {type(observer).__name__}")
                    continue
                observations.append(block)
            except Exception as e:
                errors.append(f"{type(observer).__name__}: {e}")

        header = CapsuleHeader(
            clock=clock,
            sequence=sequence,
            timestamp=time.time(),
            source=source,
            parent_id=parent_id,
            flags=flags or CapsuleFlags(),
        )

        delta = self._compute_delta(observations, previous)
        content_hash = self._compute_content_hash(header, observations, delta)

        integrity = CapsuleIntegrity(
            content_hash=content_hash,
            valid=len(errors) == 0,
            error="; ".join(errors) if errors else None,
        )

        return PLPCapsule(
            header=header,
            input=input_packet,
            observations=observations,
            delta=delta,
            integrity=integrity,
        )


# ==========================================================
# Serializer
# ==========================================================

class CapsuleSerializer:
    @staticmethod
    def to_dict(capsule: PLPCapsule) -> Dict[str, Any]:
        return capsule.to_dict()

    @staticmethod
    def to_json(capsule: PLPCapsule, indent: Optional[int] = 2) -> str:
        return json.dumps(capsule.to_dict(), ensure_ascii=False, indent=indent)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> PLPCapsule:
        header_data = dict(data.get("header", {}))
        flags_data = header_data.pop("flags", {})
        header = CapsuleHeader(
            **{k: v for k, v in header_data.items() if k in CapsuleHeader.__dataclass_fields__},
            flags=CapsuleFlags(**{k: v for k, v in flags_data.items() if k in CapsuleFlags.__dataclass_fields__}),
        )

        ref_data = data.get("input", {}).get("reference")
        reference = InputReference(**ref_data) if isinstance(ref_data, dict) else None

        inp = InputCapsule(
            raw_input=data.get("input", {}).get("raw_input"),
            input_type=data.get("input", {}).get("input_type", "opaque"),
            metadata=data.get("input", {}).get("metadata", {}),
            reference=reference,
        )

        observations = []
        for o in data.get("observations", []):
            observations.append(
                ObservationBlock(
                    name=o.get("name", ""),
                    schema=o.get("schema", ""),
                    capability=o.get("capability", Capability.CUSTOM.value),
                    values=o.get("values", {}),
                    clock=o.get("clock"),
                )
            )

        delta = DeltaBlock(changes=data.get("delta", {}).get("changes", {}))
        integrity_data = data.get("integrity", {})
        integrity = CapsuleIntegrity(
            content_hash=integrity_data.get("content_hash"),
            valid=integrity_data.get("valid", True),
            error=integrity_data.get("error"),
        )

        return PLPCapsule(
            header=header,
            input=inp,
            observations=observations,
            delta=delta,
            integrity=integrity,
        )
