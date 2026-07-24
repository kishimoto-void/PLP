# Particle Language Protocol (PLP)

**Version**: [1.0.0](CHANGELOG.md) — Stable ABI Checkpoint

> **PLP** is a protocol for transporting immutable observations through stable interfaces, independent of application domains and execution environments.

> **PLP** は、不変な観測情報（Capsule）を安定した契約（Core ABI）を通じて伝達するためのプロトコルであり、実行環境や応用分野から独立して動作する。

---

## 読む順番（導線）

```text
README          「PLP とは何か」
   ↓
ARCHITECTURE    全体構造・Stable ABI
   ↓
CAPSULE         中心概念（観測の輸送単位）
   ↓
specs/          正式仕様（SPEC / CODEC_SPEC）
   ↓
codecs/ · PGRA/ リファレンス実装
   ↓
experiments/    実証結果
```

---

## Stable ABI v1.0

**Guaranteed Stable**

- Capsule · CapsuleCodec · CapsuleModule · CapsulePipeline · CapsuleSource · CapsuleSink

**Extensible**

- Runtime · Modules · IO · Observers · References

詳しくは [ARCHITECTURE.md](ARCHITECTURE.md) · [CHANGELOG.md](CHANGELOG.md) · [specs/](specs/)

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
├── README.md / ARCHITECTURE.md / HANDOVER.md / CHANGELOG.md
├── CAPSULE.md / LICENSE / VERSION
├── plp_capsule.py · plp_kernel.py   # 移行期（次メジャーで core 配下へ予定）
├── codecs/                          # Stable ABI + PGRACodec
├── core/                            # 世界定義（Particle0…）
├── PGRA/                            # Reference Module
├── modules/
├── specs/                           # 正式仕様（読みやすさ優先）
├── experiments/                     # 実験
└── docs/research/                   # 詳細考察用（任意）
```

物理ディレクトリを `plp/core/capsule.py` 等へ揃える作業は **import 互換のため次のメジャーバージョン** で行う。

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
