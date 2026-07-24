# Particle Language Protocol (PLP)

> **PLP** is a protocol for transporting immutable observations through stable interfaces, independent of application domains and execution environments.

> **PLP** は、不変な観測情報（Capsule）を安定した契約（Core ABI）を通じて伝達するためのプロトコルであり、実行環境や応用分野から独立して動作する。

---

## Stable ABI v1.0

**Guaranteed Stable**

- Capsule
- CapsuleCodec
- CapsuleModule
- CapsulePipeline
- CapsuleSource
- CapsuleSink

**Extensible**

- Runtime（Memory, Replay, Metrics, …）
- Modules（PGRA, Fractal, …）
- IO（Logger, Network, Sources, …）
- Observers / References

詳細: [`ARCHITECTURE.md`](ARCHITECTURE.md) · [`CODEC_SPEC.md`](CODEC_SPEC.md) · [`SPEC.md`](SPEC.md)

---

## Core Flow

```text
Source → Pipeline(Modules) → Capsule → FanOut → Sinks
```

| 契約 | 役割 |
|------|------|
| **Module** | `process(capsule) → capsule`（変換） |
| **Sink** | `consume(capsule) → None`（消費・変更しない） |
| **Source** | `produce() → capsule`（入口） |
| **Pipeline** | Module の直列のみ。Sink を知らない |
| **Codec** | Capsule ⇔ 内部状態。ロジックなし |

PLP 自身は単語の意味・感情・文脈・意図を保持しない。  
意味の解釈は Capsule を受け取った側（LLM 等）が行う。

---

## Quick import

```python
from plp_capsule import PLPCapsule, CapsuleSerializer, verify_content_hash
from codecs import (
    CapsulePipeline,
    FanOutDispatcher,
    CapsuleRuntime,
    PGRAModule,
    PGRACodec,
    DecodedState,
)
from PGRA import PGRAPhysicsEngine, PhysicalState, DistanceReference
from core import Particle0, Geometry, Constraint, Clock
```

---

## Repository layout (current)

```text
PLP/
├── plp_capsule.py          # Capsule 規格
├── codecs/
│   ├── base.py             # Stable ABI v1.0
│   └── pgra_codec.py       # リファレンス Codec / Module
├── core/                   # 世界定義（Particle0 / Geometry / Constraint / Clock）
├── PGRA/                   # 幾何緩和 Module
├── modules/                # 監視（将来 observers へ）
├── ARCHITECTURE.md         # 憲法
├── CODEC_SPEC.md / SPEC.md / CAPSULE.md
└── EXPERIMENT_*.md
```

目標レイヤー（core / runtime / modules / io / specs）への物理移動は段階的。仕様は先行固定済み。

---

## Design principles

1. **Semantic Free** — 意味を知らない
2. **Observer First** — 観測のみ。推論しない
3. **Stable Core** — ABI を安易に変えない
4. **Extensible Edges** — Runtime / Modules / IO は自由に積む

---

## License

See `LICENSE`.

実験は忠実に実際行って。
