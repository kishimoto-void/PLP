# Particle Language Protocol (PLP)

> **PLP** is a protocol for transporting immutable observations through stable interfaces, independent of application domains and execution environments.

> **PLP** は、不変な観測情報（Capsule）を安定した契約（Core ABI）を通じて伝達するためのプロトコルであり、実行環境や応用分野から独立して動作する。

---

## Stable ABI v1.0

**Guaranteed Stable:** Capsule · CapsuleCodec · CapsuleModule · CapsulePipeline · CapsuleSource · CapsuleSink  
**Extensible:** Runtime · Modules · IO · Observers · References

詳しくは [ARCHITECTURE.md](ARCHITECTURE.md) · [specs/](specs/) · [CODEC_SPEC](specs/CODEC_SPEC.md)

---

## Core Flow

```text
Source → Pipeline(Modules) → Capsule → FanOut → Sinks
```

| 契約 | 役割 |
|------|------|
| **Module** | `process(capsule) → capsule` |
| **Sink** | `consume(capsule) → None` |
| **Source** | `produce() → capsule` |
| **Pipeline** | Module 直列のみ |
| **Codec** | Capsule ⇔ 内部状態 |

---

## Repository layout

```text
PLP/
├── README.md                 # 入口
├── ARCHITECTURE.md           # 憲法
├── HANDOVER.md               # 引き継ぎ
├── LICENSE
├── CAPSULE.md                # Capsule 設計目標
├── plp_capsule.py            # Capsule 実装
├── plp_kernel.py             # 旧 Kernel
├── codecs/                   # Stable ABI + PGRACodec
├── core/                     # 世界定義（Particle0…）
├── PGRA/                     # 幾何緩和 Module
├── modules/                  # 監視（将来 observers）
├── specs/                    # 正式仕様
└── experiments/              # 実験計画・結果
```

---

## Quick import

```python
from plp_capsule import PLPCapsule, CapsuleSerializer, verify_content_hash
from codecs import CapsulePipeline, FanOutDispatcher, PGRAModule, PGRACodec
from PGRA import PGRAPhysicsEngine, PhysicalState, DistanceReference
from core import Particle0, Geometry, Constraint, Clock
```

---

実験は忠実に実際行って。
