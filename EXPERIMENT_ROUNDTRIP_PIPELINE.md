# EXPERIMENT: Capsule Round-trip & Pipeline

**優先度**: 最高  
**日時**: 2026-07-24  
**目的**: Capsule 中心 + Codec 分離アーキテクチャの最小動作確認

---

## 1. 実験の目的

本実験は次の2点を確認する。

1. **Capsule 自体の Round-trip**  
   `build → to_dict → from_dict` で情報が失われないこと

2. **最小 Pipeline**  
   `Input Capsule → PGRAModule → Output Capsule` が構造的に通ること

### 現時点の制約（忠実に記載）

- `PGRACodec.decode()` はまだ簡易実装（Observation からの完全復元は未完了）
- そのため本実験では主に以下を検証する：
  - Capsule の serialize / deserialize 忠実性
  - `PGRAModule.process_state()` による「内部状態 → 緩和 → Capsule」経路
  - 生成された Capsule の基本構造（header / observations / integrity）

---

## 2. 実験環境

```bash
# リポジトリルートで実行することを想定
python -c "import plp_capsule; import codecs; import PGRA; print('import ok')"
```

必要なもの:
- `plp_capsule.py` (v1.3)
- `codecs/` (base + pgra_codec)
- `PGRA/`

---

## 3. 実験コード

以下を `experiments/roundtrip_pipeline.py` として保存して実行する想定。

