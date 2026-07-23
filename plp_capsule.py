"""
PLP Capsule v1.3
================
通信規格として固めた版。

v1.3 改善点:
- from_dict の堅牢性向上（欠落フィールドに対する安全なデフォルト）
- content_hash を 32 文字に延長（衝突耐性向上）
- Builder のエラーを構造化（Observer 名 + メッセージ）
- CapsuleIntegrity に hash_valid / observer_valid を意識した設計
- ObservationBlock の schema 補完ロジックを明確化
- verify_content_hash ヘルパーを追加

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
from typing import Any, Dict, List, Optional, Protocol, Sequence, Tuple
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
    version: str = "1.3"

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
    valid: bool = True                    # 全体として有効か（後方互換）
    observer_valid: bool = True           # Observer 実行が成功したか
    hash_valid: Optional[bool] = None     # ハッシュ検証結果（受信側で設定）
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
# Hash helper
# ==========================================================

def compute_content_hash(
    capsule_id: str,
    clock: int,
    sequence: int,
    observations: Sequence[ObservationBlock],
    delta: DeltaBlock,
) -> str:
    """
    仕様:
    - capsule_id / clock / sequence を含める（時間一貫性の検証用）
    - observations と delta を含める
    - flags や timestamp は含めない（再計算で変わりうるため）
    - 32 文字（SHA256 先頭）で衝突耐性を確保
    """
    payload = {
        "capsule_id": capsule_id,
        "clock": clock,
        "sequence": sequence,
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
    return hashlib.sha256(raw).hexdigest()[:32]


def verify_content_hash(capsule: PLPCapsule) -> bool:
    """受信側で integrity を検証するためのヘルパー"""
    if capsule.integrity.content_hash is None:
        return False
    expected = compute_content_hash(
        capsule.header.capsule_id,
        capsule.header.clock,
        capsule.header.sequence,
        capsule.observations,
        capsule.delta,
    )
    return expected == capsule.integrity.content_hash


# ==========================================================
# Builder
# ==========================================================

class CapsuleBuilder:
    def __init__(self) -> None:
        # (priority, observer) のリスト。小さい priority が先。
        self._observers: List[Tuple[int, IObserver]] = []

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

        # キーは name + schema。schema 進化時は Delta が途切れる可能性があるが、
        # 意図的に厳密な同一性を要求する設計。
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
            obs_name = type(observer).__name__
            try:
                block = observer.observe(world)
                if not isinstance(block, ObservationBlock):
                    errors.append(f"{obs_name}: returned non-ObservationBlock")
                    continue
                observations.append(block)
            except Exception as e:
                errors.append(f"{obs_name}: {type(e).__name__}: {e}")

        header = CapsuleHeader(
            clock=clock,
            sequence=sequence,
            timestamp=time.time(),
            source=source,
            parent_id=parent_id,
            flags=flags or CapsuleFlags(),
        )

        delta = self._compute_delta(observations, previous)
        content_hash = compute_content_hash(
            header.capsule_id,
            header.clock,
            header.sequence,
            observations,
            delta,
        )

        observer_valid = len(errors) == 0
        integrity = CapsuleIntegrity(
            content_hash=content_hash,
            valid=observer_valid,
            observer_valid=observer_valid,
            hash_valid=None,  # 受信側で設定
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
        """欠落フィールドに対して安全にデフォルトを適用する堅牢な復元"""
        # --- Header ---
        header_data = dict(data.get("header") or {})
        flags_data = header_data.pop("flags", {}) or {}

        # 許可されたフィールドだけを取り出す
        header_fields = CapsuleHeader.__dataclass_fields__
        safe_header = {
            k: v for k, v in header_data.items()
            if k in header_fields and k != "flags"
        }

        flags_fields = CapsuleFlags.__dataclass_fields__
        safe_flags = {
            k: v for k, v in flags_data.items()
            if k in flags_fields
        }

        header = CapsuleHeader(
            **safe_header,
            flags=CapsuleFlags(**safe_flags),
        )

        # --- Input ---
        input_data = data.get("input") or {}
        ref_data = input_data.get("reference")
        reference = None
        if isinstance(ref_data, dict) and "input_id" in ref_data:
            reference = InputReference(
                input_id=str(ref_data["input_id"]),
                input_type=str(ref_data.get("input_type", "opaque")),
                metadata=dict(ref_data.get("metadata") or {}),
            )

        inp = InputCapsule(
            raw_input=input_data.get("raw_input"),
            input_type=str(input_data.get("input_type", "opaque")),
            metadata=dict(input_data.get("metadata") or {}),
            reference=reference,
        )

        # --- Observations ---
        observations: List[ObservationBlock] = []
        for o in data.get("observations") or []:
            if not isinstance(o, dict):
                continue
            observations.append(
                ObservationBlock(
                    name=str(o.get("name", "")),
                    schema=str(o.get("schema", "")),
                    capability=str(o.get("capability", Capability.CUSTOM.value)),
                    values={str(k): float(v) for k, v in (o.get("values") or {}).items()
                            if isinstance(v, (int, float))},
                    clock=o.get("clock"),
                )
            )

        # --- Delta ---
        delta_data = data.get("delta") or {}
        changes = delta_data.get("changes") or {}
        # 値を float に正規化
        safe_changes: Dict[str, Dict[str, float]] = {}
        if isinstance(changes, dict):
            for key, diff in changes.items():
                if isinstance(diff, dict):
                    safe_changes[str(key)] = {
                        str(k): float(v)
                        for k, v in diff.items()
                        if isinstance(v, (int, float))
                    }
        delta = DeltaBlock(changes=safe_changes)

        # --- Integrity ---
        integrity_data = data.get("integrity") or {}
        integrity = CapsuleIntegrity(
            content_hash=integrity_data.get("content_hash"),
            valid=bool(integrity_data.get("valid", True)),
            observer_valid=bool(integrity_data.get("observer_valid", integrity_data.get("valid", True))),
            hash_valid=integrity_data.get("hash_valid"),
            error=integrity_data.get("error"),
        )

        return PLPCapsule(
            header=header,
            input=inp,
            observations=observations,
            delta=delta,
            integrity=integrity,
        )
