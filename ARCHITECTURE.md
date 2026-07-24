# PLP Architecture

**Version**: 1.2  
**Date**: 2026-07-24  
**Related**: SPEC.md, CAPSULE.md, CODEC_SPEC.md, HANDOVER.md

---

## 0. Guiding Principle

> **Capsule だけを知る。互いに知らない。**

Core 契約（Stable ABI）は変更しない。  
Runtime / Modules / IO はその上に自由に積む。

---

## 1. Core Stable ABI v1.0

```text
Core (変更しない契約)
├── Capsule
├── CapsuleCodec      decode / encode
├── CapsuleModule     process(capsule) -> capsule
├── CapsulePipeline   直列 Module 合成のみ
├── CapsuleSource     produce() -> capsule
└── CapsuleSink       consume(capsule) -> None
```

| 契約 | 役割 |
|------|------|
| **Module** | 変換（産む） |
| **Sink** | 消費（変更しない） |
| **Source** | 入口 |
| **Pipeline** | Module の直列のみ。Sink を知らない |
| **Codec** | Capsule ⇔ 内部状態。ロジックなし |

実装場所: `codecs/base.py`

---

## 2. Pipeline vs Runtime

```text
Pipeline（変換）

  Capsule → Module → Module → Capsule

Runtime（観測・保存・配信）

  Capsule
        │
        ├ MemorySink
        ├ LoggerSink
        ├ MetricsSink
        └ Visualizer
```

```text
Source
  ↓
Pipeline (Modules only)
  ↓
Capsule
  ↓
FanOutDispatcher
  ├── MemorySink
  ├── LoggerSink
  ├── NetworkTransport
  └── …
```

- **Module は Dispatcher を知らない**
- **Dispatcher だけが Sink 一覧を持つ**
- Sink の追加・削除はプラグイン

---

## 3. Layer Model

```text
plp/
├── core/          # Stable ABI（Capsule, Codec, Module, Pipeline, Source, Sink）
├── runtime/       # Memory, Replay, Scheduler, FanOut, Metrics
├── modules/       # PGRA, Fractal, Physics, …
├── io/            # Logger, Network, persistent Store, Visualizer
├── observers/
├── references/
└── specs/
```

| Layer | 拡張方針 |
|-------|----------|
| **core** | 契約固定。安易に増やさない |
| **runtime** | 自由に拡張（Sink 中心） |
| **modules** | 自由に拡張（Module 中心） |
| **io** | 自由に拡張（Source / Sink） |

---

## 4. Minimal Protocols

```python
class CapsuleModule(Protocol):
    def process(self, capsule: PLPCapsule) -> PLPCapsule: ...

class CapsuleSink(Protocol):
    def consume(self, capsule: PLPCapsule) -> None: ...

class CapsuleSource(Protocol):
    def produce(self) -> PLPCapsule: ...
```

これ以上のメソッドを Core に足さない。  
検索・close・connect などは各実装の固有 API とする。

---

## 5. FanOutDispatcher

```python
dispatcher = FanOutDispatcher()
dispatcher.add(memory_sink)
dispatcher.add(logger_sink)

out = pipeline.run(capsule)
dispatcher.dispatch(out)
```

または:

```python
runtime = CapsuleRuntime(
    source=file_source,
    pipeline=pipeline,
    dispatcher=dispatcher,
)
out = runtime.step()
```

---

## 6. Memory の位置

`runtime/memory` — **MemorySink**（`consume` のみが Core 契約）

- append-only Capsule Chain
- Difference / Replay / Drift は Sink 固有 API
- PGRA を知らない / PGRA も Memory を知らない

---

## 7. 現リポジトリ対応

| 現在 | 目標 |
|------|------|
| `plp_capsule.py` | core/capsule |
| `codecs/base.py` | **Core Stable ABI（実装済み）** |
| `codecs/pgra_codec.py` | modules/pgra + codec 参照実装 |
| `PGRA/` | modules/pgra |
| `core/` (Particle0…) | world 定義（modules または core/world） |
| Memory（ローカル） | runtime/memory（未 push） |

新規は契約に従う。物理ディレクトリ移動は段階的。

---

## 8. Non-Goals（Core）

Core 契約は以下をやらない・持たない:

- 永続化・ネットワーク・UI
- 推論・学習・意味解釈
- Sink の検索 API の統一
- Module 間の直接呼び出し規約

---

## 9. 一言

> **Core = 変更しない契約。**  
> Pipeline は変換、Runtime は観測・保存・配信。  
> Source → Pipeline → FanOut → Sinks が全体像。

実験は忠実に実際行って。