```python
#!/usr/bin/env python3
"""
EXPERIMENT: Capsule Round-trip & Minimal Pipeline
実験は忠実に実際行って。
"""

from __future__ import annotations

import json
import numpy as np
from pprint import pprint

from plp_capsule import (
    PLPCapsule,
    CapsuleBuilder,
    CapsuleSerializer,
    InputCapsule,
    InputReference,
    ObservationBlock,
    Capability,
    verify_content_hash,
    compute_content_hash,
)
from PGRA.state import PhysicalState, Particle, Geometry, GeometryKind
from PGRA.engine import PGRAPhysicsEngine
from PGRA.reference import DistanceReference
from codecs.pgra_codec import PGRACodec, PGRAModule


def section(title: str) -> None:
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


# ==========================================================
# Experiment 1: Capsule Round-trip (serialize fidelity)
# ==========================================================

def experiment_capsule_roundtrip() -> bool:
    section("Experiment 1: Capsule Round-trip (to_dict ↔ from_dict)")

    # 手動で最小 Capsule を構築
    builder = CapsuleBuilder()

    class DummyObserver:
        def observe(self, world):
            return ObservationBlock(
                name="geometry.radius",
                schema="plp.geometry.v1",
                capability=Capability.GEOMETRY.value,
                values={
                    "mean_radius": 1.234,
                    "std_radius": 0.017,
                    "max_radius": 1.50,
                    "n_particles": 2.0,
                },
            )

    builder.register(DummyObserver(), priority=10)

    original = builder.build(
        world=None,
        input_packet=InputCapsule(
            reference=InputReference(input_id="exp-001", input_type="opaque")
        ),
        clock=42,
        sequence=7,
        source="RoundtripTest",
    )

    # serialize → deserialize
    data = CapsuleSerializer.to_dict(original)
    restored = CapsuleSerializer.from_dict(data)

    # 検証
    checks = []

    checks.append(("protocol", original.header.protocol == restored.header.protocol))
    checks.append(("clock", original.header.clock == restored.header.clock))
    checks.append(("sequence", original.header.sequence == restored.header.sequence))
    checks.append(("capsule_id", original.header.capsule_id == restored.header.capsule_id))
    checks.append(("n_observations", len(original.observations) == len(restored.observations)))

    if original.observations and restored.observations:
        o0 = original.observations[0]
        r0 = restored.observations[0]
        checks.append(("obs.name", o0.name == r0.name))
        checks.append(("obs.schema", o0.schema == r0.schema))
        checks.append(("obs.values", o0.values == r0.values))

    # hash 検証
    hash_ok = verify_content_hash(original)
    checks.append(("verify_content_hash(original)", hash_ok))

    # restored でも同じ hash が計算できるか
    restored_hash = compute_content_hash(
        restored.header.capsule_id,
        restored.header.clock,
        restored.header.sequence,
        restored.observations,
        restored.delta,
    )
    checks.append(("hash equality", original.integrity.content_hash == restored_hash))

    print("\n[Results]")
    all_ok = True
    for name, ok in checks:
        status = "PASS" if ok else "FAIL"
        print(f"  {status}: {name}")
        if not ok:
            all_ok = False

    print(f"\n  → Capsule Round-trip: {'PASS' if all_ok else 'FAIL'}")
    return all_ok


# ==========================================================
# Experiment 2: PGRA process_state → Capsule
# ==========================================================

def experiment_pgra_process_state() -> bool:
    section("Experiment 2: PGRAModule.process_state → Output Capsule")

    # 内部状態を直接用意
    state = PhysicalState()
    state.particles["p1"] = Particle(
        id="p1",
        position=np.array([0.0, 0.0, 0.0]),
        velocity=np.zeros(3),
        mass=1.0,
    )
    state.particles["p2"] = Particle(
        id="p2",
        position=np.array([1.5, 0.0, 0.0]),
        velocity=np.zeros(3),
        mass=1.0,
    )

    engine = PGRAPhysicsEngine()
    engine.state = state
    engine.add_reference(
        DistanceReference("dist01", "p1", "p2", distance=1.0, priority=50)
    )

    module = PGRAModule(engine=engine, epsilon=1e-5, max_iterations=20)

    # 緩和前の距離
    d_before = float(np.linalg.norm(
        state.particles["p1"].position - state.particles["p2"].position
    ))
    print(f"  distance before relaxation: {d_before:.6f}")

    # process_state（内部状態 → 緩和 → Capsule）
    output = module.process_state(state)

    d_after = float(np.linalg.norm(
        engine.state.particles["p1"].position - engine.state.particles["p2"].position
    ))
    print(f"  distance after relaxation : {d_after:.6f}")

    # Capsule の基本構造確認
    checks = []
    checks.append(("has header", output.header is not None))
    checks.append(("has observations", len(output.observations) > 0))
    checks.append(("has integrity.hash", output.integrity.content_hash is not None))
    checks.append(("observer_valid", output.integrity.observer_valid is True))
    checks.append(("distance moved toward target", abs(d_after - 1.0) < abs(d_before - 1.0)))

    # observation 内容の確認
    obs_names = [o.name for o in output.observations]
    print(f"  observations: {obs_names}")

    for o in output.observations:
        print(f"    - {o.name} ({o.schema}): {o.values}")

    print("\n[Results]")
    all_ok = True
    for name, ok in checks:
        status = "PASS" if ok else "FAIL"
        print(f"  {status}: {name}")
        if not ok:
            all_ok = False

    print(f"\n  → PGRA process_state Pipeline: {'PASS' if all_ok else 'FAIL'}")
    return all_ok


# ==========================================================
# Experiment 3: Capsule → (構造のみ) → Capsule の接続確認
# ==========================================================

def experiment_minimal_pipeline() -> bool:
    section("Experiment 3: Minimal Capsule Pipeline (structural)")

    # 1. 初期 Capsule を作る（ダミー入力）
    builder = CapsuleBuilder()

    class InitObserver:
        def observe(self, world):
            return ObservationBlock(
                name="init.marker",
                schema="plp.custom.v1",
                capability=Capability.CUSTOM.value,
                values={"marker": 1.0},
            )

    builder.register(InitObserver())
    input_capsule = builder.build(
        world=None,
        input_packet=InputCapsule(
            reference=InputReference(input_id="pipeline-001")
        ),
        clock=0,
        sequence=0,
        source="PipelineTest",
    )

    print(f"  Input  capsule_id : {input_capsule.header.capsule_id[:8]}...")
    print(f"  Input  clock/seq  : {input_capsule.header.clock}/{input_capsule.header.sequence}")

    # 2. PGRAModule に渡す（現時点では process は engine.state を使う）
    #    実験では process_state 経由で出力を得る
    state = PhysicalState()
    state.particles["a"] = Particle("a", np.array([0.0, 0.0, 0.0]), np.zeros(3), 1.0)
    state.particles["b"] = Particle("b", np.array([2.0, 0.0, 0.0]), np.zeros(3), 1.0)

    engine = PGRAPhysicsEngine()
    engine.state = state
    engine.add_reference(DistanceReference("d", "a", "b", distance=1.0))

    module = PGRAModule(engine=engine)
    output_capsule = module.process_state(state, previous=input_capsule)

    print(f"  Output capsule_id : {output_capsule.header.capsule_id[:8]}...")
    print(f"  Output clock/seq  : {output_capsule.header.clock}/{output_capsule.header.sequence}")
    print(f"  parent_id matches : {output_capsule.header.parent_id == input_capsule.header.capsule_id}")

    checks = []
    checks.append(("clock incremented", output_capsule.header.clock == input_capsule.header.clock + 1))
    checks.append(("sequence incremented", output_capsule.header.sequence == input_capsule.header.sequence + 1))
    checks.append(("parent_id linked", output_capsule.header.parent_id == input_capsule.header.capsule_id))
    checks.append(("has observations", len(output_capsule.observations) >= 1))
    checks.append(("integrity present", output_capsule.integrity.content_hash is not None))

    print("\n[Results]")
    all_ok = True
    for name, ok in checks:
        status = "PASS" if ok else "FAIL"
        print(f"  {status}: {name}")
        if not ok:
            all_ok = False

    print(f"\n  → Minimal Pipeline: {'PASS' if all_ok else 'FAIL'}")
    return all_ok


# ==========================================================
# Main
# ==========================================================

if __name__ == "__main__":
    print("PLP Experiment: Capsule Round-trip & Pipeline")
    print("実験は忠実に実際行って。\n")

    results = []
    results.append(("Capsule Round-trip", experiment_capsule_roundtrip()))
    results.append(("PGRA process_state", experiment_pgra_process_state()))
    results.append(("Minimal Pipeline", experiment_minimal_pipeline()))

    section("Summary")
    for name, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}: {name}")

    total = all(ok for _, ok in results)
    print(f"\n  Overall: {'PASS' if total else 'FAIL'}")
```

---

## 4. 実行方法

```bash
# リポジトリルートで
mkdir -p experiments
# 上記コードを experiments/roundtrip_pipeline.py に保存したうえで:

python experiments/roundtrip_pipeline.py
```

---

## 5. 成功条件（判定基準）

| 実験 | 成功条件 |
|------|----------|
| Experiment 1 | to_dict → from_dict で主要フィールドが一致し、hash が検証できる |
| Experiment 2 | 距離が target に近づき、Output Capsule に geometry/energy 観測が載る |
| Experiment 3 | clock/sequence が増加し、parent_id が前の capsule_id を指す |

---

## 6. 現時点で確認できないこと（次の実験へ）

- `PGRACodec.decode()` による Observation → PhysicalState の完全復元
- 複数 Module を直列につないだ本格 Pipeline（Core → PGRA → ...）
- Capsule のバイナリ形式や圧縮フラグの往復

これらは decode 実装後に追加実験する。

---

## 7. 実験後の記録欄

```
実行日時:
実行環境:
Overall 結果:
気づいた点 / 数値:
次にやること:
```

---

実験は忠実に実際行って。
